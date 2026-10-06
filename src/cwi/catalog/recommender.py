"""Deterministic, explainable capability recommendations (no LLM)."""

from __future__ import annotations

from cwi.domain.enums import ProjectType
from cwi.domain.models import Capability, Catalog, ProjectProfile, Recommendation, normalize_tech

TYPE_MATCH_SCORE = 10
TECH_MATCH_SCORE = 5
DEFAULT_SELECTED_SCORE = 100
THRESHOLD = 10

# Aliases so "next.js" in a manifest matches "Next.js"/"nextjs" in a profile.
_ALIASES: dict[str, set[str]] = {
    "next.js": {"nextjs", "next"},
    "postgresql": {"postgres"},
    "typescript": {"ts"},
    "javascript": {"js"},
    "github actions": {"github-actions"},
}


def _canonical(tech: str) -> str:
    t = normalize_tech(tech)
    for canon, aliases in _ALIASES.items():
        if t == canon or t in aliases:
            return canon
    return t


def score_capability(cap: Capability, profile: ProjectProfile) -> Recommendation:
    score = 0
    reasons: list[str] = []
    rules = cap.manifest.recommendation
    techs = {_canonical(t) for t in profile.technologies()}
    tech_names: list[str] = []
    type_hit = False

    if rules is not None:
        if profile.project_type in rules.project_types:
            score += TYPE_MATCH_SCORE
            type_hit = True
        display = _display_names(profile)
        for tech in rules.technologies:
            canon = _canonical(tech)
            if canon in techs:
                score += TECH_MATCH_SCORE
                tech_names.append(display.get(canon, tech))
        if rules.require_technology:
            if tech_names:
                score += TYPE_MATCH_SCORE  # technology evidence is the relevance signal here
            else:
                score = 0
                type_hit = False

    if tech_names:
        reasons.append(" + ".join(tech_names) + " detected")
    if type_hit:
        reasons.append(f"{profile.project_type.label.lower()} project")
    if cap.manifest.default_selected:
        score += DEFAULT_SELECTED_SCORE
        reasons.insert(0, "Recommended default")

    return Recommendation(
        ref=cap.ref,
        score=score,
        reasons=reasons,
        preselected=score >= THRESHOLD,
    )


def _display_names(profile: ProjectProfile) -> dict[str, str]:
    names: dict[str, str] = {}
    values = [
        *profile.languages,
        *profile.frameworks,
        *profile.databases,
        *profile.test_tools,
        *profile.tools,
        *profile.infrastructure,
        *profile.package_managers,
    ]
    for value in values:
        names.setdefault(_canonical(value), value.split()[0] if value.split() else value)
    return names


def recommend(catalog: Catalog, profile: ProjectProfile) -> dict[str, Recommendation]:
    return {cap.ref: score_capability(cap, profile) for cap in catalog.capabilities}


def is_application(profile: ProjectProfile) -> bool:
    return profile.project_type != ProjectType.OTHER
