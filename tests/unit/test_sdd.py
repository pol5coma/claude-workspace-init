import json
import subprocess
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from spado.cli import app
from spado.runtime.config import dump
from spado.sdd import engine
from spado.sdd.hooks import inspect_event
from spado.sdd.install import setup
from spado.sdd.models import Feature, Milestone, Report, Review, Settings, State
from spado.sdd.store import git, read, snapshot, transaction

CATALOG = Path(__file__).resolve().parents[2] / "catalog"


def put(root, name, body):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body)


@pytest.fixture
def repo(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    git(tmp_path, "config", "user.email", "test@example.com")
    git(tmp_path, "config", "user.name", "Test")
    put(tmp_path, ".workflow/state.json", dump(State().model_dump()))
    put(tmp_path, ".workflow/config.json", dump(Settings(hosts=["codex"]).model_dump()))
    put(tmp_path, ".workflow/.gitignore", "state.json\n*.lock\nresults/\n")
    put(tmp_path, "README.md", "Example project\n")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-qm", "initial")
    return tmp_path


def report(root, role=None, **kwargs):
    reviews = [
        Review(
            role=r,
            worker=f"reviewer-{r}",
            snapshot=snapshot(root),
            decision="approve",
            evidence=["verified source contract"],
        )
        for r in ([role] if isinstance(role, str) else role or [])
    ]
    return Report(author="author", summary="Feature work", reviews=reviews, **kwargs)


def to_red(root, mode="manual", milestones=2):
    engine.start(root, "accounts", mode)
    engine.begin(root, "spec")
    put(root, "docs/features/accounts/FEATURE.md", "# Accounts\nAC-1 AC-2")
    put(root, "FEATURE-MAP.md", "accounts")
    engine.submit(
        root, report(root, "architecture", criteria=[f"AC-{i}" for i in range(1, milestones + 1)])
    )
    engine.approve(root, "approve spec")
    engine.begin(root, "roadmap")
    put(root, "docs/features/accounts/ROADMAP.md", "# Milestones")
    engine.submit(
        root,
        report(
            root,
            "plan",
            milestones=[
                Milestone(id=i, title=f"M{i}", criteria=[f"AC-{i}"])
                for i in range(1, milestones + 1)
            ],
        ),
    )
    engine.approve(root, "approve roadmap")
    # A real subprocess checks behavior and produces JUnit. No host/model calls are made.
    script = (
        "import sys,pathlib,xml.etree.ElementTree as E; "
        "m,kind,out=sys.argv[1:]; p=pathlib.Path('module'+m+'.py'); "
        "ok=p.exists() and p.read_text()=='correct'; "
        "suite=E.Element('testsuite'); case=E.SubElement(suite,'testcase',classname='m'+m,name=kind); "
        "E.SubElement(case,'failure',message='behavior missing') if not ok else None; "
        "pathlib.Path(out).write_bytes(E.tostring(suite)); sys.exit(0 if ok else 1)"
    )
    checks = [
        {
            "id": "baseline",
            "kind": "baseline",
            "argv": [
                sys.executable,
                "-c",
                "from pathlib import Path; assert 'Example project' in Path('README.md').read_text()",
            ],
        }
    ]
    for m in range(1, milestones + 1):
        for kind in ["unit", "integration", "acceptance", "e2e"]:
            out = f".workflow/results/{m}-{kind}.xml"
            checks.append(
                {
                    "id": f"m{m}-{kind}",
                    "kind": kind,
                    "argv": [sys.executable, "-c", script, str(m), kind, out],
                    "milestones": [m],
                    "criteria": [f"AC-{m}"],
                    "junit": out,
                    "red_failures": [f"m{m}.{kind}"],
                    "red_reasons": {f"m{m}.{kind}": "behavior missing"},
                }
            )
    put(
        root,
        "docs/features/accounts/CHECKS.json",
        json.dumps({"protected": ["tests/*"], "checks": checks}),
    )
    return root


def to_build(root, mode="manual", milestones=2):
    to_red(root, mode, milestones)
    assert engine.check(root, baseline=True)["passed"]
    engine.begin(root, "red")
    put(root, "tests/accounts.py", "# accepted test definition")
    assert engine.check(root)["passed"]
    engine.submit(root, report(root, "asserts" if mode == "supervised" else None))
    engine.approve(root, "assertions validated")
    return root


def test_install_inventory_idempotency_and_live_state(tmp_path):
    result = setup(tmp_path, CATALOG, ["claude", "codex"], dry_run=True)
    assert not list(tmp_path.iterdir())
    assert all(x["action"] == "created" for x in result["inventory"])
    result = setup(tmp_path, CATALOG, ["claude", "codex"])
    assert not (tmp_path / ".spado/project.json").exists()
    assert not (tmp_path / ".spado/local/compose.yaml").exists()
    assert (tmp_path / ".codex/hooks.json").exists()
    assert (tmp_path / ".claude/skills/feature-tdd-build/SKILL.md").exists()
    with transaction(tmp_path) as state:
        state.events.append({"kind": "keep-me"})
    before = (tmp_path / ".workflow/state.json").read_bytes()
    again = setup(tmp_path, CATALOG, None)
    assert (tmp_path / ".workflow/state.json").read_bytes() == before
    assert read(tmp_path).events[-1]["kind"] == "keep-me"
    assert not any(x["action"] == "updated" for x in again["inventory"])


def test_init_sdd_cli_no_database(tmp_path):
    result = CliRunner().invoke(app, ["init", "--sdd", "--host", "codex", "--root", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["inventory"]
    assert not (tmp_path / ".spado/project.json").exists()


def test_manual_complete_flow_with_future_red_and_e2e(repo):
    to_build(repo)
    for milestone in [1, 2]:
        engine.begin(repo, "build", milestone)
        put(repo, f"module{milestone}.py", "correct")
        ev = engine.check(repo)
        assert ev["passed"]
        assert {r["kind"] for r in ev["results"]} == {
            "baseline",
            "unit",
            "integration",
            "acceptance",
            "e2e",
        }
        if milestone == 1:
            assert not any(r["id"].startswith("m2") for r in ev["results"])
        engine.submit(repo, report(repo))
        assert read(repo).active.status == "awaiting_review"
        with pytest.raises(ValueError):
            engine.begin(repo, "build", milestone + 1)
        engine.approve(repo, "approved milestone")
    assert len(read(repo).active.commits) == 2
    engine.begin(repo, "close")
    put(repo, "AGENTS.md", "Project guidance")
    assert engine.check(repo)["passed"]
    engine.submit(repo, report(repo, ["code", "security"]))
    engine.approve(repo, "accepted")
    assert read(repo).active.status == "complete"
    assert not git(repo, "status", "--porcelain")


def test_no_skip_and_stale_approval(repo):
    engine.start(repo, "accounts")
    with pytest.raises(ValueError, match="next permitted"):
        engine.begin(repo, "build", 1)
    engine.begin(repo, "spec")
    put(repo, "docs/features/accounts/FEATURE.md", "feature")
    put(repo, "FEATURE-MAP.md", "accounts")
    engine.submit(repo, report(repo, "architecture", criteria=["AC-1"]))
    put(repo, "docs/features/accounts/FEATURE.md", "changed contract")
    with pytest.raises(ValueError, match="changed"):
        engine.approve(repo, "approve")


def test_architecture_must_be_independent(repo):
    engine.start(repo, "accounts")
    engine.begin(repo, "spec")
    put(repo, "docs/features/accounts/FEATURE.md", "feature")
    put(repo, "FEATURE-MAP.md", "accounts")
    data = report(repo, "architecture", criteria=["AC-1"])
    data.reviews[0].worker = data.author
    with pytest.raises(ValueError, match="independent"):
        engine.submit(repo, data)


@pytest.mark.parametrize("tamper", ["edit", "add", "delete", "rename"])
def test_frozen_tests_block_acceptance(repo, tamper):
    to_build(repo, milestones=1)
    engine.begin(repo, "build", 1)
    test = repo / "tests/accounts.py"
    if tamper == "edit":
        test.write_text("weakened")
    elif tamper == "add":
        put(repo, "tests/new.py", "new")
    elif tamper == "delete":
        test.unlink()
    else:
        test.rename(test.with_name("renamed.py"))
    with pytest.raises(ValueError, match="Protected"):
        engine.check(repo)


def test_check_configuration_tamper_and_reopen(repo):
    to_build(repo, milestones=1)
    path = repo / "docs/features/accounts/CHECKS.json"
    cfg = json.loads(path.read_text())
    cfg["protected"] = ["nothing/*"]
    path.write_text(json.dumps(cfg))
    with pytest.raises(ValueError):
        engine.begin(repo, "build", 1)
    engine.reopen(repo, "red", "Human requested corrected fixture")
    assert not read(repo).active.frozen
    assert "red" not in read(repo).active.approvals


def test_e2e_failure_blocks_even_when_other_checks_pass(repo):
    to_red(repo, milestones=1)
    path = repo / "docs/features/accounts/CHECKS.json"
    cfg = json.loads(path.read_text())
    cfg["checks"][-1]["argv"] = [sys.executable, "-c", "raise SystemExit(2)"]
    path.write_text(json.dumps(cfg))
    assert engine.check(repo, baseline=True)["passed"]
    engine.begin(repo, "red")
    ev = engine.check(repo)
    assert not ev["passed"]
    assert ev["results"][-1]["error"] == "Missing or invalid JUnit evidence"


def test_red_failure_must_match_approved_reason(repo):
    to_red(repo, milestones=1)
    path = repo / "docs/features/accounts/CHECKS.json"
    cfg = json.loads(path.read_text())
    cfg["checks"][-1]["red_reasons"] = {"m1.e2e": "different failure"}
    path.write_text(json.dumps(cfg))
    assert engine.check(repo, baseline=True)["passed"]
    engine.begin(repo, "red")
    ev = engine.check(repo)
    assert not ev["passed"]
    assert not ev["results"][-1]["passed"]


def test_pause_and_stop_do_not_trap_human(repo):
    to_build(repo, milestones=1)
    engine.begin(repo, "build", 1)
    assert inspect_event(repo, {"hook_event_name": "Stop"}) == {}
    engine.pause(repo, "question")
    assert inspect_event(repo, {"hook_event_name": "Stop"}) == {}
    assert (
        inspect_event(
            repo,
            {
                "hook_event_name": "PreToolUse",
                "tool_name": "Bash",
                "tool_input": {"command": "python -m spado sdd status"},
            },
        )
        == {}
    )
    engine.begin(repo, "build", 1)
    with pytest.raises(ValueError, match="frozen"):
        inspect_event(
            repo,
            {
                "hook_event_name": "PreToolUse",
                "tool_name": "Edit",
                "tool_input": {"file_path": "tests/accounts.py", "new_string": "bad"},
            },
        )


def test_product_dependencies_sources_and_completion_preserved(repo):
    put(repo, "requirements.md", "accounts then projects")
    features = [
        Feature(id="F1", slug="accounts", title="Accounts", rationale="identity"),
        Feature(
            id="F2",
            slug="projects",
            title="Projects",
            depends_on=["F1"],
            rationale="needs identity",
        ),
    ]
    engine.product_submit(repo, features, ["requirements.md"])
    engine.product_approve(repo, "approve product")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "product")
    with pytest.raises(ValueError, match="dependencies"):
        engine.start(repo, "projects", feature_id="F2")
    put(repo, "requirements.md", "changed requirements")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "changed source")
    with pytest.raises(ValueError, match="requirements changed"):
        engine.start(repo, "accounts", feature_id="F1")


def test_readme_assumptions_do_not_invalidate_product_source(repo):
    engine.product_submit(
        repo,
        [Feature(id="F1", slug="accounts", title="Accounts", rationale="identity")],
        ["README.md"],
    )
    engine.product_approve(repo, "approve product")
    put(repo, "README.md", "Example project\n\n## Assumptions\n\n### Accounts\nToken expires.\n")
    engine.product_valid(repo, read(repo))
    put(
        repo,
        "README.md",
        "Different requirements\n\n## Assumptions\n\n### Accounts\nToken expires.\n",
    )
    with pytest.raises(ValueError, match="requirements changed"):
        engine.product_valid(repo, read(repo))


def test_product_revision_reopens_active_feature(repo):
    put(repo, "requirements.md", "accounts")
    features = [Feature(id="F1", slug="accounts", title="Accounts", rationale="identity")]
    engine.product_submit(repo, features, ["requirements.md"])
    engine.product_approve(repo, "approved")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "product")
    engine.start(repo, "accounts", feature_id="F1")
    engine.begin(repo, "spec")
    put(repo, "docs/features/accounts/FEATURE.md", "feature")
    put(repo, "FEATURE-MAP.md", "accounts")
    engine.submit(repo, report(repo, "architecture", criteria=["AC-1"]))
    engine.approve(repo, "approved spec")
    put(repo, "requirements.md", "accounts with roles")
    engine.product_submit(repo, features, ["requirements.md"])
    state = read(repo)
    assert state.active.phase == "spec"
    assert not state.active.approvals
    assert not state.product["approved"]
    engine.product_approve(repo, "approve revision")
    engine.product_valid(repo, read(repo))


def test_latest_failed_check_prevents_approval(repo):
    to_build(repo, milestones=1)
    engine.begin(repo, "build", 1)
    put(repo, "module1.py", "correct")
    assert engine.check(repo)["passed"]
    engine.submit(repo, report(repo))
    cfg_path = repo / "docs/features/accounts/CHECKS.json"
    cfg = json.loads(cfg_path.read_text())
    # Simulate a transient test infrastructure outage without changing repository files.
    cfg["checks"][-1]["argv"] = [sys.executable, "-c", "raise SystemExit(2)"]
    cfg_path.write_text(json.dumps(cfg))
    # A frozen config itself is a stronger failure than a flaky run.
    with pytest.raises(ValueError):
        engine.approve(repo, "approve")


def test_latest_transient_failure_prevents_approval(repo, monkeypatch):
    to_build(repo, milestones=1)
    engine.begin(repo, "build", 1)
    put(repo, "module1.py", "correct")
    assert engine.check(repo)["passed"]
    engine.submit(repo, report(repo))
    from spado.sdd import engine as sdd_engine

    def failing_check(root, run, check, red=False):
        return {"id": check.id, "kind": check.kind, "passed": False, "error": "service outage"}

    monkeypatch.setattr(sdd_engine, "execute_check", failing_check)
    assert not engine.check(repo)["passed"]
    with pytest.raises(ValueError, match="latest verification failed"):
        engine.approve(repo, "approved")


def test_paused_milestone_keeps_original_diff_and_commits(repo):
    to_build(repo, milestones=2)
    engine.begin(repo, "build", 1)
    put(repo, "module1.py", "correct")
    engine.check(repo)
    engine.submit(repo, report(repo))
    engine.approve(repo, "milestone one")
    engine.begin(repo, "build", 2)
    put(repo, "module2.py", "correct")
    original = read(repo).active.phase_snapshot
    engine.pause(repo, "inspect interface")
    engine.begin(repo, "build", 2)
    assert read(repo).active.phase_snapshot == original
    engine.check(repo)
    engine.submit(repo, report(repo))
    engine.approve(repo, "milestone two")
    assert "module2.py" in git(repo, "show", "--pretty=", "--name-only", "HEAD")


def test_corrupt_state_not_reinitialized(tmp_path):
    setup(tmp_path, CATALOG, ["codex"])
    path = tmp_path / ".workflow/state.json"
    path.write_text("broken")
    with pytest.raises(ValueError):
        setup(tmp_path, CATALOG, ["codex"])
    assert path.read_text() == "broken"


def test_supervised_final_acceptance_cannot_be_delegated(repo):
    to_build(repo, mode="supervised", milestones=1)
    engine.begin(repo, "build", 1)
    put(repo, "module1.py", "correct")
    engine.check(repo)
    engine.submit(repo, report(repo))
    engine.approve(repo, "checks passed", delegated=True)
    assert read(repo).active.approvals["build:1"]["by"] == "delegated"
    engine.begin(repo, "close")
    put(repo, "AGENTS.md", "guidance")
    engine.check(repo)
    engine.submit(repo, report(repo, ["code", "security"]))
    with pytest.raises(ValueError, match="Human"):
        engine.approve(repo, "automatic", delegated=True)


def test_review_snapshot_invalid_after_code_changes(repo):
    to_build(repo, milestones=1)
    engine.begin(repo, "build", 1)
    put(repo, "module1.py", "correct")
    engine.check(repo)
    put(repo, "module1.py", "incorrect")
    with pytest.raises(ValueError, match="checks"):
        engine.submit(repo, report(repo))


def test_design_shell_bypass_rejected_at_submission(repo):
    engine.start(repo, "accounts")
    engine.begin(repo, "spec")
    put(repo, "docs/features/accounts/FEATURE.md", "feature")
    put(repo, "FEATURE-MAP.md", "accounts")
    put(repo, "production.py", "unapproved code")
    with pytest.raises(ValueError, match="implementation"):
        engine.submit(repo, report(repo, "architecture", criteria=["AC-1"]))


def test_supervised_runner_stops_for_human_after_full_e2e(repo, monkeypatch):
    to_build(repo, mode="supervised", milestones=1)
    from spado.sdd import runner

    calls = []

    def fake_launch(root, host, role, instruction, settings, deadline, readonly=False):
        calls.append((role, read(root).active.phase))
        phase = read(root).active.phase
        if readonly:
            return Review(
                role=role,
                worker=f"independent-{role}",
                snapshot=snapshot(root),
                decision="approve",
                evidence=["checked cumulative change and acceptance evidence"],
            )
        if phase == "build":
            put(root, "module1.py", "correct")
        elif phase == "close":
            put(root, "AGENTS.md", "Project guidance")
        return Report(author=f"author-{phase}", summary=f"Completed {phase}")

    monkeypatch.setattr(runner, "launch", fake_launch)
    result = runner.run_feature(repo, "codex")
    assert result["status"] == "awaiting_review"
    assert read(repo).active.phase == "close"
    assert read(repo).active.approvals["build:1"]["by"] == "delegated"
    assert "close" not in read(repo).active.approvals
    assert ("code", "close") in calls and ("security", "close") in calls
    assert all(r["passed"] for r in read(repo).active.evidence["close:1"]["results"])


def test_interrupted_commit_is_recoverable_without_duplicate(repo, monkeypatch):
    to_build(repo, milestones=1)
    engine.begin(repo, "build", 1)
    put(repo, "module1.py", "correct")
    engine.check(repo)
    engine.submit(repo, report(repo))
    actual_git = engine.git

    def interrupted(root, *args):
        if args and args[0] == "commit":
            raise OSError("interrupted before commit")
        return actual_git(root, *args)

    monkeypatch.setattr(engine, "git", interrupted)
    with pytest.raises(OSError, match="interrupted"):
        engine.approve(repo, "approved")
    assert read(repo).active.pending_commit
    monkeypatch.setattr(engine, "git", actual_git)
    assert engine.recover(repo)["recovered"]
    engine.approve(repo, "approved")
    assert git(repo, "log", "--format=%s").splitlines()[0] == "feat(accounts): build:1"
    assert read(repo).active.pending_commit is None


def test_state_lock_rejects_concurrent_transition(repo):
    from spado.sdd.store import lock

    with lock(repo), pytest.raises(ValueError, match="busy"):
        engine.start(repo, "accounts")
    engine.start(repo, "accounts")


def test_supervised_roadmap_selects_ready_feature_only(repo, monkeypatch):
    put(repo, "requirements.md", "accounts then projects")
    features = [
        Feature(id="F1", slug="accounts", title="Accounts", rationale="identity"),
        Feature(id="F2", slug="projects", title="Projects", depends_on=["F1"], rationale="work"),
    ]
    engine.product_submit(repo, features, ["requirements.md"])
    engine.product_approve(repo, "approved")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "product")
    from spado.sdd import runner

    monkeypatch.setattr(runner, "run_feature", lambda root, host: {"status": "waiting"})
    result = CliRunner().invoke(
        app, ["sdd", "run", "--roadmap", "--host", "codex", "--root", str(repo)]
    )
    assert result.exit_code == 0, result.output
    assert read(repo).active.feature_id == "F1"
    assert read(repo).active.mode == "supervised"
