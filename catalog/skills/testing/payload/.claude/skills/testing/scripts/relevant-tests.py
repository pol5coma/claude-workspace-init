#!/usr/bin/env python3
"""List test files relevant to changed source files. Read-only: never runs tests.

Usage:
    relevant-tests.py                 # changed files from `git diff` (staged + unstaged + untracked)
    relevant-tests.py path [path...]  # explicit files
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

IGNORED = {
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "dist",
    "build",
    ".next",
    "coverage",
    "__pycache__",
    "target",
}
TEST_PATTERNS = (
    re.compile(r"^test_.+\.py$"),
    re.compile(r"^.+_test\.py$"),
    re.compile(r"^.+\.(test|spec)\.(ts|tsx|js|jsx|mjs|cjs)$"),
    re.compile(r"^.+_test\.go$"),
)


def changed_files(root: Path) -> list[str]:
    files: set[str] = set()
    for args in (
        ["diff", "--name-only"],
        ["diff", "--name-only", "--cached"],
        ["ls-files", "--others", "--exclude-standard"],
    ):
        try:
            out = subprocess.run(
                ["git", *args], cwd=root, capture_output=True, text=True, timeout=10
            ).stdout
        except (OSError, subprocess.SubprocessError):
            continue
        files.update(line.strip() for line in out.splitlines() if line.strip())
    return sorted(files)


def all_tests(root: Path) -> list[Path]:
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORED and not d.startswith(".")]
        for name in filenames:
            if any(p.match(name) for p in TEST_PATTERNS):
                found.append(Path(dirpath, name).relative_to(root))
    return found


def is_test(path: str) -> bool:
    return any(p.match(Path(path).name) for p in TEST_PATTERNS)


def stem_of(path: str) -> str:
    name = Path(path).name
    for suffix in (".test", ".spec"):
        name = name.replace(suffix, "")
    stem = Path(name).stem
    return re.sub(r"^test_|_test$", "", stem)


def main(argv: list[str]) -> int:
    root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    targets = argv or changed_files(root)
    if not targets:
        print("No changed files found. Pass file paths explicitly.")
        return 0
    tests = all_tests(root)
    by_stem: dict[str, list[Path]] = {}
    for test in tests:
        by_stem.setdefault(stem_of(str(test)), []).append(test)

    relevant: set[Path] = set()
    unmatched: list[str] = []
    for target in targets:
        if is_test(target):
            relevant.add(Path(target))
            continue
        matches = by_stem.get(stem_of(target), [])
        if matches:
            relevant.update(matches)
        else:
            unmatched.append(target)

    if relevant:
        print("Relevant tests:")
        for test in sorted(relevant):
            print(f"  {test}")
        py = sorted(str(t) for t in relevant if t.suffix == ".py")
        js = sorted(
            str(t) for t in relevant if t.suffix in {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"}
        )
        go = sorted({str(t.parent) for t in relevant if t.suffix == ".go"})
        print(
            "\nSuggested commands (use the project's runner prefix from CLAUDE.md, e.g. `uv run`):"
        )
        if py:
            print("  pytest -x -q " + " ".join(py))
        if js:
            print("  <vitest|jest> run " + " ".join(js))
        if go:
            print("  go test " + " ".join(f"./{d}/..." for d in go))
    if unmatched:
        print("\nNo test file matched by name for:")
        for item in unmatched:
            print(f"  {item}")
        print("Search for usages of the changed symbols, or run the module's suite.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
