"""Resolve the versions a project actually uses. Read-only; lockfiles first, then manifests.

Only real evidence produces a version: an exact lockfile entry, an exact pin, or a caret/tilde
range. A bare lower bound such as `>=0.115` says nothing about the version in use, so it yields
None rather than a guess. Versions are shown as `major.minor`.
"""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass, field

from cwi.scanner.context import ScanContext, join

_VERSION = re.compile(r"(\d+)\.(\d+)(?:\.\d+)?")


def short(version: str | None) -> str | None:
    """'15.1.3' -> '15.1'; '19' -> '19'; junk -> None."""
    if not version:
        return None
    match = _VERSION.search(version)
    if match:
        return f"{match.group(1)}.{match.group(2)}"
    whole = re.fullmatch(r"\D*(\d+)\D*", version)
    return whole.group(1) if whole else None


def js_spec_version(spec: str) -> str | None:
    spec = spec.strip()
    if re.fullmatch(r"[\^~]?\d+(\.\d+){0,2}([-+].*)?", spec):
        return short(spec.lstrip("^~"))
    return None


def py_spec_version(spec: str) -> str | None:
    """Only exact (==) and compatible (~=) pins identify a version."""
    match = re.search(r"(==|~=)\s*([\d][\w.]*)", spec)
    return short(match.group(2)) if match else None


def _norm_py(name: str) -> str:
    return name.lower().replace("_", "-").replace(".", "-")


@dataclass
class LockIndex:
    """Exact versions from the lockfiles of one unit (and the repository root)."""

    exact: dict[str, str] = field(default_factory=dict)

    def resolve(self, name: str, spec: str | None, *, python: bool = False) -> str | None:
        key = _norm_py(name) if python else name
        if key in self.exact:
            return short(self.exact[key])
        if spec:
            return py_spec_version(spec) if python else js_spec_version(spec)
        return None


def _bases(unit_path: str) -> list[str]:
    return list(dict.fromkeys([unit_path, ""]))


def js_lock_index(ctx: ScanContext, unit_path: str, names: list[str]) -> LockIndex:
    index = LockIndex()
    wanted = set(names)
    for base in _bases(unit_path):
        lock = ctx.read_json(join(base, "package-lock.json"))
        if isinstance(lock, dict):
            packages = lock.get("packages") or {}
            prefix = f"{unit_path}/" if base == "" and unit_path else ""
            for name in wanted - set(index.exact):
                entry = packages.get(f"{prefix}node_modules/{name}") or packages.get(
                    f"node_modules/{name}"
                )
                if isinstance(entry, dict) and isinstance(entry.get("version"), str):
                    index.exact[name] = entry["version"]
            for name, entry in (lock.get("dependencies") or {}).items():  # lockfile v1
                if (
                    name in wanted
                    and isinstance(entry, dict)
                    and isinstance(entry.get("version"), str)
                ):
                    index.exact.setdefault(name, entry["version"])
        pnpm = ctx.read_text(join(base, "pnpm-lock.yaml"))
        if pnpm:
            for name in wanted - set(index.exact):
                match = re.search(rf"(?m)^\s+['\"]?/?{re.escape(name)}@(\d+\.\d+\.\d+)", pnpm)
                if match:
                    index.exact[name] = match.group(1)
        yarn = ctx.read_text(join(base, "yarn.lock"))
        if yarn:
            for name in wanted - set(index.exact):
                match = re.search(
                    rf'(?m)^"?{re.escape(name)}@[^\n]*:\n\s+version:?\s+"?(\d+\.\d+\.\d+)', yarn
                )
                if match:
                    index.exact[name] = match.group(1)
    return index


def py_lock_index(ctx: ScanContext, unit_path: str) -> LockIndex:
    index = LockIndex()
    for base in _bases(unit_path):
        for lockfile in ("uv.lock", "poetry.lock", "pdm.lock"):
            rel = join(base, lockfile)
            if rel in ctx.ignored_paths:
                continue
            text = ctx.read_text(rel)
            if not text:
                continue
            try:
                data = tomllib.loads(text)
            except tomllib.TOMLDecodeError:
                continue
            for package in data.get("package") or []:
                if isinstance(package, dict) and package.get("name") and package.get("version"):
                    index.exact.setdefault(_norm_py(str(package["name"])), str(package["version"]))
    return index
