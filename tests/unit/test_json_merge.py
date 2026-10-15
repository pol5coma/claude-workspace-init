from spado.install.json_merge import deep_merge


def test_deep_merge_dicts_and_conflicts():
    merged, conflicts = deep_merge(
        {"a": {"b": 1, "c": [1]}, "x": 1}, {"a": {"d": 2, "c": [1, 2]}, "x": 2}
    )
    assert merged == {"a": {"b": 1, "c": [1, 2], "d": 2}, "x": 1}
    assert [c.path for c in conflicts] == ["x"]
