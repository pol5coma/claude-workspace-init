"""`cwi init` orchestration: SCAN → MODEL → RECOMMEND → SELECT → PLAN → DIFF → CONFIRM → APPLY → VALIDATE → CLEAN."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from rich.console import Console

from cwi import __version__, paths
from cwi.catalog.loader import load_catalog
from cwi.claude_md.docs import architecture_is_template
from cwi.claude_md.generator import DOCS_ARCHITECTURE
from cwi.domain.enums import InitStage
from cwi.domain.errors import CWIError, UserCancelled
from cwi.domain.models import Catalog, CWIState, InstallationPlan
from cwi.install.executor import execute_plan
from cwi.install.filesystem import FileSystem
from cwi.planning.cleanup import template_gate
from cwi.planning.planner import PlanInputs, build_plan, find_decisions
from cwi.scanner.scanner import scan_project
from cwi.state.hashing import sha256_file
from cwi.state.repository import StateRepository
from cwi.ui import render, screens
from cwi.ui.prompts import AutoPrompter, InquirerPrompter, Prompter

log = logging.getLogger("cwi")


@dataclass
class InitOptions:
    root: Path | None = None
    catalog: Path | None = None
    dry_run: bool = False
    yes: bool = False
    verbose: bool = False
    prompter: Prompter | None = None
    console: Console | None = None
    filesystem_factory: object | None = None  # tests: callable(root) -> FileSystem
    now: str | None = None
    cwd: Path | None = None
    launcher: Callable[[str, list[str]], object] | None = None  # tests: replaces os.execvp
    which: Callable[[str], str | None] | None = None  # tests: replaces shutil.which


@dataclass
class InitOutcome:
    stage: InitStage
    plan: InstallationPlan | None = None
    applied: bool = False
    messages: list[str] = field(default_factory=list)


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _git(args: list[str], cwd: Path) -> str | None:
    """Read-only git queries. Never executes repository code."""
    try:
        result = subprocess.run(
            ["git", *args], cwd=cwd, capture_output=True, text=True, timeout=10, check=False
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout if result.returncode == 0 else None


def discover_git_root(cwd: Path) -> Path | None:
    out = _git(["rev-parse", "--show-toplevel"], cwd)
    return Path(out.strip()).resolve() if out and out.strip() else None


def dirty_files(root: Path) -> list[str]:
    out = _git(["status", "--porcelain"], root)
    return [line for line in (out or "").splitlines() if line.strip()]


def load_catalog_source(root: Path, explicit: Path | None) -> Catalog | None:
    if explicit is not None:
        return load_catalog(explicit.resolve())
    local = root / paths.rel(paths.CATALOG_DIR)
    if local.is_dir():
        return load_catalog(local.resolve())
    return None


def modified_managed_files(root: Path, state: CWIState | None) -> list[str]:
    if state is None:
        return []
    changed = []
    for rel, record in sorted(state.managed_files.items()):
        path = root / rel
        if not path.is_file():
            changed.append(f"{rel} (missing)")
        elif sha256_file(path) != record.sha256:
            changed.append(rel)
    return changed


def _make_prompter(options: InitOptions) -> Prompter:
    if options.prompter is not None:
        return options.prompter
    if options.yes or options.dry_run or not sys.stdin.isatty():
        return AutoPrompter()
    return InquirerPrompter()


def run_init(options: InitOptions) -> InitOutcome:
    console = options.console or Console()
    prompter = _make_prompter(options)
    render.header(console, __version__)

    render.stage(console, 1)
    # Discover root ------------------------------------------------------------------------------
    cwd = (options.cwd or Path.cwd()).resolve()
    if options.root is not None:
        root = options.root.expanduser().resolve()
    else:
        root = screens.choose_root(console, prompter, cwd, discover_git_root(cwd))
    if not root.is_dir():
        raise CWIError(f"Project root does not exist: {root}")
    log.debug("root: %s", root)
    console.print(f"[dim]Workspace: {root}[/dim]")
    if not options.dry_run:
        screens.dirty_tree_notice(
            console, prompter, dirty_files(root) if discover_git_root(root) else []
        )

    # Load state and catalog (fail before any mutation) ------------------------------------------
    state = StateRepository(root).load()
    catalog = load_catalog_source(root, options.catalog)
    if catalog is not None:
        render.step(
            console, f"Catalog loaded: {len(catalog.capabilities)} capabilities ({catalog.root})"
        )
    if state is not None:
        render.step(
            console, f"Existing CWI workspace detected (initialized {state.initialized_at})"
        )
        for rel in modified_managed_files(root, state):
            render.warning(console, f"Modified CWI-managed file: {rel}")
    if catalog is None:
        if state is not None:
            console.print(
                "[yellow]Catalog source unavailable in this repository.[/yellow]\n"
                "  Available: inspect workspace, update CLAUDE.md, validate managed resources.\n"
                "  Capability additions require a CWI catalog source (pass --catalog PATH)."
            )
        else:
            render.warning(
                console,
                "No CWI catalog found (catalog/ or --catalog). Only CLAUDE.md can be configured.",
            )

    render.stage(console, 2)
    # Scan + profile --------------------------------------------------------------------------------
    with console.status("Scanning project…"):
        scan = scan_project(root)
    render.step(
        console,
        "Project scanned" + (" (no existing application)" if not scan.meaningful_project else ""),
    )

    def rescan():
        with console.status("Rescanning project…"):
            return scan_project(root)

    render.stage(console, 3)
    profile = screens.resolve_profile(console, prompter, root, scan, state, rescan)
    stage = InitStage.PROFILE_CONFIRMED

    # CLAUDE.md ------------------------------------------------------------------------------------
    render.stage(console, 4)
    claude_md, profile = screens.configure_claude_md(
        console, prompter, root, profile, state, scan.architecture_docs
    )
    stage = InitStage.CLAUDE_MD_CONFIGURED

    # Cleanup choices ------------------------------------------------------------------------------
    is_template, _ = template_gate(root)
    cleanup_template = False
    cleanup_catalog = False
    if is_template:
        cleanup_template = prompter.confirm(
            "cleanup.template",
            "This is the CWI template. After a successful init, remove CWI bootstrap files "
            "(catalog/, templates/, src/cwi/, tests/, pyproject.toml, uv.lock, spec docs)?",
            default=True,
        )
    elif (
        catalog is not None
        and catalog.root.resolve() == (root / paths.rel(paths.CATALOG_DIR)).resolve()
    ):
        cleanup_catalog = prompter.confirm(
            "cleanup.catalog",
            "Remove the unused CWI catalog/ after a successful init?",
            default=True,
        )

    # Selection → plan → preview loop ---------------------------------------------------------------
    previous_selection: list[str] | None = None
    while True:
        render.stage(console, 5)
        if catalog is not None:
            raw = screens.select_capabilities(
                console, prompter, catalog, profile, state, previous_selection
            )
            selected = screens.resolve_selection(console, prompter, catalog, raw)
            previous_selection = selected
            render.step(console, f"{len(selected)} capabilities selected")
        else:
            selected = list(state.selected_capabilities) if state else []
        stage = InitStage.CAPABILITIES_SELECTED

        inputs = PlanInputs(
            root=root,
            profile=profile,
            catalog=catalog,
            state=state,
            claude_md=claude_md,
            selected=selected,
            cleanup_template=cleanup_template,
            cleanup_catalog=cleanup_catalog,
            now=options.now or _utc_now(),
        )
        for _ in range(10):
            decisions = find_decisions(inputs)
            if not decisions:
                break
            inputs.resolutions.update(screens.resolve_decisions(console, prompter, root, decisions))
        plan = build_plan(inputs)
        stage = InitStage.PLAN_READY
        render.stage(console, 6)

        if options.dry_run:
            render.plan_summary(console, plan, catalog)
            if plan.env_requirements:
                render.env_requirements(console, plan.env_requirements, catalog)
            render.operations_table(console, plan)
            render.diffs(console, plan, root)
            render.success(console, plan, dry_run=True)
            return InitOutcome(stage=stage, plan=plan)

        if not prompter.interactive and not options.yes and options.prompter is None:
            render.plan_summary(console, plan, catalog)
            console.print(
                "[yellow]Non-interactive terminal: nothing applied. Re-run with --yes to apply.[/yellow]"
            )
            return InitOutcome(stage=stage, plan=plan)

        choice = screens.preview(console, prompter, plan, root, catalog)
        if choice == "noop":
            render.success(console, plan)
            _finish_with_next_steps(console, prompter, options, root, plan)
            return InitOutcome(stage=InitStage.COMPLETE, plan=plan)
        if choice == "back":
            if catalog is None:
                render.note(console, "No catalog available: capability selection cannot change.")
            continue
        if choice == "cancel":
            raise UserCancelled("Cancelled before apply. No changes were made.")
        break

    # Apply -------------------------------------------------------------------------------------------
    factory = options.filesystem_factory or FileSystem
    fs = factory(root)  # type: ignore[operator]
    render.stage(console, 7)
    with console.status("Applying workspace configuration…") as status:

        def progress(done: int, total: int, op) -> None:
            status.update(f"Applying {done}/{total} · {op.target}")

        execute_plan(plan, root, fs, progress=progress)
    render.step(console, "Workspace validated")
    if plan.cleanup_template or any(op.owner == "cwi-catalog" for op in plan.operations):
        render.step(console, "CWI catalog and bootstrap resources removed")
    render.success(console, plan)
    if plan.env_requirements:
        names = sorted({r.name for reqs in plan.env_requirements.values() for r in reqs})
        render.note(console, "Remember to set: " + ", ".join(names))
    if plan.cleanup_template:
        render.note(
            console,
            "CWI's own source was removed from this project. Keep using `cwi` via `uv tool install` "
            "if you want to re-run it later.",
        )
    _finish_with_next_steps(console, prompter, options, root, plan)
    return InitOutcome(stage=InitStage.COMPLETE, plan=plan, applied=True)


# ---------------------------------------------------------------------------------------------
# After the install: the order in which to use the workflow skills
# ---------------------------------------------------------------------------------------------

KICKOFF = ("skill:kickoff", "kickoff")
DISCOVERY = ("skill:project-discovery", "project-discovery")
SPEC = ("skill:feature-spec", "feature-spec")
WORKFLOW = ("skill:feature-workflow", "feature-workflow")


def architecture_pending(root: Path, profile) -> bool:
    """No architecture doc yet, or it is still the CWI template."""
    return architecture_is_template(root / (profile.architecture_doc or DOCS_ARCHITECTURE))


def next_steps(root: Path, plan: InstallationPlan) -> tuple[list[tuple[str, str, str]], str | None]:
    selected = set(plan.state.selected_capabilities)
    pending = architecture_pending(root, plan.profile)
    steps: list[tuple[str, str, str]] = []
    if DISCOVERY[0] in selected:
        steps.append(
            (
                "next" if pending else "done",
                DISCOVERY[1],
                "Define the architecture: point to it, analyze the code, or build it from requirements.",
            )
        )
    if SPEC[0] in selected:
        steps.append(
            (
                "later" if pending and DISCOVERY[0] in selected else "next",
                SPEC[1],
                "Write the spec of each feature: acceptance criteria and open questions.",
            )
        )
    if WORKFLOW[0] in selected:
        steps.append(
            (
                "later",
                WORKFLOW[1],
                "Implement a feature from its spec: plan, test-first slices, review.",
            )
        )
    if KICKOFF[0] in selected and steps:
        # One entry point: kickoff checks the project state and runs the steps below in order.
        return steps, f'claude "/{KICKOFF[1]}"'
    first = next((skill for status, skill, _ in steps if status == "next"), None)
    return steps, (f'claude "/{first}"' if first else None)


def _finish_with_next_steps(
    console: Console, prompter: Prompter, options: InitOptions, root: Path, plan: InstallationPlan
) -> None:
    steps, command = next_steps(root, plan)
    if not steps:
        return
    render.stage(console, 8)
    render.next_steps(console, steps, command)
    which = options.which or shutil.which
    can_launch = (
        command is not None
        and prompter.interactive
        and not options.yes
        and not options.dry_run
        and which("claude") is not None
    )
    if not can_launch:
        return
    skill = command.split("/", 1)[1].rstrip('"')
    if prompter.confirm("launch", f"Open Claude Code now and start {skill}?", default=True):
        console.file.flush()
        launcher = options.launcher or os.execvp
        launcher("claude", ["claude", f"/{skill}"])
