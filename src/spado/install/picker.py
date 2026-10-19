"""Category-based capability selection for capability-only `spado init`."""

from __future__ import annotations

import shutil
from collections.abc import Iterable

from spado.authoring.prompts import Option, Prompter, heading
from spado.domain.enums import CapabilityType, Category
from spado.domain.errors import UserCancelled
from spado.domain.models import Capability, Catalog

HOST_OPTIONS = (("claude", "Claude Code"), ("codex", "Codex"))
_TYPE_ORDER = list(CapabilityType)
_CHECKBOX_INDENT = 6  # pointer, checkbox and spacing drawn before each label


def compatible(catalog: Catalog, hosts: Iterable[str]) -> list[Capability]:
    """Capabilities declared compatible with every selected host."""
    wanted = set(hosts)
    return [c for c in catalog.capabilities if wanted <= set(c.manifest.hosts)]


def refs_in_categories(
    catalog: Catalog, hosts: Iterable[str], categories: Iterable[Category]
) -> list[str]:
    """Every host-compatible capability belonging to at least one of `categories`."""
    wanted = set(categories)
    return sorted(c.ref for c in compatible(catalog, hosts) if wanted & set(c.manifest.categories))


def _label(cap: Capability, columns: int) -> str:
    """One terminal line: the reference plus as much description as fits."""
    room = columns - _CHECKBOX_INDENT - len(cap.ref) - 3
    description = " ".join(cap.manifest.description.split())
    if room < 10:
        return cap.ref
    if len(description) > room:
        description = description[: room - 1].rstrip() + "…"
    return f"{cap.ref} — {description}"


def pick(
    catalog: Catalog, prompter: Prompter, hosts: list[str] | None
) -> tuple[list[str], list[str]]:
    """Ask for hosts (when not given), categories, then capabilities. Returns (hosts, refs)."""
    if not hosts:
        hosts = prompter.checkbox(
            "hosts",
            "Install for which hosts?",
            [Option(value, label, checked=value == "claude") for value, label in HOST_OPTIONS],
        )
        if not hosts:
            raise UserCancelled("No host selected. Nothing was installed.")
    available = compatible(catalog, hosts)
    counts = {
        category: sum(category in c.manifest.categories for c in available) for category in Category
    }
    categories = prompter.checkbox(
        "categories",
        "Which categories do you want to browse?",
        [Option(category, f"{category.label} ({n})") for category, n in counts.items() if n],
    )
    if not categories:
        raise UserCancelled("No category selected. Nothing was installed.")
    # A capability in several chosen categories is listed once, under the first of them.
    columns = shutil.get_terminal_size().columns
    options: list[Option] = []
    shown: set[str] = set()
    for category in (c for c in Category if c in categories):
        members = sorted(
            (c for c in available if category in c.manifest.categories and c.ref not in shown),
            key=lambda c: (_TYPE_ORDER.index(c.type), c.id),
        )
        if not members:
            continue
        options.append(heading(f"── {category.label} ──"))
        for cap in members:
            shown.add(cap.ref)
            options.append(Option(cap.ref, _label(cap, columns)))
    selected = prompter.checkbox("capabilities", "Select what to install", options)
    if not selected:
        raise UserCancelled("Nothing selected. Nothing was installed.")
    return list(hosts), sorted(selected)
