"""The C-organization of one run as a drawable hierarchy (pure; no I/O)."""

from __future__ import annotations

from collections import Counter

from spado.workflows.models import Run

TIERS = [
    {"level": "human", "label": "Human"},
    {"level": "orchestrator", "label": "Orchestration"},
    {"level": "officer", "label": "C-suite"},
    {"level": "specialist", "label": "Specialists"},
]


def traditional_title(acronym: str) -> str | None:
    """CTAO -> CTO, CISAO -> CISO. The orchestrator has no traditional equivalent."""
    if acronym == "CAOAO" or not acronym.endswith("AO") or len(acronym) < 4:
        return None
    return acronym[:-2] + "O"


def _reports_to(run: Run, definition_id: str, level: str, subphases: list[str]) -> list[str]:
    if level == "human":
        return []
    if level == "orchestrator":
        return ["Human"]
    if level == "officer":
        return ["CAOAO"]
    owners: list[str] = []
    for sid in subphases:
        for owner in run.workflow.subphases[sid].owners:
            if owner not in owners:
                owners.append(owner)
    return owners or ["CAOAO"]


def _event_kind(event: dict) -> str:
    return event.get("request", {}).get("kind", "")


def organization(run: Run, actors: list[dict], events: list[dict]) -> dict:
    scope = run.workflow.select(run.scope)
    scope_set = set(scope)
    in_scope_definitions = {"CAOAO"}
    for sid in scope:
        in_scope_definitions.update(run.workflow.subphases[sid].owners)
        in_scope_definitions.update(run.workflow.subphases[sid].specialists)

    definitions = [
        {
            "id": "Human",
            "name": "Human",
            "acronym": "Human",
            "traditional": None,
            "level": "human",
            "mandate": "Sets the objective, scope and delegation; approves where the mode requires it.",
            "skills": [],
            "subphases": [],
            "scope_subphases": [],
            "reports_to": [],
            "in_scope": True,
        }
    ]
    for agent in run.organization.agents.values():
        subphases = list(agent.subphases)
        if agent.level == "officer":
            owned = [sid for sid in scope if agent.id in run.workflow.subphases[sid].owners]
        else:
            owned = [sid for sid in subphases if sid in scope_set]
        definitions.append(
            {
                "id": agent.id,
                "name": agent.name,
                "acronym": agent.id if agent.level != "specialist" else agent.id.upper(),
                "traditional": traditional_title(agent.id) if agent.level == "officer" else None,
                "level": agent.level,
                "mandate": agent.mandate,
                "skills": agent.skills,
                "subphases": subphases,
                "scope_subphases": owned,
                "reports_to": _reports_to(run, agent.id, agent.level, subphases),
                "in_scope": agent.id in in_scope_definitions,
            }
        )

    per_actor: dict[str, list[dict]] = {}
    for event in events:
        per_actor.setdefault(event.get("actor", ""), []).append(event)

    instances = []
    for actor in actors:
        own = per_actor.get(actor["id"], [])
        last = own[-1] if own else None
        activities = [
            {
                "id": a.id,
                "subphase": a.subphase,
                "status": a.status,
                "plan_version": a.plan.version,
                "outputs": a.outputs,
            }
            for a in sorted(run.activities.values(), key=lambda a: a.sequence)
            if a.owner == actor["id"]
        ]
        reviews = [
            {
                "activity": e["request"]["payload"].get("activity"),
                "subphase": run.activities[e["request"]["payload"]["activity"]].subphase
                if e["request"]["payload"].get("activity") in run.activities
                else None,
                "decision": e["request"]["payload"].get("decision"),
                "evidence": e["request"]["payload"].get("evidence", ""),
                "timestamp": e.get("timestamp"),
            }
            for e in own
            if _event_kind(e) in {"domain_review", "human_review"}
        ]
        instances.append(
            {
                "id": actor["id"],
                "definition": actor["definition"],
                "level": actor["level"],
                "parent_id": actor.get("parent_id"),
                "subphases": actor.get("subphases", []),
                "event_count": len(own),
                "event_kinds": dict(Counter(_event_kind(e) for e in own)),
                "last_event": {"kind": _event_kind(last), "timestamp": last.get("timestamp")}
                if last
                else None,
                "activities": activities,
                "reviews": reviews,
            }
        )
    return {
        "tiers": TIERS,
        "scope_subphases": scope,
        "definitions": definitions,
        "instances": instances,
    }
