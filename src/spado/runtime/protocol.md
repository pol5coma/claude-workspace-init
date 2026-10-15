# SPADO state protocol

All writes use `spado workflow record --run RUN --request FILE` (or the Python
`record()` facade). FILE is a JSON object with `event_id` (unique UUID, reused only
for an identical retry), `kind`, `payload`, `rationale`, and optionally
`expected_version`. The actor is authenticated by SPADO_ACTOR_TOKEN_FILE or
SPADO_ACTOR_TOKEN, never by a role name in the request. Responses include the
execution version. Approval is a separate event targeting a plan ID and version.

Use `spado workflow context --run RUN --subphase N.N` before constructing a request.
It returns the exact deliverable, exit criterion, current dependencies and assigned
roles. `spado actor create DEFINITION --run RUN` returns a credential file for the
new agent; pass it only to that assignment. The local Human credential is used with
`--human` only for actual Human decisions or explicit initial delegation. Same-OS
administrators remain trusted; actor scopes are application permissions, not a
sandbox against a process with access to the database administrator credentials.

## Events

| kind | payload | authorized actor |
|---|---|---|
| phase_plan | phase, plan, optional mode | CAOAO/Human |
| phase_approve | phase, plan_id, version | Human in manual/semi-auto; otherwise CAOAO/Human |
| prepare | subphase, owner (actor UUID), plan, optional mode/reason/new_instance | CAOAO/Human |
| revise_plan | activity, plan | CAOAO/Human |
| approve_plan | activity, plan_id, version, arrangement in manual | Human in manual/semi-auto; otherwise CAOAO/Human |
| start | activity | assigned executor or coordinator |
| deliver | activity, outputs (revision IDs), criteria_evidence (criterion → evidence) | assigned executor or coordinator |
| domain_review | activity, decision (approved/changes_requested), evidence | responsible officer in its own identity |
| human_review | activity, decision (approved/changes_requested), evidence | Human |
| accept | activity | CAOAO/Human after all gates |
| block | activity, reason | assigned participant |
| document | path, content, optional subphase/dependencies (revision IDs) | assigned participant; use docs sync to read the file |
| promote | revision | CAOAO/Human for accepted outputs; Human for initial external documents |
| external_input | subphase, revision, evidence | responsible officer/Human |
| not_applicable | subphase, reason | responsible officer; conditional activities only |
| close_phase | phase | CAOAO; Human in manual |
| retirement | evidence | CEAO |
| mode | mode, optional phase/subphase/activity | Human |
| note | category (question/decision/execution/handoff/human_question), message, optional activity/subphase | assigned participant; global notes require CAOAO/Human |

An activity plan includes `objective`, `deliverable` (exact canonical target),
`actions` (nonempty strings), `criteria` (including the canonical exit criterion),
`inputs` (revision ID → SHA-256 digest), and `assumptions` when inputs are missing.
SPADO assigns plan identity, version and approval; do not submit approval fields.
Phase plans use the same structure with a phase-level target. They must be approved
before activity execution in phase/workflow runs. Direct subphase runs need only
the activity plan. Manual arrangements are `human`, `assisted` or `delegated`.
To reuse accepted activities from an earlier phase cycle, explicitly list their IDs
in the phase plan's `reused_activities`. Closing a new cycle does not automatically
count work performed under an older phase plan.

Record all consumed input revisions. Unrecorded relationships cannot be discovered
by structural impact analysis. Review content and return uncertainty explicitly.
SPADO also includes the accepted outputs of canonical upstream dependencies in
activity plans. When missing inputs become available, revise and approve the
provisional plan against that evidence before accepting its result. A changed phase
plan requires affected activities to restart under the current approved version.
Do not record hidden internal reasoning, credentials or unnecessary personal data.

## Read-only operations

`spado status`, `spado review`, `spado workflow context`, `spado workflow export`
and `spado docs search` do not persist state. Search may call the configured
embedding provider to encode the query; it does not rebuild the index. Conversation
must not invoke write commands. Human approval of a conversational proposal alone
does not start execution.

Use `spado docs sync PATH --run RUN [--subphase N.N] [--depends REVISION]` to record
an edited document. Changes invalidate recorded consumers and remove stale gates.
The prior official revision stays official until explicit promotion. Use
`spado docs index --run RUN` to index approved revisions. Model changes use a
separate index identity; status of incomplete indexing must remain visible.
