import json
import shutil
from pathlib import Path

import pytest

from spado.runtime import commands
from spado.workflows.catalog import load_workflow
from spado.workflows.models import Scope, Workflow

CATALOG = Path(__file__).resolve().parents[2] / "catalog"


def test_phase_slug_and_numeric_select_same_subphases():
    workflow, _ = load_workflow(CATALOG)
    by_slug = workflow.select(Scope(kind="phase", id="definition-design"))
    assert by_slug == workflow.select(Scope(kind="phase", id="3"))
    assert len(by_slug) == 13
    assert workflow.resolve_scope(Scope(kind="phase", id="definition-design")).id == "3"
    assert all(workflow.resolve_phase(phase.slug) == phase.id for phase in workflow.phases)
    with pytest.raises(ValueError, match="Unknown phase"):
        workflow.select(Scope(kind="phase", id="unknown-phase"))

    snapshot = workflow.model_dump()
    for phase in snapshot["phases"]:
        phase.pop("slug")
    legacy = Workflow.model_validate(snapshot)
    assert legacy.select(Scope(kind="phase", id="definition-design")) == by_slug


def test_catalog_rejects_duplicate_or_invalid_phase_slugs(tmp_path):
    shutil.copytree(CATALOG / "workflows" / "spdlc", tmp_path / "workflows" / "spdlc")
    shutil.copytree(CATALOG / "organizations", tmp_path / "organizations")
    shutil.copytree(CATALOG / "organization-skills", tmp_path / "organization-skills")
    path = tmp_path / "workflows" / "spdlc" / "workflow.json"
    data = json.loads(path.read_text())
    data["phases"][1]["slug"] = "idea-strategy"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="Phase slugs must be unique"):
        load_workflow(tmp_path)

    data["phases"][1]["slug"] = "Invalid Slug"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="Every phase needs"):
        load_workflow(tmp_path)


def test_phase_slug_is_canonicalized_for_runs_and_events(monkeypatch, tmp_path, capsys):
    workflow, organization = load_workflow(CATALOG)

    class FakeStore:
        def create_run(self, token, run):
            assert run.scope == Scope(kind="phase", id="3")
            return run.id

        def load(self, token, run_id):
            return type("RunSnapshot", (), {"workflow": workflow})(), None

        def record(self, token, run_id, kind, payload, rationale, event_id, expected_version):
            return {"phase": payload["phase"]}

    cfg = type("ProjectConfig", (), {"workflow": "spdlc", "project": "project", "mode": "auto"})()
    monkeypatch.setattr(commands, "session", lambda root, human: (cfg, FakeStore(), "token"))
    monkeypatch.setattr(commands, "load_workflow", lambda root, name: (workflow, organization))
    monkeypatch.setattr(commands, "_sync_changed", lambda *args: None)
    commands.create_run("Design product", root=tmp_path, phase="definition-design")
    assert "run" in capsys.readouterr().out

    result = commands.record_request(
        tmp_path,
        {
            "kind": "phase_plan",
            "payload": {"phase": "definition-design"},
            "rationale": "Test",
            "event_id": "same-id",
        },
        "run-id",
    )
    assert result == {"phase": "3"}
