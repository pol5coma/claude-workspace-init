"""Pydantic models shared across CWI layers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from cwi.domain.enums import (
    CapabilityType,
    ClaudeMdMode,
    Confidence,
    OperationType,
    ProjectType,
)

# ---------------------------------------------------------------------------------------------
# Scanning
# ---------------------------------------------------------------------------------------------


class Detection(BaseModel):
    """One inferred fact plus the evidence it came from."""

    value: str
    confidence: float = Confidence.HIGH
    source: str

    @property
    def confidence_label(self) -> str:
        return Confidence.label(self.confidence)


class DetectedCommand(BaseModel):
    """A development command. `detected=False` means it is a convention-based suggestion."""

    group: str  # e.g. "Backend", "Frontend", "Project"
    label: str  # e.g. "Run", "Test", "Lint"
    command: str
    source: str
    detected: bool = True


class ExistingClaudeConfig(BaseModel):
    claude_md: bool = False
    agents_md: bool = False
    claude_local_md: bool = False
    settings: bool = False
    settings_local: bool = False
    rules: bool = False
    skills: list[str] = Field(default_factory=list)
    agents: list[str] = Field(default_factory=list)
    mcp: bool = False

    @property
    def any(self) -> bool:
        return bool(
            self.claude_md
            or self.agents_md
            or self.claude_local_md
            or self.settings
            or self.settings_local
            or self.rules
            or self.skills
            or self.agents
            or self.mcp
        )


class ScanResult(BaseModel):
    root: str
    meaningful_project: bool
    project_type: ProjectType = ProjectType.OTHER
    project_type_confidence: float = Confidence.LOW
    project_type_reason: str = ""
    backend: bool = False
    frontend: bool = False
    python_version: str | None = None
    languages: list[Detection] = Field(default_factory=list)
    frameworks: list[Detection] = Field(default_factory=list)
    package_managers: list[Detection] = Field(default_factory=list)
    databases: list[Detection] = Field(default_factory=list)
    infrastructure: list[Detection] = Field(default_factory=list)
    test_tools: list[Detection] = Field(default_factory=list)
    tools: list[Detection] = Field(default_factory=list)  # linters, formatters, type checkers
    commands: list[DetectedCommand] = Field(default_factory=list)
    monorepo: bool = False
    subprojects: list[str] = Field(default_factory=list)
    architecture_docs: list[str] = Field(default_factory=list)
    stack: dict[str, list[str]] = Field(default_factory=dict)
    existing_claude: ExistingClaudeConfig = Field(default_factory=ExistingClaudeConfig)
    signals: list[str] = Field(default_factory=list)  # why the project is (not) meaningful

    def all_detections(self) -> dict[str, list[Detection]]:
        return {
            "Languages": self.languages,
            "Frameworks": self.frameworks,
            "Package managers": self.package_managers,
            "Databases": self.databases,
            "Infrastructure": self.infrastructure,
            "Testing": self.test_tools,
            "Tooling": self.tools,
        }


# ---------------------------------------------------------------------------------------------
# Project profile
# ---------------------------------------------------------------------------------------------


class ProjectProfile(BaseModel):
    """User-confirmed interpretation of the project."""

    project_type: ProjectType = ProjectType.OTHER
    name: str | None = None
    backend: bool = False
    frontend: bool = False
    languages: list[str] = Field(default_factory=list)
    frameworks: list[str] = Field(default_factory=list)
    package_managers: list[str] = Field(default_factory=list)
    databases: list[str] = Field(default_factory=list)
    infrastructure: list[str] = Field(default_factory=list)
    test_tools: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    commands: list[DetectedCommand] = Field(default_factory=list)
    monorepo: bool = False
    architecture_doc: str | None = None
    # Explicit stack grouping for CLAUDE.md, e.g. {"Backend": [...], "Frontend": [...]}.
    stack: dict[str, list[str]] = Field(default_factory=dict)

    def technologies(self) -> set[str]:
        values = [
            *self.languages,
            *self.frameworks,
            *self.package_managers,
            *self.databases,
            *self.infrastructure,
            *self.test_tools,
            *self.tools,
        ]
        for items in self.stack.values():
            values.extend(items)
        return {normalize_tech(v) for v in values if v}

    def summary(self) -> str:
        highlights = [*self.frameworks[:3], *self.databases[:1]]
        if not highlights:
            highlights = self.languages[:2]
        text = self.project_type.label
        if self.monorepo:
            text += " (monorepo)"
        if highlights:
            text += " · " + " + ".join(highlights)
        return text


def normalize_tech(value: str) -> str:
    """Lowercase technology names and drop version suffixes ("Python 3.12" -> "python")."""
    v = value.strip().lower()
    parts = v.split()
    if len(parts) > 1 and any(ch.isdigit() for ch in parts[-1]):
        v = " ".join(parts[:-1])
    return v


# ---------------------------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------------------------


class RecommendationRules(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_types: list[ProjectType] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    require_technology: bool = False  # only recommend when a technology matches


class EnvRequirement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    description: str = ""
    required: bool = True


class Requirements(BaseModel):
    model_config = ConfigDict(extra="forbid")

    env: list[EnvRequirement] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


SUPPORTED_CATALOG_SCHEMA = 1


class CapabilityManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int
    id: str
    type: CapabilityType
    name: str
    description: str
    tags: list[str] = Field(default_factory=list)
    default_selected: bool = False
    recommendation: RecommendationRules | None = None
    dependencies: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    requirements: Requirements = Field(default_factory=Requirements)

    @field_validator("id")
    @classmethod
    def _valid_id(cls, value: str) -> str:
        import re

        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", value):
            raise ValueError("id must be lowercase letters, digits and hyphens")
        return value

    @property
    def ref(self) -> str:
        return f"{self.type.value}:{self.id}"


class CapabilityGroup(BaseModel):
    """A family of capabilities of one type, stored as catalog/<type>/<group>/<id>/.

    `defaults` maps a project type to the member ids preselected for that type.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: int
    id: str
    type: CapabilityType
    name: str
    description: str = ""
    defaults: dict[ProjectType, list[str]] = Field(default_factory=dict)

    @field_validator("id")
    @classmethod
    def _valid_id(cls, value: str) -> str:
        import re

        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", value):
            raise ValueError("id must be lowercase letters, digits and hyphens")
        return value


class Capability(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    manifest: CapabilityManifest
    source_dir: Path
    group: str | None = None  # family folder name, e.g. "development-agents"
    payload_files: list[str] = Field(default_factory=list)  # POSIX paths relative to payload/
    settings_fragment: dict[str, Any] | None = None
    mcp_fragment: dict[str, Any] | None = None

    @property
    def ref(self) -> str:
        return self.manifest.ref

    @property
    def id(self) -> str:
        return self.manifest.id

    @property
    def type(self) -> CapabilityType:
        return self.manifest.type

    @property
    def payload_dir(self) -> Path:
        return self.source_dir / "payload"


class Catalog(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    root: Path
    capabilities: list[Capability] = Field(default_factory=list)
    groups: list[CapabilityGroup] = Field(default_factory=list)

    def group(self, cap_type: CapabilityType, group_id: str | None) -> CapabilityGroup | None:
        if group_id is None:
            return None
        return next((g for g in self.groups if g.type == cap_type and g.id == group_id), None)

    def get(self, ref: str) -> Capability | None:
        for cap in self.capabilities:
            if cap.ref == ref:
                return cap
        return None

    def require(self, ref: str) -> Capability:
        cap = self.get(ref)
        if cap is None:
            from cwi.domain.errors import CatalogError

            raise CatalogError(f"Unknown capability: {ref}")
        return cap

    def by_type(self, cap_type: CapabilityType) -> list[Capability]:
        # Ungrouped capabilities first, then each family alphabetically.
        return sorted(
            (c for c in self.capabilities if c.type == cap_type),
            key=lambda c: (c.group is not None, c.group or "", c.id),
        )

    @property
    def refs(self) -> list[str]:
        return [c.ref for c in self.capabilities]


class Recommendation(BaseModel):
    ref: str
    score: int
    reasons: list[str] = Field(default_factory=list)
    preselected: bool = False

    @property
    def reason_text(self) -> str:
        return "; ".join(self.reasons)


# ---------------------------------------------------------------------------------------------
# CLAUDE.md
# ---------------------------------------------------------------------------------------------


class ClaudeMdSpec(BaseModel):
    title: str = "Project Instructions"
    safety: list[str] = Field(default_factory=list)
    dangerous_commands: list[str] = Field(default_factory=list)
    stack: dict[str, list[str]] = Field(default_factory=dict)
    commands: list[DetectedCommand] = Field(default_factory=list)
    architecture_pointer: str | None = None
    additional_instructions: list[str] = Field(default_factory=list)
    docs_index: bool = False  # render "Project docs" (architecture, glossary, specs, decisions)
    version_rule: bool = True  # tell agents to code for the versions listed in Stack
    architecture_template: bool = (
        False  # architecture doc is the CWI template: point to project-discovery
    )


class SizeReport(BaseModel):
    lines: int
    characters: int
    estimated_tokens: int
    verdict: str  # compact | review | large
    message: str


LAYOUT_AGENTS = "agents"  # AGENTS.md holds shared instructions, CLAUDE.md imports it
LAYOUT_CLAUDE = "claude"  # everything in CLAUDE.md


class ClaudeMdDecision(BaseModel):
    """What to do with the instruction files. `mode`/`content` always describe CLAUDE.md."""

    mode: ClaudeMdMode
    spec: ClaudeMdSpec | None = None
    generated: str | None = None  # rendered candidate
    content: str | None = None  # final CLAUDE.md content to write (None = do not touch)
    layout: str = LAYOUT_CLAUDE
    agents_mode: ClaudeMdMode | None = None  # AGENTS.md, only with LAYOUT_AGENTS
    agents_content: str | None = None
    docs_scaffold: dict[str, str] = Field(
        default_factory=dict
    )  # path -> content, created if missing


# ---------------------------------------------------------------------------------------------
# Planning
# ---------------------------------------------------------------------------------------------


class PlannedOperation(BaseModel):
    type: OperationType
    target: str  # POSIX path relative to the project root
    source: str | None = None  # absolute source path for COPY
    before_hash: str | None = None  # sha256 of the existing target (None = must not exist)
    after_content: str | None = None  # text content for CREATE/UPDATE/MERGE_JSON
    after_hash: str | None = None
    owner: str  # capability ref, "claude-md", "cwi-state", "cwi-template", ...
    reason: str
    only_if_empty: bool = False  # DELETE_DIR: remove only when empty

    @property
    def is_delete(self) -> bool:
        return self.type in (OperationType.DELETE, OperationType.DELETE_DIR)


class HookEntryRef(BaseModel):
    event: str
    matcher: str
    type: str
    command: str


class ManagedFile(BaseModel):
    owner: str
    sha256: str
    user_kept: bool = False  # user chose to keep their modified version over the catalog's


class CWIState(BaseModel):
    schema_version: int = 1
    cwi_version: str
    initialized_at: str
    profile: ProjectProfile | None = None
    claude_md_mode: ClaudeMdMode | None = None
    agents_md_mode: ClaudeMdMode | None = None
    instructions_layout: str | None = None
    docs_scaffolded: list[str] = Field(default_factory=list)  # never recreated once deleted
    selected_capabilities: list[str] = Field(default_factory=list)
    managed_files: dict[str, ManagedFile] = Field(default_factory=dict)
    settings_hooks: dict[str, list[HookEntryRef]] = Field(default_factory=dict)
    mcp_servers: dict[str, ManagedFile] = Field(
        default_factory=dict
    )  # server -> owner + config hash


SUPPORTED_STATE_SCHEMA = 1


class InstallationPlan(BaseModel):
    profile: ProjectProfile
    selected_capabilities: list[str] = Field(default_factory=list)
    added_capabilities: list[str] = Field(default_factory=list)  # new in this run
    removed_capabilities: list[str] = Field(default_factory=list)  # deselected, CWI-owned
    kept_capabilities: list[str] = Field(default_factory=list)  # already installed
    claude_md_mode: ClaudeMdMode | None = None
    agents_md_mode: ClaudeMdMode | None = None
    operations: list[PlannedOperation] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    env_requirements: dict[str, list[EnvRequirement]] = Field(default_factory=dict)
    state: CWIState
    cleanup_template: bool = False

    def counts(self) -> dict[str, int]:
        result = {"create": 0, "update": 0, "delete": 0}
        for op in self.operations:
            if op.type == OperationType.MKDIR:
                continue
            if op.is_delete:
                result["delete"] += 1
            elif op.before_hash is None:
                result["create"] += 1
            else:
                result["update"] += 1
        return result

    @property
    def has_changes(self) -> bool:
        return bool(self.operations)


class ExecutionResult(BaseModel):
    applied: list[PlannedOperation] = Field(default_factory=list)
    backup_dir: str | None = None
    state: CWIState
