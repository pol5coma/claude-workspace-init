"""Read Claude Code session transcripts that belong to a SPADO run (best effort, read-only).

Claude Code keeps one JSONL file per session under ``~/.claude/projects/<encoded-cwd>/`` and
each subagent under ``<session>/subagents/agent-<id>.jsonl`` with a ``.meta.json`` naming its
type and the ``Agent`` tool call that created it. The format is internal to Claude Code, so
every field is optional here and unreadable lines are skipped. Codex is not covered.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

log = logging.getLogger(__name__)

HOST = "host"  # pseudo-actor: the Claude Code session that the Human talks to
TOKEN_PATH = re.compile(
    r"actors/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\.token"
)
TEXT_LIMIT = 20_000
SUMMARY_LIMIT = 280
DELEGATION_TOOLS = {"Agent", "Task"}
_cache: dict[tuple[str, float, int], list[dict]] = {}


def default_base() -> Path:
    return Path.home() / ".claude" / "projects"


def project_dir(root: Path, base: Path | None = None) -> Path | None:
    """The transcript folder for `root`: Claude Code's encoded path, else a `cwd` match."""
    base = base or default_base()
    if not base.is_dir():
        return None
    root = root.resolve()
    encoded = base / re.sub(r"[^A-Za-z0-9]", "-", str(root))
    if encoded.is_dir():
        return encoded
    for candidate in sorted(base.iterdir()):
        sample = next(iter(sorted(candidate.glob("*.jsonl"))), None) if candidate.is_dir() else None
        if sample and any(line.get("cwd") == str(root) for line in _lines(sample)[:20]):
            return candidate
    return None


def _lines(path: Path) -> list[dict]:
    try:
        stat = path.stat()
    except OSError:
        return []
    key = (str(path), stat.st_mtime, stat.st_size)
    if key in _cache:
        return _cache[key]
    lines = []
    skipped = 0
    try:
        with path.open(encoding="utf-8", errors="replace") as handle:
            for raw in handle:
                try:
                    value = json.loads(raw)
                except json.JSONDecodeError:
                    skipped += 1
                    continue
                if isinstance(value, dict):
                    lines.append(value)
    except OSError:
        return []
    if skipped:
        log.warning("Skipped %d unreadable transcript lines in %s", skipped, path)
    _cache[key] = lines
    return lines


def _clip(text: str, limit: int = TEXT_LIMIT) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _summary(text: str) -> str:
    return _clip(" ".join(text.split()), SUMMARY_LIMIT)


def _blocks(line: dict) -> list[dict]:
    message = line.get("message")
    if not isinstance(message, dict):
        return []
    content = message.get("content")
    if isinstance(content, str):
        return [{"type": "text", "text": content}]
    return [b for b in content if isinstance(b, dict)] if isinstance(content, list) else []


def _texts(line: dict) -> str:
    return "\n".join(b.get("text", "") for b in _blocks(line) if b.get("type") == "text").strip()


def _human_prompt(line: dict) -> str | None:
    if line.get("type") != "user" or line.get("isSidechain") or line.get("isMeta"):
        return None
    blocks = _blocks(line)
    if any(b.get("type") == "tool_result" for b in blocks):
        return None
    text = _texts(line)
    # Slash-command invocations arrive wrapped in tags; keep their readable parts.
    text = re.sub(r"</?command-(name|message|args)>", " ", text)
    text = re.sub(r"<[^>]+>.*?</[^>]+>", "", text, flags=re.S).strip()
    return text or None


def _mentions(path: Path, needle: str) -> bool:
    try:
        return needle in path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False


def _session_files(folder: Path, run_id: str) -> list[Path]:
    sessions = []
    for main in sorted(folder.glob("*.jsonl")):
        subagents = sorted((folder / main.stem / "subagents").glob("agent-*.jsonl"))
        if _mentions(main, run_id) or any(_mentions(s, run_id) for s in subagents):
            sessions.append(main)
    return sessions


def signature(folder: Path | None) -> float:
    """Latest modification time of any transcript, for change detection."""
    if not folder or not folder.is_dir():
        return 0.0
    times = [p.stat().st_mtime for p in folder.glob("**/*.jsonl")]
    return max(times, default=0.0)


def _link(prompt: str, subagent_type: str, actors: list[dict]) -> str | None:
    match = TOKEN_PATH.search(prompt)
    known = {a["id"] for a in actors}
    if match and match.group(1) in known:
        return match.group(1)
    same_role = [a["id"] for a in actors if a["definition"].lower() == subagent_type.lower()]
    return same_role[0] if len(same_role) == 1 else None


def read(folder: Path | None, run_id: str, actors: list[dict]) -> dict:
    """Human prompts, delegation prompts and subagent threads for one run."""
    if not folder or not folder.is_dir():
        return {
            "available": False,
            "folder": str(folder) if folder else None,
            "entries": [],
            "threads": [],
        }
    human = next((a["id"] for a in actors if a["level"] == "human"), "def:Human")
    entries: list[dict] = []
    threads: list[dict] = []
    sessions = _session_files(folder, run_id)
    for main in sessions:
        session = main.stem
        delegations: dict[str, dict] = {}
        for line in _lines(main):
            stamp = line.get("timestamp")
            prompt = _human_prompt(line)
            if prompt:
                entries.append(_entry(line, session, "human_prompt", human, [HOST], prompt, stamp))
                continue
            if line.get("type") != "assistant" or line.get("isSidechain"):
                continue
            for block in _blocks(line):
                if block.get("type") == "tool_use" and block.get("name") in DELEGATION_TOOLS:
                    tool_input = block.get("input") or {}
                    delegations[block.get("id", "")] = {
                        "timestamp": stamp,
                        "uuid": line.get("uuid"),
                        "subagent_type": str(tool_input.get("subagent_type", "")),
                        "description": str(tool_input.get("description", "")),
                        "prompt": str(tool_input.get("prompt", "")),
                    }
                elif block.get("type") == "text" and block.get("text", "").strip():
                    entries.append(
                        _entry(line, session, "host_reply", HOST, [human], block["text"], stamp)
                    )
        for sub in sorted((folder / session / "subagents").glob("agent-*.jsonl")):
            meta = _meta(sub)
            delegation = delegations.get(meta.get("toolUseId", ""), {})
            lines = _lines(sub)
            first_prompt = next(
                (_texts(x) for x in lines if x.get("type") == "user" and _texts(x)), ""
            )
            prompt = delegation.get("prompt") or first_prompt
            subagent_type = delegation.get("subagent_type") or meta.get("agentType", "")
            actor = _link(prompt, subagent_type, actors) or f"agent:{sub.stem}"
            description = delegation.get("description") or meta.get("description", "")
            entries.append(
                {
                    "id": f"{session}:{sub.stem}:delegation",
                    "timestamp": delegation.get("timestamp")
                    or (lines[0].get("timestamp") if lines else None),
                    "source": "transcript",
                    "kind": "delegation_prompt",
                    "from": HOST,
                    "to": [actor],
                    "summary": f"{subagent_type or 'agent'}: {description}".strip(": "),
                    "text": _clip(prompt),
                    "session": session,
                    "subagent_type": subagent_type,
                }
            )
            thread = []
            for line in lines:
                stamp = line.get("timestamp")
                for block in _blocks(line):
                    if block.get("type") == "text" and block.get("text", "").strip():
                        thread.append(
                            {
                                "role": line.get("type"),
                                "timestamp": stamp,
                                "text": _clip(block["text"]),
                            }
                        )
                    elif block.get("type") == "tool_use":
                        command = (block.get("input") or {}).get("command")
                        item = {
                            "role": "tool",
                            "timestamp": stamp,
                            "tool": block.get("name"),
                            "text": _clip(str(command or json.dumps(block.get("input"))), 2000),
                        }
                        thread.append(item)
                        if isinstance(command, str) and re.search(r"\bspado\b", command):
                            entries.append(
                                {
                                    "id": f"{session}:{line.get('uuid')}:{block.get('id')}",
                                    "timestamp": stamp,
                                    "source": "transcript",
                                    "kind": "spado_command",
                                    "from": actor,
                                    "to": [],
                                    "summary": _summary(command),
                                    "text": _clip(command, 2000),
                                    "session": session,
                                }
                            )
            report = next(
                (_texts(x) for x in reversed(lines) if x.get("type") == "assistant" and _texts(x)),
                "",
            )
            if report:
                entries.append(
                    {
                        "id": f"{session}:{sub.stem}:report",
                        "timestamp": lines[-1].get("timestamp") if lines else None,
                        "source": "transcript",
                        "kind": "subagent_report",
                        "from": actor,
                        "to": [HOST],
                        "summary": _summary(report),
                        "text": _clip(report),
                        "session": session,
                    }
                )
            threads.append(
                {
                    "agent": sub.stem,
                    "actor": actor,
                    "session": session,
                    "subagent_type": subagent_type,
                    "description": description,
                    "messages": thread,
                }
            )
    return {
        "available": True,
        "folder": str(folder),
        "sessions": [m.stem for m in sessions],
        "entries": entries,
        "threads": threads,
    }


def _entry(line, session, kind, sender, to, text, stamp) -> dict:
    return {
        "id": f"{session}:{line.get('uuid')}:{kind}",
        "timestamp": stamp,
        "source": "transcript",
        "kind": kind,
        "from": sender,
        "to": to,
        "summary": _summary(text),
        "text": _clip(text),
        "session": session,
    }


def _meta(path: Path) -> dict:
    meta = path.with_suffix(".meta.json")
    try:
        value = json.loads(meta.read_text())
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}
