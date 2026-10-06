#!/usr/bin/env python3
"""Run the project's configured quality checks, and only those.

A tool runs only when the project shows evidence it is configured (config file, pyproject
section or package.json dependency) AND its executable is available locally. Nothing is
installed. Missing tools are reported as skipped, never as failures.

Usage:
    python3 scripts/run-quality-checks.py            # whole project
    python3 scripts/run-quality-checks.py --changed  # lint/format only changed files (tests still run)
    python3 scripts/run-quality-checks.py --no-tests # skip test runners
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

PY_SUFFIXES = {".py", ".pyi"}
JS_SUFFIXES = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".vue", ".svelte"}
TIMEOUT = 900


def root_dir() -> Path:
    return Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()


def load_pyproject(root: Path) -> dict:
    path = root / "pyproject.toml"
    if not path.is_file():
        return {}
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return {}


def load_package(root: Path) -> dict:
    path = root / "package.json"
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def python_tool(root: Path, name: str) -> list[str] | None:
    for candidate in (root / ".venv" / "bin" / name, root / "venv" / "bin" / name):
        if candidate.is_file():
            return [str(candidate)]
    if (root / "uv.lock").is_file() and shutil.which("uv"):
        return ["uv", "run", "--quiet", name]
    found = shutil.which(name)
    return [found] if found else None


def node_tool(root: Path, name: str) -> list[str] | None:
    candidate = root / "node_modules" / ".bin" / name
    return [str(candidate)] if candidate.exists() else None


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
        files.update(
            f.strip() for f in out.splitlines() if f.strip() and (root / f.strip()).is_file()
        )
    return sorted(files)


def plan_checks(
    root: Path, changed: list[str] | None, run_tests: bool
) -> list[tuple[str, list[str] | None, str]]:
    """Return (name, argv or None when unavailable, evidence)."""
    pyproject = load_pyproject(root)
    tool = pyproject.get("tool", {}) or {}
    package = load_package(root)
    deps = {**(package.get("dependencies") or {}), **(package.get("devDependencies") or {})}
    scripts = package.get("scripts") or {}
    checks: list[tuple[str, list[str] | None, str]] = []

    py_files = None if changed is None else [f for f in changed if Path(f).suffix in PY_SUFFIXES]
    js_files = None if changed is None else [f for f in changed if Path(f).suffix in JS_SUFFIXES]

    python_scope = py_files is None or bool(py_files)
    ruff_configured = (
        "ruff" in tool or (root / "ruff.toml").is_file() or (root / ".ruff.toml").is_file()
    )
    if ruff_configured and python_scope:
        targets = py_files or ["."]
        ruff = python_tool(root, "ruff")
        checks.append(
            (
                "ruff format --check",
                ruff and [*ruff, "format", "--check", *targets],
                "ruff configured",
            )
        )
        checks.append(("ruff check", ruff and [*ruff, "check", *targets], "ruff configured"))
    if ("mypy" in tool or (root / "mypy.ini").is_file()) and python_scope:
        mypy = python_tool(root, "mypy")
        checks.append(("mypy", mypy and [*mypy, *(py_files or ["."])], "mypy configured"))
    pytest_configured = (
        "pytest" in tool or (root / "pytest.ini").is_file() or (root / "conftest.py").is_file()
    )
    if run_tests and pytest_configured:
        pytest = python_tool(root, "pytest")
        checks.append(("pytest", pytest and [*pytest, "-q"], "pytest configured"))

    eslint_config = any(
        (root / n).exists()
        for n in (
            "eslint.config.js",
            "eslint.config.mjs",
            "eslint.config.cjs",
            "eslint.config.ts",
            ".eslintrc",
            ".eslintrc.js",
            ".eslintrc.cjs",
            ".eslintrc.json",
            ".eslintrc.yml",
        )
    )
    if "eslint" in deps and eslint_config and (js_files is None or js_files):
        eslint = node_tool(root, "eslint")
        checks.append(("eslint", eslint and [*eslint, *(js_files or ["."])], "eslint configured"))
    prettier_config = (
        any(
            (root / n).exists()
            for n in (
                ".prettierrc",
                ".prettierrc.json",
                ".prettierrc.js",
                ".prettierrc.cjs",
                ".prettierrc.yaml",
                ".prettierrc.yml",
                "prettier.config.js",
                "prettier.config.mjs",
                "prettier.config.cjs",
            )
        )
        or "prettier" in package
    )
    if "prettier" in deps and prettier_config and (js_files is None or js_files):
        prettier = node_tool(root, "prettier")
        checks.append(
            (
                "prettier --check",
                prettier and [*prettier, "--check", *(js_files or ["."])],
                "prettier configured",
            )
        )
    if (
        "typescript" in deps
        and (root / "tsconfig.json").is_file()
        and (js_files is None or js_files)
    ):
        tsc = node_tool(root, "tsc")
        checks.append(("tsc --noEmit", tsc and [*tsc, "--noEmit"], "tsconfig.json present"))
    if run_tests and "test" in scripts and ("vitest" in deps or "jest" in deps):
        runner = node_tool(root, "vitest") if "vitest" in deps else node_tool(root, "jest")
        argv = None
        if runner:
            argv = [*runner, "run"] if "vitest" in deps else [*runner, "--ci"]
        checks.append(("vitest" if "vitest" in deps else "jest", argv, "test runner configured"))
    return checks


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--changed", action="store_true", help="limit lint/format/type checks to changed files"
    )
    parser.add_argument("--no-tests", action="store_true", help="skip test runners")
    args = parser.parse_args()

    root = root_dir()
    changed = changed_files(root) if args.changed else None
    checks = plan_checks(root, changed, run_tests=not args.no_tests)
    if not checks:
        print("No configured quality tools found. Nothing to run.")
        return 0

    failed: list[str] = []
    for name, argv, evidence in checks:
        if argv is None:
            print(f"SKIP  {name}  ({evidence}, but the executable is not installed locally)")
            continue
        print(f"RUN   {name}")
        try:
            result = subprocess.run(argv, cwd=root, capture_output=True, text=True, timeout=TIMEOUT)
        except subprocess.TimeoutExpired:
            print(f"FAIL  {name}  (timed out after {TIMEOUT}s)")
            failed.append(name)
            continue
        if result.returncode == 0:
            print(f"PASS  {name}")
        else:
            failed.append(name)
            print(f"FAIL  {name}  (exit {result.returncode})")
            output = (result.stdout + result.stderr).strip()
            lines = output.splitlines()
            print("\n".join(f"      {line}" for line in lines[-60:]))
    print()
    print(
        f"{len(failed)} check(s) failed: {', '.join(failed)}"
        if failed
        else "All configured checks passed."
    )
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
