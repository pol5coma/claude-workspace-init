"""`cwi catalog`: author the template catalog (add, list, validate, remove).

These commands edit files under catalog/ in the local repository. They never commit or push:
new capabilities reach the GitHub template through a normal git commit.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table
from rich.tree import Tree

from cwi.authoring.builder import (
    HOOK_EVENTS,
    AuthoringError,
    BuiltCapability,
    Metadata,
    build_agent,
    build_hook,
    build_mcp,
    build_script,
    build_skill,
    parse_list,
    parse_pairs,
    parse_project_types,
)
from cwi.authoring.writer import remove_capability, write_capability
from cwi.catalog.loader import load_catalog
from cwi.domain.enums import ProjectType
from cwi.domain.errors import CatalogError, CWIError, UserCancelled
from cwi.ui.prompts import AutoPrompter, InquirerPrompter, Option, Prompter

catalog_app = typer.Typer(
    help="Author the CWI catalog of this template repository.", no_args_is_help=True
)
add_app = typer.Typer(help="Add a capability to the catalog.", no_args_is_help=True)
catalog_app.add_typer(add_app, name="add")

console = Console()

CatalogOpt = Annotated[Path, typer.Option("--catalog", help="Catalog directory.")]
IdOpt = Annotated[
    str | None,
    typer.Option("--id", help="Capability id (default: from the file/frontmatter name)."),
]
NameOpt = Annotated[str | None, typer.Option("--name", help="Display name shown in cwi init.")]
DescOpt = Annotated[
    str | None, typer.Option("--description", "-d", help="What it does and when to use it.")
]
DefaultOpt = Annotated[
    bool | None, typer.Option("--default/--no-default", help="Preselect it in every project.")
]
TypesOpt = Annotated[
    str | None,
    typer.Option(
        "--type",
        help="Recommend for these project types: " + ",".join(t.value for t in ProjectType),
    ),
]
TechOpt = Annotated[
    str | None,
    typer.Option(
        "--tech", help="Recommend when these technologies are detected (comma-separated)."
    ),
]
DependsOpt = Annotated[
    list[str] | None, typer.Option("--depends", help="Dependency as type:id (repeatable).")
]
ConflictsOpt = Annotated[
    list[str] | None, typer.Option("--conflicts", help="Conflict as type:id (repeatable).")
]
ForceOpt = Annotated[
    bool, typer.Option("--force", help="Replace an existing capability with the same reference.")
]
YesOpt = Annotated[
    bool, typer.Option("--yes", "-y", help="Do not ask questions; use flags and defaults.")
]
GroupOpt = Annotated[
    str | None,
    typer.Option(
        "--group",
        help="Family folder, e.g. development-agents. Agents install into .claude/agents/<group>/.",
    ),
]
GroupDefaultOpt = Annotated[
    str | None,
    typer.Option(
        "--group-default",
        help="Preselect it for these project types through its family (needs --group).",
    ),
]


def _prompter(yes: bool) -> Prompter:
    return AutoPrompter() if yes or not sys.stdin.isatty() else InquirerPrompter()


def _metadata(
    prompter: Prompter,
    *,
    cid: str | None,
    name: str | None,
    description: str | None,
    default: bool | None,
    types: str | None,
    tech: str | None,
    depends: list[str] | None,
    conflicts: list[str] | None,
    group: str | None = None,
    group_default: str | None = None,
    ask_recommendation: bool = True,
) -> Metadata:
    if group_default and not group:
        raise AuthoringError("--group-default needs --group")
    meta = Metadata(
        id=cid,
        name=name,
        description=description,
        default_selected=bool(default),
        project_types=parse_project_types(types),
        technologies=parse_list(tech),
        dependencies=list(depends or []),
        conflicts=list(conflicts or []),
        group=group,
        group_defaults=parse_project_types(group_default),
    )
    if not prompter.interactive or not ask_recommendation:
        return meta
    if default is None:
        meta.default_selected = prompter.confirm(
            "default", "Preselect it in every project (default)?", default=False
        )
    if not meta.default_selected and types is None:
        meta.project_types = [
            ProjectType(v)
            for v in prompter.checkbox(
                "types",
                "Recommend it for which project types? (none = only when selected manually)",
                [Option(t.value, t.label) for t in ProjectType],
            )
        ]
    if not meta.default_selected and tech is None:
        meta.technologies = parse_list(
            prompter.text(
                "tech",
                "Recommend it when these technologies are detected (comma-separated, optional):",
            )
        )
    return meta


def _ask_description(prompter: Prompter, meta: Metadata, what: str) -> None:
    if meta.description is None and prompter.interactive:
        value = prompter.text(
            "description", f"Describe the {what} (what it does and when to use it):"
        ).strip()
        meta.description = value or None


def _finish(
    catalog: Path, built: BuiltCapability, force: bool, meta: Metadata | None = None
) -> None:
    if meta is not None:
        built.group = meta.group
        built.group_defaults = list(meta.group_defaults)
    for warning in built.warnings:
        console.print(f"[yellow]! {warning}[/yellow]")
    target = write_capability(catalog, built, force=force)
    tree = Tree(f"[green]✓ Added {built.ref}[/green]  [dim]{target}[/dim]")
    for path in sorted(p.relative_to(target).as_posix() for p in target.rglob("*") if p.is_file()):
        tree.add(path)
    console.print(tree)
    rel = target.relative_to(Path.cwd()) if target.is_relative_to(Path.cwd()) else target
    console.print(
        f"[dim]Commit it to ship it with the template:[/dim]  git add {rel} && git commit -m 'catalog: add {built.ref}'"
    )


def _run(fn) -> None:
    try:
        fn()
    except UserCancelled as exc:
        console.print(f"[yellow]{exc}[/yellow]")
        raise typer.Exit(1) from None
    except CWIError as exc:
        console.print(f"[red]✗ {exc}[/red]")
        raise typer.Exit(1) from None


@add_app.command("skill")
def add_skill(
    path: Annotated[
        Path,
        typer.Argument(
            help="SKILL.md file, or a folder containing SKILL.md (+ references/, scripts/)."
        ),
    ],
    ref: Annotated[
        list[Path] | None, typer.Option("--ref", help="Reference file → references/ (repeatable).")
    ] = None,
    script: Annotated[
        list[Path] | None, typer.Option("--script", help="Helper script → scripts/ (repeatable).")
    ] = None,
    cid: IdOpt = None,
    name: NameOpt = None,
    description: DescOpt = None,
    default: DefaultOpt = None,
    types: TypesOpt = None,
    tech: TechOpt = None,
    depends: DependsOpt = None,
    conflicts: ConflictsOpt = None,
    group: GroupOpt = None,
    group_default: GroupDefaultOpt = None,
    exclude: Annotated[
        list[str] | None,
        typer.Option(
            "--exclude",
            help="Skip files/folders matching this pattern when copying a folder (repeatable), e.g. test.",
        ),
    ] = None,
    catalog: CatalogOpt = Path("catalog"),
    force: ForceOpt = False,
    yes: YesOpt = False,
) -> None:
    """Add a Skill (tools go in the SKILL.md frontmatter as `allowed-tools:`)."""

    def go() -> None:
        prompter = _prompter(yes)
        meta = _metadata(
            prompter,
            cid=cid,
            name=name,
            description=description,
            default=default,
            types=types,
            tech=tech,
            depends=depends,
            conflicts=conflicts,
            group=group,
            group_default=group_default,
        )
        built = build_skill(path, meta, ref or [], script or [], exclude=exclude or [])
        if built.agent_frontmatter and not prompter.interactive:
            raise AuthoringError(
                "This file has `tools:` in its frontmatter, so it is an agent definition. "
                f"Use: cwi catalog add agent {path}\n"
                "(Skills declare tools as `allowed-tools:`.)"
            )
        if built.warnings and prompter.interactive:
            for warning in built.warnings:
                console.print(f"[yellow]! {warning}[/yellow]")
            choice = prompter.select(
                "skill.agent_like",
                "Add it as?",
                [
                    Option("agent", "Agent (recommended)"),
                    Option("skill", "Skill, converting `tools` to `allowed-tools`"),
                    Option("cancel", "Cancel"),
                ],
                default="agent",
            )
            if choice == "cancel":
                raise UserCancelled("Cancelled. Nothing was added.")
            if choice == "agent":
                built = build_agent(
                    path if path.is_file() else path / "SKILL.md", meta, script or []
                )
            else:
                built = build_skill(
                    path, meta, ref or [], script or [], convert_tools=True, exclude=exclude or []
                )
        _finish(catalog, built, force, meta)

    _run(go)


@add_app.command("agent")
def add_agent(
    path: Annotated[
        Path, typer.Argument(help="Agent Markdown file with name/description frontmatter.")
    ],
    script: Annotated[
        list[Path] | None,
        typer.Option("--script", help="Helper script → .claude/scripts/<id>/ (repeatable)."),
    ] = None,
    cid: IdOpt = None,
    name: NameOpt = None,
    description: DescOpt = None,
    default: DefaultOpt = None,
    types: TypesOpt = None,
    tech: TechOpt = None,
    depends: DependsOpt = None,
    conflicts: ConflictsOpt = None,
    group: GroupOpt = None,
    group_default: GroupDefaultOpt = None,
    catalog: CatalogOpt = Path("catalog"),
    force: ForceOpt = False,
    yes: YesOpt = False,
) -> None:
    """Add an Agent (tools go in its frontmatter as `tools:`; optional `model:`)."""

    def go() -> None:
        meta = _metadata(
            _prompter(yes),
            cid=cid,
            name=name,
            description=description,
            default=default,
            types=types,
            tech=tech,
            depends=depends,
            conflicts=conflicts,
            group=group,
            group_default=group_default,
        )
        _finish(catalog, build_agent(path, meta, script or []), force, meta)

    _run(go)


@add_app.command("hook")
def add_hook(
    script: Annotated[
        Path, typer.Argument(help="Hook script (.py, .sh, .js…). Receives the hook JSON on stdin.")
    ],
    event: Annotated[str, typer.Option("--event", help="Hook event: " + ", ".join(HOOK_EVENTS))],
    matcher: Annotated[
        str | None,
        typer.Option(
            "--matcher", help="Tool matcher for Pre/PostToolUse, e.g. 'Bash' or 'Edit|Write'."
        ),
    ] = None,
    timeout: Annotated[int | None, typer.Option("--timeout", help="Timeout in seconds.")] = 30,
    support: Annotated[
        list[Path] | None,
        typer.Option(
            "--file", help="Extra file the hook needs → .claude/hooks/<id>/ (repeatable)."
        ),
    ] = None,
    cid: IdOpt = None,
    name: NameOpt = None,
    description: DescOpt = None,
    default: DefaultOpt = None,
    types: TypesOpt = None,
    tech: TechOpt = None,
    depends: DependsOpt = None,
    conflicts: ConflictsOpt = None,
    group: GroupOpt = None,
    group_default: GroupDefaultOpt = None,
    catalog: CatalogOpt = Path("catalog"),
    force: ForceOpt = False,
    yes: YesOpt = False,
) -> None:
    """Add a Hook: the script is installed in .claude/hooks/ and registered in settings.json."""

    def go() -> None:
        prompter = _prompter(yes)
        meta = _metadata(
            prompter,
            cid=cid,
            name=name,
            description=description,
            default=default,
            types=types,
            tech=tech,
            depends=depends,
            conflicts=conflicts,
            group=group,
            group_default=group_default,
        )
        _ask_description(prompter, meta, "hook")
        _finish(
            catalog,
            build_hook(
                script,
                meta,
                event=event,
                matcher=matcher,
                timeout=timeout,
                extra_files=support or [],
            ),
            force,
        )

    _run(go)


@add_app.command("script")
def add_script(
    files: Annotated[list[Path], typer.Argument(help="Script file(s), installed into scripts/.")],
    cid: IdOpt = None,
    name: NameOpt = None,
    description: DescOpt = None,
    default: DefaultOpt = None,
    types: TypesOpt = None,
    tech: TechOpt = None,
    depends: DependsOpt = None,
    conflicts: ConflictsOpt = None,
    group: GroupOpt = None,
    group_default: GroupDefaultOpt = None,
    catalog: CatalogOpt = Path("catalog"),
    force: ForceOpt = False,
    yes: YesOpt = False,
) -> None:
    """Add a project-level Script."""

    def go() -> None:
        prompter = _prompter(yes)
        meta = _metadata(
            prompter,
            cid=cid,
            name=name,
            description=description,
            default=default,
            types=types,
            tech=tech,
            depends=depends,
            conflicts=conflicts,
            group=group,
            group_default=group_default,
        )
        _ask_description(prompter, meta, "script")
        _finish(catalog, build_script(files, meta), force, meta)

    _run(go)


@add_app.command("mcp")
def add_mcp(
    server: Annotated[str, typer.Argument(help="MCP server name as it will appear in .mcp.json.")],
    url: Annotated[str | None, typer.Option("--url", help="Remote server URL (HTTP/SSE).")] = None,
    header: Annotated[
        list[str] | None,
        typer.Option("--header", help="Header KEY=VALUE; use ${VAR} for secrets (repeatable)."),
    ] = None,
    transport: Annotated[
        str, typer.Option("--transport", help="http or sse (with --url).")
    ] = "http",
    command: Annotated[
        str | None, typer.Option("--command", help="Local stdio server executable.")
    ] = None,
    arg: Annotated[
        list[str] | None, typer.Option("--arg", help="Argument for --command (repeatable).")
    ] = None,
    env: Annotated[
        list[str] | None,
        typer.Option("--env", help="Required environment variable name (repeatable)."),
    ] = None,
    cid: IdOpt = None,
    name: NameOpt = None,
    description: DescOpt = None,
    default: DefaultOpt = None,
    types: TypesOpt = None,
    tech: TechOpt = None,
    depends: DependsOpt = None,
    conflicts: ConflictsOpt = None,
    group: GroupOpt = None,
    group_default: GroupDefaultOpt = None,
    catalog: CatalogOpt = Path("catalog"),
    force: ForceOpt = False,
    yes: YesOpt = False,
) -> None:
    """Add an MCP server definition (never put real secrets here: use ${VAR})."""

    def go() -> None:
        prompter = _prompter(yes)
        meta = _metadata(
            prompter,
            cid=cid,
            name=name,
            description=description,
            default=default,
            types=types,
            tech=tech,
            depends=depends,
            conflicts=conflicts,
            group=group,
            group_default=group_default,
        )
        _ask_description(prompter, meta, "MCP server")
        built = build_mcp(
            server,
            meta,
            url=url,
            headers=parse_pairs(header or [], "--header"),
            command=command,
            args=arg or [],
            env=env or [],
            transport=transport,
        )
        _finish(catalog, built, force, meta)

    _run(go)


@catalog_app.command("list")
def list_capabilities(catalog: CatalogOpt = Path("catalog")) -> None:
    """List every capability in the catalog."""

    def go() -> None:
        try:
            loaded = load_catalog(catalog.resolve())
        except CatalogError as exc:
            raise AuthoringError(str(exc)) from exc
        table = Table(title=f"CWI catalog ({len(loaded.capabilities)})")
        table.add_column("Reference", no_wrap=True)
        for column in ("Group", "Default", "Recommended for", "Depends on"):
            table.add_column(column)
        for cap in loaded.capabilities:
            rec = cap.manifest.recommendation
            recommended = ""
            if rec:
                recommended = ", ".join([*(t.value for t in rec.project_types), *rec.technologies])
            table.add_row(
                cap.ref,
                cap.manifest.name,
                "yes" if cap.manifest.default_selected else "",
                recommended,
                ", ".join(cap.manifest.dependencies),
            )
        console.print(table)

    _run(go)


@catalog_app.command("validate")
def validate(catalog: CatalogOpt = Path("catalog")) -> None:
    """Validate the catalog (manifests, payloads, dependencies, secrets)."""

    def go() -> None:
        try:
            loaded = load_catalog(catalog.resolve())
        except CatalogError as exc:
            raise AuthoringError(str(exc)) from exc
        console.print(f"[green]✓ Catalog valid: {len(loaded.capabilities)} capabilities[/green]")

    _run(go)


@catalog_app.command("remove")
def remove(
    ref: Annotated[str, typer.Argument(help="Capability reference, e.g. skill:testing.")],
    catalog: CatalogOpt = Path("catalog"),
    force: ForceOpt = False,
    yes: YesOpt = False,
) -> None:
    """Remove a capability folder from the catalog."""

    def go() -> None:
        prompter = _prompter(yes)
        if prompter.interactive and not prompter.confirm(
            "remove", f"Remove {ref} from the catalog?", default=False
        ):
            raise UserCancelled("Cancelled. Nothing was removed.")
        target = remove_capability(catalog, ref, force=force)
        console.print(f"[green]✓ Removed {ref}[/green]  [dim]{target}[/dim]")

    _run(go)


group_app = typer.Typer(help="Manage capability families (groups).", no_args_is_help=True)
catalog_app.add_typer(group_app, name="group")


def _cap_type(value: str):
    from cwi.domain.enums import CapabilityType

    value = value.lower().rstrip("s") if value.lower() != "mcp" else "mcp"
    try:
        return CapabilityType(value)
    except ValueError as exc:
        raise AuthoringError("Type must be one of: skill, agent, script, hook, mcp") from exc


@group_app.command("create")
def group_create(
    cap_type: Annotated[
        str, typer.Argument(metavar="TYPE", help="skill, agent, script, hook or mcp.")
    ],
    group: Annotated[str, typer.Argument(help="Family id, e.g. devops-agents.")],
    name: NameOpt = None,
    description: DescOpt = None,
    catalog: CatalogOpt = Path("catalog"),
) -> None:
    """Create an empty family folder with its group.json."""
    from cwi.authoring.groups import ensure_group

    def go() -> None:
        path = ensure_group(
            catalog.resolve(), _cap_type(cap_type), group, name=name, description=description
        )
        console.print(
            f"[green]✓ Group ready[/green]  [dim]{path}[/dim]  Add members with --group {group}."
        )

    _run(go)


@group_app.command("defaults")
def group_defaults(
    cap_type: Annotated[
        str, typer.Argument(metavar="TYPE", help="skill, agent, script, hook or mcp.")
    ],
    group: Annotated[str, typer.Argument(help="Family id.")],
    project_type: Annotated[
        str, typer.Argument(help="Project type: " + ",".join(t.value for t in ProjectType))
    ],
    members: Annotated[
        str,
        typer.Argument(
            help="Comma-separated member ids to preselect for that project type ('' clears)."
        ),
    ],
    catalog: CatalogOpt = Path("catalog"),
) -> None:
    """Set which family members are preselected for one project type."""
    from cwi.authoring.groups import group_dir, read_group, write_group

    def go() -> None:
        kind = _cap_type(cap_type)
        types = parse_project_types(project_type)
        if len(types) != 1:
            raise AuthoringError("Pass exactly one project type")
        path = group_dir(catalog.resolve(), kind, group)
        data = read_group(path)
        ids = sorted(set(parse_list(members)))
        defaults = dict(data.get("defaults") or {})
        if ids:
            defaults[types[0].value] = ids
        else:
            defaults.pop(types[0].value, None)
        before = dict(data)
        data["defaults"] = dict(sorted(defaults.items()))
        write_group(path, data)
        try:
            load_catalog(catalog.resolve())
        except CatalogError as exc:
            write_group(path, before)
            raise AuthoringError(f"Not saved: {exc}") from exc
        console.print(f"[green]✓ {group}: {types[0].value} → {', '.join(ids) or '(none)'}[/green]")

    _run(go)
