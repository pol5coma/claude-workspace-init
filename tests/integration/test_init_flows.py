"""Full `cwi init` flows against temporary copies of fixture repositories."""

import json
import shutil

import pytest

from cwi.domain.errors import ApplyError, UserCancelled
from cwi.state.repository import StateRepository
from cwi.ui.prompts import Queue
from tests.helpers import PROJECT_ROOT, failing, run, tree


def load_json(path):
    return json.loads(path.read_text())


def hook_commands(settings):
    return [
        h["command"]
        for groups in settings.get("hooks", {}).values()
        for g in groups
        for h in g["hooks"]
    ]


# ---------------------------------------------------------------------------------------------
# New project
# ---------------------------------------------------------------------------------------------


def test_new_project_questions_create_workspace(tmp_repo, real_catalog):
    root = tmp_repo("empty")
    answers = {
        "new.type": "fullstack",
        "new.backend.language": "Python",
        "new.backend.package_manager": "uv",
        "new.backend.framework": "FastAPI",
        "new.database": "PostgreSQL",
        "new.frontend.language": "TypeScript",
        "new.frontend.package_manager": "npm",
        "new.frontend.framework": "React",
        "new.frontend.build": "Vite",
        "new.testing": ["pytest", "Vitest"],
        "new.infrastructure": ["Docker"],
    }
    outcome, prompter, _ = run(root, answers, catalog=real_catalog)
    assert outcome.applied
    assert "profile.confirm" not in prompter.asked  # new project: questions, not scan confirmation
    claude_md = (root / "CLAUDE.md").read_text()
    assert "Backend:\n- Python\n- FastAPI\n- uv\n- PostgreSQL" in claude_md
    assert "- React" in claude_md and "- Vite" in claude_md
    assert "Infrastructure:\n- Docker" in claude_md
    assert "`uv run pytest`" in claude_md  # suggested command accepted by default
    for skill in ("testing", "debugging", "backend-development", "frontend-development"):
        assert (root / ".claude" / "skills" / skill / "SKILL.md").is_file()
    assert (root / ".claude" / "agents" / "code-reviewer.md").is_file()
    assert (root / "scripts" / "run-quality-checks.py").is_file()  # dependency of code-reviewer
    settings = load_json(root / ".claude" / "settings.json")
    assert any("safety-guard.py" in c for c in hook_commands(settings))
    assert any("post-edit-validation.py" in c for c in hook_commands(settings))
    assert not (root / ".cwi").exists()  # transient transaction data removed
    state = StateRepository(root).load()
    assert state.profile.project_type.value == "fullstack"


def test_new_project_dependency_scripts_keep_exec_bit(tmp_repo, real_catalog):
    root = tmp_repo("empty")
    run(
        root,
        {
            "new.type": "backend",
            "new.backend.language": "Python",
            "new.backend.framework": "FastAPI",
        },
        catalog=real_catalog,
    )
    import os

    assert os.access(root / ".claude" / "hooks" / "safety-guard.py", os.X_OK)
    assert os.access(root / "scripts" / "run-quality-checks.py", os.X_OK)


# ---------------------------------------------------------------------------------------------
# Existing projects
# ---------------------------------------------------------------------------------------------


def test_existing_fastapi_project(tmp_repo, real_catalog):
    root = tmp_repo("python-fastapi")
    outcome, prompter, output = run(root, catalog=real_catalog)
    assert "profile.confirm" in prompter.asked
    assert "new.type" not in prompter.asked  # detect first: no stack questions
    plan = outcome.plan
    assert {
        "skill:backend-development",
        "skill:testing",
        "skill:debugging",
        "agent:code-reviewer",
        "agent:security-reviewer",
        "script:run-quality-checks",
        "hook:safety-guard",
        "hook:post-edit-validation",
        "mcp:github",
    } <= set(plan.selected_capabilities)
    assert "skill:frontend-development" not in plan.selected_capabilities
    claude_md = (root / "CLAUDE.md").read_text()
    assert "- Test: `uv run pytest`" in claude_md
    assert "read `docs/architecture.md` before making structural changes" in claude_md
    mcp = load_json(root / ".mcp.json")
    assert mcp["mcpServers"]["github"]["headers"]["Authorization"] == "Bearer ${GITHUB_TOKEN}"
    assert "GITHUB_TOKEN" in output
    # Untouched project files
    assert (root / "app" / "main.py").read_text().startswith("from fastapi import FastAPI")


def test_existing_claude_md_is_merged_not_overwritten(tmp_repo, real_catalog):
    root = tmp_repo("existing-claude-config")
    original = (root / "CLAUDE.md").read_text()
    run(root, catalog=real_catalog)
    merged = (root / "CLAUDE.md").read_text()
    assert merged.startswith(original.rstrip())
    assert "## Conventions" in merged and "## Safety" in merged


@pytest.mark.parametrize("choice", ["keep", "skip"])
def test_existing_claude_md_keep_or_skip(tmp_repo, real_catalog, choice):
    root = tmp_repo("existing-claude-config")
    original = (root / "CLAUDE.md").read_text()
    run(root, {"claude_md.existing": choice}, catalog=real_catalog)
    assert (root / "CLAUDE.md").read_text() == original


def test_existing_claude_md_replace(tmp_repo, real_catalog):
    root = tmp_repo("existing-claude-config")
    run(root, {"claude_md.existing": "replace"}, catalog=real_catalog)
    text = (root / "CLAUDE.md").read_text()
    assert "## Conventions" not in text
    assert text.startswith("# existing-claude-config — Project Instructions")


def test_existing_settings_preserved_and_hooks_merged_once(tmp_repo, real_catalog):
    root = tmp_repo("existing-claude-config")
    before = load_json(root / ".claude" / "settings.json")
    run(root, catalog=real_catalog)
    after = load_json(root / ".claude" / "settings.json")
    assert after["permissions"] == before["permissions"]
    assert after["env"] == before["env"]
    commands = hook_commands(after)
    assert commands[0] == "python3 scripts/hooks/custom-safety.py"
    assert sum("safety-guard.py" in c for c in commands) == 2  # Bash + Edit matchers, once each
    assert (root / ".claude" / "agents" / "my-custom-agent.md").is_file()  # user agent untouched
    run(root, catalog=real_catalog)
    assert load_json(root / ".claude" / "settings.json") == after  # rerun: no duplicates


def test_existing_mcp_preserved_and_conflict_needs_decision(tmp_repo, real_catalog):
    root = tmp_repo("existing-mcp")
    before = load_json(root / ".mcp.json")
    outcome, prompter, _ = run(root, {"select.mcp": ["mcp:github"]}, catalog=real_catalog)
    assert "mcp:github" in prompter.asked  # conflict surfaced, default keep
    assert load_json(root / ".mcp.json") == before
    assert "github" not in outcome.plan.state.mcp_servers


def test_existing_mcp_conflict_replace(tmp_repo, real_catalog):
    root = tmp_repo("existing-mcp")
    run(root, {"select.mcp": ["mcp:github"], "mcp:github": "replace"}, catalog=real_catalog)
    mcp = load_json(root / ".mcp.json")
    assert mcp["mcpServers"]["linear"] == {"type": "http", "url": "https://mcp.linear.app/mcp"}
    assert mcp["mcpServers"]["github"]["url"] == "https://api.githubcopilot.com/mcp/"


def test_user_file_collision_requires_decision(tmp_repo, real_catalog):
    root = tmp_repo("python-fastapi")
    (root / ".claude" / "agents").mkdir(parents=True)
    (root / ".claude" / "agents" / "code-reviewer.md").write_text(
        "---\nname: code-reviewer\ndescription: mine\n---\nmine\n"
    )
    _, prompter, _ = run(root, catalog=real_catalog)
    assert "file:.claude/agents/code-reviewer.md" in prompter.asked
    assert "mine" in (root / ".claude" / "agents" / "code-reviewer.md").read_text()  # default keep


# ---------------------------------------------------------------------------------------------
# Invariants: idempotency, cancel, dry run
# ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "fixture",
    [
        "empty",
        "python-fastapi",
        "react-vite",
        "fullstack",
        "existing-claude-config",
        "existing-mcp",
        "monorepo",
    ],
)
def test_rerun_is_idempotent(tmp_repo, real_catalog, fixture):
    root = tmp_repo(fixture)
    run(root, catalog=real_catalog)
    first = tree(root)
    outcome, _, _ = run(root, catalog=real_catalog)
    assert tree(root) == first
    assert not outcome.plan.has_changes


@pytest.mark.parametrize("fixture", ["empty", "python-fastapi", "existing-claude-config"])
def test_cancel_before_apply_changes_nothing(tmp_repo, real_catalog, fixture):
    root = tmp_repo(fixture)
    before = tree(root)
    with pytest.raises(UserCancelled):
        run(root, {"preview": "cancel"}, catalog=real_catalog)
    assert tree(root) == before


def test_review_and_back_then_apply(tmp_repo, real_catalog):
    root = tmp_repo("python-fastapi")
    answers = {
        "preview": Queue(["review", "operations", "back", "apply"]),
        "select.skill": Queue([["skill:testing"], ["skill:debugging"]]),
    }
    outcome, _, output = run(root, answers, catalog=real_catalog)
    assert "Planned operations" in output
    assert (root / ".claude" / "skills" / "debugging").is_dir()
    assert not (root / ".claude" / "skills" / "testing").exists()


def test_dry_run_writes_nothing(tmp_repo, real_catalog):
    root = tmp_repo("fullstack")
    before = tree(root)
    outcome, _, output = run(root, catalog=real_catalog, dry_run=True)
    assert tree(root) == before
    assert outcome.plan.has_changes
    assert "Dry run complete" in output


# ---------------------------------------------------------------------------------------------
# State, ownership, modified files, deselection
# ---------------------------------------------------------------------------------------------


def test_modified_managed_file_detected_and_kept(tmp_repo, real_catalog):
    root = tmp_repo("python-fastapi")
    run(root, catalog=real_catalog)
    agent = root / ".claude" / "agents" / "code-reviewer.md"
    agent.write_text(agent.read_text() + "\nTeam addition.\n")
    edited = agent.read_text()
    _, prompter, output = run(root, catalog=real_catalog)
    assert "Modified CWI-managed file: .claude/agents/code-reviewer.md" in output
    assert "file:.claude/agents/code-reviewer.md" in prompter.asked
    assert agent.read_text() == edited  # never silently overwritten
    state = StateRepository(root).load()
    assert state.managed_files[".claude/agents/code-reviewer.md"].user_kept
    _, prompter, _ = run(root, catalog=real_catalog)
    assert "file:.claude/agents/code-reviewer.md" not in prompter.asked  # decision remembered


def test_modified_managed_file_replace(tmp_repo, real_catalog):
    root = tmp_repo("python-fastapi")
    run(root, catalog=real_catalog)
    agent = root / ".claude" / "agents" / "code-reviewer.md"
    pristine = agent.read_text()
    agent.write_text("changed\n")
    run(root, {"file:.claude/agents/code-reviewer.md": "replace"}, catalog=real_catalog)
    assert agent.read_text() == pristine


def test_deselecting_removes_only_cwi_owned_resources(tmp_repo, real_catalog):
    root = tmp_repo("existing-claude-config")
    run(root, catalog=real_catalog)
    assert (root / ".claude" / "skills" / "testing" / "SKILL.md").is_file()
    run(
        root,
        {"select.skill": [], "select.hook": ["hook:post-edit-validation"]},
        catalog=real_catalog,
    )
    assert not (root / ".claude" / "skills" / "testing").exists()
    assert (root / ".claude" / "skills").is_dir()
    assert not (root / ".claude" / "hooks" / "safety-guard.py").exists()
    commands = hook_commands(load_json(root / ".claude" / "settings.json"))
    assert "python3 scripts/hooks/custom-safety.py" in commands  # user hook survives
    assert not any("safety-guard.py" in c for c in commands)
    assert (root / ".claude" / "agents" / "my-custom-agent.md").is_file()


def test_limited_mode_without_catalog(tmp_repo, real_catalog):
    root = tmp_repo("python-fastapi")
    run(root, catalog=real_catalog)
    before = tree(root)
    outcome, prompter, output = run(root)  # no catalog anywhere
    assert "Catalog source unavailable" in output
    assert not any(k.startswith("select.") for k in prompter.asked)
    assert tree(root) == before
    assert outcome.plan.selected_capabilities  # still tracked from state


# ---------------------------------------------------------------------------------------------
# Rollback
# ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "factory",
    [
        failing(fail_after=0),
        failing(fail_after=5),
        failing(fail_after=12),
        failing(fail_on=".claude/settings.json"),
        failing(fail_on=".mcp.json"),
        failing(fail_on="CLAUDE.md"),
        failing(fail_on=".claude/cwi-state.json"),
    ],
    ids=["first", "middle", "late", "settings", "mcp", "claude-md", "state"],
)
def test_failed_apply_restores_repository(tmp_repo, real_catalog, factory):
    root = tmp_repo("existing-claude-config")
    (root / ".mcp.json").write_text('{"mcpServers": {"linear": {"url": "x"}}}\n')
    (root / ".github" / "workflows").mkdir(parents=True)
    (root / ".github" / "workflows" / "ci.yml").write_text("on: push\n")
    before = tree(root)
    with pytest.raises(ApplyError, match="No project changes were kept"):
        run(root, catalog=real_catalog, filesystem_factory=factory)
    assert tree(root) == before
    assert not (root / ".cwi").exists()


def test_failed_cleanup_restores_catalog(tmp_path, real_catalog):
    root = tmp_path / "repo"
    shutil.copytree(PROJECT_ROOT / "tests" / "fixtures" / "repos" / "python-fastapi", root)
    shutil.copytree(real_catalog, root / "catalog")
    before = tree(root)
    with pytest.raises(ApplyError):
        run(root, filesystem_factory=failing(fail_on="catalog"))
    assert tree(root) == before


def test_rerun_after_failure_succeeds(tmp_repo, real_catalog):
    root = tmp_repo("python-fastapi")
    with pytest.raises(ApplyError):
        run(root, catalog=real_catalog, filesystem_factory=failing(fail_after=4))
    outcome, _, _ = run(root, catalog=real_catalog)
    assert outcome.applied


# ---------------------------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------------------------


def test_local_catalog_removed_after_success(tmp_path, real_catalog):
    root = tmp_path / "repo"
    shutil.copytree(PROJECT_ROOT / "tests" / "fixtures" / "repos" / "react-vite", root)
    shutil.copytree(real_catalog, root / "catalog")
    outcome, _, _ = run(root)
    assert outcome.applied
    assert not (root / "catalog").exists()
    assert (root / ".claude" / "skills" / "frontend-development" / "SKILL.md").is_file()
    assert (root / "src" / "App.tsx").is_file()  # project files untouched


def _copy_template(dest):
    ignore = shutil.ignore_patterns(
        ".git", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache", ".DS_Store", "fixtures"
    )
    shutil.copytree(PROJECT_ROOT, dest, ignore=ignore)
    for name in ("CWI_SPEC.md", "CWI_IMPLEMENTATION_GUIDE.md"):
        if not (dest / name).exists():
            (dest / name).write_text("spec\n")
    return dest


def test_template_init_leaves_minimal_claude_workspace(tmp_path):
    root = _copy_template(tmp_path / "my-new-app")
    outcome, prompter, _ = run(
        root,
        {
            "new.type": "backend",
            "new.backend.language": "Python",
            "new.backend.framework": "FastAPI",
        },
    )
    assert "new.type" in prompter.asked  # the template itself is not an application
    assert outcome.plan.cleanup_template
    remaining = sorted(p.relative_to(root).as_posix() for p in root.iterdir())
    assert remaining == [".claude", ".gitignore", "CLAUDE.md", "README.MD", "scripts"]
    claude = sorted(p.relative_to(root).as_posix() for p in (root / ".claude").iterdir())
    assert claude == [
        ".claude/agents",
        ".claude/cwi-state.json",
        ".claude/hooks",
        ".claude/scripts",
        ".claude/settings.json",
        ".claude/skills",
    ]
    # Second run: no catalog, no bootstrap files, nothing to change.
    before = tree(root)
    outcome, _, _ = run(root)
    assert not outcome.plan.has_changes
    assert tree(root) == before


def test_template_init_can_keep_bootstrap_files(tmp_path):
    root = _copy_template(tmp_path / "keep")
    run(root, {"cleanup.template": False})
    assert (root / "catalog").is_dir() and (root / "src" / "cwi").is_dir()
    assert (root / "CLAUDE.md").is_file()


def test_template_cleanup_failure_rolls_back_everything(tmp_path):
    root = _copy_template(tmp_path / "rollback")
    before = tree(root)
    with pytest.raises(ApplyError):
        run(root, filesystem_factory=failing(fail_on="tests"))
    assert tree(root) == before
