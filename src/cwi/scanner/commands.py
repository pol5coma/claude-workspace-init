"""Development command detection.

Confidence hierarchy: explicit package script > task runner target > tool configuration >
framework convention. Convention-based commands are marked `detected=False` ("Suggested").
Nothing here runs a command.
"""

from __future__ import annotations

import re
from typing import Any

from cwi.domain.models import DetectedCommand
from cwi.scanner.context import ScanContext, Unit, join
from cwi.scanner.javascript import package_manager_for

SCRIPT_LABELS: list[tuple[str, tuple[str, ...]]] = [
    ("Run", ("dev", "start", "serve")),
    ("Test", ("test", "test:unit")),
    ("Lint", ("lint",)),
    ("Typecheck", ("typecheck", "type-check", "check-types", "tsc")),
    ("Format", ("format", "fmt")),
    ("Build", ("build",)),
]

TASK_LABELS: dict[str, str] = {
    "dev": "Run",
    "run": "Run",
    "start": "Run",
    "serve": "Run",
    "test": "Test",
    "tests": "Test",
    "lint": "Lint",
    "typecheck": "Typecheck",
    "format": "Format",
    "fmt": "Format",
    "build": "Build",
    "check": "Check",
}


def group_names(ctx: ScanContext) -> dict[str, str]:
    """Human group label per unit: Backend / Frontend / Project, disambiguated by path."""
    units = [u for u in ctx.units.values() if u.has_manifest]
    roles: dict[str, list[Unit]] = {}
    for unit in units:
        roles.setdefault(unit.role, []).append(unit)
    names: dict[str, str] = {}
    for role, members in roles.items():
        for unit in members:
            if len(members) > 1 and unit.path:
                names[unit.path] = f"{role} ({unit.path})"
            else:
                names[unit.path] = role
    return names


def _in_dir(unit_path: str, command: str) -> str:
    return f"cd {unit_path} && {command}" if unit_path else command


def _js_script_command(manager: str, script: str) -> str:
    if manager == "npm":
        return "npm test" if script == "test" else f"npm run {script}"
    if manager == "yarn":
        return f"yarn {script}"
    if manager == "pnpm":
        return f"pnpm {script}"
    if manager == "bun":
        return f"bun run {script}"
    return f"{manager} run {script}"


def detect_commands(ctx: ScanContext) -> None:
    groups = group_names(ctx)
    # 1. Explicit package scripts.
    for unit in _units(ctx):
        pkg_rel = join(unit.path, "package.json")
        data = ctx.read_json(pkg_rel) if ctx.is_file(pkg_rel) else None
        if not isinstance(data, dict):
            continue
        scripts: dict[str, Any] = data.get("scripts") or {}
        manager, _, _ = package_manager_for(ctx, unit.path, data)
        for label, keys in SCRIPT_LABELS:
            for key in keys:
                if key in scripts:
                    ctx.add_command(
                        DetectedCommand(
                            group=groups.get(unit.path, "Project"),
                            label=label,
                            command=_in_dir(unit.path, _js_script_command(manager, key)),
                            source=f"{pkg_rel} scripts.{key}",
                        )
                    )
                    break
    # 2. Task runners (root only; they usually orchestrate the whole repo).
    _task_runner_commands(ctx, groups)
    # 3. Tool configuration and 4. framework conventions.
    for unit in _units(ctx):
        if unit.language == "Python":
            _python_commands(ctx, unit, groups.get(unit.path, "Project"))


def _units(ctx: ScanContext) -> list[Unit]:
    return sorted(
        (u for u in ctx.units.values() if u.has_manifest), key=lambda u: (u.path != "", u.path)
    )


def _task_runner_commands(ctx: ScanContext, groups: dict[str, str]) -> None:
    group = "Project" if len(set(groups.values())) != 1 else next(iter(groups.values()))
    makefile = next((m for m in ("Makefile", "makefile", "GNUmakefile") if ctx.is_file(m)), None)
    if makefile:
        text = ctx.read_text(makefile) or ""
        targets = re.findall(r"^([A-Za-z0-9_.-]+)\s*:(?!=)", text, re.M)
        _add_targets(ctx, group, targets, "make", makefile)
    justfile = next((j for j in ("justfile", "Justfile", ".justfile") if ctx.is_file(j)), None)
    if justfile:
        text = ctx.read_text(justfile) or ""
        targets = re.findall(r"^@?([A-Za-z0-9_-]+)(?:\s+[^:=]*)?:(?!=)", text, re.M)
        _add_targets(ctx, group, targets, "just", justfile)
    taskfile = next((t for t in ("Taskfile.yml", "Taskfile.yaml") if ctx.is_file(t)), None)
    if taskfile:
        text = ctx.read_text(taskfile) or ""
        section = text.split("tasks:", 1)[1] if "tasks:" in text else ""
        targets = re.findall(r"^  ([A-Za-z0-9_:-]+):", section, re.M)
        _add_targets(ctx, group, targets, "task", taskfile)


def _add_targets(
    ctx: ScanContext, group: str, targets: list[str], runner: str, source: str
) -> None:
    seen_labels: set[str] = set()
    for target in targets:
        label = TASK_LABELS.get(target.lower())
        if label is None or label in seen_labels:
            continue
        seen_labels.add(label)
        ctx.add_command(
            DetectedCommand(
                group=group, label=label, command=f"{runner} {target}", source=f"{source} target"
            )
        )


def _python_runner(unit: Unit) -> str:
    if "uv" in unit.package_managers:
        return "uv run "
    if "Poetry" in unit.package_managers:
        return "poetry run "
    if "Pipenv" in unit.package_managers:
        return "pipenv run "
    return ""


def _python_commands(ctx: ScanContext, unit: Unit, group: str) -> None:
    run = _python_runner(unit)
    has_manage = ctx.is_file(join(unit.path, "manage.py"))
    if has_manage:
        ctx.add_command(
            DetectedCommand(
                group=group,
                label="Run",
                command=_in_dir(unit.path, f"{run}python manage.py runserver"),
                source=f"{join(unit.path, 'manage.py')} present",
            )
        )
    if "pytest" in unit.test_tools:
        ctx.add_command(
            DetectedCommand(
                group=group,
                label="Test",
                command=_in_dir(unit.path, f"{run}pytest"),
                source="pytest configured",
            )
        )
    if "Ruff" in unit.tools:
        ctx.add_command(
            DetectedCommand(
                group=group,
                label="Lint",
                command=_in_dir(unit.path, f"{run}ruff check ."),
                source="Ruff configured",
            )
        )
        ctx.add_command(
            DetectedCommand(
                group=group,
                label="Format",
                command=_in_dir(unit.path, f"{run}ruff format ."),
                source="Ruff configured",
            )
        )
    if "mypy" in unit.tools:
        ctx.add_command(
            DetectedCommand(
                group=group,
                label="Typecheck",
                command=_in_dir(unit.path, f"{run}mypy ."),
                source="mypy configured",
            )
        )
    # Framework conventions: suggestions, never presented as detected.
    if "FastAPI" in unit.frameworks and not has_manage:
        entry = next(
            (
                e
                for e in ("main.py", "app/main.py", "src/main.py", "app.py")
                if ctx.is_file(join(unit.path, e))
            ),
            None,
        )
        target = f" {entry}" if entry else ""
        ctx.add_command(
            DetectedCommand(
                group=group,
                label="Run",
                command=_in_dir(unit.path, f"{run}fastapi dev{target}"),
                source="FastAPI convention",
                detected=False,
            )
        )
    elif "Flask" in unit.frameworks:
        ctx.add_command(
            DetectedCommand(
                group=group,
                label="Run",
                command=_in_dir(unit.path, f"{run}flask run --debug"),
                source="Flask convention",
                detected=False,
            )
        )
