---
name: feature-spec
description: Turn a feature request into a written spec in docs/specs/<feature-slug>.md before any code is written. Use when the user describes a new feature, change request or user story, or asks to "spec", "define" or "plan" a feature.
---

# Feature spec

Write down what to build before building it. The spec is the contract that planning, tests and review are checked against.

## Before anything: the architecture must exist

If there is no architecture doc, or `docs/architecture.md` still contains `cwi:architecture-template`, stop. Tell the user the architecture is not defined yet and run the **project-discovery** skill first.

## Steps

1. **Read context first.** Project docs listed in AGENTS.md / CLAUDE.md: `docs/architecture.md` (structure and versions), `docs/domain/glossary.md` (business terms), existing specs in `docs/specs/`.
2. **Clarify before writing.** Ask the user the questions you need answered. Group them; at most one round of ~5 questions. Typical gaps: who the user is, success criteria, permissions, limits, empty/error states, what is out of scope.
3. **Write the spec** to `docs/specs/<feature-slug>.md`:
   - Use `docs/specs/_template.md` if it exists, otherwise [references/spec-template.md](references/spec-template.md).
   - Acceptance criteria in Given / When / Then form, each one testable and observable.
   - Use glossary terms exactly; add new business terms to the glossary.
   - List data model, migration and API changes explicitly, or write "None".
4. **Never invent business rules.** Anything the user did not state and the code does not show goes under **Open questions**, not into the criteria.
5. **Confirm.** Show the user a short summary (goal, criteria count, open questions) and set `Status: ready` only after they agree and no open question blocks implementation.
6. **Next.** Make sure the feature is in the `## Backlog` list of `docs/specs/README.md`. Suggest **feature-workflow** to implement it, or `/kickoff` to continue in order.

## Quality bar

- A developer who never saw the conversation could implement and test it from the spec alone.
- Each acceptance criterion maps to at least one test.
- Out of scope is explicit, so the implementation does not grow.
- Keep it short: one or two screens. Link to designs or tickets instead of copying them.
