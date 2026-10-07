"""JavaScript / TypeScript detection (package.json, lockfiles, framework configs)."""

from __future__ import annotations

import re
from typing import Any

from cwi.domain.enums import Confidence
from cwi.scanner.context import ScanContext, Unit, join
from cwi.scanner.versions import js_lock_index

# package -> (category, display)
JS_PACKAGES: dict[str, tuple[str, str]] = {
    "react": ("frameworks", "React"),
    "next": ("frameworks", "Next.js"),
    "vue": ("frameworks", "Vue"),
    "nuxt": ("frameworks", "Nuxt"),
    "svelte": ("frameworks", "Svelte"),
    "@sveltejs/kit": ("frameworks", "SvelteKit"),
    "@angular/core": ("frameworks", "Angular"),
    "solid-js": ("frameworks", "Solid"),
    "astro": ("frameworks", "Astro"),
    "@remix-run/react": ("frameworks", "Remix"),
    "vite": ("frameworks", "Vite"),
    "electron": ("frameworks", "Electron"),
    "react-native": ("frameworks", "React Native"),
    "expo": ("frameworks", "Expo"),
    "express": ("frameworks", "Express"),
    "fastify": ("frameworks", "Fastify"),
    "@nestjs/core": ("frameworks", "NestJS"),
    "hono": ("frameworks", "Hono"),
    "koa": ("frameworks", "Koa"),
    "@trpc/server": ("frameworks", "tRPC"),
    "tailwindcss": ("frameworks", "Tailwind CSS"),
    "prisma": ("frameworks", "Prisma"),
    "@prisma/client": ("frameworks", "Prisma"),
    "drizzle-orm": ("frameworks", "Drizzle"),
    "typeorm": ("frameworks", "TypeORM"),
    "mongoose": ("frameworks", "Mongoose"),
    "@anthropic-ai/sdk": ("frameworks", "Anthropic SDK"),
    "@anthropic-ai/claude-agent-sdk": ("frameworks", "Claude Agent SDK"),
    "@modelcontextprotocol/sdk": ("frameworks", "MCP SDK"),
    "openai": ("frameworks", "OpenAI SDK"),
    "ai": ("frameworks", "Vercel AI SDK"),
    "langchain": ("frameworks", "LangChain"),
    "commander": ("frameworks", "Commander"),
    "yargs": ("frameworks", "yargs"),
    "@oclif/core": ("frameworks", "oclif"),
    # databases
    "pg": ("databases", "PostgreSQL"),
    "postgres": ("databases", "PostgreSQL"),
    "mysql2": ("databases", "MySQL"),
    "mysql": ("databases", "MySQL"),
    "mongodb": ("databases", "MongoDB"),
    "redis": ("databases", "Redis"),
    "ioredis": ("databases", "Redis"),
    "better-sqlite3": ("databases", "SQLite"),
    "sqlite3": ("databases", "SQLite"),
    # testing
    "vitest": ("test_tools", "Vitest"),
    "jest": ("test_tools", "Jest"),
    "@playwright/test": ("test_tools", "Playwright"),
    "cypress": ("test_tools", "Cypress"),
    "mocha": ("test_tools", "Mocha"),
    "@testing-library/react": ("test_tools", "Testing Library"),
    # tooling
    "eslint": ("tools", "ESLint"),
    "prettier": ("tools", "Prettier"),
    "@biomejs/biome": ("tools", "Biome"),
    "typescript": ("tools", "TypeScript compiler"),
    # infra hints
    "aws-sdk": ("infra_hint", "AWS"),
    "@aws-sdk/client-s3": ("infra_hint", "AWS"),
    "aws-cdk-lib": ("infrastructure", "AWS CDK"),
}

BACKEND = {"Express", "Fastify", "NestJS", "Hono", "Koa", "tRPC"}
FRONTEND = {
    "React",
    "Next.js",
    "Vue",
    "Nuxt",
    "Svelte",
    "SvelteKit",
    "Angular",
    "Solid",
    "Astro",
    "Remix",
    "React Native",
    "Expo",
    "Electron",
}
AI = {"Anthropic SDK", "Claude Agent SDK", "MCP SDK", "OpenAI SDK", "Vercel AI SDK", "LangChain"}
CLI = {"Commander", "yargs", "oclif"}

CONFIG_FILES: dict[str, tuple[str, str]] = {
    "vite.config": ("frameworks", "Vite"),
    "next.config": ("frameworks", "Next.js"),
    "nuxt.config": ("frameworks", "Nuxt"),
    "svelte.config": ("frameworks", "Svelte"),
    "astro.config": ("frameworks", "Astro"),
    "vitest.config": ("test_tools", "Vitest"),
    "jest.config": ("test_tools", "Jest"),
    "playwright.config": ("test_tools", "Playwright"),
    "cypress.config": ("test_tools", "Cypress"),
    "eslint.config": ("tools", "ESLint"),
    ".eslintrc": ("tools", "ESLint"),
    ".prettierrc": ("tools", "Prettier"),
    "prettier.config": ("tools", "Prettier"),
    "biome": ("tools", "Biome"),
}

LOCKFILES = (
    ("pnpm-lock.yaml", "pnpm"),
    ("yarn.lock", "yarn"),
    ("bun.lockb", "bun"),
    ("bun.lock", "bun"),
    ("package-lock.json", "npm"),
)


def package_manager_for(
    ctx: ScanContext, unit_path: str, package_json: dict[str, Any] | None
) -> tuple[str, str, bool]:
    """Return (manager, source, from_lockfile). Lockfiles in the unit win, then the root."""
    for base in dict.fromkeys([unit_path, ""]):
        for lockfile, manager in LOCKFILES:
            rel = join(base, lockfile)
            if ctx.is_file(rel):
                return manager, rel, True
    declared = (package_json or {}).get("packageManager")
    if isinstance(declared, str) and declared:
        return declared.split("@")[0], join(unit_path, "package.json") + " packageManager", True
    return "npm", join(unit_path, "package.json"), False


def detect_javascript(ctx: ScanContext, unit_path: str) -> bool:
    pkg_rel = join(unit_path, "package.json")
    if not ctx.is_file(pkg_rel):
        # Framework config files alone still count as evidence.
        return _detect_configs(ctx, ctx.unit(unit_path), unit_path, require_manifest=True)
    data = ctx.read_json(pkg_rel)
    if not isinstance(data, dict):
        data = {}
    unit = ctx.unit(unit_path)
    unit.has_manifest = True

    deps: dict[str, str] = {}
    specs: dict[str, str] = {}
    for section in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
        for name, spec in (data.get(section) or {}).items():
            deps.setdefault(name, f"{pkg_rel} {section}")
            if isinstance(spec, str):
                specs.setdefault(name, spec)
    locks = js_lock_index(ctx, unit_path, list(deps))

    manager, manager_source, from_lock = package_manager_for(ctx, unit_path, data)
    ctx.add_for(
        unit,
        "package_managers",
        manager,
        manager_source,
        Confidence.HIGH if from_lock else Confidence.MEDIUM,
    )

    typescript = "typescript" in deps or ctx.is_file(join(unit_path, "tsconfig.json"))
    unit.language = "TypeScript" if typescript else "JavaScript"
    if typescript and "typescript" in deps:
        unit.language_version = locks.resolve("typescript", specs.get("typescript"))
    ctx.add(
        "languages",
        unit.language,
        join(unit_path, "tsconfig.json")
        if ctx.is_file(join(unit_path, "tsconfig.json"))
        else pkg_rel,
    )

    for name, source in sorted(deps.items()):
        mapping = JS_PACKAGES.get(name)
        if mapping is None:
            continue
        category, display = mapping
        if category == "infra_hint":
            ctx.add("infrastructure", display, source, Confidence.LOW)
            continue
        if display == "TypeScript compiler":
            continue  # already represented by the TypeScript language
        ctx.add_for(unit, category, display, source)
        _classify(ctx, unit, display, source)
        if category == "frameworks":
            version = locks.resolve(name, specs.get(name))
            if version:
                unit.framework_versions.setdefault(display, version)

    if data.get("workspaces"):
        ctx.monorepo_signals.append(f"{pkg_rel} workspaces")
    if data.get("bin"):
        ctx.cli_signals.append(f"{pkg_rel} bin")
    if (data.get("main") or data.get("exports")) and not (unit.frontend or unit.backend):
        ctx.library_signals.append(f"{pkg_rel} main/exports")

    _detect_configs(ctx, unit, unit_path, require_manifest=False)
    _detect_prisma(ctx, unit, unit_path)
    return True


def _classify(ctx: ScanContext, unit: Unit, display: str, source: str) -> None:
    if display in BACKEND:
        unit.backend = True
    if display in FRONTEND:
        unit.frontend = True
    if display in AI:
        ctx.ai_signals.append(f"{display} ({source})")
    if display in CLI:
        ctx.cli_signals.append(f"{display} ({source})")


def _detect_configs(
    ctx: ScanContext, unit: Unit, unit_path: str, *, require_manifest: bool
) -> bool:
    found = False
    base = ctx.path(unit_path)
    if not base.is_dir():
        return False
    for entry in sorted(base.iterdir()):
        if not entry.is_file() or entry.is_symlink():
            continue
        for prefix, (category, display) in CONFIG_FILES.items():
            if entry.name == prefix or entry.name.startswith(prefix + "."):
                rel = join(unit_path, entry.name)
                if require_manifest and category != "frameworks":
                    continue
                ctx.add_for(unit, category, display, rel)
                _classify(ctx, unit, display, rel)
                found = True
    if found and require_manifest:
        unit.has_manifest = True
        if unit.language is None:
            unit.language = "JavaScript"
    return found


def _detect_prisma(ctx: ScanContext, unit: Unit, unit_path: str) -> None:
    for rel in (join(unit_path, "prisma/schema.prisma"), join(unit_path, "schema.prisma")):
        text = ctx.read_text(rel)
        if text is None:
            continue
        ctx.add_for(unit, "frameworks", "Prisma", rel)
        match = re.search(r'datasource\s+\w+\s*\{[^}]*?provider\s*=\s*"([a-z]+)"', text, re.S)
        provider_found = match.group(1).lower() if match else None
        for provider, display in (
            ("postgresql", "PostgreSQL"),
            ("mysql", "MySQL"),
            ("sqlite", "SQLite"),
            ("mongodb", "MongoDB"),
            ("sqlserver", "SQL Server"),
            ("cockroachdb", "CockroachDB"),
        ):
            if provider_found == provider:
                ctx.add_for(unit, "databases", display, f"{rel} datasource provider")
        return
