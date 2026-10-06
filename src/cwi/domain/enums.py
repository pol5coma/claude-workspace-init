from __future__ import annotations

from enum import StrEnum


class CapabilityType(StrEnum):
    SKILL = "skill"
    AGENT = "agent"
    SCRIPT = "script"
    HOOK = "hook"
    MCP = "mcp"

    @property
    def plural(self) -> str:
        return {
            "skill": "skills",
            "agent": "agents",
            "script": "scripts",
            "hook": "hooks",
            "mcp": "mcp",
        }[self.value]

    @property
    def title(self) -> str:
        return {
            "skill": "Skills",
            "agent": "Agents",
            "script": "Scripts",
            "hook": "Hooks",
            "mcp": "MCP",
        }[self.value]


# Order in which the selection flow walks the catalog (spec section 13).
SELECTION_ORDER: tuple[CapabilityType, ...] = (
    CapabilityType.SKILL,
    CapabilityType.AGENT,
    CapabilityType.SCRIPT,
    CapabilityType.MCP,
    CapabilityType.HOOK,
)


class ProjectType(StrEnum):
    BACKEND = "backend"
    FRONTEND = "frontend"
    FULLSTACK = "fullstack"
    AI = "ai"
    CLI = "cli"
    LIBRARY = "library"
    DATA_ML = "data_ml"
    OTHER = "other"

    @property
    def label(self) -> str:
        return PROJECT_TYPE_LABELS[self]


PROJECT_TYPE_LABELS: dict[ProjectType, str] = {
    ProjectType.BACKEND: "Backend API",
    ProjectType.FRONTEND: "Frontend application",
    ProjectType.FULLSTACK: "Full-stack application",
    ProjectType.AI: "AI / Agent application",
    ProjectType.CLI: "CLI",
    ProjectType.LIBRARY: "Library / SDK",
    ProjectType.DATA_ML: "Data / ML project",
    ProjectType.OTHER: "Other",
}


class OperationType(StrEnum):
    MKDIR = "mkdir"
    CREATE = "create"
    UPDATE = "update"
    COPY = "copy"
    MERGE_JSON = "merge_json"
    DELETE = "delete"
    DELETE_DIR = "delete_dir"


class InitStage(StrEnum):
    START = "start"
    SCANNED = "scanned"
    PROFILE_CONFIRMED = "profile_confirmed"
    CLAUDE_MD_CONFIGURED = "claude_md_configured"
    CAPABILITIES_SELECTED = "capabilities_selected"
    PLAN_READY = "plan_ready"
    APPLIED = "applied"
    VALIDATED = "validated"
    COMPLETE = "complete"


class ClaudeMdMode(StrEnum):
    CREATE = "create"  # no existing file: write generated version
    KEEP = "keep"  # keep current file untouched
    MERGE = "merge"  # append missing sections to existing file
    REPLACE = "replace"  # replace with generated version
    SKIP = "skip"  # do not configure CLAUDE.md at all


class Confidence:
    HIGH = 0.9
    MEDIUM = 0.6
    LOW = 0.3

    @staticmethod
    def label(value: float) -> str:
        if value >= 0.8:
            return "high"
        if value >= 0.5:
            return "medium"
        return "low"


class FileOwnership(StrEnum):
    USER = "user"
    CWI = "cwi"
    TEMPLATE = "template"
