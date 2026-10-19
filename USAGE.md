# SPADO usage manual

The operating manual for **SPADO 0.2.0**: repository structure, setup, daily use and **all 28 terminal commands and their parameters**. This describes the implementation in this checkout; check `spado --version` and command-specific `--help` on other versions.

[Product overview](README.MD) · [Architecture](architecture.md) · [Implementation notes](docs/manual/implementation.md)

## Contents

1. [Choose your setup](#choose-your-setup)
2. [Repository map and sources of truth](#repository-map-and-sources-of-truth)
3. [Installation and setup](#installation-and-setup)
4. [First execution and everyday use](#first-execution-and-everyday-use)
5. [Modes, plans, dependencies and states](#modes-plans-dependencies-and-states)
6. [CLI reference](#cli-reference)
7. [Host invocation reference](#host-invocation-reference)
8. [Agent recording and event reference](#agent-recording-and-event-reference)
9. [Configuration and environment](#configuration-and-environment)
10. [Updates and maintenance](#updates-and-maintenance)
11. [Troubleshooting](#troubleshooting)

Supplemental chapters: [first-run and advanced event walkthrough](docs/manual/first-run.md), [capability catalog walkthrough](docs/manual/capabilities.md), [implementation notes](docs/manual/implementation.md). The complete command reference stays in this file.

## Choose your setup

SPADO uses one package and one project installer, `spado init`. Select a whole SPDLC organization or install compatible capabilities independently. The host executes agents; SPADO provides their instructions, catalog and, for workflows, authenticated state services.

| Your goal | Use | Result |
|---|---|---|
| Work through Full SPDLC | `spado init`, `spado db up`, then the host's `spdlc` entry skill | Installs the organization and runtime configuration, starts PostgreSQL and lets the host coordinate agents. |
| Pick skills, agents and MCP by category | `spado init --no-workflow` in a terminal | Interactive picker: choose hosts, browse categories, tick capabilities, confirm. No workflow state or PostgreSQL. |
| Install selected capabilities for Claude/Codex | `spado init --no-workflow --host HOST --capability TYPE:ID` or `--category CATEGORY` | Installs compatible skills, agents, scripts, hooks or MCP without workflow state or PostgreSQL. |
| Add capabilities to Full SPDLC | Repeat `--capability TYPE:ID` during workflow setup | Installs optional resources alongside the organization. |
| Inspect or record execution | `status`, `review`, `workflow`, `actor`, `docs` commands | Authenticated reads and writes against a configured workflow project. |
| Maintain the reusable catalog | `spado catalog …` | Edits source definitions; installed projects update when `spado init` is repeated. |

SPADO supports **Claude Code and Codex**. More hosts and workflows need implementation work. There is no autonomous scheduler, graphical runtime UI or background document watcher.

The organization consists of the Human, **CAOAO** (execution coordination), nine **Chief [Role] Agentic Officers** (domain decisions) and specialists (bounded assignments). CEAO owns executive direction; CAOAO coordinates execution. Skills provide behavioral instructions. See the [complete officer mapping](README.MD#chief-role-agentic-officers).

## Repository map and sources of truth

| Location | Purpose and edit guidance |
|---|---|
| `pyproject.toml`, `src/spado/cli.py` | Package/executable and command registration. |
| `src/spado/commands/catalog.py`, `src/spado/authoring`, `src/spado/catalog`, `src/spado/install` | Capability authoring and loading, dependency resolution, safe installation and conflict checks. |
| `src/spado/workflows` | Definitions, modes, plans, gates and state transitions. |
| `src/spado/runtime` | Setup, identities, PostgreSQL, events, protocol and embeddings. |
| `src/spado/adapters` | Native host resources and entry skills. |
| `catalog/skills`, `agents`, `scripts`, `hooks`, `mcp` | Modular resources with `spado.json` manifests. Author with catalog commands. |
| `catalog/workflows/spdlc/` | Canonical `workflow.json`, rules and subphase briefs. Edit SPDLC here. |
| `catalog/organizations/spdlc/organization.json` | Canonical officers, specialists and assignments. |
| `catalog/organization-skills/` | Their behavioral instructions. |
| `catalog/workflows/Full_SPDLC_Workflow.md` | Generated reading copy. Regenerate with `workflow render`; do not edit as the source. |
| `catalog/workflows/tools/agent-record.py` | Source of the installed facade using the same services as the CLI. |
| `tests/` | Unit, CLI and integration verification. |

Organization setup creates these resources **in the product repository**:

| Installed location | Purpose |
|---|---|
| `.spado/project.json` | Project ID, hosts, mode, embeddings, capabilities and database port. |
| `.spado/installation.json` | Organization/capability installer's managed-file hashes. |
| `.spado/catalog/` | Installed workflow, organization and skill copies. |
| `.spado/protocol.md`, `.spado/tools/agent-record.py` | Agent write contract and facade. |
| `.spado/local/compose.yaml`, `database.password`, `human.token`, `actors/` | Local database configuration and private credentials. |
| `.claude/agents/`, `.claude/skills/` | Native Claude organization resources. |
| `.codex/agents/`, `.agents/skills/` | Native Codex organization resources. |
| `.mcp.json`, `.claude/settings.json`, `.codex/config.toml` | Optional capability-specific host configuration. |
| Docker named volume | PostgreSQL runs, actors, events, document revisions and embeddings. |

Product documents remain ordinary files, commonly in `docs/`. The database retains recorded revisions/history. Source catalog, installed copies and pinned run snapshots are distinct. Editing README or architecture does not change agent instructions or existing executions automatically.

## Installation and setup

### Install the tool once

Keep a permanent tool checkout separate from products:

```text
~/tools/spado/           source/catalog used by the editable installation
~/projects/my-product/   product code, installed agents and project state
```

Use Python 3.12+ and `uv`. Organization execution also requires a coding-agent host and PostgreSQL/pgvector; the provided database commands use Docker with Compose. Capability-only installation needs no database. Local embeddings require a Python extra; external embeddings require a compatible endpoint and credential.

```bash
git clone https://github.com/pol5coma/claude-workspace-init ~/tools/spado
uv tool install -e ~/tools/spado
spado --version
spado --help
```

The URL retains the repository's historical name. Editable installation reads code from that checkout; keep it in place. For local embeddings, install the extra in the **tool environment**:

```bash
uv tool install --force -e "$HOME/tools/spado[local-embeddings]"
```

For development inside the SPADO checkout, use `uv sync --group dev` and `uv run spado …`; add `uv sync --extra local-embeddings` if needed. The development environment and `uv tool` environment are separate.

### Configure an organization project

Run these commands **in the product directory**, not in the SPADO source checkout. `spado init` is not an interactive wizard: on the first workflow installation, it requires `--host`, `--mode`, `--embeddings` and `--embedding-model`. Running bare `spado init` returns an error listing those four options.

For an existing project using Codex and an external embedding provider (replace the project path and model if needed):

```bash
cd ~/projects/my-product
spado init --host codex --mode auto \
  --embeddings external --embedding-model text-embedding-3-small --dry-run
spado init --host codex --mode auto \
  --embeddings external --embedding-model text-embedding-3-small
spado db up
spado status --human
```

The preview lists files under `writes` without installing them. The real `init` may list hundreds of `writes`: these are the native agents, skills, workflow briefs and SPADO configuration. It does **not** create or execute a run. `db up` starts PostgreSQL and creates `.spado/local/human.token`; `status --human` uses that credential and normally shows `runs: []` until you start a workflow. Bare `spado status` instead expects a delegated agent credential and reports `Set SPADO_ACTOR_TOKEN_FILE ... or use --human` when none is present. Do not export the Human token as an agent token.

Open or reload this product in Codex, then invoke `$spdlc` **in Codex chat**, with an objective. See [first execution](#first-execution-and-everyday-use). The external embedding key is needed when indexing or searching documents, not for this setup/status check.

To configure both hosts with local embeddings instead, the target directory must already exist:

```bash
mkdir -p ~/projects/my-product
cd ~/projects/my-product
spado init --host claude --host codex --mode semi-auto \
  --embeddings local \
  --embedding-model sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 \
  --dry-run
```

Review `writes`, then repeat the same `init` command without `--dry-run`. Select only your intended host(s). Continue:

```bash
spado db up
spado status --human
```

An empty `runs` list is expected initially. Neither `init` nor `db up` starts agents or creates an execution.

For simultaneous projects, choose different `--database-port` values at initial setup (default `55432`). That flag is currently ignored when updating an existing project; see [known gaps](docs/manual/implementation.md#current-limits).

For external embeddings use `--embeddings external --embedding-model MODEL_ID --embedding-endpoint URL` and set `SPADO_EMBEDDING_API_KEY` through your environment. Indexing sends document chunks and searching sends queries to that provider. Local models download on first use. Setup and ordinary state operations do not encode embeddings.

### Install capabilities without a workflow

Capability-only setup provisions skills, agents, MCP servers, hooks and scripts into the project. It creates no `.spado/project.json`, PostgreSQL, run state or memory; only the files and `.spado/installation.json` bookkeeping.

#### Interactive picker

In the product directory, run without `--capability` or `--category`:

```bash
cd ~/projects/my-product
spado init --no-workflow             # pick, preview, confirm, install
spado init --no-workflow --dry-run   # pick and preview only
```

1. **Hosts**: Claude Code (preselected) and/or Codex. Skipped when `--host` is given.
2. **Categories**: each [category](#capability-categories) shows how many capabilities are compatible with the chosen hosts.
3. **Capabilities**: one list grouped under the chosen categories. A capability in several chosen categories appears once, under the first. Keys: `space` toggles, `a` toggles all, `i` inverts, `enter` confirms.
4. **Summary**: the final references, including dependencies added automatically (`required by …`), and the number of files to write.
5. **Confirm**: `Install them now?` writes the files and prints the usual JSON `writes`/`unchanged`. With `--dry-run` it prints the preview and stops.

Selecting nothing, or declining the confirmation, cancels with exit code 1 and writes nothing. The picker opens only when stdin and stdout are a terminal; elsewhere (CI, scripts, pipes) use the flags below.

#### Non-interactive selection

```bash
spado init --no-workflow --host claude --category backend --category testing --dry-run
spado init --no-workflow --host codex --capability mcp:github
spado init --no-workflow --host claude --category data --capability skill:flask-specialist
```

`--category` installs every capability of that category compatible with **all** selected hosts; it combines with `--capability`. Supply MCP credentials separately. Repeated `--capability TYPE:ID` options also add capabilities to organization setup; `--category` is capability-only.

Catalog `default_selected`, project-type recommendations and group defaults remain metadata; `init` does not scan a project or apply automatic recommendations. See the [capability walkthrough](docs/manual/capabilities.md).

#### Capability categories

Each catalog manifest lists one or more `categories`. Use the ID with `--category`.

| ID | Shown as | Typical content |
|---|---|---|
| `architecture` | Architecture & system design | Architects, ADRs, API and system design, diagrams. |
| `backend` | Backend & APIs | Django, FastAPI, Flask, Spring Boot, Laravel, NestJS, Go and other server frameworks. |
| `frontend` | Frontend & UI | React, Vue, Angular, Next.js, Nuxt, Vite, accessibility, design systems, motion. |
| `mobile` | Mobile & desktop | Flutter, React Native, Swift/SwiftUI, Kotlin/Android, desktop E2E. |
| `data` | Databases & data | PostgreSQL, MySQL, SQL, Redis, ClickHouse, ORMs, migrations. |
| `ai` | AI, ML & LLM applications | RAG, fine-tuning, PyTorch, MCP servers, LLM cost and evaluation. |
| `infrastructure` | Infrastructure, DevOps & networking | Docker, Kubernetes, Terraform, deployment, incidents, networks. |
| `security` | Security & compliance | Security reviews and scans, framework security, HIPAA/PHI, safety guards. |
| `testing` | Testing & QA | TDD, unit/E2E testing per language, verification loops, QA agents. |
| `quality` | Code review, quality & debugging | Reviewers, refactoring, debugging, build-error resolvers, performance. |
| `languages` | Languages & coding standards | Python, TypeScript, Go, Rust, Kotlin, Java, C++, .NET idioms and reviewers. |
| `workflow` | Development workflow & agent tooling | Feature specs, orchestration, planning, git/GitHub, Claude Code harness tools. |
| `product` | Product, content & business | Product discovery, research, marketing, content, media, business operations. |

`spado catalog list` shows each capability's categories.

## First execution and everyday use

Open the configured product in your host. In **Claude chat**:

```text
/spdlc --new-run --subphase initial-ideation --mode semi-auto
Start an independent opportunity assessment. The objective is to choose one product problem worth investigating. Ask for the initial business context, show the concrete plan, and wait for my approval before executing it.
```

In **Codex chat**, use `$spdlc` with the same request. These are skill invocations, not shell commands: the shell would treat `$spdlc` as a variable.

If you configured `auto` above, a first Codex request can instead be:

```text
$spdlc --new-run --subphase initial-ideation --mode auto
Assess this product idea: [describe the idea, intended users and what you want to learn]. Create an independent run, show me its ID and coordinate the work through the assigned agents.
```

The host creates a run on your instruction, delegates CAOAO/officers/specialist, obtains the brief and prepares a plan. In `semi-auto`, approve the concrete plan before work. Officers review the evidence; CAOAO accepts the activity and promotes accepted revisions. Keep the returned run ID.

```bash
spado status --run RUN_ID --human
spado workflow context --run RUN_ID --subphase initial-ideation --human
spado review subphase initial-ideation --run RUN_ID --human
```

Replace `RUN_ID` with the real UUID. `pending` means no activity was recorded, not that a background worker is running. See the [complete tutorial](docs/manual/first-run.md).

| Goal | Action |
|---|---|
| Begin a complete workflow | Host: `spdlc --new-run --mode MODE`, plus your objective. |
| Resume | Host: `spdlc --run RUN_ID`, naming the phase/subphase/activity. |
| Advance within a full run | Keep the run ID and give an explicit reason; missing dependencies remain visible. |
| Work outside a partial run's scope | Create an independent run; scope is not silently expanded. |
| Discuss only | Host: `spado --chat --run RUN_ID`; identify the scope in your message. |
| Inspect blockers or stale work | Terminal `spado review …`, or host `spado --review …`. |
| Change a mode | Give explicit Human direction; the host records a `mode` event. No `spado mode` command exists. |
| Return another day | Preserve run/credentials and resume with `--run`. There is no CLI pause/resume scheduler. |

Commands never silently choose the latest run. Most infer selection only when exactly one run is accessible; `status` lists choices for zero/multiple runs. Explicit `--run` is preferable for repeatable operations.

### Phase selectors

The phase slug and numeric ID are interchangeable in `--phase`, `spado review phase` and host invocations. For example, `--phase definition-design` and `--phase 3` select the same phase.

| ID | Slug | Phase |
|---|---|---|
| `1` | `idea-strategy` | Idea & Strategy |
| `2` | `discovery` | Discovery |
| `3` | `definition-design` | Definition and Design |
| `4` | `development-validation` | Development and Validation |
| `5` | `launch` | Launch |
| `6` | `operation-evolution` | Operation and Evolution |
| `7` | `retirement-replacement` | Retirement or Replacement |

Subphases work the same way: `--subphase ui-design` and `--subphase 3.5` select the same subphase. Run `spado workflow validate --catalog .spado/catalog` in the configured project for all 62 subphase slugs.

## Modes, plans, dependencies and states

| Mode | Before execution | Execution/result |
|---|---|---|
| `agentic` | CAOAO validates the plan; no Human approval requests | Agents execute/review; report unresolved blockers without requesting Human intervention. |
| `auto` | CAOAO validates | Ask the Human only for genuinely required information, authority or action. |
| `semi-auto` | Human approves each plan version | Agents execute; officers review; CAOAO accepts. |
| `manual` | Human approves and chooses `human`, `assisted` or `delegated` execution | Domain reviews remain required; Human also reviews the result and closes manual phases. |

Voluntary Human participation is possible in all modes. Modes do not override host permissions. All modes use plans: workflow/phase runs need approved phase and activity plans; independent subphase runs need the activity plan only. Plans include objective, canonical deliverable, actions, criteria, input revision IDs/hashes and assumptions. Approval targets a specific plan ID/version and does not accept the result.

An **activity** is one execution of a subphase. Full workflows follow phase order by default; subphases follow dependencies. Advances require a reason. Provisional work with missing inputs needs assumptions; acceptance waits for inputs, a revised approved plan and required reviews. Skipped prerequisites do not execute automatically.

New activity mode precedence: explicit override → subphase override → phase override → run default. Existing activities retain their mode. A Human `mode` event targeting an activity clears its plan approval; changing a parent default does not rewrite existing activities or accepted history.

| State | Meaning / next action |
|---|---|
| `pending` | No activity recorded; prepare a plan. |
| `awaiting_plan_approval` | Obtain approval of the current plan/version. |
| `ready` | Approved; start subject to current input/phase gates. |
| `running` | Start recorded, not live process telemetry. |
| `blocked` | Resolve the blocker and recheck before restarting. |
| `provisional` | Missing prerequisites; acceptance blocked. |
| `awaiting_review` | Delivered evidence awaits decisions. |
| `needs_revalidation` | Changes made prior approvals/evidence stale. |
| `accepted` | Activity gates passed; promotion remains separate. |
| `not_applicable` | Responsible officers excluded a conditional subphase. Required subphases cannot be skipped this way. |

SPDLC-specific: phase 6 has repeated operating cycles; phase 7 requires CEAO's recorded retirement decision. See [architecture](architecture.md) for details.

## CLI reference

### Conventions and shared options

Uppercase `RUN_ID`, `ACTIVITY_ID`, `REVISION_ID`, `FILE` and similar values are placeholders. Replace them with actual values. Brackets in syntax mean optional arguments; do not type them.

Every command/group accepts `--help`; `spado --version` prints the version; bare `spado` displays help. `--root`, `--run` and `--human` are **not global options**.

These **shared runtime options** apply to `status`, `review`, `actor create`, `workflow context|prepare|record|export` and every `docs` command:

| Option | Default | Meaning |
|---|---|---|
| `--root PATH` | `.` | Configured project directory; no upward config discovery. |
| `--run ID` | unset | Select run; infer only if exactly one is accessible. `status` instead lists zero/multiple choices. |
| `--human` | false | Local Human credential for an actual Human action; otherwise delegated actor environment credentials. |

`workflow create` shares `--root`/`--human`, without `--run`. Database commands share only `--root`. The installer has its own options.

Runtime output is generally JSON. Catalog output uses terminal tables/messages; `workflow render` emits Markdown; `db up` can print Docker output before JSON. Do not assume all stdout is pure JSON. Handled runtime failures generally exit `1`, parsing failures `2`. Some malformed requests/provider errors can still surface as Python exceptions.

### Command index

| Family | Commands |
|---|---|
| Root (3) | [`init`](#spado-init), [`status`](#spado-status), [`review`](#spado-review) |
| Workflow (7) | [`create`](#spado-workflow-create), [`context`](#spado-workflow-context), [`prepare`](#spado-workflow-prepare), [`record`](#spado-workflow-record), [`export`](#spado-workflow-export), [`validate`](#spado-workflow-validate), [`render`](#spado-workflow-render) |
| Actor (1) | [`create`](#spado-actor-create) |
| Database (3) | [`up`](#spado-db-up), [`down`](#spado-db-down), [`migrate`](#spado-db-migrate) |
| Documents (4) | [`sync`](#spado-docs-sync), [`promote`](#spado-docs-promote), [`index`](#spado-docs-index), [`search`](#spado-docs-search) |
| Catalog (10) | [`list`](#spado-catalog-list), [`validate`](#spado-catalog-validate), [`remove`](#spado-catalog-remove), [`add skill`](#spado-catalog-add-skill), [`add agent`](#spado-catalog-add-agent), [`add script`](#spado-catalog-add-script), [`add hook`](#spado-catalog-add-hook), [`add mcp`](#spado-catalog-add-mcp), [`group create`](#spado-catalog-group-create), [`group defaults`](#spado-catalog-group-defaults) |

### spado init

Install organization/host resources and optional capabilities. Requires filesystem access; no database connection or actor credential. Does not start agents.

```text
spado init [OPTIONS]
```

| Option | Default | Meaning / constraints |
|---|---|---|
| `--root PATH` | `.` | Existing product directory. |
| `--host HOST` | unset | Repeatable `claude` or `codex`; required for fresh setup and capability-only installation. |
| `--mode MODE` | unset | One of the four modes; required for fresh workflow setup. |
| `--embeddings BACKEND` | unset | `local` or `external`; required for fresh workflow setup. |
| `--embedding-model MODEL` | unset | Required for fresh workflow setup. |
| `--embedding-endpoint URL` | `https://api.openai.com/v1/embeddings` | External endpoint; update caveats below. |
| `--catalog PATH` | installed tool catalog | Root containing workflows, organizations and capabilities. |
| `--database-port INTEGER` | `55432` | `1024..65535`; applied only on initial workflow setup. |
| `--capability TYPE:ID` | none | Repeatable; dependencies and compatibility checked for all selected hosts. |
| `--category CATEGORY` | none | Repeatable; with `--no-workflow` only. Adds every [category](#capability-categories) member compatible with all selected hosts. Requires `--host`. |
| `--workflow` / `--no-workflow` | `--workflow` | SPDLC or capabilities only. Capability-only needs `--host` plus `--capability`/`--category`, or an interactive terminal, where omitting both opens the [picker](#interactive-picker). Workflow-specific flags have no effect in that route. |
| `--dry-run` | false | Render, check conflicts and preview; no writes. |

Existing workflow setup retains omitted settings. Explicit host/capability lists replace configured selection but do not remove old files. Mode changes affect the project default, not stored runs. Embedding/model changes use the supplied endpoint or its default; an endpoint-only update is ignored. Repeat a custom endpoint when updating a model/backend.

**Effects/output:** managed resources, installation hashes, local DB configuration/password; JSON `writes`, `unchanged`, and workflow setup `next`. Edited/conflicting files block installation; no `--force` option exists.

```bash
spado init --host claude --mode auto --embeddings external --embedding-model MODEL_ID --dry-run
spado init --no-workflow --host codex --capability mcp:github --dry-run
spado init --no-workflow --host claude --category backend --dry-run
spado init --no-workflow                     # interactive picker in a terminal
```

**Errors:** missing setup fields/root, invalid mode/provider/host/category, `--category` without `--no-workflow` or `--host`, capability-only setup with nothing selected outside a terminal, picker cancelled, unsupported capabilities, dependency conflicts, edited managed files. See [updates](#updates-and-maintenance).

### spado status

Read last recorded state. **Human/CAOAO** for a selected run; accepts all shared runtime options. No additional arguments/options.

```bash
spado status --human
spado status --run RUN_ID --human
```

From your own terminal, use `--human` after `spado db up`; the command does not automatically assume the shell user is the Human. Without `--human`, it requires a delegated actor credential in `SPADO_ACTOR_TOKEN_FILE` or `SPADO_ACTOR_TOKEN`. **Effects/output:** read-only JSON with phase/subphase/activity state and plans, or run choices when zero/multiple runs exist. No live-process heartbeat. **Errors:** missing credentials/config, unavailable DB, unauthorized actor or unknown run.

### spado review

Structural consistency review. Coordinators can review all; officers/specialists must restrict the target to their delegated scope. All shared runtime options apply.

```text
spado review [TARGET] [IDENTIFIER] [--run ID] [--root PATH] [--human]
```

| Argument | Default | Meaning |
|---|---|---|
| `TARGET` | `all` | `all`, `phase`, `subphase`, `activity`. |
| `IDENTIFIER` | unset | Required except for `all`; phase/subphase slug or numeric ID, or activity UUID. Omit for `all`. |

```bash
spado review all --run RUN_ID --human
spado review phase definition-design --run RUN_ID --human
spado review phase 3 --run RUN_ID --human          # same phase by numeric ID
spado review subphase ui-design --run RUN_ID --human
spado review subphase 3.5 --run RUN_ID --human     # same subphase by numeric ID
spado review activity ACTIVITY_ID --run RUN_ID --human
```

**Effects/output:** read-only findings, including changed files, and `persisted: false`. No sync/fixes. Semantic correctness requires responsible agents to inspect content. **Errors:** invalid target, missing/unknown ID, out-of-scope access.

### spado workflow create

Create a run and pin workflow/organization definitions. Normal entry is a **direct Human action** after setup/DB startup. Does not run agents.

```text
spado workflow create --objective TEXT [--phase SLUG_OR_ID | --subphase SLUG_OR_ID] [--mode MODE] [--root PATH] [--human]
```

| Option | Default | Meaning |
|---|---|---|
| `--objective TEXT` | required | Product/work objective. |
| `--phase SLUG_OR_ID` | unset | One-phase scope, for example `definition-design` or `3`. |
| `--subphase SLUG_OR_ID` | unset | One-subphase scope, for example `ui-design` or `3.5`; exclusive with `--phase`. |
| `--mode MODE` | project default | Four-mode selection. |
| `--root PATH` | `.` | Configured project. |
| `--human` | false | Local Human credential; otherwise coordinator authorization required. |

```bash
spado workflow create --objective "Choose a product opportunity" --subphase initial-ideation --mode semi-auto --human
spado workflow create --objective "Design the product" --phase definition-design --mode auto --human
spado workflow create --objective "Design the product" --phase 3 --mode auto --human
```

The last two commands use equivalent phase selectors; each invocation still creates a separate run. List available phase and subphase slugs in a configured product with `spado workflow validate --catalog .spado/catalog`, or the bundled tool catalog with `spado workflow validate`. Slugs are unique within each scope type and resolve to numeric IDs in persisted runs and events. Existing numeric IDs and earlier full-title subphase slugs still work. Runs pin their catalog snapshot: existing runs keep their original definitions, while newly created runs use the current slug list. Older snapshots also accept title-based names such as `definition-design` and `initial-ideation`.

**Effects/output:** run plus initial event, returning `{"run": "…"}`. No scope means full workflow. No `--run`/`--new-run` CLI options: every successful creation makes a new run. **Errors:** invalid/incompatible scopes, missing configuration/credentials, unavailable DB.

### spado workflow context

Read pinned definitions, roles, modes, dependencies, revisions and plans visible to the actor. All shared runtime options plus:

| Option | Default | Meaning |
|---|---|---|
| `--phase SLUG_OR_ID` | unset | Phase filter, for example `definition-design` or `3`. |
| `--subphase SLUG_OR_ID` | unset | Subphase filter, for example `ui-design` or `3.5`; exclusive with phase. |
| `--activity ID` | unset | Select that activity's subphase, possibly including its other instances; exclusive with either other selector. |

```bash
spado workflow context --run RUN_ID --subphase initial-ideation --human
spado workflow context --run RUN_ID --phase definition-design --human
spado workflow context --run RUN_ID --phase 3 --human
```

**Effects/output:** read-only JSON with `run_version`, briefs, deliverables, criteria and missing inputs. No selector means workflow view filtered by actor scope. Reading definitions beyond a run's execution scope does not expand that scope. **Errors:** incompatible/unknown selectors, explicit access beyond delegation.

### spado workflow prepare

Create/resume an activity through **CAOAO/Human**. All shared runtime options plus **required `--request FILE`** containing a `prepare` JSON event.

```bash
spado workflow prepare --run RUN_ID --request prepare.json
```

**Effects/output:** records event, returns activity ID/state and new activity missing dependencies. A prior unaccepted activity resumes unless payload `new_instance` is set; resending `prepare` does not revise its plan. Owner must be a registered specialist in this run/subphase. See the [valid walkthrough](docs/manual/first-run.md#advanced-terminal-walkthrough).

**Errors:** wrong event kind, invalid plan, unregistered owner, out-of-scope target, missing advance reason or retirement authorization. Shares pre-write sync behavior with `record` below.

### spado workflow record

Submit one authenticated event; authority depends on kind. All shared runtime options plus **required `--request FILE`**.

```bash
spado workflow record --run RUN_ID --request decision.json
```

**Effects/output:** event/state update and `run_version`. JSON needs `event_id`, `kind`, `payload`, nonempty `rationale`, optional `expected_version`. Retry identical content with the same ID/identity; changed content needs a new ID. See the [event reference](#event-reference).

Before non-document events, changed tracked files visible to the actor are synchronized. Those sync events can persist even if the requested transition then fails: the whole CLI call is not one transaction. Re-read context after failure. Queries never perform this sync.

**Errors:** stale plan/version, missing gates/evidence, unauthorized actor, missing tracked file, changed inputs outside scope or ID reused with different content. Approve/start/accept/mode are event kinds, not separate CLI commands.

### spado workflow export

Export a run and its event history. **Human/CAOAO**; all shared runtime options, no extra arguments.

```bash
spado workflow export --run RUN_ID --human > run-export.json
```

**Effects/output:** read-only `{run, events}` including document revision content; shell redirection writes the file. Not a database backup: omits credentials and embedding index. No import command exists. **Errors:** invalid run/selection, insufficient authority, DB errors.

### spado workflow validate

Validate canonical SPDLC definitions, roles, skill/brief files and dependencies. No project identity/DB. Only command-specific option: **`--catalog PATH`**, default installed tool catalog root.

```bash
spado workflow validate --catalog ~/tools/spado/catalog
```

**Effects/output:** read-only JSON counts and complete `phase_slugs` and `subphase_slugs` maps from numeric ID to slug (currently 7 phases, 62 subphases, 72 organization agents). **Errors:** missing files, inconsistent IDs/references, dependency cycles. Validates definitions, not execution completion.

### spado workflow render

Render canonical rules/briefs as Markdown. No project identity/DB. Only command-specific option: **`--catalog PATH`**, default installed tool catalog.

```bash
spado workflow render --catalog ~/tools/spado/catalog
# Maintainer operation from the SPADO checkout:
spado workflow render --catalog catalog > catalog/workflows/Full_SPDLC_Workflow.md
```

**Effects/output:** prints Markdown; shell redirection replaces the file. Does not install host resources or update runs. **Errors:** invalid/missing canonical definitions.

### spado actor create

Delegate an identity using required positional **`DEFINITION`**, a case-sensitive organization ID, and all shared runtime options.

```bash
spado actor create CAOAO --run RUN_ID --human
# In CAOAO's session with its credential:
spado actor create CPAO --run RUN_ID
```

**Effects/output:** scoped actor, delegation event and private `.spado/local/actors/UUID.token`; returns `actor` and absolute `token_file`, never the token. Does not launch an agent.

Only Human delegates CAOAO. CAOAO delegates officers/specialists; officers delegate specialists within their domain; specialists cannot delegate. Human can also delegate domain identities directly, although normal orchestration goes through CAOAO. Discover specialist IDs in context. **Errors:** unknown definition, run/scope violation. Pass each token only to its assigned session.

### spado db up

Start project Compose PostgreSQL/pgvector, wait, initialize schema and create the Human token file if absent. Only command-specific option: **`--root PATH`**, default `.`. Requires workflow setup and running Docker/Compose, no actor token.

```bash
spado db up --root ~/projects/my-product
```

**Effects/output:** creates/uses the project's named volume; Docker output then `database: ready` and credential path. **Errors:** port collision, Docker startup or DB connection failure. An external DSN does not disable the Compose startup; see configuration.

### spado db down

Stop/remove project containers/network while retaining the named volume. Only command-specific option: **`--root PATH`**, default `.`. Requires project config/Docker, no actor token.

```bash
spado db down
```

**Effects/output:** Compose output, no dedicated JSON success object. Normal down/up retains state. **Errors:** missing config/Docker or Compose failure. No reset, volume-deletion or delete-run option is exposed.

### spado db migrate

Initialize/apply the current schema on a reachable configured DB. Only command-specific option: **`--root PATH`**, default `.`. No actor token required.

```bash
spado db migrate
```

**Effects/output:** DDL and `{"schema_version": 1}`. Does not start Docker/create Human token file. Not an arbitrary migration-version runner. **Errors:** missing config or DB access failure.

### spado docs sync

Record a file revision and invalidate affected recorded consumers. All shared runtime options plus:

| Argument/option | Default | Meaning |
|---|---|---|
| `PATH` | required | Existing project-relative `.md`, `.txt`, `.rst`, `.json`; no outside paths or `.spado/local`. |
| `--subphase SLUG_OR_ID` | unset | Subphase attribution, for example `initial-ideation` or `1.1`. Omit for general context. |
| `--depends REVISION_ID` | none | Repeatable consumed revision IDs, not paths. |

```bash
spado docs sync docs/vision.md --run RUN_ID --human
spado docs sync docs/opportunity.md --subphase initial-ideation --run RUN_ID
```

**Effects/output:** reads file, records content/hash, returns revision and affected consumers; unchanged latest content reuses its revision without updating dependency metadata alone. Does not edit/promote files. Human/CAOAO coordinate; officers are scoped; a specialist must own a running activity with an approved plan, including bounded work on provisional inputs. **Errors:** forbidden/missing path, invalid dependencies or authority/gates.

### spado docs promote

Make required positional **`REVISION`** the official version of its path. All shared runtime options.

```bash
spado docs promote REVISION_ID --run RUN_ID --human
```

**Effects/output:** updates official metadata, reports affected consumers; no file overwrite/restore. Human/CAOAO promote accepted activity outputs; only Human can attest initial external/general documents. Latest candidate must match the file on disk. **Errors:** unaccepted output, stale candidate, modified file, insufficient authority. Old official content stays official until successful promotion.

### spado docs index

Encode approved official revisions and write the semantic index. **Human/CAOAO**, all shared runtime options, no extras.

```bash
spado docs index --run RUN_ID --human
```

**Effects/output:** embedding writes, `indexed_chunks` and model identity. May download the local model/call the provider. Changing provider/model selects a different index identity; index again. **Errors:** missing dependencies/API key, provider/DB failure. Partial indexing can persist; rerun after resolving the cause.

### spado docs search

Search official approved revisions with required positional **`QUERY`**. Any authenticated actor in the run; all shared runtime options.

```bash
spado docs search "What problem are we investigating?" --run RUN_ID --human
```

**Effects/output:** no project/execution/index writes; query encoding can contact the provider or populate a local model cache. Up to five chunks with path/revision/digest/distance and `index_complete`; **no `--limit` CLI flag**. Drafts excluded. **Errors:** missing embedding setup, provider/DB failure. An incomplete index can explain empty results.

### Catalog conventions and shared authoring options

Catalog commands affect reusable source resources, not installed projects; no identity/DB, commit or push. `list`/`validate` use local `catalog` or fall back to the installed tool catalog if absent. Mutating commands default to local `catalog` **without fallback**; use explicit `--catalog` outside the source checkout.

All five `catalog add` commands accept these options:

| Option | Default | Meaning |
|---|---|---|
| `--catalog PATH` | `catalog` | Writable source catalog. |
| `--id ID` | inferred | Identifier; unique across types. |
| `--name TEXT` | inferred | Display name. |
| `--description TEXT`, `-d TEXT` | input/derived | Description override; may prompt if omitted. |
| `--category CATEGORIES` | none; interactive omission asks | Comma-separated [categories](#capability-categories) used by the `init` picker and `--category`. |
| `--default` / `--no-default` | unset; false noninteractively | Default-selection metadata; interactive omission asks. Current `init` selects explicitly. |
| `--type TYPES` | none | Comma-separated `backend`, `frontend`, `fullstack`, `ai`, `cli`, `library`, `data_ml`, `other`. |
| `--tech TECHNOLOGIES` | none | Comma-separated technology recommendations. |
| `--depends TYPE:ID` | none | Repeatable dependencies. |
| `--conflicts TYPE:ID` | none | Repeatable conflicts. |
| `--group FAMILY` | none | Capability family; grouped agents get a family target path. |
| `--group-default TYPES` | none | Comma-separated family-default project types; requires `--group`. |
| `--force` | false | Replace an existing capability of the same reference. |
| `--yes`, `-y` | false | Use defaults without questions. Non-TTY catalog authoring also uses defaults. |

Adds validate and write manifest/payload and applicable family metadata. Output is a tree and suggested Git command, not an automatic commit. Common errors: duplicate IDs, invalid frontmatter, unsafe paths, literal secrets, invalid references/conflicts. There is no `--hosts` option: review and explicitly edit `spado.json` compatibility. Default is Claude; declaring Codex does not make unsupported payloads renderable.

### spado catalog list

List capabilities and canonical workflows/organizations. Only command-specific option: **`--catalog PATH`**, default/fallback above.

```bash
spado catalog list --catalog ~/tools/spado/catalog
```

**Effects/output:** read-only table with references/categories/defaults/recommendations/dependencies, then workflow/organization summaries. Currently the `Group` column displays capability names; use family metadata for membership. **Errors:** malformed catalog/workflow definitions.

### spado catalog validate

Validate manifests, payloads, references and canonical workflows. Only command-specific option: **`--catalog PATH`**.

```bash
spado catalog validate --catalog ~/tools/spado/catalog
```

**Effects/output:** read-only success counts/errors. Currently 449 modular capabilities; 72 organization agents are a separate set. Validation does not launch agents/test MCP connectivity. **Errors:** invalid manifests/payloads/dependencies or workflow definitions.

### spado catalog remove

Remove a source capability, not installed copies.

| Argument/option | Default | Meaning |
|---|---|---|
| `REF` | required | `TYPE:ID`. |
| `--catalog PATH` | `catalog` | Source catalog. |
| `--force` | false | Remove even with dependents; here the shared help wording about replacement is misleading. |
| `--yes`, `-y` | false | Skip confirmation. Non-TTY also skips prompts. |

```bash
spado catalog remove skill:my-example --catalog ~/tools/spado/catalog
```

**Effects/output:** deletes folder, updates family defaults, removes an empty family when its final member is removed; prints path. **Errors:** missing reference or dependents without force. Forced removal can leave the catalog invalid; validate afterward.

### spado catalog add skill

```text
spado catalog add skill PATH [SHARED AUTHORING OPTIONS] [--ref FILE] [--script FILE] [--exclude PATTERN]
```

Required `PATH`: `SKILL.md` or containing folder. Additional repeatable options, default none: `--ref FILE` copies references, `--script FILE` copies helpers, `--exclude PATTERN` omits matching folder-import content. All shared authoring options apply.

```bash
spado catalog add skill ./my-skill --id my-skill --category backend,testing --exclude test --yes
```

**Effects/output:** skill manifest/payload and tree. Skills use `allowed-tools:`; agent-style `tools:` triggers an interactive conversion/agent choice or a noninteractive error. **Errors:** missing SKILL.md, invalid frontmatter or shared authoring errors.

### spado catalog add agent

```text
spado catalog add agent PATH [SHARED AUTHORING OPTIONS] [--script FILE]
```

Required `PATH`: agent Markdown with name/description, `tools:` and optional `model:` frontmatter. Repeatable `--script FILE`, default none, copies helpers to `.claude/scripts/ID/`. All shared authoring options apply.

```bash
spado catalog add agent ./research-agent.md --group research-agents --group-default backend --yes
```

**Effects/output:** manifest/agent/helpers/family metadata and tree. This is a modular agent, not a new SPDLC officer. **Errors:** missing file/frontmatter or shared authoring errors.

### spado catalog add script

```text
spado catalog add script FILES... [SHARED AUTHORING OPTIONS]
```

One or more positional files required; no extra options beyond shared authoring options.

```bash
spado catalog add script ./check.sh ./check-helper.py --id my-check --description "Local checks" --yes
```

**Effects/output:** manifest/payload targeting project `scripts/`, then tree; does not execute scripts. **Errors:** missing files, unsafe/colliding paths, shared authoring errors.

### spado catalog add hook

```text
spado catalog add hook SCRIPT --event EVENT [SHARED AUTHORING OPTIONS] [--matcher TEXT] [--timeout SECONDS] [--file FILE]
```

| Argument/option | Default | Meaning |
|---|---|---|
| `SCRIPT` | required | Hook script consuming hook JSON on stdin. |
| `--event EVENT` | required | `PreToolUse`, `PostToolUse`, `UserPromptSubmit`, `Stop`, `SubagentStop`, `SessionStart`, `SessionEnd`, `Notification`, `PreCompact`. |
| `--matcher TEXT` | unset | Tool matcher for applicable events. |
| `--timeout SECONDS` | `30` | Hook timeout. |
| `--file FILE` | none | Repeatable support files. |

All shared authoring options apply. Event names reflect this builder, not a claim about every future host event.

```bash
spado catalog add hook ./check-edit.py --event PostToolUse --matcher 'Edit|Write' --timeout 20 --yes
```

**Effects/output:** Claude hook payload/settings fragment and tree. **Errors:** unsupported event/invalid script or shared authoring errors. Current adapter does not translate Claude hooks/settings to Codex.

### spado catalog add mcp

```text
spado catalog add mcp SERVER [SHARED AUTHORING OPTIONS] (--url URL | --command EXECUTABLE) [MCP OPTIONS]
```

| Argument/option | Default | Meaning |
|---|---|---|
| `SERVER` | required | Server configuration name. |
| `--url URL` | unset | Remote endpoint; exactly one of URL/command required. |
| `--header KEY=VALUE` | none | Repeatable remote headers; quote `${VAR}` literally. |
| `--transport TYPE` | `http` | `http` or `sse` for remote servers. |
| `--command EXECUTABLE` | unset | Local stdio executable. |
| `--arg VALUE` | none | Repeatable executable arguments; `--arg=--flag` passes a leading-dash value. |
| `--env NAME` | none | Repeatable required environment variable names. |

All shared authoring options apply.

```bash
spado catalog add mcp example --url https://example.com/mcp \
  --header 'Authorization=Bearer ${EXAMPLE_TOKEN}' --env EXAMPLE_TOKEN --yes
```

The URL is illustrative, not a live service. **Effects/output:** manifest/MCP fragment and tree; no connection attempt. **Errors:** literal credentials, malformed header pairs, both/neither mechanisms. Use `http`/`sse`: the builder does not currently enforce transport choices. Codex installation additionally requires declared compatibility and supported interpolation.

### spado catalog group create

```text
spado catalog group create TYPE GROUP [--name TEXT] [--description TEXT] [--catalog PATH]
```

| Argument/option | Default | Meaning |
|---|---|---|
| `TYPE` | required | `skill`, `agent`, `script`, `hook`, `mcp`. |
| `GROUP` | required | Family ID. |
| `--name TEXT` | inferred | Display name. |
| `--description TEXT`, `-d TEXT` | empty/inferred | Description. |
| `--catalog PATH` | `catalog` | Source catalog. |

```bash
spado catalog group create agent product-agents --name "Product agents"
```

**Effects/output:** ensures family directory/`group.json`, prints `Group ready`. Add members with `--group`. **Errors:** invalid type/ID/path. No force/yes flags exposed.

### spado catalog group defaults

```text
spado catalog group defaults TYPE GROUP PROJECT_TYPE MEMBERS [--catalog PATH]
```

All four positional arguments required. `TYPE` is a capability type, `GROUP` an existing family, `PROJECT_TYPE` exactly one of the eight project types, `MEMBERS` comma-separated member IDs (`''` clears). Only command-specific option: **`--catalog PATH`**, default `catalog`.

```bash
spado catalog group defaults agent development-agents backend debugger,test-automator
spado catalog group defaults agent development-agents backend ''
```

**Effects/output:** replaces that type's family defaults, validates and restores prior metadata on failure; prints selection. No installed-project changes. **Errors:** unknown group/member, invalid/multiple project types.

## Host invocation reference

These are **instructions to installed entry skills**, interpreted by the host agent. They are not additional Typer commands or an independent deterministic command parser. The host translates them into CLI operations and native delegation.

| Purpose | Claude chat | Codex chat |
|---|---|---|
| Full workflow | `/spdlc --mode auto` | `$spdlc --mode auto` |
| Phase by slug | `/spdlc --phase definition-design --mode manual` | `$spdlc --phase definition-design --mode manual` |
| Same phase by ID | `/spdlc --phase 3 --mode manual` | `$spdlc --phase 3 --mode manual` |
| Subphase by slug | `/spdlc --subphase ui-design --mode semi-auto` | `$spdlc --subphase ui-design --mode semi-auto` |
| Same subphase by ID | `/spdlc --subphase 3.5 --mode semi-auto` | `$spdlc --subphase 3.5 --mode semi-auto` |
| Existing activity | `/spdlc --activity ACTIVITY_ID --run RUN_ID` | `$spdlc --activity ACTIVITY_ID --run RUN_ID` |
| Independent run | `/spdlc --new-run --subphase initial-ideation` | `$spdlc --new-run --subphase initial-ideation` |
| State | `/spado --status --run RUN_ID` | `$spado --status --run RUN_ID` |
| Review everything | `/spado --review all --run RUN_ID` | `$spado --review all --run RUN_ID` |
| Review phase | `/spado --review phase definition-design --run RUN_ID` | `$spado --review phase definition-design --run RUN_ID` |
| Review subphase | `/spado --review subphase ui-design --run RUN_ID` | `$spado --review subphase ui-design --run RUN_ID` |
| Review activity | `/spado --review activity ACTIVITY_ID --run RUN_ID` | `$spado --review activity ACTIVITY_ID --run RUN_ID` |
| Discussion only | `/spado --chat --run RUN_ID` | `$spado --chat --run RUN_ID` |

`--phase` and `--subphase` each accept a slug or numeric ID; `definition-design`/`3` and `ui-design`/`3.5` select the same scopes respectively. `spdlc` accepts one target: whole workflow (no selector), `--phase`, `--subphase` or `--activity`. `--mode` uses the four modes; omission follows the configured/run rules. `--run` selects the existing execution; `--new-run` requests an independent execution and needs an objective in your message. Do not combine an existing activity/run selection with a request for a new run. The host should reuse the unambiguous conversation run unless explicitly asked to create another.

For discussion, name the phase/subphase/activity in ordinary text after `--chat`. You can move between topics without writing anything. `spado` consultation must not create runs, sync/index documents, approve plans, write files/events or change external systems. Request execution explicitly through `spdlc` when ready.

Terminal equivalents differ: use `spado status`, **not** `spado --status`; `spado review phase 3`, **not** `spado --review phase 3`. There is no terminal `spado --chat`. The host's chat route reads `workflow context` and discusses it. `--root PATH` belongs to the underlying CLI commands when a different project needs explicit selection.

The optional `/kickoff`, `/project-discovery`, `/feature-spec` and `/feature-workflow` skills are standalone catalog capabilities described in the [capability chapter](docs/manual/capabilities.md). They are not SPDLC phases and are available only when installed. Third-party skills and native host commands have their own documentation; they are not additional SPADO CLI commands.

## Agent recording and event reference

### Identity and script interface

Human shell actions use `--human`. Agents use a delegated token, normally through `SPADO_ACTOR_TOKEN_FILE`:

```bash
export SPADO_ACTOR_TOKEN_FILE='/absolute/path/returned/by/actor-create.token'
spado workflow context --run RUN_ID --subphase initial-ideation
```

This path is a placeholder. If `SPADO_ACTOR_TOKEN` is also set, its nonempty value takes precedence. Never print tokens or use `--human` to bypass an agent's authority. A role name in a request does not authenticate an officer. These are application permissions, not an OS sandbox against the machine/database administrator.

The installed facade is `.spado/tools/agent-record.py`. Run it using **a Python interpreter with SPADO installed**, not an arbitrary product Python:

```text
SPADO_PYTHON .spado/tools/agent-record.py record --run RUN_ID --request FILE [--root PATH]
SPADO_PYTHON .spado/tools/agent-record.py status --run RUN_ID [--root PATH]
```

`SPADO_PYTHON` above denotes an interpreter path, not a command shipped by SPADO. For an editable `uv tool` installation, determine it with `uv tool dir`, then use the `spado/bin/python` inside that directory. For example, from a configured product on a POSIX shell:

```bash
spado_python="$(uv tool dir)/spado/bin/python"
"$spado_python" .spado/tools/agent-record.py status --run RUN_ID
```

| Parameter | Default / rule |
|---|---|
| `record` or `status` | Required positional operation. |
| `--run ID` | Required for both. |
| `--root PATH` | `.`; configured product root. |
| `--request FILE` | Required for `record`; omit for `status`. |
| `--help`, `-h` | Argparse usage. |

No `--human` script flag exists. Always omit `--request` for `status` and provide a nonempty request object for `record`: the current facade dispatches by request content, so `status --request FILE` can incorrectly call the write handler. This is listed as a current limit in the [implementation notes](docs/manual/implementation.md#current-limits). `record` uses the same services/permissions as `workflow record`; `status` requires CAOAO/coordinator authority. JSON success is the service result. Handled service failures report `persisted: false`, `pending` (record) or `unavailable` (status), error type and event ID, exiting `1`. This is not a durable retry queue. Retain the request and retry explicitly; a preceding automatic file sync may already have persisted. Malformed JSON can fail before the facade's handler.

The Python functions `record(root, run_id, request)` and `read_status(root, run_id)` expose the same operations. The detailed contract is in [the source protocol](src/spado/runtime/protocol.md), installed as `.spado/protocol.md`.

### Request format

```json
{
  "event_id": "15fab421-b404-4fb6-afc0-a328139d91d2",
  "kind": "note",
  "payload": {
    "category": "decision",
    "message": "Assess one opportunity before expanding the scope."
  },
  "rationale": "Keep the initial investigation bounded."
}
```

Save as `decision.json`, then submit with CAOAO's credential using `spado workflow record --run RUN_ID --request decision.json`. Generate a fresh UUID for a new event; keep it for identical retries. Optional `expected_version` asserts the current run version from context. If the version has changed, inspect current context before constructing a revised request.

### Event reference

All writes below use `workflow record --request FILE` (or the facade), except where a convenience command is noted. Payload names are JSON keys; `plan` has the common structure below. Event actors must also belong to the correct project/run/scope.

| Kind | Payload | Authority and effect |
|---|---|---|
| `phase_plan` | `phase`, `plan`, optional `mode` | Human/CAOAO: version a phase plan, auto-validate in agentic/auto. |
| `phase_approve` | `phase`, `plan_id`, `version` | Human in manual/semi-auto; otherwise Human/CAOAO. |
| `prepare` | `subphase`, `owner`, `plan`; optional `mode`, `reason`, `new_instance` | Human/CAOAO; owner is delegated specialist UUID. `workflow prepare` wrapper available. |
| `revise_plan` | `activity`, `plan` | Human/CAOAO; replaces plan, clears result reviews and reapplies mode gate. |
| `approve_plan` | `activity`, `plan_id`, `version`; `arrangement` in manual | Human in manual/semi-auto; otherwise Human/CAOAO. Manual arrangement: `human`, `assisted`, `delegated`. |
| `start` | `activity` | Assigned executor or coordinator; checks activity/phase plans and inputs. |
| `deliver` | `activity`, `outputs`, `criteria_evidence` | Executor/coordinator; outputs are revision IDs, evidence maps each criterion to evidence. |
| `domain_review` | `activity`, `decision`, `evidence` | Responsible officer in its own identity; `approved` or `changes_requested`. |
| `human_review` | `activity`, `decision`, `evidence` | Human result review; same decision values. Required by manual mode. |
| `accept` | `activity` | Human/CAOAO; requires current inputs, criteria and all applicable reviews. |
| `block` | `activity`, `reason` | Assigned participant; records blocked work. |
| `document` | `path`, `content`; optional `subphase`, `dependencies` | Authorized participant; prefer `docs sync` to read actual file content. |
| `promote` | `revision` | Human/CAOAO for accepted outputs; Human attests initial external context. Prefer `docs promote`. |
| `external_input` | `subphase`, `revision`, `evidence` | Responsible officer/Human: attest current official evidence as satisfying that upstream subphase's input contribution. |
| `not_applicable` | `subphase`, `reason` | Every responsible officer must approve; only conditional subphases. |
| `close_phase` | `phase` | Coordinator after all work accepted/N/A and plan valid; Human required in manual. |
| `retirement` | `evidence` | CEAO: authorize SPDLC retirement where run scope permits. |
| `mode` | `mode`; optional `phase`, `subphase` or `activity` | Human direction only; use at most one target. No target updates run default. |
| `note` | `category`, `message`; optional `activity` or `subphase` | Assigned participant; global notes need coordinator. Categories: `question`, `decision`, `execution`, `handoff`, `human_question`. Agentic disallows `human_question`. |

`run_created` and `delegation` are recorded by `workflow create` and `actor create`, not submitted as ordinary transition kinds.

An activity plan contains `objective`, exact canonical `deliverable`, nonempty `actions`, `criteria` including the canonical exit criterion, and `inputs` mapping revision UUIDs to SHA-256 hashes. Supply `assumptions` for missing inputs. Read context first; do not invent revision IDs, criteria evidence or completed work. SPADO assigns plan identity/version/approval. Phase plans have the same structure with a phase-level target; explicit `reused_activities` identifies accepted activities from previous cycles.

Revised input evidence can invalidate approvals and consumers. The system can only assess relationships it records; describe actual consumed revisions and ask responsible officers to review semantic effects. See the [advanced example](docs/manual/first-run.md#advanced-terminal-walkthrough).

## Configuration and environment

The generated `.spado/project.json` contains:

| Field | Meaning |
|---|---|
| `schema_version` | Currently `1`. |
| `project` | Generated project UUID; identity boundary, not a display label to casually rename. |
| `hosts` | `claude`/`codex` list. |
| `mode` | Default for new runs. |
| `workflow` | Currently `spdlc`; another name alone does not install another workflow. |
| `capabilities` | Explicit optional capability references. |
| `database_port` | Local database port, default `55432`. |
| `embeddings.backend`, `.model`, `.endpoint` | Provider/model configuration; local or external. |
| `embeddings.key_env` | External credential variable, default `SPADO_EMBEDDING_API_KEY`; no dedicated CLI flag. |

Prefer supported `init` updates to manual edits: configuration files are tracked by installation hashes, so manual changes can trigger conflicts on a later installation. Existing run snapshots remain pinned.

| Environment variable | Used by / precedence |
|---|---|
| `SPADO_ACTOR_TOKEN_FILE` | Path to delegated actor credential. Used when direct token is absent/empty. |
| `SPADO_ACTOR_TOKEN` | Direct actor token; a nonempty value overrides the file variable. |
| `SPADO_EMBEDDING_API_KEY` | Default external embedding credential; `key_env` can select a different variable. |
| `SPADO_DATABASE_URL` | Overrides generated local DSN for state services. |
| Capability-specific names, e.g. `GITHUB_TOKEN` | MCP/tool requirements from selected manifests; not a universal SPADO credential. |
| `SPADO_POSTGRES_TEST=1` | Maintainer-only switch for Docker integration tests; not runtime setup. |

`--human` uses `.spado/local/human.token` instead of agent environment credentials. The fallback DSN uses localhost, project port, database/user `spado` and `.spado/local/database.password`. External embedding endpoints must use HTTPS, except local HTTP on `localhost`/`127.0.0.1`; the adapter still requires its configured key variable.

`SPADO_DATABASE_URL` is an advanced connection override, **not a complete managed remote-DB mode**. `db up` still starts the local Compose service and `db down` still stops that local service. `db migrate` and state services use the override. Provision/bootstrap a remote database deliberately; do not assume local volume lifecycle commands control it.

Keep `.spado/local/` private and untracked. Generated `.spado/.gitignore` excludes local data/backups. Versionable project configuration/resources are separate from private credentials and database contents.

## Updates and maintenance

### Tool, installed resources and run snapshots

These are three distinct update layers:

1. **Tool:** pull your permanent checkout. Editable Python source changes take effect; reinstall when dependencies/entry points/extras change.
2. **Project resources:** preview and repeat `spado init` to install current resources, including selected standalone capabilities.
3. **Runs:** existing executions retain their workflow/organization snapshots. New runs use the installed definitions; there is no automatic run migration.

```bash
git -C ~/tools/spado pull
uv tool install --force -e "$HOME/tools/spado[local-embeddings]"
cd ~/projects/my-product
spado init --dry-run
# After inspecting the proposed changes:
spado init
```

Use the plain package instead of the extra when you use external embeddings. Do not run these project setup commands from the tool checkout by mistake.

An edited managed file causes a conflict. Review its diff and preserve intentional customizations before reconciling it with the expected source. `init` has no force/interactive overwrite switch. Its installation is additive: changing the selected hosts/capabilities does not remove old resource files. Removing a selection from config does not prune previously installed resources.

### Documents and continuation

After editing a tracked product document, run `docs sync`, inspect review findings, revise affected plans and obtain fresh approvals. Promote only the accepted/current revision; index official content after promotion when you need semantic retrieval. Queries alone never perform synchronization.

In a partial run, existing upstream evidence can be supplied as a synchronized and promoted document, then attested through `external_input` by a responsible officer or Human. That records suitability; it does not mark the upstream activity executed. Preserve the distinction in reviews.

### Stop, retain and export

`db down` retains the persistent volume; `db up` returns to it. Keep the associated project configuration/password and actor credentials as well as the database. Deleting the volume or credentials is not an ordinary reset procedure.

`workflow export` is a readable run/event export, not a restore-capable backup. No SPADO backup/restore, credential-recovery, import, uninstall or delete-run command is provided. Use your database administration process if you need a full backup and include the relevant project files/credentials securely.

## Troubleshooting

| Symptom / error | Meaning and action |
|---|---|
| `spado: command not found` | Check the tool installation and PATH; `uv tool update-shell` can configure the tool executable directory. Reopen the shell. |
| Claude Code reports `Unknown command: /spdlc` | Check that the project has `.claude/skills/spdlc/SKILL.md`. If it was configured only for Codex, run `spado init --host codex --host claude` in that project to retain both hosts, then start a new Claude Code session there. Codex's `$spdlc` skill does not install Claude's `/spdlc` skill. |
| `Capability-only setup requires --host and --capability or --category` | You ran `--no-workflow` without a selection outside an interactive terminal. Pass `--host` with `--capability`/`--category`, or run it in a terminal to open the picker. |
| Missing `.spado/project.json` | You are in the wrong root or used capability-only setup. Configure the organization before runtime commands. |
| `Initial setup requires --host, --mode, --embeddings and --embedding-model` | Workflow setup is non-interactive. Supply all four on the first workflow installation; see the [Codex example](#configure-an-organization-project). Use `--no-workflow` only for capability installation. |
| PostgreSQL operation failed | Check Docker, `spado db up`, project port/password and any DSN override. |
| Port already in use | Give simultaneously active projects distinct ports at initial setup; existing-port updates are currently unsupported by `init`. |
| No Human token | Complete `db up`; do not substitute an agent token. Lost credentials on an existing DB need deliberate recovery, not assumed rebootstrap. |
| `Set SPADO_ACTOR_TOKEN_FILE ... or use --human` / unauthorized actor | If you ran `spado status` yourself after `spado db up`, use `spado status --human`. Agent sessions need their own delegated token file; `SPADO_ACTOR_TOKEN` overrides the file when nonempty. |
| Select an execution with `--run` | Inspect `spado status --human` and choose the intended run ID. |
| Scope/delegation error | Use the assigned scope/identity; request CAOAO coordination or create a separate run outside current execution scope. |
| Approval targets a stale plan / execution changed | Refresh context; review and approve current plan ID/version. Do not replay stale approval as a new decision. |
| Phase plan required | Full/phase runs require a phase plan before activity execution; independent subphase runs do not. |
| Activity not ready / inputs missing | Inspect status/review, approvals and missing prerequisites. Provisional results cannot be accepted early. |
| Recorded document missing / changed outside scope | Restore the expected file or ask CAOAO to synchronize and revalidate its consumers. |
| Document differs / only accepted outputs can be promoted | Sync the actual file, complete reviews/acceptance and promote its latest revision. |
| Event ID reused with different content | Same ID is only for identical retries under the same identity/run. A changed decision needs a new ID. |
| Facade reports pending/unavailable | Preserve request/ID, resolve failure, inspect context and retry. No background retry queue exists. |
| `No module named spado` from agent-record.py | Use the Python environment containing SPADO, not the product's unrelated interpreter. |
| Missing local embeddings package | Install the extra in the environment that runs the CLI/facade. |
| Missing embedding key / provider failure | Check model, endpoint and key environment. External updates must repeat custom endpoints. |
| Empty search / `index_complete: false` | Promote approved sources and index with the current model. Drafts are excluded. |
| User edits conflict with installation | Review managed-file diffs; reconcile customizations before reinstalling. No `init --force`. |
| Capability incompatible with Codex | Choose compatible resources; unsupported hooks/settings/agent payloads are rejected, not automatically converted. |
| Capability no longer selected but files remain | Current `init` does not prune installations. Review installation ownership before manual reconciliation. |
| ID already used / literal secret detected | Choose a unique capability ID; use quoted `${VAR}` references instead of secret values. |
| Host does not expose installed resources | Check the selected host and generated directories, then reload its project/session. Host discovery and permissions are host responsibilities. |
| MCP does not connect | Supply the selected server's required environment and host permission; catalog validation does not test a connection. |

See [implementation notes](docs/manual/implementation.md) for source evidence and pending limitations. For implementation changes, edit canonical sources and run the checks described in [README](README.MD#development); do not treat the manual as executable agent instructions.
