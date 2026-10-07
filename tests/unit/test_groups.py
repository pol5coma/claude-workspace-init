"""Capability families: catalog/<type>/<group>/<id>/ with group.json defaults per project type."""

import json
import shutil

import pytest
from typer.testing import CliRunner

from cwi.catalog.loader import load_catalog
from cwi.catalog.recommender import recommend
from cwi.cli import app
from cwi.domain.enums import ProjectType
from cwi.domain.errors import CatalogError
from cwi.domain.models import ProjectProfile
from tests.helpers import REAL_CATALOG, add_capability, agent_md, run, tree

runner = CliRunner()


def make_group(catalog, gid="dev", defaults=None, members=("alpha", "beta"), cap_type="agent"):
    group = catalog / f"{cap_type}s" / gid
    group.mkdir(parents=True)
    (group / "group.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "id": gid,
                "type": cap_type,
                "name": "Dev agents",
                "defaults": defaults or {},
            }
        )
    )
    for cid in members:
        d = group / cid
        d.mkdir()
        (d / "cwi.json").write_text(
            json.dumps(
                {"schema_version": 1, "id": cid, "type": cap_type, "name": cid, "description": "d"}
            )
        )
        target = d / "payload" / ".claude" / "agents" / gid / f"{cid}.md"
        target.parent.mkdir(parents=True)
        target.write_text(agent_md(cid))
    return group


def test_bundled_development_family():
    catalog = load_catalog(REAL_CATALOG)
    group = catalog.group(catalog.require("agent:debugger").type, "development-agents")
    assert group is not None and group.name == "Development agents"
    members = [c for c in catalog.capabilities if c.group == "development-agents"]
    assert len(members) == 35
    assert catalog.require("agent:debugger").payload_files == [
        ".claude/agents/development-agents/debugger.md"
    ]
    assert catalog.require("agent:code-reviewer").group is None


def test_group_loads_and_sorts_after_ungrouped(tmp_path):
    catalog = tmp_path / "catalog"
    add_capability(catalog, "agent", "solo", {".claude/agents/solo.md": agent_md("solo")})
    make_group(catalog, defaults={"backend": ["alpha"]})
    loaded = load_catalog(catalog)
    from cwi.domain.enums import CapabilityType

    assert [c.id for c in loaded.by_type(CapabilityType.AGENT)] == ["solo", "alpha", "beta"]
    assert loaded.require("agent:alpha").group == "dev"


def test_family_defaults_drive_recommendations(tmp_path):
    catalog = tmp_path / "catalog"
    make_group(catalog, defaults={"backend": ["alpha"], "frontend": ["beta"]})
    loaded = load_catalog(catalog)
    backend = recommend(loaded, ProjectProfile(project_type=ProjectType.BACKEND))
    assert backend["agent:alpha"].preselected and not backend["agent:beta"].preselected
    assert "Dev agents default for backend api projects" in backend["agent:alpha"].reason_text
    assert recommend(loaded, ProjectProfile(project_type=ProjectType.FRONTEND))[
        "agent:beta"
    ].preselected
    assert not any(r.preselected for r in recommend(loaded, ProjectProfile()).values())


@pytest.mark.parametrize(
    "mutate,message",
    [
        (
            lambda g: (g / "group.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "id": "dev",
                        "type": "agent",
                        "name": "x",
                        "defaults": {"backend": ["ghost"]},
                    }
                )
            ),
            "not a member",
        ),
        (
            lambda g: (g / "group.json").write_text(
                json.dumps({"schema_version": 1, "id": "other", "type": "agent", "name": "x"})
            ),
            "does not match directory name",
        ),
        (
            lambda g: (g / "group.json").write_text(
                json.dumps({"schema_version": 1, "id": "dev", "type": "skill", "name": "x"})
            ),
            "does not match directory",
        ),
        (lambda g: (g / "alpha" / "group.json").write_text("{}"), "cannot be nested"),
        (lambda g: (g / "cwi.json").write_text("{}"), "both a capability"),
    ],
)
def test_group_validation(tmp_path, mutate, message):
    catalog = tmp_path / "catalog"
    mutate(make_group(catalog))
    with pytest.raises(CatalogError, match=message):
        load_catalog(catalog)


def test_grouped_agent_must_install_into_group_folder(tmp_path):
    catalog = tmp_path / "catalog"
    group = make_group(catalog, members=("alpha",))
    payload = group / "alpha" / "payload" / ".claude" / "agents"
    shutil.move(str(payload / "dev" / "alpha.md"), str(payload / "alpha.md"))
    shutil.rmtree(payload / "dev")
    with pytest.raises(CatalogError, match="missing payload .claude/agents/dev/alpha.md"):
        load_catalog(catalog)


def test_init_installs_family_and_removes_empty_folder(tmp_path, tmp_repo):
    catalog = tmp_path / "catalog"
    make_group(catalog, defaults={"backend": ["alpha", "beta"]})
    root = tmp_repo("python-fastapi")
    run(root, catalog=catalog)
    assert (root / ".claude/agents/dev/alpha.md").is_file()
    assert (root / ".claude/agents/dev/beta.md").is_file()
    first = tree(root)
    run(root, catalog=catalog)
    assert tree(root) == first
    run(root, {"select.agent": []}, catalog=catalog)
    assert not (root / ".claude/agents/dev").exists()  # emptied family folder removed
    assert (root / ".claude/agents").is_dir()


def test_local_grouped_catalog_is_cleaned_up(tmp_path, tmp_repo):
    root = tmp_repo("python-fastapi")
    make_group(root / "catalog", defaults={"backend": ["alpha"]})
    outcome, _, _ = run(root)
    assert outcome.applied and not (root / "catalog").exists()


# ---------------------------------------------------------------------------------------------
# Authoring
# ---------------------------------------------------------------------------------------------


def cli(*args):
    return runner.invoke(app, ["catalog", *args], catch_exceptions=False)


def test_add_agent_to_new_group_with_defaults(tmp_path):
    catalog = tmp_path / "catalog"
    shutil.copytree(REAL_CATALOG, catalog)
    src = tmp_path / "terraform-expert.md"
    src.write_text(
        "---\nname: terraform-expert\ndescription: Terraform help\ntools: Read, Bash\n---\nx\n"
    )
    result = cli(
        "add",
        "agent",
        str(src),
        "--group",
        "devops-agents",
        "--group-default",
        "backend,fullstack",
        "--catalog",
        str(catalog),
        "--yes",
    )
    assert result.exit_code == 0, result.stdout
    loaded = load_catalog(catalog)
    cap = loaded.require("agent:terraform-expert")
    assert cap.group == "devops-agents"
    assert cap.payload_files == [".claude/agents/devops-agents/terraform-expert.md"]
    group = json.loads((catalog / "agents/devops-agents/group.json").read_text())
    assert group["defaults"] == {"backend": ["terraform-expert"], "fullstack": ["terraform-expert"]}
    assert "agent:terraform-expert" in cli("list", "--catalog", str(catalog)).stdout


def test_group_default_requires_group(tmp_path):
    src = tmp_path / "a.md"
    src.write_text("---\nname: a\ndescription: d\n---\n")
    result = cli(
        "add",
        "agent",
        str(src),
        "--group-default",
        "backend",
        "--catalog",
        str(REAL_CATALOG),
        "--yes",
    )
    assert result.exit_code == 1 and "needs --group" in result.stdout


def test_group_create_defaults_and_remove_last_member(tmp_path):
    catalog = tmp_path / "catalog"
    shutil.copytree(REAL_CATALOG, catalog)
    assert (
        cli(
            "group",
            "create",
            "agent",
            "product-agents",
            "--name",
            "Product agents",
            "--catalog",
            str(catalog),
        ).exit_code
        == 0
    )
    src = tmp_path / "pm.md"
    src.write_text("---\nname: pm\ndescription: Writes PRDs\n---\nx\n")
    assert (
        cli(
            "add",
            "agent",
            str(src),
            "--group",
            "product-agents",
            "--catalog",
            str(catalog),
            "--yes",
        ).exit_code
        == 0
    )
    assert (
        cli(
            "group",
            "defaults",
            "agent",
            "product-agents",
            "fullstack",
            "pm",
            "--catalog",
            str(catalog),
        ).exit_code
        == 0
    )
    assert json.loads((catalog / "agents/product-agents/group.json").read_text())["defaults"] == {
        "fullstack": ["pm"]
    }
    bad = cli(
        "group",
        "defaults",
        "agent",
        "product-agents",
        "backend",
        "ghost",
        "--catalog",
        str(catalog),
    )
    assert bad.exit_code == 1 and "Not saved" in bad.stdout
    assert json.loads((catalog / "agents/product-agents/group.json").read_text())["defaults"] == {
        "fullstack": ["pm"]
    }
    assert cli("remove", "agent:pm", "--catalog", str(catalog), "--yes").exit_code == 0
    assert not (catalog / "agents/product-agents").exists()
    assert load_catalog(catalog).groups == [
        g for g in load_catalog(catalog).groups if g.id != "product-agents"
    ]


def test_remove_member_cleans_group_defaults(tmp_path):
    catalog = tmp_path / "catalog"
    shutil.copytree(REAL_CATALOG, catalog)
    assert cli("remove", "agent:debugger", "--catalog", str(catalog), "--yes").exit_code == 0
    group = json.loads((catalog / "agents/development-agents/group.json").read_text())
    assert all("debugger" not in ids for ids in group["defaults"].values())
    load_catalog(catalog)  # still valid


def test_group_name_cannot_shadow_capability(tmp_path):
    catalog = tmp_path / "catalog"
    shutil.copytree(REAL_CATALOG, catalog)
    src = tmp_path / "x.md"
    src.write_text("---\nname: x\ndescription: d\n---\n")
    result = cli(
        "add", "agent", str(src), "--group", "code-reviewer", "--catalog", str(catalog), "--yes"
    )
    assert result.exit_code == 1
