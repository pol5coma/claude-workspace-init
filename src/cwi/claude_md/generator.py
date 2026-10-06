"""Pure CLAUDE.md builder: structured spec in, Markdown out. No file I/O except template lookup."""

from __future__ import annotations

from importlib import resources
from pathlib import Path

from cwi import paths
from cwi.claude_md.defaults import ALWAYS_DANGEROUS, DANGEROUS_COMMANDS_BY_TECH, DEFAULT_SAFETY
from cwi.domain.models import ClaudeMdSpec, ProjectProfile, SizeReport

COMPACT_TOKENS = 800
REVIEW_TOKENS = 1500


def load_template(root: Path | None = None) -> str:
    """Project override at templates/CLAUDE.md, else the packaged template."""
    if root is not None:
        override = root / paths.rel(paths.TEMPLATES_DIR) / "CLAUDE.md"
        if override.is_file():
            text = override.read_text(encoding="utf-8")
            if "{{sections}}" in text:
                return text
    return (
        resources.files("cwi.claude_md").joinpath("templates/CLAUDE.md").read_text(encoding="utf-8")
    )


def profile_to_stack(profile: ProjectProfile) -> dict[str, list[str]]:
    if profile.stack:
        return {k: list(v) for k, v in profile.stack.items() if v}
    items = [*profile.languages, *profile.frameworks, *profile.databases]
    stack: dict[str, list[str]] = {}
    if items:
        stack["Project"] = list(dict.fromkeys(items))
    if profile.infrastructure:
        stack["Infrastructure"] = list(profile.infrastructure)
    return stack


def propose_dangerous_commands(profile: ProjectProfile) -> list[str]:
    techs = profile.technologies()
    commands: list[str] = []
    for tech, cmds in DANGEROUS_COMMANDS_BY_TECH.items():
        if tech in techs:
            commands.extend(cmds)
    commands.extend(ALWAYS_DANGEROUS)
    return list(dict.fromkeys(commands))


def default_spec(profile: ProjectProfile, title: str | None = None) -> ClaudeMdSpec:
    return ClaudeMdSpec(
        title=title
        or (f"{profile.name} — Project Instructions" if profile.name else "Project Instructions"),
        safety=list(DEFAULT_SAFETY),
        dangerous_commands=propose_dangerous_commands(profile),
        stack=profile_to_stack(profile),
        commands=list(profile.commands),
        architecture_pointer=profile.architecture_doc,
        additional_instructions=[],
    )


def render_sections(spec: ClaudeMdSpec) -> list[tuple[str, str]]:
    """Return (heading, body) pairs. Empty sections are never produced."""
    sections: list[tuple[str, str]] = []

    safety_lines = [*spec.safety]
    if spec.dangerous_commands:
        safety_lines.append(
            "Commands that always require explicit approval: "
            + ", ".join(f"`{c}`" for c in spec.dangerous_commands)
            + "."
        )
    if safety_lines:
        sections.append(("Safety", "\n\n".join(safety_lines)))

    stack = {k: v for k, v in spec.stack.items() if v}
    if stack:
        if len(stack) == 1 and next(iter(stack)) == "Project":
            body = "\n".join(f"- {item}" for item in next(iter(stack.values())))
        else:
            body = "\n\n".join(
                f"{group}:\n" + "\n".join(f"- {item}" for item in items)
                for group, items in stack.items()
            )
        sections.append(("Stack", body))

    if spec.commands:
        groups: dict[str, list[str]] = {}
        for cmd in spec.commands:
            groups.setdefault(cmd.group, []).append(f"- {cmd.label}: `{cmd.command}`")
        if len(groups) == 1:
            body = "\n".join(next(iter(groups.values())))
        else:
            body = "\n\n".join(f"{group}:\n" + "\n".join(lines) for group, lines in groups.items())
        sections.append(("Commands", body))

    if spec.architecture_pointer:
        pointer = spec.architecture_pointer.strip()
        sections.append(
            (
                "Architecture",
                f"For architecture details, read `{pointer}` before making structural changes.",
            )
        )

    additional = [i.strip() for i in spec.additional_instructions if i.strip()]
    if additional:
        sections.append(("Additional Instructions", "\n".join(f"- {i}" for i in additional)))
    return sections


def render_claude_md(spec: ClaudeMdSpec, template: str | None = None) -> str:
    """Pure renderer: ClaudeMdSpec -> Markdown string."""
    frame = template if template is not None else "# {{title}}\n\n{{sections}}\n"
    body = "\n\n".join(f"## {heading}\n\n{text}" for heading, text in render_sections(spec))
    text = frame.replace("{{title}}", spec.title).replace("{{sections}}", body)
    return text.rstrip() + "\n"


def estimate_size(text: str) -> SizeReport:
    """Rough size feedback. Tokens are estimated (~4 characters per token), not tokenized."""
    lines = text.count("\n") + (0 if text.endswith("\n") or not text else 1)
    chars = len(text)
    tokens = max(1, round(chars / 4)) if chars else 0
    if tokens < COMPACT_TOKENS:
        verdict, message = "compact", "Healthy global context size"
    elif tokens <= REVIEW_TOKENS:
        verdict, message = (
            "review",
            "Review recommended: is every instruction needed in almost every session?",
        )
    else:
        verdict, message = "large", "Consider moving scoped instructions into Skills or Rules"
    return SizeReport(
        lines=lines, characters=chars, estimated_tokens=tokens, verdict=verdict, message=message
    )
