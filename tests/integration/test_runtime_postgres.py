"""Real PostgreSQL/pgvector contract tests in an isolated, disposable Docker project.

Opt in with SPADO_POSTGRES_TEST=1. No existing database or Docker volume is reused.
"""

import json
import os
import socket
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from typer.testing import CliRunner

from spado.cli import app
from spado.runtime import config
from spado.runtime.embeddings import index, search
from spado.runtime.install import install, resources
from spado.runtime.store import Store
from spado.workflows.catalog import load_workflow
from spado.workflows.models import Mode, Run, Scope, uid

pytestmark = pytest.mark.skipif(
    os.environ.get("SPADO_POSTGRES_TEST") != "1",
    reason="Set SPADO_POSTGRES_TEST=1 for isolated Docker integration tests",
)
CATALOG = Path(__file__).resolve().parents[2] / "catalog"


@pytest.fixture(scope="module")
def database(tmp_path_factory):
    root = tmp_path_factory.mktemp("spado-postgres")
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    cfg = config.ProjectConfig(
        hosts=["codex"],
        mode=Mode.AUTO,
        embeddings=config.Embeddings(backend="external", model="fixture"),
        database_port=port,
    )
    install(root, resources(CATALOG, cfg))
    command = ["docker", "compose", "-f", str(root / ".spado/local/compose.yaml")]
    try:
        subprocess.run([*command, "up", "-d", "--wait"], check=True, timeout=240)
        dsn = config.dsn(root, cfg)
        Store(dsn, cfg.project).migrate()
        yield dsn
    finally:
        subprocess.run([*command, "down", "--volumes"], check=False, timeout=60)


@pytest.fixture
def state(database):
    store = Store(database, uid())
    human, human_token = store.bootstrap()
    workflow, organization = load_workflow(CATALOG)
    run = Run(
        project=store.project,
        workflow=workflow,
        organization=organization,
        scope=Scope(kind="subphase", id="1.1"),
        mode=Mode.AUTO,
        objective="Integration fixture",
    )
    store.create_run(human_token, run)
    caoao, token = store.delegate(human_token, run.id, "CAOAO")
    specialist, specialist_token = store.delegate(token, run.id, "spdlc-1-1")
    return store, run, human_token, token, specialist, specialist_token


def test_idempotence_conflict_rollback_and_isolation(state):
    store, run, human, token, specialist, specialist_token = state
    event = uid()
    payload = {"path": "docs/strategy.md", "content": "Product vision"}
    first = store.record(human, run.id, "document", payload, "Initial document", event)
    assert store.record(human, run.id, "document", payload, "Initial document", event) == first
    with pytest.raises(ValueError, match="Event ID reused"):
        store.record(
            human, run.id, "document", payload | {"content": "Other"}, "Initial document", event
        )
    before, _ = store.load(token, run.id)
    with pytest.raises(PermissionError):
        store.record(
            specialist_token,
            run.id,
            "promote",
            {"revision": first["revision"]},
            "Not allowed",
            uid(),
        )
    after, _ = store.load(token, run.id)
    assert before == after
    with pytest.raises(PermissionError):
        store.load("not-a-token", run.id)
    with pytest.raises(PermissionError):
        store.events(specialist_token, run.id)
    other = Store(store.dsn, uid())
    _, other_token = other.bootstrap()
    with pytest.raises(ValueError, match="not found"):
        other.load(other_token, run.id)


def test_concurrent_records_keep_all_changes(state):
    store, run, human, *_ = state

    def write(i):
        return store.record(
            human,
            run.id,
            "document",
            {"path": f"docs/{i}.md", "content": f"Evidence {i}"},
            "Concurrent evidence",
            uid(),
        )

    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(write, range(12)))
    final, _ = store.load(human, run.id)
    assert len(final.revisions) == 12 and final.version == 12


def test_persisted_revision_chain_and_activity_order(state):
    store, run, human, token, specialist, _ = state
    previous = None
    definition = run.workflow.subphases["1.1"]
    for i in range(5):
        revision = store.record(
            human,
            run.id,
            "document",
            {"path": "docs/revised.md", "content": f"Revision {i}"},
            "Update recorded evidence",
            uid(),
        )["revision"]
        current, _ = store.load(token, run.id)
        assert current.latest_revisions()["docs/revised.md"].id == revision
        assert current.revisions[revision].supersedes == previous
        previous = revision
        activity = store.record(
            token,
            run.id,
            "prepare",
            {
                "subphase": "1.1",
                "owner": specialist.id,
                "new_instance": True,
                "plan": {
                    "objective": "Re-evaluate the opportunity",
                    "deliverable": definition.deliverable,
                    "criteria": [definition.exit_criteria],
                    "actions": ["Review current evidence"],
                },
            },
            "Explicitly create an independent activity instance",
            uid(),
        )["activity"]
        current, _ = store.load(token, run.id)
        assert current.latest("1.1").id == activity


def test_pinned_workflow_and_mode_acceptance_end_to_end(state):
    store, run, human, token, specialist, specialist_token = state
    definition = run.workflow.subphases["1.1"]
    payload = {
        "subphase": "1.1",
        "owner": specialist.id,
        "mode": "semi-auto",
        "plan": {
            "objective": run.objective,
            "deliverable": definition.deliverable,
            "criteria": [definition.exit_criteria],
            "actions": ["Evaluate and document the opportunity"],
        },
    }
    result = store.record(token, run.id, "prepare", payload, "Prepare bounded work", uid())
    aid = result["activity"]
    with pytest.raises(ValueError):
        store.record(
            specialist_token, run.id, "start", {"activity": aid}, "Attempt premature start", uid()
        )
    current, _ = store.load(human, run.id)
    plan = current.activities[aid].plan
    store.record(
        human,
        run.id,
        "approve_plan",
        {"activity": aid, "plan_id": plan.id, "version": plan.version},
        "Human approves scope",
        uid(),
    )
    store.record(
        specialist_token, run.id, "start", {"activity": aid}, "Execute approved plan", uid()
    )
    rev = store.record(
        specialist_token,
        run.id,
        "document",
        {"path": "docs/opportunity.md", "content": "Research evidence", "subphase": "1.1"},
        "Deliver evidence",
        uid(),
    )["revision"]
    store.record(
        specialist_token,
        run.id,
        "deliver",
        {
            "activity": aid,
            "outputs": [rev],
            "criteria_evidence": {definition.exit_criteria: "Research evidence"},
        },
        "Report criteria",
        uid(),
    )
    for role in definition.owners:
        _, officer = store.delegate(token, run.id, role)
        store.record(
            officer,
            run.id,
            "domain_review",
            {
                "activity": aid,
                "decision": "approved",
                "evidence": "Reviewed research and acceptance criteria",
            },
            "Domain decision",
            uid(),
        )
    store.record(
        token, run.id, "accept", {"activity": aid}, "All applicable reviews satisfied", uid()
    )
    store.record(token, run.id, "promote", {"revision": rev}, "Promote accepted output", uid())
    final, _ = store.load(token, run.id)
    assert final.activities[aid].status == "accepted"
    assert final.official["docs/opportunity.md"] == rev
    assert final.workflow.subphases["1.1"].brief_content == definition.brief_content


def test_changed_global_input_blocks_specialist_without_impersonating_coordinator(
    state, tmp_path, monkeypatch
):
    from spado.runtime.commands import record_request

    store, run, human, token, specialist, specialist_token = state
    cfg = config.ProjectConfig(
        project=store.project,
        hosts=["codex"],
        mode=Mode.AUTO,
        embeddings=config.Embeddings(backend="external", model="fixture"),
    )
    install(tmp_path, resources(CATALOG, cfg))
    source = tmp_path / "docs/brief.md"
    source.parent.mkdir()
    source.write_text("Original direction")
    revision = store.record(
        human,
        run.id,
        "document",
        {"path": "docs/brief.md", "content": source.read_text()},
        "Initial source",
        uid(),
    )["revision"]
    current, _ = store.load(token, run.id)
    definition = run.workflow.subphases["1.1"]
    aid = store.record(
        token,
        run.id,
        "prepare",
        {
            "subphase": "1.1",
            "owner": specialist.id,
            "plan": {
                "objective": "Review source",
                "deliverable": definition.deliverable,
                "criteria": [definition.exit_criteria],
                "actions": ["Review current source"],
                "inputs": {revision: current.revisions[revision].digest},
            },
        },
        "Prepare source-dependent work",
        uid(),
    )["activity"]
    source.write_text("Changed direction")
    monkeypatch.setenv("SPADO_DATABASE_URL", store.dsn)
    monkeypatch.setenv("SPADO_ACTOR_TOKEN", specialist_token)
    before, _ = store.load(token, run.id)
    with pytest.raises(ValueError, match="outside delegated scope"):
        record_request(
            tmp_path,
            {
                "kind": "start",
                "payload": {"activity": aid},
                "event_id": uid(),
                "rationale": "Start",
            },
            run.id,
        )
    after, _ = store.load(token, run.id)
    assert before == after


class FakeEmbedder:
    identity = "fixture-model-v1"

    def encode(self, texts):
        return [[1.0, 0.2, 0.1] if "product" in text.lower() else [0.1, 1.0, 0.2] for text in texts]


def test_vector_search_is_project_scoped_and_read_only(state):
    store, run, human, token, _, specialist_token = state
    revision = store.record(
        human,
        run.id,
        "document",
        {"path": "docs/vision.md", "content": "Product direction"},
        "Initial approved context",
        uid(),
    )["revision"]
    store.record(human, run.id, "promote", {"revision": revision}, "Approve initial context", uid())
    embedder = FakeEmbedder()
    assert not search(store, token, run.id, embedder, "Product")["index_complete"]
    assert index(store, token, run.id, embedder)["indexed_chunks"] == 1
    before, _ = store.load(token, run.id)
    result = search(store, specialist_token, run.id, embedder, "Product")
    assert result["results"][0]["revision"] == revision
    assert result["index_complete"]
    after, _ = store.load(token, run.id)
    assert before == after
    with pytest.raises(PermissionError):
        index(store, specialist_token, run.id, embedder)
    embedder.identity = "fixture-model-v2"
    assert not search(store, token, run.id, embedder, "Product")["index_complete"]


def test_cli_queries_do_not_write_files_or_database(state, tmp_path, monkeypatch):
    store, run, human, token, *_ = state
    cfg = config.ProjectConfig(
        project=store.project,
        hosts=["codex"],
        mode=Mode.AUTO,
        embeddings=config.Embeddings(backend="external", model="fixture"),
    )
    install(tmp_path, resources(CATALOG, cfg))
    monkeypatch.setenv("SPADO_DATABASE_URL", store.dsn)
    monkeypatch.setenv("SPADO_ACTOR_TOKEN", token)
    before = {str(p): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    events = store.events(token, run.id)
    runner = CliRunner()
    for command in [["status"], ["review", "all"], ["workflow", "context"], ["workflow", "export"]]:
        response = runner.invoke(app, [*command, "--root", str(tmp_path), "--run", run.id])
        assert response.exit_code == 0, response.output
        assert isinstance(json.loads(response.stdout), dict)
    assert {str(p): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()} == before
    assert store.events(token, run.id) == events
