"""End-to-end tests of the unified SPADO command entry point."""

import json

from typer.testing import CliRunner

from spado import __version__
from spado.cli import app
from tests.helpers import REAL_CATALOG, tree

runner = CliRunner()


def invoke(*args):
    return runner.invoke(app, list(args), catch_exceptions=False)


def test_version_and_root_help():
    assert invoke("--version").stdout.strip() == f"spado {__version__}"
    result = invoke("--help")
    assert result.exit_code == 0
    assert "init" in result.stdout
    assert "workflow" in result.stdout
    assert "provision" not in result.stdout


def test_init_help_exposes_current_setup_options():
    result = invoke("init", "--help")
    assert result.exit_code == 0
    for flag in ("--host", "--mode", "--embeddings", "--capability", "--no-workflow", "--dry-run"):
        assert flag in result.stdout


def test_capability_only_dry_run_and_install(tmp_repo, real_catalog):
    root = tmp_repo("react-vite")
    before = tree(root)
    args = (
        "init",
        "--root",
        str(root),
        "--catalog",
        str(real_catalog),
        "--host",
        "claude",
        "--no-workflow",
        "--capability",
        "skill:kickoff",
    )
    preview = invoke(*args, "--dry-run")
    assert preview.exit_code == 0, preview.stdout
    assert tree(root) == before
    applied = invoke(*args)
    assert applied.exit_code == 0, applied.stdout
    assert (root / ".claude/skills/kickoff/SKILL.md").is_file()
    assert (root / ".spado/installation.json").is_file()
    installed = tree(root)
    assert invoke(*args).exit_code == 0
    assert tree(root) == installed


def test_full_init_installs_host_resources_without_starting_db(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    result = invoke(
        "init",
        "--root",
        str(root),
        "--catalog",
        str(REAL_CATALOG),
        "--host",
        "claude",
        "--host",
        "codex",
        "--mode",
        "auto",
        "--embeddings",
        "external",
        "--embedding-model",
        "text-embedding-3-small",
    )
    assert result.exit_code == 0, result.stdout
    cfg = json.loads((root / ".spado/project.json").read_text())
    assert set(cfg["hosts"]) == {"claude", "codex"}
    assert (root / ".spado/installation.json").is_file()
    assert (root / ".claude/skills/spdlc/SKILL.md").is_file()
    assert (root / ".agents/skills/spdlc/SKILL.md").is_file()


def test_invalid_setup_does_not_modify_project(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    before = tree(root)
    result = invoke("init", "--root", str(root), "--no-workflow", "--host", "claude")
    assert result.exit_code == 1
    assert "--capability" in result.stderr
    assert tree(root) == before
