"""Interactive screens: one function per init stage. They ask; they never mutate the repository."""

from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from cwi import paths
from cwi.catalog.dependency_resolver import find_conflicts, resolve
from cwi.catalog.recommender import recommend
from cwi.claude_md.docs import architecture_is_template, scaffold_files
from cwi.claude_md.generator import (
    CLAUDE_IMPORT_FILE,
    DOCS_ARCHITECTURE,
    add_agents_import,
    default_spec,
    drop_sections,
    estimate_size,
    has_agents_import,
    load_template,
    render_claude_md,
)
from cwi.claude_md.merger import classify_instruction, merge_claude_md
from cwi.domain.enums import SELECTION_ORDER, ClaudeMdMode, ProjectType
from cwi.domain.errors import UserCancelled
from cwi.domain.models import (
    LAYOUT_AGENTS,
    LAYOUT_CLAUDE,
    Catalog,
    ClaudeMdDecision,
    CWIState,
    DetectedCommand,
    InstallationPlan,
    ProjectProfile,
    ScanResult,
)
from cwi.planning.diff import unified_diff
from cwi.planning.planner import FileDecision, McpDecision
from cwi.profile import build_new_profile, profile_from_scan, uncertain_detections
from cwi.state.hashing import sha256_file
from cwi.ui import render
from cwi.ui.prompts import Option, Prompter, heading

OTHER = "__other__"
SCAFFOLD = "__scaffold__"
SKIP = "__skip__"


# ---------------------------------------------------------------------------------------------
# Root and git
# ---------------------------------------------------------------------------------------------


def choose_root(console: Console, prompter: Prompter, cwd: Path, git_root: Path | None) -> Path:
    if git_root is None or git_root == cwd:
        return cwd
    console.print(
        f"Repository root detected:\n\n  [bold]{git_root}[/bold]\n\nYou ran cwi from [bold]{cwd}[/bold]."
    )
    choice = prompter.select(
        "root",
        "Initialize which workspace?",
        [
            Option("current", f"Use current directory ({cwd.name})"),
            Option("git", f"Use repository root ({git_root.name})"),
            Option("cancel", "Cancel"),
        ],
        default="current",
    )
    if choice == "cancel":
        raise UserCancelled("Cancelled. No changes were made.")
    return git_root if choice == "git" else cwd


def dirty_tree_notice(console: Console, prompter: Prompter, dirty_files: list[str]) -> None:
    if not dirty_files:
        return
    render.warning(
        console,
        f"Uncommitted changes detected ({len(dirty_files)} path(s)).\n"
        "  CWI will show every planned modification and keep a rollback backup during apply,\n"
        "  but existing uncommitted work may make diffs harder to review.",
    )
    if not prompter.confirm("git.dirty", "Continue?", default=True):
        raise UserCancelled("Cancelled. No changes were made.")


# ---------------------------------------------------------------------------------------------
# Project profile
# ---------------------------------------------------------------------------------------------


def _pick(
    prompter: Prompter, key: str, message: str, values: list[str], default: str | None = None
) -> str | None:
    options = [Option(v, v) for v in values] + [Option(OTHER, "Other…"), Option(SKIP, "Skip")]
    answer = prompter.select(
        key, message, options, default=default or (values[0] if values else SKIP)
    )
    if answer == OTHER:
        text = prompter.text(f"{key}.other", f"{message.rstrip('?')} (type it):").strip()
        return text or None
    if answer == SKIP or answer is None:
        return None
    return answer


def _pick_many(
    prompter: Prompter, key: str, message: str, values: list[str], checked: list[str] | None = None
) -> list[str]:
    checked = checked or []
    chosen = prompter.checkbox(key, message, [Option(v, v, v in checked) for v in values])
    extra = prompter.text(
        f"{key}.other", "Other (comma-separated, empty to skip):", default=""
    ).strip()
    return [*chosen, *[e.strip() for e in extra.split(",") if e.strip()]]


BACKEND_FRAMEWORKS = {
    "Python": ["FastAPI", "Django", "Flask"],
    "TypeScript": ["Express", "NestJS", "Fastify", "Hono"],
    "JavaScript": ["Express", "Fastify", "Hono"],
    "Go": ["Gin", "Echo", "chi"],
    "Rust": ["Axum", "Actix Web"],
    "Java": ["Spring Boot"],
}
FRONTEND_FRAMEWORKS = ["React", "Next.js", "Vue", "Svelte", "Angular"]
AI_SDKS = ["Anthropic SDK", "Claude Agent SDK", "OpenAI SDK", "LangChain"]
CLI_FRAMEWORKS = {
    "Python": ["Typer", "Click"],
    "TypeScript": ["Commander", "oclif"],
    "Go": ["Cobra"],
    "Rust": ["clap"],
}
DATA_LIBS = ["pandas", "NumPy", "scikit-learn", "PyTorch", "Polars", "Jupyter"]
DATABASES = ["PostgreSQL", "MySQL", "SQLite", "MongoDB"]
PY_MANAGERS = ["uv", "Poetry", "pip"]
JS_MANAGERS = ["npm", "pnpm", "yarn", "bun"]
TEST_TOOLS = {
    "Python": ["pytest"],
    "TypeScript": ["Vitest", "Jest", "Playwright"],
    "JavaScript": ["Vitest", "Jest", "Playwright"],
    "Go": ["go test"],
    "Rust": ["cargo test"],
    "Java": ["JUnit"],
}
INFRASTRUCTURE = [
    "Docker",
    "GitHub Actions",
    "AWS",
    "Google Cloud",
    "Azure",
    "Vercel",
    "Terraform",
    "Kubernetes",
]
LANGUAGES = ["Python", "TypeScript", "JavaScript", "Go", "Rust", "Java"]


def _language_block(
    prompter: Prompter, prefix: str, role: str, languages: list[str]
) -> tuple[list[str], str | None]:
    items: list[str] = []
    language = _pick(prompter, f"{prefix}.language", f"{role} language?", languages)
    if language:
        items.append(language)
        managers = (
            PY_MANAGERS
            if language == "Python"
            else JS_MANAGERS
            if language in ("TypeScript", "JavaScript")
            else []
        )
        if managers:
            manager = _pick(prompter, f"{prefix}.package_manager", "Package manager?", managers)
            if manager:
                items.append(manager)
    return items, language


def ask_new_project(console: Console, prompter: Prompter, root: Path) -> ProjectProfile:
    console.print(
        "[bold]No existing application detected.[/bold] A few questions to set up the workspace.\n"
    )
    project_type = ProjectType(
        prompter.select(
            "new.type",
            "What are you building?",
            [Option(t.value, t.label) for t in ProjectType],
            default=ProjectType.OTHER.value,
        )
    )
    stack: dict[str, list[str]] = {}
    languages: list[str] = []

    if project_type in (ProjectType.BACKEND, ProjectType.FULLSTACK):
        items, language = _language_block(prompter, "new.backend", "Backend", LANGUAGES)
        if language:
            languages.append(language)
            framework = _pick(
                prompter,
                "new.backend.framework",
                "Backend framework?",
                BACKEND_FRAMEWORKS.get(language, []),
            )
            if framework:
                items.insert(1, framework)
        database = _pick(prompter, "new.database", "Database?", DATABASES)
        if database:
            items.append(database)
        stack["Backend"] = items
    if project_type in (ProjectType.FRONTEND, ProjectType.FULLSTACK):
        items, language = _language_block(
            prompter, "new.frontend", "Frontend", ["TypeScript", "JavaScript"]
        )
        if language:
            languages.append(language)
        framework = _pick(
            prompter, "new.frontend.framework", "Frontend framework?", FRONTEND_FRAMEWORKS
        )
        if framework:
            items.insert(1 if items else 0, framework)
            if framework in ("React", "Vue", "Svelte"):
                build = _pick(prompter, "new.frontend.build", "Build tool?", ["Vite"])
                if build:
                    items.insert(2, build)
        stack["Frontend"] = items
    if project_type == ProjectType.AI:
        items, language = _language_block(prompter, "new.ai", "Language", ["Python", "TypeScript"])
        if language:
            languages.append(language)
        sdk = _pick(prompter, "new.ai.sdk", "AI / agent SDK?", AI_SDKS)
        if sdk:
            items.append(sdk)
        if language:
            server = _pick(
                prompter,
                "new.ai.server",
                "Serving framework?",
                BACKEND_FRAMEWORKS.get(language, []),
                default=SKIP,
            )
            if server:
                items.append(server)
        stack["Project"] = items
    if project_type == ProjectType.CLI:
        items, language = _language_block(prompter, "new.cli", "Language", LANGUAGES)
        if language:
            languages.append(language)
            framework = _pick(
                prompter, "new.cli.framework", "CLI framework?", CLI_FRAMEWORKS.get(language, [])
            )
            if framework:
                items.append(framework)
        stack["Project"] = items
    if project_type == ProjectType.LIBRARY:
        items, language = _language_block(prompter, "new.library", "Language", LANGUAGES)
        if language:
            languages.append(language)
        stack["Project"] = items
    if project_type == ProjectType.DATA_ML:
        items, language = _language_block(prompter, "new.data", "Language", ["Python"])
        if language:
            languages.append(language)
        items.extend(
            _pick_many(
                prompter, "new.data.libraries", "Libraries?", DATA_LIBS, checked=["pandas", "NumPy"]
            )
        )
        stack["Project"] = items
    if project_type == ProjectType.OTHER:
        raw = prompter.text(
            "new.other.stack", "Main languages / frameworks (comma-separated, empty to skip):"
        )
        stack["Project"] = [x.strip() for x in raw.split(",") if x.strip()]
        languages.extend(x for x in stack["Project"] if x in LANGUAGES)

    test_choices = list(dict.fromkeys(t for lang in languages for t in TEST_TOOLS.get(lang, [])))
    tests = (
        _pick_many(
            prompter, "new.testing", "Testing tools?", test_choices, checked=test_choices[:1]
        )
        if test_choices
        else []
    )
    infra = _pick_many(prompter, "new.infrastructure", "Infrastructure?", INFRASTRUCTURE)
    profile = build_new_profile(project_type, root.name, stack, tests, infra)
    render.step(console, "Workspace profile created")
    return profile


def _edit_list(prompter: Prompter, key: str, label: str, values: list[str]) -> list[str]:
    raw = prompter.text(key, f"{label} (comma-separated):", default=", ".join(values))
    return [v.strip() for v in raw.split(",") if v.strip()]


def edit_profile(console: Console, prompter: Prompter, profile: ProjectProfile) -> ProjectProfile:
    profile = profile.model_copy(deep=True)
    while True:
        render.profile(console, profile, title="Edit project profile")
        fields = [
            Option("done", "Done editing"),
            Option("type", f"Project type ({profile.project_type.label})"),
        ]
        fields += [Option(f"stack:{g}", f"Stack · {g}") for g in profile.stack]
        fields += [
            Option("stack:+", "Add a stack group"),
            Option("testing", "Testing tools"),
            Option("tooling", "Tooling (linters, formatters)"),
            Option("architecture", "Architecture documentation pointer"),
        ]
        choice = prompter.select(
            "profile.edit.field", "What do you want to change?", fields, default="done"
        )
        if choice == "done":
            break
        if choice == "type":
            profile.project_type = ProjectType(
                prompter.select(
                    "profile.edit.type",
                    "Project type?",
                    [Option(t.value, t.label) for t in ProjectType],
                    default=profile.project_type.value,
                )
            )
            profile.backend = (
                profile.project_type in (ProjectType.BACKEND, ProjectType.FULLSTACK)
                or profile.backend
            )
            profile.frontend = (
                profile.project_type in (ProjectType.FRONTEND, ProjectType.FULLSTACK)
                or profile.frontend
            )
        elif choice == "stack:+":
            name = prompter.text(
                "profile.edit.group", "Group name (e.g. Backend, Frontend, Infrastructure):"
            ).strip()
            if name:
                profile.stack[name] = _edit_list(prompter, "profile.edit.group.items", name, [])
        elif isinstance(choice, str) and choice.startswith("stack:"):
            group = choice.split(":", 1)[1]
            items = _edit_list(
                prompter, f"profile.edit.stack.{group}", group, profile.stack.get(group, [])
            )
            if items:
                profile.stack[group] = items
            else:
                profile.stack.pop(group, None)
        elif choice == "testing":
            profile.test_tools = _edit_list(
                prompter, "profile.edit.testing", "Testing tools", profile.test_tools
            )
        elif choice == "tooling":
            profile.tools = _edit_list(prompter, "profile.edit.tooling", "Tooling", profile.tools)
        elif choice == "architecture":
            value = prompter.text(
                "profile.edit.architecture",
                "Path Claude should read before structural changes (empty for none):",
                default=profile.architecture_doc or "",
            ).strip()
            profile.architecture_doc = value or None
        _sync_lists_from_stack(profile)
    return profile


def _sync_lists_from_stack(profile: ProjectProfile) -> None:
    """Keep flat lists consistent with an edited stack so recommendations follow the edit."""
    from cwi.profile import KNOWN_DATABASES, KNOWN_LANGUAGES, KNOWN_PACKAGE_MANAGERS

    items = [
        i for group, values in profile.stack.items() if group != "Infrastructure" for i in values
    ]
    profile.languages = [i for i in items if i.split()[0] in KNOWN_LANGUAGES]
    profile.databases = [i for i in items if i in KNOWN_DATABASES]
    profile.package_managers = [i for i in items if i in KNOWN_PACKAGE_MANAGERS]
    profile.frameworks = [
        i
        for i in items
        if i not in profile.languages
        and i not in profile.databases
        and i not in profile.package_managers
    ]
    profile.infrastructure = list(profile.stack.get("Infrastructure", []))


def resolve_profile(
    console: Console,
    prompter: Prompter,
    root: Path,
    scan: ScanResult,
    state: CWIState | None,
    rescan,
) -> ProjectProfile:
    """Detect first, ask second. Returns the user-confirmed profile."""
    if state is not None and state.profile is not None:
        render.profile(console, state.profile, title="Saved project profile (previous cwi init)")
        choice = prompter.select(
            "profile.saved",
            "Use the saved profile?",
            [
                Option("confirm", "Confirm"),
                Option("edit", "Edit"),
                Option("rescan", "Rescan project"),
            ],
            default="confirm",
        )
        if choice == "confirm":
            return state.profile
        if choice == "edit":
            return edit_profile(console, prompter, state.profile)
        scan = rescan()

    if not scan.meaningful_project:
        return ask_new_project(console, prompter, root)

    while True:
        render.step(console, f"{scan.project_type.label} detected")
        render.scan_summary(console, scan)
        choice = prompter.select(
            "profile.confirm",
            "Is this correct?",
            [
                Option("confirm", "Confirm"),
                Option("edit", "Edit"),
                Option("evidence", "View evidence"),
                Option("rescan", "Rescan"),
                Option("cancel", "Cancel"),
            ],
            default="confirm",
        )
        if choice == "evidence":
            render.evidence(console, scan)
            continue
        if choice == "rescan":
            scan = rescan()
            continue
        if choice == "cancel":
            raise UserCancelled("Cancelled. No changes were made.")
        uncertain = uncertain_detections(scan)
        include: list[str] = []
        if uncertain:
            include = prompter.checkbox(
                "profile.uncertain",
                "Include these uncertain signals?",
                [Option(f"{c}:{v}", f"{v}  ({s})", False) for c, v, s in uncertain],
            )
        profile = profile_from_scan(scan, include)
        if choice == "edit":
            profile = edit_profile(console, prompter, profile)
        render.step(console, "Profile confirmed")
        return profile


# ---------------------------------------------------------------------------------------------
# CLAUDE.md
# ---------------------------------------------------------------------------------------------


def review_commands(
    console: Console, prompter: Prompter, commands: list[DetectedCommand]
) -> list[DetectedCommand]:
    if not commands:
        if prompter.confirm(
            "commands.add_any",
            "No development commands detected. Add some to CLAUDE.md?",
            default=False,
        ):
            return _add_commands(prompter, [])
        return []
    from cwi.domain.models import ProjectProfile as _P

    render.commands_table(console, _P(commands=commands))
    choice = prompter.select(
        "commands",
        "Essential commands for CLAUDE.md",
        [Option("confirm", "Confirm"), Option("edit", "Edit"), Option("remove", "Remove all")],
        default="confirm",
    )
    if choice == "remove":
        return []
    if choice == "edit":
        keep = prompter.checkbox(
            "commands.keep",
            "Keep which commands?",
            [
                Option(i, f"{c.group} · {c.label}: {c.command}", True)
                for i, c in enumerate(commands)
            ],
        )
        kept = [commands[i] for i in keep]
        return _add_commands(prompter, kept)
    return list(commands)


def _add_commands(prompter: Prompter, commands: list[DetectedCommand]) -> list[DetectedCommand]:
    result = list(commands)
    for _ in range(20):
        raw = prompter.text(
            "commands.add", "Add a command as 'Label: command' (empty to finish):"
        ).strip()
        if not raw:
            break
        label, sep, command = raw.partition(":")
        if not sep or not command.strip():
            continue
        result.append(
            DetectedCommand(
                group="Project",
                label=label.strip(),
                command=command.strip(),
                source="user",
                detected=True,
            )
        )
    return result


def _additional_instructions(console: Console, prompter: Prompter) -> list[str]:
    instructions: list[str] = []
    for _ in range(20):
        text = prompter.text(
            "claude_md.additional",
            "Any other instruction Claude should know in almost every session? (empty to finish)",
        ).strip()
        if not text:
            break
        advice = classify_instruction(text)
        if not advice.scoped:
            instructions.append(text)
            continue
        console.print(
            Panel(
                f"{advice.reason}\n\nRecommended destination: [bold]{advice.destination}[/bold] instead of CLAUDE.md.",
                border_style="yellow",
                expand=False,
            )
        )
        choice = prompter.select(
            "claude_md.additional.scoped",
            "What should CWI do with it?",
            [
                Option("later", f"Move it to a {advice.destination} later (not added now)"),
                Option("keep", "Keep globally in CLAUDE.md"),
                Option("discard", "Discard"),
            ],
            default="later",
        )
        if choice == "keep":
            instructions.append(text)
        elif choice == "later":
            render.note(console, f"Not added. Consider creating a {advice.destination} for it.")
    return instructions


def _build_spec(
    console: Console,
    prompter: Prompter,
    root: Path,
    profile: ProjectProfile,
    architecture_candidates: list[str],
):
    """Ask for the shared instruction content (spec sections 7.1 to 7.5)."""
    spec = default_spec(profile)

    # 7.1 Safety net
    console.print(
        Panel(
            "\n\n".join(spec.safety)
            + "\n\nCommands that always require approval: "
            + ", ".join(spec.dangerous_commands),
            title="Proposed safety net",
            border_style="cyan",
            expand=False,
        )
    )
    safety = prompter.select(
        "claude_md.safety",
        "Safety section",
        [
            Option("keep", "Keep proposed safety rules"),
            Option("edit", "Edit protected command list"),
            Option("no_commands", "Keep rules, drop the command list"),
            Option("remove", "Remove the Safety section (not recommended)"),
        ],
        default="keep",
    )
    if safety == "edit":
        spec.dangerous_commands = _edit_list(
            prompter, "claude_md.safety.commands", "Protected commands", spec.dangerous_commands
        )
    elif safety == "no_commands":
        spec.dangerous_commands = []
    elif safety == "remove":
        spec.safety, spec.dangerous_commands = [], []

    # 7.3 Commands
    spec.commands = review_commands(console, prompter, spec.commands)
    profile = profile.model_copy(update={"commands": spec.commands})

    # 7.4 Project docs: architecture, requirements and decisions (pointers only in the instructions)
    candidates = list(
        dict.fromkeys(
            [
                *([profile.architecture_doc] if profile.architecture_doc else []),
                *[c for c in architecture_candidates if not c.endswith("/")],
            ]
        )
    )
    options = [
        Option(
            SCAFFOLD,
            "Create docs/ skeleton: architecture + versions, glossary, specs, decisions (recommended)",
        )
    ]
    options += [
        Option(c, f"Point to existing {c} (and create the rest of docs/)") for c in candidates
    ]
    options += [
        Option(OTHER, "Point to another path…"),
        Option(SKIP, "No project docs"),
    ]
    choice = prompter.select(
        "claude_md.architecture",
        "Where do architecture, requirements and decisions live?",
        options,
        default=candidates[0] if candidates else SCAFFOLD,
    )
    scaffold: dict[str, str] = {}
    if choice == OTHER:
        choice = (
            prompter.text(
                "claude_md.architecture.path", "Path to architecture documentation:"
            ).strip()
            or SKIP
        )
        spec.architecture_pointer = None if choice == SKIP else choice
    elif choice == SKIP:
        spec.architecture_pointer = None
    else:
        existing = None if choice == SCAFFOLD else choice
        spec.docs_index = True
        spec.architecture_pointer = existing or DOCS_ARCHITECTURE
        spec.architecture_template = architecture_is_template(root / spec.architecture_pointer)
        scaffold = scaffold_files(profile, root.name, include_architecture=existing is None)
    profile = profile.model_copy(update={"architecture_doc": spec.architecture_pointer})

    # 7.5 Additional critical instructions
    spec.additional_instructions = _additional_instructions(console, prompter)
    return spec, profile, scaffold


def _decide_generated_file(
    console: Console,
    prompter: Prompter,
    path: Path,
    label: str,
    generated: str,
    state: CWIState | None,
    key: str,
) -> tuple[ClaudeMdMode, str | None]:
    """Create, or ask what to do with an existing instruction file. Never silently overwrites."""
    if not path.is_file():
        return ClaudeMdMode.CREATE, generated
    current = path.read_text(encoding="utf-8")
    record = state.managed_files.get(label) if state else None
    cwi_owned_unmodified = record is not None and sha256_file(path) == record.sha256
    if current == generated:
        render.note(console, f"Existing {label} already matches the generated version.")
        return ClaudeMdMode.KEEP, None

    console.print(
        f"[bold]Existing {label} detected.[/bold]"
        + (" [dim](created by CWI, unmodified)[/dim]" if cwi_owned_unmodified else "")
    )
    default = "replace" if cwi_owned_unmodified else "merge"
    while True:
        choice = prompter.select(
            key,
            "What should CWI do with it?",
            [
                Option("keep", "Keep current file"),
                Option("merge", "Review proposed merge (adds only missing sections)"),
                Option("replace", "Replace with generated version"),
                Option("skip", f"Skip {label} configuration"),
                Option("diff", "Show diff (current → generated)"),
            ],
            default=default,
        )
        if choice == "diff":
            console.print(
                Syntax(unified_diff(current, generated, label) or "(no differences)", "diff")
            )
            continue
        if choice == "keep":
            return ClaudeMdMode.KEEP, None
        if choice == "skip":
            return ClaudeMdMode.SKIP, None
        if choice == "replace":
            return ClaudeMdMode.REPLACE, generated
        merged = merge_claude_md(current, generated)
        if not merged.changed:
            render.note(
                console, f"{label} already has every proposed section; it is kept unchanged."
            )
            return ClaudeMdMode.KEEP, None
        console.print(Syntax(unified_diff(current, merged.content, label), "diff"))
        render.note(
            console,
            "Existing sections are kept untouched: " + (", ".join(merged.kept_sections) or "none"),
        )
        if prompter.confirm(f"{key}.merge.confirm", "Use the merged version?", default=True):
            return ClaudeMdMode.MERGE, merged.content


def _decide_claude_import(
    console: Console, prompter: Prompter, path: Path, state: CWIState | None
) -> tuple[ClaudeMdMode, str | None]:
    """CLAUDE.md in the AGENTS.md layout: it must import AGENTS.md so Claude Code reads it."""
    if not path.is_file():
        return ClaudeMdMode.CREATE, CLAUDE_IMPORT_FILE
    current = path.read_text(encoding="utf-8")
    if has_agents_import(current):
        return ClaudeMdMode.KEEP, None
    label = paths.rel(paths.CLAUDE_MD)
    record = state.managed_files.get(label) if state else None
    cwi_owned_unmodified = record is not None and sha256_file(path) == record.sha256
    console.print(
        "[bold]Existing CLAUDE.md detected.[/bold] Claude Code ignores AGENTS.md when CLAUDE.md "
        "exists, unless CLAUDE.md imports it with `@AGENTS.md`."
        + (" [dim](created by CWI, unmodified)[/dim]" if cwi_owned_unmodified else "")
    )
    while True:
        choice = prompter.select(
            "claude_md.import",
            "What should CWI do with CLAUDE.md?",
            [
                Option("import", "Add `@AGENTS.md` at the top (keeps everything else)"),
                Option("replace", "Replace with an import-only CLAUDE.md"),
                Option("keep", "Keep as is (Claude Code will not read AGENTS.md)"),
                Option("diff", "Show diff for the import"),
            ],
            default="replace" if cwi_owned_unmodified else "import",
        )
        if choice == "diff":
            console.print(Syntax(unified_diff(current, add_agents_import(current), label), "diff"))
            continue
        if choice == "keep":
            render.warning(
                console, "CLAUDE.md kept without the import: Claude Code will not load AGENTS.md."
            )
            return ClaudeMdMode.KEEP, None
        if choice == "replace":
            return ClaudeMdMode.REPLACE, CLAUDE_IMPORT_FILE
        return ClaudeMdMode.MERGE, add_agents_import(current)


def configure_claude_md(
    console: Console,
    prompter: Prompter,
    root: Path,
    profile: ProjectProfile,
    state: CWIState | None,
    architecture_candidates: list[str],
) -> tuple[ClaudeMdDecision, ProjectProfile]:
    console.rule("Agent instructions")
    claude_path = root / paths.rel(paths.CLAUDE_MD)
    agents_path = root / paths.rel(paths.AGENTS_MD)
    previous_layout = state.instructions_layout if state else None
    layout = prompter.select(
        "instructions.layout",
        "Where should the project instructions live?",
        [
            Option(
                LAYOUT_AGENTS,
                "AGENTS.md for every coding agent + CLAUDE.md importing it (recommended)",
            ),
            Option(LAYOUT_CLAUDE, "CLAUDE.md only"),
        ],
        default=previous_layout or LAYOUT_AGENTS,
    )
    main_label = "AGENTS.md" if layout == LAYOUT_AGENTS else "CLAUDE.md"
    main_path = agents_path if layout == LAYOUT_AGENTS else claude_path
    if not main_path.is_file() and not prompter.confirm(
        "claude_md.create", f"Create a minimal {main_label}?", default=True
    ):
        return ClaudeMdDecision(mode=ClaudeMdMode.SKIP, layout=layout), profile

    spec, profile, scaffold = _build_spec(console, prompter, root, profile, architecture_candidates)
    generated = render_claude_md(spec, load_template(root))

    if layout == LAYOUT_CLAUDE:
        render.claude_md_preview(console, generated, estimate_size(generated), "CLAUDE.md")
        mode, content = _decide_generated_file(
            console, prompter, claude_path, "CLAUDE.md", generated, state, "claude_md.existing"
        )
        return ClaudeMdDecision(
            mode=mode,
            spec=spec,
            generated=generated,
            content=content,
            layout=layout,
            docs_scaffold=scaffold,
        ), profile

    claude_mode, claude_content = _decide_claude_import(console, prompter, claude_path, state)
    final_claude = (
        claude_content
        if claude_content is not None
        else (claude_path.read_text(encoding="utf-8") if claude_path.is_file() else "")
    )
    shared = drop_sections(generated, final_claude)  # never duplicate sections CLAUDE.md keeps
    if shared != generated:
        render.note(console, "Sections already present in CLAUDE.md are not repeated in AGENTS.md.")
    render.claude_md_preview(console, shared, estimate_size(shared), "AGENTS.md")
    agents_mode, agents_content = _decide_generated_file(
        console, prompter, agents_path, "AGENTS.md", shared, state, "agents_md.existing"
    )
    return ClaudeMdDecision(
        mode=claude_mode,
        spec=spec,
        generated=shared,
        content=claude_content,
        layout=layout,
        agents_mode=agents_mode,
        agents_content=agents_content,
        docs_scaffold=scaffold,
    ), profile


# ---------------------------------------------------------------------------------------------
# Capabilities
# ---------------------------------------------------------------------------------------------


def select_capabilities(
    console: Console,
    prompter: Prompter,
    catalog: Catalog,
    profile: ProjectProfile,
    state: CWIState | None,
    previous_selection: list[str] | None = None,
) -> list[str]:
    recs = recommend(catalog, profile)
    installed = set(state.selected_capabilities) if state else set()
    prior = set(previous_selection) if previous_selection is not None else None
    selected: list[str] = []
    for cap_type in SELECTION_ORDER:
        caps = catalog.by_type(cap_type)
        if not caps:
            continue
        console.rule(f"Select {cap_type.title}")
        render.capability_table(console, cap_type, caps, recs, installed)
        options = []
        current_group: str | None = None
        for cap in caps:
            if cap.group != current_group and cap.group is not None:
                group = catalog.group(cap_type, cap.group)
                options.append(heading(f"── {group.name if group else cap.group} ──"))
            current_group = cap.group
            rec = recs[cap.ref]
            if prior is not None:
                checked = cap.ref in prior
            elif state is not None:
                checked = cap.ref in installed
            else:
                checked = rec.preselected
            hint = "installed" if cap.ref in installed else (rec.label if rec.preselected else "")
            options.append(Option(cap.ref, f"{cap.id:<24} {hint}".rstrip(), checked))
        chosen = prompter.checkbox(f"select.{cap_type.value}", f"Select {cap_type.title}", options)
        selected.extend(chosen)
    return selected


def resolve_selection(
    console: Console, prompter: Prompter, catalog: Catalog, selected: list[str]
) -> list[str]:
    """Dependencies are shown and confirmed; conflicts always require an explicit choice."""
    selected = list(dict.fromkeys(selected))
    for _ in range(20):
        resolution = resolve(selected, catalog)
        if resolution.added:
            lines = "\n".join(
                f"  + {ref}  [dim](required by {by})[/dim]"
                for ref, by in sorted(resolution.added.items())
            )
            console.print(f"[bold]Also required:[/bold]\n{lines}")
            if not prompter.confirm(
                "dependencies.confirm", "Include required dependencies?", default=True
            ):
                dropped = sorted(set(resolution.added.values()))
                render.warning(
                    console,
                    "Dropping capabilities whose dependencies were declined: " + ", ".join(dropped),
                )
                selected = [r for r in selected if r not in dropped]
                continue
        final = resolution.final
        conflicts = find_conflicts(final, catalog)
        if not conflicts:
            return final
        conflict = conflicts[0]
        console.print(
            f"[bold red]Conflict detected[/bold red]\n\n  {conflict.a}\n  conflicts with\n  {conflict.b}\n"
        )
        keep = prompter.select(
            f"conflict.{conflict.a}|{conflict.b}",
            "Choose one:",
            [
                Option(conflict.a, conflict.a),
                Option(conflict.b, conflict.b),
                Option("cancel", "Cancel"),
            ],
            default=conflict.a,
        )
        if keep == "cancel":
            raise UserCancelled("Cancelled. No changes were made.")
        drop = conflict.b if keep == conflict.a else conflict.a
        selected = [r for r in final if r != drop]
    return selected


def resolve_decisions(
    console: Console, prompter: Prompter, root: Path, decisions: list[FileDecision | McpDecision]
) -> dict[str, str]:
    import json

    answers: dict[str, str] = {}
    for decision in decisions:
        while True:
            if isinstance(decision, McpDecision):
                console.print(
                    f'[bold yellow]MCP server "{decision.name}" already exists with different configuration.[/bold yellow]'
                )
                options = [
                    Option("keep", "Keep existing"),
                    Option("replace", "Replace with CWI definition"),
                    Option("diff", "Show diff"),
                    Option("stop", "Cancel"),
                ]
            elif decision.kind == "modified_managed":
                console.print(
                    f"[bold yellow]Modified CWI-managed file detected:[/bold yellow] {decision.target}\n"
                    "The file has changed since CWI installed it."
                )
                options = [
                    Option("keep", "Keep user version"),
                    Option("diff", "Show diff"),
                    Option("replace", "Replace with catalog version"),
                    Option("stop", "Stop"),
                ]
            elif decision.kind == "modified_removed":
                console.print(
                    f"[bold yellow]{decision.target}[/bold yellow] belongs to deselected {decision.owner} "
                    "but was modified after CWI installed it."
                )
                options = [
                    Option("keep", "Keep the file (becomes yours)"),
                    Option("delete", "Delete it"),
                    Option("stop", "Stop"),
                ]
            else:
                console.print(
                    f"[bold yellow]{decision.target}[/bold yellow] already exists and is not managed by CWI "
                    f"({decision.owner} wants to install it)."
                )
                options = [
                    Option("keep", "Keep existing file"),
                    Option("diff", "Show diff"),
                    Option("replace", "Replace with catalog version"),
                    Option("stop", "Stop"),
                ]
            choice = prompter.select(decision.key, "Choose:", options, default="keep")
            if choice == "stop":
                raise UserCancelled("Stopped. No changes were made.")
            if choice == "diff":
                if isinstance(decision, McpDecision):
                    before = json.dumps(decision.existing, indent=2) + "\n"
                    after = json.dumps(decision.incoming, indent=2) + "\n"
                    text = unified_diff(before, after, f".mcp.json#{decision.name}")
                else:
                    current = (root / decision.target).read_text(encoding="utf-8", errors="replace")
                    new = (
                        decision.source.read_text(encoding="utf-8", errors="replace")
                        if decision.source
                        else ""
                    )
                    text = unified_diff(current, new, decision.target)
                console.print(Syntax(text or "(no differences)", "diff"))
                continue
            answers[decision.key] = choice
            break
    return answers


def preview(
    console: Console,
    prompter: Prompter,
    plan: InstallationPlan,
    root: Path,
    catalog: Catalog | None,
) -> str:
    render.plan_summary(console, plan, catalog)
    if plan.env_requirements:
        render.env_requirements(console, plan.env_requirements, catalog)
    render.tool_requirements(console, plan)
    if not plan.has_changes:
        return "noop"
    while True:
        choice = prompter.select(
            "preview",
            "Apply workspace configuration?",
            [
                Option("apply", "Apply"),
                Option("review", "Review changes (diffs)"),
                Option("operations", "Show all operations"),
                Option("back", "Back to capability selection"),
                Option("cancel", "Cancel"),
            ],
            default="apply",
        )
        if choice == "review":
            render.diffs(console, plan, root, include_new=False)
            continue
        if choice == "operations":
            render.operations_table(console, plan)
            continue
        return choice
