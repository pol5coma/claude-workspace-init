---
name: feature-close
description: Close one SDD feature with full acceptance/E2E evidence, independent code/security reviews and Human acceptance.
---

# Feature close

Require every milestone approved and committed. Begin close. Delegate a fresh writer to remove
identified dead code, debug logs and temporary artifacts; preserve approved specs and tests. Update
FEATURE-MAP.md with verified existing paths and relevant AGENTS.md guidance without overwriting
unrelated instructions. Run `spado sdd check` for the complete suite including acceptance and E2E.
The main thread commissions TWO separate fresh read-only workers: code-reviewer (`code`) and
security-reviewer (`security`). Review the complete change from the feature's recorded base commit,
including committed, staged and unstaged changes; a plain working-tree git diff is insufficient.
Report evidence-backed findings. Corrections invalidate affected reviews and tests; rerun them on
the final files. Submit the report and show requirements, check results, reviews and remaining limits.
Final acceptance always belongs to the Human, including supervised mode. After explicit approval,
SPADO records completion and updates product roadmap progress. Do not select the next feature.

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
