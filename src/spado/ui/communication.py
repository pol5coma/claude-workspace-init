"""Recorded events as messages between organization members (pure; no I/O).

SPADO stores who acted, not who was addressed. Recipients are derived from the run:
subphase owner officers, the activity's specialist, CAOAO and the Human. A role with no
delegated instance yet is addressed as ``def:<ROLE>`` so viewers can still place it.
"""

from __future__ import annotations

from spado.workflows.models import Mode, Run

APPROVAL_MODES = {Mode.SEMI_AUTO, Mode.MANUAL}


class _Directory:
    def __init__(self, run: Run, actors: list[dict]):
        self.run = run
        self.by_id = {a["id"]: a for a in actors}
        self.by_definition: dict[str, list[str]] = {}
        for actor in actors:
            self.by_definition.setdefault(actor["definition"], []).append(actor["id"])
        humans = [a["id"] for a in actors if a["level"] == "human"]
        self.human = humans or ["def:Human"]

    def role(self, definition: str) -> list[str]:
        return self.by_definition.get(definition) or [f"def:{definition}"]

    def caoao(self) -> list[str]:
        return self.role("CAOAO")

    def officers(self, subphase: str | None) -> list[str]:
        if not subphase or subphase not in self.run.workflow.subphases:
            return []
        found: list[str] = []
        for owner in self.run.workflow.subphases[subphase].owners:
            found += self.role(owner)
        return found

    def definition(self, actor_id: str) -> str:
        actor = self.by_id.get(actor_id)
        return actor["definition"] if actor else actor_id


def _unique(ids: list[str], sender: str) -> list[str]:
    result: list[str] = []
    for actor_id in ids:
        if actor_id != sender and actor_id not in result:
            result.append(actor_id)
    return result


def message(run: Run, directory: _Directory, event: dict) -> dict:
    request = event.get("request", {})
    result = event.get("result", {}) or {}
    kind = request.get("kind", "")
    payload = request.get("payload", {}) or {}
    sender = event.get("actor", "")
    activity_id = payload.get("activity") or result.get("activity")
    activity = run.activities.get(activity_id) if activity_id else None
    subphase = payload.get("subphase") or (activity.subphase if activity else None)
    owner = [activity.owner] if activity else []
    if kind == "prepare" and payload.get("owner"):
        owner = [payload["owner"]]
    officers = directory.officers(subphase)
    caoao = directory.caoao()
    human = directory.human
    to: list[str] = []
    summary = kind.replace("_", " ")

    if kind == "run_created":
        scope = payload.get("scope", {})
        target = scope.get("id") or "full workflow"
        to, summary = caoao, f"Started {scope.get('kind', 'workflow')} run ({target})"
    elif kind == "delegation":
        to = [payload.get("id", "")]
        summary = f"Delegated {payload.get('definition', 'actor')}"
    elif kind == "phase_plan":
        phase = payload.get("phase")
        plan_version = (result.get("plan") or {}).get("version", 1)
        phase_officers: list[str] = []
        for sid in run.workflow.select(run.scope):
            if run.workflow.subphases[sid].phase == phase:
                phase_officers += directory.officers(sid)
        needs_human = Mode(payload.get("mode", run.phase_modes.get(phase, run.mode)))
        to = phase_officers + (human if needs_human in APPROVAL_MODES else [])
        summary = f"Phase {phase} plan v{plan_version}"
    elif kind == "phase_approve":
        to, summary = caoao, f"Approved phase {payload.get('phase')} plan"
    elif kind in {"prepare", "revise_plan"}:
        plan = payload.get("plan", {})
        status = result.get("status")
        to = owner + officers + (human if status == "awaiting_plan_approval" else [])
        verb = "Revised plan" if kind == "revise_plan" else "Plan"
        summary = f"{verb} for {subphase}: {plan.get('objective', '')}".strip()
        if result.get("resumed"):
            summary = f"Resumed existing activity for {subphase}"
    elif kind == "approve_plan":
        to = owner + caoao
        summary = f"Approved plan v{payload.get('version')}"
    elif kind == "start":
        to, summary = officers + caoao, f"Started work on {subphase}"
    elif kind == "document":
        to = officers or caoao
        summary = f"Wrote {payload.get('path')}"
        if result.get("unchanged"):
            summary += " (unchanged)"
    elif kind == "deliver":
        outputs = payload.get("outputs", [])
        to, summary = officers, f"Delivered {len(outputs)} output(s) for review"
    elif kind == "domain_review":
        decision = payload.get("decision")
        to = caoao + (owner if decision == "changes_requested" else [])
        summary = (
            f"{decision.replace('_', ' ') if decision else 'review'}: {payload.get('evidence', '')}"
        )
    elif kind == "human_review":
        to = caoao + owner
        summary = f"Human {payload.get('decision', 'review').replace('_', ' ')}: {payload.get('evidence', '')}"
    elif kind == "accept":
        to, summary = human + owner + officers, f"Accepted {subphase}"
    elif kind == "promote":
        revision = run.revisions.get(payload.get("revision", ""))
        to = human
        summary = f"Promoted {revision.path if revision else 'revision'} to official"
    elif kind == "block":
        to, summary = caoao + officers, f"Blocked: {payload.get('reason', '')}"
    elif kind in {"external_input", "not_applicable"}:
        to = caoao
        summary = f"{summary.capitalize()} for {subphase}"
    elif kind == "close_phase":
        to, summary = human, f"Closed phase {payload.get('phase')}"
    elif kind == "retirement":
        to, summary = caoao + human, "Authorized retirement"
    elif kind == "mode":
        to, summary = caoao, f"Mode changed to {payload.get('mode')}"
    elif kind == "note":
        category = payload.get("category", "")
        participants = owner + officers + caoao
        if category == "human_question":
            to = human
        elif category == "question":
            to = caoao if directory.definition(sender) != "CAOAO" else owner + officers
        elif category == "handoff":
            to = officers + caoao
        else:
            to = participants
        summary = f"{category.replace('_', ' ')}: {payload.get('message', '')}"

    return {
        "id": event.get("id"),
        "timestamp": event.get("timestamp"),
        "source": "db",
        "kind": kind,
        "category": payload.get("category"),
        "from": sender,
        "to": _unique(to, sender),
        "summary": summary,
        "rationale": request.get("rationale", ""),
        "subphase": subphase,
        "activity": activity_id,
        "payload": payload,
        "result": result,
    }


def messages(run: Run, actors: list[dict], events: list[dict]) -> list[dict]:
    directory = _Directory(run, actors)
    return [message(run, directory, event) for event in events]
