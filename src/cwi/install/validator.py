"""Post-apply validation of the resulting workspace."""

from __future__ import annotations

import json
from pathlib import Path

from cwi import paths
from cwi.domain.enums import CapabilityType, ClaudeMdMode
from cwi.domain.errors import ValidationError
from cwi.domain.models import InstallationPlan
from cwi.install.json_merge import hook_identity, iter_hooks
from cwi.planning.safety import resolve_inside
from cwi.state.hashing import sha256_file


def _load_json(path: Path, label: str, problems: list[str]) -> dict | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        problems.append(f"{label} is not valid JSON: {exc.msg}")
        return None
    if not isinstance(data, dict):
        problems.append(f"{label} is not a JSON object")
        return None
    return data


def validate_installation(root: Path, plan: InstallationPlan) -> None:
    problems: list[str] = []
    state = plan.state

    for op in plan.operations:
        try:
            resolve_inside(root, op.target)
        except Exception as exc:  # noqa: BLE001 - report every escape
            problems.append(str(exc))

    for rel, record in state.managed_files.items():
        path = root / rel
        if not path.is_file():
            problems.append(f"managed file missing: {rel}")
        elif sha256_file(path) != record.sha256:
            problems.append(f"managed file hash mismatch: {rel}")

    for ref in state.selected_capabilities:
        kind, cid = ref.split(":", 1)
        if (
            kind == CapabilityType.SKILL.value
            and not (root / paths.rel(paths.SKILLS_DIR) / cid / "SKILL.md").is_file()
        ):
            problems.append(f"skill {cid}: SKILL.md missing")
        if kind == CapabilityType.AGENT.value and not any(
            (root / paths.rel(paths.AGENTS_DIR)).rglob(f"{cid}.md")
        ):
            problems.append(f"agent {cid}: definition missing")

    settings = _load_json(
        root / paths.rel(paths.SETTINGS_FILE), paths.rel(paths.SETTINGS_FILE), problems
    )
    present = {hook_identity(e, m, h) for e, m, h in iter_hooks(settings or {})}
    for ref, hooks in state.settings_hooks.items():
        for hook in hooks:
            if (hook.event, hook.matcher, hook.type, hook.command) not in present:
                problems.append(
                    f"{ref}: hook {hook.event}/{hook.matcher} not represented in settings.json"
                )

    mcp = _load_json(root / paths.rel(paths.MCP_FILE), paths.rel(paths.MCP_FILE), problems)
    servers = (mcp or {}).get("mcpServers") or {}
    for name, record in state.mcp_servers.items():
        if name not in servers:
            problems.append(f"{record.owner}: MCP server '{name}' missing from .mcp.json")

    if (
        plan.claude_md_mode in (ClaudeMdMode.CREATE, ClaudeMdMode.REPLACE, ClaudeMdMode.MERGE)
        and not (root / paths.rel(paths.CLAUDE_MD)).is_file()
    ):
        problems.append("CLAUDE.md missing")
    if (
        plan.agents_md_mode in (ClaudeMdMode.CREATE, ClaudeMdMode.REPLACE, ClaudeMdMode.MERGE)
        and not (root / paths.rel(paths.AGENTS_MD)).is_file()
    ):
        problems.append("AGENTS.md missing")

    state_path = root / paths.rel(paths.STATE_FILE)
    if not state_path.is_file():
        problems.append("CWI state file missing")
    else:
        _load_json(state_path, paths.rel(paths.STATE_FILE), problems)

    if problems:
        raise ValidationError("Workspace validation failed:\n  - " + "\n  - ".join(problems))


def validate_cleanup(root: Path, plan: InstallationPlan) -> None:
    problems = [
        f"not removed: {op.target}"
        for op in plan.operations
        if op.is_delete and not op.only_if_empty and (root / op.target).exists()
    ]
    if problems:
        raise ValidationError("Cleanup failed:\n  - " + "\n  - ".join(problems))
