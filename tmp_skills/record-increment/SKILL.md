---
name: record-increment
description: Record implementation increments under .dev/increments/. Use when starting an increment, approving a revised plan, or handing back completed, partial or blocked implementation work. Preserve the original prompt, version approved plans and final outputs, and invoke update-agent-notes after implementation and verification.
---

# Record Increment

Maintain a concise, factual record of each implementation increment.

## 1. Paths and naming

Use `.dev/increments/<increment-id>/`.

For increment 1.1:

- Original prompt: `.dev/increments/1.1/prompt.md`
- First approved plan: `.dev/increments/1.1/plan1.md`
- Revised plans: `plan1-v2.md`, `plan1-v3.md`, etc.
- First implementation handoff: `.dev/increments/1.1/out.md`
- Subsequent handoffs: `out-v2.md`, `out-v3.md`, etc.

Plan and output versions are independent sequences.
Each output must identify the approved plan version it follows.

Determine the increment identifier from the user's request or
the current approved task. If ambiguous, ask before writing.

Read existing records before creating files. Never overwrite an
existing prompt, approved plan or output.

## 2. Respect Plan Mode and approval

During Plan Mode:
- Inspect existing records and relevant project documentation.
- Prepare the implementation plan.
- Ask about genuine ambiguities.
- Do not write increment records or implement code.

Wait for explicit plan approval and an editing-enabled mode.

After approval, save the prompt and approved plan before starting
implementation.

If a new ambiguity materially affects scope or behavior, ask before
implementing the affected part. Continue independent work where safe.

Do not ask the user to reconfirm decisions already documented.

## 3. Save the original prompt

Create `prompt.md` from the user's original implementation prompt.

Preserve its wording and formatting. Do not replace it with a
summary or reconstruct missing text.

If the original prompt is unavailable, ask the user to provide it.

Never overwrite an existing `prompt.md`. Later instructions and
corrections must be reflected in the next approved plan when they
change the agreed work.

Before saving, remove credentials, secrets, real customer data and
fixture sensitiveFields. Mark necessary redactions explicitly and
tell the user the saved prompt is sanitized.

## 4. Save approved plans

Save the first approved plan as `plan1.md`.

When the user approves a modified plan:
- Save the complete revised plan.
- Use the next available version: `plan1-v2.md`, `plan1-v3.md`, etc.
- Preserve all earlier versions.
- Do not create a version if the approved plan is unchanged.
- Do not label an unapproved proposal as approved.

Include a short header identifying:
- Increment.
- Plan version.
- Previous version, where applicable.
- A concise explanation of what changed.

Keep the complete approved plan below that header.

If approval or the approved text is unclear, ask before saving
or implementing the affected changes.

If another worker creates a file concurrently, re-read the records
and resolve the conflict without overwriting their work.

## 5. Follow the approved scope

Implement only within the approved scope.

For a material change to scope or behavior:
- Explain the change and its implications.
- Obtain approval.
- Save the revised plan before implementing the affected part.

Routine implementation details do not require a new plan version
unless they change the agreed plan.

Treat these files as execution records. They do not replace
specs, architecture, data models or user flows.

## 6. Update the agent work note

After implementation and verification, invoke `update-agent-notes`.

Also invoke it when handing back partial or blocked implementation
with meaningful work to record.

Supply only available evidence:
- Agents and tools used and work delegated.
- Useful contributions.
- Outputs corrected, rejected or deliberately checked.
- Commands and checks executed, with observed results.
- Remaining uncertainty or blockers.

Do not invoke it merely because a prompt or plan was saved.

Do not claim the candidate personally reviewed or tested anything
unless the candidate explicitly confirmed it.

Let update-agent-notes maintain the repository-root AGENT-NOTES.md
within its 30-line limit. Do not copy the full increment report into it.

If the skill is unavailable or fails, report that clearly and include
the limitation in the final output. Do not claim it ran successfully.

## 7. Save the final output

After implementation, verification and the update-agent-notes step,
save the final handoff as `out.md`.

Record:
- Increment and approved plan version followed.
- Implementation status: completed, partial or blocked.
- What changed and the relevant files.
- Commands and checks actually executed, with observed results.
- Review findings and corrections.
- Remaining limitations or blockers.
- Reproducible manual verification steps and expected outcomes.
- Whether update-agent-notes ran successfully.
- A proposed commit message, if requested.

Distinguish implementation completion from the user's pending
manual verification and acceptance.

Do not claim checks, reviews or completion without evidence.
Distinguish agent-executed checks from user-reported checks.

If a previous handoff exists:
- Preserve it.
- Save new substantive results as `out-v2.md`, `out-v3.md`, etc.
- Do not create another version for an unchanged handoff.

Apply the same redaction rules used for the prompt.
Do not include raw sensitive payloads or secret-bearing logs.

Write output records only when editing is permitted.
Do not create an implementation completion report merely because
planning finished.

## 8. Boundaries and final response

This skill may write only:
- Records under the current increment directory.
- AGENT-NOTES.md through update-agent-notes.

The approved implementation task separately authorizes application
and documentation changes.

Do not:
- Execute Git mutations.
- Mark roadmap items complete without the user's confirmation.
- Change requirements or architecture to match an execution record.
- Create additional tracking files unless requested.
- Modify unrelated increment directories.

In the response to the user:
- Summarize the implementation and verification truthfully.
- Identify unresolved issues and required manual checks.
- List the record files created and the approved plan version.
- State whether update-agent-notes ran.

Keep the response consistent with the saved output. A shorter
response is acceptable, but do not omit material failures or blockers.