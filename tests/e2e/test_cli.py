"""End-to-end tests of the `cwi` console entry point."""

import json

from typer.testing import CliRunner

from cwi import __version__
from cwi.cli import app
from tests.helpers import tree

runner = CliRunner()


def invoke(*args):
    return runner.invoke(app, list(args), catch_exceptions=False)


def test_version():
    result = invoke("--version")
    assert result.exit_code == 0
    assert result.stdout.strip() == f"cwi {__version__}"


def test_help_lists_init():
    result = invoke("--help")
    assert result.exit_code == 0
    assert "init" in result.stdout


def test_init_help_flags():
    result = invoke("init", "--help")
    for flag in ("--root", "--catalog", "--dry-run", "--yes", "--verbose"):
        assert flag in result.stdout


def test_dry_run_writes_nothing(tmp_repo, real_catalog):
    root = tmp_repo("python-fastapi")
    before = tree(root)
    result = invoke("init", "--root", str(root), "--catalog", str(real_catalog), "--dry-run")
    assert result.exit_code == 0, result.stdout
    assert "Claude Workspace Plan" in result.stdout
    assert "Dry run complete" in result.stdout
    assert tree(root) == before


def test_yes_applies_and_rerun_is_idempotent(tmp_repo, real_catalog):
    root = tmp_repo("fullstack")
    result = invoke("init", "--root", str(root), "--catalog", str(real_catalog), "--yes")
    assert result.exit_code == 0, result.stdout
    assert "Claude workspace initialized" in result.stdout
    assert (root / "CLAUDE.md").is_file()
    settings = json.loads((root / ".claude" / "settings.json").read_text())
    assert "PreToolUse" in settings["hooks"]
    first = tree(root)
    result = invoke("init", "--root", str(root), "--catalog", str(real_catalog), "--yes")
    assert result.exit_code == 0
    assert "already up to date" in result.stdout
    assert tree(root) == first


def test_non_interactive_without_yes_applies_nothing(tmp_repo, real_catalog):
    root = tmp_repo("react-vite")
    before = tree(root)
    result = invoke("init", "--root", str(root), "--catalog", str(real_catalog))
    assert result.exit_code == 0
    assert "Re-run with --yes" in result.stdout
    assert tree(root) == before


def test_invalid_catalog_fails_cleanly_before_mutation(tmp_repo, tmp_path):
    root = tmp_repo("python-fastapi")
    bad = tmp_path / "bad-catalog" / "skills" / "broken"
    bad.mkdir(parents=True)
    (bad / "cwi.json").write_text("{ nope")
    before = tree(root)
    result = invoke(
        "init", "--root", str(root), "--catalog", str(tmp_path / "bad-catalog"), "--yes"
    )
    assert result.exit_code == 1
    assert "Invalid JSON" in result.stdout
    assert "Traceback" not in result.stdout
    assert tree(root) == before


def test_missing_root_fails_cleanly(tmp_path):
    result = invoke("init", "--root", str(tmp_path / "nope"), "--yes")
    assert result.exit_code == 1
    assert "does not exist" in result.stdout
