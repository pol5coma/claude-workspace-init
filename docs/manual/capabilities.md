# Capability catalog

[Usage manual](../../USAGE.md) · [Architecture](../../architecture.md)

SPADO's catalog contains reusable skills, agents, scripts, hooks and MCP configurations. Install selected capabilities through `spado init`, with or without the Full SPDLC workflow. The CLI resolves declared dependencies, checks conflicts and host compatibility, previews changes and records installed file hashes in `.spado/installation.json`.

## Install capabilities

Choose explicit references from `spado catalog list`:

```bash
spado catalog list
spado catalog validate
spado init --no-workflow --host claude --capability skill:kickoff --dry-run
spado init --no-workflow --host claude --capability skill:kickoff
```

The last two commands install a standalone capability without `.spado/project.json` or PostgreSQL. To add capabilities to the organization, include repeatable `--capability TYPE:ID` options with normal workflow setup:

```bash
spado init --host claude --mode auto --embeddings external \
  --embedding-model text-embedding-3-small --capability mcp:github --dry-run
```

The installed tool catalog is the default source. `--catalog PATH` selects another catalog root. Project installation is additive: deselecting a previously installed capability does not delete its files. `--dry-run` performs validation and produces a preview without writing. Repeating an unchanged installation is idempotent; a modified managed file causes a conflict requiring reconciliation.

Catalog manifests (`spado.json`) declare identity, type, host support, dependencies, conflicts, optional requirements and recommendation metadata. Selection is currently explicit. `default_selected`, technology recommendations and family defaults are catalog metadata; `spado init` does not scan project technology or select capabilities automatically. A capability supporting only Claude cannot be installed for Codex. The renderer also rejects host-specific payloads it cannot safely translate.

## Author and validate

Use `spado catalog add skill|agent|script|hook|mcp` to import an existing resource. Each subcommand exposes the required source or configuration fields in `--help`; the [USAGE command reference](../../USAGE.md#cli-reference) lists every option. For example:

```bash
spado catalog add skill /path/to/SKILL.md --catalog ./catalog --yes
spado catalog validate --catalog ./catalog
spado catalog list --catalog ./catalog
```

The authoring commands write manifests and payloads under `catalog/<type>/[group/]ID/`. Edit those source files when updating the tool catalog. A group uses `group.json` and can hold defaults by project type; `spado catalog group create` and `spado catalog group defaults` manage them. Group metadata is available for future selection interfaces, while installation still requires explicit capability references. `spado catalog remove` edits the source catalog; it does not uninstall from existing projects.

Review source licenses and declared host support before importing third-party resources. MCP credentials belong in environment variables or host secrets, never literal values in catalog files. A catalog validation result checks structure and references; it does not connect to an MCP server or run an imported script.

## Optional project skills

`skill:kickoff`, `skill:project-discovery`, `skill:feature-spec` and `skill:feature-workflow` are standalone catalog skills. They can be installed individually. They do not create SPDLC runs, approve plans or record workflow evidence unless an agent separately uses SPADO's workflow services. Read each installed `SKILL.md` for its own instructions. The catalog also includes specialist agents, safety hooks and integration resources; `spado catalog list` shows their current IDs.

SPADO installs native resources in the selected host's directories. The host discovers and executes them after its project/session reload. `spado init` itself does not launch agents or invoke MCP tools.
