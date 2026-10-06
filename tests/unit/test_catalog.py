import json
import os

import pytest

from cwi.catalog.loader import load_catalog
from cwi.catalog.validator import is_safe_relative, validate_catalog
from cwi.domain.errors import CatalogError
from cwi.domain.models import Capability, CapabilityManifest, Catalog
from tests.helpers import REAL_CATALOG, add_capability, agent_md, minimal_catalog, skill_md


def test_bundled_catalog_is_valid():
    catalog = load_catalog(REAL_CATALOG)
    refs = set(catalog.refs)
    assert {
        "skill:testing",
        "skill:debugging",
        "skill:backend-development",
        "skill:frontend-development",
        "agent:code-reviewer",
        "agent:security-reviewer",
        "script:run-quality-checks",
        "hook:safety-guard",
        "hook:post-edit-validation",
        "mcp:github",
    } <= refs


def test_bundled_catalog_has_no_literal_secrets():
    text = (REAL_CATALOG / "mcp" / "github" / "mcp.fragment.json").read_text()
    assert "${GITHUB_TOKEN}" in text
    assert "ghp_" not in text


def test_minimal_catalog_loads(tmp_path):
    catalog = load_catalog(minimal_catalog(tmp_path))
    assert catalog.get("agent:beta").manifest.dependencies == ["script:gamma"]
    assert catalog.get("skill:alpha").payload_files == [".claude/skills/alpha/SKILL.md"]


def test_missing_manifest_fails(tmp_path):
    (tmp_path / "catalog" / "skills" / "orphan").mkdir(parents=True)
    with pytest.raises(CatalogError, match="Missing manifest"):
        load_catalog(tmp_path / "catalog")


def test_invalid_json_fails(tmp_path):
    d = tmp_path / "catalog" / "skills" / "broken"
    d.mkdir(parents=True)
    (d / "cwi.json").write_text("{not json")
    with pytest.raises(CatalogError, match="Invalid JSON"):
        load_catalog(tmp_path / "catalog")


def test_unsupported_schema_version_fails(tmp_path):
    add_capability(
        tmp_path / "catalog",
        "skill",
        "future",
        {".claude/skills/future/SKILL.md": skill_md("future")},
        schema_version=2,
    )
    with pytest.raises(CatalogError, match="Unsupported catalog schema version: 2"):
        load_catalog(tmp_path / "catalog")


def test_type_directory_mismatch_fails(tmp_path):
    add_capability(
        tmp_path / "catalog",
        "skill",
        "x",
        {".claude/skills/x/SKILL.md": skill_md("x")},
        type="agent",
    )
    with pytest.raises(CatalogError, match="does not match"):
        load_catalog(tmp_path / "catalog")


def test_duplicate_ids_across_types_fail(tmp_path):
    catalog = tmp_path / "catalog"
    add_capability(
        catalog, "skill", "review", {".claude/skills/review/SKILL.md": skill_md("review")}
    )
    add_capability(catalog, "agent", "review", {".claude/agents/review.md": agent_md("review")})
    with pytest.raises(CatalogError, match="Duplicate capability id 'review'"):
        load_catalog(catalog)


def test_missing_payload_fails(tmp_path):
    add_capability(tmp_path / "catalog", "skill", "empty")
    with pytest.raises(CatalogError, match="missing payload .claude/skills/empty/SKILL.md"):
        load_catalog(tmp_path / "catalog")


def test_skill_frontmatter_required(tmp_path):
    add_capability(
        tmp_path / "catalog",
        "skill",
        "nofront",
        {".claude/skills/nofront/SKILL.md": "# no frontmatter\n"},
    )
    with pytest.raises(CatalogError, match="no YAML frontmatter"):
        load_catalog(tmp_path / "catalog")


def test_skill_frontmatter_description_required(tmp_path):
    add_capability(
        tmp_path / "catalog",
        "skill",
        "nodesc",
        {".claude/skills/nodesc/SKILL.md": "---\nname: nodesc\n---\n"},
    )
    with pytest.raises(CatalogError, match="missing 'description'"):
        load_catalog(tmp_path / "catalog")


def test_payload_outside_allowed_targets_fails(tmp_path):
    add_capability(
        tmp_path / "catalog",
        "skill",
        "sneaky",
        {
            ".claude/skills/sneaky/SKILL.md": skill_md("sneaky"),
            ".claude/agents/other.md": agent_md("other"),
        },
    )
    with pytest.raises(CatalogError, match="outside allowed targets"):
        load_catalog(tmp_path / "catalog")


def test_payload_cannot_ship_reserved_files(tmp_path):
    add_capability(
        tmp_path / "catalog",
        "script",
        "settings",
        {".claude/settings.json": "{}", "scripts/x.sh": "x"},
    )
    with pytest.raises(CatalogError, match="CWI generates/merges it"):
        load_catalog(tmp_path / "catalog")


@pytest.mark.parametrize("path", ["../../x", "/etc/passwd", "C:\\x", "a/../../b", "", ".."])
def test_unsafe_relative_paths(path):
    assert not is_safe_relative(path)


def test_path_traversal_payload_rejected(tmp_path):
    manifest = CapabilityManifest(
        schema_version=1, id="evil", type="script", name="e", description="d"
    )
    cap = Capability(manifest=manifest, source_dir=tmp_path, payload_files=["../../x"])
    with pytest.raises(CatalogError, match="unsafe payload path"):
        validate_catalog(Catalog(root=tmp_path, capabilities=[cap]))


def test_symlink_in_payload_rejected(tmp_path):
    catalog = tmp_path / "catalog"
    directory = add_capability(
        catalog, "skill", "linky", {".claude/skills/linky/SKILL.md": skill_md("linky")}
    )
    os.symlink("/etc", directory / "payload" / ".claude" / "skills" / "linky" / "escape")
    with pytest.raises(CatalogError, match="symlink"):
        load_catalog(catalog)


def test_symlinked_payload_dir_rejected(tmp_path):
    catalog = tmp_path / "catalog"
    directory = catalog / "skills" / "x"
    directory.mkdir(parents=True)
    (directory / "cwi.json").write_text(
        json.dumps(
            {"schema_version": 1, "id": "x", "type": "skill", "name": "x", "description": "d"}
        )
    )
    os.symlink(tmp_path, directory / "payload")
    with pytest.raises(CatalogError, match="symlink"):
        load_catalog(catalog)


def test_unknown_dependency_fails(tmp_path):
    add_capability(
        tmp_path / "catalog",
        "skill",
        "a",
        {".claude/skills/a/SKILL.md": skill_md("a")},
        dependencies=["script:missing"],
    )
    with pytest.raises(CatalogError, match="unknown dependency 'script:missing'"):
        load_catalog(tmp_path / "catalog")


def test_invalid_reference_format_fails(tmp_path):
    add_capability(
        tmp_path / "catalog",
        "skill",
        "a",
        {".claude/skills/a/SKILL.md": skill_md("a")},
        dependencies=["missing"],
    )
    with pytest.raises(CatalogError, match="invalid dependency reference"):
        load_catalog(tmp_path / "catalog")


def test_circular_dependencies_fail(tmp_path):
    catalog = tmp_path / "catalog"
    add_capability(
        catalog,
        "skill",
        "a",
        {".claude/skills/a/SKILL.md": skill_md("a")},
        dependencies=["skill:b"],
    )
    add_capability(
        catalog,
        "skill",
        "b",
        {".claude/skills/b/SKILL.md": skill_md("b")},
        dependencies=["skill:c"],
    )
    add_capability(
        catalog,
        "skill",
        "c",
        {".claude/skills/c/SKILL.md": skill_md("c")},
        dependencies=["skill:a"],
    )
    with pytest.raises(CatalogError, match="Circular dependency"):
        load_catalog(catalog)


def test_conflicting_target_files_fail(tmp_path):
    catalog = tmp_path / "catalog"
    add_capability(catalog, "script", "one", {"scripts/shared.sh": "1"})
    add_capability(catalog, "script", "two", {"scripts/shared.sh": "2"})
    with pytest.raises(CatalogError, match="Conflicting target file 'scripts/shared.sh'"):
        load_catalog(catalog)


def test_duplicate_mcp_server_names_fail(tmp_path):
    catalog = tmp_path / "catalog"
    frag = {"mcpServers": {"same": {"type": "http", "url": "https://a"}}}
    add_capability(catalog, "mcp", "one", mcp_fragment=frag)
    add_capability(catalog, "mcp", "two", mcp_fragment=frag)
    with pytest.raises(CatalogError, match="MCP server 'same'"):
        load_catalog(catalog)


def test_literal_secret_in_mcp_fragment_fails(tmp_path):
    frag = {
        "mcpServers": {
            "x": {
                "type": "http",
                "url": "https://a",
                "headers": {"Authorization": "Bearer ghp_realtoken"},
            }
        }
    }
    add_capability(tmp_path / "catalog", "mcp", "x", mcp_fragment=frag)
    with pytest.raises(CatalogError, match="literal secret"):
        load_catalog(tmp_path / "catalog")


def test_hook_requires_settings_fragment(tmp_path):
    add_capability(tmp_path / "catalog", "hook", "h", {".claude/hooks/h.py": "x"})
    with pytest.raises(CatalogError, match="non-empty 'hooks' object"):
        load_catalog(tmp_path / "catalog")


def test_junk_files_ignored(tmp_path):
    catalog = minimal_catalog(tmp_path)
    (
        catalog / "skills" / "alpha" / "payload" / ".claude" / "skills" / "alpha" / ".DS_Store"
    ).write_text("junk")
    loaded = load_catalog(catalog)
    assert loaded.get("skill:alpha").payload_files == [".claude/skills/alpha/SKILL.md"]
