# Using CWI

CWI sets up Claude Code for a project in one command. You pick what you need from a catalog of skills, agents, hooks, scripts and MCP servers. CWI installs only those, and the project stays clean.

This guide covers three tasks:

1. [Install CWI](#1-install-cwi) (once per machine)
2. [Set up a project](#2-set-up-a-project) (new or existing)
3. [Add things to the catalog](#3-add-things-to-the-catalog) (for maintainers of this template)

---

## 1. Install CWI

You need [uv](https://docs.astral.sh/uv/) and Python 3.12 or newer.

```bash
git clone <this-repo-url> ~/tools/claude-workspace-init
uv tool install -e ~/tools/claude-workspace-init
cwi --version
```

Install it this way, as a tool. When CWI sets up a project created from this template, it deletes its own source code from that project. The installed `cwi` command keeps working.

---

## 2. Set up a project

### Option A: start a new project from the template

```bash
git clone <this-repo-url> my-app
cd my-app
cwi init
```

### Option B: add Claude Code to an existing project

```bash
cd my-existing-project
cwi init --catalog ~/tools/claude-workspace-init/catalog
```

### What happens next

CWI walks you through a few short screens. Press **Enter** to accept the suggestion on any screen.

| Step | What you see | What to do |
| --- | --- | --- |
| 1. Project | Detected stack, for an existing project. A few questions, for a new project. | Confirm, or edit what is wrong. |
| 2. Instructions | Where the instructions live: `AGENTS.md` plus a `CLAUDE.md` that imports it (recommended), or `CLAUDE.md` only. Then a short proposal with safety rules, stack, commands and an architecture pointer. | Accept, edit the commands, or add a global instruction. |
| 3. Capabilities | Five lists: Skills, Agents, Scripts, MCP and Hooks. Recommended items are already ticked. | **Space** toggles an item and **Enter** continues. |
| 4. Preview | Every file CWI will create, change or delete. | Choose **Apply**, **Review changes** to see diffs, **Back** or **Cancel**. |

Nothing is written before you choose **Apply**. **Cancel** leaves the project exactly as it was.

### What you end up with

```text
my-app/
├── AGENTS.md                 short, project-wide instructions for any coding agent
├── CLAUDE.md                 imports AGENTS.md (@AGENTS.md) + Claude-only notes
├── .mcp.json                 only if you picked an MCP server
├── scripts/                  only if you picked a script
└── .claude/
    ├── settings.json         your hooks
    ├── cwi-state.json        CWI's record of what it installed (no secrets)
    ├── skills/
    ├── agents/
    └── hooks/
```

In a project created from the template, CWI also deletes the catalog and its own files. Commit the result:

```bash
git add -A && git commit -m "Set up Claude Code workspace"
```

### Useful flags

| Command | When to use it |
| --- | --- |
| `cwi init --dry-run` | See what would happen. Writes nothing. |
| `cwi init --yes` | Accept every suggestion with no questions. Good for scripts and CI. |
| `cwi init --root ../other-app` | Set up a different folder. |
| `cwi init --verbose` | Show details when something fails. |

### Running it again

Run `cwi init` again whenever you want to:

- **Change your selection.** Untick a capability and CWI removes the files it installed for it.
- **Refresh AGENTS.md and CLAUDE.md** after your stack changes.
- **Check your workspace.** CWI warns you if one of its files was edited.

CWI never overwrites a file you changed without asking. It never deletes files it did not create. Running it twice with the same answers changes nothing.

### AGENTS.md and CLAUDE.md

`AGENTS.md` is the open standard that Codex, Cursor, Gemini CLI, GitHub Copilot and Claude Code read. CWI writes the shared instructions there. Claude Code ignores `AGENTS.md` whenever a `CLAUDE.md` exists, so CWI also writes a `CLAUDE.md` whose first line is `@AGENTS.md`. That line imports the shared file. Put Claude-only notes below it.

If you already have a `CLAUDE.md`, CWI adds the `@AGENTS.md` line at the top and leaves the rest untouched. Sections your `CLAUDE.md` already has are not repeated in `AGENTS.md`. An existing `AGENTS.md` is never overwritten without asking. You choose to keep, merge, replace or skip it.

Prefer a single file? Choose **CLAUDE.md only** on the instructions screen.

### After `cwi init`: run `/kickoff` in Claude Code

`cwi init` only provisions the workspace and runs no AI. To start working, open Claude Code in the project and run:

```bash
claude "/kickoff"
```

In an interactive terminal, `cwi init` offers to do this for you when it finishes.

`kickoff` is the "init" inside Claude Code. It reads the project state with a read-only script, shows a short status, proposes the next step, and asks before starting it. It always works in this order:

| Order | Skill it runs | When |
| --- | --- | --- |
| 1 | `project-discovery` | The architecture is missing or still the CWI template. |
| 2 | `feature-spec` | A feature has no spec yet, or its spec is a draft or has open questions. |
| 3 | `feature-workflow` | A spec is `ready`. A spec that is `in progress` is resumed first. |

How `kickoff` behaves in each situation:

- **Existing project with code and no architecture doc.** It asks whether the architecture is documented somewhere. If not, it analyzes the code, delegating to `codebase-explorer`, and writes `docs/architecture.md`, the glossary and the implicit decisions.
- **New project.** It looks for requirements documents, for example `docs/requirements/` or files named PRD, brief or requirements. It proposes using them or asks where they are. Without documents it interviews you. The result is the architecture, the stack decision and an ordered backlog in `docs/specs/README.md`, starting with `project-setup`.
- **Project in progress.** It continues the feature `in progress`, implements the next `ready` spec in backlog order, or finishes a draft spec.

**Diagrams with archify.** The `archify` skill is installed by default and needs Node.js 18+. The workflow skills offer it at the moments where it helps. None of these steps is ever required:

- **`project-discovery`:** when the architecture is written, an architecture diagram based on the real code.
- **`kickoff`:** when the architecture exists but has no diagram yet, it offers to create one.
- **`feature-spec`:** a workflow, sequence, dataflow or state diagram when a feature's flow is not obvious.
- **`feature-workflow`:** after a structural change, it offers to refresh the diagram and link it in the PR.

Diagrams are saved in `docs/diagrams/<type>-<slug>/`, versioned with the docs. You can also ask for one at any time, for example "make a sequence diagram of the checkout flow". To use archify in every project, outside CWI, link your global install: `ln -s ~/.agents/skills/archify ~/.claude/skills/archify`.

It is resumable. Run `/kickoff` any time and it continues from the current state of the files: spec `Status:` lines and the backlog. You can also call `project-discovery`, `feature-spec` or `feature-workflow` directly.

Until the architecture is written, `docs/architecture.md` keeps a `cwi:architecture-template` marker. `feature-spec` and `feature-workflow` refuse to start while that marker is there. Every skill stops and asks when something is unclear, contradictory or missing an important decision. Claude Code shows which agent is running in its own interface.

### Project docs: where requirements and architecture live

`cwi init` offers to create a `docs/` skeleton. It only creates missing files and never overwrites yours:

```text
docs/
├── architecture.md        structure, data flow, integrations + "Stack & versions" table
├── domain/glossary.md     business terms
├── specs/                 one spec per feature (start from specs/_template.md)
└── decisions/             short records of significant design decisions
```

`AGENTS.md` only holds short pointers to these files, so Claude and every agent know where to look without loading them every session. If you delete a scaffolded file, a later `cwi init` won't recreate it.

**Versions.** The Stack section lists the versions the project really uses, read from the lockfiles, for example `Next.js 15.1` and `React 19.0`. It ends with a rule: write code for these versions, and check the official docs for that version when an API differs. Keep the table in `docs/architecture.md` up to date when you upgrade.

### Building a feature

With the `feature-spec` and `feature-workflow` skills installed, which are recommended for every application type:

1. "Write the spec for <feature>." Claude asks clarifying questions and writes `docs/specs/<feature>.md` with acceptance criteria. Unknowns go to *Open questions* instead of being invented.
2. "Implement <feature>." Claude works through these phases:
   - baseline on a feature branch
   - explore the code
   - plan, which you approve
   - test-first slices, one commit each
   - verify the result
   - independent review with `code-reviewer`, plus `security-reviewer` when needed
   - write the PR description and update the docs

### If you need an MCP token

Some MCP servers need a token, for example GitHub needs `GITHUB_TOKEN`. CWI tells you which one. Set it in your shell, not in the repo:

```bash
export GITHUB_TOKEN=ghp_...
```

`.mcp.json` only holds the reference `${GITHUB_TOKEN}`, never the value.

### The Safety Guard hook

The Safety Guard is ticked by default. It stops Claude from running clearly destructive commands, such as `terraform destroy`, `prisma migrate reset`, `git push --force` or `rm -rf /`. It also stops Claude from editing `.env` files, keys or `.git/`. Claude then explains why the command seemed necessary and asks you first.

To allow something for one project, create `.claude/safety-guard.json`:

```json
{
  "allow_paths": [".env.local"],
  "allow_commands": ["^terraform destroy -target=module\\.sandbox"],
  "disabled_rules": ["git-reset-hard"],
  "protected_paths": ["config/production.yml"]
}
```

---

## 3. Add things to the catalog

This section is for people maintaining this template repository. Run these commands from the repository root.

### The one command you need

```bash
cwi catalog add <type> <file> [options]
```

CWI reads your file, asks for anything missing and creates the catalog entry. It then checks the whole catalog. If something is wrong, nothing is added.

### Skills

A skill is a Markdown file with a short header:

```markdown
---
name: api-design
description: REST API design rules. Use when adding or changing endpoints.
allowed-tools: Read, Grep
---

# API design
...instructions for Claude...
```

The `allowed-tools` line is optional.

```bash
cwi catalog add skill path/to/SKILL.md
cwi catalog add skill path/to/SKILL.md --ref rest-guide.md --script check.py
cwi catalog add skill path/to/api-design/          # a folder with SKILL.md, references/, scripts/
```

### Agents

An agent is one Markdown file. Its tools go in the header as `tools:`, not `allowed-tools:`.

```markdown
---
name: dba
description: Reviews SQL and migrations. Use before merging database changes.
tools: Read, Grep, Bash
model: sonnet
---

You are a database reviewer...
```

The `tools` and `model` lines are optional.

```bash
cwi catalog add agent path/to/dba.md
cwi catalog add agent path/to/dba.md --script explain-query.py
```

> If you run `add skill` on a file that has `tools:` in its header, CWI tells you it is an agent.

### Hooks

A hook is a script Claude Code runs on an event. It receives JSON on stdin. To block an action, exit with code `2` and print the reason to stderr.

```bash
cwi catalog add hook block-prod.sh --event PreToolUse --matcher Bash -d "Blocks production deploys"
cwi catalog add hook notify.py --event Stop -d "Desktop notification when Claude finishes"
```

Events: `PreToolUse`, `PostToolUse`, `UserPromptSubmit`, `Stop`, `SubagentStop`, `SessionStart`, `SessionEnd`, `Notification`, `PreCompact`.
`--matcher` only applies to `PreToolUse` and `PostToolUse`. Examples are `Bash` and `Edit|Write`.

### Scripts

```bash
cwi catalog add script seed-db.sh -d "Seeds the local database with demo data"
```

### MCP servers

```bash
# Remote server
cwi catalog add mcp linear --url https://mcp.linear.app/mcp \
  --header 'Authorization=Bearer ${LINEAR_TOKEN}'

# Local server
cwi catalog add mcp postgres --command npx \
  --arg -y --arg @modelcontextprotocol/server-postgres --arg '${DATABASE_URL}'
```

Always write secrets as `${VAR}`. CWI refuses a real token.

### When should it be ticked?

Add these options to any `add` command:

| Option | Effect in `cwi init` |
| --- | --- |
| `--default` | Ticked for every project. |
| `--type backend,fullstack` | Ticked for these project types: `backend`, `frontend`, `fullstack`, `ai`, `cli`, `library`, `data_ml`, `other`. |
| `--tech fastapi,react` | Ticked when these technologies are detected. |
| *(none)* | Listed, but the user ticks it manually. |
| `--depends script:run-quality-checks` | Also installs this capability when it is selected. |
| `--group dev-agents --group-default backend` | Put it in a family and tick it for backend projects through that family. See [Families](#families-groups). |

Without `--yes`, CWI asks these questions for you.

### Families (groups)

A family is a folder that groups related capabilities, for example `development-agents`. Families can also make a set of members preselected for a project type. For example, choosing **Backend** in `cwi init` ticks the backend members of `development-agents`.

```text
catalog/agents/development-agents/
├── group.json                 family name + defaults per project type
├── debugger/
│   ├── cwi.json
│   └── payload/.claude/agents/development-agents/debugger.md
└── test-automator/...
```

Grouped agents install into `.claude/agents/<family>/`. Claude Code finds agents in subfolders too.

```bash
# Add an agent to a family. The family is created if it does not exist.
cwi catalog add agent terraform-expert.md --group devops-agents --group-default backend,fullstack

# Create an empty family
cwi catalog group create agent product-agents --name "Product agents"

# Choose which members are ticked for one project type (replaces the list for that type)
cwi catalog group defaults agent development-agents backend debugger,test-automator,refactoring-specialist
```

You can also edit `group.json` directly:

```json
{
  "schema_version": 1,
  "id": "development-agents",
  "type": "agent",
  "name": "Development agents",
  "defaults": {
    "backend": ["debugger", "test-automator"],
    "frontend": ["accessibility-tester", "debugger"]
  }
}
```

Run `cwi catalog validate` after editing it by hand.

### Other catalog commands

```bash
cwi catalog list                 # everything in the catalog
cwi catalog validate             # check the catalog for problems
cwi catalog remove skill:old     # delete an entry
cwi catalog add skill SKILL.md --force   # replace an existing entry
```

### Publish your changes

The commands only change files in `catalog/`. To ship them with the template, commit and push:

```bash
git add catalog/
git commit -m "catalog: add api-design skill"
git push
```

Every project created from the template after that push gets the new capability.

---

## Troubleshooting

| Problem | Fix |
| --- | --- |
| `No CWI catalog found` | Run from the template folder, or pass `--catalog /path/to/catalog`. |
| `Catalog source unavailable` on a re-run | Expected after cleanup. Pass `--catalog` to add or remove capabilities. |
| `Re-run with --yes to apply` | You ran CWI without an interactive terminal. Add `--yes`, or run it in a terminal. |
| `... changed since the preview` | A file changed while CWI was running. Run `cwi init` again. |
| `The id '...' is already used` | Names must be unique across all types. Pass `--id another-name`. |
| `looks like a literal secret` | Replace the token with `${VAR_NAME}`. |
| Anything else | Run the command again with `--verbose`. |
