#!/usr/bin/env python3
"""Report where this project stands in the CWI workflow, as JSON. Read-only.

Used by the kickoff skill to decide the next step:
  architecture -> specs -> implementation

Usage: python3 project-status.py [project-root]
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

TEMPLATE_MARKER = "cwi:architecture-template"
IGNORED_DIRS = {
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "env",
    "dist",
    "build",
    ".next",
    ".nuxt",
    "coverage",
    "__pycache__",
    "target",
    ".cwi",
    ".claude",
    "docs",
    ".idea",
    ".vscode",
    ".turbo",
    ".cache",
}
CWI_FILES = {"scripts/run-quality-checks.py"}
SOURCE_SUFFIXES = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".mjs",
    ".cjs",
    ".go",
    ".rs",
    ".java",
    ".kt",
    ".rb",
    ".php",
    ".cs",
    ".swift",
    ".vue",
    ".svelte",
    ".dart",
    ".ex",
    ".exs",
    ".scala",
    ".c",
    ".cpp",
    ".h",
}
REQUIREMENT_NAME = re.compile(r"(requirement|prd|brief|product|user[-_ ]?stor|functional)", re.I)
STATUSES = ("in progress", "ready", "draft", "done")


def read(path: Path, limit: int = 200_000) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")[:limit]
    except OSError:
        return ""


def architecture(root: Path) -> dict:
    pointer = None
    for name in ("AGENTS.md", "CLAUDE.md", ".claude/CLAUDE.md"):
        text = read(root / name)
        match = re.search(r"[Aa]rchitecture[^`\n]*`([^`]+)`", text)
        if match:
            pointer = match.group(1).strip()
            break
    candidates = [pointer] if pointer else []
    candidates += ["docs/architecture.md", "ARCHITECTURE.md", "docs/ARCHITECTURE.md"]
    for rel in candidates:
        path = root / rel
        if path.is_file():
            state = "template" if TEMPLATE_MARKER in read(path, 2000) else "defined"
            return {"state": state, "path": rel}
    return {"state": "missing", "path": pointer or "docs/architecture.md"}


def has_code(root: Path, limit: int = 20_000) -> bool:
    seen = 0
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = Path(dirpath).relative_to(root)
        dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS and not d.startswith(".")]
        for name in filenames:
            seen += 1
            rel = (rel_dir / name).as_posix()
            if Path(name).suffix in SOURCE_SUFFIXES and rel not in CWI_FILES:
                return True
            if seen > limit:
                return False
    return False


def requirements(root: Path) -> list[str]:
    found: list[str] = []
    for rel in ("docs/requirements", "requirements", "docs/product", "docs/prd"):
        if (root / rel).is_dir():
            found.append(rel + "/")
    docs = root / "docs"
    if docs.is_dir():
        for path in sorted(docs.rglob("*")):
            rel = path.relative_to(root).as_posix()
            if any(rel.startswith(f) for f in found) or rel.startswith(
                ("docs/specs/", "docs/decisions/")
            ):
                continue
            if (
                path.is_file()
                and path.suffix.lower() in {".md", ".txt", ".pdf", ".docx"}
                and REQUIREMENT_NAME.search(path.name)
            ):
                found.append(rel)
    for path in sorted(root.glob("*")):
        if (
            path.is_file()
            and path.suffix.lower() in {".md", ".txt", ".pdf", ".docx"}
            and REQUIREMENT_NAME.search(path.stem)
            and path.name != "requirements.txt"
        ):
            found.append(path.name)
    return found


def spec_status(text: str) -> str:
    match = re.search(r"(?im)^\s*\**status\**\s*:\s*(.+)$", text)
    if not match:
        return "draft"
    value = match.group(1).strip().lower()
    if "|" in value:  # untouched template line
        return "draft"
    for status in STATUSES:
        if status in value:
            return status
    return "draft"


def open_questions(text: str) -> int:
    match = re.search(r"(?ims)^##\s*open questions\s*$(.*?)(?=^##\s|\Z)", text)
    if not match:
        return 0
    count = 0
    for line in match.group(1).splitlines():
        item = (
            re.sub(r"^\s*(?:[-*]|\d+[.)])\s*", "", line).strip()
            if re.match(r"^\s*(?:[-*]|\d+[.)])\s", line)
            else ""
        )
        item = re.sub(r"<!--.*?-->", "", item).strip()
        if item and item.lower() not in {"none", "n/a", "-"}:
            count += 1
    return count


def specs(root: Path) -> list[dict]:
    result = []
    folder = root / "docs" / "specs"
    if not folder.is_dir():
        return result
    for path in sorted(folder.glob("*.md")):
        if path.name.lower() in {"readme.md", "_template.md"} or path.name.startswith("_"):
            continue
        text = read(path)
        result.append(
            {
                "slug": path.stem,
                "path": path.relative_to(root).as_posix(),
                "status": spec_status(text),
                "open_questions": open_questions(text),
            }
        )
    return result


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def backlog(root: Path) -> list[str]:
    text = read(root / "docs" / "specs" / "README.md")
    match = re.search(r"(?ims)^##\s*backlog\s*$(.*?)(?=^##\s|\Z)", text)
    if not match:
        return []
    items = []
    for line in match.group(1).splitlines():
        if not re.match(r"^\s*(?:[-*]|\d+[.)])\s", line):
            continue
        tick = re.search(r"`([^`]+)`", line)
        label = (
            tick.group(1)
            if tick
            else re.sub(r"^\s*(?:[-*]|\d+[.)])\s*", "", line).split(" — ")[0].split(" - ")[0]
        )
        slug = slugify(label.replace(".md", ""))
        if slug and slug not in items:
            items.append(slug)
    return items


def diagrams(root: Path) -> list[str]:
    found: list[str] = []
    for base in ("docs/diagrams", ".archify"):
        folder = root / base
        if folder.is_dir():
            found += sorted(p.relative_to(root).as_posix() for p in folder.rglob("*.html"))
    return found


def decide(state: dict) -> str:
    arch = state["architecture"]["state"]
    if arch in ("missing", "template"):
        return "discovery:code" if state["code"] else "discovery:new"
    specs_ = state["specs"]
    order = {slug: i for i, slug in enumerate(state["backlog"])}

    def ranked(items):
        return sorted(items, key=lambda s: (order.get(s["slug"], len(order)), s["slug"]))

    in_progress = [s for s in specs_ if s["status"] == "in progress"]
    if in_progress:
        return "workflow:" + ranked(in_progress)[0]["slug"]
    ready = [s for s in specs_ if s["status"] == "ready" and s["open_questions"] == 0]
    if ready:
        return "workflow:" + ranked(ready)[0]["slug"]
    unfinished = [s for s in specs_ if s["status"] != "done"]
    if unfinished:
        return "spec:" + ranked(unfinished)[0]["slug"]
    written = {s["slug"] for s in specs_}
    for slug in state["backlog"]:
        if slug not in written:
            return "spec:" + slug
    if not specs_:
        return "spec:new"
    return "done"


def main() -> int:
    root = Path(
        sys.argv[1] if len(sys.argv) > 1 else os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    ).resolve()
    state = {
        "root": str(root),
        "architecture": architecture(root),
        "code": has_code(root),
        "requirements": requirements(root),
        "specs": specs(root),
        "backlog": backlog(root),
        "diagrams": diagrams(root),
    }
    state["next"] = decide(state)
    print(json.dumps(state, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
