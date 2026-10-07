"""Shared mutable scan state used by the individual detectors.

Detectors only read files. Nothing here executes repository code.
"""

from __future__ import annotations

import json
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from cwi.domain.enums import Confidence
from cwi.domain.models import DetectedCommand, Detection

MAX_READ_BYTES = 512 * 1024  # never read huge files during detection

CATEGORIES = (
    "languages",
    "frameworks",
    "package_managers",
    "databases",
    "infrastructure",
    "test_tools",
    "tools",
)


@dataclass
class Unit:
    """A project unit: the root or a subproject directory (apps/api, frontend, ...)."""

    path: str  # "" for the root, otherwise POSIX relative path
    language: str | None = None
    language_version: str | None = None
    frameworks: list[str] = field(default_factory=list)
    framework_versions: dict[str, str] = field(default_factory=dict)  # display name -> "15.1"
    databases: list[str] = field(default_factory=list)
    package_managers: list[str] = field(default_factory=list)
    test_tools: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    backend: bool = False
    frontend: bool = False
    has_manifest: bool = False

    def add_unique(self, attr: str, value: str) -> None:
        items: list[str] = getattr(self, attr)
        if value not in items:
            items.append(value)

    @property
    def display_path(self) -> str:
        return self.path or "."

    @property
    def role(self) -> str:
        if self.backend and self.frontend:
            return "App"
        if self.backend:
            return "Backend"
        if self.frontend:
            return "Frontend"
        return "Project"

    def prefix(self, file: str) -> str:
        return f"{self.path}/{file}" if self.path else file


@dataclass
class ScanContext:
    root: Path
    cwi_template: bool = False
    detections: dict[str, dict[str, Detection]] = field(
        default_factory=lambda: {c: {} for c in CATEGORIES}
    )
    units: dict[str, Unit] = field(default_factory=dict)
    commands: list[DetectedCommand] = field(default_factory=list)
    signals: list[str] = field(default_factory=list)
    python_version: str | None = None
    monorepo_signals: list[str] = field(default_factory=list)
    ai_signals: list[str] = field(default_factory=list)
    data_signals: list[str] = field(default_factory=list)
    cli_signals: list[str] = field(default_factory=list)
    library_signals: list[str] = field(default_factory=list)
    ignored_paths: set[str] = field(default_factory=set)

    # --- detections --------------------------------------------------------------------------
    def add(
        self, category: str, value: str, source: str, confidence: float = Confidence.HIGH
    ) -> None:
        bucket = self.detections[category]
        key = value.lower()
        current = bucket.get(key)
        if current is None or confidence > current.confidence:
            bucket[key] = Detection(value=value, confidence=confidence, source=source)

    def add_for(
        self,
        unit: Unit,
        category: str,
        value: str,
        source: str,
        confidence: float = Confidence.HIGH,
    ) -> None:
        """Record a detection globally and on the unit it belongs to."""
        self.add(category, value, source, confidence)
        if category in ("frameworks", "databases", "package_managers", "test_tools", "tools"):
            unit.add_unique(category, value)

    def has(self, category: str, value: str) -> bool:
        return value.lower() in self.detections[category]

    def unit(self, path: str) -> Unit:
        if path not in self.units:
            self.units[path] = Unit(path=path)
        return self.units[path]

    def add_command(self, command: DetectedCommand) -> None:
        for existing in self.commands:
            if existing.group == command.group and existing.label == command.label:
                return  # first (highest-precedence) source wins
        self.commands.append(command)

    # --- safe file helpers ---------------------------------------------------------------------
    def path(self, rel: str) -> Path:
        return self.root / rel if rel else self.root

    def exists(self, rel: str) -> bool:
        p = self.path(rel)
        return p.exists() and not p.is_symlink()

    def is_file(self, rel: str) -> bool:
        p = self.path(rel)
        return p.is_file() and not p.is_symlink()

    def exact_file(self, rel: str) -> bool:
        """Like is_file, but the final name must match case-sensitively (macOS/Windows safe)."""
        p = self.path(rel)
        if not self.is_file(rel):
            return False
        try:
            return p.name in {c.name for c in p.parent.iterdir()}
        except OSError:
            return False

    def is_dir(self, rel: str) -> bool:
        p = self.path(rel)
        return p.is_dir() and not p.is_symlink()

    def read_text(self, rel: str) -> str | None:
        p = self.path(rel)
        try:
            if not p.is_file() or p.is_symlink() or p.stat().st_size > MAX_READ_BYTES:
                return None
            return p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return None

    def read_json(self, rel: str) -> Any:
        text = self.read_text(rel)
        if text is None:
            return None
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None

    def read_toml(self, rel: str) -> dict[str, Any] | None:
        text = self.read_text(rel)
        if text is None:
            return None
        try:
            return tomllib.loads(text)
        except tomllib.TOMLDecodeError:
            return None

    def glob(self, rel_dir: str, pattern: str) -> list[str]:
        base = self.path(rel_dir)
        if not base.is_dir():
            return []
        out = []
        for p in sorted(base.glob(pattern)):
            if p.is_symlink():
                continue
            out.append(p.relative_to(self.root).as_posix())
        return out


def join(unit_path: str, name: str) -> str:
    return f"{unit_path}/{name}" if unit_path else name
