import json
import tomllib
from pathlib import Path

import pytest
from typer.testing import CliRunner

from spado.adapters.hosts import render
from spado.cli import app
from spado.runtime.config import Embeddings, ProjectConfig
from spado.runtime.install import install, resources
from spado.workflows.models import Mode

CATALOG = Path(__file__).resolve().parents[2] / "catalog"


def settings():
    return ProjectConfig(
        hosts=["claude", "codex"],
        mode=Mode.AUTO,
        embeddings=Embeddings(backend="local", model="test-model"),
    )


def tree(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def test_native_resources_have_real_agents_and_skills():
    generated = render(CATALOG, "codex")
    agents = [tomllib.loads(body.decode()) for p, body in generated.items() if p.endswith(".toml")]
    assert len(agents) == 72
    assert all(a["name"] and a["description"] and a["developer_instructions"] for a in agents)
    assert ".agents/skills/spdlc/SKILL.md" in generated
    assert ".agents/skills/spado/SKILL.md" in generated
    claude = render(CATALOG, "claude")
    assert b"skills:" in claude[".claude/agents/ctao.md"]


def test_install_dry_run_idempotency_and_conflict(tmp_path):
    desired = resources(CATALOG, settings())
    assert install(tmp_path, desired, dry_run=True)["writes"]
    assert not tree(tmp_path)
    install(tmp_path, desired)
    first = tree(tmp_path)
    assert install(tmp_path, desired)["writes"] == []
    assert tree(tmp_path) == first
    changed = tmp_path / ".agents/skills/spado/SKILL.md"
    changed.write_text("User changes")
    before = tree(tmp_path)
    with pytest.raises(ValueError, match="conflict"):
        install(tmp_path, desired)
    assert tree(tmp_path) == before


def test_install_rejects_symlink_escape(tmp_path):
    (tmp_path / ".agents").symlink_to(tmp_path.parent, target_is_directory=True)
    with pytest.raises(Exception, match="symlink|outside|Symlink"):
        install(tmp_path, {".agents/escape.md": b"No"})


def test_install_rolls_back_failure(tmp_path, monkeypatch):
    from spado.install.filesystem import FileSystem

    original = FileSystem.atomic_write_bytes
    calls = 0

    def failing(self, path, body):
        nonlocal calls
        calls += 1
        if calls == 3:
            raise OSError("Injected failure")
        return original(self, path, body)

    monkeypatch.setattr(FileSystem, "atomic_write_bytes", failing)
    with pytest.raises(OSError):
        install(tmp_path, {"one.md": b"one", "two.md": b"two", "three.md": b"three"})
    assert not tree(tmp_path)


def test_init_requires_choices_and_writes_nothing_on_missing_config(tmp_path):
    result = CliRunner().invoke(app, ["init", "--root", str(tmp_path)])
    assert result.exit_code == 1
    assert "Initial setup requires" in result.output
    assert not tree(tmp_path)


def test_cli_init_available_hosts_and_reconfigure(tmp_path):
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "init",
            "--root",
            str(tmp_path),
            "--host",
            "codex",
            "--mode",
            "semi-auto",
            "--embeddings",
            "external",
            "--embedding-model",
            "test-embedding",
        ],
    )
    assert result.exit_code == 0, result.output
    cfg = json.loads((tmp_path / ".spado/project.json").read_text())
    assert cfg["mode"] == "semi-auto" and cfg["embeddings"]["backend"] == "external"
    before = tree(tmp_path)
    result = runner.invoke(app, ["init", "--root", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert tree(tmp_path) == before
