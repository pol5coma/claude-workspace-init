"""Transactional plan executor. It applies exactly the plan; it never decides anything."""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

from cwi.domain.enums import OperationType
from cwi.domain.errors import ApplyError, CWIError
from cwi.domain.models import ExecutionResult, InstallationPlan, PlannedOperation
from cwi.install.filesystem import FileSystem
from cwi.install.rollback import Transaction
from cwi.install.validator import validate_cleanup, validate_installation
from cwi.planning.cleanup import CATALOG_OWNER, TEMPLATE_OWNER
from cwi.state.hashing import sha256_file

log = logging.getLogger("cwi.executor")
_JUNK = {".DS_Store", "Thumbs.db"}
RECURSIVE_DELETE_OWNERS = {TEMPLATE_OWNER, CATALOG_OWNER}


def _check_preconditions(fs: FileSystem, plan: InstallationPlan) -> None:
    """The repository must still look exactly like it did when the plan was previewed."""
    for op in plan.operations:
        path = fs.path(op.target)
        if op.type == OperationType.MKDIR:
            if path.exists() and not path.is_dir():
                raise ApplyError(f"{op.target} changed since the preview (a file now exists there)")
            continue
        if op.type == OperationType.DELETE_DIR:
            if op.owner not in RECURSIVE_DELETE_OWNERS and not op.only_if_empty:
                raise ApplyError(f"Refusing recursive deletion of non-CWI directory {op.target}")
            continue
        if op.before_hash is None:
            if path.exists() and op.type != OperationType.DELETE:
                raise ApplyError(f"{op.target} appeared since the preview; re-run cwi init")
        elif not path.is_file() or sha256_file(path) != op.before_hash:
            raise ApplyError(f"{op.target} changed since the preview; re-run cwi init")


def _apply(fs: FileSystem, tx: Transaction, op: PlannedOperation) -> bool:
    """Apply one operation. Returns False when it was a no-op (e.g. non-empty only-if-empty dir)."""
    path = fs.path(op.target)
    if op.type == OperationType.MKDIR:
        if path.is_dir():
            return False
        fs.mkdir(op.target)
        tx.created_dir(op.target)
        return True
    if op.type == OperationType.COPY:
        assert op.source is not None
        if path.exists():
            tx.backup_file(op.target)
        else:
            tx.created_file(op.target)
        fs.copy_file(Path(op.source), op.target)
        return True
    if op.type in (OperationType.CREATE, OperationType.UPDATE, OperationType.MERGE_JSON):
        assert op.after_content is not None
        if path.exists():
            tx.backup_file(op.target)
        else:
            tx.created_file(op.target)
        fs.atomic_write_text(op.target, op.after_content)
        return True
    if op.type == OperationType.DELETE:
        if not path.exists():
            return False
        tx.backup_file(op.target, action="deleted_file")
        fs.remove_file(op.target)
        return True
    if op.type == OperationType.DELETE_DIR:
        if not path.is_dir():
            return False
        if op.only_if_empty:
            children = list(path.iterdir())
            if any(c.name not in _JUNK for c in children):
                return False
            for junk in children:
                rel = f"{op.target}/{junk.name}"
                tx.backup_file(rel, action="deleted_file")
                fs.remove_file(rel)
            fs.remove_empty_dir(op.target)
            tx.removed_empty_dir(op.target)
            return True
        tx.backup_tree(op.target)
        fs.remove_tree(op.target)
        return True
    raise ApplyError(f"Unknown operation type {op.type}")


def execute_plan(
    plan: InstallationPlan,
    root: Path,
    fs: FileSystem | None = None,
    progress: Callable[[int, int, PlannedOperation], None] | None = None,
) -> ExecutionResult:
    fs = fs or FileSystem(root)
    root = fs.root
    _check_preconditions(fs, plan)
    tx = Transaction(root=root, fs=fs)
    applied: list[PlannedOperation] = []
    total = len(plan.operations)
    done = 0

    def report(op: PlannedOperation) -> None:
        nonlocal done
        done += 1
        if progress is not None:
            progress(done, total, op)

    tx.begin()
    try:
        for op in plan.operations:
            if op.is_delete:
                continue
            log.debug("apply %s %s", op.type, op.target)
            report(op)
            if _apply(fs, tx, op):
                applied.append(op)
        validate_installation(root, plan)
        for op in plan.operations:
            if not op.is_delete:
                continue
            log.debug("apply %s %s", op.type, op.target)
            report(op)
            if _apply(fs, tx, op):
                applied.append(op)
        validate_cleanup(root, plan)
    except BaseException as exc:
        problems = tx.rollback()
        detail = f"{type(exc).__name__}: {exc}"
        if problems:
            raise ApplyError(
                "Initialization failed and rollback was incomplete.\n"
                f"Cause: {detail}\nBackup kept at {tx.backup_dir}\nProblems:\n  - "
                + "\n  - ".join(problems)
            ) from exc
        if isinstance(exc, KeyboardInterrupt):
            raise
        message = str(exc) if isinstance(exc, CWIError) else detail
        raise ApplyError(
            f"Initialization failed: {message}\nNo project changes were kept."
        ) from exc
    tx.commit()
    return ExecutionResult(applied=applied, backup_dir=None, state=plan.state)
