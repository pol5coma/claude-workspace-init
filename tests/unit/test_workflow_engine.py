from pathlib import Path

import pytest

from spado.workflows.catalog import load_workflow, render_workflow
from spado.workflows.engine import apply, main_phase, missing_inputs, review
from spado.workflows.models import Actor, Mode, Run, Scope, Status

CATALOG = Path(__file__).resolve().parents[2] / "catalog"


@pytest.fixture
def execution():
    workflow, organization = load_workflow(CATALOG)
    run = Run(
        project="project",
        workflow=workflow,
        organization=organization,
        scope=Scope(kind="subphase", id="1.1"),
        mode=Mode.AUTO,
        objective="Test a product opportunity",
    )

    def actor(name, level, subphases=None):
        return Actor(
            project=run.project,
            definition=name,
            level=level,
            run_id=run.id,
            subphases=subphases or ["1.1"],
        )

    return (
        run,
        actor("CAOAO", "orchestrator"),
        actor("Human", "human"),
        actor("spdlc-1-1", "specialist"),
    )


def plan(run, sid="1.1", **changes):
    definition = run.workflow.subphases[sid]
    data = {
        "objective": "Evaluate opportunity",
        "deliverable": definition.deliverable,
        "actions": ["Investigate alternatives", "Record evidence"],
        "criteria": [definition.exit_criteria],
    }
    return data | changes


def prepare(execution, mode=Mode.AUTO, sid="1.1", **changes):
    run, caoao, _, specialist = execution
    result = apply(
        run,
        caoao,
        "prepare",
        {
            "subphase": sid,
            "owner": specialist.id,
            "plan": plan(run, sid, **changes),
            "mode": mode,
            "reason": "Explicit user invocation",
        },
    )
    return run.activities[result["activity"]]


def deliver(execution, activity):
    run, _, _, specialist = execution
    apply(run, specialist, "start", {"activity": activity.id})
    revision = apply(
        run,
        specialist,
        "document",
        {
            "path": "docs/opportunity.md",
            "content": "Observed evidence",
            "subphase": activity.subphase,
        },
    )["revision"]
    apply(
        run,
        specialist,
        "deliver",
        {
            "activity": activity.id,
            "outputs": [revision],
            "criteria_evidence": {c: "docs/opportunity.md" for c in activity.plan.criteria},
        },
    )
    for role in run.workflow.subphases[activity.subphase].owners:
        officer = Actor(
            project=run.project,
            definition=role,
            level="officer",
            run_id=run.id,
            subphases=[activity.subphase],
        )
        apply(
            run,
            officer,
            "domain_review",
            {
                "activity": activity.id,
                "decision": "approved",
                "evidence": "Reviewed the recorded opportunity evidence",
            },
        )
    return revision


def test_catalog_preserves_all_briefs_and_master_is_reproducible():
    workflow, organization = load_workflow(CATALOG)
    assert len(workflow.phases) == 7 and len(workflow.subphases) == 62
    assert "3.12" in workflow.subphases["3.5"].dependencies
    assert "6.12" not in workflow.subphases["1.1"].dependencies
    assert all(a.skills for a in organization.agents.values())
    assert render_workflow(CATALOG) == (CATALOG / "workflows/Full_SPDLC_Workflow.md").read_text()


@pytest.mark.parametrize("mode", list(Mode))
def test_mode_gates(execution, mode):
    run, caoao, human, specialist = execution
    activity = prepare(execution, mode)
    if mode in {Mode.MANUAL, Mode.SEMI_AUTO}:
        with pytest.raises(ValueError):
            apply(run, specialist, "start", {"activity": activity.id})
        request = {
            "activity": activity.id,
            "plan_id": activity.plan.id,
            "version": activity.plan.version,
            "arrangement": "delegated",
        }
        with pytest.raises(PermissionError):
            apply(run, caoao, "approve_plan", request)
        apply(run, human, "approve_plan", request)
    deliver(execution, activity)
    if mode == Mode.MANUAL:
        with pytest.raises(ValueError, match="Human result"):
            apply(run, caoao, "accept", {"activity": activity.id})
        apply(
            run,
            human,
            "human_review",
            {
                "activity": activity.id,
                "decision": "approved",
                "evidence": "Result accepted by user",
            },
        )
    apply(run, caoao, "accept", {"activity": activity.id})
    assert activity.status == Status.ACCEPTED


def test_provisional_outputs_cannot_be_accepted(execution):
    run, caoao, _, specialist = execution
    run.scope = Scope(kind="subphase", id="1.2")
    specialist.subphases = ["1.2"]
    with pytest.raises(ValueError, match="assumptions"):
        prepare(execution, sid="1.2")
    activity = prepare(execution, sid="1.2", assumptions=["Opportunity selection pending"])
    deliver(execution, activity)
    assert activity.status == Status.PROVISIONAL
    with pytest.raises(ValueError, match="unresolved inputs"):
        apply(run, caoao, "accept", {"activity": activity.id})
    assert missing_inputs(run, "1.2") == ["1.1"]


def test_advance_retains_full_scope_and_sequence(execution):
    run, caoao, _, specialist = execution
    run.scope = Scope()
    specialist.subphases = ["3.5"]
    activity = prepare(execution, sid="3.5", assumptions=["Provisional brand and requirements"])
    assert activity.out_of_order
    assert main_phase(run) == "1"
    assert len(run.workflow.select(run.scope)) == 62
    assert any(f["code"] == "out_of_order" for f in review(run))
    with pytest.raises(ValueError, match="phase plan"):
        apply(run, specialist, "start", {"activity": activity.id})


def test_plan_revision_revokes_approval(execution):
    run, caoao, human, _ = execution
    activity = prepare(execution, Mode.SEMI_AUTO)
    old = {"activity": activity.id, "plan_id": activity.plan.id, "version": 1}
    apply(run, human, "approve_plan", old)
    apply(run, caoao, "revise_plan", {"activity": activity.id, "plan": plan(run)})
    with pytest.raises(ValueError, match="stale"):
        apply(run, human, "approve_plan", old)
    assert activity.plan.approved_by is None


def test_document_change_invalidates_consumer_without_replacing_official(execution):
    run, caoao, human, _ = execution
    original = apply(
        run, human, "document", {"path": "docs/strategy.md", "content": "Original direction"}
    )["revision"]
    apply(run, human, "promote", {"revision": original})
    activity = prepare(execution, inputs={original: run.revisions[original].digest})
    deliver(execution, activity)
    apply(run, caoao, "accept", {"activity": activity.id})
    changed = apply(
        run, human, "document", {"path": "docs/strategy.md", "content": "Different direction"}
    )
    assert changed["affected"] == [activity.id]
    assert run.official["docs/strategy.md"] == original
    assert activity.status == Status.REVALIDATE
    assert not activity.plan.approved_by


def test_specialist_cannot_promote_or_impersonate_officer(execution):
    run, _, _, specialist = execution
    activity = prepare(execution)
    with pytest.raises(PermissionError):
        apply(
            run, specialist, "domain_review", {"activity": activity.id, "evidence": "Self approved"}
        )
    with pytest.raises(PermissionError):
        apply(run, specialist, "promote", {"revision": "anything"})
    outsider = specialist.model_copy(update={"project": "another"})
    with pytest.raises(PermissionError):
        apply(run, outsider, "start", {"activity": activity.id})


def test_read_review_does_not_mutate(execution):
    run, *_ = execution
    before = run.model_dump_json()
    assert review(run)
    assert run.model_dump_json() == before


def test_retirement_is_not_automatic(execution):
    run, caoao, *_ = execution
    run.scope = Scope()
    with pytest.raises(ValueError, match="Retirement"):
        prepare(execution, sid="7.1", assumptions=["Business closure pending"])
    with pytest.raises(PermissionError):
        apply(run, caoao, "retirement", {"evidence": "No authority"})
    ceao = Actor(project=run.project, definition="CEAO", level="officer", run_id=run.id)
    apply(run, ceao, "retirement", {"evidence": "Recorded business decision"})
    assert run.retirement_authorized


def test_rejected_review_requires_correction_and_fresh_domain_reviews(execution):
    run, caoao, _, specialist = execution
    activity = prepare(execution)
    deliver(execution, activity)
    ceao = Actor(
        project=run.project, definition="CEAO", level="officer", run_id=run.id, subphases=["1.1"]
    )
    apply(
        run,
        ceao,
        "domain_review",
        {
            "activity": activity.id,
            "decision": "changes_requested",
            "evidence": "The audience evidence is incomplete",
        },
    )
    assert activity.status == Status.BLOCKED
    with pytest.raises(ValueError):
        apply(run, caoao, "accept", {"activity": activity.id})
    apply(run, specialist, "start", {"activity": activity.id})
    revision = apply(
        run,
        specialist,
        "document",
        {"path": "docs/opportunity.md", "content": "Corrected evidence", "subphase": "1.1"},
    )["revision"]
    assert activity.status == Status.RUNNING
    apply(
        run,
        specialist,
        "deliver",
        {
            "activity": activity.id,
            "outputs": [revision],
            "criteria_evidence": {c: "Corrected evidence" for c in activity.plan.criteria},
        },
    )
    assert activity.domain_reviews == {}
    with pytest.raises(ValueError, match="domain reviews"):
        apply(run, caoao, "accept", {"activity": activity.id})


def test_new_phase_cycle_needs_explicit_reuse_of_accepted_work(execution):
    from spado.workflows.models import Activity, Plan

    run, caoao, _, specialist = execution
    run.scope = Scope(kind="phase", id="1")
    apply(run, caoao, "phase_plan", {"phase": "1", "plan": plan(run)})
    for sid in run.workflow.select(run.scope):
        activity = Activity(
            subphase=sid,
            mode=Mode.AUTO,
            owner=specialist.id,
            status=Status.ACCEPTED,
            plan=Plan.model_validate(plan(run, sid)),
            phase_plan_id=run.phase_plans["1"].id,
        )
        run.activities[activity.id] = activity
    apply(run, caoao, "close_phase", {"phase": "1"})
    apply(run, caoao, "phase_plan", {"phase": "1", "plan": plan(run)})
    with pytest.raises(ValueError, match="explicit reuse"):
        apply(run, caoao, "close_phase", {"phase": "1"})
    apply(
        run,
        caoao,
        "phase_plan",
        {"phase": "1", "plan": plan(run, reused_activities=list(run.activities))},
    )
    apply(run, caoao, "close_phase", {"phase": "1"})
    assert main_phase(run) is None


def test_na_requires_all_responsible_domains(execution):
    run, _, _, _ = execution
    run.scope = Scope(kind="subphase", id="3.5")
    for role in ["CPAO", "CMAO"]:
        actor = Actor(
            project=run.project, definition=role, level="officer", run_id=run.id, subphases=["3.5"]
        )
        apply(
            run,
            actor,
            "not_applicable",
            {
                "subphase": "3.5",
                "reason": "Headless service; consumer contracts cover the interface",
            },
        )
        assert ("3.5" in run.not_applicable) == (role == "CMAO")


def test_specialist_cannot_record_outputs_before_plan_gate(execution):
    run, _, _, specialist = execution
    prepare(execution, Mode.MANUAL)
    with pytest.raises(PermissionError, match="approved activity"):
        apply(
            run,
            specialist,
            "document",
            {"subphase": "1.1", "path": "docs/work.md", "content": "Premature work"},
        )


def test_snapshot_object_order_does_not_change_latest_work_or_revision(execution):
    run, caoao, human, _ = execution
    first = prepare(execution)
    second = apply(
        run,
        caoao,
        "prepare",
        {"subphase": "1.1", "owner": first.owner, "new_instance": True, "plan": plan(run)},
    )["activity"]
    revisions = [
        apply(run, human, "document", {"path": "docs/input.md", "content": content})["revision"]
        for content in ["Original", "Updated"]
    ]
    snapshot = run.model_dump()
    for key in ["activities", "revisions"]:
        snapshot[key] = dict(reversed(list(snapshot[key].items())))
    restored = Run.model_validate(snapshot)
    assert restored.latest("1.1").id == second
    assert restored.latest_revisions()["docs/input.md"].id == revisions[-1]
    third = apply(restored, human, "document", {"path": "docs/input.md", "content": "Third"})
    assert restored.revisions[third["revision"]].supersedes == revisions[-1]


def test_changed_phase_input_revokes_approval_before_any_activity(execution):
    run, caoao, human, _ = execution
    run.scope = Scope(kind="phase", id="1")
    revision = apply(run, human, "document", {"path": "docs/brief.md", "content": "Original"})[
        "revision"
    ]
    apply(
        run,
        caoao,
        "phase_plan",
        {"phase": "1", "plan": plan(run, inputs={revision: run.revisions[revision].digest})},
    )
    assert run.phase_plans["1"].approved_by
    apply(run, human, "document", {"path": "docs/brief.md", "content": "New direction"})
    assert run.phase_plans["1"].approved_by is None
    with pytest.raises(ValueError, match="edited revision"):
        apply(
            run,
            caoao,
            "phase_approve",
            {"phase": "1", "plan_id": run.phase_plans["1"].id, "version": 1},
        )


def test_canonical_dependency_revisions_are_included_in_plan(execution):
    run, caoao, _, specialist = execution
    activity = prepare(execution)
    revision = deliver(execution, activity)
    apply(run, caoao, "accept", {"activity": activity.id})
    run.scope = Scope(kind="subphase", id="1.2")
    specialist.subphases = ["1.2"]
    downstream = prepare(execution, sid="1.2")
    assert downstream.plan.inputs == {revision: run.revisions[revision].digest}
