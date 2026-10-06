"""The only module that mutates the repository. Every path is containment-checked first."""

from __future__ import annotations

import os
import shutil
import uuid
from pathlib import Path

from cwi.domain.errors import UnsafePathError
from cwi.planning.safety import resolve_inside


class FileSystem:
    """Root-scoped filesystem adapter. Subclass in tests to inject failures."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def path(self, rel: str) -> Path:
        return resolve_inside(self.root, rel)

    # --- hooks for failure injection ----------------------------------------------------------
    def before_mutation(
        self, action: str, rel: str
    ) -> None:  # pragma: no cover - overridden in tests
        return None

    # --- primitives ---------------------------------------------------------------------------
    def mkdir(self, rel: str) -> None:
        self.before_mutation("mkdir", rel)
        self.path(rel).mkdir(parents=False, exist_ok=False)

    def atomic_write_text(self, rel: str, content: str) -> None:
        self.atomic_write_bytes(rel, content.encode("utf-8"))

    def atomic_write_bytes(self, rel: str, content: bytes) -> None:
        self.before_mutation("write", rel)
        target = self.path(rel)
        tmp = target.with_name(f".{target.name}.cwi-tmp-{uuid.uuid4().hex[:8]}")
        try:
            with tmp.open("wb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            if target.exists():
                shutil.copymode(target, tmp)
            os.replace(tmp, target)
        finally:
            if tmp.exists():
                tmp.unlink()

    def copy_file(self, source: Path, rel: str) -> None:
        """Copy preserving the source's permission bits (executable intent)."""
        self.before_mutation("copy", rel)
        if source.is_symlink():
            raise UnsafePathError(f"Refusing to copy symlink {source}")
        target = self.path(rel)
        tmp = target.with_name(f".{target.name}.cwi-tmp-{uuid.uuid4().hex[:8]}")
        try:
            shutil.copyfile(source, tmp)
            shutil.copymode(source, tmp)
            os.replace(tmp, target)
        finally:
            if tmp.exists():
                tmp.unlink()

    def remove_file(self, rel: str) -> None:
        self.before_mutation("remove_file", rel)
        target = self.path(rel)
        if target.is_dir() and not target.is_symlink():
            raise UnsafePathError(f"Expected a file, found a directory: {rel}")
        target.unlink()

    def remove_empty_dir(self, rel: str) -> None:
        self.before_mutation("rmdir", rel)
        self.path(rel).rmdir()

    def remove_tree(self, rel: str) -> None:
        self.before_mutation("remove_tree", rel)
        target = self.path(rel)
        if target == self.root:
            raise UnsafePathError("Refusing to remove the project root")
        if target.is_symlink() or not target.is_dir():
            raise UnsafePathError(f"Refusing recursive removal of non-directory {rel}")
        shutil.rmtree(target)
