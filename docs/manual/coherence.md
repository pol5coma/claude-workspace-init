# CWI to SPADO: repository coherence review

[Usage manual](../../USAGE.md) · [Architecture](../../architecture.md)

This review describes the **0.2.0 checkout**, separating current behavior, historical material and outstanding gaps. It does not claim every host/provider combination has been exercised live. This documentation change does not alter runtime behavior.

## How the product now fits together

SPADO is the package/executable. Its two installation routes share a capability catalog but have separate planners and ownership records:

| Layer | Evidence | Meaning |
|---|---|---|
| Package/CLI | [pyproject.toml](../../pyproject.toml), [registration](../../src/spado/cli.py) | Only `spado` is installed; no `cwi` alias. |
| Modular provisioner | [commands/init.py](../../src/spado/commands/init.py), [planner](../../src/spado/planning/planner.py), [paths](../../src/spado/paths.py) | Exposed as `spado provision`; internal `init` names are inherited. State: `.claude/spado-state.json`. |
| Organization setup | [runtime commands](../../src/spado/runtime/commands.py), [installer](../../src/spado/runtime/install.py) | Exposed as `spado init`; manages project config and `.spado/installation.json`. |
| Canonical definitions | [workflow loader](../../src/spado/workflows/catalog.py) | Reads workflow JSON, rules, briefs, organization and skills, not historical outlines. |
| Execution state | [engine](../../src/spado/workflows/engine.py), [store](../../src/spado/runtime/store.py) | Plans, authority, dependencies, reviews, evidence and transactional events. |
| Host integration | [host renderer](../../src/spado/adapters/hosts.py), [capability renderer](../../src/spado/adapters/capabilities.py) | Installs instructions; the host executes agents. No standalone SPADO scheduler. |

The modular approach and organization model both remain active. Optional skills/MCP can complement an organization or be installed alone. These are not interchangeable ownership/migration systems. Existing CWI installations have no automatic migration; old ignore patterns do not implement migration.

## Canonical, generated and historical material

| Material | Classification / action |
|---|---|
| `catalog/workflows/spdlc/`, `catalog/organizations/spdlc/`, `catalog/organization-skills/` | Current editable execution sources. |
| `catalog/workflows/Full_SPDLC_Workflow.md` | Generated reading copy; matches the canonical renderer in this checkout. |
| Product `.spado/catalog/` | Installed copies, not automatically changed by tool updates. |
| PostgreSQL workflow/organization snapshots | Authoritative versions for existing runs. |
| `catalog/workflows/c-suite-workflow.md`, `catalog/workflows/workflows.md` | Historical designs, explicitly labeled. Old commands, acronyms, modes and envisioned integrations are not current instructions. |
| `catalog/c-suite/*.json` | Earlier organizations, not the current runtime loader's source. |
| Third-party CWI attribution comments | Import/adaptation history; preserve licenses and attribution. |
| `.gitignore` CWI patterns/comments | Historical protection for local files, not an active executable. |
| `claude-workspace-init` directory/clone URL | Historical repository name; package name is independently `spado`. Do not invent a new remote URL by renaming text. |
| Test fixtures mentioning CWI | Historical sample content, including user files that preservation tests retain. |

The catalog validates **423 modular capabilities**, plus SPDLC's **7 phases, 62 subphases and 72 organization agents**. These are different sets; organization agents are not the whole modular agent catalog.

## Documentation inconsistencies resolved here

- `USAGE.md` now covers the full product and all 29 commands/options, rather than only `provision`/`kickoff`.
- Tool installation, project provisioning, run creation and host execution have distinct instructions.
- CLI `spado status` is separated from host `/spado --status` and `$spado --status`.
- Editable update instructions distinguish source changes, dependency installation, project copies and run snapshots.
- Template cleanup is an optional modular operation with an allowlist, not part of every setup route.
- Catalog discovery differences are explicit: runtime setup uses the tool catalog; catalog read commands can fall back to it; `provision` requires local `catalog/` or `--catalog` to offer capabilities.
- `--verbose` is only documented for `provision`.
- Historical designs point to current instructions; historical attribution is retained.

## Functional gaps and operational limits

These remain **pending or explicit v1 limits**; this documentation task does not fix them.

| Finding | Source evidence | Consequence / next engineering work |
|---|---|---|
| Existing-project port updates ignored | `initialize` existing-config branch in [commands](../../src/spado/runtime/commands.py) | Select at initial setup. A supported change must update config and Compose together. |
| Endpoint-only updates ignored; model/backend updates can reset custom endpoint | Same branch | Repeat custom endpoint with model/backend changes. Future logic should distinguish supplied options from defaults. |
| Runtime installation does not prune resources | [installer](../../src/spado/runtime/install.py) retains prior ownership and writes desired files | Selection may differ from files present; future removal must preserve user edits. |
| Installers have independent ownership | [runtime install](../../src/spado/runtime/install.py), [modular state](../../src/spado/state/repository.py) | Overlapping files can conflict; no automatic adoption/migration. |
| Catalog `Group` column contains capability names | `list_capabilities` in [catalog commands](../../src/spado/commands/catalog.py) | Use family metadata; fix the displayed field separately. |
| Remove-force help describes replacement | Shared `ForceOpt` vs [remove](../../src/spado/authoring/writer.py) | For removal, force bypasses dependency protection; help should be command-specific. |
| MCP transport choices are not enforced | [build_mcp](../../src/spado/authoring/builder.py), [validator](../../src/spado/catalog/validator.py) | Use `http`/`sse`; arbitrary strings can reach fragments. Add explicit validation separately. |
| Pre-write sync precedes requested transition in separate transactions | `_sync_changed`/`record_request` in [commands](../../src/spado/runtime/commands.py) | Syncs can persist even if the requested event fails. Inspect state after errors. |
| Same-content document sync ignores metadata-only dependency changes | `document` branch in [engine](../../src/spado/workflows/engine.py) | Same digest reuses the revision; a metadata-only correction path needs separate design. |
| External DSN does not disable Compose lifecycle | [config](../../src/spado/runtime/config.py), DB commands | Connection override is not complete remote-DB provisioning. |
| Facade dispatch uses request truthiness instead of the operation | [agent-record.py](../../catalog/workflows/tools/agent-record.py) `main` | `status --request FILE` with nonempty JSON selects the write handler; `record` with `{}` selects status. Use only the documented valid combinations until dispatch/validation is fixed. |
| Error output is not universally normalized | `guarded`, facade parsing, [embeddings](../../src/spado/runtime/embeddings.py) | Some malformed/provider failures can escape JSON; check exit code/stderr. |
| Supplemental manual outside template-cleanup allowlist | [paths](../../src/spado/paths.py), [cleanup](../../src/spado/planning/cleanup.py) | Template copies retain `docs/manual/`, like other unlisted files. Cleanup behavior was not expanded. |

No graphical runtime UI, scheduler, watcher, terminal chat command, arbitrary workflow selector, restore/import or automatic credential-recovery command is provided. Do not infer these features from historical designs.

## What to do next

1. Keep the tool checkout separate from the product. Choose organization, capability-only or modular setup using the [route table](../../USAGE.md#from-cwi-to-spado).
2. Try the [first-run walkthrough](first-run.md) in a disposable product before applying it to an existing product.
3. Consult the matching command entry before changing state/configuration. Retain run IDs, credentials and database volumes.
4. For authoring, edit canonical sources, validate, regenerate the master and preview installation. README/architecture edits alone do not change agents.

## Validation boundary

Checks cover registered CLI metadata, source behavior, canonical catalog validation, generated-master equality and existing installation/CLI/workflow tests. Request examples are checked against the engine and setup examples in temporary directories, without changing this repository's runtime configuration.

This does not demonstrate a live host-driven lifecycle, MCP service availability, paid embedding calls, local model download or backup recovery. PostgreSQL integration remains an opt-in runtime validation route documented in README.
