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
| 2. CLAUDE.md | A short proposed `CLAUDE.md` with safety rules, stack, commands and an architecture pointer. | Accept, edit the commands, or add a global instruction. |
| 3. Capabilities | Five lists: Skills, Agents, Scripts, MCP and Hooks. Recommended items are already ticked. | **Space** toggles an item and **Enter** continues. |
| 4. Preview | Every file CWI will create, change or delete. | Choose **Apply**, **Review changes** to see diffs, **Back** or **Cancel**. |

Nothing is written before you choose **Apply**. **Cancel** leaves the project exactly as it was.

### What you end up with

```text
my-app/
├── CLAUDE.md                 short, project-wide instructions
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
- **Refresh CLAUDE.md** after your stack changes.
- **Check your workspace.** CWI warns you if one of its files was edited.

CWI never overwrites a file you changed without asking. It never deletes files it did not create. Running it twice with the same answers changes nothing.

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

Without `--yes`, CWI asks these questions for you.

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
