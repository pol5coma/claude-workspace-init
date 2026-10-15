"""Pure domain transitions. No host invocation, filesystem access or hidden scheduling."""

from __future__ import annotations

import hashlib

from spado.workflows.models import (
    Activity,
    Actor,
    Mode,
    Plan,
    Revision,
    Run,
    Scope,
    Status,
    now,
    uid,
)


def authorize(run: Run, actor: Actor, subphase: str | None = None, *, coordinator=False):
    if actor.project != run.project or (actor.run_id and actor.run_id != run.id):
        raise PermissionError("Actor is outside this project/run")
    if coordinator and actor.level not in {"human", "orchestrator"}:
        raise PermissionError("This operation requires the Human or CAOAO")
    if (
        subphase is not None
        and actor.level in {"officer", "specialist"}
        and subphase not in actor.subphases
    ):
        raise PermissionError("Actor is outside its delegated subphases")


def missing_inputs(run: Run, sid: str) -> list[str]:
    missing = []
    for dep in run.workflow.subphases[sid].dependencies:
        previous = run.latest(dep)
        external = run.revisions.get(run.external_inputs.get(dep, ""))
        if dep in run.not_applicable:
            continue
        if external and external.approved_by and run.official.get(external.path) == external.id:
            continue
        if previous and previous.status == Status.ACCEPTED:
            continue
        missing.append(dep)
    return missing


def main_phase(run: Run) -> str | None:
    selected = set(run.workflow.select(run.scope))
    for phase in run.workflow.phases:
        if not selected.intersection(phase.subphases):
            continue
        if phase.lifecycle == "conditional" and not run.retirement_authorized:
            continue
        if phase.lifecycle == "recurring" and not run.retirement_authorized:
            return phase.id
        if phase.id not in run.phase_reviews:
            return phase.id
    return None


def approved_plan(plan: Plan):
    if not plan.approved_by:
        raise ValueError("The current plan version has not been approved")


def check_inputs(run: Run, plan: Plan):
    for rid, digest in plan.inputs.items():
        revision = run.revisions.get(rid)
        if not revision or revision.digest != digest:
            raise ValueError(f"Unknown or mismatched input revision {rid}")
        official = run.official.get(revision.path)
        if official and official != rid:
            raise ValueError(f"Input {revision.path} has been superseded; revise the plan")
        latest = run.latest_revisions()[revision.path]
        if latest.digest != revision.digest:
            raise ValueError(f"Input {revision.path} has an edited revision; revise the plan")


def plan_for(run: Run, sid: str, data: dict) -> Plan:
    plan = Plan.model_validate(data)
    plan.id = uid()
    # Approval metadata is never accepted from a submitted plan.
    plan.approved_by = plan.approved_at = None
    definition = run.workflow.subphases[sid]
    if definition.exit_criteria not in plan.criteria:
        raise ValueError("Plan criteria must include the subphase exit criteria")
    if plan.deliverable != definition.deliverable:
        raise ValueError("Plan must target the canonical subphase deliverable")
    plan.missing_dependencies = missing_inputs(run, sid)
    if plan.missing_dependencies and not plan.assumptions:
        raise ValueError("Provisional work requires explicit assumptions for missing inputs")
    # Canonical dependency edges must survive even if the caller omits their revisions.
    for dependency in definition.dependencies:
        if dependency in run.not_applicable:
            continue
        upstream = run.latest(dependency)
        external = run.external_inputs.get(dependency)
        revisions = (
            upstream.outputs
            if upstream and upstream.status == Status.ACCEPTED
            else [external]
            if external and dependency not in plan.missing_dependencies
            else []
        )
        for rid in revisions:
            plan.inputs.setdefault(rid, run.revisions[rid].digest)
    check_inputs(run, plan)
    return plan


def auto_approve(plan: Plan, mode: Mode, actor: Actor):
    if mode in {Mode.AGENTIC, Mode.AUTO} and actor.level == "orchestrator":
        plan.approved_by, plan.approved_at = actor.id, now()


def _activity(run: Run, actor: Actor, data: dict) -> Activity:
    activity = run.activities[data["activity"]]
    authorize(run, actor, activity.subphase)
    return activity


def invalidate(
    run: Run, revision_ids: set[str], producing_activity: str | None = None
) -> list[str]:
    affected = set(revision_ids)
    changed = True
    while changed:
        changed = False
        for revision in run.revisions.values():
            if revision.id not in affected and affected.intersection(revision.dependencies):
                affected.add(revision.id)
                changed = True
        for activity in run.activities.values():
            if affected.intersection(activity.plan.inputs) or affected.intersection(
                activity.outputs
            ):
                for output in activity.outputs:
                    if output not in affected:
                        affected.add(output)
                        changed = True
    invalidated = []
    for pid, plan in run.phase_plans.items():
        if affected.intersection(plan.inputs):
            plan.approved_by = plan.approved_at = None
            run.phase_reviews.pop(pid, None)
    for activity in run.activities.values():
        if activity.id == producing_activity and not affected.intersection(activity.plan.inputs):
            activity.domain_reviews.clear()
            activity.human_review = None
            continue
        if affected.intersection(activity.plan.inputs) or affected.intersection(activity.outputs):
            activity.status = Status.REVALIDATE
            activity.plan.approved_by = activity.plan.approved_at = None
            activity.domain_reviews.clear()
            activity.human_review = None
            phase = run.workflow.subphases[activity.subphase].phase
            run.phase_reviews.pop(phase, None)
            if phase in run.phase_plans:
                run.phase_plans[phase].approved_by = run.phase_plans[phase].approved_at = None
            invalidated.append(activity.id)
    return invalidated


def apply(run: Run, actor: Actor, kind: str, data: dict) -> dict:
    """Validate and apply one event inside the repository transaction."""
    if kind == "phase_plan":
        authorize(run, actor, coordinator=True)
        pid = data["phase"]
        run.workflow.select(Scope(kind="phase", id=pid))
        if not any(run.workflow.subphases[s].phase == pid for s in run.workflow.select(run.scope)):
            raise ValueError("Phase is outside this execution's scope")
        mode = Mode(data.get("mode", run.phase_modes.get(pid, run.mode)))
        plan = Plan.model_validate(data["plan"])
        plan.id = uid()
        plan.approved_by = plan.approved_at = None
        previous = run.phase_plans.get(pid)
        plan.version = previous.version + 1 if previous else 1
        check_inputs(run, plan)
        auto_approve(plan, mode, actor)
        run.phase_modes[pid] = mode
        run.phase_plans[pid] = plan
        run.phase_reviews.pop(pid, None)
        return {"phase": pid, "plan": plan.model_dump()}
    if kind == "phase_approve":
        authorize(run, actor, coordinator=True)
        pid = data["phase"]
        plan = run.phase_plans[pid]
        check_inputs(run, plan)
        if data["plan_id"] != plan.id or data["version"] != plan.version:
            raise ValueError("Approval targets a stale plan")
        mode = run.phase_modes.get(pid, run.mode)
        if mode in {Mode.MANUAL, Mode.SEMI_AUTO} and actor.level != "human":
            raise PermissionError("This mode requires Human plan approval")
        plan.approved_by, plan.approved_at = actor.id, now()
        return {"phase": pid, "plan_id": plan.id}
    if kind == "prepare":
        authorize(run, actor, coordinator=True)
        sid = data["subphase"]
        if sid not in run.workflow.select(run.scope):
            raise ValueError("Target is outside this run; create an independent run")
        definition = run.workflow.subphases[sid]
        if definition.phase == "7" and not run.retirement_authorized:
            raise ValueError("Retirement requires a recorded lifecycle decision")
        previous = run.latest(sid)
        if (
            previous
            and previous.status not in {Status.ACCEPTED, Status.NA}
            and not data.get("new_instance")
        ):
            return {"activity": previous.id, "status": previous.status, "resumed": True}
        plan = plan_for(run, sid, data["plan"])
        mode = run.effective_mode(sid, Mode(data["mode"]) if data.get("mode") else None)
        auto_approve(plan, mode, actor)
        owner = data["owner"]
        activity = Activity(
            sequence=len(run.activities) + 1,
            subphase=sid,
            mode=mode,
            owner=owner,
            plan=plan,
            previous_id=previous.id if previous else None,
            out_of_order=run.scope.kind == "workflow" and definition.phase != main_phase(run),
            reason=data.get("reason", ""),
        )
        if activity.out_of_order and not activity.reason:
            raise ValueError("An out-of-order invocation needs a recorded reason")
        if plan.approved_by:
            activity.status = Status.READY
        run.activities[activity.id] = activity
        return {
            "activity": activity.id,
            "status": activity.status,
            "missing": plan.missing_dependencies,
            "out_of_order": activity.out_of_order,
        }
    if kind in {
        "approve_plan",
        "revise_plan",
        "start",
        "deliver",
        "domain_review",
        "human_review",
        "accept",
        "block",
    }:
        activity = _activity(run, actor, data)
        definition = run.workflow.subphases[activity.subphase]
        if kind == "revise_plan":
            if actor.level not in {"human", "orchestrator"}:
                raise PermissionError("CAOAO coordinates plan revisions")
            plan = plan_for(run, activity.subphase, data["plan"])
            plan.version = activity.plan.version + 1
            auto_approve(plan, activity.mode, actor)
            activity.plan = plan
            activity.domain_reviews.clear()
            activity.human_review = None
            activity.status = Status.READY if plan.approved_by else Status.AWAITING_PLAN
        elif kind == "approve_plan":
            check_inputs(run, activity.plan)
            if data["plan_id"] != activity.plan.id or data["version"] != activity.plan.version:
                raise ValueError("Approval targets a stale plan")
            if activity.mode in {Mode.MANUAL, Mode.SEMI_AUTO} and actor.level != "human":
                raise PermissionError("This mode requires Human plan approval")
            if actor.level not in {"human", "orchestrator"}:
                raise PermissionError("Plan approval requires CAOAO or Human")
            if activity.mode == Mode.MANUAL:
                arrangement = data.get("arrangement")
                if arrangement not in {"human", "assisted", "delegated"}:
                    raise ValueError("Manual mode needs human, assisted or delegated execution")
                activity.arrangement = arrangement
            activity.plan.approved_by, activity.plan.approved_at = actor.id, now()
            activity.status = Status.READY
        elif kind == "start":
            if actor.level not in {"human", "orchestrator"} and actor.id != activity.owner:
                raise PermissionError("Only the assigned executor or coordinator may start work")
            if activity.status not in {Status.READY, Status.BLOCKED}:
                raise ValueError("Activity is not ready to start")
            approved_plan(activity.plan)
            check_inputs(run, activity.plan)
            if run.scope.kind != "subphase":
                if definition.phase not in run.phase_plans:
                    raise ValueError("A phase plan is required before execution")
                approved_plan(run.phase_plans[definition.phase])
                check_inputs(run, run.phase_plans[definition.phase])
                activity.phase_plan_id = run.phase_plans[definition.phase].id
            if actor.level == "specialist" and actor.id != activity.owner:
                raise PermissionError("Only the assigned specialist may execute this activity")
            if (
                activity.mode == Mode.MANUAL
                and activity.arrangement == "human"
                and actor.level != "human"
            ):
                raise PermissionError("The Human chose to perform this work")
            if missing_inputs(run, activity.subphase) and not activity.plan.assumptions:
                raise ValueError("Missing inputs require a revised provisional plan")
            activity.status = Status.RUNNING
        elif kind == "deliver":
            if actor.level not in {"human", "orchestrator"} and actor.id != activity.owner:
                raise PermissionError("Only the assigned executor or coordinator may deliver work")
            if activity.status != Status.RUNNING:
                raise ValueError("Delivery requires a running activity")
            if actor.level == "specialist" and actor.id != activity.owner:
                raise PermissionError("Only the assigned specialist may deliver")
            outputs = data["outputs"]
            if not outputs or any(
                r not in run.revisions or run.revisions[r].subphase != activity.subphase
                for r in outputs
            ):
                raise ValueError("Outputs must reference recorded revisions for this subphase")
            evidence = data["criteria_evidence"]
            if any(not evidence.get(c) for c in activity.plan.criteria):
                raise ValueError("Every plan criterion requires evidence")
            activity.outputs = outputs
            activity.criteria_evidence = evidence
            activity.domain_reviews.clear()
            activity.human_review = None
            activity.status = (
                Status.PROVISIONAL if missing_inputs(run, activity.subphase) else Status.REVIEW
            )
        elif kind == "domain_review":
            if actor.level != "officer" or actor.definition not in definition.owners:
                raise PermissionError("Only the assigned domain officer can record this review")
            if activity.status not in {Status.REVIEW, Status.PROVISIONAL}:
                raise ValueError("Review requires a delivered result")
            if not data.get("evidence") or data.get("decision") not in {
                "approved",
                "changes_requested",
            }:
                raise ValueError("Review requires evidence and an explicit decision")
            if data["decision"] == "approved":
                activity.domain_reviews[actor.definition] = actor.id + ": " + data["evidence"]
            else:
                activity.domain_reviews.pop(actor.definition, None)
                activity.status = Status.BLOCKED
                activity.reason = data["evidence"]
        elif kind == "human_review":
            if actor.level != "human":
                raise PermissionError("Human review requires Human identity")
            if activity.status not in {Status.REVIEW, Status.PROVISIONAL} or not data.get(
                "evidence"
            ):
                raise ValueError("Human review requires a delivered result and evidence")
            if data.get("decision") not in {"approved", "changes_requested"}:
                raise ValueError("Human review needs an explicit decision")
            if data["decision"] == "approved":
                activity.human_review = data["evidence"]
            else:
                activity.human_review = None
                activity.status = Status.BLOCKED
                activity.reason = data["evidence"]
        elif kind == "accept":
            authorize(run, actor, coordinator=True)
            approved_plan(activity.plan)
            check_inputs(run, activity.plan)
            if activity.status not in {Status.REVIEW, Status.PROVISIONAL} or not activity.outputs:
                raise ValueError("Acceptance requires delivered outputs")
            if missing_inputs(run, activity.subphase):
                raise ValueError("Provisional outputs cannot be accepted with unresolved inputs")
            if activity.plan.missing_dependencies:
                raise ValueError("Revise the provisional plan against the now-resolved inputs")
            if run.scope.kind != "subphase":
                phase_plan = run.phase_plans[definition.phase]
                approved_plan(phase_plan)
                check_inputs(run, phase_plan)
                if activity.phase_plan_id != phase_plan.id:
                    raise ValueError("Restart activity under the current approved phase plan")
            for rid in activity.plan.inputs:
                revision = run.revisions[rid]
                if not revision.approved_by and not any(
                    a.status == Status.ACCEPTED and rid in a.outputs
                    for a in run.activities.values()
                ):
                    raise ValueError(
                        "Provisional input revisions must be accepted before result acceptance"
                    )
            if any(owner not in activity.domain_reviews for owner in definition.owners):
                raise ValueError("Required domain reviews are missing")
            if activity.mode == Mode.MANUAL and not activity.human_review:
                raise ValueError("Manual mode requires Human result review")
            activity.status = Status.ACCEPTED
        elif kind == "block":
            if actor.level == "specialist" and actor.id != activity.owner:
                raise PermissionError("Only the assigned specialist can block its activity")
            if not data.get("reason"):
                raise ValueError("A blocker must identify its reason")
            activity.status, activity.reason = Status.BLOCKED, data["reason"]
        return {"activity": activity.id, "status": activity.status}
    if kind == "document":
        sid = data.get("subphase")
        authorize(run, actor, sid, coordinator=sid is None)
        if actor.level == "specialist" and not any(
            a.owner == actor.id and a.subphase == sid and a.status == Status.RUNNING
            for a in run.activities.values()
        ):
            raise PermissionError("Specialist output requires its own running, approved activity")
        content = data["content"]
        digest = hashlib.sha256(content.encode()).hexdigest()
        dependencies = data.get("dependencies", [])
        if any(r not in run.revisions for r in dependencies):
            raise ValueError("Document dependencies must reference existing revisions")
        if not data["path"] or data["path"].startswith("/") or ".." in data["path"].split("/"):
            raise ValueError("Document path must be project-relative")
        existing = run.latest_revisions().get(data["path"])
        if existing and actor.level in {"officer", "specialist"} and existing.subphase != sid:
            raise PermissionError("Cannot move another scope's document into this assignment")
        if existing and existing.digest == digest:
            return {"revision": existing.id, "unchanged": True}
        revision = Revision(
            sequence=len(run.revisions) + 1,
            path=data["path"],
            digest=digest,
            content=content,
            author=actor.id,
            subphase=sid,
            dependencies=dependencies,
            supersedes=existing.id if existing else None,
        )
        run.revisions[revision.id] = revision
        producing = max(
            (
                a
                for a in run.activities.values()
                if a.subphase == sid
                and a.status == Status.RUNNING
                and (actor.level != "specialist" or a.owner == actor.id)
            ),
            key=lambda a: a.sequence,
            default=None,
        )
        affected = (
            invalidate(run, {existing.id}, producing.id if producing else None) if existing else []
        )
        return {"revision": revision.id, "affected": affected}
    if kind == "promote":
        authorize(run, actor, coordinator=True)
        revision = run.revisions[data["revision"]]
        if run.latest_revisions()[revision.path].id != revision.id:
            raise ValueError("Only the latest document candidate can be promoted")
        if revision.subphase:
            accepted = any(
                a.status == Status.ACCEPTED and revision.id in a.outputs
                for a in run.activities.values()
            )
            if not accepted:
                raise ValueError("Only accepted activity outputs can be promoted")
        elif actor.level != "human":
            raise PermissionError(
                "Initial external project documentation requires Human attestation"
            )
        old = run.official.get(revision.path)
        revision.approved_by = actor.id
        run.official[revision.path] = revision.id
        return {
            "revision": revision.id,
            "affected": invalidate(run, {old}) if old and old != revision.id else [],
        }
    if kind == "external_input":
        sid = data["subphase"]
        authorize(run, actor, sid)
        if actor.level not in {"human", "officer"}:
            raise PermissionError("External input suitability requires a domain decision")
        if actor.level == "officer" and actor.definition not in run.workflow.subphases[sid].owners:
            raise PermissionError("This officer cannot accept evidence for that subphase")
        revision = run.revisions[data["revision"]]
        if (
            not revision.approved_by
            or run.official.get(revision.path) != revision.id
            or not data.get("evidence")
        ):
            raise ValueError(
                "External evidence must reference current approved documentation and a suitability rationale"
            )
        run.external_inputs[sid] = revision.id
        return {"subphase": sid, "revision": revision.id}
    if kind == "not_applicable":
        sid = data["subphase"]
        authorize(run, actor, sid)
        definition = run.workflow.subphases[sid]
        if not definition.applicability.lower().startswith("conditional"):
            raise ValueError("Required activities cannot be skipped as N/A")
        if (
            actor.level != "officer"
            or actor.definition not in definition.owners
            or not data.get("reason")
        ):
            raise PermissionError("N/A requires a responsible officer and rationale")
        approvals = run.not_applicable_reviews.setdefault(sid, {})
        approvals[actor.definition] = data["reason"]
        if all(role in approvals for role in definition.owners):
            run.not_applicable[sid] = "; ".join(
                f"{role}: {reason}" for role, reason in approvals.items()
            )
        return {
            "subphase": sid,
            "status": Status.NA if sid in run.not_applicable else Status.REVIEW,
        }
    if kind == "close_phase":
        authorize(run, actor, coordinator=True)
        pid = data["phase"]
        approved_plan(run.phase_plans[pid])
        check_inputs(run, run.phase_plans[pid])
        for sid in run.workflow.select(Scope(kind="phase", id=pid)):
            activity = run.latest(sid)
            if sid not in run.not_applicable and (
                not activity or activity.status != Status.ACCEPTED
            ):
                raise ValueError(f"Phase still has unaccepted work: {sid}")
            if (
                sid not in run.not_applicable
                and activity
                and (
                    activity.phase_plan_id != run.phase_plans[pid].id
                    and activity.id not in run.phase_plans[pid].reused_activities
                )
            ):
                raise ValueError(
                    f"Previous-cycle work needs explicit reuse in the approved phase plan: {sid}"
                )
        if run.phase_modes.get(pid, run.mode) == Mode.MANUAL and actor.level != "human":
            raise PermissionError("Manual phase closure requires Human review")
        run.phase_reviews[pid] = actor.id
        return {"phase": pid, "main_phase": main_phase(run)}
    if kind == "retirement":
        authorize(run, actor)
        if "7.1" not in run.workflow.select(run.scope):
            raise ValueError("Lifecycle transition is outside the selected execution scope")
        if actor.definition != "CEAO" or not data.get("evidence"):
            raise PermissionError("Retirement needs a CEAO lifecycle decision and evidence")
        run.retirement_authorized = True
        return {"retirement_authorized": True}
    if kind == "mode":
        authorize(run, actor, coordinator=True)
        if actor.level != "human":
            raise PermissionError("Mode changes require explicit Human direction")
        mode = Mode(data["mode"])
        if data.get("activity"):
            activity = run.activities[data["activity"]]
            if activity.status == Status.ACCEPTED:
                raise ValueError("Mode changes do not alter accepted history")
            activity.mode = mode
            activity.plan.approved_by = activity.plan.approved_at = None
            activity.status = Status.AWAITING_PLAN
        elif data.get("subphase"):
            run.workflow.select(Scope(kind="subphase", id=data["subphase"]))
            run.subphase_modes[data["subphase"]] = mode
        elif data.get("phase"):
            run.workflow.select(Scope(kind="phase", id=data["phase"]))
            run.phase_modes[data["phase"]] = mode
        else:
            run.mode = mode
        return {"mode": mode}
    if kind == "note":
        sid = (
            run.activities[data["activity"]].subphase
            if data.get("activity")
            else data.get("subphase")
        )
        authorize(run, actor, sid, coordinator=sid is None)
        if data.get("category") not in {
            "question",
            "decision",
            "execution",
            "handoff",
            "human_question",
        } or not data.get("message"):
            raise ValueError("Notes require a supported category and nonempty message")
        mode = (
            run.activities[data["activity"]].mode
            if data.get("activity")
            else run.effective_mode(sid)
            if sid
            else run.mode
        )
        if data["category"] == "human_question" and mode == Mode.AGENTIC:
            raise ValueError(
                "Agentic execution reports blockers without requesting Human intervention"
            )
        return {"recorded": True, "category": data["category"]}
    raise ValueError(f"Unknown event kind: {kind}")


def status(run: Run) -> dict:
    return {
        "run": run.id,
        "workflow": run.workflow.id,
        "workflow_version": run.workflow.version,
        "workflow_digest": run.workflow.content_digest,
        "scope": run.scope.model_dump(),
        "mode": run.mode,
        "version": run.version,
        "main_phase": main_phase(run),
        "last_recorded_at": run.updated_at,
        "live_execution_verified": False,
        "phases": [
            {
                "id": p.id,
                "closed": p.id in run.phase_reviews,
                "plan": run.phase_plans[p.id].model_dump() if p.id in run.phase_plans else None,
                "subphases": [
                    {
                        "id": sid,
                        "selected": sid in run.workflow.select(run.scope),
                        "status": (
                            run.latest(sid).status
                            if run.latest(sid)
                            else Status.NA
                            if sid in run.not_applicable
                            else Status.PENDING
                        ),
                        "instances": [
                            a.model_dump() for a in run.activities.values() if a.subphase == sid
                        ],
                    }
                    for sid in p.subphases
                ],
            }
            for p in run.workflow.phases
        ],
    }


def review(run: Run, scope: Scope | None = None, activity_id: str | None = None) -> list[dict]:
    selected = set(run.workflow.select(scope or Scope()))
    if activity_id:
        selected = {run.activities[activity_id].subphase}
    findings = []
    for sid in selected:
        for dep in missing_inputs(run, sid):
            findings.append(
                {
                    "severity": "warning",
                    "subphase": sid,
                    "code": "missing_input",
                    "dependency": dep,
                    "action": "Supply reviewed evidence or retain provisional status",
                }
            )
    for activity in run.activities.values():
        if activity.subphase not in selected or (activity_id and activity.id != activity_id):
            continue
        if activity.status in {Status.REVALIDATE, Status.BLOCKED, Status.PROVISIONAL}:
            findings.append(
                {
                    "severity": "warning",
                    "activity": activity.id,
                    "code": activity.status,
                    "action": "Review changed evidence and revise the plan before acceptance",
                }
            )
        if activity.out_of_order:
            findings.append(
                {
                    "severity": "info",
                    "activity": activity.id,
                    "code": "out_of_order",
                    "reason": activity.reason,
                }
            )
    return findings
