"""Category metadata and the interactive capability picker of `spado init --no-workflow`."""

import shutil

import pytest
from typer.testing import CliRunner

from spado.authoring.prompts import AutoPrompter
from spado.catalog.loader import load_catalog
from spado.cli import app
from spado.domain.enums import Category
from spado.domain.errors import UserCancelled
from spado.install.picker import pick, refs_in_categories
from spado.runtime import commands
from tests.helpers import REAL_CATALOG

runner = CliRunner()


@pytest.fixture(scope="module")
def bundled():
    return load_catalog(REAL_CATALOG)


class RecordingPrompter(AutoPrompter):
    """AutoPrompter that also keeps the options each checkbox offered."""

    def __init__(self, overrides):
        super().__init__(overrides)
        self.offered = {}

    def checkbox(self, key, message, options):
        self.offered[key] = options
        return super().checkbox(key, message, options)


def test_every_bundled_capability_has_a_category(bundled):
    assert [c.ref for c in bundled.capabilities if not c.manifest.categories] == []


def test_refs_in_categories_respects_host_compatibility(bundled):
    claude = refs_in_categories(bundled, ["claude"], [Category.WORKFLOW])
    codex = refs_in_categories(bundled, ["codex"], [Category.WORKFLOW])
    assert "hook:safety-guard" in claude
    assert "hook:safety-guard" not in codex
    assert set(codex) <= set(claude)


def test_pick_lists_each_capability_once_under_its_first_chosen_category(bundled):
    prompter = RecordingPrompter(
        {
            "categories": [Category.FRONTEND, Category.QUALITY],
            "capabilities": ["agent:react-reviewer", "skill:react-expert"],
        }
    )
    hosts, selected = pick(bundled, prompter, ["claude"])
    assert hosts == ["claude"]
    assert selected == ["agent:react-reviewer", "skill:react-expert"]
    values = [o.value for o in prompter.offered["capabilities"] if not o.separator]
    assert len(values) == len(set(values))
    headings = [o.label for o in prompter.offered["capabilities"] if o.separator]
    assert headings == [f"── {Category.FRONTEND.label} ──", f"── {Category.QUALITY.label} ──"]
    options = prompter.offered["capabilities"]
    second_heading = next(i for i, o in enumerate(options) if o.separator and i > 0)
    assert "agent:react-reviewer" in [o.value for o in options[1:second_heading]]


def test_pick_asks_for_hosts_when_missing(bundled):
    prompter = RecordingPrompter(
        {"categories": [Category.BACKEND], "capabilities": ["skill:flask-specialist"]}
    )
    hosts, _ = pick(bundled, prompter, None)
    assert hosts == ["claude"]  # Claude Code is checked by default
    assert prompter.asked[0] == "hosts"


@pytest.mark.parametrize(
    "overrides",
    [
        {"hosts": []},
        {"categories": []},
        {"categories": [Category.BACKEND], "capabilities": []},
    ],
)
def test_pick_cancels_on_empty_answers(bundled, overrides):
    with pytest.raises(UserCancelled):
        pick(bundled, AutoPrompter(overrides), None)


def _init(root, *args):
    return runner.invoke(
        app, ["init", "--root", str(root), "--catalog", str(REAL_CATALOG), "--no-workflow", *args]
    )


def test_init_category_installs_the_whole_category(tmp_path):
    result = _init(tmp_path, "--host", "claude", "--category", "data")
    assert result.exit_code == 0, result.output
    assert (tmp_path / ".claude/skills/flask-specialist").exists() is False
    assert (tmp_path / ".claude/skills/postgres-pro/SKILL.md").is_file()
    assert (tmp_path / ".claude/skills/redis-core/SKILL.md").is_file()
    assert not (tmp_path / ".spado/project.json").exists()


def test_init_category_requires_no_workflow(tmp_path):
    result = runner.invoke(
        app, ["init", "--root", str(tmp_path), "--host", "claude", "--category", "data"]
    )
    assert result.exit_code == 1
    assert "--no-workflow" in result.stderr


def test_init_without_selection_outside_a_terminal_explains_options(tmp_path):
    result = _init(tmp_path, "--host", "claude")
    assert result.exit_code == 1
    assert "--category" in result.stderr
    assert list(tmp_path.iterdir()) == []


@pytest.fixture
def interactive(monkeypatch):
    def factory(overrides):
        monkeypatch.setattr(commands, "interactive_terminal", lambda: True)
        monkeypatch.setattr(commands, "capability_prompter", lambda: AutoPrompter(overrides))

    return factory


def test_interactive_init_installs_the_picked_capabilities(tmp_path, interactive):
    interactive(
        {
            "categories": [Category.BACKEND],
            "capabilities": ["skill:flask-specialist", "agent:python-reviewer"],
        }
    )
    result = _init(tmp_path)
    assert result.exit_code == 0, result.output
    assert (tmp_path / ".claude/skills/flask-specialist/SKILL.md").is_file()
    assert (tmp_path / ".claude/agents/python-reviewer.md").is_file()
    assert not (tmp_path / ".spado/project.json").exists()


def test_interactive_dry_run_and_declined_confirmation_write_nothing(tmp_path, interactive):
    picked = {"categories": [Category.BACKEND], "capabilities": ["skill:flask-specialist"]}
    interactive(picked)
    preview = _init(tmp_path, "--dry-run")
    assert preview.exit_code == 0, preview.output
    assert ".claude/skills/flask-specialist/SKILL.md" in preview.stdout
    interactive({**picked, "confirm": False})
    declined = _init(tmp_path)
    assert declined.exit_code == 1
    assert "Cancelled" in declined.stderr
    assert list(tmp_path.iterdir()) == []


def test_catalog_add_records_categories(tmp_path):
    catalog = tmp_path / "catalog"
    shutil.copytree(REAL_CATALOG, catalog, ignore=shutil.ignore_patterns("__pycache__"))
    source = tmp_path / "SKILL.md"
    source.write_text("---\nname: demo\ndescription: Demo skill.\n---\n\n# Demo\n")
    args = ["catalog", "add", "skill", str(source), "--catalog", str(catalog), "--yes"]
    bad = runner.invoke(app, [*args, "--category", "cooking"])
    assert bad.exit_code == 1
    assert "Unknown category" in bad.output
    ok = runner.invoke(app, [*args, "--category", "backend,testing"])
    assert ok.exit_code == 0, ok.output
    demo = load_catalog(catalog).require("skill:demo")
    assert demo.manifest.categories == [Category.BACKEND, Category.TESTING]
