---
name: feature-workflow
description: Implement a feature end to end from its spec: baseline, explore, plan, test-first slices with small commits, verification and an independent review before the PR. Use when asked to implement, build or develop a feature or user story.
---

# Feature workflow

Deliver a feature in small, verified steps. Follow the phases in order; do not skip the baseline or the review.

## Before anything: the architecture must exist

If there is no architecture doc, or `docs/architecture.md` still contains `cwi:architecture-template`, stop. Tell the user the architecture is not defined yet and run the **project-discovery** skill first.

## Ask, don't assume

Stop and ask the user — do not continue on a guess — whenever:
- a requirement is unclear, ambiguous or contradicts another requirement, the spec or the architecture;
- an important decision is missing: data model or migration, public API or contract, security or permissions, a new dependency, or user-facing behaviour;
- the spec and the existing code disagree about how something works;
- the approved plan has to change during implementation;
- a step would be destructive or hard to reverse.

Ask concrete questions with the options you see and your recommendation. Record answers that change the spec in the spec, and design decisions in `docs/decisions/`.

## Rules for the whole workflow

- Work on a feature branch (`git switch -c feature/<slug>`). Never commit to `main`/`master`; never force-push.
- Code for the versions listed in the Stack section and `docs/architecture.md`. If an API differs between versions, check the official docs for the version in use.
- Stop and ask before anything destructive or irreversible (migrations that drop data, resets, deleting files you did not create).
- Agents named below are optional: use them if they are installed (`/agents`), otherwise do that step yourself.

## 1. Baseline

- Set the spec's `Status:` to `in progress` when you start, and to `done` when the feature is merged-ready.

- Find the spec in `docs/specs/`. If there is none, use the `feature-spec` skill first; do not implement an unwritten feature.
- Run the test and lint commands from AGENTS.md / CLAUDE.md. Report pre-existing failures to the user before changing anything.

## 2. Explore (read-only)

- Read `docs/architecture.md` and the code paths the feature touches. For an unfamiliar codebase, delegate to **codebase-explorer**.
- Identify existing patterns to reuse. Do not introduce a new pattern when one exists.

## 3. Plan

- Write a plan: files to change, data/API changes, risks, and the tests that prove each acceptance criterion.
- Split it into slices that each leave the app working and can be committed alone.
- If the plan changes structure (new module, layer, data model), ask **architect-reviewer** to review it, and record the decision in `docs/decisions/`.
- Get the user's approval before coding.

## 4. Implement slice by slice

For each slice:
1. Write the tests first from the acceptance criteria (**test-automator** if available). They must fail for the right reason.
2. Implement the smallest change that makes them pass. Follow existing conventions.
3. Run the relevant tests and lint; fix everything the post-edit validation reports.
4. Commit with a clear message. One slice, one commit.

If something breaks and the cause is unclear, switch to the **debugging** skill or the **debugger** agent instead of guessing.

## 5. Verify like a user

- Run the full test suite and lint.
- Run the app and exercise the feature against every acceptance criterion, including edge cases.
- UI changes: check accessibility (**accessibility-tester**). Heavy data or hot paths: check performance (**performance-engineer**).

## 6. Independent review and PR

- Review the whole branch diff with **code-reviewer** in a fresh context. Add **security-reviewer** when the feature touches authentication, authorization, user input, payments or personal data.
- Fix confirmed findings, re-run tests, commit.
- Update `docs/architecture.md` (structure or versions changed), the glossary and the spec status (`done`).
- After `project-setup` or any dependency upgrade: update the versions table in `docs/architecture.md` and tell the user to run `cwi init` and choose **Rescan**, so the Stack in AGENTS.md lists the real versions.
- Write the PR description: what and why, how to test, risks, and which acceptance criteria are covered by which tests.

## Done means

Afterwards, suggest `/kickoff` (if installed) to pick the next feature.


Every acceptance criterion is covered by a passing test, the full suite and lint pass, the review findings are resolved, and the docs reflect the change.
