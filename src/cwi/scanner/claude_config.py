"""Detection of existing Claude Code configuration (treated as user-owned)."""

from __future__ import annotations

from cwi import paths
from cwi.domain.models import ExistingClaudeConfig
from cwi.scanner.context import ScanContext


def detect_claude_config(ctx: ScanContext) -> ExistingClaudeConfig:
    skills_dir = ctx.path(paths.rel(paths.SKILLS_DIR))
    agents_dir = ctx.path(paths.rel(paths.AGENTS_DIR))
    skills = (
        sorted(p.name for p in skills_dir.iterdir() if p.is_dir() and (p / "SKILL.md").is_file())
        if skills_dir.is_dir()
        else []
    )
    agents = sorted(p.stem for p in agents_dir.rglob("*.md")) if agents_dir.is_dir() else []
    return ExistingClaudeConfig(
        claude_md=ctx.is_file(paths.rel(paths.CLAUDE_MD)),
        claude_local_md=ctx.is_file(paths.rel(paths.CLAUDE_LOCAL_MD)),
        settings=ctx.is_file(paths.rel(paths.SETTINGS_FILE)),
        settings_local=ctx.is_file(paths.rel(paths.SETTINGS_LOCAL_FILE)),
        rules=ctx.is_dir(paths.rel(paths.RULES_DIR)),
        skills=skills,
        agents=agents,
        mcp=ctx.is_file(paths.rel(paths.MCP_FILE)),
    )
