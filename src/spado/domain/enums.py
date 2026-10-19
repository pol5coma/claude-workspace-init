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


class Category(StrEnum):
    """Topical catalog categories used to browse and select capabilities."""

    ARCHITECTURE = "architecture"
    BACKEND = "backend"
    FRONTEND = "frontend"
    MOBILE = "mobile"
    DATA = "data"
    AI = "ai"
    INFRASTRUCTURE = "infrastructure"
    SECURITY = "security"
    TESTING = "testing"
    QUALITY = "quality"
    LANGUAGES = "languages"
    WORKFLOW = "workflow"
    PRODUCT = "product"

    @property
    def label(self) -> str:
        return CATEGORY_LABELS[self]


CATEGORY_LABELS: dict[Category, str] = {
    Category.ARCHITECTURE: "Architecture & system design",
    Category.BACKEND: "Backend & APIs",
    Category.FRONTEND: "Frontend & UI",
    Category.MOBILE: "Mobile & desktop",
    Category.DATA: "Databases & data",
    Category.AI: "AI, ML & LLM applications",
    Category.INFRASTRUCTURE: "Infrastructure, DevOps & networking",
    Category.SECURITY: "Security & compliance",
    Category.TESTING: "Testing & QA",
    Category.QUALITY: "Code review, quality & debugging",
    Category.LANGUAGES: "Languages & coding standards",
    Category.WORKFLOW: "Development workflow & agent tooling",
    Category.PRODUCT: "Product, content & business",
}
