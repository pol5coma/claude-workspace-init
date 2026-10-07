---
name: kickoff
description: Start or resume work on this project in the right order - architecture first, then feature specs, then implementation. Checks the project state and runs project-discovery, feature-spec or feature-workflow as needed. Use when opening the project, when the user says start, kickoff, continue, "what's next" or "where were we", or right after cwi init.
---

# Kickoff

The entry point for working on this project. It figures out where the project stands and walks the user through the next step, in this fixed order:

1. **Architecture** defined → `project-discovery`
2. **Feature specs** written → `feature-spec`
3. **Implementation** → `feature-workflow`

It is resumable: running `/kickoff` again continues where the project is now.

## 1. Read the project state

Run the status script (read-only):

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/project-status.py"
```

It prints JSON: `architecture` (missing / template / defined + path), `code` (is there source code), `requirements` (candidate requirement documents), `specs` (each with status and open questions), `backlog` (ordered items from `docs/specs/README.md`) and `next` (the recommended step).

Show the user a short status summary (3–6 lines), for example:

> Architecture: not defined yet · Code: yes · Specs: none · Next: analyze the code and write the architecture.

## 2. Propose the next step and confirm

Map `next` to an action, explain it in one sentence, and ask the user to confirm or choose another step. Never start a phase without the user's go-ahead.

| `next` | Action |
| --- | --- |
| `discovery:code` | Use the **project-discovery** skill, path "analyze the existing code". First ask: "Is the architecture already documented somewhere?" — if yes, use the "path" or "find it" path instead. |
| `discovery:new` | Use **project-discovery**, path "new project". If `requirements` lists documents, propose them ("I found docs/requirements/ — use it?"); otherwise ask for their path or offer the interview. |
| `workflow:<slug>` | Use the **feature-workflow** skill on `docs/specs/<slug>.md` (resume it if its status is `in progress`). |
| `spec:<slug>` | Use the **feature-spec** skill for `<slug>`: finish the draft or resolve its open questions, or write it if it does not exist yet. |
| `spec:new` | No backlog and no specs. Ask what feature the user wants to build. If requirement documents exist, offer to derive an ordered backlog from them with project-discovery first. |
| `done` | Every spec is done. Summarize what was delivered and ask what comes next. |

The user can always override: if they ask for a specific feature or phase, do that, but warn if it skips an earlier step (for example, specs before the architecture exists).

## 3. Run the phase, then loop

- Follow the chosen skill's instructions fully; do not shortcut them here.
- When the phase ends, run the status script again, show what changed, and propose the next step. Stop whenever the user wants; tell them `/kickoff` resumes from here.

## Rules

- **Order matters.** Do not write specs while the architecture is missing or still the CWI template, and do not implement a feature without a `ready` spec.
- **Ask, don't assume.** Stop and ask when anything is unclear, contradictory, or missing an important decision. Never invent requirements or business rules.
- **Status lives in the files.** Keep `Status:` in each spec and the backlog in `docs/specs/README.md` up to date (`## Backlog` as a numbered list of `` `slug` — description `` items), so the next `/kickoff` picks up correctly.
- **Stay safe.** Work on feature branches, never force-push, and ask before anything destructive.
