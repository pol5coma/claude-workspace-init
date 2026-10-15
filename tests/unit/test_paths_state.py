import json
import os

import pytest

from spado.domain.errors import StateError, UnsafePathError
from spado.domain.models import ManagedFile, SPADOState
from spado.planning.safety import resolve_inside
from spado.state.hashing import hash_tree, sha256_file, sha256_text
from spado.state.repository import StateRepository


def test_resolve_inside_accepts_normal_paths(tmp_path):
    assert (
        resolve_inside(tmp_path, ".claude/skills/x/SKILL.md")
        == tmp_path.resolve() / ".claude/skills/x/SKILL.md"
    )


@pytest.mark.parametrize("rel", ["../escape", "/etc/passwd", "a/../../b", ""])
def test_resolve_inside_rejects_escapes(tmp_path, rel):
    with pytest.raises(UnsafePathError):
        resolve_inside(tmp_path, rel)


def test_resolve_inside_rejects_symlinked_parent(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    repo = tmp_path / "repo"
    repo.mkdir()
    os.symlink(outside, repo / ".claude")
    with pytest.raises(UnsafePathError, match="symlink"):
        resolve_inside(repo, ".claude/settings.json")


def test_hashing(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("hello")
    assert sha256_file(f) == sha256_text("hello")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "x").write_text("ignored")
    assert set(hash_tree(tmp_path)) == {"a.txt"}


def test_state_roundtrip(tmp_path):
    repo = StateRepository(tmp_path)
    assert repo.load() is None
    state = SPADOState(
        spado_version="0.1.0",
        initialized_at="t",
        managed_files={"a": ManagedFile(owner="o", sha256="h")},
    )
    repo.path.parent.mkdir(parents=True)
    repo.path.write_text(StateRepository.serialize(state))
    assert repo.load() == state


def test_state_never_contains_secret_values(tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_supersecret")
    state = SPADOState(spado_version="0.1.0", initialized_at="t")
    assert "ghp_supersecret" not in StateRepository.serialize(state)


def test_unsupported_state_schema(tmp_path):
    path = tmp_path / ".claude" / "spado-state.json"
    path.parent.mkdir()
    path.write_text(json.dumps({"schema_version": 99}))
    with pytest.raises(StateError, match="Unsupported SPADO state schema version: 99"):
        StateRepository(tmp_path).load()


def test_corrupt_state(tmp_path):
    path = tmp_path / ".claude" / "spado-state.json"
    path.parent.mkdir()
    path.write_text("{")
    with pytest.raises(StateError):
        StateRepository(tmp_path).load()
