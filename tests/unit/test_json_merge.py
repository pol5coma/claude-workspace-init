import pytest

from cwi.install.json_merge import (
    deep_merge,
    fragment_hook_refs,
    merge_hooks,
    merge_mcp,
    remove_hooks,
)

GUARD = {
    "hooks": {
        "PreToolUse": [
            {
                "matcher": "Bash",
                "hooks": [{"type": "command", "command": "python3 guard.py", "timeout": 30}],
            }
        ]
    }
}


def test_deep_merge_dicts_and_conflicts():
    merged, conflicts = deep_merge(
        {"a": {"b": 1, "c": [1]}, "x": 1}, {"a": {"d": 2, "c": [1, 2]}, "x": 2}
    )
    assert merged == {"a": {"b": 1, "c": [1, 2], "d": 2}, "x": 1}
    assert [c.path for c in conflicts] == ["x"]


def test_merge_hooks_into_empty_settings():
    result = merge_hooks({}, GUARD)
    assert result.settings == GUARD
    assert len(result.added) == 1


def test_merge_hooks_preserves_existing_settings_and_hooks():
    existing = {
        "permissions": {"allow": ["Bash(ls)"]},
        "hooks": {
            "PreToolUse": [
                {"matcher": "Bash", "hooks": [{"type": "command", "command": "python3 custom.py"}]}
            ]
        },
    }
    result = merge_hooks(existing, GUARD)
    assert result.settings["permissions"] == {"allow": ["Bash(ls)"]}
    commands = [h["command"] for h in result.settings["hooks"]["PreToolUse"][0]["hooks"]]
    assert commands == ["python3 custom.py", "python3 guard.py"]
    assert len(result.neighbours) == 1  # coexistence notice, not a conflict
    assert (
        existing["hooks"]["PreToolUse"][0]["hooks"][0]["command"] == "python3 custom.py"
    )  # input untouched


def test_merge_hooks_is_idempotent():
    once = merge_hooks({}, GUARD).settings
    twice = merge_hooks(once, GUARD)
    assert twice.settings == once
    assert twice.added == []
    assert len(twice.already_present) == 1


def test_merge_hooks_new_matcher_group():
    existing = {
        "hooks": {
            "PreToolUse": [{"matcher": "Edit", "hooks": [{"type": "command", "command": "x"}]}]
        }
    }
    result = merge_hooks(existing, GUARD).settings
    assert [g["matcher"] for g in result["hooks"]["PreToolUse"]] == ["Edit", "Bash"]


def test_merge_hooks_refuses_malformed_existing():
    with pytest.raises(ValueError):
        merge_hooks({"hooks": []}, GUARD)


def test_remove_hooks_only_removes_owned_entries():
    existing = {
        "hooks": {
            "PreToolUse": [
                {"matcher": "Bash", "hooks": [{"type": "command", "command": "python3 custom.py"}]}
            ]
        }
    }
    merged = merge_hooks(existing, GUARD).settings
    removed = remove_hooks(merged, fragment_hook_refs(GUARD))
    assert removed == existing


def test_remove_hooks_prunes_empty_structures():
    merged = merge_hooks({"model": "x"}, GUARD).settings
    assert remove_hooks(merged, fragment_hook_refs(GUARD)) == {"model": "x"}


def test_merge_mcp_add_noop_conflict():
    frag = {"mcpServers": {"github": {"type": "http", "url": "https://a"}}}
    added = merge_mcp({"mcpServers": {"linear": {"url": "l"}}}, frag)
    assert added.added == ["github"]
    assert set(added.config["mcpServers"]) == {"linear", "github"}

    noop = merge_mcp(added.config, frag)
    assert noop.unchanged == ["github"] and noop.added == []

    conflict = merge_mcp({"mcpServers": {"github": {"url": "other"}}}, frag)
    assert conflict.conflicts == ["github"]
    assert conflict.config["mcpServers"]["github"] == {"url": "other"}  # never silently replaced


def test_merge_mcp_resolutions():
    frag = {"mcpServers": {"github": {"url": "new"}}}
    existing = {"mcpServers": {"github": {"url": "old"}}}
    assert merge_mcp(existing, frag, {"github": "keep"}).config["mcpServers"]["github"] == {
        "url": "old"
    }
    assert merge_mcp(existing, frag, {"github": "replace"}).config["mcpServers"]["github"] == {
        "url": "new"
    }
