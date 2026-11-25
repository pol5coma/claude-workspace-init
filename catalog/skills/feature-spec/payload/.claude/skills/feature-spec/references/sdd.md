# SDD feature specification

Read `.workflow/PROTOCOL.md` and `spado sdd status`. Accept a product feature ID, brief, or independent
idea. Resolve product IDs against the approved product roadmap, preserving source requirements.
For a new run choose the feature slug and invoke `spado sdd start SLUG [--feature ID]`; manual is
the default. Use `--mode supervised` only on explicit delegation. Never change an active run's mode.
Starting needs a clean Git worktree with an initial commit; do not commit unrelated work to bypass it.

Interview the Human one question per turn until requirements are clear. Capture assumptions under
`## Assumptions` in the existing README, using a feature-specific subsection. Do not invent requirements.
Begin spec, then assign a fresh worker without conversation history to write
`docs/features/SLUG/FEATURE.md`: objective, actors, flows, inputs/outputs, error and edge cases,
exclusions, and unique stable acceptance criterion IDs. Update global `FEATURE-MAP.md` functionally.
Provide enough brief context to the worker through explicit artifacts, not the entire chat.

The main conversation separately commissions a fresh read-only `architect-reviewer`. Give it the
spec and relevant project sources, not the author's reasoning or desired verdict. Inspect existing
architecture/ADRs, API routes, request/response/error/auth contracts, callers, events, schemas and
migrations. Identify reuse opportunities and regression risks. Distinguish evidence, inference,
blockers, recommendations and uncertainty. With no existing project, assess coherence and feasibility.
Do not require a context-manager service or invent benchmark results.

Every incompatible change must identify affected consumers and an explicit compatibility,
versioning or migration strategy. Translate risks to acceptance criteria and required contract/E2E
tests. Resolve blockers and repeat the affected review after changes. Architecture review does not
prove runtime behavior; later executable tests are mandatory.

Get `spado sdd context` for the current snapshot and schemas. Submit the author's Report with an
independent `architecture` Review tied to that snapshot. Present the spec and findings. Only after
an explicit response call `spado sdd approve --response "EXACT RESPONSE"`. Do not start roadmap.
Workers never record approval, commit, or advance. If clean-context delegation is unavailable,
stop and explain how to invoke this assignment in a new conversation.

In supervised execution, the controller supplies the brief and coordinates workers and independent
reviews. Return the requested Report; never invoke another controller or transition from a worker.
