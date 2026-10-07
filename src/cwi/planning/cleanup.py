"""Cleanup planning: CWI may clean up what CWI owns. It never guesses ownership of user files."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

from cwi import paths
from cwi.catalog.validator import is_safe_relative
from cwi.domain.enums import CapabilityType, OperationType
from cwi.domain.models import Catalog, PlannedOperation
from cwi.planning.safety import resolve_inside

TEMPLATE_OWNER = "cwi-template"
CATALOG_OWNER = "cwi-catalog"
_JUNK = {".DS_Store", "Thumbs.db"}


def template_gate(root: Path) -> tuple[bool, str]:
    """True when root is an uninitialized CWI template (marker + CWI pyproject)."""
    marker = root / paths.rel(paths.TEMPLATE_MARKER)
    if not marker.is_file():
        return False, "no CWI template marker"
    pyproject = root / "pyproject.toml"
    if not pyproject.is_file():
        return False, "template marker present but pyproject.toml is missing"
    try:
        name = (tomllib.loads(pyproject.read_text(encoding="utf-8")).get("project") or {}).get(
            "name"
        )
    except (OSError, tomllib.TOMLDecodeError):
        return False, "pyproject.toml is unreadable"
    if name != paths.CWI_PACKAGE_NAME:
        return False, f"pyproject.toml belongs to '{name}', not CWI"
    return True, "CWI template detected"


def bootstrap_paths(root: Path) -> list[str]:
    """Paths listed by the marker, restricted to the known CWI bootstrap set (marker can only narrow)."""
    allowed = set(paths.DEFAULT_BOOTSTRAP_PATHS)
    marker = root / paths.rel(paths.TEMPLATE_MARKER)
    try:
        data = json.loads(marker.read_text(encoding="utf-8"))
        listed = data.get("bootstrap_paths") if isinstance(data, dict) else None
    except (OSError, json.JSONDecodeError):
        listed = None
    if not isinstance(listed, list):
        listed = list(paths.DEFAULT_BOOTSTRAP_PATHS)
    result = [p for p in listed if isinstance(p, str) and p in allowed and is_safe_relative(p)]
    if paths.rel(paths.TEMPLATE_MARKER) not in result:
        result.append(paths.rel(paths.TEMPLATE_MARKER))
    return result


def _looks_like_cwi_catalog(directory: Path) -> bool:
    if not directory.is_dir() or directory.is_symlink():
        return False
    type_dirs = {t.plural for t in CapabilityType}
    for child in directory.iterdir():
        if child.name in _JUNK:
            continue
        if child.name not in type_dirs or not child.is_dir() or child.is_symlink():
            return False
        for cap_dir in child.iterdir():
            if cap_dir.name in _JUNK:
                continue
            if not cap_dir.is_dir() or cap_dir.is_symlink():
                return False
            if (cap_dir / paths.GROUP_MANIFEST).is_file():
                for member in cap_dir.iterdir():
                    if member.name in _JUNK or member.name == paths.GROUP_MANIFEST:
                        continue
                    if not member.is_dir() or not (member / "cwi.json").is_file():
                        return False
            elif not (cap_dir / "cwi.json").is_file():
                return False
    return True


def _only_template_files(directory: Path) -> bool:
    if not directory.is_dir() or directory.is_symlink():
        return False
    names = {c.name for c in directory.iterdir()} - _JUNK
    return names <= {"CLAUDE.md"}


def _delete_op(root: Path, rel: str, owner: str, reason: str) -> PlannedOperation | None:
    path = resolve_inside(root, rel)
    if not path.exists() and not path.is_symlink():
        return None
    if path.is_dir() and not path.is_symlink():
        return PlannedOperation(
            type=OperationType.DELETE_DIR, target=rel, owner=owner, reason=reason
        )
    from cwi.state.hashing import sha256_file

    before = sha256_file(path) if path.is_file() else None
    return PlannedOperation(
        type=OperationType.DELETE, target=rel, before_hash=before, owner=owner, reason=reason
    )


def plan_cleanup(
    root: Path,
    *,
    catalog: Catalog | None,
    template: bool,
    catalog_cleanup: bool,
) -> tuple[list[PlannedOperation], list[str]]:
    ops: list[PlannedOperation] = []
    warnings: list[str] = []
    gate, why = template_gate(root)

    if template:
        if not gate:
            warnings.append(f"Bootstrap cleanup skipped: {why}")
        else:
            for rel in bootstrap_paths(root):
                op = _delete_op(root, rel, TEMPLATE_OWNER, "remove CWI bootstrap resource")
                if op:
                    ops.append(op)
            for parent in paths.BOOTSTRAP_PARENTS_IF_EMPTY:
                if (root / parent).is_dir():
                    ops.append(
                        PlannedOperation(
                            type=OperationType.DELETE_DIR,
                            target=parent,
                            owner=TEMPLATE_OWNER,
                            reason="remove directory if empty after bootstrap cleanup",
                            only_if_empty=True,
                        )
                    )
            return ops, warnings

    if not catalog_cleanup or catalog is None:
        return ops, warnings
    local_catalog = root.resolve() / paths.rel(paths.CATALOG_DIR)
    if catalog.root.resolve() == local_catalog:
        if _looks_like_cwi_catalog(local_catalog):
            op = _delete_op(
                root, paths.rel(paths.CATALOG_DIR), CATALOG_OWNER, "remove unused CWI catalog"
            )
            if op:
                ops.append(op)
        else:
            warnings.append("catalog/ contains files CWI does not recognise; it was not removed")
        templates = root / paths.rel(paths.TEMPLATES_DIR)
        if templates.exists():
            if _only_template_files(templates):
                op = _delete_op(
                    root, paths.rel(paths.TEMPLATES_DIR), CATALOG_OWNER, "remove CWI templates"
                )
                if op:
                    ops.append(op)
            else:
                warnings.append("templates/ contains non-CWI files; it was not removed")
    return ops, warnings
