"""Rich renderers. Pure presentation: no prompts, no filesystem mutation."""

from __future__ import annotations

from pathlib import Path

from rich.console import Console, Group
from rich.panel import Panel
from rich.rule import Rule
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from cwi.domain.enums import SELECTION_ORDER, CapabilityType, OperationType
from cwi.domain.models import (
    Capability,
    Catalog,
    EnvRequirement,
    InstallationPlan,
    ProjectProfile,
    Recommendation,
    ScanResult,
    SizeReport,
)
from cwi.planning.diff import operation_diff, reviewable

CHECK = "[green]✓[/green]"
WARN = "[yellow]![/yellow]"


def header(console: Console, version: str) -> None:
    console.print(
        Panel.fit(
            Text.assemble(("Claude Workspace Init", "bold"), ("  v" + version, "dim")),
            subtitle="Start with everything available. Finish with only what the project needs.",
            border_style="cyan",
        )
    )


def step(console: Console, message: str) -> None:
    console.print(f"{CHECK} {message}")


def note(console: Console, message: str) -> None:
    console.print(f"[dim]{message}[/dim]")


def warning(console: Console, message: str) -> None:
    console.print(f"{WARN} {message}")


def _confidence_mark(confidence: float) -> str:
    if confidence >= 0.8:
        return ""
    if confidence >= 0.5:
        return " [dim](medium confidence)[/dim]"
    return " [yellow](uncertain)[/yellow]"


def scan_summary(console: Console, scan: ScanResult) -> None:
    lines: list[str] = [f"[bold]Type[/bold]\n  {scan.project_type.label}"]
    if scan.project_type_reason:
        lines[0] += f" [dim]· {scan.project_type_reason}[/dim]"
    if scan.monorepo:
        lines.append(
            "[bold]Monorepo[/bold]\n  " + ", ".join(scan.subprojects or ["workspaces detected"])
        )
    for group, items in scan.stack.items():
        lines.append(f"[bold]{group}[/bold]\n" + "\n".join(f"  {i}" for i in items))
    if scan.test_tools:
        lines.append(
            "[bold]Testing[/bold]\n"
            + "\n".join(f"  {d.value}{_confidence_mark(d.confidence)}" for d in scan.test_tools)
        )
    uncertain = [d for d in [*scan.databases, *scan.infrastructure] if d.confidence < 0.5]
    if uncertain:
        lines.append(
            "[bold]Possible[/bold]\n"
            + "\n".join(f"  {d.value}{_confidence_mark(d.confidence)}" for d in uncertain)
        )
    if scan.existing_claude.any:
        found = []
        ec = scan.existing_claude
        if ec.claude_md:
            found.append("CLAUDE.md")
        if ec.settings:
            found.append(".claude/settings.json")
        if ec.mcp:
            found.append(".mcp.json")
        if ec.skills:
            found.append(f"{len(ec.skills)} skill(s)")
        if ec.agents:
            found.append(f"{len(ec.agents)} agent(s)")
        if ec.rules:
            found.append(".claude/rules/")
        lines.append(
            "[bold]Existing Claude configuration[/bold]\n  "
            + ", ".join(found)
            + " [dim](preserved)[/dim]"
        )
    console.print(
        Panel("\n\n".join(lines), title="Detected project", border_style="cyan", expand=False)
    )


def evidence(console: Console, scan: ScanResult) -> None:
    table = Table(title="Scan evidence", show_lines=False, expand=False)
    table.add_column("Category", style="bold")
    table.add_column("Value")
    table.add_column("Confidence")
    table.add_column("Evidence", style="dim")
    for category, detections in scan.all_detections().items():
        for d in detections:
            table.add_row(category, d.value, d.confidence_label, d.source)
    for cmd in scan.commands:
        table.add_row(
            "Command",
            f"{cmd.group} · {cmd.label}: {cmd.command}",
            "detected" if cmd.detected else "suggested",
            cmd.source,
        )
    if scan.signals:
        table.add_row("Project", "meaningful project", "", "; ".join(scan.signals))
    console.print(table)


def profile(console: Console, prof: ProjectProfile, title: str = "Project profile") -> None:
    lines = [f"[bold]{prof.project_type.label}[/bold]" + (" · monorepo" if prof.monorepo else "")]
    for group, items in (prof.stack or {}).items():
        if items:
            lines.append(f"[bold]{group}[/bold]: " + ", ".join(items))
    if prof.test_tools:
        lines.append("[bold]Testing[/bold]: " + ", ".join(prof.test_tools))
    if prof.tools:
        lines.append("[bold]Tooling[/bold]: " + ", ".join(prof.tools))
    if prof.commands:
        lines.append("[bold]Commands[/bold]")
        for cmd in prof.commands:
            tag = "" if cmd.detected else " [dim](suggested)[/dim]"
            lines.append(f"  {cmd.group} · {cmd.label}: [cyan]{cmd.command}[/cyan]{tag}")
    if prof.architecture_doc:
        lines.append(f"[bold]Architecture docs[/bold]: {prof.architecture_doc}")
    console.print(Panel("\n".join(lines), title=title, border_style="cyan", expand=False))


def commands_table(console: Console, prof: ProjectProfile) -> None:
    table = Table(title="Essential commands", expand=False)
    table.add_column("Group")
    table.add_column("Purpose")
    table.add_column("Command", style="cyan")
    table.add_column("Status")
    table.add_column("Source", style="dim")
    for cmd in prof.commands:
        table.add_row(
            cmd.group,
            cmd.label,
            cmd.command,
            "Detected" if cmd.detected else "Suggested",
            cmd.source,
        )
    console.print(table)


def claude_md_preview(console: Console, content: str, size: SizeReport) -> None:
    console.print(
        Panel(
            Syntax(content, "markdown", word_wrap=True), title="CLAUDE.md (proposed)", expand=False
        )
    )
    style = {"compact": "green", "review": "yellow", "large": "red"}[size.verdict]
    mark = "✓" if size.verdict == "compact" else "!"
    console.print(
        f"[bold]CLAUDE.md[/bold]  {size.lines} lines · ~{size.estimated_tokens} estimated tokens  "
        f"[{style}]{mark} {size.message}[/{style}]"
    )


def capability_table(
    console: Console,
    cap_type: CapabilityType,
    caps: list[Capability],
    recs: dict[str, Recommendation],
    installed: set[str],
) -> None:
    table = Table(
        title=f"{cap_type.title} available in catalog/{cap_type.plural}/",
        expand=False,
        show_lines=False,
    )
    table.add_column("Capability", style="bold")
    table.add_column("Description")
    table.add_column("Why", style="green")
    for cap in caps:
        rec = recs.get(cap.ref)
        why_parts = []
        if cap.ref in installed:
            why_parts.append("installed")
        if rec and rec.preselected:
            why_parts.append(("Recommended: " + rec.reason_text) if rec.reasons else "Recommended")
        deps = ", ".join(d.split(":", 1)[1] for d in cap.manifest.dependencies)
        description = cap.manifest.description + (f" [dim](requires {deps})[/dim]" if deps else "")
        table.add_row(cap.id, description, "; ".join(why_parts))
    console.print(table)


def env_requirements(
    console: Console, env: dict[str, list[EnvRequirement]], catalog: Catalog | None
) -> None:
    for ref, reqs in env.items():
        name = catalog.get(ref).manifest.name if catalog and catalog.get(ref) else ref
        body = "\n".join(
            f"  [bold]{r.name}[/bold]" + (f"  [dim]{r.description}[/dim]" if r.description else "")
            for r in reqs
        )
        console.print(
            Panel(
                f"Required:\n{body}\n\nCWI configures the reference only. No secret is stored by CWI.\n"
                "Add it to your local environment before using the integration.",
                title=f"{name} requires",
                border_style="yellow",
                expand=False,
            )
        )


def plan_summary(console: Console, plan: InstallationPlan, catalog: Catalog | None) -> None:
    console.print(Rule("Claude Workspace Plan"))
    lines: list[str] = [f"[bold]Project[/bold]\n  {plan.profile.summary()}"]
    if plan.claude_md_mode is not None:
        touched = any(op.target == "CLAUDE.md" for op in plan.operations)
        mode = plan.claude_md_mode.value.upper()
        if not touched:
            mode = "UNCHANGED" if mode not in ("SKIP", "KEEP") else mode
        lines.append(f"[bold]CLAUDE.md[/bold]\n  {mode}")

    by_type: dict[CapabilityType, list[str]] = {t: [] for t in SELECTION_ORDER}
    for ref in plan.selected_capabilities:
        kind = CapabilityType(ref.split(":", 1)[0])
        cid = ref.split(":", 1)[1]
        marker = "[green]+[/green]" if ref in plan.added_capabilities else "[dim]=[/dim]"
        by_type[kind].append(f"  {marker} {cid}")
    for ref in plan.removed_capabilities:
        kind = CapabilityType(ref.split(":", 1)[0])
        by_type[kind].append(f"  [red]-[/red] {ref.split(':', 1)[1]}")
    for kind in (
        CapabilityType.SKILL,
        CapabilityType.AGENT,
        CapabilityType.SCRIPT,
        CapabilityType.HOOK,
        CapabilityType.MCP,
    ):
        if by_type[kind]:
            lines.append(f"[bold]{kind.title}[/bold]\n" + "\n".join(by_type[kind]))

    counts = plan.counts()
    lines.append(
        "[bold]Files[/bold]\n"
        f"  CREATE  {counts['create']}\n  UPDATE  {counts['update']}\n  DELETE  {counts['delete']} CWI-owned"
    )
    cleanup = [
        op
        for op in plan.operations
        if op.owner in ("cwi-template", "cwi-catalog") and not op.only_if_empty
    ]
    if cleanup:
        lines.append(
            "[bold]Cleanup[/bold]\n"
            + "\n".join(
                f"  remove {op.target}{'/' if op.type == OperationType.DELETE_DIR else ''}"
                for op in cleanup
            )
        )
    if plan.warnings:
        lines.append(
            "[bold]Warnings[/bold]\n" + "\n".join(f"  [yellow]{w}[/yellow]" for w in plan.warnings)
        )
    console.print("\n\n".join(lines))
    console.print(Rule())


def operations_table(console: Console, plan: InstallationPlan) -> None:
    table = Table(title="Planned operations", expand=False)
    table.add_column("#", justify="right", style="dim")
    table.add_column("Action")
    table.add_column("Target")
    table.add_column("Owner", style="dim")
    table.add_column("Reason", style="dim")
    styles = {
        "mkdir": "dim",
        "copy": "green",
        "create": "green",
        "update": "yellow",
        "merge_json": "yellow",
        "delete": "red",
        "delete_dir": "red",
    }
    for i, op in enumerate(plan.operations, 1):
        action = op.type.value
        if op.type == OperationType.COPY and op.before_hash:
            action = "update"
        table.add_row(
            str(i),
            f"[{styles.get(op.type.value, '')}]{action.upper()}[/]",
            op.target,
            op.owner,
            op.reason,
        )
    console.print(table)


def diffs(console: Console, plan: InstallationPlan, root: Path, include_new: bool = False) -> None:
    shown = 0
    for op in plan.operations:
        if reviewable(op):
            text = operation_diff(root, op)
            console.print(
                Panel(Syntax(text, "diff", word_wrap=True), title=op.target, expand=False)
            )
            shown += 1
        elif op.type == OperationType.MKDIR:
            continue
        elif op.is_delete:
            console.print(f"[red]{operation_diff(root, op)}[/red]")
        elif op.before_hash is None:
            if include_new and op.after_content is not None:
                console.print(
                    Panel(
                        Syntax(
                            op.after_content, "markdown" if op.target.endswith(".md") else "json"
                        ),
                        title=f"NEW FILE {op.target}",
                        expand=False,
                    )
                )
            else:
                console.print(f"[green]NEW FILE[/green] {op.target}")
    if not shown:
        note(console, "No existing project file is modified by this plan.")


def success(console: Console, plan: InstallationPlan, dry_run: bool = False) -> None:
    if dry_run:
        console.print(
            Panel("Dry run complete. No files were written.", border_style="cyan", expand=False)
        )
        return
    if not plan.has_changes:
        console.print(
            Panel(
                "Workspace already up to date. Nothing to change.",
                border_style="green",
                expand=False,
            )
        )
        return
    tree = Group(
        Text("✓ Claude workspace initialized", style="bold green"),
        Text(
            f"{len(plan.selected_capabilities)} capabilities active · state recorded in .claude/cwi-state.json",
            style="dim",
        ),
    )
    console.print(Panel(tree, border_style="green", expand=False))


def error(console: Console, message: str) -> None:
    console.print(Panel(message, title="cwi init failed", border_style="red", expand=False))
