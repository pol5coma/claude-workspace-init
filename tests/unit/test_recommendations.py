import pytest

from cwi.catalog.dependency_resolver import find_conflicts, resolve
from cwi.catalog.loader import load_catalog
from cwi.catalog.recommender import recommend
from cwi.domain.enums import ProjectType
from cwi.domain.errors import CatalogError
from cwi.domain.models import ProjectProfile
from tests.helpers import REAL_CATALOG, add_capability, minimal_catalog, skill_md


@pytest.fixture(scope="module")
def catalog():
    return load_catalog(REAL_CATALOG)


def fastapi_profile():
    return ProjectProfile(
        project_type=ProjectType.BACKEND,
        backend=True,
        languages=["Python 3.12"],
        frameworks=["FastAPI", "SQLAlchemy"],
        databases=["PostgreSQL"],
        test_tools=["pytest"],
        tools=["Ruff"],
        infrastructure=["Docker", "GitHub Actions"],
    )


def preselected(recs):
    return {ref for ref, rec in recs.items() if rec.preselected}


def test_fastapi_project_recommendations(catalog):
    recs = recommend(catalog, fastapi_profile())
    chosen = preselected(recs)
    assert {
        "skill:testing",
        "skill:debugging",
        "skill:backend-development",
        "agent:code-reviewer",
        "agent:security-reviewer",
        "hook:safety-guard",
        "hook:post-edit-validation",
        "mcp:github",
    } <= chosen
    assert "skill:frontend-development" not in chosen
    assert "pytest detected" in recs["skill:testing"].reason_text
    assert recs["hook:safety-guard"].reasons[0] == "Recommended default"


def test_recommendations_are_deterministic(catalog):
    a = recommend(catalog, fastapi_profile())
    b = recommend(catalog, fastapi_profile())
    assert a == b


def test_unknown_project_gets_only_defaults(catalog):
    recs = recommend(catalog, ProjectProfile())
    assert preselected(recs) == {"hook:safety-guard", "hook:post-edit-validation"}


def test_github_requires_evidence(catalog):
    profile = fastapi_profile()
    profile.infrastructure = ["Docker"]
    assert not recommend(catalog, profile)["mcp:github"].preselected


def test_dependency_resolution(tmp_path):
    catalog = load_catalog(minimal_catalog(tmp_path))
    resolution = resolve(["agent:beta"], catalog)
    assert resolution.final == ["agent:beta", "script:gamma"]
    assert resolution.added == {"script:gamma": "agent:beta"}


def test_real_code_reviewer_pulls_quality_script(catalog):
    assert resolve(["agent:code-reviewer"], catalog).added == {
        "script:run-quality-checks": "agent:code-reviewer"
    }


def test_conflicts_are_symmetric(tmp_path):
    root = tmp_path / "catalog"
    add_capability(
        root, "skill", "a", {".claude/skills/a/SKILL.md": skill_md("a")}, conflicts=["skill:b"]
    )
    add_capability(root, "skill", "b", {".claude/skills/b/SKILL.md": skill_md("b")})
    catalog = load_catalog(root)
    conflicts = find_conflicts(["skill:b", "skill:a"], catalog)
    assert [(c.a, c.b) for c in conflicts] == [("skill:a", "skill:b")]
    assert find_conflicts(["skill:a"], catalog) == []


def test_resolve_unknown_ref_fails(tmp_path):
    catalog = load_catalog(minimal_catalog(tmp_path))
    with pytest.raises(CatalogError):
        resolve(["skill:nope"], catalog)
