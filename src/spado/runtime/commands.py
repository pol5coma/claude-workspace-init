from __future__ import annotations

import json
import os
import subprocess
import sys
from functools import wraps
from pathlib import Path
from typing import Annotated

import psycopg
import typer

from spado.domain.enums import Category
from spado.domain.errors import SPADOError
from spado.runtime import config
from spado.runtime.config import Embeddings, ProjectConfig, dump
from spado.runtime.install import install, resources
from spado.runtime.store import Store
from spado.workflows.catalog import load_workflow, render_workflow
from spado.workflows.engine import authorize, missing_inputs, review, status
from spado.workflows.models import Mode, Run, Scope, uid

workflow_app = typer.Typer(help="Prepare, inspect and record organization workflow execution.")
database_app = typer.Typer(help="Manage the local PostgreSQL/pgvector container.")
actor_app = typer.Typer(help="Delegate scoped actor identities.")
docs_app = typer.Typer(help="Version, promote and search project documentation.")
Root = Annotated[Path, typer.Option("--root", help="Configured project root.")]
RunId = Annotated[
    str | None, typer.Option("--run", help="Execution ID; required when selection is ambiguous.")
]
Human = Annotated[
    bool, typer.Option("--human", help="Direct Human action using the local Human credential.")
]


def guarded(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except (ValueError, PermissionError, KeyError, OSError, psycopg.Error, SPADOError) as exc:
            # Do not expose connection strings or provider credentials in exception details.
            message = (
                "PostgreSQL operation failed; check `spado db up` and database configuration"
                if isinstance(exc, psycopg.Error)
                else str(exc)
            )
            typer.echo(dump({"error": message}), err=True)
            raise typer.Exit(1) from None

    return wrapped


def session(root: Path, human=False):
    root = root.resolve()
    cfg = config.load(root)
    return cfg, Store(config.dsn(root, cfg), cfg.project), config.actor_token(root, human=human)


def select_run(store, token, run_id):
    if run_id:
        return run_id
    choices = store.list_runs(token)
    if len(choices) != 1:
        raise ValueError(
            "Select an execution with --run; available IDs: " + ", ".join(r["id"] for r in choices)
        )
    return choices[0]["id"]


def target_scope(phase: str | None, subphase: str | None):
    if phase and subphase:
        raise ValueError("--phase and --subphase are mutually exclusive")
    return (
        Scope(kind="phase", id=phase)
        if phase
        else Scope(kind="subphase", id=subphase)
        if subphase
        else Scope()
    )


def _sync_changed(root, store, token, run_id):
    from spado.install.filesystem import FileSystem
    from spado.runtime.install import sha

    run, actor = store.load(token, run_id)
    latest = run.latest_revisions()
    fs = FileSystem(root)
    required = {
        rid
        for activity in run.activities.values()
        if activity.subphase in actor.subphases
        for rid in activity.plan.inputs
    }
    required.update(
        rid
        for pid, plan in run.phase_plans.items()
        if any(run.workflow.subphases[s].phase == pid for s in actor.subphases)
        for rid in plan.inputs
    )
    required_paths = {run.revisions[rid].path for rid in required}
    for path, revision in latest.items():
        outside_scope = (
            actor.level in {"officer", "specialist"} and revision.subphase not in actor.subphases
        )
        if outside_scope and path not in required_paths:
            continue
        source = fs.path(path)
        if not source.is_file():
            raise ValueError(
                f"Recorded document is missing: {path}; restore it or resolve its consumers"
            )
        content = source.read_text()
        if sha(content.encode()) != revision.digest:
            if outside_scope:
                raise ValueError(
                    f"Input changed outside delegated scope: {path}; ask CAOAO to synchronize and revalidate"
                )
            store.record(
                token,
                run_id,
                "document",
                {
                    "path": path,
                    "content": content,
                    "subphase": revision.subphase,
                    "dependencies": revision.dependencies,
                },
                "Detected an external edit before execution",
                uid(),
            )


def interactive_terminal() -> bool:
    return sys.stdin.isatty() and sys.stdout.isatty()


def capability_prompter():
    from spado.authoring.prompts import InquirerPrompter

    return InquirerPrompter()


def choose_capabilities(
    root: Path, catalog_path: Path, hosts: list[str] | None, merges: dict, dry_run: bool
) -> tuple[list[str], list[str]]:
    """Interactive picker: browse categories, select, preview, confirm."""
    from rich.console import Console

    from spado.adapters.capabilities import render_capabilities
    from spado.catalog.dependency_resolver import resolve
    from spado.catalog.loader import load_catalog
    from spado.domain.errors import UserCancelled
    from spado.install.picker import pick

    loaded = load_catalog(catalog_path)
    prompter = capability_prompter()
    hosts, selected = pick(loaded, prompter, hosts)
    resolution = resolve(selected, loaded)
    preview = install(
        root,
        render_capabilities(root, catalog_path, hosts, selected),
        dry_run=True,
        merge_preconditions=merges,
    )
    console = Console(stderr=True)
    console.print(f"\n[bold]{len(resolution.final)} capabilities for {', '.join(hosts)}:[/bold]")
    for ref in resolution.final:
        note = (
            f"  [dim](required by {resolution.added[ref]})[/dim]" if ref in resolution.added else ""
        )
        console.print(f"  • {ref}{note}")
    console.print(f"[dim]{len(preview['writes'])} files to write in {root}[/dim]\n")
    if dry_run:
        typer.echo(dump(preview))
        return hosts, selected
    if not prompter.confirm("confirm", "Install them now?", default=True):
        raise UserCancelled("Cancelled. Nothing was installed.")
    return hosts, selected


@guarded
def initialize(
    root: Root = Path("."),
    host: Annotated[
        list[str] | None, typer.Option("--host", help="claude or codex; repeat for both.")
    ] = None,
    mode: Annotated[Mode | None, typer.Option("--mode")] = None,
    embeddings: Annotated[
        str | None, typer.Option("--embeddings", help="local or external.")
    ] = None,
    model: Annotated[str | None, typer.Option("--embedding-model")] = None,
    endpoint: Annotated[
        str, typer.Option("--embedding-endpoint")
    ] = "https://api.openai.com/v1/embeddings",
    catalog: Annotated[Path | None, typer.Option("--catalog")] = None,
    port: Annotated[int, typer.Option("--database-port")] = 55432,
    capability: Annotated[
        list[str] | None,
        typer.Option("--capability", help="Optional catalog reference; repeatable."),
    ] = None,
    category: Annotated[
        list[Category] | None,
        typer.Option(
            "--category",
            help="With --no-workflow: install every capability in this category; repeatable.",
        ),
    ] = None,
    workflow: Annotated[
        bool,
        typer.Option(
            "--workflow/--no-workflow", help="Install SPDLC, or only the selected capabilities."
        ),
    ] = True,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
):
    """Install the SPDLC organization or selected standalone capabilities.

    With --no-workflow and neither --capability nor --category, an interactive terminal
    opens a category picker.
    """
    root = root.resolve()
    if not root.is_dir():
        raise ValueError("Project root must already exist")
    from spado.adapters.capabilities import render_capabilities
    from spado.install.filesystem import FileSystem
    from spado.runtime.install import sha

    merges = {}
    for relative in [".codex/config.toml", ".mcp.json", ".claude/settings.json"]:
        path = FileSystem(root).path(relative)
        if path.is_file():
            merges[relative] = sha(path.read_bytes())
    if category and workflow:
        raise ValueError("--category is only available with --no-workflow")
    if not workflow:
        catalog_path = catalog or config.default_catalog()
        selected = list(capability or [])
        if category:
            from spado.catalog.loader import load_catalog
            from spado.install.picker import refs_in_categories

            if not host:
                raise ValueError("--category requires --host")
            selected = sorted(
                {*selected, *refs_in_categories(load_catalog(catalog_path), host, category)}
            )
        if not selected and interactive_terminal():
            host, selected = choose_capabilities(root, catalog_path, host, merges, dry_run)
            if dry_run:
                return
        if not host or not selected:
            raise ValueError(
                "Capability-only setup requires --host and --capability or --category "
                "(run it in an interactive terminal to pick from the catalog)"
            )
        output = render_capabilities(root, catalog_path, host, selected)
        typer.echo(dump(install(root, output, dry_run=dry_run, merge_preconditions=merges)))
        return
    existing = config.load(root) if (root / ".spado/project.json").exists() else None
    if existing:
        # Updating the embedding model selects a fresh index identity; no silent reuse.
        values = existing.model_dump(mode="json")
        if host:
            values["hosts"] = host
        if mode:
            values["mode"] = mode
        if capability is not None:
            values["capabilities"] = capability
        if embeddings or model:
            values["embeddings"] = {
                "backend": embeddings or existing.embeddings.backend,
                "model": model or existing.embeddings.model,
                "endpoint": endpoint,
            }
        cfg = ProjectConfig.model_validate(values)
    else:
        if not host or not mode or not embeddings or not model:
            raise ValueError(
                "Initial setup requires --host, --mode, --embeddings and --embedding-model"
            )
        cfg = ProjectConfig(
            hosts=host,
            mode=mode,
            embeddings=Embeddings(backend=embeddings, model=model, endpoint=endpoint),
            database_port=port,
            capabilities=capability or [],
        )
    output = resources(catalog or config.default_catalog(), cfg)
    extras = render_capabilities(
        root, catalog or config.default_catalog(), cfg.hosts, cfg.capabilities
    )
    if any(name in output and output[name] != body for name, body in extras.items()):
        raise ValueError("Optional capabilities conflict with organization resources")
    output.update(extras)
    result = install(root, output, dry_run=dry_run, merge_preconditions=merges)
    result["next"] = "spado db up, then spado workflow create --objective TEXT --human"
    typer.echo(dump(result))


@database_app.command("up")
@guarded
def database_up(root: Root = Path(".")):
    cfg = config.load(root)
    result = subprocess.run(
        [
            "docker",
            "compose",
            "-f",
            str(root.resolve() / ".spado/local/compose.yaml"),
            "up",
            "-d",
            "--wait",
        ],
        check=False,
    )
    if result.returncode:
        raise ValueError("Docker Compose failed to start PostgreSQL")
    store = Store(config.dsn(root, cfg), cfg.project)
    store.migrate()
    credential = root / ".spado/local/human.token"
    if not credential.exists():
        _, token = store.bootstrap()
        fd = os.open(credential, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "w") as handle:
            handle.write(token)
    typer.echo(dump({"database": "ready", "human_credential": str(credential)}))


@database_app.command("down")
@guarded
def database_down(root: Root = Path(".")):
    config.load(root)
    result = subprocess.run(
        ["docker", "compose", "-f", str(root.resolve() / ".spado/local/compose.yaml"), "down"],
        check=False,
    )
    if result.returncode:
        raise ValueError("Docker Compose failed; persistent volumes were not requested for removal")


@database_app.command("migrate")
@guarded
def database_migrate(root: Root = Path(".")):
    cfg = config.load(root)
    Store(config.dsn(root, cfg), cfg.project).migrate()
    typer.echo(dump({"schema_version": 1}))


@actor_app.command("create")
@guarded
def create_actor(
    definition: str, run_id: RunId = None, root: Root = Path("."), human: Human = False
):
    _, store, token = session(root, human)
    actor, credential = store.delegate(token, select_run(store, token, run_id), definition)
    directory = root / ".spado/local/actors"
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    path = directory / f"{actor.id}.token"
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "w") as handle:
        handle.write(credential)
    typer.echo(dump({"actor": actor.model_dump(), "token_file": str(path.resolve())}))


@workflow_app.command("create")
@guarded
def create_run(
    objective: Annotated[str, typer.Option("--objective")],
    root: Root = Path("."),
    phase: Annotated[str | None, typer.Option("--phase", help="Phase slug or numeric ID.")] = None,
    subphase: Annotated[
        str | None,
        typer.Option(
            "--subphase",
            help="Subphase slug; numeric IDs also work. List with `spado workflow validate`.",
        ),
    ] = None,
    mode: Mode | None = None,
    human: Human = False,
):
    cfg, store, token = session(root, human)
    workflow, organization = load_workflow(root / ".spado/catalog", cfg.workflow)
    scope = workflow.resolve_scope(target_scope(phase, subphase))
    workflow.select(scope)
    run = Run(
        project=cfg.project,
        workflow=workflow,
        organization=organization,
        objective=objective,
        scope=scope,
        mode=mode or cfg.mode,
    )
    typer.echo(dump({"run": store.create_run(token, run)}))


@workflow_app.command("context")
@guarded
def context(
    run_id: RunId = None,
    phase: Annotated[str | None, typer.Option("--phase", help="Phase slug or numeric ID.")] = None,
    subphase: Annotated[
        str | None, typer.Option("--subphase", help="Subphase slug or numeric ID.")
    ] = None,
    activity: str | None = None,
    root: Root = Path("."),
    human: Human = False,
):
    _, store, token = session(root, human)
    run, actor = store.load(token, select_run(store, token, run_id))
    if activity:
        if phase or subphase:
            raise ValueError("Activity and phase/subphase selectors are mutually exclusive")
        subphase = run.activities[activity].subphase
    selected = run.workflow.select(target_scope(phase, subphase))
    if actor.level in {"officer", "specialist"}:
        if (phase or subphase) and not set(selected).issubset(actor.subphases):
            raise PermissionError("Requested context exceeds the assigned scope")
        selected = [s for s in selected if s in actor.subphases]
    agent_ids = {"CAOAO"}
    for sid in selected:
        agent_ids.update(
            run.workflow.subphases[sid].owners + run.workflow.subphases[sid].specialists
        )
    visible = {
        rid: r.model_dump()
        for rid, r in run.revisions.items()
        if rid in run.official.values()
        or actor.level in {"human", "orchestrator"}
        or r.subphase in actor.subphases
    }
    typer.echo(
        dump(
            {
                "run": run.id,
                "run_version": run.version,
                "objective": run.objective,
                "scope": run.scope.model_dump(),
                "actor": actor.model_dump(),
                "rules": run.workflow.rules_content,
                "agents": {a: run.organization.agents[a].model_dump() for a in agent_ids},
                "subphases": [
                    {
                        "definition": run.workflow.subphases[s].model_dump(),
                        "mode": run.effective_mode(s),
                        "missing_inputs": missing_inputs(run, s),
                        "instances": [
                            a.model_dump() for a in run.activities.values() if a.subphase == s
                        ],
                    }
                    for s in selected
                ],
                "revisions": visible,
                "phase_plans": {
                    p: plan.model_dump()
                    for p, plan in run.phase_plans.items()
                    if any(run.workflow.subphases[s].phase == p for s in selected)
                },
            }
        )
    )


def record_request(root: Path, request: dict, run_id: str | None, human=False) -> dict:
    _, store, token = session(root, human)
    selected = select_run(store, token, run_id)
    payload = request["payload"]
    if isinstance(payload.get("phase"), str) or isinstance(payload.get("subphase"), str):
        run, _ = store.load(token, selected)
        payload = {**payload}
        if isinstance(payload.get("phase"), str):
            payload["phase"] = run.workflow.resolve_phase(payload["phase"])
        if isinstance(payload.get("subphase"), str):
            payload["subphase"] = run.workflow.resolve_subphase(payload["subphase"])
    if request["kind"] != "document":
        _sync_changed(root, store, token, selected)
    return store.record(
        token,
        selected,
        request["kind"],
        payload,
        request["rationale"],
        request["event_id"],
        request.get("expected_version"),
    )


@workflow_app.command("record")
@guarded
def record(
    request: Annotated[Path, typer.Option("--request")],
    run_id: RunId = None,
    root: Root = Path("."),
    human: Human = False,
):
    typer.echo(dump(record_request(root, json.loads(request.read_text()), run_id, human)))


@workflow_app.command("prepare")
@guarded
def prepare(
    request: Annotated[Path, typer.Option("--request")],
    run_id: RunId = None,
    root: Root = Path("."),
    human: Human = False,
):
    body = json.loads(request.read_text())
    if body.get("kind") != "prepare":
        raise ValueError("workflow prepare requires a prepare request")
    typer.echo(dump(record_request(root, body, run_id, human)))


@workflow_app.command("export")
@guarded
def export_run(run_id: RunId = None, root: Root = Path("."), human: Human = False):
    _, store, token = session(root, human)
    run, actor = store.load(token, select_run(store, token, run_id))
    authorize(run, actor, coordinator=True)
    typer.echo(dump({"run": run.model_dump(mode="json"), "events": store.events(token, run.id)}))


@workflow_app.command("validate")
@guarded
def validate_catalog(catalog: Annotated[Path | None, typer.Option("--catalog")] = None):
    workflow, organization = load_workflow(catalog or config.default_catalog())
    typer.echo(
        dump(
            {
                "workflow": workflow.id,
                "phases": len(workflow.phases),
                "subphases": len(workflow.subphases),
                "agents": len(organization.agents),
                "phase_slugs": {phase.id: phase.slug for phase in workflow.phases},
                "subphase_slugs": {
                    sid: subphase.slug for sid, subphase in workflow.subphases.items()
                },
            }
        )
    )


@workflow_app.command("render")
@guarded
def render_catalog(catalog: Annotated[Path | None, typer.Option("--catalog")] = None):
    typer.echo(render_workflow(catalog or config.default_catalog()), nl=False)


@guarded
def show_status(run_id: RunId = None, root: Root = Path("."), human: Human = False):
    _, store, token = session(root, human)
    if not run_id:
        runs = store.list_runs(token)
        if len(runs) != 1:
            typer.echo(dump({"runs": runs, "selection_required": len(runs) > 1}))
            return
        run_id = runs[0]["id"]
    run, actor = store.load(token, run_id)
    authorize(run, actor, coordinator=True)
    typer.echo(dump(status(run)))


@guarded
def show_review(
    target: Annotated[str, typer.Argument()] = "all",
    identifier: Annotated[str | None, typer.Argument()] = None,
    run_id: RunId = None,
    root: Root = Path("."),
    human: Human = False,
):
    _, store, token = session(root, human)
    run, actor = store.load(token, select_run(store, token, run_id))
    if target not in {"all", "phase", "subphase", "activity"}:
        raise ValueError("Review target must be all, phase, subphase or activity")
    if target != "all" and not identifier:
        raise ValueError("Specify a target ID")
    scope = Scope() if target in {"all", "activity"} else Scope(kind=target, id=identifier)
    selected = (
        [run.activities[identifier].subphase]
        if target == "activity"
        else run.workflow.select(scope)
    )
    if actor.level in {"officer", "specialist"} and not set(selected).issubset(actor.subphases):
        raise PermissionError(
            "Requested review exceeds delegated scope; use CAOAO for consolidation"
        )
    from spado.install.filesystem import FileSystem
    from spado.runtime.install import sha

    findings = review(run, scope, identifier if target == "activity" else None)
    for revision in run.latest_revisions().values():
        if revision.subphase is not None and revision.subphase not in selected:
            continue
        path = FileSystem(root).path(revision.path)
        if not path.is_file() or sha(path.read_bytes()) != revision.digest:
            findings.append(
                {
                    "severity": "warning",
                    "code": "external_document_change",
                    "path": revision.path,
                    "action": "Synchronize and review impact before execution",
                }
            )
    typer.echo(
        dump(
            {
                "run": run.id,
                "findings": findings,
                "semantic_review": "Requires the responsible agents to inspect the cited evidence",
                "persisted": False,
            }
        )
    )


@docs_app.command("sync")
@guarded
def sync_document(
    path: Path,
    run_id: RunId = None,
    subphase: Annotated[
        str | None, typer.Option("--subphase", help="Subphase slug or numeric ID.")
    ] = None,
    depends: Annotated[list[str] | None, typer.Option("--depends")] = None,
    root: Root = Path("."),
    human: Human = False,
):
    from spado.install.filesystem import FileSystem

    source = FileSystem(root).path(path.as_posix())
    if (
        source.suffix.lower() not in {".md", ".txt", ".rst", ".json"}
        or ".spado/local" in path.as_posix()
    ):
        raise ValueError("Only project documentation files can be synchronized")
    request = {
        "kind": "document",
        "payload": {
            "path": path.as_posix(),
            "content": source.read_text(),
            "subphase": subphase,
            "dependencies": depends or [],
        },
        "event_id": uid(),
        "rationale": "Synchronize project documentation and check recorded consumers",
    }
    typer.echo(dump(record_request(root, request, run_id, human)))


@docs_app.command("promote")
@guarded
def promote_document(
    revision: str, run_id: RunId = None, root: Root = Path("."), human: Human = False
):
    from spado.install.filesystem import FileSystem
    from spado.runtime.install import sha

    _, store, token = session(root, human)
    run, _ = store.load(token, select_run(store, token, run_id))
    document = run.revisions[revision]
    if sha(FileSystem(root).path(document.path).read_bytes()) != document.digest:
        raise ValueError("Document file differs from this revision; synchronize before promotion")
    typer.echo(
        dump(
            record_request(
                root,
                {
                    "kind": "promote",
                    "payload": {"revision": revision},
                    "event_id": uid(),
                    "rationale": "Promote reviewed evidence to official project context",
                },
                run.id,
                human,
            )
        )
    )


@docs_app.command("index")
@guarded
def index_documents(run_id: RunId = None, root: Root = Path("."), human: Human = False):
    from spado.runtime.embeddings import Embedder, index

    cfg, store, token = session(root, human)
    typer.echo(
        dump(index(store, token, select_run(store, token, run_id), Embedder(cfg.embeddings)))
    )


@docs_app.command("search")
@guarded
def search_documents(
    query: str, run_id: RunId = None, root: Root = Path("."), human: Human = False
):
    from spado.runtime.embeddings import Embedder, search

    cfg, store, token = session(root, human)
    typer.echo(
        dump(
            search(store, token, select_run(store, token, run_id), Embedder(cfg.embeddings), query)
        )
    )


@guarded
def serve_ui(
    root: Root = Path("."),
    port: Annotated[int, typer.Option("--port", help="Local port (127.0.0.1 only).")] = 8765,
    demo: Annotated[
        bool, typer.Option("--demo", help="Serve a synthetic run instead of the project database.")
    ] = False,
    demo_step: Annotated[
        float,
        typer.Option("--demo-step", help="Seconds between revealed demo events; 0 shows all."),
    ] = 2.0,
    transcripts: Annotated[
        Path | None,
        typer.Option("--transcripts", help="Claude Code transcript folder for this project."),
    ] = None,
    use_transcripts: Annotated[
        bool,
        typer.Option(
            "--transcripts-enabled/--no-transcripts", help="Read local Claude Code transcripts."
        ),
    ] = True,
    browser: Annotated[
        bool, typer.Option("--browser/--no-browser", help="Open the web app in a browser.")
    ] = True,
):
    """Open a read-only web view of runs: organization, communication, documents and database."""
    import webbrowser

    from spado.ui.server import make_server
    from spado.ui.source import PostgresSource

    if demo:
        from spado.ui.demo import DemoSource

        source = DemoSource(config.default_catalog(), step=demo_step)
    else:
        source = PostgresSource(root, transcripts, use_transcripts)
    server = make_server(source, port)
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    typer.echo(f"spado ui ({source.label}) on {url} — read-only; Ctrl+C to stop", err=True)
    if browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def register(app: typer.Typer):
    app.command("ui")(serve_ui)
    app.command("init")(initialize)
    app.command("status")(show_status)
    app.command("review")(show_review)
    app.add_typer(workflow_app, name="workflow")
    app.add_typer(database_app, name="db")
    app.add_typer(actor_app, name="actor")
    app.add_typer(docs_app, name="docs")
