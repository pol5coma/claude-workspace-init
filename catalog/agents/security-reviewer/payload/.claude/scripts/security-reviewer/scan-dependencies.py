#!/usr/bin/env python3
"""Offline dependency inventory for the security-reviewer agent.

Reads manifests only. Never runs a package manager and never contacts the network.
Reports declared dependencies, loose version constraints and missing lockfiles.
"""

from __future__ import annotations

import json
import os
import re
import sys
import tomllib
from pathlib import Path

IGNORED = {
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "dist",
    "build",
    ".next",
    "target",
    "__pycache__",
}
MAX_DEPTH = 3


def manifests(root: Path):
    for dirpath, dirnames, filenames in os.walk(root):
        depth = len(Path(dirpath).relative_to(root).parts)
        dirnames[:] = (
            [d for d in dirnames if d not in IGNORED and not d.startswith(".")]
            if depth < MAX_DEPTH
            else []
        )
        for name in filenames:
            if name in {
                "package.json",
                "pyproject.toml",
                "requirements.txt",
                "go.mod",
                "Cargo.toml",
            }:
                yield Path(dirpath, name)


def loose_python(spec: str) -> bool:
    spec = spec.split(";")[0].strip()
    return not re.search(r"(==|~=|<)", spec)


def check_python(path: Path, report: list[str]) -> None:
    deps: list[str] = []
    if path.name == "pyproject.toml":
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        deps = list((data.get("project") or {}).get("dependencies") or [])
        lock = any((path.parent / f).exists() for f in ("uv.lock", "poetry.lock", "pdm.lock"))
    else:
        deps = [
            line.strip()
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith(("#", "-"))
        ]
        lock = all("==" in d for d in deps) if deps else True
    loose = [d for d in deps if loose_python(d)]
    report.append(f"{path}: {len(deps)} runtime dependencies")
    if loose:
        report.append(
            f"  unpinned/lower-bound only ({len(loose)}): " + ", ".join(sorted(loose)[:15])
        )
    if not lock:
        report.append("  ! no lockfile found next to this manifest (builds are not reproducible)")


def check_node(path: Path, report: list[str]) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    deps = {**(data.get("dependencies") or {}), **(data.get("devDependencies") or {})}
    wildcard = [
        f"{k}@{v}"
        for k, v in deps.items()
        if v in ("*", "latest", "") or v.startswith(("http:", "git+http:"))
    ]
    report.append(f"{path}: {len(deps)} dependencies")
    if wildcard:
        report.append("  ! wildcard/insecure specifiers: " + ", ".join(sorted(wildcard)))
    lockfiles = ("package-lock.json", "pnpm-lock.yaml", "yarn.lock", "bun.lockb", "bun.lock")
    if not any((path.parent / f).exists() for f in lockfiles) and not any(
        (Path(os.getcwd()) / f).exists() for f in lockfiles
    ):
        report.append("  ! no lockfile found (builds are not reproducible)")
    if (data.get("scripts") or {}).get("postinstall") or (data.get("scripts") or {}).get(
        "preinstall"
    ):
        report.append("  note: install-time scripts present (preinstall/postinstall); review them")


def main() -> int:
    root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    report: list[str] = []
    for path in sorted(manifests(root)):
        rel = path.relative_to(root)
        try:
            if path.name in ("pyproject.toml", "requirements.txt"):
                check_python(path, report)
            elif path.name == "package.json":
                check_node(path, report)
            else:
                report.append(f"{rel}: present (inspect manually)")
        except (OSError, ValueError, tomllib.TOMLDecodeError) as exc:
            report.append(f"{rel}: could not parse ({exc})")
    if not report:
        print("No dependency manifests found.")
        return 0
    print("\n".join(str(line).replace(str(root) + os.sep, "") for line in report))
    print(
        "\nFor known-vulnerability data run the ecosystem auditor, e.g. `pip-audit` or `npm audit`."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
