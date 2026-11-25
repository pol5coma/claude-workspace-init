from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from spado.runtime.commands import guarded
from spado.runtime.config import dump
from spado.sdd import engine
from spado.sdd.models import Feature, Report
from spado.sdd.store import read, snapshot

app = typer.Typer(help="Human-directed SDD; manual phases or supervised execution of one feature.")


def emit(value):
    typer.echo(dump(value))


@app.command("start")
@guarded
def start(slug: str, root: Path = Path("."), mode: str = "manual", feature: str | None = None):
    emit(engine.start(root.resolve(), slug, mode, feature))


@app.command("status")
@guarded
def status(root: Path = Path(".")):
    emit(read(root.resolve()).model_dump())


@app.command("context")
@guarded
def context(root: Path = Path(".")):
    root = root.resolve()
    state = read(root)
    emit(
        {
            "state": state.model_dump(),
            "snapshot": snapshot(root),
            "protocol": (root / ".workflow/PROTOCOL.md").read_text(),
            "report_schema": Report.model_json_schema(),
        }
    )


@app.command("begin")
@guarded
def begin(phase: str, root: Path = Path("."), milestone: int | None = None):
    engine.begin(root.resolve(), phase, milestone)
    status(root)


@app.command("check")
@guarded
def check(root: Path = Path("."), baseline: bool = False):
    result = engine.check(root.resolve(), baseline)
    emit(result)
    if not result["passed"]:
        raise typer.Exit(1)


@app.command("submit")
@guarded
def submit(report: Annotated[Path, typer.Option()], root: Path = Path(".")):
    engine.submit(root.resolve(), Report.model_validate_json(report.read_text()))
    status(root)


@app.command("approve")
@guarded
def approve(
    response: str = typer.Option(...),
    root: Path = Path("."),
    continue_roadmap: bool = typer.Option(False, "--continue-roadmap"),
    host: str | None = typer.Option(None, "--host"),
):
    # Delegated approval intentionally is not exposed as a command-line escape hatch.
    root = root.resolve()
    before = read(root).active
    if continue_roadmap and (
        not host
        or not before
        or before.mode != "supervised"
        or before.phase != "close"
        or not before.feature_id
        or before.status != "awaiting_review"
    ):
        raise ValueError(
            "--continue-roadmap requires --host and final acceptance of a supervised product feature"
        )
    engine.approve(root, response)
    if not continue_roadmap:
        status(root)
        return
    item = engine.next_product_feature(root)
    if not item:
        emit({"status": "product_complete"})
        return
    engine.start(root, item["slug"], "supervised", item["id"])
    from spado.sdd.runner import run_feature

    emit(run_feature(root, host))


@app.command("pause")
@guarded
def pause(reason: str = typer.Option(...), root: Path = Path(".")):
    engine.pause(root.resolve(), reason)
    status(root)


@app.command("reopen")
@guarded
def reopen(phase: str, reason: str = typer.Option(...), root: Path = Path(".")):
    engine.reopen(root.resolve(), phase, reason)
    status(root)


@app.command("recover")
@guarded
def recover(root: Path = Path(".")):
    emit(engine.recover(root.resolve()))


@app.command("product-submit")
@guarded
def product_submit(proposal: Annotated[Path, typer.Option()], root: Path = Path(".")):
    data = json.loads(proposal.read_text())
    engine.product_submit(
        root.resolve(), [Feature.model_validate(f) for f in data["features"]], data["sources"]
    )
    status(root)


@app.command("product-approve")
@guarded
def product_approve(response: str = typer.Option(...), root: Path = Path(".")):
    engine.product_approve(root.resolve(), response)
    status(root)


@app.command("run")
@guarded
def run(
    host: str = typer.Option(...),
    root: Path = Path("."),
    roadmap: bool = typer.Option(False, "--roadmap"),
):
    """Execute one explicitly delegated feature, stopping before Human final acceptance."""
    from spado.sdd.runner import run_feature

    root = root.resolve()
    if roadmap and (not read(root).active or read(root).active.status == "complete"):
        item = engine.next_product_feature(root)
        if not item:
            emit({"status": "product_complete"})
            return
        engine.start(root, item["slug"], "supervised", item["id"])
    emit(run_feature(root, host))


@app.command("hook", hidden=True)
def hook(root: Path = Path("."), host: str = "claude"):
    from spado.sdd.hooks import main

    main(root.resolve(), host)
