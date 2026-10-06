#!/usr/bin/env python3
"""CWI Post-edit Validation: a Claude Code PostToolUse hook.

After Claude edits a file, format and lint *that file only* with tools the project is already
configured for. Problems are returned to Claude (stderr + exit 2). No configured tool means
skip silently: CWI never installs or guesses tools, and never runs the test suite here.

Exit codes: 0 clean or skipped, 2 problems found (shown to Claude), 1 internal error.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

TOOL_TIMEOUT = 60
JS_SUFFIXES = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".vue", ".svelte"}
PRETTIER_CONFIGS = (
    ".prettierrc",
    ".prettierrc.json",
    ".prettierrc.yaml",
    ".prettierrc.yml",
    ".prettierrc.js",
    ".prettierrc.cjs",
    ".prettierrc.mjs",
    ".prettierrc.toml",
    "prettier.config.js",
    "prettier.config.cjs",
    "prettier.config.mjs",
)
ESLINT_CONFIGS = (
    "eslint.config.js",
    "eslint.config.mjs",
    "eslint.config.cjs",
    "eslint.config.ts",
    ".eslintrc",
    ".eslintrc.js",
    ".eslintrc.cjs",
    ".eslintrc.json",
    ".eslintrc.yml",
    ".eslintrc.yaml",
)


def find_up(start: Path, root: Path, names: tuple[str, ...]) -> Path | None:
    """Nearest directory between start and root containing one of `names`."""
    current = start if start.is_dir() else start.parent
    while True:
        for name in names:
            if (current / name).exists():
                return current
        if current == root or root not in current.parents:
            return None
        current = current.parent


def ruff_configured(directory: Path) -> bool:
    if (directory / "ruff.toml").is_file() or (directory / ".ruff.toml").is_file():
        return True
    pyproject = directory / "pyproject.toml"
    if pyproject.is_file():
        try:
            return "ruff" in (
                tomllib.loads(pyproject.read_text(encoding="utf-8")).get("tool") or {}
            )
        except (OSError, tomllib.TOMLDecodeError):
            return False
    return False


def python_tool(base: Path, name: str) -> list[str] | None:
    for candidate in (base / ".venv" / "bin" / name, base / "venv" / "bin" / name):
        if candidate.is_file():
            return [str(candidate)]
    if (base / "uv.lock").is_file() and shutil.which("uv"):
        return ["uv", "run", "--quiet", name]
    found = shutil.which(name)
    return [found] if found else None


def node_bin(base: Path, name: str) -> list[str] | None:
    candidate = base / "node_modules" / ".bin" / name
    return [str(candidate)] if candidate.exists() else None


def package_json(base: Path) -> dict:
    try:
        return json.loads((base / "package.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def run(argv: list[str], cwd: Path) -> tuple[int, str]:
    try:
        result = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=TOOL_TIMEOUT)
    except subprocess.TimeoutExpired:
        return 0, ""  # never block Claude on a slow tool
    except OSError:
        return 0, ""
    return result.returncode, (result.stdout + result.stderr).strip()


def validate(path: Path, root: Path) -> list[str]:
    problems: list[str] = []
    suffix = path.suffix

    if suffix in (".py", ".pyi"):
        base = find_up(path, root, ("pyproject.toml", "ruff.toml", ".ruff.toml"))
        if base and ruff_configured(base):
            ruff = python_tool(base, "ruff")
            if ruff:
                code, out = run([*ruff, "check", "--fix", str(path)], base)
                run([*ruff, "format", str(path)], base)
                if code != 0 and out:
                    problems.append(f"ruff check {path.name}:\n{out}")

    elif suffix in JS_SUFFIXES:
        base = find_up(path, root, ("package.json",))
        if base:
            pkg = package_json(base)
            has_prettier_config = bool(find_up(path, root, PRETTIER_CONFIGS)) or "prettier" in pkg
            prettier = node_bin(base, "prettier") or node_bin(root, "prettier")
            if prettier and has_prettier_config:
                run([*prettier, "--write", "--log-level", "warn", str(path)], base)
            eslint = node_bin(base, "eslint") or node_bin(root, "eslint")
            if eslint and (find_up(path, root, ESLINT_CONFIGS) or "eslintConfig" in pkg):
                code, out = run([*eslint, "--fix", str(path)], base)
                if code != 0 and out:
                    problems.append(f"eslint {path.name}:\n{out}")

    elif suffix == ".go":
        base = find_up(path, root, ("go.mod",))
        if base and shutil.which("gofmt"):
            run(["gofmt", "-w", str(path)], base)
            if shutil.which("go"):
                rel = path.parent.relative_to(base).as_posix()
                code, out = run(["go", "vet", "." if rel == "." else f"./{rel}"], base)
                if code != 0 and out:
                    problems.append(f"go vet:\n{out}")

    elif suffix == ".rs":
        base = find_up(path, root, ("Cargo.toml",))
        if base and shutil.which("rustfmt"):
            code, out = run(["rustfmt", "--edition", "2021", str(path)], base)
            if code != 0 and out:
                problems.append(f"rustfmt {path.name}:\n{out}")
    return problems


def main() -> int:
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        return 0
    tool_input = payload.get("tool_input") or {}
    file_path = tool_input.get("file_path")
    if not file_path:
        return 0
    root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd") or os.getcwd()).resolve()
    path = Path(file_path)
    if not path.is_absolute():
        path = Path(payload.get("cwd") or root) / path
    path = path.resolve()
    if not path.is_file() or (path != root and root not in path.parents):
        return 0
    if any(
        part in ("node_modules", ".venv", "venv", ".git", "dist", "build")
        for part in path.relative_to(root).parts
    ):
        return 0
    problems = validate(path, root)
    if problems:
        text = "\n\n".join(p if len(p) < 4000 else p[:4000] + "\n…(truncated)" for p in problems)
        print(
            f"Post-edit validation found problems in {path.relative_to(root)}:\n\n{text}\n\nFix them before continuing.",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001 - never crash Claude's tool loop
        print(f"post-edit-validation: internal error ({exc})", file=sys.stderr)
        sys.exit(1)
