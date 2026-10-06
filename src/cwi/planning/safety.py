"""Path containment checks shared by the planner and the filesystem adapter."""

from __future__ import annotations

from pathlib import Path

from cwi.catalog.validator import is_safe_relative
from cwi.domain.errors import UnsafePathError


def resolve_inside(root: Path, rel: str) -> Path:
    """Return root/rel after verifying it stays inside root and crosses no symlink.

    Every existing component between root and the target must be a real directory/file,
    never a symlink, so a malicious link cannot redirect a write or delete outside the repo.
    """
    if not is_safe_relative(rel):
        raise UnsafePathError(f"Refusing unsafe path '{rel}' (absolute or traversal)")
    root_resolved = root.resolve()
    current = root_resolved
    for part in Path(rel).parts:
        current = current / part
        if current.is_symlink():
            raise UnsafePathError(f"Refusing to operate through symlink: {current}")
    target = (root_resolved / rel).resolve(strict=False)
    if target != root_resolved and root_resolved not in target.parents:
        raise UnsafePathError(f"Path escapes the project root: {rel}")
    return root_resolved / rel
