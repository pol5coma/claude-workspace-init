"""Shared test helpers for fixture repositories and capability catalogs."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "repos"
REAL_CATALOG = PROJECT_ROOT / "catalog"


def copy_fixture(name: str, dest: Path) -> Path:
    target = dest / name
    shutil.copytree(FIXTURES / name, target)
    return target


def copy_catalog(dest: Path) -> Path:
    """Copy only the capability folders of the bundled catalog (not notes kept next to them)."""
    from spado.domain.enums import CapabilityType

    target = dest / "catalog"
    target.mkdir(parents=True)
    for cap_type in CapabilityType:
        source = REAL_CATALOG / cap_type.plural
        if source.is_dir():
            shutil.copytree(
                source,
                target / cap_type.plural,
                ignore=shutil.ignore_patterns("__pycache__", ".DS_Store"),
            )
    return target


def tree(root: Path) -> dict[str, str]:
    """Hash fixture files to verify read-only and idempotent commands."""
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in root.rglob("*")
        if path.is_file() and ".git" not in path.relative_to(root).parts
    }


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
    (directory / "spado.json").write_text(json.dumps(manifest(cap_type, cid, **manifest_overrides)))
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
