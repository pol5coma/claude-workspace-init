"""Installation planner. Pure with respect to the repository: it reads, it never writes.

Inputs: scan, profile, state, catalog, selection, CLAUDE.md decision and user resolutions.
Output: an InstallationPlan that is the single source of truth for the executor.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from cwi import __version__, paths
from cwi.domain.enums import SELECTION_ORDER, CapabilityType, ClaudeMdMode, OperationType
from cwi.domain.errors import ConflictError, PlanError
from cwi.domain.models import (
    LAYOUT_AGENTS,
    Capability,
    Catalog,
    ClaudeMdDecision,
    CWIState,
    EnvRequirement,
    HookEntryRef,
    InstallationPlan,
    ManagedFile,
    PlannedOperation,
    ProjectProfile,
)
from cwi.install.json_merge import (
    dump_json,
    merge_hooks,
    merge_mcp,
    remove_hooks,
)
from cwi.planning.cleanup import plan_cleanup
from cwi.planning.safety import resolve_inside
from cwi.state.hashing import sha256_file, sha256_text
from cwi.state.repository import StateRepository

CLAUDE_MD_OWNER = "claude-md"
AGENTS_MD_OWNER = "agents-md"
DOCS_OWNER = "docs"
INSTRUCTION_OWNERS = {CLAUDE_MD_OWNER, AGENTS_MD_OWNER}
STATE_OWNER = "cwi-state"

# Directories that are never removed even when CWI empties them.
_STOP_DIRS = {
    paths.rel(paths.CLAUDE_DIR),
    paths.rel(paths.SKILLS_DIR),
    paths.rel(paths.AGENTS_DIR),
    paths.rel(paths.HOOKS_DIR),
    paths.rel(paths.CLAUDE_SCRIPTS_DIR),
    paths.rel(paths.SCRIPTS_DIR),
}


# ---------------------------------------------------------------------------------------------
# Decisions the user must take before a plan can be final
# ---------------------------------------------------------------------------------------------


@dataclass
class FileDecision:
    kind: str  # "user_file" | "modified_managed" | "modified_removed"
    target: str
    owner: str
    source: Path | None = None  # catalog version (None for removals)

    @property
    def key(self) -> str:
        return f"file:{self.target}"


@dataclass
class McpDecision:
    name: str
    owner: str
    existing: dict[str, Any]
    incoming: dict[str, Any]

    @property
    def key(self) -> str:
        return f"mcp:{self.name}"


@dataclass
class PlanInputs:
    root: Path
    profile: ProjectProfile
    catalog: Catalog | None
    state: CWIState | None
    claude_md: ClaudeMdDecision
    selected: list[str]
    # decision key -> "keep" | "replace" (files/MCP) or "delete" (modified removals)
    resolutions: dict[str, str] = field(default_factory=dict)
    cleanup_template: bool = False
    cleanup_catalog: bool = True
    now: str = "1970-01-01T00:00:00Z"


@dataclass
class _Builder:
    inputs: PlanInputs
    ops: list[PlannedOperation] = field(default_factory=list)
    mkdirs: set[str] = field(default_factory=set)
    managed: dict[str, ManagedFile] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    decisions: list[FileDecision | McpDecision] = field(default_factory=list)
    settings_hooks: dict[str, list[HookEntryRef]] = field(default_factory=dict)
    mcp_servers: dict[str, ManagedFile] = field(default_factory=dict)
    docs_scaffolded: list[str] = field(default_factory=list)

    @property
    def root(self) -> Path:
        return self.inputs.root

    def abs(self, rel: str) -> Path:
        return resolve_inside(self.root, rel)

    def ensure_parent_dirs(self, rel: str) -> None:
        parts = Path(rel).parts[:-1]
        for i in range(1, len(parts) + 1):
            directory = "/".join(parts[:i])
            if directory in self.mkdirs:
                continue
            path = self.abs(directory)
            if path.exists():
                if not path.is_dir():
                    raise PlanError(
                        f"Cannot create directory '{directory}': a file exists at that path"
                    )
                continue
            self.mkdirs.add(directory)
            self.ops.append(
                PlannedOperation(
                    type=OperationType.MKDIR,
                    target=directory,
                    owner="cwi",
                    reason="create directory",
                )
            )

    def resolution(self, key: str) -> str | None:
        return self.inputs.resolutions.get(key)


def _ordered(refs: list[str]) -> list[str]:
    rank = {t.value: i for i, t in enumerate(SELECTION_ORDER)}
    return sorted(refs, key=lambda r: (rank.get(r.split(":", 1)[0], 99), r))


def _read_json_file(path: Path, label: str) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PlanError(
            f"{label} is not valid JSON ({exc.msg}, line {exc.lineno}). Fix it before running cwi init."
        ) from exc
    if not isinstance(data, dict):
        raise PlanError(f"{label} must contain a JSON object. Fix it before running cwi init.")
    return data


def _server_hash(server: Any) -> str:
    return sha256_text(json.dumps(server, sort_keys=True))


# ---------------------------------------------------------------------------------------------
# Capability payloads
# ---------------------------------------------------------------------------------------------


def _plan_payload(b: _Builder, cap: Capability) -> None:
    prev = b.inputs.state.managed_files if b.inputs.state else {}
    for rel in cap.payload_files:
        source = cap.payload_dir / rel
        target = b.abs(rel)
        src_hash = sha256_file(source)
        if not target.exists():
            b.ensure_parent_dirs(rel)
            b.ops.append(
                PlannedOperation(
                    type=OperationType.COPY,
                    target=rel,
                    source=str(source),
                    after_hash=src_hash,
                    owner=cap.ref,
                    reason=f"install {cap.ref}",
                )
            )
            b.managed[rel] = ManagedFile(owner=cap.ref, sha256=src_hash)
            continue
        if not target.is_file():
            raise PlanError(f"Cannot install '{rel}': a directory exists at that path")
        current = sha256_file(target)
        record = prev.get(rel)
        owned = record is not None and record.owner == cap.ref
        if current == src_hash:
            b.managed[rel] = ManagedFile(owner=cap.ref, sha256=src_hash)
            continue
        if owned and record.user_kept and current == record.sha256:
            b.managed[rel] = record  # user's kept version, still untouched since
            continue
        if owned and current == record.sha256:
            # CWI-managed and unmodified: safe to refresh to the catalog version.
            b.ops.append(
                PlannedOperation(
                    type=OperationType.COPY,
                    target=rel,
                    source=str(source),
                    before_hash=current,
                    after_hash=src_hash,
                    owner=cap.ref,
                    reason=f"update {cap.ref} to catalog version",
                )
            )
            b.managed[rel] = ManagedFile(owner=cap.ref, sha256=src_hash)
            continue
        decision = FileDecision(
            kind="modified_managed" if owned else "user_file",
            target=rel,
            owner=cap.ref,
            source=source,
        )
        choice = b.resolution(decision.key)
        if choice == "replace":
            b.ops.append(
                PlannedOperation(
                    type=OperationType.COPY,
                    target=rel,
                    source=str(source),
                    before_hash=current,
                    after_hash=src_hash,
                    owner=cap.ref,
                    reason=f"replace with {cap.ref} catalog version (user approved)",
                )
            )
            b.managed[rel] = ManagedFile(owner=cap.ref, sha256=src_hash)
        elif choice == "keep":
            if owned:
                b.managed[rel] = ManagedFile(owner=cap.ref, sha256=current, user_kept=True)
            else:
                b.warnings.append(
                    f"Kept existing user file {rel}; {cap.ref} may be incomplete without its version"
                )
        else:
            b.decisions.append(decision)


def _plan_removals(b: _Builder, removed: list[str]) -> None:
    state = b.inputs.state
    if state is None:
        return
    deleted_dirs: set[str] = set()
    for rel, record in sorted(state.managed_files.items()):
        if record.owner not in removed:
            continue
        target = b.abs(rel)
        if not target.is_file():
            continue
        current = sha256_file(target)
        if current == record.sha256 and not record.user_kept:
            choice = "delete"
        else:
            decision = FileDecision(kind="modified_removed", target=rel, owner=record.owner)
            choice = b.resolution(decision.key)
            if choice is None:
                b.decisions.append(decision)
                continue
        if choice == "delete":
            b.ops.append(
                PlannedOperation(
                    type=OperationType.DELETE,
                    target=rel,
                    before_hash=current,
                    owner=record.owner,
                    reason=f"remove deselected {record.owner}",
                )
            )
            parent = str(Path(rel).parent.as_posix())
            while parent not in ("", ".") and parent not in _STOP_DIRS:
                deleted_dirs.add(parent)
                parent = str(Path(parent).parent.as_posix())
        # "keep": file becomes user-owned (not re-added to managed files)
    for directory in sorted(deleted_dirs, key=lambda d: -d.count("/")):
        b.ops.append(
            PlannedOperation(
                type=OperationType.DELETE_DIR,
                target=directory,
                owner="cwi",
                reason="remove directory left empty by deselection",
                only_if_empty=True,
            )
        )


# ---------------------------------------------------------------------------------------------
# settings.json and .mcp.json
# ---------------------------------------------------------------------------------------------


def _plan_settings(b: _Builder, hook_caps: list[Capability], removed: list[str]) -> None:
    rel = paths.rel(paths.SETTINGS_FILE)
    path = b.abs(rel)
    current = _read_json_file(path, rel)
    settings = current or {}
    state = b.inputs.state
    prev_hooks = state.settings_hooks if state else {}

    to_remove = [ref for owner in removed for ref in prev_hooks.get(owner, [])]
    if to_remove:
        settings = remove_hooks(settings, to_remove)
    for cap in hook_caps:
        assert cap.settings_fragment is not None
        try:
            result = merge_hooks(settings, cap.settings_fragment)
        except ValueError as exc:
            raise PlanError(f"{rel}: {exc}") from exc
        settings = result.settings
        previously_owned = {
            (r.event, r.matcher, r.type, r.command) for r in prev_hooks.get(cap.ref, [])
        }
        owned = list(result.added)
        owned += [
            r
            for r in result.already_present
            if (r.event, r.matcher, r.type, r.command) in previously_owned
        ]
        foreign = [r for r in result.already_present if r not in owned]
        if foreign:
            b.warnings.append(
                f"{cap.ref}: identical hook already configured by the project; it stays user-owned"
            )
        if owned:
            b.settings_hooks[cap.ref] = owned
        for existing, incoming in result.neighbours:
            if existing.command in {r.command for r in prev_hooks.get(cap.ref, [])}:
                continue
            b.warnings.append(
                f"{incoming.event}/{incoming.matcher or '*'}: existing hook `{existing.command}` will run "
                f"alongside {cap.ref} (both coexist)"
            )
    if current is None and not settings:
        return
    if current is not None and settings == current:
        return
    if current is not None:
        b.warnings.append(f"{rel} already exists; merge preserves all existing settings and hooks")
    content = dump_json(settings)
    b.ensure_parent_dirs(rel)
    b.ops.append(
        PlannedOperation(
            type=OperationType.MERGE_JSON,
            target=rel,
            before_hash=sha256_file(path) if current is not None else None,
            after_content=content,
            after_hash=sha256_text(content),
            owner="hooks",
            reason="merge selected hooks into Claude settings",
        )
    )


def _plan_mcp(b: _Builder, mcp_caps: list[Capability], removed: list[str]) -> None:
    rel = paths.rel(paths.MCP_FILE)
    path = b.abs(rel)
    current = _read_json_file(path, rel)
    config = json.loads(json.dumps(current)) if current else {}
    state = b.inputs.state
    prev = state.mcp_servers if state else {}

    servers = config.get("mcpServers") if isinstance(config.get("mcpServers"), dict) else None
    for name, record in sorted(prev.items()):
        if record.owner in removed and servers and name in servers:
            if _server_hash(servers[name]) == record.sha256:
                del servers[name]
            else:
                b.warnings.append(
                    f"MCP server '{name}' was modified after CWI installed it; it is kept as user configuration"
                )
    if (
        servers is not None
        and not servers
        and current
        and "mcpServers" in current
        and current["mcpServers"]
    ):
        del config["mcpServers"]

    for cap in mcp_caps:
        assert cap.mcp_fragment is not None
        resolutions = {
            name: choice
            for name in cap.mcp_fragment["mcpServers"]
            if (choice := b.resolution(f"mcp:{name}")) is not None
        }
        try:
            result = merge_mcp(config, cap.mcp_fragment, resolutions)
        except ValueError as exc:
            raise PlanError(f"{rel}: {exc}") from exc
        config = result.config
        for name in result.conflicts:
            b.decisions.append(
                McpDecision(
                    name=name,
                    owner=cap.ref,
                    existing=config["mcpServers"][name],
                    incoming=cap.mcp_fragment["mcpServers"][name],
                )
            )
        for name in [*result.added, *result.replaced]:
            b.mcp_servers[name] = ManagedFile(
                owner=cap.ref, sha256=_server_hash(cap.mcp_fragment["mcpServers"][name])
            )
        for name in result.unchanged:
            owned_before = prev.get(name)
            if owned_before and owned_before.owner == cap.ref:
                b.mcp_servers[name] = owned_before
            elif config["mcpServers"][name] == cap.mcp_fragment["mcpServers"][name]:
                b.warnings.append(
                    f"MCP server '{name}' already configured identically; it stays user-owned"
                )
            else:
                b.warnings.append(f"Kept existing MCP server '{name}' configuration")

    if current is None and not config.get("mcpServers"):
        return
    if current is not None and config == current:
        return
    content = dump_json(config)
    b.ops.append(
        PlannedOperation(
            type=OperationType.MERGE_JSON,
            target=rel,
            before_hash=sha256_file(path) if current is not None else None,
            after_content=content,
            after_hash=sha256_text(content),
            owner="mcp",
            reason="merge selected MCP servers",
        )
    )


# ---------------------------------------------------------------------------------------------
# CLAUDE.md and state
# ---------------------------------------------------------------------------------------------


def _plan_instruction_file(
    b: _Builder, rel: str, mode: ClaudeMdMode | None, content: str | None, owner: str
) -> None:
    """CLAUDE.md / AGENTS.md: create, merge or replace exactly as the user decided."""
    path = b.abs(rel)
    prev = (b.inputs.state.managed_files if b.inputs.state else {}).get(rel)
    exists = path.is_file()
    current_hash = sha256_file(path) if exists else None

    if mode is None or mode in (ClaudeMdMode.KEEP, ClaudeMdMode.SKIP) or content is None:
        if prev is not None and exists and current_hash == prev.sha256:
            b.managed[rel] = prev
        return
    new_hash = sha256_text(content)
    if mode in (ClaudeMdMode.CREATE, ClaudeMdMode.REPLACE) or (
        prev and current_hash == prev.sha256
    ):
        b.managed[rel] = ManagedFile(owner=owner, sha256=new_hash)
    if exists and current_hash == new_hash:
        return
    b.ops.append(
        PlannedOperation(
            type=OperationType.UPDATE if exists else OperationType.CREATE,
            target=rel,
            before_hash=current_hash,
            after_content=content,
            after_hash=new_hash,
            owner=owner,
            reason={
                ClaudeMdMode.CREATE: f"create minimal {rel}",
                ClaudeMdMode.MERGE: f"update {rel} (existing content kept)",
                ClaudeMdMode.REPLACE: f"replace {rel} with generated version",
            }.get(mode, f"update {rel}"),
        )
    )


def _plan_docs(b: _Builder) -> list[str]:
    """Create the docs skeleton files that are missing. Docs belong to the user afterwards:
    they are not hash-tracked, existing files are never touched, and a scaffolded file the user
    deleted is not recreated."""
    previous = set(b.inputs.state.docs_scaffolded) if b.inputs.state else set()
    created: list[str] = []
    for rel, content in sorted(b.inputs.claude_md.docs_scaffold.items()):
        path = b.abs(rel)
        if path.exists() or rel in previous:
            continue
        b.ensure_parent_dirs(rel)
        b.ops.append(
            PlannedOperation(
                type=OperationType.CREATE,
                target=rel,
                after_content=content,
                after_hash=sha256_text(content),
                owner=DOCS_OWNER,
                reason="create project docs skeleton",
            )
        )
        created.append(rel)
    return sorted(previous | set(created))


def _plan_claude_md(b: _Builder) -> None:
    decision = b.inputs.claude_md
    if decision.layout == LAYOUT_AGENTS:
        _plan_instruction_file(
            b,
            paths.rel(paths.AGENTS_MD),
            decision.agents_mode,
            decision.agents_content,
            AGENTS_MD_OWNER,
        )
    _plan_instruction_file(
        b, paths.rel(paths.CLAUDE_MD), decision.mode, decision.content, CLAUDE_MD_OWNER
    )


def _plan_state(b: _Builder, selected: list[str]) -> CWIState:
    previous = b.inputs.state
    state = CWIState(
        cwi_version=__version__,
        initialized_at=previous.initialized_at if previous else b.inputs.now,
        profile=b.inputs.profile,
        claude_md_mode=b.inputs.claude_md.mode,
        agents_md_mode=b.inputs.claude_md.agents_mode,
        instructions_layout=b.inputs.claude_md.layout,
        docs_scaffolded=b.docs_scaffolded,
        selected_capabilities=selected,
        managed_files=dict(sorted(b.managed.items())),
        settings_hooks=dict(sorted(b.settings_hooks.items())),
        mcp_servers=dict(sorted(b.mcp_servers.items())),
    )
    if (
        previous is not None
        and previous.claude_md_mode
        and b.inputs.claude_md.mode
        in (
            ClaudeMdMode.KEEP,
            ClaudeMdMode.SKIP,
        )
    ):
        state.claude_md_mode = previous.claude_md_mode
    if (
        previous is not None
        and previous.agents_md_mode
        and b.inputs.claude_md.agents_mode
        in (
            ClaudeMdMode.KEEP,
            ClaudeMdMode.SKIP,
            None,
        )
    ):
        state.agents_md_mode = previous.agents_md_mode
    content = StateRepository.serialize(state)
    rel = paths.rel(paths.STATE_FILE)
    path = b.abs(rel)
    before = sha256_file(path) if path.is_file() else None
    if before == sha256_text(content):
        return state
    b.ensure_parent_dirs(rel)
    b.ops.append(
        PlannedOperation(
            type=OperationType.UPDATE if before else OperationType.CREATE,
            target=rel,
            before_hash=before,
            after_content=content,
            after_hash=sha256_text(content),
            owner=STATE_OWNER,
            reason="record CWI ownership state",
        )
    )
    return state


# ---------------------------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------------------------


def _build(inputs: PlanInputs) -> tuple[InstallationPlan | None, list[FileDecision | McpDecision]]:
    b = _Builder(inputs=inputs)
    catalog = inputs.catalog
    state = inputs.state
    previous = list(state.selected_capabilities) if state else []

    if catalog is None:
        # Limited mode: capabilities cannot be sourced; keep what is installed untouched.
        selected = _ordered(previous)
        if state:
            b.managed.update(
                {k: v for k, v in state.managed_files.items() if v.owner not in INSTRUCTION_OWNERS}
            )
            b.settings_hooks.update(state.settings_hooks)
            b.mcp_servers.update(state.mcp_servers)
        removed: list[str] = []
        caps: list[Capability] = []
    else:
        unknown = [r for r in inputs.selected if catalog.get(r) is None]
        if unknown:
            raise PlanError(f"Unknown capabilities selected: {', '.join(unknown)}")
        selected = _ordered(list(dict.fromkeys(inputs.selected)))
        removed = _ordered([r for r in previous if r not in selected])
        caps = [catalog.require(r) for r in selected]

    for cap in caps:
        _plan_payload(b, cap)
    _plan_removals(b, removed)
    _plan_claude_md(b)
    b.docs_scaffolded = _plan_docs(b)
    if catalog is not None:
        _plan_settings(b, [c for c in caps if c.type == CapabilityType.HOOK], removed)
        _plan_mcp(b, [c for c in caps if c.type == CapabilityType.MCP], removed)

    env: dict[str, list[EnvRequirement]] = {}
    for cap in caps:
        if cap.manifest.requirements.env:
            env[cap.ref] = list(cap.manifest.requirements.env)

    if b.decisions:
        return None, b.decisions

    state_obj = _plan_state(b, selected)
    cleanup_ops, cleanup_warnings = plan_cleanup(
        inputs.root,
        catalog=catalog,
        template=inputs.cleanup_template,
        catalog_cleanup=inputs.cleanup_catalog,
    )
    b.ops.extend(cleanup_ops)
    b.warnings.extend(cleanup_warnings)

    # Execution order: mkdir -> create/copy -> update/merge -> state -> deletes.
    def order(op: PlannedOperation) -> int:
        if op.type == OperationType.MKDIR:
            return 0
        if op.owner == STATE_OWNER:
            return 3
        if op.is_delete:
            return 4
        if op.before_hash is None:
            return 1
        return 2

    operations = sorted(b.ops, key=order)  # stable: preserves planning order within a phase
    plan = InstallationPlan(
        profile=inputs.profile,
        selected_capabilities=selected,
        added_capabilities=[r for r in selected if r not in previous],
        removed_capabilities=removed,
        kept_capabilities=[r for r in selected if r in previous],
        claude_md_mode=inputs.claude_md.mode,
        agents_md_mode=inputs.claude_md.agents_mode,
        operations=operations,
        warnings=list(dict.fromkeys(b.warnings)),
        env_requirements=env,
        state=state_obj,
        cleanup_template=any(op.owner == "cwi-template" for op in cleanup_ops),
    )
    return plan, []


def find_decisions(inputs: PlanInputs) -> list[FileDecision | McpDecision]:
    """Decisions the user must take before `build_plan` can succeed."""
    _, decisions = _build(inputs)
    return decisions


def build_plan(inputs: PlanInputs) -> InstallationPlan:
    plan, decisions = _build(inputs)
    if plan is None:
        keys = ", ".join(d.key for d in decisions)
        raise ConflictError(f"Unresolved conflicts require a decision: {keys}")
    return plan
