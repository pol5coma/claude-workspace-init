"""Python ecosystem detection (pyproject.toml via tomllib, requirements files, lockfiles)."""

from __future__ import annotations

import re
from typing import Any

from cwi import paths
from cwi.domain.enums import Confidence
from cwi.scanner.context import ScanContext, join

# dependency name -> (category, display name)
PY_PACKAGES: dict[str, tuple[str, str]] = {
    "fastapi": ("frameworks", "FastAPI"),
    "django": ("frameworks", "Django"),
    "djangorestframework": ("frameworks", "Django REST Framework"),
    "flask": ("frameworks", "Flask"),
    "starlette": ("frameworks", "Starlette"),
    "litestar": ("frameworks", "Litestar"),
    "sqlalchemy": ("frameworks", "SQLAlchemy"),
    "sqlmodel": ("frameworks", "SQLModel"),
    "alembic": ("frameworks", "Alembic"),
    "pydantic": ("frameworks", "Pydantic"),
    "celery": ("frameworks", "Celery"),
    "tortoise-orm": ("frameworks", "Tortoise ORM"),
    "streamlit": ("frameworks", "Streamlit"),
    "typer": ("frameworks", "Typer"),
    "click": ("frameworks", "Click"),
    "anthropic": ("frameworks", "Anthropic SDK"),
    "claude-agent-sdk": ("frameworks", "Claude Agent SDK"),
    "openai": ("frameworks", "OpenAI SDK"),
    "langchain": ("frameworks", "LangChain"),
    "langgraph": ("frameworks", "LangGraph"),
    "llama-index": ("frameworks", "LlamaIndex"),
    "mcp": ("frameworks", "MCP SDK"),
    "pandas": ("frameworks", "pandas"),
    "polars": ("frameworks", "Polars"),
    "numpy": ("frameworks", "NumPy"),
    "scikit-learn": ("frameworks", "scikit-learn"),
    "torch": ("frameworks", "PyTorch"),
    "tensorflow": ("frameworks", "TensorFlow"),
    "transformers": ("frameworks", "Transformers"),
    "jupyter": ("frameworks", "Jupyter"),
    "jupyterlab": ("frameworks", "Jupyter"),
    # databases
    "psycopg": ("databases", "PostgreSQL"),
    "psycopg2": ("databases", "PostgreSQL"),
    "psycopg2-binary": ("databases", "PostgreSQL"),
    "asyncpg": ("databases", "PostgreSQL"),
    "pymysql": ("databases", "MySQL"),
    "mysqlclient": ("databases", "MySQL"),
    "aiomysql": ("databases", "MySQL"),
    "pymongo": ("databases", "MongoDB"),
    "motor": ("databases", "MongoDB"),
    "beanie": ("databases", "MongoDB"),
    "redis": ("databases", "Redis"),
    "aiosqlite": ("databases", "SQLite"),
    # testing
    "pytest": ("test_tools", "pytest"),
    "hypothesis": ("test_tools", "Hypothesis"),
    "tox": ("test_tools", "tox"),
    "nox": ("test_tools", "nox"),
    # tooling
    "ruff": ("tools", "Ruff"),
    "black": ("tools", "Black"),
    "isort": ("tools", "isort"),
    "flake8": ("tools", "Flake8"),
    "mypy": ("tools", "mypy"),
    "pyright": ("tools", "Pyright"),
    "pre-commit": ("tools", "pre-commit"),
    # infrastructure hints (low confidence, see infrastructure.py)
    "boto3": ("infra_hint", "AWS"),
    "google-cloud-storage": ("infra_hint", "Google Cloud"),
    "azure-identity": ("infra_hint", "Azure"),
}

BACKEND_FRAMEWORKS = {
    "FastAPI",
    "Django",
    "Flask",
    "Starlette",
    "Litestar",
    "Django REST Framework",
}
AI_FRAMEWORKS = {
    "Anthropic SDK",
    "Claude Agent SDK",
    "OpenAI SDK",
    "LangChain",
    "LangGraph",
    "LlamaIndex",
    "MCP SDK",
}
DATA_FRAMEWORKS = {
    "pandas",
    "Polars",
    "NumPy",
    "scikit-learn",
    "PyTorch",
    "TensorFlow",
    "Transformers",
    "Jupyter",
}
CLI_FRAMEWORKS = {"Typer", "Click"}

_NAME_RE = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")


def normalize_requirement(spec: str) -> str | None:
    """'FastAPI[standard]>=0.110 ; python_version>"3.9"' -> 'fastapi'."""
    spec = spec.strip()
    if not spec or spec.startswith(("#", "-", "git+", "http")):
        return None
    match = _NAME_RE.match(spec)
    if not match:
        return None
    return match.group(1).lower().replace("_", "-").replace(".", "-")


def _collect_pyproject_deps(data: dict[str, Any]) -> list[str]:
    deps: list[str] = []
    project = data.get("project", {}) or {}
    deps.extend(project.get("dependencies", []) or [])
    for group in (project.get("optional-dependencies", {}) or {}).values():
        deps.extend(group or [])
    for group in (data.get("dependency-groups", {}) or {}).values():
        deps.extend(item for item in (group or []) if isinstance(item, str))
    tool = data.get("tool", {}) or {}
    uv = tool.get("uv", {}) or {}
    deps.extend(uv.get("dev-dependencies", []) or [])
    poetry = tool.get("poetry", {}) or {}
    deps.extend((poetry.get("dependencies", {}) or {}).keys())
    deps.extend((poetry.get("dev-dependencies", {}) or {}).keys())
    for group in (poetry.get("group", {}) or {}).values():
        deps.extend(((group or {}).get("dependencies", {}) or {}).keys())
    names = []
    for dep in deps:
        if not isinstance(dep, str):
            continue
        name = normalize_requirement(dep)
        if name and name != "python":
            names.append(name)
    return names


def _python_version(requires: str | None) -> str | None:
    if not requires:
        return None
    match = re.search(r"(\d+\.\d+)", requires)
    return match.group(1) if match else None


def is_cwi_pyproject(data: dict[str, Any] | None) -> bool:
    return bool(data) and (data.get("project", {}) or {}).get("name") == paths.CWI_PACKAGE_NAME


def detect_python(ctx: ScanContext, unit_path: str) -> bool:
    """Detect Python signals in `unit_path`. Returns True when a Python manifest was found."""
    pyproject_rel = join(unit_path, "pyproject.toml")
    pyproject = ctx.read_toml(pyproject_rel) if ctx.is_file(pyproject_rel) else None
    if is_cwi_pyproject(pyproject):
        # The CWI template's own packaging is not the user's application.
        ctx.ignored_paths.update(
            {pyproject_rel, join(unit_path, "uv.lock"), join(unit_path, ".python-version")}
        )
        pyproject = None
        pyproject_rel = ""

    req_files = [
        r
        for r in (
            "requirements.txt",
            "requirements-dev.txt",
            "requirements/base.txt",
            "requirements/dev.txt",
        )
        if ctx.is_file(join(unit_path, r))
    ]
    pipfile = ctx.is_file(join(unit_path, "Pipfile"))
    setup_py = ctx.is_file(join(unit_path, "setup.py")) or ctx.is_file(join(unit_path, "setup.cfg"))
    manage_py = ctx.is_file(join(unit_path, "manage.py"))

    if not (pyproject is not None or req_files or pipfile or setup_py or manage_py):
        return False

    unit = ctx.unit(unit_path)
    unit.has_manifest = True
    deps: dict[str, str] = {}  # name -> source

    if pyproject is not None:
        for name in _collect_pyproject_deps(pyproject):
            deps.setdefault(name, f"{pyproject_rel} dependency")
        requires = (pyproject.get("project", {}) or {}).get("requires-python")
        version = _python_version(requires)
        poetry_python = ((pyproject.get("tool", {}) or {}).get("poetry", {}) or {}).get(
            "dependencies", {}
        ) or {}
        if not version and isinstance(poetry_python.get("python"), str):
            version = _python_version(poetry_python["python"])
        if version:
            unit.language_version = version
        tool = pyproject.get("tool", {}) or {}
        for section, (category, display) in {
            "ruff": ("tools", "Ruff"),
            "black": ("tools", "Black"),
            "mypy": ("tools", "mypy"),
            "pyright": ("tools", "Pyright"),
            "isort": ("tools", "isort"),
        }.items():
            if section in tool:
                ctx.add_for(unit, category, display, f"{pyproject_rel} [tool.{section}]")
        if "pytest" in tool:
            ctx.add_for(unit, "test_tools", "pytest", f"{pyproject_rel} [tool.pytest]")
        if "poetry" in tool:
            ctx.add_for(unit, "package_managers", "Poetry", f"{pyproject_rel} [tool.poetry]")
        if (pyproject.get("project", {}) or {}).get("scripts"):
            ctx.cli_signals.append(f"{pyproject_rel} [project.scripts]")
        if "build-system" in pyproject:
            ctx.library_signals.append(f"{pyproject_rel} [build-system]")

    for req in req_files:
        rel = join(unit_path, req)
        text = ctx.read_text(rel) or ""
        for line in text.splitlines():
            name = normalize_requirement(line)
            if name:
                deps.setdefault(name, f"{rel} requirement")

    pv_rel = join(unit_path, ".python-version")
    if not unit.language_version and pv_rel not in ctx.ignored_paths and ctx.is_file(pv_rel):
        version = _python_version(ctx.read_text(pv_rel))
        if version:
            unit.language_version = version

    unit.language = "Python"
    language_label = f"Python {unit.language_version}" if unit.language_version else "Python"
    source = pyproject_rel or (
        join(unit_path, req_files[0]) if req_files else join(unit_path, "manage.py")
    )
    ctx.add("languages", language_label, source)
    if unit.language_version and not ctx.python_version:
        ctx.python_version = unit.language_version

    # Package managers from lockfiles.
    for lockfile, manager in (
        ("uv.lock", "uv"),
        ("poetry.lock", "Poetry"),
        ("Pipfile.lock", "Pipenv"),
        ("pdm.lock", "PDM"),
    ):
        rel = join(unit_path, lockfile)
        if rel not in ctx.ignored_paths and ctx.is_file(rel):
            ctx.add_for(unit, "package_managers", manager, rel)
    if pipfile and "Pipenv" not in unit.package_managers:
        ctx.add_for(unit, "package_managers", "Pipenv", join(unit_path, "Pipfile"))
    if req_files and not unit.package_managers:
        ctx.add_for(
            unit, "package_managers", "pip", join(unit_path, req_files[0]), Confidence.MEDIUM
        )

    if manage_py:
        ctx.add_for(unit, "frameworks", "Django", join(unit_path, "manage.py"))
        unit.backend = True

    for name, source in sorted(deps.items()):
        mapping = PY_PACKAGES.get(name)
        if mapping is None:
            continue
        category, display = mapping
        if category == "infra_hint":
            ctx.add("infrastructure", display, source, Confidence.LOW)
            continue
        ctx.add_for(unit, category, display, source)
        if category == "frameworks":
            if display in BACKEND_FRAMEWORKS:
                unit.backend = True
            if display in AI_FRAMEWORKS:
                ctx.ai_signals.append(f"{display} ({source})")
            if display in DATA_FRAMEWORKS:
                ctx.data_signals.append(f"{display} ({source})")
            if display in CLI_FRAMEWORKS:
                ctx.cli_signals.append(f"{display} ({source})")

    if ctx.glob(unit_path, "*.ipynb") or ctx.glob(join(unit_path, "notebooks"), "*.ipynb"):
        ctx.data_signals.append(f"Jupyter notebooks in {unit.display_path}")
    if ctx.is_file(join(unit_path, "alembic.ini")):
        ctx.add_for(unit, "frameworks", "Alembic", join(unit_path, "alembic.ini"))
    for conf in ("ruff.toml", ".ruff.toml"):
        if ctx.is_file(join(unit_path, conf)):
            ctx.add_for(unit, "tools", "Ruff", join(unit_path, conf))
    if ctx.is_file(join(unit_path, "mypy.ini")):
        ctx.add_for(unit, "tools", "mypy", join(unit_path, "mypy.ini"))
    for conf in ("pytest.ini", "conftest.py", "tests/conftest.py"):
        if ctx.is_file(join(unit_path, conf)):
            ctx.add_for(unit, "test_tools", "pytest", join(unit_path, conf))
            break
    if ctx.is_file(join(unit_path, "tox.ini")):
        ctx.add_for(unit, "test_tools", "tox", join(unit_path, "tox.ini"))
    return True
