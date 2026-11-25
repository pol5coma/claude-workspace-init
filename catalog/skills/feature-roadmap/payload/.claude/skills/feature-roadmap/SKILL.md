---
name: feature-roadmap
description: Plan the technical milestones of one approved SDD feature and commission an independent senior audit.
---

# Feature roadmap

Require an approved spec. Begin `roadmap`, then delegate a new author to read FEATURE.md,
architecture findings and the affected code. Write `docs/features/SLUG/ROADMAP.md` with consecutive
milestone IDs starting at 1, dependencies, expected changes and observable acceptance criteria.
Return the milestone list with criterion IDs matching the spec exactly. Do not implement code.
Commission a different fresh senior reviewer (role `plan`) to assess coverage, ordering, feasibility,
regressions and testability. Revisit architecture only for new decisions. Resolve blockers without
changing the approved spec; if scope changes, request reopening spec.
Combine the author's Report with the independent Review and submit. Present the roadmap and audit,
then wait for Human approval. The product roadmap is not this feature's technical ROADMAP.md.

## SDD execution contract

This is an explicit entrypoint. Read `.workflow/PROTOCOL.md` and `spado sdd status` before acting.
Keep the Human conversation in the main thread. Use a new worker without inherited conversation
history for each execution assignment; send approved artifacts and the bounded task. If the host
cannot exclude history, stop and explain how to use a new conversation. Do not silently reuse context.
The main thread registers transitions; workers do not approve, advance, commit or delegate.
Return control after this phase. Never invoke the next skill automatically in manual mode.
Record Human approvals only after an explicit response to the concrete version presented.
If the Human explicitly delegates supervised execution, use `spado sdd start SLUG --mode supervised`
(or the already selected supervised run) and `spado sdd run --host claude|codex`; the controller
stops before final feature acceptance. Do not change an existing run's mode implicitly.
Do not push, merge or deploy as part of SDD.
