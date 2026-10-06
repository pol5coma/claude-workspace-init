"""Non-destructive CLAUDE.md merging and instruction triage."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_HEADING = re.compile(r"^##\s+(.+?)\s*#*\s*$")


@dataclass
class MergeResult:
    content: str
    added_sections: list[str] = field(default_factory=list)
    kept_sections: list[str] = field(default_factory=list)

    @property
    def changed(self) -> bool:
        return bool(self.added_sections)


def split_sections(text: str) -> tuple[str, list[tuple[str, str]]]:
    """Split Markdown into (preamble, [(heading, block_text_including_heading)])."""
    preamble: list[str] = []
    sections: list[tuple[str, list[str]]] = []
    in_fence = False
    for line in text.splitlines():
        if line.strip().startswith(("```", "~~~")):
            in_fence = not in_fence
        match = None if in_fence else _HEADING.match(line)
        if match:
            sections.append((match.group(1).strip(), [line]))
        elif sections:
            sections[-1][1].append(line)
        else:
            preamble.append(line)
    return "\n".join(preamble), [(h, "\n".join(lines).rstrip()) for h, lines in sections]


def _norm(heading: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", heading.lower()).strip()


def merge_claude_md(existing: str, generated: str) -> MergeResult:
    """Keep every existing section untouched; append generated sections whose heading is absent."""
    _, existing_sections = split_sections(existing)
    _, generated_sections = split_sections(generated)
    existing_keys = {_norm(h) for h, _ in existing_sections}
    added: list[str] = []
    blocks: list[str] = []
    for heading, block in generated_sections:
        if _norm(heading) in existing_keys:
            continue
        added.append(heading)
        blocks.append(block)
    kept = [h for h, _ in existing_sections]
    if not blocks:
        return MergeResult(content=existing, added_sections=[], kept_sections=kept)
    base = existing.rstrip()
    content = (base + "\n\n" if base else "") + "\n\n".join(blocks) + "\n"
    return MergeResult(content=content, added_sections=added, kept_sections=kept)


@dataclass
class InstructionAdvice:
    scoped: bool
    destination: str | None
    reason: str


_PROCEDURE_HINTS = (
    "whenever implementing",
    "when implementing",
    "step 1",
    "follow these steps",
    "steps:",
    "procedure",
    "checklist",
)
_SCOPED_HINTS = {
    "api": ("endpoint", "api route", "controller", "rest api", "graphql"),
    "frontend": ("component", "css", "tailwind", "styling", "react hook"),
    "database": ("migration", "schema change", "sql query", "orm model"),
    "testing": ("unit test", "test file", "fixtures", "mock"),
}


def classify_instruction(text: str) -> InstructionAdvice:
    """Heuristic triage for 'additional instructions' (guide section 36). Advisory only."""
    lowered = text.lower().strip()
    numbered = len(re.findall(r"(?m)^\s*\d+[.)]\s+", text))
    if len(text) > 300 or numbered >= 3 or any(h in lowered for h in _PROCEDURE_HINTS):
        return InstructionAdvice(
            scoped=True,
            destination="Skill",
            reason="This looks like a reusable procedure rather than global project context.",
        )
    for area, hints in _SCOPED_HINTS.items():
        if any(h in lowered for h in hints):
            return InstructionAdvice(
                scoped=True,
                destination="scoped rule or Skill",
                reason=f"This instruction appears specific to {area} work.",
            )
    return InstructionAdvice(
        scoped=False, destination=None, reason="Looks like a global instruction."
    )
