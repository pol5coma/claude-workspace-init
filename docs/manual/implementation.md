# Current implementation and limits

[Usage manual](../../USAGE.md) · [Architecture](../../architecture.md) · [Capability catalog](capabilities.md)

This page records the behavior of the current SPADO 0.2.0 implementation. The [CLI](../../src/spado/cli.py) exposes one installer, `spado init`, for Full SPDLC or selected standalone capabilities. The [catalog](../../catalog/) holds canonical definitions; the [runtime installer](../../src/spado/runtime/install.py) writes native host resources and `.spado/installation.json`. Workflow runs use PostgreSQL state and snapshots; the host executes agents. The [Full SPDLC reading copy](../../catalog/workflows/Full_SPDLC_Workflow.md) is generated from canonical workflow files.

## Current limits

| Behavior | Practical consequence |
|---|---|
| Reinitializing an existing workflow project ignores `--database-port`. | Select a free port during initial setup. Changing it later requires deliberate config and Compose reconciliation. |
| Supplying only `--embedding-endpoint` on an existing project does not update it; changing model/backend without repeating a custom endpoint restores the default. | Repeat the custom endpoint whenever changing model or backend. |
| Installation is additive and does not prune deselected resources. | Review managed files before removing them manually. |
| Catalog `list` displays capability names in the Group column. | Inspect group metadata or the catalog path for the actual family. |
| `catalog remove --force` bypasses dependent protection; its shared help text can imply replacement. | Inspect dependents before forcing removal. |
| MCP transport strings are not fully validated during authoring. | Use supported `http`/`sse` values and test connectivity separately. |
| A changed document may be synchronized before a subsequent write transition fails. | Reinspect state after a failed recording request. |
| Synchronizing unchanged document content reuses the revision even if only dependency metadata changed. | Update content or plan the metadata correction explicitly. |
| `SPADO_DATABASE_URL` changes service connections but `db up/down` still operate local Compose. | Manage an external database outside these lifecycle commands. |
| The agent facade currently dispatches by request content rather than the explicit operation. | Use `record` only with a nonempty request object and `status` without `--request`. |
| Some malformed requests and embedding-provider failures may escape the usual JSON error format. | Check process exit status and stderr. |

There is no autonomous agent scheduler, graphical runtime UI, background document watcher, generic workflow selector, automatic run migration, restore/import command or automatic credential recovery. These are future capabilities, not commands in this version. PostgreSQL integration tests require a Docker environment and are opt-in; ordinary tests cover the catalog, installation, workflow engine and CLI without invoking a live coding-agent host.
