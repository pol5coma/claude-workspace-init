"""Pure builders: author inputs -> catalog capability (manifest, fragments, payload files).

Nothing here writes to disk; `writer.py` does that.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from cwi import paths
from cwi.catalog.frontmatter import parse_frontmatter
from cwi.domain.enums import CapabilityType, ProjectType
from cwi.domain.errors import CWIError

HOOK_EVENTS = (
    "PreToolUse",
    "PostToolUse",
    "UserPromptSubmit",
    "Stop",
    "SubagentStop",
    "SessionStart",
    "SessionEnd",
    "Notification",
    "PreCompact",
)
TOOL_EVENTS = {"PreToolUse", "PostToolUse"}
JUNK = {".DS_Store", "Thumbs.db", "desktop.ini"}
JUNK_DIRS = {"__pycache__", ".pytest_cache", ".ruff_cache", ".git", "node_modules"}
_VAR_REF = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-[^}]*)?\}")


class AuthoringError(CWIError):
    """The capability could not be built from the given inputs."""


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    if not slug:
        raise AuthoringError(f"Cannot derive an id from '{value}'. Pass --id.")
    return slug


@dataclass
class Metadata:
    """Manifest fields shared by every capability type."""

    id: str | None = None
    name: str | None = None
    description: str | None = None
    default_selected: bool = False
    project_types: list[ProjectType] = field(default_factory=list)
    technologies: list[str] = field(default_factory=list)
    require_technology: bool = False
    dependencies: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    group: str | None = None  # family folder, e.g. "development-agents"
    group_defaults: list[ProjectType] = field(
        default_factory=list
    )  # preselect for these types via the family


@dataclass
class BuiltCapability:
    cap_type: CapabilityType
    id: str
    manifest: dict[str, Any]
    # payload-relative POSIX path -> source Path (copied) or str (written as text)
    payload: dict[str, Path | str] = field(default_factory=dict)
    fragments: dict[str, dict[str, Any]] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    group: str | None = None
    group_defaults: list[ProjectType] = field(default_factory=list)
    agent_frontmatter: bool = (
        False  # a "skill" whose frontmatter has `tools:` is almost surely an agent
    )

    @property
    def ref(self) -> str:
        return f"{self.cap_type.value}:{self.id}"


# ---------------------------------------------------------------------------------------------
# Frontmatter editing
# ---------------------------------------------------------------------------------------------


def _yaml_scalar(value: str) -> str:
    if re.search(r"[:#\[\]{}&*!|>'\"%@`]|^\s|\s$|^-", value) or "\n" in value:
        escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
        return f'"{escaped}"'
    return value


def set_frontmatter(text: str, updates: dict[str, str]) -> str:
    """Set top-level frontmatter keys, creating the block if missing. Other keys are untouched."""
    lines = text.splitlines()
    if lines and lines[0].strip() == "---" and "---" in (line.strip() for line in lines[1:]):
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
        head, body = lines[1:end], lines[end + 1 :]
    else:
        head, body = [], lines
    remaining = dict(updates)
    new_head: list[str] = []
    skipping = False
    for line in head:
        key = (
            line.split(":", 1)[0].strip() if line and line[0] not in " \t" and ":" in line else None
        )
        if key is not None:
            skipping = False
            if key in remaining:
                new_head.append(f"{key}: {_yaml_scalar(remaining.pop(key))}")
                skipping = True  # drop continuation lines of the replaced value
                continue
        elif skipping and line[:1] in (" ", "\t"):
            continue
        new_head.append(line)
    first = [f"name: {_yaml_scalar(remaining.pop('name'))}"] if "name" in remaining else []
    rest = [f"{k}: {_yaml_scalar(v)}" for k, v in remaining.items()]
    result = ["---", *first, *new_head, *rest, "---", *body]
    return "\n".join(result).rstrip("\n") + "\n"


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise AuthoringError(f"Cannot read {path}: {exc}") from exc


def _excluded(rel: Path, patterns: list[str]) -> bool:
    import fnmatch

    posix = rel.as_posix()
    return any(
        fnmatch.fnmatch(posix, pattern) or any(fnmatch.fnmatch(part, pattern) for part in rel.parts)
        for pattern in patterns
    )


def _iter_tree(directory: Path, exclude: list[str] | None = None):
    for path in sorted(directory.rglob("*")):
        rel = path.relative_to(directory)
        if exclude and _excluded(rel, exclude):
            continue
        if path.is_symlink():
            raise AuthoringError(f"Symlinks are not allowed in catalog payloads: {path}")
        if (
            any(part in JUNK_DIRS for part in rel.parts)
            or path.name in JUNK
            or path.suffix == ".pyc"
        ):
            continue
        if path.is_file():
            yield rel.as_posix(), path


def _require_file(path: Path, what: str) -> Path:
    path = path.expanduser()
    if not path.is_file():
        raise AuthoringError(f"{what} not found: {path}")
    return path


def _manifest(
    cap_type: CapabilityType, cid: str, meta: Metadata, name: str, description: str, **extra: Any
) -> dict[str, Any]:
    manifest: dict[str, Any] = {
        "schema_version": 1,
        "id": cid,
        "type": cap_type.value,
        "name": name,
        "description": description,
    }
    if meta.tags:
        manifest["tags"] = meta.tags
    if meta.default_selected:
        manifest["default_selected"] = True
    if meta.project_types or meta.technologies:
        rec: dict[str, Any] = {
            "project_types": [t.value for t in meta.project_types],
            "technologies": [t.lower() for t in meta.technologies],
        }
        # Technologies without project types are the only relevance signal: let them preselect alone.
        if meta.require_technology or (meta.technologies and not meta.project_types):
            rec["require_technology"] = True
        manifest["recommendation"] = rec
    manifest["dependencies"] = list(meta.dependencies)
    manifest["conflicts"] = list(meta.conflicts)
    manifest.update(extra)
    return manifest


def _title(cid: str) -> str:
    return cid.replace("-", " ").capitalize()


def _first_paragraph(body: str) -> str | None:
    for block in re.split(r"\n\s*\n", body):
        text = " ".join(
            line.strip() for line in block.splitlines() if not line.strip().startswith("#")
        ).strip()
        if text:
            return text[:300]
    return None


def _strip_frontmatter(text: str) -> str:
    lines = text.splitlines()
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                return "\n".join(lines[i + 1 :])
    return text


def looks_like_agent(front: dict[str, str] | None, text: str) -> list[str]:
    reasons = []
    if front and "tools" in front:
        reasons.append("its frontmatter has `tools:` (an agent field; skills use `allowed-tools:`)")
    if re.search(
        r"use this agent|invoke this agent|you are an? [a-z ]*(agent|reviewer|assistant)",
        text,
        re.I,
    ):
        reasons.append("its text describes an agent")
    return reasons


# ---------------------------------------------------------------------------------------------
# Builders per type
# ---------------------------------------------------------------------------------------------


def build_skill(
    source: Path,
    meta: Metadata,
    refs: list[Path],
    scripts: list[Path],
    *,
    convert_tools: bool = False,
    exclude: list[str] | None = None,
) -> BuiltCapability:
    source = source.expanduser()
    if source.is_dir():
        skill_md = source / "SKILL.md"
        if not skill_md.is_file():
            raise AuthoringError(f"No SKILL.md inside {source}")
        extra_files = [
            (rel, path) for rel, path in _iter_tree(source, exclude) if rel != "SKILL.md"
        ]
        default_name = source.name
    else:
        skill_md = _require_file(source, "Skill file")
        extra_files = []
        default_name = source.parent.name if source.name.upper() == "SKILL.MD" else source.stem

    text = _read_text(skill_md)
    front = parse_frontmatter(text) or {}
    cid = slugify(meta.id or front.get("name") or default_name)
    description = (
        meta.description or front.get("description") or _first_paragraph(_strip_frontmatter(text))
    )
    if not description:
        raise AuthoringError(
            "The skill needs a description (frontmatter `description:` or --description)."
        )

    built = BuiltCapability(CapabilityType.SKILL, cid, {})
    agent_signals = looks_like_agent(front, text)
    built.agent_frontmatter = "tools" in front and not convert_tools
    if agent_signals and not convert_tools:
        built.warnings.append(
            "This looks like an agent, not a skill: " + "; ".join(agent_signals) + "."
        )

    updates = {"name": cid}
    if not front.get("description"):
        updates["description"] = description
    if convert_tools and "tools" in front and "allowed-tools" not in front:
        updates["allowed-tools"] = front["tools"]
    content = set_frontmatter(text, updates)
    if convert_tools and "tools" in front:
        content = re.sub(r"(?m)^tools:.*\n", "", content, count=1)

    base = f"{paths.SKILLS_DIR}/{cid}"
    built.payload[f"{base}/SKILL.md"] = content
    for rel, path in extra_files:
        built.payload[f"{base}/{rel}"] = path
    for ref in refs:
        ref = _require_file(ref, "Reference file")
        built.payload[f"{base}/references/{ref.name}"] = ref
    for script in scripts:
        script = _require_file(script, "Script")
        built.payload[f"{base}/scripts/{script.name}"] = script
    built.manifest = _manifest(
        CapabilityType.SKILL, cid, meta, meta.name or _title(cid), description
    )
    return built


def build_agent(source: Path, meta: Metadata, scripts: list[Path]) -> BuiltCapability:
    source = _require_file(source, "Agent file")
    text = _read_text(source)
    front = parse_frontmatter(text)
    if front is None:
        raise AuthoringError(
            f"{source} has no YAML frontmatter. Agents need at least:\n---\nname: my-agent\ndescription: When to use it\n---"
        )
    cid = slugify(meta.id or front.get("name") or source.stem)
    description = meta.description or front.get("description")
    if not description:
        raise AuthoringError(
            "The agent needs a `description:` in its frontmatter (or --description)."
        )
    updates = {"name": cid}
    if not front.get("description"):
        updates["description"] = description
    built = BuiltCapability(CapabilityType.AGENT, cid, {})
    built.payload[paths.agent_file(cid, meta.group)] = set_frontmatter(text, updates)
    for script in scripts:
        script = _require_file(script, "Script")
        built.payload[f"{paths.CLAUDE_SCRIPTS_DIR}/{cid}/{script.name}"] = script
    # Agents see a short manifest description; long agent descriptions (with examples) are trimmed.
    short = description.replace("\\n", " ").split("<example>")[0].strip()
    short = re.sub(r"\s+", " ", short)[:300]
    built.manifest = _manifest(CapabilityType.AGENT, cid, meta, meta.name or _title(cid), short)
    return built


def _interpreter(filename: str) -> str:
    suffix = Path(filename).suffix
    return {
        ".py": "python3 ",
        ".sh": "bash ",
        ".bash": "bash ",
        ".js": "node ",
        ".mjs": "node ",
        ".cjs": "node ",
        ".ts": "npx tsx ",
    }.get(suffix, "")


def build_hook(
    script: Path,
    meta: Metadata,
    *,
    event: str,
    matcher: str | None,
    timeout: int | None,
    extra_files: list[Path] | None = None,
) -> BuiltCapability:
    script = _require_file(script, "Hook script")
    if event not in HOOK_EVENTS:
        raise AuthoringError(f"Unknown hook event '{event}'. Use one of: {', '.join(HOOK_EVENTS)}")
    if matcher and event not in TOOL_EVENTS:
        raise AuthoringError(
            f"--matcher only applies to tool events ({', '.join(sorted(TOOL_EVENTS))})"
        )
    cid = slugify(meta.id or script.stem)
    filename = f"{cid}{script.suffix}"
    target = f"{paths.HOOKS_DIR}/{filename}"
    handler: dict[str, Any] = {
        "type": "command",
        "command": f'{_interpreter(filename)}"${{CLAUDE_PROJECT_DIR}}/{target}"',
    }
    if timeout:
        handler["timeout"] = timeout
    group: dict[str, Any] = {"hooks": [handler]}
    if matcher:
        group = {"matcher": matcher, **group}
    description = meta.description or f"{event} hook" + (f" for {matcher}" if matcher else "")
    built = BuiltCapability(CapabilityType.HOOK, cid, {})
    built.payload[target] = script
    for extra in extra_files or []:
        extra = _require_file(extra, "Hook support file")
        built.payload[f"{paths.HOOKS_DIR}/{cid}/{extra.name}"] = extra
    built.fragments["settings.fragment.json"] = {"hooks": {event: [group]}}
    built.manifest = _manifest(
        CapabilityType.HOOK, cid, meta, meta.name or _title(cid), description
    )
    if not script.stat().st_mode & 0o111 and not _interpreter(filename):
        built.warnings.append(
            f"{script.name} is not executable and has no known interpreter; run chmod +x on it."
        )
    return built


def build_script(files: list[Path], meta: Metadata) -> BuiltCapability:
    if not files:
        raise AuthoringError("Pass at least one script file.")
    resolved = [_require_file(f, "Script") for f in files]
    cid = slugify(meta.id or resolved[0].stem)
    description = meta.description
    if not description:
        raise AuthoringError("Scripts need --description (what it does and when to run it).")
    built = BuiltCapability(CapabilityType.SCRIPT, cid, {})
    for path in resolved:
        built.payload[f"{paths.SCRIPTS_DIR}/{path.name}"] = path
    built.manifest = _manifest(
        CapabilityType.SCRIPT, cid, meta, meta.name or _title(cid), description
    )
    return built


def build_mcp(
    server_name: str,
    meta: Metadata,
    *,
    url: str | None,
    headers: dict[str, str],
    command: str | None,
    args: list[str],
    env: list[str],
    transport: str = "http",
) -> BuiltCapability:
    if bool(url) == bool(command):
        raise AuthoringError(
            "Pass exactly one of --url (remote server) or --command (local stdio server)."
        )
    cid = slugify(meta.id or server_name)
    server: dict[str, Any]
    if url:
        server = {"type": transport, "url": url}
        if headers:
            server["headers"] = headers  # remote servers take credentials via headers
    else:
        server = {"command": command, "args": list(args)}
        if env:
            server["env"] = {name: f"${{{name}}}" for name in env}
    referenced = set(env)
    for value in [url or "", command or "", *args, *headers.values()]:
        referenced.update(_VAR_REF.findall(value))
    description = meta.description or f"{server_name} MCP server"
    built = BuiltCapability(CapabilityType.MCP, cid, {})
    built.fragments["mcp.fragment.json"] = {"mcpServers": {server_name: server}}
    requirements = (
        {"env": [{"name": name, "description": ""} for name in sorted(referenced)]}
        if referenced
        else None
    )
    extra = {"requirements": requirements} if requirements else {}
    built.manifest = _manifest(
        CapabilityType.MCP, cid, meta, meta.name or server_name, description, **extra
    )
    return built


def parse_pairs(values: list[str], what: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in values:
        key, sep, value = item.partition("=")
        if not sep or not key.strip():
            raise AuthoringError(f"{what} must look like KEY=VALUE (got '{item}')")
        result[key.strip()] = value.strip()
    return result


def parse_project_types(raw: str | None) -> list[ProjectType]:
    if not raw:
        return []
    result = []
    for item in raw.split(","):
        item = item.strip().lower().replace("-", "_")
        if not item:
            continue
        try:
            result.append(ProjectType(item))
        except ValueError as exc:
            valid = ", ".join(t.value for t in ProjectType)
            raise AuthoringError(f"Unknown project type '{item}'. Use: {valid}") from exc
    return result


def parse_list(raw: str | None) -> list[str]:
    return [x.strip() for x in (raw or "").split(",") if x.strip()]
