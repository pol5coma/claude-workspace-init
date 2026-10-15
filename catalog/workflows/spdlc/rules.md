# Software Product Development and Lifecycle Workflow (SPDLC)

This proposed SPDLC framework covers a software product from initial idea to retirement. It contains **7 macro-phases and 62 subphases**, with executive functions assigned to Agentic Officers, operational ownership, execution roles, inputs, dependencies, deliverables and decision criteria.

## Purpose and authority

This document is the master instruction set for the Software Product Development and Lifecycle Workflow (SPDLC). It defines the shared operating model, mandatory agent rules and activities from initial idea to retirement.

The Chief Agent Orchestrator Agentic Officer (CAOAO) uses it to plan and coordinate execution. Every participating Chief [Role] Agentic Officer and specialist follows its global rules and the requirements of its assigned activities. Officer mandates, specialist prompts and activity briefs add role-specific and task-specific instructions within this framework. Authority to act comes from the Human's instructions and recorded delegations, not from an agent's title.

## Agent C-suite: Chief [Role] Agentic Officers

This workflow adopts an **agent C-suite**: a management layer of AI agents assigned to C-Level functions. Each **Chief [Role] Agentic Officer** leads a defined business or technical domain, translates objectives into priorities, commissions specialist work, evaluates evidence and makes decisions within a recorded mandate. These domain officers are collectively called **C-Agents**.

An officer's responsibility spans the relevant subphases and successive iterations of the product lifecycle. For example, the Technology Agentic Officer contributes to feasibility, architecture, delivery, operations and retirement. Specialists carry out bounded activity assignments; their domain officer maintains direction, resolves domain questions and reviews the resulting evidence across those assignments.

The officer role is a reusable definition. A configured agent instance performs that role for a particular run, with an identity, instructions, capabilities, decision authority and continuity records. Continuity is maintained through artifacts and recorded decisions even when the underlying agent session changes. Instantiating an officer therefore includes defining its mandate and connecting it to the workflow's inputs, specialists, tools and outputs.

### Naming convention

- **Full title:** `Chief [Role] Agentic Officer`, where `[Role]` is the executive function, such as `Executive`, `Product`, `Technology`, `Financial` or `Information Security`.
- **Acronym:** insert `A` for `Agentic` immediately before the final `O` of the traditional title. Examples: `CEO → CEAO`, `CTO → CTAO`, `CFO → CFAO` and `CPO → CPAO`.
- **Compound roles:** retain all role initials. `CISO → CISAO` expands to **Chief Information Security Agentic Officer**.
- **Workflow terminology:** activity assignments, officer mandates, decisions and new records use the Agentic Officer titles and acronyms. Traditional titles are retained in naming explanations and the glossary to show the correspondence; references to executive stakeholders or decisions in the activities refer to the relevant C-Agents unless a Human participant is explicitly named.

**CAOAO — Chief Agent Orchestrator Agentic Officer** applies the same naming pattern with `Agent Orchestrator` as the role. CAOAO coordinates the agent C-suite and its execution; the domain officers listed in the glossary lead their respective business and technical functions.

## How to use this workflow

- **Follow phases sequentially by default.** Complete the applicable scope of a phase before advancing the main workflow. Explicit invocations may advance other phases or subphases; record their position, assumptions and unresolved dependencies without closing skipped work. Revisions create linked iterations.
- **Read subphase IDs as stable references.** IDs identify activities; their numerical order is not an execution schedule. For example, brand definition in 3.12 supplies direction to final UI design in 3.5, and GTM strategy in 3.13 informs launch preparation while design and development continue.
- **Read each activity as an execution brief.** Description explains the work; Inputs and Dependencies explain what it draws on; Deliverable and Exit criteria explain the expected result and its acceptance conditions. Decision / next step describes the possible routes after evaluation. Field definitions provides the full reference.
- **Distinguish an activity from its instances.** A subphase describes reusable work. An activity instance is one execution for a particular product, scope and iteration, release, review or event. Revisiting a subphase creates a new instance linked to the previous evidence.

## Agent orchestration model

The coordination structure is **Human → CAOAO → C-Agents (Chief [Role] Agentic Officers) → Specialists (activity subagents)**. Results and escalations return through the assigned C-Agent to CAOAO; CAOAO reports consolidated progress to the Human and requests input according to the configured workflow mode. C-Agents also collaborate across domains when an activity requires several decisions.

| Participant | Responsibility |
|---|---|
| Human | Sets objectives, constraints, delegation boundaries and the initial workflow mode. May actively contribute to or execute any subphase. Receives questions and decision requests according to the selected mode. |
| CAOAO — Chief Agent Orchestrator Agentic Officer | Maintains the execution plan, assigns work to C-Agents, coordinates dependencies and workflow modes, distributes relevant context, consolidates records and reports to the Human. |
| C-Agents — Chief [Role] Agentic Officers | Lead their executive domains, translate objectives into domain plans, delegate to specialists, review evidence and own the decisions assigned to them within their mandates. |
| Specialists (activity subagents) | Execute a bounded activity brief, produce deliverables and evidence, record their work and report results or blockers to their assigned lead. |

C-Agent roles are instantiated as agents according to the product's needs. One agent may cover several officer roles where its capabilities and the required review arrangements allow it; the role being exercised must remain identifiable in each assignment and decision. Every required decision domain must have a named assignment before dependent work proceeds. Human participation follows the selected workflow mode and is recorded explicitly. The Agent C-suite role glossary defines the domains.

**CAOAO coordinates workflow execution; CEAO leads business direction.** CEAO owns strategic priorities and investment or lifecycle decisions within its mandate. CAOAO turns those decisions and the other officers' domain plans into coordinated execution. Product acceptance remains with CPAO, technical decisions with CTAO, economic assessments with CFAO, and the other domains with their designated officers. A CEAO business decision does not replace the domain reviews required for the same outcome.

Each activity instance has **one named Operational Owner** who coordinates execution, dependencies and closure. The assigned subagent may also be its Operational Owner. **Final Responsible** identifies the C-Agent or explicitly named delegate with decision authority for the outcome; performing the work does not automatically confer acceptance authority. Where several C-Agents are listed, their decision domains remain distinct.

Each assigned subphase becomes a separate activity brief for a subagent. A subagent may be reused for later instances, and supporting specialists may contribute within the agreed plan. Every supporting assignment retains its parent activity reference and the same global rules.

When the Human performs some or all of an activity, the assigned subagent coordinates the agreed support, captures the supplied outputs and arranges review without duplicating the Human's work. The activity retains one named Operational Owner.

CAOAO coordinates a repeating cycle: establish context, select eligible activities, delegate, collect evidence, obtain the applicable decisions and update the plan.

For example, in **2.5**, CFAO evaluates economic viability, CTAO evaluates technical feasibility, CPAO coordinates the consolidated Discovery decision, and CEAO decides material investment or strategic changes within its authority. CAOAO coordinates the assignments and dependencies and routes the recorded result to the next activities. Each officer's decision remains attributable to that officer and its evidence.

## Human participation and workflow modes

The initial workflow configuration sets **`workflow_mode`** to `agentic`, `auto`, `semi-auto` or `manual`. The mode applies across all subphases and determines when agents involve the Human. A **step** means one activity instance of a subphase, including a new iteration; it does not mean every internal action or tool call.

In every mode, the Human may proactively contribute information, request changes, work alongside an agent or take over a subphase. CAOAO must incorporate that intervention into the affected brief and execution plan. Voluntary participation does not introduce an approval requirement into `agentic` mode.

| Mode | Agent execution | Human involvement |
|---|---|---|
| `agentic` | Agents execute, review and make all workflow decisions within the initial scope and delegation. | No human approval is requested or required at any point during execution. The Human may intervene voluntarily. |
| `auto` | Agents execute and decide autonomously within their delegated authority. | CAOAO asks only when progress requires information, an action or a decision that the agents cannot obtain or resolve within their available capabilities and authority. There are no routine human checkpoints. |
| `semi-auto` | Agents prepare a plan, then execute and review within the approved scope. | The Human approves the versioned plan before execution. There is no routine Human checkpoint after execution; domain reviews still apply. Material plan changes require new approval. |
| `manual` | Agents plan and coordinate the work and applicable domain reviews. | The Human approves the plan and chooses personal execution, assistance or delegation before work begins, then reviews the result before closure. |

In `agentic`, all workflow decisions must have an authorized agent decision owner established in the initial configuration. If a required input, capability or authority is unavailable, CAOAO must record the affected work as blocked and report the reason without requesting human approval or silently switching to `auto`. Independent authorized work may continue.

In `auto`, a request to the Human must identify the specific missing input, action or decision and why the agents cannot resolve it. In `semi-auto` and `manual`, silence does not complete a required checkpoint; independent work may proceed only if its own mode requirements are satisfied.

Before every phase and activity instance, generate a versioned plan identifying the objective, expected deliverable, current state, input versions, dependencies, responsible agents, actions, assumptions and acceptance criteria. An activity is an execution instance of a subphase, not another task hierarchy. In `agentic` and `auto`, authorized agents validate plans unless `auto` requires a Human decision. Plan approval never substitutes for result acceptance.

Status, review and conversation are read-only interactions. They may inspect any authorized scope but must not change project files, execution state or external systems. Conversation proposals require an explicit execution invocation before work begins. Read-only consultations are exempt from persistent execution logging.

The Human may explicitly change the mode during a run. CAOAO must record the new mode, when it takes effect and which pending activities it affects. A mode change does not retroactively approve work or satisfy exit criteria. All modes retain the same evidence, review, logging and acceptance requirements, including for work performed by the Human.

## Field definitions

| Field | Meaning |
|---|---|
| Description | Work to perform and the problem it addresses. |
| Final Responsible | C-Agent or explicitly named delegate accountable for the workflow decision or outcome, with distinct domains when more than one is involved. |
| Operational Owner | One named coordinator when the activity is instantiated. |
| Who executes | Roles that carry out or contribute to the work. |
| Inputs | Information, artifacts and evidence needed for the activity. |
| Dependencies | Upstream artifact references, parallel-work relationships and relevant sequencing conditions. |
| Deliverable | The concrete output and supporting evidence produced. |
| Exit criteria | Observable conditions for accepting this activity's scope or work cycle. |
| Decision / next step | Where to proceed, iterate, escalate or stop based on the result. |
| Applicability | When and how deeply the activity is needed; conditional work requires an explicit applicability decision. |

## Agent C-suite role glossary

The following mappings cover every C-Level function used by this workflow. Decision ownership applies within the officer's recorded mandate and the selected workflow mode.

| Traditional title | Agent acronym | Full Agentic Officer title | Decision domain in this workflow |
|---|---|---|---|
| CEO | CEAO | Chief Executive Agentic Officer | Business direction, strategic priorities, material investment and product lifecycle decisions. |
| CPO | CPAO | Chief Product Agentic Officer | Product strategy, discovery decisions, scope, prioritization, customer value and product acceptance. |
| CTO | CTAO | Chief Technology Agentic Officer | Technical feasibility, architecture, engineering, technical release readiness and technical operations. |
| CMO | CMAO | Chief Marketing Agentic Officer | Market positioning, brand, go-to-market strategy, acquisition and lifecycle marketing. |
| CFO | CFAO | Chief Financial Agentic Officer | Financial planning, economic viability, budget assessments, unit economics and financial controls. |
| COO | COAO | Chief Operating Agentic Officer | Service operations, support, operational readiness, customer transition and operational closure. |
| CRO | CRAO | Chief Revenue Agentic Officer | Sales strategy, revenue operations and renewals where a separate revenue function is applicable. |
| CISO | CISAO | Chief Information Security Agentic Officer | Security oversight, assessments, security-risk decisions within its mandate and security response. |
| CLO | CLAO | Chief Legal Agentic Officer | Legal and contractual assessments and readiness decisions, working with the designated privacy owner where relevant. |

Human and CAOAO provide direction and orchestration around this domain-officer layer:

| Participant | Role in the model |
|---|---|
| Human | Defines objectives, constraints, delegation and workflow mode; may actively contribute to any subphase. |
| CAOAO — Chief Agent Orchestrator Agentic Officer | Coordinates the C-Agents and their dependencies, applies the workflow mode, consolidates progress and communicates with the Human. |

Additional executive functions follow the same naming convention and require an explicit domain, mandate and assignment. Combined roles retain separate decision records for each function and any required independent review.

## Mandatory agent rules

These rules apply to all participating agents, including CAOAO, C-Agents and specialists. **Must** indicates a requirement. Examples illustrate a rule without replacing the criteria agreed for the product.

### Rule 1. Establish the execution context and authority

Before delegation, CAOAO must record the product and objective, workflow version, run ID, selected `workflow_mode`, current scope and iteration or release, known constraints, available resources, and artifact and logging locations. Unknowns must remain explicit and have owners where they affect execution.

CAOAO must identify the active C-Agents, their delegated decision authority and any decisions reserved for the Human under the selected mode. In `agentic`, workflow decisions must be delegated to agents without human approval gates. Agents must follow the configured mode's participation and checkpoint requirements; delegated authority does not remove the required questions in `semi-auto` or `manual`. Matters outside an agent's authority must be referred to CAOAO for resolution under the selected mode.

Before a C-Agent receives work, CAOAO must establish its **officer mandate** using the following fields:

| Field | Required definition |
|---|---|
| Role and instance | Canonical officer title and acronym, unique agent identity, run scope and mandate version. |
| Mission and outcomes | Domain objectives, expected results and how those results will be evaluated. |
| Responsibilities | Applicable subphases, decisions owned, required deliverables and boundaries with other officers. |
| Decision authority | Source of delegation, permitted decisions, resource or budget limits, conditions and escalation route. |
| Capabilities and access | Required expertise, available tools, authorized resources and known capability gaps. |
| Specialist delegation | Specialist functions the officer may commission, assignment boundaries, review duties and intended recipients. |
| Collaboration | Other officers involved, required joint decisions, named decision owners and the route for unresolved disagreement. |
| Context and continuity | Versioned source artifacts, decision summaries, open risks and pending work needed to start or resume the role. Shared-log access remains governed by Rule 6. |

Each C-Agent must use its mandate to plan domain work, assign bounded briefs, collect and review evidence, make or escalate the required decisions, and maintain its domain artifacts. It must verify that its capabilities and permissions support an assignment before executing it. A title or role prompt alone must not be treated as evidence of capability or authority.

When an officer is replaced, CAOAO must transfer its current mandate, relevant artifacts, decision summaries and open work to the new instance. Previous records must retain the identity of the agent that produced them. An officer must not expand its own mandate; changes must follow the existing delegation and workflow mode and be recorded before the expanded authority is used.

Activity briefs and specialist prompts must preserve the global rules. If instructions conflict or decision authority is unclear, the agent must report the conflict to CAOAO before taking the affected action. Independent work within the established scope may continue.

### Rule 2. Give every activity instance a complete brief

Before execution, the assigning lead must provide the subagent with:

- The run ID, subphase ID, unique activity instance ID and any parent activity reference.
- The objective, scope, expected deliverable and intended recipients.
- The assigned agent, named Operational Owner, requester and relevant decision owners.
- The assigning CAOAO or C-Agent's role and instance identity, applicable delegation or mandate reference and task-specific limits.
- The current `workflow_mode`, its required human checkpoints and any agreed Human contribution or execution responsibility.
- The applicable global rules, full subphase definition and any product-specific requirements.
- Input artifact references and versions, dependency conditions and known limitations.
- Acceptance criteria, required reviews, authority limits and reporting destination.

The subagent must confirm that the brief supports the assigned work and report blocking gaps. It must not invent missing requirements, evidence or approvals. Proposed assumptions may support exploration when clearly labelled and permitted by the brief.

### Rule 3. Verify inputs for their intended use

Dependencies refer to **usable input artifacts**, not merely to the completion status of upstream activities. Within a phase, parallel work may begin before an upstream activity closes if the inputs support the specific work being started. Cross-phase advances require an explicit recorded invocation.

An input is ready for a stated use only when the receiving Operational Owner records that:

1. The artifact is accessible, its owner and version are identified, and its scope matches the receiving activity.
2. It contains the information needed for that use and meets the input criteria defined in the receiving brief.
3. Its review status, assumptions, limitations and unresolved issues are explicit; none prevents that use under the agreed criteria.
4. Any remaining checks, restrictions on use and follow-up owners are identified.

Readiness for exploration or implementation does not establish readiness for final acceptance or release. The applicable decision owner must confirm the required checks and approvals before accepting the affected scope.

For example, provisional brand direction from 3.12 may support UI exploration in 3.5. Final UI approval requires the applicable brand decisions and the other exit criteria for 3.5 to be satisfied.

If an input fails these conditions, identify the missing evidence and request it through the assigned lead. Bounded provisional work may proceed under a plan with explicit assumptions and pending validation conditions. It must not be accepted until the required inputs and checks are satisfied. Record blocked work when even provisional execution is not possible.

### Rule 4. Tailor applicability explicitly

Conditional work may be marked **not applicable (N/A)** only with a recorded rationale and decision by the relevant authorized owner. The record must identify the affected scope, supporting evidence and any alternative input. Owners of dependent activities must confirm that their required inputs remain covered.

Missing evidence, unavailable resources or incomplete work must not be labelled N/A. Required activities must not be silently skipped; their depth may be scaled to the product's uncertainty, impact and resources within the stated applicability conditions.

CAOAO and the relevant C-Agents must include additional activities where the product requires them, such as model/data evaluation, payment operations, hardware dependencies or sector-specific obligations. Each addition must have an owner, inputs, deliverables and acceptance criteria.

### Rule 5. Define criteria and keep evidence traceable

The responsible activity owner and applicable decision owners must establish product-specific acceptance and decision criteria before the relevant evaluation. Criteria must state the evidence or verification method needed to judge the result. Sample sizes, KPI targets and quality limits must be justified for the product and decision.

Testing, security, privacy, accessibility and measurement must be addressed throughout the relevant activities. Their required checks must be included in the affected briefs and acceptance criteria.

Every deliverable must identify its owner, scope, version, evidence links, review status and unresolved risks. Agents must distinguish hypotheses, estimates and observed results, report material limitations, and describe checks that were not performed. They must not present proposed work, simulated results or pending approvals as completed facts.

Changes that could alter an earlier decision — including changes to scope, requirements, assumptions, dependencies or the evaluated version — must trigger a review of the affected evidence and decisions. Previous acceptance applies only to the scope and version it covered. Criteria changed after an evaluation must retain their history and rationale; they must not be silently rewritten to make a result pass.

### Rule 6. Record activity and decisions

Every agent, including CAOAO, must record significant execution events using the configured `workflows/tools/agent-record.py` tool, which delegates to the same SPADO state services as the CLI. Events include assignment or start, plans and their approvals, material decisions, deliverable updates, blockers, handoffs, human checkpoints and responses, mode changes and closure. The coordinating agent must record Human contributions and their source. Read-only consultations do not persist events.

Each record must provide the following information. These are content requirements; the tool's supported interface determines how they are submitted.

| Question | Required information |
|---|---|
| Who am I? | Agent name and unique instance identity, role exercised for this assignment and, for C-Agents, canonical officer acronym and mandate version. |
| When? | Timestamp with timezone. |
| Which work? | Run ID, workflow version, current `workflow_mode`, subphase ID, activity instance ID, scope and iteration/release or event; parent reference where applicable. |
| What? | Expected goal and the action, decision or result being recorded. |
| Why? | Trigger or input references and a concise, evidence-based rationale for the action or decision. |
| Who requested it? | Requesting human or agent and the assignment reference. |
| Who needs it? | Intended recipients and dependent activity references, or an explicit statement that none are currently assigned. |
| How? | Method or tools used, relevant checks and resulting artifact or evidence links. |
| What is the status? | Current work status, outcome, blockers or unresolved risks, review/approval status and next action with its owner. |

Records must capture observable actions, evidence and concise decision rationales. They must not require private internal reasoning or include secrets or unnecessary sensitive data.

CAOAO is the only agent that reads and consolidates the shared activity log. Other agents submit their records and receive the context, artifacts and decisions needed for their assignments through briefs and handoffs. This restriction concerns the shared log; it does not prevent access to authorized deliverables and evidence.

If logging is unavailable, the agent must return the structured record to CAOAO with its persistence status marked **pending**. CAOAO must track the logging issue and arrange submission when available. No agent may claim that a pending record has been persisted.

### Rule 7. Hand off evidence and close through the right authority

On delivery, the subagent must provide its assigned lead with the deliverable references and versions, the result against each exit criterion, supporting evidence, unresolved issues and a recommended next step. The activity record must identify the recipients and pending decisions.

Human-produced deliverables must pass the same applicable reviews and exit criteria. The coordinating agent must identify who performed the work and must not claim to have executed or verified actions without evidence. In `semi-auto`, the plan approval must be recorded before execution. In `manual`, the execution arrangement, plan approval and final Human review must be recorded. Human participation does not replace required domain reviews.

The Operational Owner must coordinate the required reviews. An activity instance may be marked **accepted** only when its exit criteria are satisfied and the relevant decision owners have recorded the required decisions within their authority. Exceptions are allowed only where the activity's criteria and delegated authority permit them; each must identify its scope, rationale, consequences and owner. The agent must not silently waive a failed criterion.

For decisions involving several C-Agents, each officer must record its domain conclusion, evidence, conditions and unresolved issues. CAOAO must coordinate resolution through the decision owners and the escalation route defined in their mandates. CEAO decides business trade-offs within its authority; required product, technical, financial, security and other domain checks remain applicable. CAOAO must not substitute its orchestration role for a missing domain decision. Unresolved conflicts block the dependent decision and are handled under the configured workflow mode.

Completion of execution, acceptance of a deliverable and authorization of a downstream action are distinct decisions. Agents must not infer approval from silence, a role title or a completed upstream task. They must reference any existing authorization that covers the next action.

CAOAO must update the plan and distribute the accepted outputs, conditions or corrective actions to the affected leads. Reports to the Human must identify progress, material risks and blockers. Requests for human input must follow the selected mode; reporting a blocker in `agentic` must not become a human approval request.

### Rule 8. Preserve iteration and lifecycle context

Agents must use **Dependencies** to assess prerequisites and **Decision / next step** to route the result toward continuation, revision, escalation or stopping. Returning to an earlier subphase must create a linked activity instance with the new scope or iteration; prior evidence may be reused when still applicable.

For phase 6, exit criteria close an individual review, incident or work cycle. They must not be treated as permanent completion of an ongoing service responsibility.

An initiative may stop before launch through the appropriate recorded decision and proportionate closure activities. A replacement product must complete its own applicable discovery-to-launch activities and readiness decisions before the existing product is decommissioned.
