"""`cwi catalog` authoring: builders, writer and CLI."""

import json
import os
import shutil

import pytest
from typer.testing import CliRunner

from cwi.authoring.builder import AuthoringError, Metadata, build_skill, set_frontmatter, slugify
from cwi.authoring.writer import write_capability
from cwi.catalog.frontmatter import parse_frontmatter
from cwi.catalog.loader import load_catalog
from cwi.cli import app
from tests.helpers import REAL_CATALOG

runner = CliRunner()


@pytest.fixture
def catalog(tmp_path):
    target = tmp_path / "catalog"
    shutil.copytree(REAL_CATALOG, target, ignore=shutil.ignore_patterns("__pycache__", ".DS_Store"))
    return target


@pytest.fixture
def sources(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    return src


def cli(*args):
    return runner.invoke(app, ["catalog", *args], catch_exceptions=False)


def test_slugify():
    assert slugify("Senior Code Reviewer") == "senior-code-reviewer"
    assert slugify("API_design v2") == "api-design-v2"
    with pytest.raises(AuthoringError):
        slugify("!!!")


def test_set_frontmatter_preserves_other_keys():
    text = "---\nname: Old\ndescription: >\n  folded\n  text\nallowed-tools: Read\n---\n\nBody\n"
    out = set_frontmatter(text, {"name": "old"})
    front = parse_frontmatter(out)
    assert front["name"] == "old"
    assert front["allowed-tools"] == "Read"
    assert "folded" in front["description"]
    assert out.endswith("Body\n")


def test_add_skill_file_with_refs_and_scripts(catalog, sources):
    (sources / "SKILL.md").write_text(
        "---\nname: API Design\ndescription: REST API design rules.\n---\n\n# API\n"
    )
    (sources / "rest.md").write_text("# REST\n")
    (sources / "lint.py").write_text("print(1)\n")
    os.chmod(sources / "lint.py", 0o755)
    result = cli(
        "add",
        "skill",
        str(sources / "SKILL.md"),
        "--ref",
        str(sources / "rest.md"),
        "--script",
        str(sources / "lint.py"),
        "--type",
        "backend,fullstack",
        "--tech",
        "FastAPI",
        "--catalog",
        str(catalog),
        "--yes",
    )
    assert result.exit_code == 0, result.stdout
    cap = load_catalog(catalog).get("skill:api-design")
    assert sorted(cap.payload_files) == [
        ".claude/skills/api-design/SKILL.md",
        ".claude/skills/api-design/references/rest.md",
        ".claude/skills/api-design/scripts/lint.py",
    ]
    manifest = cap.manifest
    assert manifest.description == "REST API design rules."
    assert [t.value for t in manifest.recommendation.project_types] == ["backend", "fullstack"]
    assert manifest.recommendation.technologies == ["fastapi"]
    assert os.access(cap.payload_dir / ".claude/skills/api-design/scripts/lint.py", os.X_OK)
    assert (
        parse_frontmatter((cap.payload_dir / ".claude/skills/api-design/SKILL.md").read_text())[
            "name"
        ]
        == "api-design"
    )


def test_add_skill_folder(catalog, sources):
    folder = sources / "migrations"
    (folder / "references").mkdir(parents=True)
    (folder / "SKILL.md").write_text(
        "---\nname: migrations\ndescription: Safe DB migrations.\n---\n"
    )
    (folder / "references" / "alembic.md").write_text("x")
    (folder / ".DS_Store").write_text("junk")
    assert (
        cli("add", "skill", str(folder), "--default", "--catalog", str(catalog), "--yes").exit_code
        == 0
    )
    cap = load_catalog(catalog).get("skill:migrations")
    assert cap.manifest.default_selected
    assert ".claude/skills/migrations/references/alembic.md" in cap.payload_files
    assert not any(".DS_Store" in f for f in cap.payload_files)


def test_skill_without_frontmatter_needs_description(catalog, sources):
    (sources / "notes.md").write_text("")
    result = cli("add", "skill", str(sources / "notes.md"), "--catalog", str(catalog), "--yes")
    assert result.exit_code == 1
    assert "needs a description" in result.stdout
    (sources / "notes.md").write_text("# Notes\n\nKeep notes short and factual.\n")
    assert (
        cli("add", "skill", str(sources / "notes.md"), "--catalog", str(catalog), "--yes").exit_code
        == 0
    )
    text = (catalog / "skills/notes/payload/.claude/skills/notes/SKILL.md").read_text()
    assert parse_frontmatter(text) == {
        "name": "notes",
        "description": "Keep notes short and factual.",
    }


def test_agent_file_rejected_as_skill_non_interactive(catalog, sources):
    (sources / "rev.md").write_text(
        "---\nname: rev\ndescription: Use this agent to review\ntools: Read\n---\nYou are a reviewer.\n"
    )
    result = cli("add", "skill", str(sources / "rev.md"), "--catalog", str(catalog), "--yes")
    assert result.exit_code == 1
    assert "cwi catalog add agent" in result.stdout
    assert not (catalog / "skills" / "rev").exists()


def test_convert_tools_to_allowed_tools(sources):
    (sources / "SKILL.md").write_text(
        "---\nname: x\ndescription: d\ntools: Read, Grep\n---\nbody\n"
    )
    built = build_skill(sources / "SKILL.md", Metadata(), [], [], convert_tools=True)
    front = parse_frontmatter(built.payload[".claude/skills/x/SKILL.md"])
    assert front["allowed-tools"] == "Read, Grep"
    assert "tools" not in front


def test_add_agent_with_script(catalog, sources):
    (sources / "dba.md").write_text(
        "---\nname: DBA\ndescription: Reviews SQL and migrations.\ntools: Read, Bash\nmodel: sonnet\n---\nYou are a DBA.\n"
    )
    (sources / "explain.py").write_text("print('plan')\n")
    result = cli(
        "add",
        "agent",
        str(sources / "dba.md"),
        "--script",
        str(sources / "explain.py"),
        "--depends",
        "script:run-quality-checks",
        "--catalog",
        str(catalog),
        "--yes",
    )
    assert result.exit_code == 0, result.stdout
    cap = load_catalog(catalog).get("agent:dba")
    assert sorted(cap.payload_files) == [".claude/agents/dba.md", ".claude/scripts/dba/explain.py"]
    assert cap.manifest.dependencies == ["script:run-quality-checks"]
    front = parse_frontmatter((cap.payload_dir / ".claude/agents/dba.md").read_text())
    assert front["tools"] == "Read, Bash" and front["model"] == "sonnet"


def test_agent_requires_frontmatter(catalog, sources):
    (sources / "a.md").write_text("You are an agent.\n")
    result = cli("add", "agent", str(sources / "a.md"), "--catalog", str(catalog), "--yes")
    assert result.exit_code == 1
    assert "no YAML frontmatter" in result.stdout


def test_add_hook(catalog, sources):
    (sources / "block-prod.sh").write_text("#!/bin/sh\nexit 0\n")
    result = cli(
        "add",
        "hook",
        str(sources / "block-prod.sh"),
        "--event",
        "PreToolUse",
        "--matcher",
        "Bash",
        "--timeout",
        "10",
        "-d",
        "Blocks prod deploys",
        "--catalog",
        str(catalog),
        "--yes",
    )
    assert result.exit_code == 0, result.stdout
    cap = load_catalog(catalog).get("hook:block-prod")
    group = cap.settings_fragment["hooks"]["PreToolUse"][0]
    assert group["matcher"] == "Bash"
    assert group["hooks"][0] == {
        "type": "command",
        "command": 'bash "${CLAUDE_PROJECT_DIR}/.claude/hooks/block-prod.sh"',
        "timeout": 10,
    }


def test_hook_validation(catalog, sources):
    (sources / "h.py").write_text("x")
    assert (
        cli(
            "add",
            "hook",
            str(sources / "h.py"),
            "--event",
            "Nope",
            "--catalog",
            str(catalog),
            "--yes",
        ).exit_code
        == 1
    )
    result = cli(
        "add",
        "hook",
        str(sources / "h.py"),
        "--event",
        "Stop",
        "--matcher",
        "Bash",
        "--catalog",
        str(catalog),
        "--yes",
    )
    assert result.exit_code == 1 and "--matcher only applies" in result.stdout


def test_add_script_requires_description(catalog, sources):
    (sources / "seed.sh").write_text("echo seed\n")
    assert (
        cli("add", "script", str(sources / "seed.sh"), "--catalog", str(catalog), "--yes").exit_code
        == 1
    )
    assert (
        cli(
            "add",
            "script",
            str(sources / "seed.sh"),
            "-d",
            "Seeds dev data",
            "--catalog",
            str(catalog),
            "--yes",
        ).exit_code
        == 0
    )
    assert load_catalog(catalog).get("script:seed").payload_files == ["scripts/seed.sh"]


def test_add_mcp_remote_and_local(catalog):
    result = cli(
        "add",
        "mcp",
        "linear",
        "--url",
        "https://mcp.linear.app/mcp",
        "--header",
        "Authorization=Bearer ${LINEAR_TOKEN}",
        "--catalog",
        str(catalog),
        "--yes",
    )
    assert result.exit_code == 0, result.stdout
    cap = load_catalog(catalog).get("mcp:linear")
    assert cap.mcp_fragment == {
        "mcpServers": {
            "linear": {
                "type": "http",
                "url": "https://mcp.linear.app/mcp",
                "headers": {"Authorization": "Bearer ${LINEAR_TOKEN}"},
            }
        }
    }
    assert [e.name for e in cap.manifest.requirements.env] == ["LINEAR_TOKEN"]

    result = cli(
        "add",
        "mcp",
        "postgres",
        "--command",
        "npx",
        "--arg",
        "-y",
        "--arg",
        "@modelcontextprotocol/server-postgres",
        "--arg",
        "${DATABASE_URL}",
        "--catalog",
        str(catalog),
        "--yes",
    )
    assert result.exit_code == 0, result.stdout
    server = load_catalog(catalog).get("mcp:postgres").mcp_fragment["mcpServers"]["postgres"]
    assert server["command"] == "npx" and server["args"][-1] == "${DATABASE_URL}"


def test_mcp_literal_secret_leaves_nothing(catalog):
    before = sorted(p.name for p in (catalog / "mcp").iterdir())
    result = cli(
        "add",
        "mcp",
        "leak",
        "--url",
        "https://x",
        "--header",
        "Authorization=Bearer abc123",
        "--catalog",
        str(catalog),
        "--yes",
    )
    assert result.exit_code == 1
    assert "literal secret" in result.stdout
    assert sorted(p.name for p in (catalog / "mcp").iterdir()) == before


def test_mcp_needs_exactly_one_transport(catalog):
    assert cli("add", "mcp", "x", "--catalog", str(catalog), "--yes").exit_code == 1


def test_duplicate_ids_and_force(catalog, sources):
    (sources / "SKILL.md").write_text("---\nname: code-reviewer\ndescription: d\n---\n")
    result = cli("add", "skill", str(sources / "SKILL.md"), "--catalog", str(catalog), "--yes")
    assert result.exit_code == 1 and "already used by agent:code-reviewer" in result.stdout

    (sources / "SKILL.md").write_text("---\nname: testing\ndescription: replacement\n---\n")
    result = cli("add", "skill", str(sources / "SKILL.md"), "--catalog", str(catalog), "--yes")
    assert result.exit_code == 1 and "--force" in result.stdout
    assert (
        cli(
            "add", "skill", str(sources / "SKILL.md"), "--force", "--catalog", str(catalog), "--yes"
        ).exit_code
        == 0
    )
    cap = load_catalog(catalog).get("skill:testing")
    assert cap.manifest.description == "replacement"
    assert cap.payload_files == [".claude/skills/testing/SKILL.md"]  # replaced, not merged
    assert not [
        p for p in (catalog / "skills").iterdir() if p.name.startswith(".")
    ]  # no temp leftovers


def test_refuses_when_catalog_already_invalid(catalog, sources):
    (catalog / "skills" / "broken").mkdir()
    (sources / "SKILL.md").write_text("---\nname: ok\ndescription: d\n---\n")
    with pytest.raises(AuthoringError, match="already invalid"):
        write_capability(catalog, build_skill(sources / "SKILL.md", Metadata(), [], []))


def test_list_validate_remove(catalog):
    result = cli("list", "--catalog", str(catalog))
    assert result.exit_code == 0 and "skill:testing" in result.stdout
    assert "Catalog valid: 10" in cli("validate", "--catalog", str(catalog)).stdout

    result = cli("remove", "script:run-quality-checks", "--catalog", str(catalog), "--yes")
    assert result.exit_code == 1 and "required by agent:code-reviewer" in result.stdout
    assert cli("remove", "skill:debugging", "--catalog", str(catalog), "--yes").exit_code == 0
    assert load_catalog(catalog).get("skill:debugging") is None
    assert cli("remove", "skill:nope", "--catalog", str(catalog), "--yes").exit_code == 1


def test_validate_reports_problems(catalog):
    (catalog / "skills" / "broken").mkdir()
    result = cli("validate", "--catalog", str(catalog))
    assert result.exit_code == 1 and "Missing manifest" in result.stdout


def test_new_capability_is_installed_by_init(catalog, sources, tmp_repo):
    (sources / "SKILL.md").write_text(
        "---\nname: house-style\ndescription: Team writing style.\n---\n# Style\n"
    )
    assert (
        cli(
            "add",
            "skill",
            str(sources / "SKILL.md"),
            "--default",
            "--catalog",
            str(catalog),
            "--yes",
        ).exit_code
        == 0
    )
    from tests.helpers import run

    root = tmp_repo("python-fastapi")
    run(root, catalog=catalog)
    assert (root / ".claude/skills/house-style/SKILL.md").is_file()
    assert json.loads((root / ".claude/cwi-state.json").read_text())["selected_capabilities"][0]
