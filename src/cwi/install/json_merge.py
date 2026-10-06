"""Explicit, conflict-aware JSON merging for Claude settings and MCP configuration.

Never uses dict.update on nested configuration: that can erase user data.
"""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field
from typing import Any

from cwi.domain.models import HookEntryRef


@dataclass
class JsonConflict:
    path: str
    existing: Any
    incoming: Any


def deep_merge(base: Any, incoming: Any, path: str = "") -> tuple[Any, list[JsonConflict]]:
    """Recursive merge. dict+dict merges keys; lists append unseen items; scalar mismatch conflicts.

    On conflict the existing value is kept and the conflict is reported.
    """
    conflicts: list[JsonConflict] = []
    if isinstance(base, dict) and isinstance(incoming, dict):
        result = copy.deepcopy(base)
        for key, value in incoming.items():
            sub = f"{path}.{key}" if path else key
            if key in result:
                merged, sub_conflicts = deep_merge(result[key], value, sub)
                result[key] = merged
                conflicts.extend(sub_conflicts)
            else:
                result[key] = copy.deepcopy(value)
        return result, conflicts
    if isinstance(base, list) and isinstance(incoming, list):
        result_list = copy.deepcopy(base)
        for item in incoming:
            if item not in result_list:
                result_list.append(copy.deepcopy(item))
        return result_list, conflicts
    if base == incoming:
        return copy.deepcopy(base), conflicts
    conflicts.append(JsonConflict(path=path, existing=base, incoming=incoming))
    return copy.deepcopy(base), conflicts


# ---------------------------------------------------------------------------------------------
# Hooks (.claude/settings.json)
# ---------------------------------------------------------------------------------------------


def hook_identity(
    event: str, matcher: str | None, hook: dict[str, Any]
) -> tuple[str, str, str, str]:
    """Semantic identity of one hook handler. Centralized so every caller agrees."""
    return (event, matcher or "", str(hook.get("type", "")), str(hook.get("command", "")).strip())


def iter_hooks(settings: dict[str, Any]):
    """Yield (event, matcher, hook_dict) for every hook handler in a settings object."""
    hooks = settings.get("hooks") if isinstance(settings, dict) else None
    if not isinstance(hooks, dict):
        return
    for event, groups in hooks.items():
        if not isinstance(groups, list):
            continue
        for group in groups:
            if not isinstance(group, dict):
                continue
            for hook in group.get("hooks") or []:
                if isinstance(hook, dict):
                    yield event, group.get("matcher"), hook


def fragment_hook_refs(fragment: dict[str, Any]) -> list[HookEntryRef]:
    return [
        HookEntryRef(
            event=e, matcher=m or "", type=str(h.get("type", "")), command=str(h.get("command", ""))
        )
        for e, m, h in iter_hooks(fragment)
    ]


@dataclass
class HookMergeResult:
    settings: dict[str, Any]
    added: list[HookEntryRef] = field(default_factory=list)
    already_present: list[HookEntryRef] = field(default_factory=list)
    # Existing user hooks on the same event+matcher (coexistence notices, not conflicts).
    neighbours: list[tuple[HookEntryRef, HookEntryRef]] = field(default_factory=list)


def merge_hooks(settings: dict[str, Any], fragment: dict[str, Any]) -> HookMergeResult:
    """Additively merge a hooks fragment. Existing hooks are never replaced or removed."""
    result = copy.deepcopy(settings) if settings else {}
    if "hooks" in result and not isinstance(result["hooks"], dict):
        raise ValueError("Existing settings 'hooks' is not an object; refusing to merge")
    hooks = result.setdefault("hooks", {})
    existing_ids = {hook_identity(e, m, h) for e, m, h in iter_hooks(result)}
    outcome = HookMergeResult(settings=result)

    for event, groups in (fragment.get("hooks") or {}).items():
        event_groups = hooks.setdefault(event, [])
        if not isinstance(event_groups, list):
            raise ValueError(f"Existing settings hooks.{event} is not a list; refusing to merge")
        for group in groups:
            matcher = group.get("matcher")
            for hook in group.get("hooks") or []:
                ident = hook_identity(event, matcher, hook)
                ref = HookEntryRef(
                    event=event, matcher=matcher or "", type=ident[2], command=ident[3]
                )
                if ident in existing_ids:
                    outcome.already_present.append(ref)
                    continue
                for e, m, h in iter_hooks({"hooks": {event: event_groups}}):
                    if (m or "") == (matcher or ""):
                        outcome.neighbours.append(
                            (
                                HookEntryRef(
                                    event=e,
                                    matcher=m or "",
                                    type=str(h.get("type", "")),
                                    command=str(h.get("command", "")),
                                ),
                                ref,
                            )
                        )
                target = next(
                    (
                        g
                        for g in event_groups
                        if isinstance(g, dict)
                        and (g.get("matcher") or "") == (matcher or "")
                        and isinstance(g.get("hooks"), list)
                    ),
                    None,
                )
                if target is None:
                    target = {"hooks": []}
                    if matcher is not None:
                        target = {"matcher": matcher, "hooks": []}
                    event_groups.append(target)
                target["hooks"].append(copy.deepcopy(hook))
                existing_ids.add(ident)
                outcome.added.append(ref)
    return outcome


def remove_hooks(settings: dict[str, Any], refs: list[HookEntryRef]) -> dict[str, Any]:
    """Remove exactly the given hook handlers; prune groups/events that become empty."""
    result = copy.deepcopy(settings)
    targets = {(r.event, r.matcher, r.type, r.command) for r in refs}
    hooks = result.get("hooks")
    if not isinstance(hooks, dict):
        return result
    for event in list(hooks):
        groups = hooks[event]
        if not isinstance(groups, list):
            continue
        new_groups = []
        for group in groups:
            if not isinstance(group, dict) or not isinstance(group.get("hooks"), list):
                new_groups.append(group)
                continue
            kept = [
                h
                for h in group["hooks"]
                if not (
                    isinstance(h, dict) and hook_identity(event, group.get("matcher"), h) in targets
                )
            ]
            if kept:
                group = {**group, "hooks": kept}
                new_groups.append(group)
        if new_groups:
            hooks[event] = new_groups
        else:
            del hooks[event]
    if not hooks:
        del result["hooks"]
    return result


# ---------------------------------------------------------------------------------------------
# MCP (.mcp.json)
# ---------------------------------------------------------------------------------------------


@dataclass
class McpMergeResult:
    config: dict[str, Any]
    added: list[str] = field(default_factory=list)
    unchanged: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    replaced: list[str] = field(default_factory=list)


def merge_mcp(
    existing: dict[str, Any], fragment: dict[str, Any], resolutions: dict[str, str] | None = None
) -> McpMergeResult:
    """Merge servers by name: ADD / NO-OP / CONFLICT. `resolutions[name]` is 'keep' or 'replace'."""
    resolutions = resolutions or {}
    result = copy.deepcopy(existing) if existing else {}
    if "mcpServers" in result and not isinstance(result["mcpServers"], dict):
        raise ValueError("Existing .mcp.json 'mcpServers' is not an object; refusing to merge")
    servers = result.setdefault("mcpServers", {})
    outcome = McpMergeResult(config=result)
    for name, server in (fragment.get("mcpServers") or {}).items():
        if name not in servers:
            servers[name] = copy.deepcopy(server)
            outcome.added.append(name)
        elif servers[name] == server:
            outcome.unchanged.append(name)
        else:
            choice = resolutions.get(name)
            if choice == "replace":
                servers[name] = copy.deepcopy(server)
                outcome.replaced.append(name)
            elif choice == "keep":
                outcome.unchanged.append(name)
            else:
                outcome.conflicts.append(name)
    return outcome


def dump_json(data: Any) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"
