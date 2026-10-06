"""Project profile construction (pure): scan -> profile, answers -> profile."""

from __future__ import annotations

from pathlib import Path

from cwi.domain.enums import ProjectType
from cwi.domain.models import DetectedCommand, ProjectProfile, ScanResult

UNCERTAIN = 0.5


def uncertain_detections(scan: ScanResult) -> list[tuple[str, str, str]]:
    """(category, value, source) for low-confidence signals the user should confirm."""
    out: list[tuple[str, str, str]] = []
    for category, detections in (
        ("databases", scan.databases),
        ("infrastructure", scan.infrastructure),
    ):
        for d in detections:
            if d.confidence < UNCERTAIN:
                out.append((category, d.value, d.source))
    return out


def profile_from_scan(
    scan: ScanResult, include_uncertain: list[str] | None = None
) -> ProjectProfile:
    include = set(include_uncertain or [])

    def values(detections, category: str) -> list[str]:
        result = []
        for d in detections:
            if d.confidence >= UNCERTAIN or f"{category}:{d.value}" in include:
                result.append(d.value)
        return result

    stack = {k: list(v) for k, v in scan.stack.items()}
    for key in sorted(include):
        category, _, value = key.partition(":")
        if category == "infrastructure":
            bucket = stack.setdefault("Infrastructure", [])
        else:
            bucket = stack.setdefault(
                next((g for g in stack if g.startswith(("Backend", "App"))), "Data"), []
            )
        if value not in bucket:
            bucket.append(value)

    architecture = next((d for d in scan.architecture_docs if not d.endswith("/")), None)
    return ProjectProfile(
        project_type=scan.project_type,
        name=Path(scan.root).name,
        backend=scan.backend,
        frontend=scan.frontend,
        languages=[d.value for d in scan.languages],
        frameworks=values(scan.frameworks, "frameworks"),
        package_managers=values(scan.package_managers, "package_managers"),
        databases=values(scan.databases, "databases"),
        infrastructure=values(scan.infrastructure, "infrastructure"),
        test_tools=values(scan.test_tools, "test_tools"),
        tools=values(scan.tools, "tools"),
        commands=list(scan.commands),
        monorepo=scan.monorepo,
        architecture_doc=architecture,
        stack=stack,
    )


def suggest_commands(profile: ProjectProfile) -> list[DetectedCommand]:
    """Convention-based suggestions for a new project. Always labelled 'suggested'."""
    techs = profile.technologies()
    cmds: list[DetectedCommand] = []
    multi = profile.backend and profile.frontend

    def add(group: str, label: str, command: str, why: str) -> None:
        cmds.append(
            DetectedCommand(group=group, label=label, command=command, source=why, detected=False)
        )

    py_group = "Backend" if multi else "Project"
    js_group = "Frontend" if multi else "Project"
    if "python" in techs:
        runner = "uv run " if "uv" in techs else "poetry run " if "poetry" in techs else ""
        if "fastapi" in techs:
            add(py_group, "Run", f"{runner}fastapi dev", "FastAPI convention")
        elif "django" in techs:
            add(py_group, "Run", f"{runner}python manage.py runserver", "Django convention")
        if "pytest" in techs:
            add(py_group, "Test", f"{runner}pytest", "pytest convention")
        if "ruff" in techs:
            add(py_group, "Lint", f"{runner}ruff check .", "Ruff convention")
    if techs & {"typescript", "javascript"}:
        pm = next((p for p in ("pnpm", "yarn", "bun") if p in techs), "npm")
        run = {"npm": "npm run ", "pnpm": "pnpm ", "yarn": "yarn ", "bun": "bun run "}[pm]
        if techs & {"vite", "next.js", "react", "vue", "svelte", "nuxt", "astro"}:
            add(js_group, "Run", f"{run}dev", "framework convention")
        if techs & {"vitest", "jest"}:
            add(
                js_group,
                "Test",
                "npm test" if pm == "npm" else f"{run}test",
                "test runner convention",
            )
    return cmds


def build_new_profile(
    project_type: ProjectType,
    name: str,
    stack: dict[str, list[str]],
    test_tools: list[str],
    infrastructure: list[str],
) -> ProjectProfile:
    stack = {k: [i for i in v if i] for k, v in stack.items() if any(v)}
    all_items = [i for items in stack.values() for i in items]
    languages = [i for i in all_items if i.split()[0] in KNOWN_LANGUAGES]
    databases = [i for i in all_items if i in KNOWN_DATABASES]
    managers = [i for i in all_items if i in KNOWN_PACKAGE_MANAGERS]
    frameworks = [
        i for i in all_items if i not in languages and i not in databases and i not in managers
    ]
    if infrastructure:
        stack["Infrastructure"] = list(infrastructure)
    backend = project_type in (ProjectType.BACKEND, ProjectType.FULLSTACK) or "Backend" in stack
    frontend = project_type in (ProjectType.FRONTEND, ProjectType.FULLSTACK) or "Frontend" in stack
    profile = ProjectProfile(
        project_type=project_type,
        name=name,
        backend=backend,
        frontend=frontend,
        languages=list(dict.fromkeys(languages)),
        frameworks=list(dict.fromkeys(frameworks)),
        package_managers=list(dict.fromkeys(managers)),
        databases=list(dict.fromkeys(databases)),
        infrastructure=list(infrastructure),
        test_tools=list(test_tools),
        stack=stack,
    )
    profile.commands = suggest_commands(profile)
    return profile


KNOWN_LANGUAGES = {
    "Python",
    "TypeScript",
    "JavaScript",
    "Go",
    "Rust",
    "Java",
    "Kotlin",
    "C#",
    "Ruby",
    "PHP",
    "Swift",
    "Dart",
    "Elixir",
}
KNOWN_DATABASES = {
    "PostgreSQL",
    "MySQL",
    "SQLite",
    "MongoDB",
    "Redis",
    "MariaDB",
    "DynamoDB",
    "Supabase",
}
KNOWN_PACKAGE_MANAGERS = {"uv", "Poetry", "pip", "npm", "pnpm", "yarn", "bun"}
