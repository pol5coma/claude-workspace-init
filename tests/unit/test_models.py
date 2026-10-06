from cwi.domain.enums import CapabilityType, ClaudeMdMode, OperationType, ProjectType
from cwi.domain.models import (
    CapabilityManifest,
    CWIState,
    DetectedCommand,
    InstallationPlan,
    ManagedFile,
    PlannedOperation,
    ProjectProfile,
    normalize_tech,
)


def test_manifest_ref_and_validation():
    m = CapabilityManifest(
        schema_version=1, id="testing", type="skill", name="Testing", description="d"
    )
    assert m.ref == "skill:testing"
    assert m.type is CapabilityType.SKILL


def test_manifest_rejects_bad_id():
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        CapabilityManifest(schema_version=1, id="../evil", type="skill", name="x", description="d")


def test_manifest_rejects_unknown_fields():
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        CapabilityManifest(
            schema_version=1, id="x", type="skill", name="x", description="d", surprise=True
        )


def test_normalize_tech_strips_versions():
    assert normalize_tech("Python 3.12") == "python"
    assert normalize_tech("Next.js") == "next.js"
    assert normalize_tech("GitHub Actions") == "github actions"


def test_profile_technologies_and_summary():
    p = ProjectProfile(
        project_type=ProjectType.FULLSTACK,
        languages=["Python 3.12", "TypeScript"],
        frameworks=["FastAPI", "React"],
        databases=["PostgreSQL"],
    )
    assert {"python", "typescript", "fastapi", "react", "postgresql"} <= p.technologies()
    assert p.summary().startswith("Full-stack application · FastAPI + React")


def test_state_roundtrip():
    state = CWIState(
        cwi_version="0.1.0",
        initialized_at="2026-10-06T12:00:00Z",
        profile=ProjectProfile(
            commands=[DetectedCommand(group="Project", label="Test", command="pytest", source="x")]
        ),
        claude_md_mode=ClaudeMdMode.CREATE,
        selected_capabilities=["skill:testing"],
        managed_files={"CLAUDE.md": ManagedFile(owner="claude-md", sha256="abc")},
    )
    again = CWIState.model_validate_json(state.model_dump_json())
    assert again == state


def test_plan_counts():
    ops = [
        PlannedOperation(type=OperationType.MKDIR, target=".claude", owner="cwi", reason=""),
        PlannedOperation(type=OperationType.COPY, target="a", source="/x", owner="o", reason=""),
        PlannedOperation(
            type=OperationType.MERGE_JSON,
            target="b",
            before_hash="h",
            after_content="{}",
            owner="o",
            reason="",
        ),
        PlannedOperation(
            type=OperationType.DELETE_DIR, target="catalog", owner="cwi-template", reason=""
        ),
    ]
    plan = InstallationPlan(
        profile=ProjectProfile(),
        operations=ops,
        state=CWIState(cwi_version="0.1.0", initialized_at="x"),
    )
    assert plan.counts() == {"create": 1, "update": 1, "delete": 1}
