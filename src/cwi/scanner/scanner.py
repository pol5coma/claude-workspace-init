"""Project scanner: deterministic, read-only, never executes repository code."""

from __future__ import annotations

import os
from pathlib import Path

from cwi import paths
from cwi.domain.models import ScanResult
from cwi.scanner.claude_config import detect_claude_config
from cwi.scanner.commands import detect_commands, group_names
from cwi.scanner.context import ScanContext
from cwi.scanner.inference import infer_project_type
from cwi.scanner.infrastructure import (
    detect_env_examples,
    detect_infrastructure,
    detect_other_languages,
)
from cwi.scanner.javascript import BACKEND as JS_BACKEND
from cwi.scanner.javascript import FRONTEND as JS_FRONTEND
from cwi.scanner.javascript import detect_javascript
from cwi.scanner.python import BACKEND_FRAMEWORKS as PY_BACKEND
from cwi.scanner.python import detect_python

SUBPROJECT_PARENTS = ("apps", "packages", "services", "libs")
SUBPROJECT_DIRS = ("backend", "frontend", "api", "web", "server", "client", "app", "ui")
SOURCE_DIRS = ("src", "app", "apps", "packages", "lib", "services", "cmd", "internal", "pkg")
SOURCE_SUFFIXES = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".mjs",
    ".go",
    ".rs",
    ".java",
    ".kt",
    ".rb",
    ".php",
    ".cs",
    ".swift",
    ".vue",
    ".svelte",
    ".ipynb",
}
ARCHITECTURE_DOCS = (
    "ARCHITECTURE.md",
    "docs/architecture.md",
    "docs/ARCHITECTURE.md",
    "docs/architecture/README.md",
    "docs/design.md",
)
MONOREPO_FILES = ("pnpm-workspace.yaml", "turbo.json", "nx.json", "lerna.json", "rush.json")


def is_cwi_template(root: Path) -> bool:
    return (root / paths.rel(paths.TEMPLATE_MARKER)).is_file()


def _cwi_owned(ctx: ScanContext, rel: str) -> bool:
    """Paths that belong to the CWI template and never count as project signals."""
    top = rel.split("/", 1)[0]
    if top in (
        paths.rel(paths.CATALOG_DIR),
        paths.rel(paths.TEMPLATES_DIR),
        paths.rel(paths.CWI_WORK_DIR),
    ):
        return True
    if rel == "src/cwi" or rel.startswith("src/cwi/"):
        return True
    return bool(ctx.cwi_template and top == "tests")


def _candidate_units(ctx: ScanContext) -> list[str]:
    units = [""]
    for parent in SUBPROJECT_PARENTS:
        if ctx.is_dir(parent):
            for child in sorted(ctx.path(parent).iterdir()):
                rel = f"{parent}/{child.name}"
                if (
                    child.is_dir()
                    and not child.is_symlink()
                    and child.name not in paths.IGNORED_SCAN_DIRS
                ):
                    units.append(rel)
    for name in SUBPROJECT_DIRS:
        if ctx.is_dir(name):
            units.append(name)
    return [u for u in units if not (u and _cwi_owned(ctx, u))]


def _source_tree(ctx: ScanContext, max_entries: int = 5000) -> str | None:
    """Find one source file in a conventional source directory, pruning ignored dirs."""
    seen = 0
    for name in SOURCE_DIRS:
        base = ctx.path(name)
        if not base.is_dir() or base.is_symlink():
            continue
        for dirpath, dirnames, filenames in os.walk(base, followlinks=False):
            rel_dir = Path(dirpath).relative_to(ctx.root).as_posix()
            if _cwi_owned(ctx, rel_dir):
                dirnames[:] = []
                continue
            dirnames[:] = sorted(
                d
                for d in dirnames
                if d not in paths.IGNORED_SCAN_DIRS and not _cwi_owned(ctx, f"{rel_dir}/{d}")
            )
            for filename in sorted(filenames):
                seen += 1
                if Path(filename).suffix in SOURCE_SUFFIXES:
                    return f"{rel_dir}/{filename}"
            if seen > max_entries:
                return None
    for child in sorted(ctx.root.iterdir()):
        if child.is_file() and child.suffix in SOURCE_SUFFIXES and not child.name.startswith("."):
            return child.name
    return None


def scan_project(root: Path) -> ScanResult:
    root = root.resolve()
    ctx = ScanContext(root=root, cwi_template=is_cwi_template(root))

    unit_paths = _candidate_units(ctx)
    for unit_path in unit_paths:
        detect_python(ctx, unit_path)
        detect_javascript(ctx, unit_path)
        detect_other_languages(ctx, unit_path)
    manifest_units = [u.path for u in ctx.units.values() if u.has_manifest]
    detect_infrastructure(ctx, unit_paths)
    detect_env_examples(ctx, unit_paths)
    detect_commands(ctx)

    for name in MONOREPO_FILES:
        if ctx.is_file(name):
            ctx.monorepo_signals.append(name)
    sub_units = [p for p in manifest_units if p]
    if len(sub_units) >= 2 and any(p.split("/")[0] in SUBPROJECT_PARENTS for p in sub_units):
        ctx.monorepo_signals.append(f"{len(sub_units)} subprojects")
    monorepo = bool(ctx.monorepo_signals)

    project_type, confidence, reason, backend, frontend = infer_project_type(ctx)

    signals: list[str] = []
    if manifest_units:
        signals.append("project manifest in " + ", ".join(p or "." for p in sorted(manifest_units)))
    source = _source_tree(ctx)
    if source:
        signals.append(f"source file {source}")
    meaningful = bool(signals)

    architecture_docs: list[str] = []
    seen_docs: set[Path] = set()
    for doc in ARCHITECTURE_DOCS:
        if ctx.exact_file(doc):
            resolved = ctx.path(doc).resolve()
            if resolved not in seen_docs:
                seen_docs.add(resolved)
                architecture_docs.append(doc)
    for adr_dir in ("docs/adr", "docs/decisions", "adr"):
        if ctx.is_dir(adr_dir):
            architecture_docs.append(adr_dir + "/")

    def sorted_detections(category: str):
        return sorted(
            ctx.detections[category].values(), key=lambda d: (-d.confidence, d.value.lower())
        )

    return ScanResult(
        root=str(root),
        meaningful_project=meaningful,
        project_type=project_type,
        project_type_confidence=confidence,
        project_type_reason=reason,
        backend=backend,
        frontend=frontend,
        python_version=ctx.python_version,
        languages=sorted_detections("languages"),
        frameworks=sorted_detections("frameworks"),
        package_managers=sorted_detections("package_managers"),
        databases=sorted_detections("databases"),
        infrastructure=sorted_detections("infrastructure"),
        test_tools=sorted_detections("test_tools"),
        tools=sorted_detections("tools"),
        commands=ctx.commands,
        monorepo=monorepo,
        subprojects=sorted(sub_units),
        architecture_docs=architecture_docs,
        existing_claude=detect_claude_config(ctx),
        signals=signals,
        stack=build_stack(ctx),
    )


_PRIMARY = {
    *PY_BACKEND,
    *JS_BACKEND,
    *JS_FRONTEND,
    "Rails",
    "Spring Boot",
    "Laravel",
    "Gin",
    "Echo",
    "Axum",
    "Actix Web",
}
_SECONDARY = {"Vite", "Tailwind CSS", "Typer", "Click", "Commander", "Streamlit"}


def _framework_rank(name: str) -> int:
    if name in _PRIMARY:
        return 0
    if name in _SECONDARY:
        return 1
    return 2


def build_stack(ctx: ScanContext) -> dict[str, list[str]]:
    """Concise stack declaration grouped by role (spec section 7.2)."""
    groups = group_names(ctx)
    stack: dict[str, list[str]] = {}
    units = sorted(
        (u for u in ctx.units.values() if u.has_manifest), key=lambda u: (u.path != "", u.path)
    )
    unit_dbs: set[str] = set()
    for unit in units:
        items: list[str] = []
        if unit.language:
            items.append(
                f"{unit.language} {unit.language_version}"
                if unit.language_version
                else unit.language
            )
        frameworks = sorted(
            (f for f in unit.frameworks if f not in ("Pydantic",)),
            key=lambda f: (_framework_rank(f), unit.frameworks.index(f)),
        )
        items.extend(
            f"{f} {unit.framework_versions[f]}" if f in unit.framework_versions else f
            for f in frameworks
        )
        items.extend(unit.databases)
        unit_dbs.update(unit.databases)
        items.extend(pm for pm in unit.package_managers if pm not in ("npm", "pip"))
        name = groups.get(unit.path, "Project")
        bucket = stack.setdefault(name, [])
        for item in items:
            if item not in bucket:
                bucket.append(item)
    extra_dbs = [
        d.value
        for d in ctx.detections["databases"].values()
        if d.value not in unit_dbs and d.confidence >= 0.5
    ]
    if extra_dbs:
        target = next((g for g in stack if g.startswith(("Backend", "App"))), None) or "Data"
        bucket = stack.setdefault(target, [])
        bucket.extend(d for d in sorted(extra_dbs) if d not in bucket)
    infra = [
        d.value
        for d in sorted(ctx.detections["infrastructure"].values(), key=lambda d: d.value)
        if d.confidence >= 0.5 and d.value not in ("GitHub Actions", "GitLab CI")
    ]
    if infra:
        stack["Infrastructure"] = infra
    return {k: v for k, v in stack.items() if v}
