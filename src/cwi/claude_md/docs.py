"""Project docs skeleton (pure): where requirements, architecture and decisions live."""

from __future__ import annotations

from importlib import resources
from pathlib import Path

from cwi.claude_md.generator import (
    ARCHITECTURE_TEMPLATE_MARKER,
    DOCS_ARCHITECTURE,
    DOCS_DECISIONS,
    DOCS_GLOSSARY,
    DOCS_SPECS,
)
from cwi.domain.models import ProjectProfile

_TEMPLATES = {
    DOCS_ARCHITECTURE: "architecture.md",
    DOCS_GLOSSARY: "glossary.md",
    f"{DOCS_SPECS}README.md": "specs-readme.md",
    f"{DOCS_SPECS}_template.md": "spec-template.md",
    f"{DOCS_DECISIONS}README.md": "decisions-readme.md",
    f"{DOCS_DECISIONS}0000-template.md": "decision-template.md",
}


def _template(name: str) -> str:
    return (
        resources.files("cwi.claude_md")
        .joinpath(f"templates/docs/{name}")
        .read_text(encoding="utf-8")
    )


def _split_version(item: str) -> tuple[str, str]:
    parts = item.rsplit(" ", 1)
    if len(parts) == 2 and any(ch.isdigit() for ch in parts[1]) and parts[1][0].isdigit():
        return parts[0], parts[1]
    return item, ""


def versions_table(profile: ProjectProfile) -> str:
    rows = []
    for group, items in (profile.stack or {}).items():
        for item in items:
            name, version = _split_version(item)
            rows.append(f"| {group} | {name} | {version or '<!-- set the version in use -->'} |")
    return "\n".join(rows) or "| <!-- area --> | <!-- technology --> | <!-- version --> |"


def scaffold_files(
    profile: ProjectProfile, project_name: str, *, include_architecture: bool = True
) -> dict[str, str]:
    """Relative path -> content for the docs skeleton. Callers create only missing files."""
    files: dict[str, str] = {}
    for path, template in _TEMPLATES.items():
        if path == DOCS_ARCHITECTURE and not include_architecture:
            continue
        text = _template(template)
        text = text.replace("{{project}}", project_name).replace(
            "{{versions}}", versions_table(profile)
        )
        files[path] = text
    return files


def architecture_is_template(path: Path) -> bool:
    """True when the architecture doc will be scaffolded or still holds the CWI template marker."""
    if not path.exists():
        return True
    try:
        return (
            ARCHITECTURE_TEMPLATE_MARKER in path.read_text(encoding="utf-8", errors="replace")[:500]
        )
    except OSError:
        return False
