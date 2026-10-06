import json

import pytest

from cwi.catalog.loader import load_catalog
from cwi.domain.enums import ClaudeMdMode, OperationType
from cwi.domain.errors import ConflictError, PlanError
from cwi.domain.models import ClaudeMdDecision, ProjectProfile
from cwi.planning.planner import FileDecision, McpDecision, PlanInputs, build_plan, find_decisions
from cwi.state.hashing import hash_tree
from tests.helpers import minimal_catalog


def inputs(root, catalog, selected, **kw):
    defaults = dict(
        root=root,
        profile=ProjectProfile(),
        catalog=catalog,
        state=None,
        claude_md=ClaudeMdDecision(mode=ClaudeMdMode.CREATE, content="# Project Instructions\n"),
        selected=selected,
        now="2026-10-06T12:00:00Z",
    )
    defaults.update(kw)
    return PlanInputs(**defaults)


@pytest.fixture
def setup(tmp_path):
    catalog = load_catalog(minimal_catalog(tmp_path / "src"))
    repo = tmp_path / "repo"
    repo.mkdir()
    return repo, catalog


def test_plan_is_pure_and_deterministic(setup):
    repo, catalog = setup
    before = hash_tree(repo)
    refs = ["skill:alpha", "agent:beta", "script:gamma", "hook:delta", "mcp:epsilon"]
    a = build_plan(inputs(repo, catalog, refs))
    b = build_plan(inputs(repo, catalog, list(reversed(refs))))
    assert a.model_dump() == b.model_dump()
    assert hash_tree(repo) == before  # planner wrote nothing


def test_plan_operation_order(setup):
    repo, catalog = setup
    plan = build_plan(inputs(repo, catalog, ["skill:alpha", "hook:delta", "mcp:epsilon"]))
    kinds = [op.type for op in plan.operations]
    assert kinds[0] == OperationType.MKDIR
    targets = [op.target for op in plan.operations]
    assert (
        targets.index(".claude")
        < targets.index(".claude/skills")
        < targets.index(".claude/skills/alpha/SKILL.md")
    )
    assert targets[-1] == ".claude/cwi-state.json"
    assert {".mcp.json", ".claude/settings.json", "CLAUDE.md"} <= set(targets)
    assert plan.state.managed_files[".claude/skills/alpha/SKILL.md"].owner == "skill:alpha"
    assert plan.state.mcp_servers["epsilon"].owner == "mcp:epsilon"
    assert plan.state.settings_hooks["hook:delta"][0].event == "PreToolUse"


def test_unknown_capability_rejected(setup):
    repo, catalog = setup
    with pytest.raises(PlanError, match="Unknown capabilities"):
        build_plan(inputs(repo, catalog, ["skill:nope"]))


def test_existing_user_file_requires_decision(setup):
    repo, catalog = setup
    (repo / "scripts").mkdir()
    (repo / "scripts" / "gamma.sh").write_text("my own script\n")
    i = inputs(repo, catalog, ["script:gamma"])
    decisions = find_decisions(i)
    assert len(decisions) == 1 and isinstance(decisions[0], FileDecision)
    assert decisions[0].kind == "user_file"
    with pytest.raises(ConflictError):
        build_plan(i)
    i.resolutions["file:scripts/gamma.sh"] = "keep"
    plan = build_plan(i)
    assert all(op.target != "scripts/gamma.sh" for op in plan.operations)
    assert "scripts/gamma.sh" not in plan.state.managed_files
    i.resolutions["file:scripts/gamma.sh"] = "replace"
    plan = build_plan(i)
    op = next(op for op in plan.operations if op.target == "scripts/gamma.sh")
    assert op.before_hash is not None  # backed up and replaced


def test_identical_existing_file_is_adopted_without_decision(setup):
    repo, catalog = setup
    (repo / "scripts").mkdir()
    (repo / "scripts" / "gamma.sh").write_text("#!/bin/sh\necho gamma\n")
    plan = build_plan(inputs(repo, catalog, ["script:gamma"]))
    assert all(op.target != "scripts/gamma.sh" for op in plan.operations)
    assert plan.state.managed_files["scripts/gamma.sh"].owner == "script:gamma"


def test_mcp_conflict_requires_decision(setup):
    repo, catalog = setup
    (repo / ".mcp.json").write_text(
        json.dumps({"mcpServers": {"epsilon": {"url": "mine"}, "other": {"url": "o"}}})
    )
    i = inputs(repo, catalog, ["mcp:epsilon"])
    decisions = find_decisions(i)
    assert len(decisions) == 1 and isinstance(decisions[0], McpDecision)
    i.resolutions["mcp:epsilon"] = "keep"
    plan = build_plan(i)
    assert all(op.target != ".mcp.json" for op in plan.operations)
    i.resolutions["mcp:epsilon"] = "replace"
    plan = build_plan(i)
    merged = json.loads(
        next(op for op in plan.operations if op.target == ".mcp.json").after_content
    )
    assert merged["mcpServers"]["other"] == {"url": "o"}
    assert merged["mcpServers"]["epsilon"]["url"] == "https://example.com/mcp"


def test_invalid_existing_settings_fails_before_mutation(setup):
    repo, catalog = setup
    (repo / ".claude").mkdir()
    (repo / ".claude" / "settings.json").write_text("{ not json")
    with pytest.raises(PlanError, match="not valid JSON"):
        build_plan(inputs(repo, catalog, ["hook:delta"]))


def test_claude_md_keep_produces_no_operation(setup):
    repo, catalog = setup
    (repo / "CLAUDE.md").write_text("# Mine\n")
    plan = build_plan(inputs(repo, catalog, [], claude_md=ClaudeMdDecision(mode=ClaudeMdMode.KEEP)))
    assert all(op.target != "CLAUDE.md" for op in plan.operations)


def test_template_cleanup_requires_gate(setup):
    repo, catalog = setup
    (repo / "catalog").mkdir()
    (repo / ".cwi-template.json").write_text("{}")
    (repo / "pyproject.toml").write_text('[project]\nname = "someone-else"\n')
    plan = build_plan(inputs(repo, catalog, [], cleanup_template=True))
    assert not any(op.owner == "cwi-template" for op in plan.operations)
    assert any("Bootstrap cleanup skipped" in w for w in plan.warnings)


def test_template_cleanup_with_gate(setup):
    repo, catalog = setup
    for d in ("catalog", "templates", "src/cwi", "tests", "src/myapp"):
        (repo / d).mkdir(parents=True)
    (repo / ".cwi-template.json").write_text(
        json.dumps({"bootstrap_paths": ["catalog", "src", "tests", "../../etc"]})
    )
    (repo / "pyproject.toml").write_text('[project]\nname = "claude-workspace-init"\n')
    plan = build_plan(inputs(repo, catalog, [], cleanup_template=True))
    deleted = {op.target for op in plan.operations if op.owner == "cwi-template"}
    # The marker can only narrow the known bootstrap set: "src" and "../../etc" are ignored.
    assert deleted == {"catalog", "tests", ".cwi-template.json", "src"}
    src = next(op for op in plan.operations if op.target == "src")
    assert src.only_if_empty


def test_local_catalog_cleanup_only_when_it_looks_like_cwi(tmp_path):
    repo = tmp_path / "repo"
    catalog_dir = minimal_catalog(repo)
    catalog = load_catalog(catalog_dir)
    plan = build_plan(inputs(repo, catalog, ["skill:alpha"], cleanup_catalog=True))
    assert any(op.target == "catalog" and op.owner == "cwi-catalog" for op in plan.operations)
    (catalog_dir / "my-notes.txt").write_text("user file")
    plan = build_plan(inputs(repo, catalog, ["skill:alpha"], cleanup_catalog=True))
    assert not any(op.target == "catalog" for op in plan.operations)
    assert any("does not recognise" in w for w in plan.warnings)
