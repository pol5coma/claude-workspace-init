"""Diff rendering helpers (text only; the UI decides how to display them)."""

from __future__ import annotations

import difflib
from pathlib import Path

from cwi.domain.enums import OperationType
from cwi.domain.models import PlannedOperation
from cwi.planning.safety import resolve_inside


def unified_diff(before: str, after: str, path: str) -> str:
    lines = difflib.unified_diff(
        before.splitlines(keepends=True),
        after.splitlines(keepends=True),
        fromfile=f"a/{path}",
        tofile=f"b/{path}",
    )
    return "".join(lines)


def _read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def operation_diff(root: Path, op: PlannedOperation) -> str:
    """Human-readable diff for one operation."""
    target = resolve_inside(root, op.target)
    if op.type == OperationType.MKDIR:
        return f"NEW DIRECTORY {op.target}"
    if op.type == OperationType.DELETE_DIR:
        suffix = " (only if empty)" if op.only_if_empty else ""
        return f"REMOVE CWI-OWNED DIRECTORY {op.target}{suffix}"
    if op.type == OperationType.DELETE:
        return f"REMOVE CWI-OWNED FILE {op.target}"
    if op.type == OperationType.COPY:
        new = _read(Path(op.source)) if op.source else None
    else:
        new = op.after_content
    if op.before_hash is None:
        return f"NEW FILE {op.target}"
    old = _read(target)
    if old is None or new is None:
        return f"UPDATE {op.target} (binary or unreadable)"
    diff = unified_diff(old, new, op.target)
    return diff or f"UNCHANGED {op.target}"


def reviewable(op: PlannedOperation) -> bool:
    """Operations that modify an existing file (diffs worth showing)."""
    return op.before_hash is not None and op.type in (
        OperationType.UPDATE,
        OperationType.MERGE_JSON,
        OperationType.COPY,
    )
