from cwi.claude_md.generator import (
    default_spec,
    estimate_size,
    load_template,
    render_claude_md,
    render_sections,
)
from cwi.claude_md.merger import classify_instruction, merge_claude_md, split_sections
from cwi.domain.enums import ProjectType
from cwi.domain.models import ClaudeMdSpec, DetectedCommand, ProjectProfile


def spec(**kw):
    return ClaudeMdSpec(**kw)


def test_empty_spec_renders_only_title():
    text = render_claude_md(spec())
    assert text == "# Project Instructions\n"
    assert "##" not in text


def test_no_empty_sections():
    text = render_claude_md(spec(safety=["Be careful."], stack={"Backend": []}, commands=[]))
    assert "## Safety" in text
    assert "## Stack" not in text
    assert "## Commands" not in text
    assert "## Architecture" not in text


def test_full_render_matches_expected_structure():
    s = spec(
        safety=["Never drop data."],
        dangerous_commands=["terraform destroy"],
        stack={"Backend": ["Python 3.12", "FastAPI"], "Frontend": ["TypeScript", "React"]},
        commands=[
            DetectedCommand(group="Backend", label="Test", command="uv run pytest", source="x"),
            DetectedCommand(group="Frontend", label="Run", command="npm run dev", source="x"),
        ],
        architecture_pointer="docs/architecture.md",
        additional_instructions=["Use British English in user-facing copy."],
    )
    text = render_claude_md(s)
    assert (
        text.index("## Safety")
        < text.index("## Stack")
        < text.index("## Commands")
        < text.index("## Architecture")
    )
    assert "Backend:\n- Python 3.12\n- FastAPI" in text
    assert "- Test: `uv run pytest`" in text
    assert "`terraform destroy`" in text
    assert "read `docs/architecture.md` before making structural changes" in text
    assert "## Additional Instructions\n\n- Use British English" in text


def test_single_group_renders_flat():
    sections = dict(
        render_sections(
            spec(
                version_rule=False,
                stack={"Project": ["Go"]},
                commands=[
                    DetectedCommand(
                        group="Project", label="Test", command="go test ./...", source="x"
                    )
                ],
            )
        )
    )
    assert sections["Stack"] == "- Go"
    assert sections["Commands"] == "- Test: `go test ./...`"


def test_renderer_is_pure_and_deterministic():
    s = default_spec(
        ProjectProfile(
            project_type=ProjectType.BACKEND, frameworks=["FastAPI"], languages=["Python"]
        )
    )
    assert render_claude_md(s) == render_claude_md(s)


def test_default_spec_proposes_dangerous_commands_from_stack():
    profile = ProjectProfile(frameworks=["Prisma"], infrastructure=["Terraform"])
    s = default_spec(profile)
    assert "prisma migrate reset" in s.dangerous_commands
    assert "terraform destroy" in s.dangerous_commands


def test_template_override(tmp_path):
    (tmp_path / "templates").mkdir()
    (tmp_path / "templates" / "CLAUDE.md").write_text(
        "<!-- team header -->\n# {{title}}\n\n{{sections}}\n"
    )
    text = render_claude_md(spec(safety=["x"]), load_template(tmp_path))
    assert text.startswith("<!-- team header -->")


def test_packaged_template_used_without_override(tmp_path):
    assert "{{sections}}" in load_template(tmp_path)


def test_size_report_thresholds():
    assert estimate_size("a" * 400).verdict == "compact"
    assert estimate_size("a" * 4000).verdict == "review"
    assert estimate_size("a" * 8000).verdict == "large"
    report = estimate_size("line1\nline2\n")
    assert report.lines == 2


def test_merge_keeps_existing_sections_and_appends_missing():
    existing = "# Payments\n\n## Conventions\n\n- cents\n\n## Safety\n\nCustom safety.\n"
    generated = "# Project Instructions\n\n## Safety\n\nGenerated safety.\n\n## Stack\n\n- Python\n"
    merged = merge_claude_md(existing, generated)
    assert merged.added_sections == ["Stack"]
    assert "Custom safety." in merged.content
    assert "Generated safety." not in merged.content
    assert merged.content.startswith(existing.rstrip())
    assert merged.content.endswith("## Stack\n\n- Python\n")


def test_merge_is_idempotent():
    generated = "# T\n\n## Safety\n\nX\n\n## Stack\n\n- Go\n"
    once = merge_claude_md("# Mine\n", generated).content
    twice = merge_claude_md(once, generated)
    assert not twice.changed
    assert twice.content == once


def test_split_ignores_headings_inside_code_fences():
    _, sections = split_sections("## A\n\n```md\n## not a heading\n```\n\n## B\n")
    assert [h for h, _ in sections] == ["A", "B"]


def test_classify_instruction():
    assert not classify_instruction("Use pnpm, never npm.").scoped
    long_procedure = (
        "Whenever implementing an API endpoint, follow these 28 steps: 1. ... 2. ... 3. ..."
    )
    advice = classify_instruction(long_procedure)
    assert advice.scoped and advice.destination == "Skill"
    assert classify_instruction("Every new API endpoint needs rate limiting").scoped


def test_version_rule_follows_stack():
    text = render_claude_md(spec(stack={"Frontend": ["Next.js 15.1", "React 19.0"]}))
    assert "- Next.js 15.1" in text
    assert "Write code for these versions." in text
    assert "Write code for these versions." not in render_claude_md(
        spec(safety=["x"])
    )  # no stack, no rule


def test_project_docs_section_replaces_architecture():
    text = render_claude_md(spec(docs_index=True, architecture_pointer="ARCHITECTURE.md"))
    assert "## Project docs" in text and "## Architecture\n" not in text
    assert (
        "`ARCHITECTURE.md`" in text
        and "`docs/specs/`" in text
        and "`docs/domain/glossary.md`" in text
    )
    assert "## Project docs" not in render_claude_md(spec(architecture_pointer="docs/a.md"))


def test_scaffold_files():
    from cwi.claude_md.docs import scaffold_files

    profile = ProjectProfile(stack={"Frontend": ["TypeScript 5.5", "Vite"]})
    files = scaffold_files(profile, "demo")
    assert set(files) == {
        "docs/architecture.md",
        "docs/domain/glossary.md",
        "docs/specs/README.md",
        "docs/specs/_template.md",
        "docs/decisions/README.md",
        "docs/decisions/0000-template.md",
    }
    assert "| Frontend | TypeScript | 5.5 |" in files["docs/architecture.md"]
    assert "| Frontend | Vite | <!-- set the version in use --> |" in files["docs/architecture.md"]
    assert "## Acceptance criteria" in files["docs/specs/_template.md"]
    assert "docs/architecture.md" not in scaffold_files(profile, "demo", include_architecture=False)
