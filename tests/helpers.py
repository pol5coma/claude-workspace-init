"""Shared test helpers: fixture repos, scripted runs, catalog builders, failing filesystems."""

from __future__ import annotations

import io
import json
import shutil
from pathlib import Path
from typing import Any

from rich.console import Console

from cwi.commands.init import InitOptions, InitOutcome, run_init
from cwi.install.filesystem import FileSystem
from cwi.state.hashing import hash_tree
from cwi.ui.prompts import ScriptedPrompter

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "repos"
REAL_CATALOG = PROJECT_ROOT / "catalog"
FIXED_NOW = "2026-10-06T12:00:00Z"


def copy_fixture(name: str, dest: Path) -> Path:
    target = dest / name
    shutil.copytree(FIXTURES / name, target)
    return target


def copy_catalog(dest: Path) -> Path:
    target = dest / "catalog"
    shutil.copytree(REAL_CATALOG, target, ignore=shutil.ignore_patterns("__pycache__", ".DS_Store"))
    return target


def tree(root: Path) -> dict[str, str]:
    return hash_tree(root, ignore={".git"})


def run(
    root: Path,
    answers: dict[str, Any] | None = None,
    *,
    catalog: Path | None = None,
    dry_run: bool = False,
    filesystem_factory=None,
) -> tuple[InitOutcome, ScriptedPrompter, str]:
    prompter = ScriptedPrompter(answers or {})
    buffer = io.StringIO()
    console = Console(file=buffer, width=120, force_terminal=False, color_system=None)
    outcome = run_init(
        InitOptions(
            root=root,
            catalog=catalog,
            dry_run=dry_run,
            yes=True,
            prompter=prompter,
            console=console,
            filesystem_factory=filesystem_factory,
            now=FIXED_NOW,
        )
    )
    return outcome, prompter, buffer.getvalue()


class FailingFileSystem(FileSystem):
    """Raises after `fail_after` successful mutations (or on a matching target)."""

    def __init__(
        self, root: Path, fail_after: int | None = None, fail_on: str | None = None
    ) -> None:
        super().__init__(root)
        self.fail_after = fail_after
        self.fail_on = fail_on
        self.mutations = 0

    def before_mutation(self, action: str, rel: str) -> None:
        if self.fail_on is not None and rel == self.fail_on:
            raise OSError(f"injected failure on {rel}")
        if self.fail_after is not None and self.mutations >= self.fail_after:
            raise OSError(f"injected failure after {self.mutations} mutations ({action} {rel})")
        self.mutations += 1


def failing(fail_after: int | None = None, fail_on: str | None = None):
    return lambda root: FailingFileSystem(root, fail_after=fail_after, fail_on=fail_on)


# ---------------------------------------------------------------------------------------------
# Catalog builders
# ---------------------------------------------------------------------------------------------

_PLURAL = {"skill": "skills", "agent": "agents", "script": "scripts", "hook": "hooks", "mcp": "mcp"}


def manifest(cap_type: str, cid: str, **overrides: Any) -> dict[str, Any]:
    data = {
        "schema_version": 1,
        "id": cid,
        "type": cap_type,
        "name": cid.replace("-", " ").title(),
        "description": f"Test {cap_type} {cid}",
    }
    data.update(overrides)
    return data


def add_capability(
    catalog: Path,
    cap_type: str,
    cid: str,
    files: dict[str, str] | None = None,
    *,
    settings_fragment: dict | None = None,
    mcp_fragment: dict | None = None,
    **manifest_overrides: Any,
) -> Path:
    directory = catalog / _PLURAL[cap_type] / cid
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "cwi.json").write_text(json.dumps(manifest(cap_type, cid, **manifest_overrides)))
    for rel, content in (files or {}).items():
        path = directory / "payload" / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    if settings_fragment is not None:
        (directory / "settings.fragment.json").write_text(json.dumps(settings_fragment))
    if mcp_fragment is not None:
        (directory / "mcp.fragment.json").write_text(json.dumps(mcp_fragment))
    return directory


def skill_md(cid: str, name: str | None = None) -> str:
    return f"---\nname: {name or cid}\ndescription: Test skill {cid}\n---\n\n# {cid}\n"


def agent_md(cid: str) -> str:
    return f"---\nname: {cid}\ndescription: Test agent {cid}\n---\n\nDo {cid} things.\n"


def minimal_catalog(root: Path) -> Path:
    catalog = root / "catalog"
    add_capability(catalog, "skill", "alpha", {".claude/skills/alpha/SKILL.md": skill_md("alpha")})
    add_capability(
        catalog,
        "agent",
        "beta",
        {".claude/agents/beta.md": agent_md("beta")},
        dependencies=["script:gamma"],
    )
    add_capability(catalog, "script", "gamma", {"scripts/gamma.sh": "#!/bin/sh\necho gamma\n"})
    add_capability(
        catalog,
        "hook",
        "delta",
        {".claude/hooks/delta.py": "print('delta')\n"},
        settings_fragment={
            "hooks": {
                "PreToolUse": [
                    {
                        "matcher": "Bash",
                        "hooks": [{"type": "command", "command": "python3 .claude/hooks/delta.py"}],
                    }
                ]
            }
        },
    )
    add_capability(
        catalog,
        "mcp",
        "epsilon",
        mcp_fragment={
            "mcpServers": {"epsilon": {"type": "http", "url": "https://example.com/mcp"}}
        },
    )
    return catalog
