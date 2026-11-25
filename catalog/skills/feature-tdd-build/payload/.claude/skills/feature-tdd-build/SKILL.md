---
name: feature-tdd-build
description: Implement exactly one SDD technical milestone without modifying approved tests, and verify acceptance and E2E behavior.
---

# Feature TDD build

Take a milestone number (for example `/feature-tdd-build 2`). Verify it is the next allowed milestone.
Run `spado sdd begin build --milestone N`, then delegate a fresh worker with AGENTS.md, FEATURE.md,
ROADMAP.md, approved tests and relevant architecture decisions. Implement only this milestone.
Never edit tests, fixtures, selectors, assertions or runner configuration to pass checks. A defect in
those contracts is a blocker requiring explicit reopening, not permission to weaken them.
Run `spado sdd check`: baseline plus unit, integration, acceptance and E2E for this and earlier
milestones must pass. Future milestones may remain red; the final milestone verifies the full feature.
Fix actual failures within this scope. Present the diff, requirement-to-test evidence and limitations.
Submit a Report and wait for Human approval before the commit. SPADO creates the commit; do not
run git add/commit yourself. In supervised mode the controller owns intermediate approvals/commits.
Do not start another milestone. Questions and blockers return control to the Human.

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
