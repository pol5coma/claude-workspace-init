from pathlib import Path

from cwi.domain.enums import ProjectType
from cwi.profile import profile_from_scan, uncertain_detections
from cwi.scanner.scanner import scan_project
from tests.helpers import PROJECT_ROOT


def values(detections):
    return {d.value for d in detections}


def test_empty_repo_is_new_project(tmp_repo):
    scan = scan_project(tmp_repo("empty"))
    assert scan.meaningful_project is False
    assert scan.project_type == ProjectType.OTHER


def test_python_fastapi_detection(tmp_repo):
    root = tmp_repo("python-fastapi")
    scan = scan_project(root)
    assert scan.meaningful_project
    assert scan.project_type == ProjectType.BACKEND
    assert "Python 3.12" in values(scan.languages)
    assert {"FastAPI", "SQLAlchemy", "Alembic"} <= values(scan.frameworks)
    assert "PostgreSQL" in values(scan.databases)
    assert "uv" in values(scan.package_managers)
    assert "pytest" in values(scan.test_tools)
    assert "Ruff" in values(scan.tools)
    assert {"Docker", "GitHub Actions"} <= values(scan.infrastructure)
    assert scan.architecture_docs == ["docs/architecture.md"]
    commands = {(c.label, c.command, c.detected) for c in scan.commands}
    assert ("Test", "uv run pytest", True) in commands
    assert ("Lint", "uv run ruff check .", True) in commands
    assert (
        "Run",
        "uv run fastapi dev app/main.py",
        False,
    ) in commands  # convention: suggested only
    assert scan.stack["Backend"][:2] == [
        "Python 3.12",
        "FastAPI 0.115",
    ]  # exact version from uv.lock


def test_env_example_values_never_leak(tmp_repo):
    root = tmp_repo("python-fastapi")
    scan = scan_project(root)
    dumped = scan.model_dump_json()
    assert "password" not in dumped
    assert "change-me" not in dumped


def test_react_vite_detection(tmp_repo):
    scan = scan_project(tmp_repo("react-vite"))
    assert scan.project_type == ProjectType.FRONTEND
    assert "TypeScript" in values(scan.languages)
    assert {"React", "Vite"} <= values(scan.frameworks)
    assert "Vitest" in values(scan.test_tools)
    assert "ESLint" in values(scan.tools)
    assert "npm" in values(scan.package_managers)
    commands = {(c.label, c.command) for c in scan.commands}
    assert {
        ("Run", "npm run dev"),
        ("Test", "npm test"),
        ("Lint", "npm run lint"),
        ("Build", "npm run build"),
    } <= commands
    assert all(c.detected for c in scan.commands)


def test_fullstack_detection(tmp_repo):
    scan = scan_project(tmp_repo("fullstack"))
    assert scan.project_type == ProjectType.FULLSTACK
    assert scan.backend and scan.frontend
    assert {"FastAPI", "React"} <= values(scan.frameworks)
    assert {"PostgreSQL", "Redis"} <= values(scan.databases)
    assert set(scan.stack) >= {"Backend", "Frontend", "Infrastructure"}
    groups = {c.group for c in scan.commands}
    assert {"Backend", "Frontend"} <= groups
    frontend_run = next(c for c in scan.commands if c.group == "Frontend" and c.label == "Run")
    assert frontend_run.command == "cd frontend && npm run dev"


def test_monorepo_detection(tmp_repo):
    scan = scan_project(tmp_repo("monorepo"))
    assert scan.monorepo
    assert scan.project_type == ProjectType.FULLSTACK
    assert {"apps/api", "apps/web", "packages/shared"} <= set(scan.subprojects)
    assert {"Express", "Next.js"} <= values(scan.frameworks)
    assert "pnpm" in values(scan.package_managers)


def test_cli_detection(tmp_repo):
    scan = scan_project(tmp_repo("existing-mcp"))
    assert scan.project_type == ProjectType.CLI
    assert scan.existing_claude.mcp


def test_existing_claude_config_detected(tmp_repo):
    scan = scan_project(tmp_repo("existing-claude-config"))
    ec = scan.existing_claude
    assert ec.claude_md and ec.settings
    assert ec.agents == ["my-custom-agent"]


def test_cwi_template_itself_is_not_an_application():
    scan = scan_project(PROJECT_ROOT)
    assert scan.meaningful_project is False, scan.signals


def test_scanner_skips_ignored_dirs(tmp_path):
    (tmp_path / "node_modules" / "react").mkdir(parents=True)
    (tmp_path / "node_modules" / "react" / "package.json").write_text(
        '{"dependencies": {"next": "1"}}'
    )
    scan = scan_project(tmp_path)
    assert not scan.meaningful_project
    assert scan.frameworks == []


def test_scanner_does_not_follow_symlinked_manifests(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "package.json").write_text('{"dependencies": {"react": "1"}}')
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "package.json").symlink_to(outside / "package.json")
    scan = scan_project(repo)
    assert "React" not in values(scan.frameworks)


def test_low_confidence_signals_need_confirmation(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname="x"\ndependencies=["boto3", "flask"]\n'
    )
    scan = scan_project(tmp_path)
    uncertain = uncertain_detections(scan)
    assert ("infrastructure", "AWS") in {(c, v) for c, v, _ in uncertain}
    assert "AWS" not in profile_from_scan(scan).infrastructure
    assert "AWS" in profile_from_scan(scan, ["infrastructure:AWS"]).infrastructure


def test_scan_does_not_execute_code(tmp_path):
    marker = tmp_path / "executed"
    (tmp_path / "setup.py").write_text(f"open({str(marker)!r}, 'w').write('x')\n")
    (tmp_path / "package.json").write_text('{"scripts": {"preinstall": "touch executed"}}')
    scan_project(tmp_path)
    assert not marker.exists()
    assert not (Path(tmp_path) / "executed").exists()


def test_version_resolution(tmp_path):
    from cwi.scanner.versions import js_spec_version, py_spec_version, short

    assert short("15.1.3") == "15.1" and short("19") == "19" and short(None) is None
    assert js_spec_version("^15.1.0") == "15.1" and js_spec_version("~5.4.2") == "5.4"
    assert js_spec_version("latest") is None and js_spec_version(">=1 <2") is None
    assert (
        py_spec_version("fastapi==0.115.6") == "0.115" and py_spec_version("django~=5.1") == "5.1"
    )
    assert py_spec_version("fastapi>=0.115") is None  # a lower bound is not the version in use


def test_package_lock_beats_manifest_range(tmp_path):
    (tmp_path / "package.json").write_text(
        '{"dependencies": {"next": "^14.0.0", "react": "^18.2.0"}}'
    )
    (tmp_path / "package-lock.json").write_text(
        '{"lockfileVersion": 3, "packages": {"node_modules/next": {"version": "14.2.15"}}}'
    )
    stack = scan_project(tmp_path).stack["Frontend"]
    assert "Next.js 14.2" in stack and "React 18.2" in stack


def test_pnpm_and_yarn_locks(tmp_path):
    a = tmp_path / "a"
    a.mkdir()
    (a / "package.json").write_text('{"dependencies": {"vue": "*"}}')
    (a / "pnpm-lock.yaml").write_text("packages:\n  vue@3.5.12:\n    resolution: {}\n")
    assert "Vue 3.5" in scan_project(a).stack["Frontend"]
    b = tmp_path / "b"
    b.mkdir()
    (b / "package.json").write_text('{"dependencies": {"svelte": "*"}}')
    (b / "yarn.lock").write_text('"svelte@*":\n  version "5.1.9"\n')
    assert "Svelte 5.1" in scan_project(b).stack["Frontend"]
