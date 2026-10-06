"""Minimal YAML-frontmatter reader (top-level `key: value` pairs only).

CWI only needs to confirm that `name` and `description` exist; it deliberately does not
interpret the rest of a Skill or Agent definition.
"""

from __future__ import annotations


def parse_frontmatter(text: str) -> dict[str, str] | None:
    """Return top-level frontmatter keys, or None when the file has no frontmatter block."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    result: dict[str, str] = {}
    current_key: str | None = None
    for line in lines[1:]:
        if line.strip() == "---":
            return result
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line[0] in " \t":
            # Continuation of a folded/multiline value or a nested mapping.
            if current_key is not None:
                result[current_key] = (result[current_key] + " " + line.strip()).strip()
            continue
        key, sep, value = line.partition(":")
        if not sep:
            continue
        current_key = key.strip()
        value = value.strip()
        if value in {">", "|", ">-", "|-"}:
            value = ""
        result[current_key] = value.strip("\"'")
    return None  # unterminated block
