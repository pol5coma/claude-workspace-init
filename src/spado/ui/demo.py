"""A synthetic Idea & Strategy run, produced by the real domain engine, for `spado ui --demo`.

Every transition goes through `engine.apply`, so the demo obeys the same gates as a real run.
The events can be revealed progressively to imitate live execution.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

from spado.ui.transcripts import HOST
from spado.workflows.catalog import load_workflow
from spado.workflows.engine import apply
from spado.workflows.models import Actor, Event, Mode, Run, Scope, uid

PROJECT = "demo"
START = datetime(2026, 10, 19, 9, 0, tzinfo=UTC)
OBJECTIVE = "Choose one product opportunity worth investigating and frame its strategy"


class _Recorder:
    def __init__(self, run: Run):
        self.run = run
        self.clock = START
        self.events: list[dict] = []
        self.snapshots: list[Run] = []
        self.actors: list[Actor] = []
        self.transcript: list[dict] = []

    def tick(self, minutes: float = 3) -> str:
        self.clock += timedelta(minutes=minutes)
        return self.clock.isoformat()

    def _store(self, actor: Actor, kind: str, request: dict, result: dict) -> None:
        stamp = self.tick()
        self.events.append(
            {
                "id": uid(),
                "actor": actor.id,
                "timestamp": stamp,
                "request": request,
                "result": result,
            }
        )
        self.run.updated_at = stamp
        self.snapshots.append(self.run.model_copy(deep=True))

    def lifecycle(self, actor: Actor, kind: str, rationale: str, payload: dict, result: dict):
        event = Event(
            kind=kind, actor=actor.id, run_id=self.run.id, rationale=rationale, payload=payload
        )
        self._store(actor, kind, event.model_dump(), result)

    def record(self, actor: Actor, kind: str, payload: dict, rationale: str) -> dict:
        result = apply(self.run, actor, kind, payload)
        # The engine stamps wall-clock times; keep the demo on its own simulated clock.
        upcoming = (self.clock + timedelta(minutes=3)).isoformat()
        if kind == "document" and not result.get("unchanged"):
            self.run.revisions[result["revision"]].created_at = upcoming
        elif kind == "approve_plan":
            self.run.activities[payload["activity"]].plan.approved_at = upcoming
        elif kind == "phase_approve":
            self.run.phase_plans[payload["phase"]].approved_at = upcoming
        self.run.version += 1
        result["run_version"] = self.run.version
        self._store(actor, kind, {"kind": kind, "payload": payload, "rationale": rationale}, result)
        return result

    def delegate(self, parent: Actor, definition: str) -> Actor:
        template = self.run.organization.agents[definition]
        actor = Actor(
            project=PROJECT,
            definition=definition,
            level=template.level,
            run_id=self.run.id,
            subphases=template.subphases,
            parent_id=parent.id,
        )
        self.actors.append(actor)
        self.say(
            "delegation_prompt",
            HOST,
            [actor.id],
            f"{definition.lower()}: act as {template.name}",
            f"You are {template.name} for SPADO run {self.run.id}.\n"
            f"SPADO_ACTOR_TOKEN_FILE=.spado/local/actors/{actor.id}.token\n\n{template.mandate}",
            subagent_type=definition.lower(),
        )
        self.lifecycle(
            parent, "delegation", template.mandate, actor.model_dump(), {"actor": actor.id}
        )
        return actor

    def say(self, kind: str, sender: str, to: list[str], summary: str, text: str, **extra):
        self.transcript.append(
            {
                "id": uid(),
                "timestamp": self.tick(1),
                "source": "transcript",
                "kind": kind,
                "from": sender,
                "to": to,
                "summary": summary,
                "text": text,
                "session": "demo-session",
                "position": len(self.events),
                **extra,
            }
        )


def _plan(run: Run, sid: str, objective: str, actions: list[str], **extra) -> dict:
    definition = run.workflow.subphases[sid]
    return {
        "objective": objective,
        "deliverable": definition.deliverable,
        "actions": actions,
        "criteria": [definition.exit_criteria],
        **extra,
    }


def _evidence(run: Run, activity_id: str, where: str) -> dict:
    return {c: where for c in run.activities[activity_id].plan.criteria}


def build(catalog: Path) -> _Recorder:
    workflow, organization = load_workflow(catalog)
    run = Run(
        project=PROJECT,
        workflow=workflow,
        organization=organization,
        scope=Scope(kind="phase", id="1"),
        mode=Mode.SEMI_AUTO,
        objective=OBJECTIVE,
        created_at=START.isoformat(),
        updated_at=START.isoformat(),
    )
    rec = _Recorder(run)
    human = Actor(project=PROJECT, definition="Human", level="human")
    rec.actors.append(human)

    rec.say(
        "human_prompt",
        human.id,
        [HOST],
        "/spdlc --new-run --phase idea-strategy --mode semi-auto",
        "/spdlc --new-run --phase idea-strategy --mode semi-auto\n"
        "We want to help independent physiotherapists fill cancelled appointments. "
        "Assess the opportunity and frame the strategy. Show me each plan before executing it.",
    )
    rec.lifecycle(
        human,
        "run_created",
        OBJECTIVE,
        {"scope": run.scope.model_dump(), "workflow_version": workflow.version},
        {"run": run.id},
    )
    caoao = rec.delegate(human, "CAOAO")
    ceao = rec.delegate(caoao, "CEAO")
    cpao = rec.delegate(caoao, "CPAO")
    cmao = rec.delegate(caoao, "CMAO")
    founder = rec.delegate(ceao, "spdlc-1-1")
    marketer = rec.delegate(cmao, "spdlc-1-3")
    product = rec.delegate(caoao, "spdlc-1-2")

    phase_plan = rec.record(
        caoao,
        "phase_plan",
        {
            "phase": "1",
            "plan": {
                "objective": "Select an opportunity, its vision, audience and business model",
                "deliverable": "Accepted Idea & Strategy outputs for subphases 1.1–1.6",
                "actions": [
                    "Assess opportunities (1.1)",
                    "Define vision (1.2) and audience (1.3) on the chosen opportunity",
                    "Frame business model, risks and budget (1.4–1.6)",
                ],
                "criteria": ["Each subphase accepted by its domain officers"],
            },
        },
        "Phase 1 is the first incomplete phase of the selected scope.",
    )["plan"]
    rec.say(
        "host_reply",
        HOST,
        [human.id],
        "Phase 1 plan ready for approval",
        "CAOAO prepared the phase 1 plan v1. Do you approve it?",
    )
    rec.say("human_prompt", human.id, [HOST], "Approve phase plan", "Approved, go ahead.")
    rec.record(
        human,
        "phase_approve",
        {"phase": "1", "plan_id": phase_plan["id"], "version": phase_plan["version"]},
        "Human approved the phase plan in chat.",
    )

    first = rec.record(
        caoao,
        "prepare",
        {
            "subphase": "1.1",
            "owner": founder.id,
            "plan": _plan(
                run,
                "1.1",
                "Assess five opportunity ideas and choose one to investigate",
                [
                    "List candidate ideas",
                    "Score them against selection criteria",
                    "Record rejected ideas and unknowns",
                ],
            ),
        },
        "Brief 1.1 assigns the Founder / Business Lead under CEAO and CPAO.",
    )["activity"]
    activity = run.activities[first]
    rec.record(
        caoao,
        "note",
        {
            "activity": first,
            "category": "human_question",
            "message": "Plan v1 for 1.1 is ready. Approve?",
        },
        "Semi-auto mode requires Human plan approval.",
    )
    rec.say("human_prompt", human.id, [HOST], "Approve plan 1.1", "Yes, approve the 1.1 plan.")
    rec.record(
        human,
        "approve_plan",
        {"activity": first, "plan_id": activity.plan.id, "version": activity.plan.version},
        "Human approved plan v1 in chat.",
    )
    rec.record(founder, "start", {"activity": first}, "Plan approved and no missing inputs.")
    draft = rec.record(
        founder,
        "document",
        {
            "path": "docs/strategy/opportunities.md",
            "subphase": "1.1",
            "content": "# Opportunities\n\n1. **Cancellation backfill for physiotherapists** — chosen.\n2. Group class scheduling.\n3. Insurance pre-authorisation.\n",
        },
        "First draft of the opportunity assessment.",
    )["revision"]
    rec.record(
        founder,
        "deliver",
        {
            "activity": first,
            "outputs": [draft],
            "criteria_evidence": _evidence(run, first, "docs/strategy/opportunities.md"),
        },
        "Draft covers the shortlist and the chosen opportunity.",
    )
    rec.say(
        "subagent_report",
        founder.id,
        [HOST],
        "Delivered opportunity assessment v1",
        "Delivered docs/strategy/opportunities.md with three ideas and the chosen opportunity.",
    )
    rec.record(
        ceao,
        "domain_review",
        {
            "activity": first,
            "decision": "approved",
            "evidence": "Clear problem hypothesis and beneficiary.",
        },
        "Business review of the draft.",
    )
    rec.record(
        cpao,
        "domain_review",
        {
            "activity": first,
            "decision": "changes_requested",
            "evidence": "Rejected ideas lack reasons and major unknowns are missing.",
        },
        "Exit criterion requires rejected ideas and unknowns.",
    )
    rec.record(
        founder,
        "note",
        {
            "activity": first,
            "category": "execution",
            "message": "Adding rejection rationale and an unknowns section.",
        },
        "Responding to CPAO.",
    )
    rec.record(founder, "start", {"activity": first}, "Resuming after requested changes.")
    final = rec.record(
        founder,
        "document",
        {
            "path": "docs/strategy/opportunities.md",
            "subphase": "1.1",
            "content": "# Opportunities\n\n## Chosen\n**Cancellation backfill for physiotherapists**: clinics lose 12–18% of slots to late cancellations.\n\n## Rejected\n- Group class scheduling — crowded market.\n- Insurance pre-authorisation — regulatory dependency.\n\n## Unknowns\n- Willingness to pay per filled slot.\n- Patient opt-in rates for short-notice offers.\n",
        },
        "Corrected assessment with rejection reasons and unknowns.",
    )["revision"]
    rec.record(
        founder,
        "deliver",
        {
            "activity": first,
            "outputs": [final],
            "criteria_evidence": _evidence(run, first, "docs/strategy/opportunities.md#unknowns"),
        },
        "All exit criteria evidenced.",
    )
    rec.record(
        ceao,
        "domain_review",
        {
            "activity": first,
            "decision": "approved",
            "evidence": "Still coherent after corrections.",
        },
        "Business review.",
    )
    rec.record(
        cpao,
        "domain_review",
        {
            "activity": first,
            "decision": "approved",
            "evidence": "Rejections and unknowns recorded.",
        },
        "Product review.",
    )
    rec.record(caoao, "accept", {"activity": first}, "Both owner officers approved; gates pass.")
    rec.record(caoao, "promote", {"revision": final}, "Accepted output becomes official.")

    third = rec.record(
        caoao,
        "prepare",
        {
            "subphase": "1.3",
            "owner": marketer.id,
            "plan": _plan(
                run,
                "1.3",
                "Define the initial audience and value proposition",
                ["Segment clinics", "Draft value proposition"],
            ),
        },
        "1.1 is accepted, so 1.3 has its input.",
    )["activity"]
    rec.say("human_prompt", human.id, [HOST], "Approve plan 1.3", "Approve 1.3.")
    rec.record(
        human,
        "approve_plan",
        {"activity": third, "plan_id": run.activities[third].plan.id, "version": 1},
        "Human approved in chat.",
    )
    rec.record(marketer, "start", {"activity": third}, "Plan approved.")
    audience = rec.record(
        marketer,
        "document",
        {
            "path": "docs/strategy/audience.md",
            "subphase": "1.3",
            "content": "# Audience\n\nIndependent clinics with 2–10 practitioners and online booking.\n",
        },
        "Audience draft.",
    )["revision"]
    rec.record(
        marketer,
        "deliver",
        {
            "activity": third,
            "outputs": [audience],
            "criteria_evidence": _evidence(run, third, "docs/strategy/audience.md"),
        },
        "Audience and value proposition drafted.",
    )
    rec.record(
        cpao,
        "domain_review",
        {
            "activity": third,
            "decision": "approved",
            "evidence": "Segment is specific and reachable.",
        },
        "Product review.",
    )

    second = rec.record(
        caoao,
        "prepare",
        {
            "subphase": "1.2",
            "owner": product.id,
            "plan": _plan(
                run,
                "1.2",
                "Write the product vision and strategic goals",
                ["Draft vision", "Set three goals"],
            ),
        },
        "1.1 accepted; vision can start.",
    )["activity"]
    rec.record(
        caoao,
        "note",
        {
            "activity": second,
            "category": "human_question",
            "message": "Plan v1 for 1.2 awaits your approval.",
        },
        "Semi-auto mode requires Human plan approval.",
    )
    rec.record(
        cmao,
        "note",
        {
            "activity": third,
            "category": "question",
            "message": "Should 1.3 include clinic owners as buyers as well as users?",
        },
        "Pending marketing review.",
    )
    return rec


class DemoSource:
    """In-memory demo. With `step` > 0 seconds, one more event becomes visible per step."""

    label = "demo"

    def __init__(self, catalog: Path, step: float = 2.0):
        self.recorder = build(catalog)
        self.step = step
        self.started = time.monotonic()
        self.run_id = self.recorder.run.id

    def _visible(self) -> int:
        total = len(self.recorder.events)
        if self.step <= 0:
            return total
        return min(total, 1 + int((time.monotonic() - self.started) / self.step))

    def _check(self, run_id: str) -> None:
        if run_id != self.run_id:
            raise ValueError("Execution not found in this project")

    def runs(self) -> list[dict]:
        run = self.run(self.run_id)
        return [
            {
                "id": run.id,
                "workflow": run.workflow.id,
                "scope": run.scope.model_dump(),
                "objective": run.objective,
                "mode": run.mode,
                "version": run.version,
                "created_at": run.created_at,
                "updated_at": run.updated_at,
            }
        ]

    def run(self, run_id: str) -> Run:
        self._check(run_id)
        return self.recorder.snapshots[self._visible() - 1]

    def events(self, run_id: str) -> list[dict]:
        self._check(run_id)
        return self.recorder.events[: self._visible()]

    def actors(self, run_id: str) -> list[dict]:
        self._check(run_id)
        delegated = {e["result"].get("actor") for e in self.events(run_id)}
        return [
            a.model_dump() for a in self.recorder.actors if a.level == "human" or a.id in delegated
        ]

    def embeddings(self, run_id: str) -> list[dict]:
        self._check(run_id)
        return []

    def pulse(self, run_id: str) -> dict:
        run = self.run(run_id)
        return {
            "version": run.version,
            "updated_at": run.updated_at,
            "event_count": self._visible(),
            "transcripts": float(self._visible()),
        }

    def transcripts(self, run_id: str, actors: list[dict]) -> dict:
        self._check(run_id)
        visible = self._visible()
        entries = [
            {k: v for k, v in e.items() if k != "position"}
            for e in self.recorder.transcript
            if e["position"] < visible
        ]
        return {
            "available": True,
            "folder": "demo",
            "sessions": ["demo-session"],
            "entries": entries,
            "threads": [],
        }
