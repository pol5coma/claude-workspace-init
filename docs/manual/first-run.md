# First execution: from setup to accepted evidence

[Back to the manual](../../USAGE.md) · [CLI reference](../../USAGE.md#cli-reference) · [Event contract](../../src/spado/runtime/protocol.md)

This chapter follows **`initial-ideation` (subphase 1.1, Initial ideation and opportunity assessment)**, in `semi-auto`. It has no canonical upstream dependency, so it is suitable for a first independent run. The selected opportunity is a hypothesis, not proof of demand.

## Host-led walkthrough

1. Install SPADO from a permanent checkout and configure a separate product directory using the [setup instructions](../../USAGE.md#installation-and-setup). Select your host, mode and embedding backend explicitly. Preview first, then apply and run `spado db up`.
2. Open that product in Claude or Codex. Invoke `/spdlc --new-run --subphase initial-ideation --mode semi-auto` or `$spdlc --new-run --subphase initial-ideation --mode semi-auto`. Provide your objective, ideas, intended users, existing evidence and constraints. Ask to assess one opportunity, recording discarded ideas and unknowns.
3. The host registers the run and CAOAO, delegates CEAO, CPAO and specialist `spdlc-1-1`, reads the canonical brief and prepares the activity. Keep the run ID. The owner is a runtime specialist UUID, not the string `spdlc-1-1`.
4. Read the actual plan: objective, deliverable, actions, criteria, inputs and assumptions. Approve that plan ID/version or request changes. Expected state before approval: `awaiting_plan_approval`; afterward: `ready`.
5. The assigned specialist records `start`, performs the assessment and writes a document. It synchronizes the file and delivers the returned revision with criterion evidence. Expected progression: `running` → `awaiting_review`.
6. CEAO and CPAO each review under their own identity. Changes requested mean the work must be corrected and delivered again. After both approve, CAOAO accepts the activity and promotes the revision.
7. Inspect `spado status --run RUN_ID --human` and `spado review subphase initial-ideation --run RUN_ID --human`. Confirm acceptance, the real deliverable and the current official revision through context. Structural success does not replace reading the content.

Semantic indexing is optional for this first exercise. After promotion, use `docs index` and `docs search` when you want retrieval; that is when model download/API access becomes relevant.

An independent 1.1 run cannot later execute 1.2 inside the same scope. Start a phase/full-workflow run if you want that broader journey, and deliberately bring existing evidence into it. Within a full run, selecting another included subphase preserves the same run and its dependency map.

## Advanced terminal walkthrough

This is the underlying protocol, useful for understanding or debugging the host's work. **Each action belongs to the indicated real actor.** Do not submit a Human approval before the Human decides, or officer approvals before those officers review. Credential possession does not substitute for those decisions.

Run commands from the configured product. Uppercase IDs/token paths are placeholders returned by earlier commands. JSON UUIDs below are illustrative event IDs: generate a fresh UUID for each new event and retain it for identical retries. Request files can live in a local scratch directory; pass their actual path to `--request`.

### 1. Human creates the run and delegates CAOAO

```bash
spado workflow create --objective "Select one product opportunity for investigation" \
  --subphase initial-ideation --mode semi-auto --human
spado actor create CAOAO --run RUN_ID --human
```

The first result provides `run`. The second provides `actor` and `token_file`. Pass that file path to the CAOAO session as `SPADO_ACTOR_TOKEN_FILE`. Ensure a leftover `SPADO_ACTOR_TOKEN` is not overriding it.

### 2. CAOAO delegates the required identities

With CAOAO's token in its environment:

```bash
spado workflow context --run RUN_ID --subphase initial-ideation
spado actor create CEAO --run RUN_ID
spado actor create CPAO --run RUN_ID
spado actor create spdlc-1-1 --run RUN_ID
```

Pass each returned token file only to the corresponding native agent session. Record the specialist's `actor.id` as `SPECIALIST_ACTOR_ID`. The command registers identities; the host still needs to instantiate/delegate the native agents.

### 3. CAOAO prepares the activity

Save the following as `prepare.json`, replacing the owner with the actual specialist UUID. Deliverable and criterion text come directly from context:

```json
{
  "event_id": "11111111-1111-4111-8111-111111111111",
  "kind": "prepare",
  "payload": {
    "subphase": "initial-ideation",
    "owner": "SPECIALIST_ACTOR_ID",
    "plan": {
      "objective": "Select one product opportunity for investigation",
      "deliverable": "Shortlisted ideas, initial opportunity statements, selection criteria and rationale for the opportunity chosen for investigation.",
      "actions": ["Compare candidate problems and intended beneficiaries", "Record selection rationale, rejected ideas and unknowns"],
      "criteria": ["At least one opportunity has a clear problem hypothesis, intended beneficiary and selection rationale; rejected ideas and major unknowns are recorded."],
      "inputs": {},
      "assumptions": []
    }
  },
  "rationale": "Bound the first investigation to one opportunity assessment."
}
```

This minimal plan has no recorded input documents because 1.1 has no upstream dependency. If your assessment consumes recorded documents, include their real revision IDs and digests. Add product-specific actions, criteria and assumptions where needed before approval.

```bash
spado workflow prepare --run RUN_ID --request prepare.json
spado workflow context --run RUN_ID --subphase initial-ideation
```

Keep the returned `ACTIVITY_ID`. Context contains `instances[].plan.id` and `.version` for that activity. A `prepare` request for an existing unaccepted instance resumes it; use `revise_plan` to change its plan, or explicitly `new_instance` to create another activity.

### 4. Human approves the concrete plan

After reading and approving the plan, save `approve.json` using its current ID/version. The first plan version is `1`; do not assume this for a revised plan.

```json
{
  "event_id": "22222222-2222-4222-8222-222222222222",
  "kind": "approve_plan",
  "payload": {"activity": "ACTIVITY_ID", "plan_id": "PLAN_ID", "version": 1},
  "rationale": "The Human reviewed and approved this exact assessment plan."
}
```

```bash
spado workflow record --run RUN_ID --request approve.json --human
```

The rationale must describe an actual decision, not a simulated approval. Expected state: `ready`.

### 5. Specialist starts and records the document

Save `start.json`:

```json
{
  "event_id": "33333333-3333-4333-8333-333333333333",
  "kind": "start",
  "payload": {"activity": "ACTIVITY_ID"},
  "rationale": "Begin the approved assessment with the assigned specialist."
}
```

In the specialist session with its token:

```bash
spado workflow record --run RUN_ID --request start.json
```

Perform the assessment and create `docs/opportunity.md`. It must contain the actual candidates, beneficiary, selected problem hypothesis, selection criteria/rationale, rejected ideas, evidence limitations and unknowns. This guide does not manufacture that business evidence.

```bash
spado docs sync docs/opportunity.md --subphase initial-ideation --run RUN_ID
```

Keep the returned revision as `REVISION_ID`. This records evidence but does not deliver or approve it.

### 6. Specialist delivers criterion evidence

Save `deliver.json`. Replace the sample evidence description with a precise reference to the real document's content; include evidence for every criterion if you added more to the plan.

```json
{
  "event_id": "44444444-4444-4444-8444-444444444444",
  "kind": "deliver",
  "payload": {
    "activity": "ACTIVITY_ID",
    "outputs": ["REVISION_ID"],
    "criteria_evidence": {
      "At least one opportunity has a clear problem hypothesis, intended beneficiary and selection rationale; rejected ideas and major unknowns are recorded.": "docs/opportunity.md: the selected-opportunity section identifies the problem and beneficiary; comparison and unknowns sections record the rationale and exclusions."
    }
  },
  "rationale": "Submit the completed assessment and its criterion evidence for review."
}
```

```bash
spado workflow record --run RUN_ID --request deliver.json
```

Expected state: `awaiting_review`. The specialist cannot continue syncing output in that state: a correction needs the activity returned to execution through the proper gates.

### 7. Both responsible officers review

CEAO and CPAO inspect the actual revision, within their domains. Each submits its own `domain_review` event and evidence using its own token. For example, CEAO's `ceao-review.json`:

```json
{
  "event_id": "55555555-5555-4555-8555-555555555555",
  "kind": "domain_review",
  "payload": {
    "activity": "ACTIVITY_ID",
    "decision": "approved",
    "evidence": "Replace with CEAO's actual assessment of strategic fit, selection rationale and recorded constraints."
  },
  "rationale": "Record CEAO's completed domain review."
}
```

```bash
spado workflow record --run RUN_ID --request ceao-review.json
```

CPAO's separately authored `cpao-review.json` uses a **different UUID**, the same activity, and CPAO's own evidence concerning the beneficiary/problem and selection criteria. Submit it from CPAO's session:

```bash
spado workflow record --run RUN_ID --request cpao-review.json
```

If either officer requests changes, record `decision: "changes_requested"` with actionable evidence. The activity becomes blocked; revise the plan if needed, obtain its approvals, restart, correct, synchronize and deliver again. Delivery clears prior reviews, so both officers review the corrected output.

### 8. CAOAO accepts and promotes

After all gates pass, CAOAO saves `accept.json`:

```json
{
  "event_id": "77777777-7777-4777-8777-777777777777",
  "kind": "accept",
  "payload": {"activity": "ACTIVITY_ID"},
  "rationale": "Required domain reviews and criterion evidence are complete for the current plan."
}
```

```bash
spado workflow record --run RUN_ID --request accept.json
spado docs promote REVISION_ID --run RUN_ID
spado status --run RUN_ID
spado review subphase initial-ideation --run RUN_ID
```

Expected state: `accepted`; `workflow context` exposes the approved document revision. Promotion does not change file contents. Optional retrieval:

```bash
spado docs index --run RUN_ID
spado docs search "selected opportunity and unknowns" --run RUN_ID
```

### Variations: other modes and broader scopes

| Variation | Additional/different actions |
|---|---|
| `agentic` / `auto` | CAOAO validates prepared plans automatically; skip Human plan approval. Auto permits exceptional Human questions; agentic reports blockers without requesting them. Domain reviews remain. |
| `manual` | Human's `approve_plan` adds `arrangement: "human"`, `"assisted"` or `"delegated"`. Human execution starts under Human identity when selected. Add Human `human_review` after delivery, then acceptance. |
| Phase/full run | Before starting activities, submit a `phase_plan` with `phase` and a concrete plan. In semi-auto/manual obtain `phase_approve` with its ID/version. Close only after every required subphase is accepted or validly N/A. |
| Missing dependencies | Record consumed evidence, assumptions and any explicit advance reason. Execute bounded provisional work; resolve inputs, revise/approve the plan and obtain reviews before acceptance. |
| Repeated phase cycle | Prepare a new phase plan; explicitly list `reused_activities` if accepted older work should count. Older work is not automatically counted. |

For a Human result review in manual mode, the event has `kind: "human_review"`, payload `{ "activity": "ACTIVITY_ID", "decision": "approved", "evidence": "Actual Human review evidence" }`, a new event UUID and rationale. Submit with `--human` only after that real review.

## If interrupted or rejected

Preserve request files and run/actor identities. Read `status`/`context`, resolve the reported cause and retry identical uncertain submissions with the original event ID. A changed request gets a new UUID. The facade has no automatic pending queue. A failed write can have recorded preceding document syncs, so inspect current state rather than assuming nothing happened.

Use `/spado --chat --run RUN_ID` or `$spado --chat --run RUN_ID` to discuss alternatives without recording events or altering files. Switch back to an explicit execution request when ready.
