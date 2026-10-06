import json
import os
import shutil
import subprocess
import sys

import pytest

from tests.helpers import REAL_CATALOG

HOOK = (
    REAL_CATALOG
    / "hooks"
    / "post-edit-validation"
    / "payload"
    / ".claude"
    / "hooks"
    / "post-edit-validation.py"
)


def run_hook(project, file_path, path_env="/usr/bin:/bin"):
    payload = {
        "tool_name": "Edit",
        "tool_input": {"file_path": str(file_path)},
        "cwd": str(project),
    }
    env = {"CLAUDE_PROJECT_DIR": str(project), "PATH": path_env}
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )


def test_skips_when_no_tool_configured(tmp_path):
    f = tmp_path / "app.py"
    f.write_text("x=1\n")
    result = run_hook(tmp_path, f)
    assert result.returncode == 0
    assert f.read_text() == "x=1\n"  # untouched: no configured formatter


def test_skips_outside_project(tmp_path):
    project = tmp_path / "p"
    project.mkdir()
    other = tmp_path / "other.py"
    other.write_text("x")
    assert run_hook(project, other).returncode == 0


def test_skips_missing_file_and_bad_input(tmp_path):
    assert run_hook(tmp_path, tmp_path / "missing.py").returncode == 0
    result = subprocess.run(
        [sys.executable, str(HOOK)], input="nope", capture_output=True, text=True
    )
    assert result.returncode == 0


ruff = shutil.which("ruff") or (
    os.path.join(os.path.dirname(sys.executable), "ruff")
    if os.path.exists(os.path.join(os.path.dirname(sys.executable), "ruff"))
    else None
)


@pytest.mark.skipif(ruff is None, reason="ruff not installed")
def test_ruff_formats_and_reports(tmp_path):
    (tmp_path / "pyproject.toml").write_text('[project]\nname="x"\n[tool.ruff]\nline-length=100\n')
    f = tmp_path / "app.py"
    f.write_text("import os\nx=1\n")
    result = run_hook(tmp_path, f, path_env=os.path.dirname(ruff) + ":/usr/bin:/bin")
    assert f.read_text() == "x = 1\n"  # formatted, unused import auto-fixed
    assert result.returncode == 0

    f.write_text("def f():\n    return undefined_name\n")
    result = run_hook(tmp_path, f, path_env=os.path.dirname(ruff) + ":/usr/bin:/bin")
    assert result.returncode == 2
    assert "undefined_name" in result.stderr
