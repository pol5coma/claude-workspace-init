"""After cwi init: architecture-first order of skills, step headers, progress and the hand-off."""

from cwi.install.executor import execute_plan
from cwi.ui.prompts import ScriptedPrompter
from tests.helpers import run

MARKER = "cwi:architecture-template"


def test_scaffold_marks_architecture_as_template(tmp_repo, real_catalog):
    root = tmp_repo("react-vite")
    run(root, catalog=real_catalog)
    assert (root / "docs/architecture.md").read_text().startswith(f"<!-- {MARKER}")
    assert f"still contains `{MARKER}`" in (root / "AGENTS.md").read_text()


def test_existing_architecture_has_no_template_gate(tmp_repo, real_catalog):
    root = tmp_repo("python-fastapi")  # ships docs/architecture.md written by the team
    run(root, catalog=real_catalog)
    assert MARKER not in (root / "AGENTS.md").read_text()


def test_gate_line_disappears_once_architecture_is_written(tmp_repo, real_catalog):
    root = tmp_repo("react-vite")
    run(root, catalog=real_catalog)
    arch = root / "docs/architecture.md"
    arch.write_text(
        "\n".join(arch.read_text().splitlines()[1:]) + "\n"
    )  # what project-discovery does
    run(root, catalog=real_catalog)
    assert MARKER not in (root / "AGENTS.md").read_text()


def test_step_headers_and_next_steps(tmp_repo, real_catalog):
    root = tmp_repo("react-vite")
    outcome, _, output = run(root, catalog=real_catalog)
    for n, title in enumerate(
        [
            "Workspace",
            "Scan",
            "Project profile",
            "Instructions & docs",
            "Capabilities",
            "Review plan",
            "Apply",
            "Next steps",
        ],
        start=1,
    ):
        assert f"Step {n}/8 · {title}" in output
    assert 'claude "/kickoff"' in output
    assert (
        output.index("project-discovery")
        < output.rindex("feature-spec")
        < output.rindex("feature-workflow")
    )
    assert {"skill:kickoff", "skill:project-discovery"} <= set(outcome.plan.selected_capabilities)


def test_next_step_is_feature_spec_when_architecture_exists(tmp_repo, real_catalog):
    from cwi.commands.init import next_steps

    root = tmp_repo("python-fastapi")
    outcome, _, _ = run(root, catalog=real_catalog)
    steps, command = next_steps(root, outcome.plan)
    assert [(status, skill) for status, skill, _ in steps][:2] == [
        ("done", "project-discovery"),
        ("next", "feature-spec"),
    ]
    assert command == 'claude "/kickoff"'


def test_without_kickoff_the_command_is_the_next_skill(tmp_repo, real_catalog):
    root = tmp_repo("python-fastapi")
    skills = ["skill:project-discovery", "skill:feature-spec", "skill:feature-workflow"]
    _, _, output = run(root, {"select.skill": skills}, catalog=real_catalog)
    assert 'claude "/feature-spec"' in output


class InteractivePrompter(ScriptedPrompter):
    interactive = True


def _run_interactive(root, catalog, *, which="/usr/bin/claude", yes=False, answers=None):
    import io

    from rich.console import Console

    from cwi.commands.init import InitOptions, run_init

    calls = []
    prompter = InteractivePrompter(answers or {})
    run_init(
        InitOptions(
            root=root,
            catalog=catalog,
            yes=yes,
            prompter=prompter,
            console=Console(file=io.StringIO(), width=120),
            now="2026-10-07T00:00:00Z",
            launcher=lambda exe, argv: calls.append((exe, argv)),
            which=lambda name: which,
        )
    )
    return calls, prompter


def test_offers_to_launch_claude_with_project_discovery(tmp_repo, real_catalog):
    calls, prompter = _run_interactive(tmp_repo("react-vite"), real_catalog)
    assert "launch" in prompter.asked
    assert calls == [("claude", ["claude", "/kickoff"])]


def test_launch_declined(tmp_repo, real_catalog):
    calls, _ = _run_interactive(tmp_repo("react-vite"), real_catalog, answers={"launch": False})
    assert calls == []


def test_never_launches_without_claude_or_with_yes(tmp_repo, real_catalog):
    calls, prompter = _run_interactive(tmp_repo("react-vite"), real_catalog, which=None)
    assert calls == [] and "launch" not in prompter.asked
    calls, prompter = _run_interactive(tmp_repo("monorepo"), real_catalog, yes=True)
    assert calls == [] and "launch" not in prompter.asked


def test_no_launch_when_discovery_not_installed(tmp_repo, real_catalog):
    calls, prompter = _run_interactive(
        tmp_repo("react-vite"),
        real_catalog,
        answers={"select.skill": ["skill:testing"]},
    )
    assert calls == [] and "launch" not in prompter.asked


def test_progress_callback_once_per_operation(tmp_repo, real_catalog):
    from cwi.catalog.loader import load_catalog
    from cwi.domain.enums import ClaudeMdMode
    from cwi.domain.models import ClaudeMdDecision, ProjectProfile
    from cwi.planning.planner import PlanInputs, build_plan

    root = tmp_repo("react-vite")
    catalog = load_catalog(real_catalog)
    plan = build_plan(
        PlanInputs(
            root=root,
            profile=ProjectProfile(),
            catalog=catalog,
            state=None,
            claude_md=ClaudeMdDecision(mode=ClaudeMdMode.CREATE, content="# x\n"),
            selected=["skill:testing", "hook:safety-guard"],
        )
    )
    seen = []
    execute_plan(plan, root, progress=lambda done, total, op: seen.append((done, total)))
    assert [d for d, _ in seen] == list(range(1, len(plan.operations) + 1))
    assert {t for _, t in seen} == {len(plan.operations)}
