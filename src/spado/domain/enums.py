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
