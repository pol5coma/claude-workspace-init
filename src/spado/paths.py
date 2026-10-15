"""Catalog capability payload paths, relative to a project root."""

from pathlib import PurePosixPath as P

CLAUDE_MD = P("CLAUDE.md")
CLAUDE_LOCAL_MD = P("CLAUDE.local.md")
AGENTS_MD = P("AGENTS.md")
CLAUDE_DIR = P(".claude")
SKILLS_DIR = CLAUDE_DIR / "skills"
AGENTS_DIR = CLAUDE_DIR / "agents"
HOOKS_DIR = CLAUDE_DIR / "hooks"
CLAUDE_SCRIPTS_DIR = CLAUDE_DIR / "scripts"
SETTINGS_FILE = CLAUDE_DIR / "settings.json"
SETTINGS_LOCAL_FILE = CLAUDE_DIR / "settings.local.json"
MCP_FILE = P(".mcp.json")
SCRIPTS_DIR = P("scripts")
GROUP_MANIFEST = "group.json"


def agent_file(agent_id: str, group: str | None = None) -> str:
    """Install target of an agent definition; groups use a subfolder."""
    base = f"{AGENTS_DIR}/{group}" if group else str(AGENTS_DIR)
    return f"{base}/{agent_id}.md"


def rel(path: P | str) -> str:
    """Normalize a relative path to its POSIX string form."""
    return str(P(path))
