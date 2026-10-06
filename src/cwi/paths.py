"""Central registry of every Claude Code and CWI path contract.

Claude Code evolves; keeping these paths in one module keeps compatibility updates small.
All paths are relative to the project root.
"""

from __future__ import annotations

from pathlib import PurePosixPath as P

# --- Claude Code project contract ---------------------------------------------------------
CLAUDE_MD = P("CLAUDE.md")
CLAUDE_LOCAL_MD = P("CLAUDE.local.md")
CLAUDE_DIR = P(".claude")
SKILLS_DIR = CLAUDE_DIR / "skills"
AGENTS_DIR = CLAUDE_DIR / "agents"
HOOKS_DIR = CLAUDE_DIR / "hooks"
RULES_DIR = CLAUDE_DIR / "rules"
CLAUDE_SCRIPTS_DIR = CLAUDE_DIR / "scripts"
SETTINGS_FILE = CLAUDE_DIR / "settings.json"
SETTINGS_LOCAL_FILE = CLAUDE_DIR / "settings.local.json"
MCP_FILE = P(".mcp.json")

# --- Project-level scripts ------------------------------------------------------------------
SCRIPTS_DIR = P("scripts")

# --- CWI metadata ---------------------------------------------------------------------------
STATE_FILE = CLAUDE_DIR / "cwi-state.json"
LEGACY_STATE_FILE = P(".cwi") / "state.json"
CWI_WORK_DIR = P(".cwi")  # transient: transaction backups only, removed after success
BACKUPS_DIR = CWI_WORK_DIR / "backups"

# --- CWI template (bootstrap) resources -------------------------------------------------------
CATALOG_DIR = P("catalog")
TEMPLATES_DIR = P("templates")
TEMPLATE_MARKER = P(".cwi-template.json")
CWI_PACKAGE_NAME = "claude-workspace-init"

# Paths owned by the CWI template. Removed after a successful init when the template marker is
# present and pyproject.toml declares the CWI package (see planning.cleanup).
DEFAULT_BOOTSTRAP_PATHS: tuple[str, ...] = (
    "catalog",
    "templates",
    "src/cwi",
    "tests",
    "pyproject.toml",
    "uv.lock",
    ".python-version",
    "CWI_SPEC.md",
    "CWI_IMPLEMENTATION_GUIDE.md",
    "USAGE.md",
    ".cwi-template.json",
)
# Parent directories removed only when they end up empty after bootstrap cleanup.
BOOTSTRAP_PARENTS_IF_EMPTY: tuple[str, ...] = ("src",)

# --- Scanner ---------------------------------------------------------------------------------
IGNORED_SCAN_DIRS: frozenset[str] = frozenset(
    {
        ".git",
        "node_modules",
        ".venv",
        "venv",
        "env",
        "dist",
        "build",
        ".next",
        ".nuxt",
        ".svelte-kit",
        "coverage",
        "__pycache__",
        "target",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
        ".turbo",
        ".cache",
        ".idea",
        ".vscode",
        ".cwi",
        ".claude",
    }
)

CATALOG_TYPE_DIRS: dict[str, str] = {
    "skill": "skills",
    "agent": "agents",
    "script": "scripts",
    "hook": "hooks",
    "mcp": "mcp",
}


def rel(path: P | str) -> str:
    """Normalize a relative path to its POSIX string form."""
    return str(P(path))
