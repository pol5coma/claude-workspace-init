"""Pure views behind `spado ui`: the C-organization hierarchy and derived messages."""

import pytest

from spado.ui.communication import messages
from spado.ui.demo import DemoSource
from spado.ui.organization import organization, traditional_title
from spado.workflows.models import Scope
from tests.helpers import REAL_CATALOG


@pytest.fixture(scope="module")
def demo():
    source = DemoSource(REAL_CATALOG, step=0)
    run = source.run(source.run_id)
    return source, run, source.actors(run.id), source.events(run.id)


def by_definition(actors):
    return {a["definition"]: a["id"] for a in actors}


def test_traditional_titles():
    assert traditional_title("CTAO") == "CTO"
    assert traditional_title("CISAO") == "CISO"
    assert traditional_title("CAOAO") is None


def test_demo_run_passes_the_real_engine_gates(demo):
    _, run, _, _ = demo
    statuses = {sid: run.latest(sid).status for sid in ("1.1", "1.2", "1.3")}
    assert statuses == {
        "1.1": "accepted",
        "1.2": "awaiting_plan_approval",
        "1.3": "awaiting_review",
    }
    assert len(run.official) == 1


def test_organization_tiers_and_reporting_lines(demo):
    _, run, actors, events = demo
    org = organization(run, actors, events)
    assert [t["level"] for t in org["tiers"]] == ["human", "orchestrator", "officer", "specialist"]
    definitions = {d["id"]: d for d in org["definitions"]}
    assert definitions["CAOAO"]["reports_to"] == ["Human"]
    assert definitions["CTAO"]["reports_to"] == ["CAOAO"]
    assert definitions["CTAO"]["traditional"] == "CTO"
    # 1.4 has four owner officers; the specialist reports to all of them, first one primary.
    assert definitions["spdlc-1-4"]["reports_to"] == ["CEAO", "CFAO", "CPAO", "CMAO"]
    assert definitions["CPAO"]["scope_subphases"] == ["1.1", "1.2", "1.3", "1.4", "1.5"]


def test_organization_marks_scope_and_delegation(demo):
    _, run, actors, events = demo
    org = organization(run, actors, events)
    in_scope = {d["id"] for d in org["definitions"] if d["in_scope"]}
    assert {"CEAO", "CPAO", "CMAO", "CFAO", "CTAO", "spdlc-1-6"} <= in_scope
    assert "CLAO" not in in_scope and "spdlc-4-1" not in in_scope
    instances = {i["definition"]: i for i in org["instances"]}
    assert "CTAO" not in instances  # in scope, not delegated yet: drawn dimmed
    assert instances["spdlc-1-2"]["parent_id"] == instances["CAOAO"]["id"]
    cpao = instances["CPAO"]
    assert [r["decision"] for r in cpao["reviews"]] == ["changes_requested", "approved", "approved"]
    assert cpao["event_kinds"] == {"domain_review": 3}


def test_organization_follows_the_run_scope(demo):
    _, run, actors, events = demo
    narrowed = run.model_copy(update={"scope": Scope(kind="subphase", id="1.3")})
    org = organization(narrowed, actors, events)
    in_scope = {d["id"] for d in org["definitions"] if d["in_scope"] and d["level"] != "human"}
    assert in_scope == {"CAOAO", "CPAO", "CMAO", "spdlc-1-3"}


def test_messages_route_each_event_to_the_right_members(demo):
    _, run, actors, events = demo
    ids = by_definition(actors)
    found = messages(run, actors, events)
    assert len(found) == len(events)

    def one(kind, **match):
        return next(
            m
            for m in found
            if m["kind"] == kind and all(m["payload"].get(k) == v for k, v in match.items())
        )

    delegation = one("delegation", definition="spdlc-1-2")
    assert delegation["from"] == ids["CAOAO"] and delegation["to"] == [ids["spdlc-1-2"]]
    phase_plan = one("phase_plan")
    assert ids["Human"] in phase_plan["to"] and "def:CTAO" in phase_plan["to"]
    rejected = one("domain_review", decision="changes_requested")
    assert rejected["from"] == ids["CPAO"]
    assert rejected["to"] == [ids["CAOAO"], ids["spdlc-1-1"]]
    approved = next(m for m in found if m["kind"] == "domain_review" and m["from"] == ids["CEAO"])
    assert approved["to"] == [ids["CAOAO"]]
    deliver = next(m for m in found if m["kind"] == "deliver")
    assert deliver["to"] == [ids["CEAO"], ids["CPAO"]] and deliver["subphase"] == "1.1"
    human_question = one("note", category="human_question")
    assert human_question["to"] == [ids["Human"]]
    question = one("note", category="question")
    assert question["from"] == ids["CMAO"] and question["to"] == [ids["CAOAO"]]
    accept = next(m for m in found if m["kind"] == "accept")
    assert accept["to"][0] == ids["Human"] and ids["CAOAO"] not in accept["to"]
    assert all(m["from"] not in m["to"] for m in found)
