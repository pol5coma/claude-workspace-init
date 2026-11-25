---
name: feature-tdd-start
description: Establish a green baseline, write all SDD feature tests and present verified Red evidence for assertion approval.
---

# Feature TDD start

Require approved spec and roadmap. First prepare `docs/features/SLUG/CHECKS.json` using the protocol
schema; this preparation may occur while Red is pending. Declare baseline commands, protected test
and fixture globs, runner configuration, and unit/integration/acceptance/E2E checks for EVERY milestone.
Map all acceptance criteria to acceptance AND E2E checks. All new checks need JUnit reports and exact
expected failing test IDs. Store JUnit reports under `.workflow/results/`.
Run `spado sdd check --baseline` before writing tests. Stop on failure; do not repair unrelated baseline
failures or claim an empty command is a test suite. Then `spado sdd begin red` and delegate a fresh
worker to write all feature tests from the approved contract, including compatibility regressions.
Do not implement production behavior. Run `spado sdd check`; every new check must fail for the specified
assertion reason, with no collection, infrastructure errors or skipped tests. Explain the failure causes.
In supervised mode obtain a fresh independent `asserts` review. In manual mode present asserts,
commands, coverage, fixtures and Red evidence to the Human. Approval freezes tests and configuration.

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
