"""Native lifecycle guards. These are not an OS security boundary."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from spado.sdd.engine import approved_inputs, checks, integrity
from spado.sdd.store import read, snapshot


def inspect_event(root: Path, payload: dict) -> dict:
    state = read(root)
    run = state.active
    event = payload.get("hook_event_name", "")
    if not run or run.status == "complete":
        return {}
    if event in {"SessionStart", "SubagentStart"}:
        return {
            "hookSpecificOutput": {
                "hookEventName": event,
                "additionalContext": f"SDD {run.slug}: {run.phase}, milestone {run.milestone}, {run.status}. "
                "Read .workflow/PROTOCOL.md. Never advance phases or approve on behalf of the Human. "
                "A fresh worker must receive only its explicit assignment, not conversation history.",
            }
        }
    if event in {"Stop", "SubagentStop"}:
        # A worker must be able to return its report before the controller runs checks.
        # Only an actually submitted result is a completion claim enforced here.
        if run.status != "awaiting_review":
            return {}
        integrity(root, run)
        approved_inputs(root, run)
        if run.submitted_snapshot != snapshot(root):
            raise ValueError("SDD submitted result is stale; return control and request changes")
        return {}
    if event not in {"PreToolUse", "PostToolUse"}:
        return {}
    tool = payload.get("tool_name", "")
    args = payload.get("tool_input", {})
    text = json.dumps(args) if not isinstance(args, str) else args
    paths = []
    if isinstance(args, dict):
        paths.extend(str(args[k]) for k in ("file_path", "path") if k in args)
    paths.extend(
        re.findall(r"\*\*\* (?:Add|Update|Delete) File: ([^\n]+)", text.replace("\\n", "\n"))
    )
    scratch_only = bool(paths) and all(
        p.removeprefix(str(root) + "/").startswith(".workflow/results/") for p in paths
    )
    if scratch_only:
        return {}
    # Read/status/recovery must remain possible even after an integrity failure.
    writing = tool in {"Edit", "Write", "MultiEdit", "NotebookEdit", "apply_patch"}
    shell = tool in {"Bash", "exec_command", "shell", "shell_command"}
    shell_write = shell and bool(
        re.search(
            r"(?:\b(?:rm|mv|cp|tee|touch|mkdir)\b|\b(?:sed|perl)\s+-i\b|(?<![2])>(?!&)|)", text
        )
    )
    if event == "PreToolUse" and (writing or shell_write):
        if ".workflow/state.json" in text or ".workflow/config.json" in text:
            raise ValueError(
                "SDD state/configuration cannot be edited by workers; use the transition API"
            )
        check_plan = (
            run.phase == "red"
            and run.status in {"pending", "paused", "blocked"}
            and bool(paths)
            and all(
                p.removeprefix(str(root) + "/") == f"docs/features/{run.slug}/CHECKS.json"
                for p in paths
            )
        )
        if run.status != "in_progress" and not check_plan:
            raise ValueError("SDD has not authorized edits: begin or reopen the current phase")
        approved_inputs(root, run)
        if run.frozen:
            integrity(root, run)
            names = [p for p in run.frozen if not p.startswith("@")]
            if any(p in text for p in names) or "CHECKS.json" in text:
                raise ValueError("Tests and test configuration are frozen; reopen Red explicitly")
            # New test files must also be protected, not only the frozen inventory.
            paths = re.findall(
                r'(?:"(?:file_path|path)"\s*:\s*"([^"\n]+)"|\*\*\* (?:Add|Update|Delete) File: ([^\n]+))',
                text.replace("\\n", "\n"),
            )
            cfg = checks(root, run)
            for pair in paths:
                candidate = next(p for p in pair if p)
                rel = candidate.removeprefix(str(root) + "/")
                if any(Path(rel).match(p) for p in cfg.protected):
                    raise ValueError("New or renamed test files are protected during Green/Close")
        if run.phase in {"spec", "roadmap"} and writing:
            paths = re.findall(r'"(?:file_path|path)"\s*:\s*"([^"\n]+)"', text)
            patches = re.findall(
                r"\*\*\* (?:Add|Update|Delete) File: ([^\n]+)", text.replace("\\n", "\n")
            )
            if any(not p.endswith(".md") for p in paths + patches):
                raise ValueError("Spec and roadmap phases may only write Markdown documentation")
    if event == "PostToolUse" and (writing or shell):
        integrity(root, run)
    return {}


def main(root: Path, host: str):
    payload = {}
    try:
        payload = json.load(sys.stdin)
        result = inspect_event(root, payload)
        print(json.dumps(result))
    except (ValueError, OSError, KeyError) as exc:
        reason = str(exc)
        event = payload.get("hook_event_name")
        if event == "PreToolUse":
            print(
                json.dumps(
                    {
                        "hookSpecificOutput": {
                            "hookEventName": "PreToolUse",
                            "permissionDecision": "deny",
                            "permissionDecisionReason": reason,
                        }
                    }
                )
            )
        elif event in {"Stop", "SubagentStop"}:
            print(json.dumps({"decision": "block", "reason": reason}))
        else:
            print(reason, file=sys.stderr)
            raise SystemExit(2) from exc
