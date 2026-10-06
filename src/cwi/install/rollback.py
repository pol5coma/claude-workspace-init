"""Transaction journal with backups so a failed apply restores the previous repository state."""

from __future__ import annotations

import json
import shutil
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from cwi import paths
from cwi.install.filesystem import FileSystem


@dataclass
class _Entry:
    action: str  # created_file | created_dir | modified_file | deleted_file | deleted_dir | removed_empty_dir
    target: str
    backup: str | None = None


@dataclass
class Transaction:
    root: Path
    fs: FileSystem
    txid: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    entries: list[_Entry] = field(default_factory=list)
    _created_work_dir: bool = False
    _started: bool = False

    @property
    def work_dir(self) -> Path:
        return self.root / paths.rel(paths.CWI_WORK_DIR)

    @property
    def backup_dir(self) -> Path:
        return self.root / paths.rel(paths.BACKUPS_DIR) / self.txid

    def begin(self) -> None:
        self._created_work_dir = not self.work_dir.exists()
        self.backup_dir.mkdir(parents=True, exist_ok=False)
        self._started = True
        self._save()

    def _save(self) -> None:
        journal = [e.__dict__ for e in self.entries]
        (self.backup_dir / "journal.json").write_text(
            json.dumps(journal, indent=2), encoding="utf-8"
        )

    def _backup_path(self, rel: str) -> Path:
        return self.backup_dir / "files" / rel

    # --- recording ----------------------------------------------------------------------------
    def created_file(self, rel: str) -> None:
        self.entries.append(_Entry("created_file", rel))
        self._save()

    def created_dir(self, rel: str) -> None:
        self.entries.append(_Entry("created_dir", rel))
        self._save()

    def removed_empty_dir(self, rel: str) -> None:
        self.entries.append(_Entry("removed_empty_dir", rel))
        self._save()

    def backup_file(self, rel: str, action: str = "modified_file") -> None:
        source = self.fs.path(rel)
        backup = self._backup_path(rel)
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, backup)
        self.entries.append(_Entry(action, rel, backup.relative_to(self.backup_dir).as_posix()))
        self._save()

    def backup_tree(self, rel: str) -> None:
        source = self.fs.path(rel)
        backup = self._backup_path(rel)
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, backup, symlinks=True)
        self.entries.append(
            _Entry("deleted_dir", rel, backup.relative_to(self.backup_dir).as_posix())
        )
        self._save()

    # --- outcome ------------------------------------------------------------------------------
    def rollback(self) -> list[str]:
        """Undo every recorded action in reverse order. Returns problems (empty = clean)."""
        problems: list[str] = []
        for entry in reversed(self.entries):
            target = self.root / entry.target
            try:
                if entry.action == "created_file":
                    if target.exists() or target.is_symlink():
                        target.unlink()
                elif entry.action == "removed_empty_dir":
                    target.mkdir(parents=True, exist_ok=True)
                elif entry.action == "created_dir":
                    if target.is_dir() and not any(target.iterdir()):
                        target.rmdir()
                elif entry.action in ("modified_file", "deleted_file"):
                    assert entry.backup
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(self.backup_dir / entry.backup, target)
                elif entry.action == "deleted_dir":
                    assert entry.backup
                    if target.exists():
                        shutil.rmtree(target)
                    shutil.copytree(self.backup_dir / entry.backup, target, symlinks=True)
            except OSError as exc:
                problems.append(f"{entry.action} {entry.target}: {exc}")
        if not problems:
            self._discard()
        return problems

    def commit(self) -> None:
        self._discard()

    def _discard(self) -> None:
        if not self._started:
            return
        shutil.rmtree(self.backup_dir, ignore_errors=True)
        backups = self.root / paths.rel(paths.BACKUPS_DIR)
        for directory in (backups, self.work_dir):
            if directory.is_dir() and not any(directory.iterdir()):
                directory.rmdir()
        self._started = False
