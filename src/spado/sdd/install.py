from __future__ import annotations

import json
import shlex
import sys
from importlib.resources import files
from pathlib import Path

from spado.catalog.frontmatter import parse_frontmatter
from spado.install.filesystem import FileSystem
from spado.runtime.config import dump
from spado.runtime.install import install, sha
from spado.sdd.models import Settings, State

SKILLS = (
    "product-roadmap",
    "feature-spec",
    "feature-roadmap",
    "feature-tdd-start",
    "feature-tdd-build",
    "feature-close",
)
AGENTS = {"sdd-worker", "architect-reviewer", "code-reviewer", "security-reviewer"}


def native_agent(cap, host):
    """Reviewed translation for SDD's four known agents, never arbitrary Claude agents."""
    output = {}
    for rel in cap.payload_files:
        body = (cap.payload_dir / rel).read_text()
        if rel.endswith(".md") and "/agents/" in rel:
            front = parse_frontmatter(body)
            instructions = body.split("---", 2)[2].strip()
            instructions += (
                "\n\nWhen assigned SDD work, read .workflow/PROTOCOL.md and the exact assignment. "
                "Use repository evidence; no context-manager service is required. "
                "Reviewers never modify files, commit, approve transitions or delegate. "
                "Report concrete blockers, recommendations and uncertainties; never invent measurements."
            )
            if host == "claude":
                output[rel] = body.encode()
            else:
                instructions = instructions.replace(".claude/scripts/", ".codex/scripts/")
                output[f".codex/agents/{cap.id}.toml"] = (
                    f"name = {json.dumps(cap.id)}\ndescription = {json.dumps(front['description'])}\n"
                    f"developer_instructions = {json.dumps(instructions)}\n"
                ).encode()
        else:
            output[rel.replace(".claude/", f".{host}/", 1)] = body.encode()
    return output


def guard(root, host, cap):
    directory = ".claude" if host == "claude" else ".codex"
    source = cap.payload_dir / ".claude/hooks/sdd-guard.py"
    target = f"{directory}/hooks/sdd-guard.py"
    command = f"{shlex.quote(sys.executable)} {shlex.quote(str(root / target))} --host {host}"
    hooks = {}
    for event in (
        "SessionStart",
        "SubagentStart",
        "PreToolUse",
        "PostToolUse",
        "Stop",
        "SubagentStop",
    ):
        group = {"hooks": [{"type": "command", "command": command, "timeout": 30}]}
        if event in {"PreToolUse", "PostToolUse"}:
            group["matcher"] = ".*"
        hooks[event] = [group]
    return {target: source.read_bytes()}, {"hooks": hooks}


def setup(root: Path, catalog: Path, hosts: list[str] | None, dry_run=False):
    from spado.adapters.capabilities import render_capabilities

    fs = FileSystem(root)
    config_path = fs.path(".workflow/config.json")
    existing = (
        Settings.model_validate_json(config_path.read_text()) if config_path.exists() else None
    )
    if not hosts:
        if existing:
            hosts = existing.hosts
        elif fs.path(".spado/project.json").exists():
            hosts = json.loads(fs.path(".spado/project.json").read_text())["hosts"]
        elif sys.stdin.isatty():
            import typer

            choice = typer.prompt("Install SDD for claude, codex, or both", default="both")
            hosts = ["claude", "codex"] if choice == "both" else [choice]
        else:
            raise ValueError("SDD setup requires --host in a non-interactive terminal")
    cfg = existing or Settings(hosts=hosts)
    cfg = Settings.model_validate({**cfg.model_dump(), "hosts": sorted(set(cfg.hosts + hosts))})
    merges = {}
    for name in (
        ".claude/settings.json",
        ".codex/hooks.json",
        ".codex/config.toml",
        "AGENTS.md",
        "CLAUDE.md",
        ".workflow/config.json",
    ):
        p = fs.path(name)
        if p.is_file():
            merges[name] = sha(p.read_bytes())
    selected = [f"skill:{name}" for name in SKILLS] + ["hook:sdd-guard"]
    desired = render_capabilities(root, catalog, cfg.hosts, selected)
    for host in cfg.hosts:
        skill_root = ".claude/skills" if host == "claude" else ".agents/skills"
        for name in SKILLS:
            path = f"{skill_root}/{name}/SKILL.md"
            body = desired[path].decode()
            if host == "claude" and "disable-model-invocation:" not in body:
                body = body.replace("---\n", "---\ndisable-model-invocation: true\n", 1)
            desired[path] = body.encode()
            if host == "codex":
                desired[f"{skill_root}/{name}/agents/openai.yaml"] = (
                    b"policy:\n  allow_implicit_invocation: false\n"
                )
    desired[".workflow/config.json"] = dump(cfg.model_dump()).encode()
    state = fs.path(".workflow/state.json")
    if state.exists():
        State.model_validate_json(state.read_text())
    desired[".workflow/state.json"] = (
        state.read_bytes() if state.exists() else dump(State().model_dump()).encode()
    )
    desired[".workflow/.gitignore"] = b"state.json\n*.lock\nresults/\n"
    desired[".workflow/PROTOCOL.md"] = files("spado.sdd").joinpath("PROTOCOL.md").read_bytes()
    block = (
        "<!-- spado:sdd:start -->\n## SDD workflow\n"
        "Read `.workflow/PROTOCOL.md` for SDD work. Invoke phases explicitly; do not use "
        "feature-workflow for an active SDD feature. State transitions and checks use `spado sdd`. "
        "Never manufacture Human approval. Supervising a run delegates intermediate reviews, "
        "not final feature acceptance.\n<!-- spado:sdd:end -->"
    )
    for name in ("AGENTS.md", "CLAUDE.md"):
        target = fs.path(name)
        body = target.read_text() if target.exists() else ""
        if "<!-- spado:sdd:start -->" not in body:
            desired[name] = (body.rstrip() + "\n\n" + block + "\n").lstrip().encode()
    inventory = []
    owned_file = fs.path(".spado/installation.json")
    owned = json.loads(owned_file.read_text()).get("files", {}) if owned_file.exists() else {}
    for name, body in sorted(desired.items()):
        path = fs.path(name)
        old = path.read_bytes() if path.exists() else None
        action = "created" if old is None else "preserved" if old == body else "updated"
        if old is not None and old != body and sha(old) not in {owned.get(name), merges.get(name)}:
            action = "conflict"
        inventory.append({"path": name, "action": action})
    conflicts = [x for x in inventory if x["action"] == "conflict"]
    if conflicts:
        raise ValueError("SDD installation conflicts; nothing written:\n" + dump(inventory))
    result = install(root, desired, dry_run=dry_run, merge_preconditions=merges)
    covered = {x["path"] for x in inventory}
    inventory.extend(
        {"path": p, "action": "updated" if fs.path(p).exists() and dry_run else "created"}
        for p in result["writes"]
        if p not in covered
    )
    result.update(
        inventory=inventory,
        hosts=cfg.hosts,
        dry_run=dry_run,
        activation=[
            "Review/trust project hooks in each host; restart/reload host resources if required. "
            "No hook-trust or permission bypass is installed."
        ],
        next="Commit installation files. Invoke product-roadmap or feature-spec explicitly.",
    )
    return result
