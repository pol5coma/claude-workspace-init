---
name: project-discovery
description: First step after cwi init. Defines the project architecture before any spec or code - finds existing architecture docs, analyzes existing code, or builds the architecture from requirements documents - and fills docs/architecture.md, the glossary and the feature backlog. Use when starting work on a project, when docs/architecture.md contains cwi:architecture-template, or when asked to document or define the architecture.
---

# Project discovery

Goal: a reviewed, written architecture before anyone writes specs or code. Everything later (feature-spec, feature-workflow, reviews) is checked against it.

Always talk to the user. Ask whenever something is unclear, contradictory or missing a decision. Never invent business rules, requirements or constraints. Show a summary and get confirmation before writing files.

## Step 1 — Ask where the architecture stands

Ask the user exactly this, with these options:

> Is the architecture already defined?
> 1. Yes, I'll give you the path.
> 2. Yes, find it yourself.
> 3. No — there is already code: analyze it.
> 4. No — it's a new project.

Then follow the matching path.

### 1. Yes, path given
- Read the document. If it misses structure, data flow, integrations or versions, list the gaps and ask whether to complete them.
- Make sure AGENTS.md (or CLAUDE.md) points to it under "Project docs". If `docs/architecture.md` is the unused CWI template, ask whether to delete it.

### 2. Yes, find it
- Search: `ARCHITECTURE.md`, `docs/**/architecture*`, `docs/**/design*`, ADR folders (`docs/adr`, `docs/decisions`), README sections named "Architecture". Skip `node_modules`, build output and vendored code.
- Show what you found and let the user confirm which document is authoritative. If nothing is found, say so and offer option 3 or 4.

### 3. No, analyze the existing code
- Delegate the exploration to the **codebase-explorer** agent if it is installed (check `/agents`); otherwise explore yourself (read-only).
- Fill `docs/architecture.md`: Overview, Stack & versions (verify against the lockfiles), Structure, Data flow, Integrations, Conventions. Describe what the code does today, not what it should do.
- Seed `docs/domain/glossary.md` with the domain terms found in the code.
- List implicit decisions you discovered (e.g. "sessions in Redis", "REST, not GraphQL") and ask which ones to record in `docs/decisions/`.
- Ask the user about anything the code cannot tell you: purpose, users, constraints, planned direction.

### 4. No, new project
- Ask: "Do you have requirements documents? Give me their path (for example `docs/requirements/`), or say none."
- **With requirements:** read all of them, then:
  - Build `docs/domain/glossary.md` from the business terms.
  - Propose the architecture in `docs/architecture.md` (components, data, integrations) using the stack in AGENTS.md. Use the latest stable versions unless the requirements say otherwise, and record them in the versions table.
  - Record the stack choice in `docs/decisions/0001-stack.md`.
  - Write an ordered feature backlog in `docs/specs/README.md` under a `## Backlog` heading, as a numbered list of `` `slug` — description `` items (dependencies first). The first item is `project-setup`: the walking skeleton (project scaffold, tooling, CI, one end-to-end path).
  - Every contradiction, gap or ambiguity between documents becomes a question for the user — list them and ask before writing.
- **Without requirements:** interview the user section by section (goal and users, main capabilities, data, integrations, constraints, non-functional needs), then write the same files.
- If the user prefers to complete it later, leave the skeleton untouched and stop.

## Step 2 — Confirm and finish

1. Show a short summary of what you will write; write it only after the user agrees.
2. Delete the `cwi:architecture-template` line at the top of `docs/architecture.md`.
3. **Diagram (optional).** If the **archify** skill is installed, offer to generate the architecture diagram from `docs/architecture.md` and the code (repository evidence). Diagrams live in `docs/diagrams/<type>-<slug>/` (tell archify to use that folder) so they are versioned with the docs. Link it from the Overview of `docs/architecture.md`. If Node.js is missing, say so and skip.
4. Tell the user the next step: **feature-spec** for the first feature in the backlog (`project-setup` for a new project). If the **kickoff** skill is installed, suggest `/kickoff` to continue in order.
