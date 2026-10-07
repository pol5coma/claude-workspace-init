"""Catalog validation. Bad template data must never reach the install step."""

from __future__ import annotations

import re
from pathlib import PurePosixPath, PureWindowsPath
from typing import Any

from cwi import paths
from cwi.catalog.frontmatter import parse_frontmatter
from cwi.domain.enums import CapabilityType
from cwi.domain.errors import CatalogError
from cwi.domain.models import Capability, Catalog

# Files that CWI generates or merges itself; a payload must never ship them directly.
RESERVED_TARGETS = {
    paths.rel(paths.CLAUDE_MD),
    paths.rel(paths.CLAUDE_LOCAL_MD),
    paths.rel(paths.AGENTS_MD),
    paths.rel(paths.SETTINGS_FILE),
    paths.rel(paths.SETTINGS_LOCAL_FILE),
    paths.rel(paths.MCP_FILE),
    paths.rel(paths.STATE_FILE),
}

SECRET_KEY_PATTERN = re.compile(
    r"(token|secret|password|passwd|api[_-]?key|authorization|auth)", re.I
)
REF_PATTERN = re.compile(r"^(skill|agent|script|hook|mcp):[a-z0-9][a-z0-9-]*$")


def is_safe_relative(path: str) -> bool:
    """True when `path` is a relative POSIX path that cannot escape its root."""
    if not path or "\\" in path or "\x00" in path:
        return False
    if PureWindowsPath(path).drive or path.startswith("/"):
        return False
    pure = PurePosixPath(path)
    if pure.is_absolute():
        return False
    return all(part not in ("..", "") for part in pure.parts)


def _allowed_prefixes(cap: Capability) -> tuple[str, ...]:
    cid = cap.id
    if cap.type == CapabilityType.SKILL:
        return (f"{paths.SKILLS_DIR}/{cid}/",)
    if cap.type == CapabilityType.AGENT:
        return (
            paths.agent_file(cid, cap.group),
            f"{paths.CLAUDE_SCRIPTS_DIR}/{cid}/",
        )
    if cap.type == CapabilityType.SCRIPT:
        return (f"{paths.SCRIPTS_DIR}/",)
    if cap.type == CapabilityType.HOOK:
        return (f"{paths.HOOKS_DIR}/",)
    return ()  # MCP: fragment only


def _check_payload(cap: Capability, errors: list[str]) -> None:
    where = f"{cap.ref} ({cap.source_dir})"
    for file in cap.payload_files:
        if not is_safe_relative(file):
            errors.append(f"{where}: unsafe payload path '{file}' (absolute or traversal)")
            continue
        if file in RESERVED_TARGETS:
            errors.append(f"{where}: payload may not ship '{file}'; CWI generates/merges it")
            continue
        prefixes = _allowed_prefixes(cap)
        if not any(file == p or file.startswith(p) for p in prefixes):
            allowed = ", ".join(prefixes) or "(no payload allowed)"
            errors.append(f"{where}: payload file '{file}' is outside allowed targets: {allowed}")

    if cap.type == CapabilityType.SKILL:
        skill_md = f"{paths.SKILLS_DIR}/{cap.id}/SKILL.md"
        if skill_md not in cap.payload_files:
            errors.append(f"{where}: missing payload {skill_md}")
        else:
            _check_frontmatter(cap, skill_md, errors, expect_name=cap.id)
    elif cap.type == CapabilityType.AGENT:
        agent_md = paths.agent_file(cap.id, cap.group)
        if agent_md not in cap.payload_files:
            errors.append(f"{where}: missing payload {agent_md}")
        else:
            _check_frontmatter(cap, agent_md, errors, expect_name=cap.id)
    elif cap.type == CapabilityType.SCRIPT:
        if not cap.payload_files:
            errors.append(f"{where}: script capability has no payload files")
    elif cap.type == CapabilityType.HOOK:
        _check_settings_fragment(cap, errors)
    elif cap.type == CapabilityType.MCP:
        _check_mcp_fragment(cap, errors)

    if cap.type != CapabilityType.HOOK and cap.settings_fragment is not None:
        errors.append(f"{where}: only hook capabilities may define settings.fragment.json")
    if cap.type != CapabilityType.MCP and cap.mcp_fragment is not None:
        errors.append(f"{where}: only mcp capabilities may define mcp.fragment.json")


def _check_frontmatter(cap: Capability, rel_path: str, errors: list[str], expect_name: str) -> None:
    path = cap.payload_dir / rel_path
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        errors.append(f"{cap.ref}: cannot read {rel_path}: {exc}")
        return
    front = parse_frontmatter(text)
    if front is None:
        errors.append(f"{cap.ref}: {rel_path} has no YAML frontmatter")
        return
    for key in ("name", "description"):
        if not front.get(key):
            errors.append(f"{cap.ref}: {rel_path} frontmatter is missing '{key}'")
    name = front.get("name")
    if name and name != expect_name:
        errors.append(
            f"{cap.ref}: {rel_path} frontmatter name '{name}' must equal id '{expect_name}'"
        )


def _check_settings_fragment(cap: Capability, errors: list[str]) -> None:
    frag = cap.settings_fragment
    where = cap.ref
    if not isinstance(frag, dict) or not isinstance(frag.get("hooks"), dict) or not frag["hooks"]:
        errors.append(f"{where}: settings.fragment.json must contain a non-empty 'hooks' object")
        return
    extra = set(frag) - {"hooks"}
    if extra:
        errors.append(
            f"{where}: settings.fragment.json may only define 'hooks' (found {sorted(extra)})"
        )
    for event, groups in frag["hooks"].items():
        if not isinstance(groups, list) or not groups:
            errors.append(f"{where}: hooks.{event} must be a non-empty list")
            continue
        for group in groups:
            if not isinstance(group, dict) or not isinstance(group.get("hooks"), list):
                errors.append(f"{where}: hooks.{event} entries need a 'hooks' list")
                continue
            if "matcher" in group and not isinstance(group["matcher"], str):
                errors.append(f"{where}: hooks.{event} matcher must be a string")
            for hook in group["hooks"]:
                if (
                    not isinstance(hook, dict)
                    or hook.get("type") != "command"
                    or not hook.get("command")
                ):
                    errors.append(
                        f"{where}: hooks.{event} entries must be {{type: command, command: ...}}"
                    )


def _check_mcp_fragment(cap: Capability, errors: list[str]) -> None:
    frag = cap.mcp_fragment
    where = cap.ref
    if (
        not isinstance(frag, dict)
        or not isinstance(frag.get("mcpServers"), dict)
        or not frag["mcpServers"]
    ):
        errors.append(f"{where}: mcp.fragment.json must contain a non-empty 'mcpServers' object")
        return
    for name, server in frag["mcpServers"].items():
        if not isinstance(server, dict):
            errors.append(f"{where}: mcpServers.{name} must be an object")
            continue
        for section in ("env", "headers"):
            values = server.get(section) or {}
            if not isinstance(values, dict):
                errors.append(f"{where}: mcpServers.{name}.{section} must be an object")
                continue
            for key, value in values.items():
                if _looks_like_literal_secret(key, value):
                    errors.append(
                        f"{where}: mcpServers.{name}.{section}.{key} looks like a literal secret. "
                        "Use an environment reference such as ${VAR}."
                    )


def _looks_like_literal_secret(key: str, value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    if "${" in value:
        return False
    return bool(SECRET_KEY_PATTERN.search(key))


def _check_refs_and_cycles(catalog: Catalog, errors: list[str]) -> None:
    refs = set(catalog.refs)
    graph: dict[str, list[str]] = {}
    for cap in catalog.capabilities:
        for kind, items in (
            ("dependency", cap.manifest.dependencies),
            ("conflict", cap.manifest.conflicts),
        ):
            for ref in items:
                if not REF_PATTERN.match(ref):
                    errors.append(f"{cap.ref}: invalid {kind} reference '{ref}' (expected type:id)")
                elif ref not in refs:
                    errors.append(f"{cap.ref}: unknown {kind} '{ref}'")
                elif ref == cap.ref:
                    errors.append(f"{cap.ref}: cannot reference itself as a {kind}")
        graph[cap.ref] = [d for d in cap.manifest.dependencies if d in refs]
        both = set(cap.manifest.dependencies) & set(cap.manifest.conflicts)
        if both:
            errors.append(f"{cap.ref}: {sorted(both)} listed as both dependency and conflict")

    WHITE, GREY, BLACK = 0, 1, 2
    color = dict.fromkeys(graph, WHITE)

    def visit(node: str, stack: list[str]) -> None:
        color[node] = GREY
        for dep in graph[node]:
            if color[dep] == GREY:
                cycle = [*stack[stack.index(dep) :], dep] if dep in stack else [node, dep]
                errors.append("Circular dependency: " + " -> ".join(cycle))
            elif color[dep] == WHITE:
                visit(dep, [*stack, dep])
        color[node] = BLACK

    for node in sorted(graph):
        if color[node] == WHITE:
            visit(node, [node])


def _check_target_collisions(catalog: Catalog, errors: list[str]) -> None:
    owners: dict[str, str] = {}
    for cap in catalog.capabilities:
        for file in cap.payload_files:
            if file in owners and owners[file] != cap.ref:
                errors.append(
                    f"Conflicting target file '{file}' shipped by {owners[file]} and {cap.ref}"
                )
            owners.setdefault(file, cap.ref)
    servers: dict[str, str] = {}
    for cap in catalog.capabilities:
        if cap.mcp_fragment and isinstance(cap.mcp_fragment.get("mcpServers"), dict):
            for name in cap.mcp_fragment["mcpServers"]:
                if name in servers:
                    errors.append(
                        f"MCP server '{name}' defined by both {servers[name]} and {cap.ref}"
                    )
                servers.setdefault(name, cap.ref)


def _check_groups(catalog: Catalog, errors: list[str]) -> None:
    for group in catalog.groups:
        members = {
            c.id for c in catalog.capabilities if c.type == group.type and c.group == group.id
        }
        for project_type, ids in group.defaults.items():
            for cid in ids:
                if cid not in members:
                    errors.append(
                        f"group {group.id}: defaults.{project_type.value} lists '{cid}', which is not a member of the group"
                    )


def validate_catalog(catalog: Catalog) -> None:
    """Raise CatalogError listing every problem found in the catalog."""
    errors: list[str] = []
    seen: dict[str, str] = {}
    for cap in catalog.capabilities:
        if cap.id in seen:
            errors.append(
                f"Duplicate capability id '{cap.id}' ({seen[cap.id]} and {cap.ref}); ids must be unique"
            )
        seen.setdefault(cap.id, cap.ref)
        _check_payload(cap, errors)
    _check_refs_and_cycles(catalog, errors)
    _check_target_collisions(catalog, errors)
    _check_groups(catalog, errors)
    if errors:
        bullet = "\n  - "
        raise CatalogError("Invalid CWI catalog:" + bullet + bullet.join(errors))
