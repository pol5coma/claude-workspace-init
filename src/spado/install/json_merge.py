"""Explicit, conflict-aware JSON merging for Claude settings and MCP configuration.

Never uses dict.update on nested configuration: that can erase user data.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any


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
