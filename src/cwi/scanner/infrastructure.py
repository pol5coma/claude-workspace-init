"""Infrastructure and database detection from configuration files only."""

from __future__ import annotations

import re

from cwi.domain.enums import Confidence
from cwi.scanner.context import ScanContext, join

COMPOSE_FILES = ("docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml")
ENV_EXAMPLES = (".env.example", "example.env", ".env.sample", ".env.template", ".env.dist")

COMPOSE_IMAGES: dict[str, str] = {
    "postgres": "PostgreSQL",
    "postgis": "PostgreSQL",
    "mysql": "MySQL",
    "mariadb": "MariaDB",
    "mongo": "MongoDB",
    "redis": "Redis",
    "valkey": "Redis",
    "rabbitmq": "RabbitMQ",
    "elasticsearch": "Elasticsearch",
    "opensearch": "OpenSearch",
}

URL_SCHEMES: dict[str, str] = {
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "mysql": "MySQL",
    "mongodb": "MongoDB",
    "mongodb+srv": "MongoDB",
    "redis": "Redis",
    "rediss": "Redis",
    "sqlite": "SQLite",
}

ENV_NAME_HINTS: dict[str, str] = {
    "POSTGRES": "PostgreSQL",
    "PG": "PostgreSQL",
    "MYSQL": "MySQL",
    "MONGO": "MongoDB",
    "REDIS": "Redis",
}

_ENV_LINE = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$")


def detect_infrastructure(ctx: ScanContext, unit_paths: list[str]) -> None:
    for unit_path in unit_paths:
        for name in ("Dockerfile", "dockerfile"):
            rel = join(unit_path, name)
            if ctx.is_file(rel):
                ctx.add("infrastructure", "Docker", rel)
                break
        for name in COMPOSE_FILES:
            rel = join(unit_path, name)
            if ctx.is_file(rel):
                ctx.add("infrastructure", "Docker Compose", rel)
                _compose_services(ctx, rel)

    root_files = {
        "fly.toml": "Fly.io",
        "vercel.json": "Vercel",
        "netlify.toml": "Netlify",
        "serverless.yml": "Serverless Framework",
        "serverless.yaml": "Serverless Framework",
        "cdk.json": "AWS CDK",
        "render.yaml": "Render",
        "railway.json": "Railway",
        "app.yaml": "Google App Engine",
        "Procfile": "Heroku",
        "skaffold.yaml": "Kubernetes",
    }
    for name, display in root_files.items():
        if ctx.is_file(name):
            ctx.add(
                "infrastructure",
                display,
                name,
                Confidence.HIGH if name != "app.yaml" else Confidence.LOW,
            )
    if ctx.is_file("cdk.json"):
        ctx.add("infrastructure", "AWS", "cdk.json")

    if ctx.glob(".github/workflows", "*.yml") or ctx.glob(".github/workflows", "*.yaml"):
        ctx.add("infrastructure", "GitHub Actions", ".github/workflows/")
    if ctx.is_file(".gitlab-ci.yml"):
        ctx.add("infrastructure", "GitLab CI", ".gitlab-ci.yml")

    tf_files: list[str] = []
    for base in ("", "terraform", "infra", "infrastructure", "deploy"):
        tf_files.extend(ctx.glob(base, "*.tf"))
        if base and ctx.is_dir(base):
            tf_files.extend(ctx.glob(base, "*/*.tf"))
    if tf_files:
        ctx.add("infrastructure", "Terraform", tf_files[0])
        for rel in tf_files[:20]:
            text = ctx.read_text(rel) or ""
            for provider, display in (
                ("aws", "AWS"),
                ("google", "Google Cloud"),
                ("azurerm", "Azure"),
            ):
                if re.search(rf'provider\s+"{provider}"', text):
                    ctx.add("infrastructure", display, f"{rel} provider", Confidence.MEDIUM)
    for base in ("k8s", "kubernetes", "helm", "charts"):
        if ctx.is_dir(base):
            ctx.add("infrastructure", "Kubernetes", f"{base}/", Confidence.MEDIUM)
            break


def _compose_services(ctx: ScanContext, rel: str) -> None:
    text = ctx.read_text(rel) or ""
    for match in re.finditer(r"^\s*image:\s*[\"']?([^\s\"'#]+)", text, re.M):
        image = match.group(1).split("/")[-1].split(":")[0].split("@")[0].lower()
        for key, display in COMPOSE_IMAGES.items():
            if image == key or image.startswith(key + "-"):
                ctx.add("databases", display, f"{rel} service image", Confidence.MEDIUM)
                break


def detect_env_examples(ctx: ScanContext, unit_paths: list[str]) -> None:
    """Inspect example env files only. Values are never stored; URL schemes are read in memory."""
    for unit_path in unit_paths:
        for name in ENV_EXAMPLES:
            rel = join(unit_path, name)
            text = ctx.read_text(rel)
            if text is None:
                continue
            for line in text.splitlines():
                match = _ENV_LINE.match(line)
                if not match:
                    continue
                var, value = match.group(1), match.group(2).strip().strip("\"'")
                scheme = value.split("://", 1)[0].lower() if "://" in value else ""
                scheme = scheme.split("+")[0] if scheme not in URL_SCHEMES else scheme
                if scheme in URL_SCHEMES:
                    ctx.add(
                        "databases", URL_SCHEMES[scheme], f"{rel} ({var} scheme)", Confidence.MEDIUM
                    )
                    continue
                for prefix, display in ENV_NAME_HINTS.items():
                    if var.startswith(prefix + "_"):
                        ctx.add("databases", display, f"{rel} ({var} name)", Confidence.LOW)
                        break


def detect_other_languages(ctx: ScanContext, unit_path: str) -> bool:
    """Lightweight detection for non-Python/JS ecosystems (language + package manager only)."""
    found = False
    manifests = (
        ("go.mod", "Go", "Go modules"),
        ("Cargo.toml", "Rust", "Cargo"),
        ("pom.xml", "Java", "Maven"),
        ("build.gradle", "Java/Kotlin", "Gradle"),
        ("build.gradle.kts", "Kotlin", "Gradle"),
        ("Gemfile", "Ruby", "Bundler"),
        ("composer.json", "PHP", "Composer"),
        ("mix.exs", "Elixir", "Mix"),
        ("Package.swift", "Swift", "SwiftPM"),
        ("pubspec.yaml", "Dart", "pub"),
    )
    for name, language, manager in manifests:
        rel = join(unit_path, name)
        if ctx.is_file(rel):
            unit = ctx.unit(unit_path)
            unit.has_manifest = True
            unit.language = unit.language or language
            ctx.add("languages", language, rel)
            ctx.add_for(unit, "package_managers", manager, rel)
            found = True
            _framework_hints(ctx, unit_path, name, rel)
    for pattern in ("*.sln", "*.csproj"):
        hits = ctx.glob(unit_path, pattern)
        if hits:
            unit = ctx.unit(unit_path)
            unit.has_manifest = True
            unit.language = unit.language or "C#"
            ctx.add("languages", "C#", hits[0])
            ctx.add_for(unit, "package_managers", ".NET", hits[0])
            found = True
            break
    return found


def _framework_hints(ctx: ScanContext, unit_path: str, manifest: str, rel: str) -> None:
    text = ctx.read_text(rel) or ""
    unit = ctx.unit(unit_path)
    hints: dict[str, list[tuple[str, str, bool]]] = {
        "go.mod": [
            ("github.com/gin-gonic/gin", "Gin", True),
            ("github.com/labstack/echo", "Echo", True),
            ("github.com/gofiber/fiber", "Fiber", True),
            ("github.com/go-chi/chi", "chi", True),
            ("github.com/jackc/pgx", "PostgreSQL", False),
            ("github.com/lib/pq", "PostgreSQL", False),
        ],
        "Cargo.toml": [
            ("axum", "Axum", True),
            ("actix-web", "Actix Web", True),
            ("rocket", "Rocket", True),
            ("sqlx", "SQLx", False),
            ("tokio-postgres", "PostgreSQL", False),
        ],
        "Gemfile": [
            ("rails", "Rails", True),
            ("sinatra", "Sinatra", True),
            ("pg", "PostgreSQL", False),
        ],
        "pom.xml": [("spring-boot", "Spring Boot", True)],
        "build.gradle": [("spring-boot", "Spring Boot", True)],
        "build.gradle.kts": [("spring-boot", "Spring Boot", True)],
        "composer.json": [("laravel/framework", "Laravel", True), ("symfony/", "Symfony", True)],
    }
    for needle, display, backend in hints.get(manifest, []):
        if needle in text:
            category = "databases" if display == "PostgreSQL" else "frameworks"
            ctx.add_for(unit, category, display, f"{rel} dependency")
            if backend:
                unit.backend = True
