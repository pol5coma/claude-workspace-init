import json
import tomllib
from pathlib import Path

import pytest
from typer.testing import CliRunner

from spado.adapters.capabilities import codex_server
from spado.cli import app

CATALOG = Path(__file__).resolve().parents[2] / "catalog"


def test_mcp_bearer_reference_not_interpolated():
    server = codex_server(
        {
            "type": "http",
            "url": "https://example.test/mcp",
            "headers": {"Authorization": "Bearer ${GITHUB_TOKEN}"},
        }
    )
    assert server == {"url": "https://example.test/mcp", "bearer_token_env_var": "GITHUB_TOKEN"}
    with pytest.raises(ValueError, match="interpolation"):
        codex_server({"url": "https://example.test/mcp", "headers": {"X-Key": "prefix-${TOKEN}"}})


def test_capabilities_only_merges_host_config_without_database(tmp_path):
    target = tmp_path / ".codex/config.toml"
    target.parent.mkdir()
    target.write_text('model = "existing-model"\n')
    result = CliRunner().invoke(
        app,
        [
            "init",
            "--root",
            str(tmp_path),
            "--no-workflow",
            "--host",
            "codex",
            "--catalog",
            str(CATALOG),
            "--capability",
            "mcp:github",
        ],
    )
    assert result.exit_code == 0, result.output
    configuration = tomllib.loads(target.read_text())
    assert configuration["model"] == "existing-model"
    assert configuration["mcp_servers"]["github"]["bearer_token_env_var"] == "GITHUB_TOKEN"
    assert not (tmp_path / ".spado/local/database.password").exists()
    first = target.read_bytes()
    again = CliRunner().invoke(
        app,
        [
            "init",
            "--root",
            str(tmp_path),
            "--no-workflow",
            "--host",
            "codex",
            "--catalog",
            str(CATALOG),
            "--capability",
            "mcp:github",
        ],
    )
    assert again.exit_code == 0, again.output
    assert target.read_bytes() == first


def test_claude_mcp_preserves_other_servers(tmp_path):
    target = tmp_path / ".mcp.json"
    target.write_text(json.dumps({"mcpServers": {"existing": {"command": "existing-server"}}}))
    result = CliRunner().invoke(
        app,
        [
            "init",
            "--root",
            str(tmp_path),
            "--no-workflow",
            "--host",
            "claude",
            "--capability",
            "mcp:github",
        ],
    )
    assert result.exit_code == 0, result.output
    assert set(json.loads(target.read_text())["mcpServers"]) == {"existing", "github"}


def test_unsupported_host_does_not_install_partial_configuration(tmp_path):
    result = CliRunner().invoke(
        app,
        [
            "init",
            "--root",
            str(tmp_path),
            "--no-workflow",
            "--host",
            "codex",
            "--capability",
            "hook:safety-guard",
        ],
    )
    assert result.exit_code == 1
    assert not list(tmp_path.iterdir())
