import json
import shutil
from pathlib import Path

import pytest

from spado.runtime import commands
from spado.workflows.catalog import load_workflow
from spado.workflows.models import Scope, Workflow

CATALOG = Path(__file__).resolve().parents[2] / "catalog"


def test_slug_selectors_and_legacy_run_snapshot():
    workflow, _ = load_workflow(CATALOG)
    assert workflow.subphases["1.1"].slug == "initial-ideation"
    assert workflow.select(Scope(kind="subphase", id="initial-ideation")) == ["1.1"]
    assert workflow.resolve_scope(Scope(kind="subphase", id="initial-ideation")).id == "1.1"
    assert workflow.select(Scope(kind="subphase", id="1.1")) == ["1.1"]
    assert workflow.subphases["3.5"].slug == "ui-design"
    assert workflow.select(Scope(kind="subphase", id="ui-design")) == ["3.5"]
    assert workflow.select(Scope(kind="subphase", id="design-the-user-interface")) == ["3.5"]
    assert all(
        len(subphase.slug) <= 25 and workflow.resolve_subphase(subphase.slug) == sid
        for sid, subphase in workflow.subphases.items()
    )
    with pytest.raises(ValueError, match="Unknown subphase"):
        workflow.select(Scope(kind="subphase", id="not-a-subphase"))

    # Persisted runs from before slugs were added still deserialize and accept a unique title prefix.
    snapshot = workflow.model_dump()
    for subphase in snapshot["subphases"].values():
        subphase.pop("slug")
    legacy = Workflow.model_validate(snapshot)
    assert legacy.select(Scope(kind="subphase", id="initial-ideation")) == ["1.1"]


def test_catalog_rejects_duplicate_slugs(tmp_path):
    shutil.copytree(CATALOG / "workflows" / "spdlc", tmp_path / "workflows" / "spdlc")
    shutil.copytree(CATALOG / "organizations", tmp_path / "organizations")
    shutil.copytree(CATALOG / "organization-skills", tmp_path / "organization-skills")
    path = tmp_path / "workflows" / "spdlc" / "workflow.json"
    data = json.loads(path.read_text())
    data["subphases"]["1.2"]["slug"] = "initial-ideation"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="must be unique"):
        load_workflow(tmp_path)

    data["subphases"]["1.2"]["slug"] = "Invalid Slug"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="lowercase hyphenated"):
        load_workflow(tmp_path)


def test_create_run_stores_numeric_scope(monkeypatch, tmp_path, capsys):
    workflow, organization = load_workflow(CATALOG)

    class FakeStore:
        def create_run(self, token, run):
            assert run.scope == Scope(kind="subphase", id="1.1")
            return run.id

    cfg = type("ProjectConfig", (), {"workflow": "spdlc", "project": "project", "mode": "auto"})()
    monkeypatch.setattr(commands, "session", lambda root, human: (cfg, FakeStore(), "token"))
    monkeypatch.setattr(commands, "load_workflow", lambda root, name: (workflow, organization))
    commands.create_run("Assess opportunity", root=tmp_path, subphase="initial-ideation")
    assert "run" in capsys.readouterr().out


def test_event_payload_slug_is_stored_as_numeric_id(monkeypatch, tmp_path):
    workflow, _ = load_workflow(CATALOG)

    class FakeStore:
        def load(self, token, run_id):
            return type("RunSnapshot", (), {"workflow": workflow})(), None

        def record(self, token, run_id, kind, payload, rationale, event_id, expected_version):
            return {"subphase": payload["subphase"]}

    monkeypatch.setattr(commands, "session", lambda root, human: (None, FakeStore(), "token"))
    monkeypatch.setattr(commands, "_sync_changed", lambda *args: None)
    result = commands.record_request(
        tmp_path,
        {
            "kind": "prepare",
            "payload": {"subphase": "initial-ideation"},
            "rationale": "Test",
            "event_id": "same-id",
        },
        "run-id",
    )
    assert result == {"subphase": "1.1"}
