# Claude Workspace Init (CWI)

An opinionated Claude Code workspace bootstrapper.

> Start with everything available. Finish with only what the project needs.

This repository ships a catalog of reusable Claude Code capabilities: skills, agents, scripts, hooks and MCP servers. Nothing in `catalog/` is active. Running `cwi init` scans the project or asks a few questions, writes a minimal `AGENTS.md` (imported by `CLAUDE.md`), and lets you pick capabilities. It previews every change before applying it, then installs only what you selected.

For a step-by-step guide, see [USAGE.md](USAGE.md).

## Quick start

Install the CLI once, so it survives the template cleanup:

```bash
uv tool install -e /path/to/claude-workspace-init
```

### New project from this template

```bash
git clone <this repo> my-app && cd my-app
cwi init
```

After a successful run the project contains only the Claude workspace:

```text
AGENTS.md              shared instructions for any coding agent (agents.md standard)
docs/                  optional skeleton: architecture + versions, glossary, specs, decisions
CLAUDE.md              @AGENTS.md import + Claude-only notes
.claude/
  settings.json        merged hooks
  cwi-state.json       CWI ownership record (paths, owners, hashes; no secrets)
  skills/<id>/SKILL.md
  agents/<id>.md
  hooks/*.py
  scripts/<agent>/…    only if a selected agent ships helpers
.mcp.json              only if an MCP server was selected
scripts/               only if a project script was selected
```

The catalog, templates, CWI source, tests, packaging files, `USAGE.md` and spec docs are removed. `README.MD` and `.gitignore` stay.

### Existing project

Point CWI at a catalog:

```bash
cd existing-project
cwi init --catalog /path/to/claude-workspace-init/catalog
```

You can also copy `catalog/` into the project. CWI then removes it after a successful run, but only if it still looks like an unmodified CWI catalog.

## Flags

| Flag | Effect |
| --- | --- |
| `--root PATH` | Project to initialize. The default is the current directory, and CWI asks before switching to a git root. |
| `--catalog PATH` | Catalog to source capabilities from. The default is `./catalog`. |
| `--dry-run` | Scan, plan and preview with default answers. Writes nothing. |
| `--yes`, `-y` | Accept every default and apply without prompts. |
| `--verbose`, `-v` | Debug logs and tracebacks. |

Without a TTY and without `--yes`, CWI prints the plan and applies nothing.

## What `cwi init` does

1. **Scan.** It reads manifests only and never executes project code. It detects languages, frameworks, package managers, databases, infrastructure, test tools, commands and existing Claude configuration. Every detection keeps its evidence and a confidence level.
2. **Profile.** For an existing project you confirm, edit or rescan the detected profile. For a new project you answer a few progressive questions.
3. **Instructions.** By default, CWI writes compact Safety, Stack, Commands and Architecture sections to `AGENTS.md`, with no empty sections, and shows an estimated size. `CLAUDE.md` imports it with `@AGENTS.md`, because Claude Code ignores `AGENTS.md` when a `CLAUDE.md` exists. You can choose "CLAUDE.md only" instead. Existing files are never silently overwritten. CWI adds the import line to your `CLAUDE.md`, and for `AGENTS.md` you choose keep, merge, replace or skip.
4. **Select.** You pick Skills, Agents, Scripts, MCP servers and Hooks. Recommendations are deterministic, explained and preselected. Dependencies are confirmed and conflicts always need a choice.
5. **Plan and preview.** CWI builds the full operation list, with diffs for every existing file it would change. Cancelling at this point changes nothing.
6. **Apply.** The apply is transactional, with backups in `.cwi/backups/` and atomic writes. Results are validated before cleanup, and any failure restores the repository.
7. **Clean.** CWI removes only resources it owns. User files are never deleted.

It finishes by pointing you to `claude "/kickoff"`, and can open Claude Code with it already started. `kickoff` then runs `project-discovery`, `feature-spec` and `feature-workflow` in order. See [USAGE.md](USAGE.md#after-cwi-init-run-kickoff-in-claude-code).

Re-running `cwi init` with the same answers produces the same repository state. Modified CWI-managed files are detected by hash and never overwritten without asking.

## Bundled catalog

| Type | ID | Purpose |
| --- | --- | --- |
| Skill | `testing` | Smallest relevant test scope first. Includes a related-test finder script. |
| Skill | `debugging` | Reproduce, isolate, hypothesize, fix, then add a regression test. |
| Skill | `backend-development` | API, persistence and migration conventions, with FastAPI, Django and Express references. |
| Skill | `kickoff` | Selected by default. The entry point in Claude Code: it checks the project state and runs discovery, specs and implementation in order. It is resumable. |
| Skill | `project-discovery` | Selected by default. It is the first step after `cwi init` and defines the architecture: it finds an existing one, analyzes the code, or builds one from your requirements. |
| Skill | `feature-spec` | Turns a request into `docs/specs/<feature>.md` with testable acceptance criteria and open questions. |
| Skill | `feature-workflow` | Implements a feature from its spec: branch, plan, test-first slices, verification, independent review. |
| Skill | `frontend-development` | Component, state and accessibility conventions, with React, Next.js, Vue and Svelte references. |
| Agent | `code-reviewer` | Diff review plus the project's configured quality checks. |
| Agent | `security-reviewer` | Security review plus an offline dependency inventory. |
| Agents | `development-agents/` family, 35 agents | Development, maintenance, review and testing. Each project type preselects a subset. Adapted from davila7/claude-code-templates (MIT). |
| Script | `run-quality-checks` | Runs only the linters, type checkers and tests the project is configured for. |
| Hook | `safety-guard` | Recommended by default. Blocks destructive commands and edits to protected files. |
| Hook | `post-edit-validation` | Recommended by default. Formats and lints only the edited file with the project's own tools. |
| MCP | `github` | GitHub remote MCP server. Requires `GITHUB_TOKEN` in your environment, and CWI never stores it. |

### Safety Guard

The guard parses commands instead of matching raw text. `terraform destroy` is blocked, while `echo "do not run terraform destroy"` is allowed. It covers these areas:

- **Infrastructure and data:** destroy commands, database resets and drops, destructive SQL, volume deletion.
- **Git:** force pushes, `reset --hard`, `clean -f`.
- **Deletion:** `rm -r` on `/`, `~`, `.` or paths outside the project.
- **Protected files:** edits to `.env*`, keys, `.git/` and the guard itself.

Project overrides live in `.claude/safety-guard.json`, which only you can edit:

```json
{
  "protected_paths": ["config/production.yml"],
  "allow_paths": [".env.local"],
  "allow_commands": ["^terraform destroy -target=module\\.scratch"],
  "disabled_rules": ["git-reset-hard"]
}
```

## Adding a capability to the catalog

Use `cwi catalog add`. It writes `cwi.json` and the `payload/` folder for you, validates the whole catalog, and leaves nothing behind if something is wrong. It only edits files under `catalog/`. The new capability reaches the GitHub template when you commit and push it.

| Type | You pass | Optional extras | Where tools go |
| --- | --- | --- | --- |
| Skill | `SKILL.md`, or a folder containing it | `--ref file.md`, `--script file` | `allowed-tools:` in the SKILL.md frontmatter |
| Agent | the agent `.md` file | `--script file` | `tools:` and `model:` in the agent frontmatter |
| Hook | the hook script | `--event`, `--matcher`, `--timeout` | not applicable |
| Script | the script file(s) | none | not applicable |
| MCP | the server name | `--url` with `--header`, or `--command` with `--arg`, and `--env` | secrets always as `${VAR}` |

```bash
cwi catalog add skill path/to/SKILL.md --ref docs/rest.md --type backend,fullstack --tech fastapi
cwi catalog add skill path/to/my-skill/            # folder with SKILL.md, references/, scripts/
cwi catalog add agent path/to/dba.md --script explain.py --depends script:run-quality-checks
cwi catalog add hook  block-prod.sh --event PreToolUse --matcher Bash -d "Blocks prod deploys"
cwi catalog add script seed.sh -d "Seeds development data"
cwi catalog add mcp linear --url https://mcp.linear.app/mcp --header 'Authorization=Bearer ${LINEAR_TOKEN}'
cwi catalog list
cwi catalog validate
cwi catalog remove skill:debugging
```

Common options:

- `--default` preselects the capability in every project.
- `--type` and `--tech` recommend it only for matching projects.
- `--id` and `--description` override what is read from the file.
- `--force` replaces an existing capability with the same reference.
- `--group <family>` stores it in a family folder such as `catalog/agents/development-agents/<id>/`. Grouped agents install into `.claude/agents/<family>/`.
- `--group-default backend,fullstack` preselects it for those project types through the family's `group.json`. Edit the per-type lists with `cwi catalog group defaults`.

Without `--yes`, the command asks for anything missing. A file with `tools:` in its frontmatter is an agent, so `add skill` refuses it and suggests `add agent`.

Commit the result to ship it:

```bash
git add catalog/skills/my-skill && git commit -m "catalog: add skill:my-skill"
```

## Development

```bash
uv sync
uv run pytest
uv run ruff check . && uv run ruff format --check .
uv run cwi init --dry-run
```

The code lives in `src/cwi/`, split by responsibility:

- `scanner/` reads the project and never prints.
- `planning/` builds the plan and never prompts.
- `install/` mutates the repository and never decides what to do.
- `ui/` renders screens and asks questions.

Every Claude Code path contract is centralized in `src/cwi/paths.py`.
