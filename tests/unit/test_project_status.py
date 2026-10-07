"""kickoff's project-status.py: read-only state detection and next-step routing."""

import json
import subprocess
import sys

import pytest

from tests.helpers import REAL_CATALOG, tree

SCRIPT = REAL_CATALOG / "skills/kickoff/payload/.claude/skills/kickoff/scripts/project-status.py"
TEMPLATE = "<!-- cwi:architecture-template · run project-discovery -->\n# Architecture\n"


def status(root):
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(root)], capture_output=True, text=True, timeout=30
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def write(root, rel, text):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def spec(slug, state, questions=""):
    return f"# {slug}\n\nStatus: {state}\n\n## Acceptance criteria\n\n- Given x\n\n## Open questions\n\n{questions}\n"


@pytest.fixture
def project(tmp_path):
    write(tmp_path, "docs/architecture.md", "# Architecture\n\nReal content.\n")
    return tmp_path


def test_code_without_architecture(tmp_path):
    write(tmp_path, "src/app.ts", "export {}\n")
    data = status(tmp_path)
    assert data["architecture"]["state"] == "missing" and data["code"] is True
    assert data["next"] == "discovery:code"


def test_template_without_code_detects_requirements(tmp_path):
    write(tmp_path, "docs/architecture.md", TEMPLATE)
    write(tmp_path, "docs/requirements/vision.md", "# Vision\n")
    write(tmp_path, "docs/PRD-checkout.md", "# PRD\n")
    write(tmp_path, ".claude/hooks/safety-guard.py", "x")  # CWI files are not project code
    write(tmp_path, "scripts/run-quality-checks.py", "x")
    data = status(tmp_path)
    assert data["architecture"]["state"] == "template" and data["code"] is False
    assert data["next"] == "discovery:new"
    assert (
        "docs/requirements/" in data["requirements"]
        and "docs/PRD-checkout.md" in data["requirements"]
    )


def test_architecture_pointer_from_agents_md(tmp_path):
    write(
        tmp_path,
        "AGENTS.md",
        "## Project docs\n\n- Architecture and versions: `ARCH.md`. Read it.\n",
    )
    write(tmp_path, "ARCH.md", "# Ours\n")
    data = status(tmp_path)
    assert data["architecture"] == {"state": "defined", "path": "ARCH.md"}


def test_in_progress_beats_ready_and_backlog_order(project):
    write(
        project,
        "docs/specs/README.md",
        "# Specs\n\n## Backlog\n\n1. `checkout` — pay\n2. `login` — auth\n",
    )
    write(project, "docs/specs/login.md", spec("login", "ready"))
    write(project, "docs/specs/checkout.md", spec("checkout", "ready"))
    assert status(project)["next"] == "workflow:checkout"  # backlog order
    write(project, "docs/specs/login.md", spec("login", "in progress"))
    assert status(project)["next"] == "workflow:login"


def test_ready_with_open_questions_goes_back_to_spec(project):
    write(project, "docs/specs/login.md", spec("login", "ready", "- Which SSO providers?"))
    data = status(project)
    assert data["specs"][0]["open_questions"] == 1
    assert data["next"] == "spec:login"


def test_untouched_template_status_is_draft(project):
    write(
        project, "docs/specs/search.md", "# Search\n\nStatus: draft | ready | in progress | done\n"
    )
    assert status(project)["next"] == "spec:search"


def test_backlog_without_specs(project):
    write(
        project,
        "docs/specs/README.md",
        "## Backlog\n\n<!-- comment -->\n1. `project-setup` — skeleton\n2. `login`\n",
    )
    write(project, "docs/specs/_template.md", "Status: draft | ready\n")
    data = status(project)
    assert data["backlog"] == ["project-setup", "login"]
    assert data["next"] == "spec:project-setup"


def test_nothing_yet_and_all_done(project):
    assert status(project)["next"] == "spec:new"
    write(project, "docs/specs/README.md", "## Backlog\n\n1. `login`\n")
    write(project, "docs/specs/login.md", spec("login", "done"))
    assert status(project)["next"] == "done"


def test_script_is_read_only(tmp_path):
    write(tmp_path, "docs/architecture.md", TEMPLATE)
    write(tmp_path, "docs/specs/a.md", spec("a", "ready"))
    before = tree(tmp_path)
    status(tmp_path)
    assert tree(tmp_path) == before


def test_installed_by_init_and_works(tmp_repo, real_catalog):
    from tests.helpers import run

    root = tmp_repo("react-vite")
    run(root, catalog=real_catalog)
    installed = root / ".claude/skills/kickoff/scripts/project-status.py"
    assert installed.is_file()
    result = subprocess.run(
        [sys.executable, str(installed), str(root)], capture_output=True, text=True
    )
    assert json.loads(result.stdout)["next"] == "discovery:code"


def test_reports_diagrams(project):
    assert status(project)["diagrams"] == []
    write(project, "docs/diagrams/architecture-app/app.html", "<html></html>")
    write(project, ".archify/workflow-x-1/x.html", "<html></html>")
    assert status(project)["diagrams"] == [
        "docs/diagrams/architecture-app/app.html",
        ".archify/workflow-x-1/x.html",
    ]
