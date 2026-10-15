import os

import pytest

from spado.domain.errors import UnsafePathError
from spado.install.safety import resolve_inside


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
