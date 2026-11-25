---
name: product-roadmap
description: Prepare and prioritize a product backlog from local documents or an interview; explicitly invoked SDD product planning.
---

# Product roadmap

Accept explicit source files or folders with any names. Without paths, discover candidates while
excluding dependencies, build output and vendor code; ask which sources are authoritative.
Without documentation interview the Human one question per turn, then record agreed requirements
in `backlog.md`. Distinguish assumptions from facts. Do not invent business rules or numeric scores.
Resolve duplicates and contradictions. Break large initiatives into implementable features and link
cross-cutting requirements to affected features. Propose stable IDs, slugs, dependencies, scope,
MVP/value/risk/effort rationale and traceable source references. Never silently remove requirements.
Present the proposed order for discussion. Use `spado sdd product-submit --proposal FILE` with
`{"sources":["backlog.md"],"features":[{"id":"FEAT-001","slug":"accounts","title":"Accounts",
"sources":["backlog.md#accounts"],"depends_on":[],"rationale":"Required by projects"}]}`.
SPADO renders `feature-roadmap-implementation.md`; only after the Human agrees run
`spado sdd product-approve --response "EXACT RESPONSE"`. Do not start a feature.
Preserve IDs, completed work and source documents when reprioritizing. Report active-scope conflicts.

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
