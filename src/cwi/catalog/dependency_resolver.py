"""Capability dependency resolution and conflict detection."""

from __future__ import annotations

from dataclasses import dataclass, field

from cwi.domain.models import Catalog


@dataclass
class Resolution:
    final: list[str]
    added: dict[str, str] = field(default_factory=dict)  # dependency ref -> first requiring ref


def resolve(selected: list[str], catalog: Catalog) -> Resolution:
    """Return the selection plus transitive dependencies, in deterministic order."""
    final: list[str] = []
    added: dict[str, str] = {}
    seen: set[str] = set()
    selected_set = set(selected)

    def visit(ref: str, required_by: str | None) -> None:
        if ref in seen:
            return
        seen.add(ref)
        cap = catalog.require(ref)
        for dep in cap.manifest.dependencies:
            visit(dep, ref)
        final.append(ref)
        if required_by is not None and ref not in selected_set:
            added.setdefault(ref, required_by)

    for ref in sorted(selected):
        visit(ref, None)
    return Resolution(final=sorted(final), added=added)


@dataclass(frozen=True)
class Conflict:
    a: str
    b: str


def find_conflicts(selected: list[str], catalog: Catalog) -> list[Conflict]:
    chosen = set(selected)
    found: set[tuple[str, str]] = set()
    for ref in sorted(chosen):
        cap = catalog.require(ref)
        for other in cap.manifest.conflicts:
            if other in chosen:
                found.add(tuple(sorted((ref, other))))  # type: ignore[arg-type]
    # Conflicts are symmetric even if only one side declares them.
    return [Conflict(a, b) for a, b in sorted(found)]
