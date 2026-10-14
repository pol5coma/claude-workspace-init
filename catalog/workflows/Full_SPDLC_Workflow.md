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

- **Read phases as work areas.** Discovery, design, engineering and marketing can overlap and repeat as evidence develops.
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
| `semi-auto` | Agents execute each subphase autonomously and prepare its result for review. | At the end of every step, CAOAO presents the result and asks whether the Human wants changes or wants to continue. The affected step waits for a response before closure or dependent progression. Requested changes are addressed and presented again. |
| `manual` | Agents coordinate the workflow and are ready to execute each subphase. | Before starting substantive work on every step, CAOAO presents its brief and asks whether the Human wants to do it personally, work with agent assistance or delegate it fully. Execution follows that choice; the agent waits for the response before starting. |

In `agentic`, all workflow decisions must have an authorized agent decision owner established in the initial configuration. If a required input, capability or authority is unavailable, CAOAO must record the affected work as blocked and report the reason without requesting human approval or silently switching to `auto`. Independent authorized work may continue.

In `auto`, a request to the Human must identify the specific missing input, action or decision and why the agents cannot resolve it. In `semi-auto` and `manual`, silence does not complete a required checkpoint; independent work may proceed only if its own mode requirements are satisfied.

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

Dependencies refer to **usable input artifacts**, not merely to the completion status of upstream activities. Parallel work may begin before an upstream activity closes if the inputs support the specific work being started.

An input is ready for a stated use only when the receiving Operational Owner records that:

1. The artifact is accessible, its owner and version are identified, and its scope matches the receiving activity.
2. It contains the information needed for that use and meets the input criteria defined in the receiving brief.
3. Its review status, assumptions, limitations and unresolved issues are explicit; none prevents that use under the agreed criteria.
4. Any remaining checks, restrictions on use and follow-up owners are identified.

Readiness for exploration or implementation does not establish readiness for final acceptance or release. The applicable decision owner must confirm the required checks and approvals before accepting the affected scope.

For example, provisional brand direction from 3.12 may support UI exploration in 3.5. Final UI approval requires the applicable brand decisions and the other exit criteria for 3.5 to be satisfied.

If an input fails these conditions, the receiving agent must identify the missing evidence, request it through the assigned lead and mark the dependent work as blocked. Unaffected work may continue.

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

Every agent, including CAOAO, must record significant execution events using the configured `workflows/tools/agent-record.py` tool. Events include assignment or start, material decisions, deliverable updates, blockers, handoffs, human checkpoints and responses, mode changes and closure. The coordinating agent must record Human contributions and their source.

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

Human-produced deliverables must pass the same applicable reviews and exit criteria. The coordinating agent must identify who performed the work and must not claim to have executed or verified actions without evidence. In `semi-auto`, the end-of-step response must be recorded before closure or dependent progression; in `manual`, the agreed execution arrangement must have been followed. Human participation does not replace the required domain reviews.

The Operational Owner must coordinate the required reviews. An activity instance may be marked **accepted** only when its exit criteria are satisfied and the relevant decision owners have recorded the required decisions within their authority. Exceptions are allowed only where the activity's criteria and delegated authority permit them; each must identify its scope, rationale, consequences and owner. The agent must not silently waive a failed criterion.

For decisions involving several C-Agents, each officer must record its domain conclusion, evidence, conditions and unresolved issues. CAOAO must coordinate resolution through the decision owners and the escalation route defined in their mandates. CEAO decides business trade-offs within its authority; required product, technical, financial, security and other domain checks remain applicable. CAOAO must not substitute its orchestration role for a missing domain decision. Unresolved conflicts block the dependent decision and are handled under the configured workflow mode.

Completion of execution, acceptance of a deliverable and authorization of a downstream action are distinct decisions. Agents must not infer approval from silence, a role title or a completed upstream task. They must reference any existing authorization that covers the next action.

CAOAO must update the plan and distribute the accepted outputs, conditions or corrective actions to the affected leads. Reports to the Human must identify progress, material risks and blockers. Requests for human input must follow the selected mode; reporting a blocker in `agentic` must not become a human approval request.

### Rule 8. Preserve iteration and lifecycle context

Agents must use **Dependencies** to assess prerequisites and **Decision / next step** to route the result toward continuation, revision, escalation or stopping. Returning to an earlier subphase must create a linked activity instance with the new scope or iteration; prior evidence may be reused when still applicable.

For phase 6, exit criteria close an individual review, incident or work cycle. They must not be treated as permanent completion of an ongoing service responsibility.

An initiative may stop before launch through the appropriate recorded decision and proportionate closure activities. A replacement product must complete its own applicable discovery-to-launch activities and readiness decisions before the existing product is decommissioned.


# Workflow:

## 1. Idea & Strategy

Frame the opportunity, make assumptions explicit and authorize a bounded investment in Discovery.

### 1.1. Initial ideation and opportunity assessment

- **Description:** Generate, collect and screen product ideas. Identify the opportunity behind each idea and assess its strategic fit, potential impact, differentiation and obvious constraints using available information.
- **Final Responsible:** CEAO, in collaboration with CPAO.
- **Operational Owner:** Founder / Business Lead.
- **Who executes:** Founder/Business Lead, Product Manager and relevant stakeholders, with Marketing, Finance and Engineering input.
- **Inputs:** Initial ideas, business context, observed problems, existing capabilities and known constraints.
- **Dependencies:** No upstream activity required for a new initiative. Root activity for a new product. Existing-product opportunities can also enter from 6.8 or 6.12 as a new iteration.
- **Deliverable:** Shortlisted ideas, initial opportunity statements, selection criteria and rationale for the opportunity chosen for investigation.
- **Exit criteria:** At least one opportunity has a clear problem hypothesis, intended beneficiary and selection rationale; rejected ideas and major unknowns are recorded.
- **Decision / next step:** Advance selected opportunities to 1.2 and 1.3; revisit ideas or stop if none warrants investigation.
- **Applicability:** Required; scale the depth to the product's uncertainty, impact and resources.

### 1.2. Define product vision and strategic goals

- **Description:** Define the intended long-term direction of the product, its connection to business objectives and the outcomes it should achieve. Establish initial success criteria and strategic boundaries.
- **Final Responsible:** CEAO for business direction; CPAO for product vision and goals.
- **Operational Owner:** Product Manager.
- **Who executes:** Product Manager and Business/Strategy Lead, working with executive stakeholders.
- **Inputs:** Selected opportunity, business direction, organizational goals and stakeholder expectations.
- **Dependencies:** Upstream references: 1.1. Develop with 1.3 and revisit after Discovery; goals remain provisional until evidence improves.
- **Deliverable:** Product vision statement, strategic objectives, initial outcome metrics and guiding product principles.
- **Exit criteria:** Vision, intended outcomes, strategic boundaries and initial success measures are understandable and agreed by the designated business and product decision owners.
- **Decision / next step:** Use the agreed direction in 1.4 and 1.6; return to 1.1 if the opportunity does not fit.
- **Applicability:** Required; scale the depth to the product's uncertainty, impact and resources.

### 1.3. Define initial target audience and value proposition

- **Description:** Form initial hypotheses about target users, buyers and their problems. Describe the value the product could provide, why customers might choose it and how it could differ from existing alternatives.
- **Final Responsible:** CPAO, in collaboration with CMAO.
- **Operational Owner:** Product Marketing Manager.
- **Who executes:** Product Manager and Product Marketing Manager, with UX Researcher input.
- **Inputs:** Opportunity hypothesis, existing audience information, proposed problem and business context.
- **Dependencies:** Upstream references: 1.1. Work with 1.2; these are audience and value hypotheses to test in phase 2, not validated personas.
- **Deliverable:** Initial user and buyer segment hypotheses, problem statements, value proposition and differentiation hypotheses.
- **Exit criteria:** Users and buyers are distinguished where relevant; the proposed problem, value and differentiation are explicit and assumptions are labelled.
- **Decision / next step:** Feed 1.4 and 2.1; narrow or revise the segment if the proposition is too broad.
- **Applicability:** Required; scale the depth to the product's uncertainty, impact and resources.

### 1.4. Define the business model

- **Description:** Outline how the product could create, deliver and capture value. Identify potential revenue streams, pricing approaches, distribution channels, key partners and major cost drivers. Keep assumptions explicit until evidence is available.
- **Final Responsible:** CEAO, in collaboration with CFAO, CPAO and CMAO.
- **Operational Owner:** Business / Strategy Lead.
- **Who executes:** Business/Strategy Analyst, Finance Analyst, Product Manager and Product Marketing Manager.
- **Inputs:** Product direction, audience/value hypotheses, potential revenue mechanisms, channels and rough cost drivers.
- **Dependencies:** Upstream references: 1.2, 1.3. Iterate with 1.5 and 1.6; quantify uncertainty rather than presenting early forecasts as actual results.
- **Deliverable:** Initial business model, monetization and pricing hypotheses, cost structure and preliminary economic assumptions.
- **Exit criteria:** The model explains value delivery, funding or revenue, major costs and critical dependencies, with assumptions and alternatives visible.
- **Decision / next step:** Feed 1.6 and 2.5; revise the proposition or business model if no plausible sustainable option is identified.
- **Applicability:** Required; scale the depth to the product's uncertainty, impact and resources.

### 1.5. Identify strategic assumptions, risks and constraints

- **Description:** Identify what must be true for the opportunity to succeed. Surface market, adoption, economic, technical and operational uncertainties, plus applicable legal, licensing, privacy and data-use constraints. Record budget, timing and organizational boundaries, and prioritize the assumptions Discovery should investigate first.
- **Final Responsible:** CPAO for consolidated discovery priorities, with CEAO, CFAO, CTAO and CMAO owning decisions within their areas and the designated legal/privacy owner assessing applicable constraints.
- **Operational Owner:** Product Manager.
- **Who executes:** Product Manager, UX Researcher, Business/Finance Analyst and Tech Lead, with relevant specialists.
- **Inputs:** Opportunity brief, known organizational constraints, emerging audience and business-model assumptions, and intended data or third-party use.
- **Dependencies:** Upstream references: 1.1. Maintain while 1.2–1.4 develop. Request relevant specialist input early for constraints capable of invalidating the opportunity.
- **Deliverable:** Prioritized assumptions and risks, known constraints, initial data-use and licensing questions, validation priorities and decision criteria for continuing, changing direction or stopping.
- **Exit criteria:** High-impact assumptions and constraints have owners, evidence status, an investigation priority and proposed decision criteria.
- **Decision / next step:** Use the risk priorities in 1.6 and 2.1; resolve critical constraints before making dependent commitments.
- **Applicability:** Required; scale the depth to the product's uncertainty, impact and resources.

### 1.6. Define the initial budget and resource allocation

- **Description:** Allocate the funding, people and time needed for Discovery and early validation. Establish spending boundaries, decision checkpoints and an indicative investment envelope for later stages, subject to discovery findings.
- **Final Responsible:** CEAO for investment approval; CFAO for financial planning.
- **Operational Owner:** Finance Lead / Finance Analyst.
- **Who executes:** Finance Analyst, Product Manager and relevant functional leads, with CTAO and CMAO input.
- **Inputs:** Strategic goals, preliminary business model, prioritized uncertainties and proposed Discovery work.
- **Dependencies:** Upstream references: 1.2, 1.4, 1.5. Fund learning first; later development and marketing allocations are reviewed after Discovery and updated planning.
- **Deliverable:** Approved discovery budget, initial resource allocation, indicative timeline, funding assumptions and agreed investment review checkpoints.
- **Exit criteria:** Discovery has an approved resource envelope, named capacity, review dates and an investment decision owner; funding conditions are explicit.
- **Decision / next step:** Authorize 2.1 within the agreed envelope; reduce scope, seek an investment decision or pause if resources are insufficient.
- **Applicability:** Required; scale the depth to the product's uncertainty, impact and resources.

## 2. Discovery

Establish evidence about the problem, solution concepts, demand, economics and feasibility, then record a cross-functional decision.

### 2.1. Market and user research

- **Description:** Investigate the market, potential user segments, relevant stakeholders, existing alternatives and competitors. Understand users’ contexts, behaviours, needs and current ways of addressing the problem.
- **Final Responsible:** CPAO, in collaboration with CMAO.
- **Operational Owner:** UX Researcher.
- **Who executes:** UX Researcher, Product Manager and Product Marketing Manager, with Market/Data Analyst support when needed.
- **Inputs:** Initial audience and problem hypotheses, strategic constraints, research priorities and Discovery resources.
- **Dependencies:** Upstream references: 1.3, 1.5, 1.6. Coordinate market and user research in one evidence repository. Protect participant information and use appropriate recruiting and consent arrangements.
- **Deliverable:** Market and competitor analysis, initial user segmentation, stakeholder map, research findings and problem hypotheses.
- **Exit criteria:** Relevant users, buyers, stakeholders and alternatives have been investigated with a documented method, sample, findings and limitations.
- **Decision / next step:** Feed 2.2; refine segments or conduct targeted follow-up if the evidence is not relevant or sufficient.
- **Applicability:** Required; scale the depth to the product's uncertainty, impact and resources.

### 2.2. Problem validation

- **Description:** Test whether the identified problem exists for the target users and assess its frequency, severity and impact. Understand dissatisfaction with existing alternatives and identify which problems are worth prioritizing.
- **Final Responsible:** CPAO.
- **Operational Owner:** Product Manager.
- **Who executes:** UX Researcher and Product Manager, with Product/Data Analyst support.
- **Inputs:** Research findings, observed behaviours, existing alternatives and initial problem statements.
- **Dependencies:** Upstream references: 2.1. Problem validation may trigger more research. Predetermine what evidence would support, weaken or reject each important hypothesis.
- **Deliverable:** Evidence-backed problem statements, prioritized user needs, findings that support or challenge the hypotheses, and remaining uncertainties.
- **Exit criteria:** Priority problems have evidence of significance and context, disconfirming findings and limitations are recorded, and a proceed/revise/stop recommendation is justified.
- **Decision / next step:** Explore plausible solutions in 2.3; revisit 2.1 or stop if the problem is not worth solving.
- **Applicability:** Required; scale the depth to the product's uncertainty, impact and resources.

### 2.3. Explore solution concepts

- **Description:** Identify and compare alternative solution concepts and candidate features addressing the prioritized problems. Explore their expected user value, assumptions and risks, and run early concept tests with relevant users before committing to a solution.
- **Final Responsible:** CPAO.
- **Operational Owner:** Product Designer.
- **Who executes:** Product Manager, Product Designer and UX Researcher, with Tech Lead and Product Marketing Manager input.
- **Inputs:** Prioritized problems, user context, strategic constraints and relevant existing alternatives.
- **Dependencies:** Upstream references: 2.2. Use low-cost concepts and early user tests; consult Engineering and Product Marketing before selecting a direction. Detailed design follows in phase 3.
- **Deliverable:** Solution concepts, candidate feature hypotheses, lightweight sketches or concept prototypes, early concept-test findings and a shortlist of options with remaining uncertainties.
- **Exit criteria:** At least one promising concept has an explicit value hypothesis, initial user feedback, comparison with alternatives and visible unresolved risks.
- **Decision / next step:** Test demand in 2.4 and investigate feasibility in 2.5; revise concepts or return to the problem evidence if necessary.
- **Applicability:** Required; scale the depth to the product's uncertainty, impact and resources.

### 2.4. Evaluate demand

- **Description:** Assess whether target users would adopt the proposed solution and whether buyers would pay where applicable. Test the value proposition, willingness to switch, pricing assumptions and ability to reach the intended audience through appropriate experiments.
- **Final Responsible:** CMAO, in collaboration with CPAO.
- **Operational Owner:** Product Marketing Manager.
- **Who executes:** Product Marketing Manager, Product Manager and Growth Marketer, with UX Researcher and Data Analyst support.
- **Inputs:** Candidate concepts, audience evidence, business-model and pricing hypotheses, and resources authorized for demand experiments.
- **Dependencies:** Upstream references: 2.3, 1.4. Coordinate experiments with economic/technical investigation in 2.5; distinguish research interest, waitlist signals, commitments and actual purchases.
- **Deliverable:** Demand-validation findings, evidence of adoption or purchase interest, initial acquisition-channel hypotheses, and documented limitations distinguishing stated intent from actual commitments.
- **Exit criteria:** Adoption and, where relevant, purchase hypotheses have been tested against predefined criteria; evidence strength, sample and uncertainty are reported.
- **Decision / next step:** Feed the joint decision in 2.5; revise the offer, concept, target segment or route to market if demand evidence is insufficient.
- **Applicability:** Required; scale the depth to the product's uncertainty, impact and resources.

### 2.5. Evaluate economic viability and technical feasibility

- **Description:** Assess whether proposed solutions could support a sustainable business and be built and operated within realistic constraints. Estimate revenue potential, acquisition and operating costs, development effort, critical dependencies and technical risks. Consolidate problem, concept and demand evidence into an explicit cross-functional Discovery decision.
- **Final Responsible:** CFAO for economic viability; CTAO for technical feasibility; CPAO for coordinating the overall Discovery decision, with CEAO approval for material investment or strategic changes.
- **Operational Owner:** Product Manager.
- **Who executes:** Finance/Business Analyst, Product Manager, Tech Lead and Software Architect, with Engineering and Operations input.
- **Inputs:** Problem evidence, concept findings, demand results, initial cost/revenue assumptions, technical constraints and specialist assessments.
- **Dependencies:** Upstream references: 2.2, 2.3, 2.4, 1.5. Feasibility investigation can begin alongside 2.3–2.4; the final Discovery decision consolidates all four dimensions: problem relevance, demand, economics and feasibility.
- **Deliverable:** Preliminary business case, assumption-based unit economics and financial scenarios, initial technical feasibility assessment, consolidated Discovery evidence, major risks and a recorded decision to proceed, investigate further, reformulate or stop.
- **Exit criteria:** The evidence and material uncertainties are consolidated; the designated product, business and technical decision owners record whether to proceed, investigate further, reformulate or stop, including any conditions.
- **Decision / next step:** Proceed to 3.1 for an agreed opportunity; route unanswered questions to the relevant Discovery activity, revise phase 1 assumptions or close the initiative.
- **Applicability:** Required; scale the depth to the product's uncertainty, impact and resources.

## 3. Definition and Design

Define and validate the next useful product increment, its quality and technical approach, the brand and its route to market.

**Sequencing note:** 3.12 and 3.13 preserve the existing numbering; follow their dependencies rather than postponing this work until the end of phase 3.

### 3.1. Define scope and priorities

- **Description:** Define the scope, what is included and excluded, and the smallest useful product increment to deliver first. Prioritize outcomes and features using customer value, evidence, effort, risk and dependencies.
- **Final Responsible:** CPAO.
- **Operational Owner:** Product Manager.
- **Who executes:** Product Manager, Design team and Engineering team.
- **Inputs:** Recorded Discovery decision, prioritized problems, solution evidence, strategic goals and resource constraints.
- **Dependencies:** Upstream references: 2.5, 1.2. Define the next useful increment; consult Engineering, Design and Marketing on value, effort and dependencies rather than fixing every future feature.
- **Deliverable:** Prioritized scope, explicit exclusions, initial product increment and rationale linking priorities to intended outcomes.
- **Exit criteria:** Included and excluded scope, intended outcomes, priority rationale and the first useful increment are agreed; unresolved assumptions have owners.
- **Decision / next step:** Feed 3.2, 3.3, 3.7 and 3.10; revisit Discovery for unsupported scope or phase 1 for investment changes.
- **Applicability:** Required; scale the depth to the product's uncertainty, impact and resources.

### 3.2. Specify behaviour

- **Description:** Specify features, business rules, roles and permissions, entity and workflow states, state transitions, exceptions and edge cases. Define observable acceptance criteria and distinguish required behaviour from implementation choices.
- **Final Responsible:** CPAO.
- **Operational Owner:** Product Manager / Business Analyst.
- **Who executes:** Product Manager / Business Analyst, with Design and Engineering input.
- **Inputs:** Agreed increment scope, user and buyer needs, business context and relevant existing process rules.
- **Dependencies:** Upstream references: 3.1. Co-develop with UX and Engineering. Keep rules, states, permissions and acceptance examples linked to features and outcomes.
- **Deliverable:** Functional requirements (FR), business rules, state and permission models, business flows, exception scenarios and acceptance criteria linked to the agreed scope.
- **Exit criteria:** The next increment's critical behaviours, permissions, state transitions and exception cases are defined well enough to design and test; contradictions and blocking unknowns are resolved.
- **Decision / next step:** Feed UX, technical design and validation planning; revise scope or investigate unresolved business rules before dependent implementation.
- **Applicability:** Required; scale the depth to the product's uncertainty, impact and resources.

### 3.3. Define quality requirements

- **Description:** Define measurable quality requirements for performance, expected capacity, availability, reliability, compatibility, security, privacy and accessibility as relevant to the product. Agree recovery objectives, data-handling constraints and the conditions under which each requirement will be verified. Use product-specific thresholds and label unvalidated assumptions.
- **Final Responsible:** CTAO for technical quality requirements, in collaboration with CPAO, COAO, Security, Design and the designated legal/privacy owner.
- **Operational Owner:** Tech Lead.
- **Who executes:** Tech Lead, Security team, design team, and operations team.
- **Inputs:** Scope, operating expectations, critical journeys, Discovery risks and applicable specialist constraints.
- **Dependencies:** Upstream references: 1.5, 2.5, 3.1. Agree measurable thresholds with Product, Operations, Security and Design. Document expected load, measurement conditions, recovery expectations and justified exclusions.
- **Deliverable:** Verifiable non-functional requirements (NFR), product-specific quality thresholds and test conditions, initial service and recovery objectives, and applicable security, accessibility and privacy requirements.
- **Exit criteria:** Applicable quality requirements have measurable criteria, verification methods and owners; assumptions, cost implications and risk acceptance are explicit.
- **Decision / next step:** Feed 3.6, 3.11, 4.6 and 4.7; adjust scope or investment if required quality cannot be supported.
- **Applicability:** Required; scale the depth to the product's uncertainty, impact and resources.

### 3.4. Design the experience (UX)

- **Description:** Design the user experience, navigation, paths, interactions, content and error handling.
- **Final Responsible:** CPAO.
- **Operational Owner:** Product Designer.
- **Who executes:** UX Designer, UX Researcher and UX Writer.
- **Inputs:** Functional requirements, business flows, user research and prioritized experience problems.
- **Dependencies:** Upstream references: 3.2, 2.2. Explore with 3.8 at low fidelity; coordinate with brand and content work and include error, permission and relevant accessibility behaviours.
- **Deliverable:** Information architecture, user flows, and wireframes.
- **Exit criteria:** Priority journeys and information structure cover normal and significant exception paths; the intended content and interaction logic are understandable for the next increment.
- **Decision / next step:** Feed 3.5 and 3.8; return to requirements or research when experience gaps expose unresolved needs.
- **Applicability:** Required; scale the depth to the product's uncertainty, impact and resources.

### 3.5. Design the user interface

- **Description:** Design screens, visual hierarchy, reusable components, interaction states and responsive behaviour, ensuring consistency with the brand and accessibility requirements.
- **Final Responsible:** CPAO, in coordination with CMAO.
- **Operational Owner:** Product / UI Designer.
- **Who executes:** Product/UI Designer and Brand Designer, with Engineering input on feasibility.
- **Inputs:** User flows and wireframes, brand identity, content direction, accessibility requirements and target device contexts.
- **Dependencies:** Upstream references: 3.4, 3.12, 3.3. Brand work in 3.12 supplies direction before final UI approval. Explore iteratively with prototypes; reuse an existing design system where suitable.
- **Deliverable:** Visual designs, screen and component states, responsive specifications and a design system.
- **Exit criteria:** Required screens, responsive behaviour and relevant component states are specified and reviewed for brand consistency, usability, accessibility and implementation feasibility.
- **Decision / next step:** Feed 3.8 and 4.2; resolve significant review findings before approving the affected interface scope.
- **Applicability:** Conditional on a visual product interface; reuse established design assets when appropriate. For headless services, document N/A and specify consumer-facing contracts in 3.2 and 3.6.

### 3.6. Design the technical solution

- **Description:** Define the initial software architecture, system components, data model, interfaces and integrations. Evaluate technical trade-offs against functional and non-functional requirements. Specify trust boundaries, key threats, data sources and permitted uses, access ownership, retention and deletion behaviour, and relevant third-party or licensing constraints.
- **Final Responsible:** CTAO.
- **Operational Owner:** Tech Lead / Software Architect.
- **Who executes:** Software Architects, Tech Lead and Engineering team, with Security and Operations input.
- **Inputs:** Functional and quality requirements, integration constraints, data needs, feasibility findings and available organizational capabilities.
- **Dependencies:** Upstream references: 3.2, 3.3. Develop with 3.9. Assess data lifecycle, trust boundaries and third-party choices before committing to designs with high reversal costs.
- **Deliverable:** Initial technical architecture, data model, API and integration contracts, data-flow and lifecycle specifications, security design and threat assessment, and documented technical decisions and trade-offs.
- **Exit criteria:** The architecture supports the first increment and quality requirements; interfaces, data responsibilities and trade-offs are explicit, with critical design risks resolved or accepted by the relevant authority.
- **Decision / next step:** Feed 3.11 and engineering setup; use 3.9 for unresolved feasibility questions or return to requirements where constraints require a product change.
- **Applicability:** Required; scale the depth to the product's uncertainty, impact and resources.

### 3.7. Align product & offer

- **Description:** Align features per plan, pricing and packaging proposals, positioning, messaging and commercial promises with the defined product scope and business model.
- **Final Responsible:** CMAO, in collaboration with CPAO and CFAO; final pricing approval follows the agreed business decision authority.
- **Operational Owner:** Product Marketing Manager.
- **Who executes:** Product Marketing Manager and Product Manager, with Finance input.
- **Inputs:** Prioritized product scope, demand and pricing evidence, business-model hypotheses and audience understanding.
- **Dependencies:** Upstream references: 3.1, 2.4, 1.4. Coordinate with Finance and Product; keep planned, validated and available capabilities distinct. This defines the offer; 3.13 defines its route to market.
- **Deliverable:** Product offering and packaging proposal, feature-to-plan mapping, positioning and messaging aligned with the product’s actual capabilities.
- **Exit criteria:** The initial offer, packaging, claims and proposed pricing fit the scope and audience; required pricing decisions and unsupported promises are resolved or clearly pending with owners.
- **Decision / next step:** Feed brand definition in 3.12, GTM strategy in 3.13 and launch materials; revisit scope, demand tests or business assumptions when misaligned.
- **Applicability:** Required; scale the depth to the product's uncertainty, impact and resources.

### 3.8. Prototype and validate the experience

- **Description:** Build prototypes at the fidelity needed to test the proposed experience. Evaluate comprehension, usefulness and usability with relevant users, record limitations and iterate on significant findings.
- **Final Responsible:** CPAO.
- **Operational Owner:** UX Researcher.
- **Who executes:** Product Designer, UX Researcher and Product Manager.
- **Inputs:** User flows, acceptance criteria, appropriate prototype fidelity, recruiting criteria and research questions.
- **Dependencies:** Upstream references: 3.4, 3.2. Use 3.5 designs when visual fidelity is relevant; low-fidelity tests can start earlier. Study results apply to the tested audience and tasks, not to guaranteed market demand.
- **Deliverable:** Tested prototypes, research findings and limitations, prioritized adjustments and a recorded decision on the proposed experience.
- **Exit criteria:** Critical tasks and messages have been tested with relevant participants; significant findings are resolved, retested or explicitly accepted, with limitations documented.
- **Decision / next step:** Refine 3.2, 3.4 or 3.5 as needed; provide validated experience evidence to 3.11 and the implementation team.
- **Applicability:** Required; scale the depth to the product's uncertainty, impact and resources.

### 3.9. Resolve technical uncertainty

- **Description:** Identify and investigate critical technical assumptions, integration constraints and feasibility risks. Use focused technical spikes or proofs of concept where evidence is needed before committing to implementation.
- **Final Responsible:** CTAO.
- **Operational Owner:** Tech Lead.
- **Who executes:** Tech Lead, Software Architects and relevant engineers, with specialists as needed.
- **Inputs:** Initial feasibility assessment, critical requirements, candidate technical approaches and prioritized technical unknowns.
- **Dependencies:** Upstream references: 2.5, 3.2, 3.3. Run bounded investigations alongside 3.6. Prototype code is not assumed production-ready; focus effort on uncertainties affecting a decision.
- **Deliverable:** Technical feasibility findings, proof-of-concept results, recommended approaches, and remaining risks with mitigation actions.
- **Exit criteria:** Each investigated critical assumption has a result, limitations and a decision; remaining risks have owners and do not silently invalidate the chosen implementation approach.
- **Decision / next step:** Update 3.6 and 3.11; revise scope or revisit Discovery if technical constraints undermine the value or economics.
- **Applicability:** Conditional: focused spikes or proofs of concept are required only for material unresolved uncertainty. Otherwise record why existing evidence is sufficient.

### 3.10. Define measurement

- **Description:** Define how product success and user behaviour will be measured. Specify outcome metrics, activation criteria, funnel stages, events and data requirements, distinguishing observed results from assumptions.
- **Final Responsible:** CPAO, in collaboration with CMAO and CTAO.
- **Operational Owner:** Product / Data Analyst.
- **Who executes:** Product/Data Analyst and Product Manager, with Growth Marketing and Engineering input.
- **Inputs:** Strategic outcomes, initial product scope, critical user journeys and demand/channel hypotheses.
- **Dependencies:** Upstream references: 1.2, 3.1, 2.4. Coordinate Product, Marketing, Engineering and privacy needs. Separate first-value activation from onboarding completion and observed data from forecasts.
- **Deliverable:** Measurement plan, metric definitions, analytics event specifications and an initial reporting plan.
- **Exit criteria:** Priority outcomes have metric definitions, populations/windows, required events/data, ownership and decision use; collection is feasible and respects agreed data constraints.
- **Decision / next step:** Feed 3.13, 4.8 and launch evaluation; simplify or revise measures that cannot support a useful decision.
- **Applicability:** Required; scale the depth to the product's uncertainty, impact and resources.

### 3.11. Plan development

- **Description:** Break the agreed scope into incremental deliveries. Identify dependencies, estimate effort and uncertainty, allocate capacity and define acceptance and release criteria. Prepare sufficient detail for the first increment, including a risk-based validation approach and clear ownership of relevant tests and reviews.
- **Final Responsible:** CPAO for product priorities and scope; CTAO for technical delivery planning and engineering capacity.
- **Operational Owner:** Engineering Manager / Tech Lead.
- **Who executes:** Product Manager, Engineering Manager and Tech Lead, with Design, Engineering, QA and Operations input.
- **Inputs:** Prioritized scope, requirements, architecture, prototype findings, technical-risk evidence, measurement needs and available capacity.
- **Dependencies:** Upstream references: 3.1, 3.2, 3.3, 3.6, 3.8, 3.9, 3.10. Coordinate with 3.13 for commercial timing; prepare detail for the next increment and refine later work as evidence changes. Record accepted N/A for conditional inputs.
- **Deliverable:** Prioritized backlog, initial delivery plan, dependency map, effort estimates, resource allocation, risk-based validation approach and agreed acceptance and release criteria.
- **Exit criteria:** The first increment has owners, workable dependencies, bounded estimates, acceptance criteria and a risk-based test/review approach; funding and capacity constraints are addressed.
- **Decision / next step:** Start 4.1 and incremental delivery within the authorized scope; revise priorities, technical approach or resource allocation where planning exposes a blocker.
- **Applicability:** Required; scale the depth to the product's uncertainty, impact and resources.

### 3.12. Define brand identity and communication principles

- **Description:** Translate product positioning and audience understanding into a coherent brand identity. Define brand personality, voice, visual direction, naming where needed, and principles for expressing the brand across product and marketing touchpoints. Reuse and adapt an existing identity when appropriate.
- **Final Responsible:** CMAO for brand direction, in coordination with CPAO for product experience.
- **Operational Owner:** Brand / Creative Lead.
- **Who executes:** Brand/Creative Lead, Brand Designer and Copywriter, with Product Marketing, Product Design and UX Writing input.
- **Inputs:** Strategic direction, target-audience evidence, positioning, offer definition and any existing brand assets.
- **Dependencies:** Upstream references: 1.2, 1.3, 3.7. Start alongside UX exploration; provide usable direction to 3.5 before final UI approval and to 5.3 before marketing assets are finalized.
- **Deliverable:** Brand brief, approved visual identity and tone-of-voice guidelines, initial brand assets, naming decisions where relevant and shared product/marketing usage principles.
- **Exit criteria:** Brand voice, visual direction and usage principles are approved at the required depth; product and marketing can apply them consistently, with naming/licensing questions resolved where applicable.
- **Decision / next step:** Feed 3.5 and 5.3; revise brand decisions if comprehension tests or the offer reveal material inconsistency.
- **Applicability:** Required at proportionate depth; adapt an existing brand where appropriate. Naming and full identity creation are conditional, not mandatory reinvention.

### 3.13. Define the go-to-market strategy

- **Description:** Translate positioning, demand evidence and the product scope into a practical route to market. Select initial segments and use cases, acquisition and distribution channels, sales or self-service motion, launch objectives, budget allocation and lifecycle approach. Define hypotheses, experiments and readiness criteria before campaign execution.
- **Final Responsible:** CMAO for go-to-market strategy, with CPAO confirming product scope, CFAO reviewing budget and economics, and CRAO owning sales strategy where applicable.
- **Operational Owner:** Product Marketing Manager.
- **Who executes:** Product Marketing Manager, Growth Marketing Lead and Product Manager, with Sales, Customer Success, Finance and Data input.
- **Inputs:** Offer and positioning, demand/channel evidence, business goals, measurement definitions, financial constraints and draft delivery timing.
- **Dependencies:** Upstream references: 3.7, 2.4, 3.10, 1.6. Develop alongside 3.11; test channels and messages within approved budgets while product design and development continue. Internal products use an adoption and rollout plan.
- **Deliverable:** GTM strategy, prioritized segments and channels, commercial motion, launch and lifecycle objectives, approved or explicitly pending budget assumptions, initial experiment portfolio and marketing readiness criteria.
- **Exit criteria:** Initial segments, route to market, owners, budget status, launch/lifecycle objectives, experiments and readiness criteria are explicit and aligned with product capability and economics.
- **Decision / next step:** Feed launch coordination and commercial preparation in phase 5; return to 2.4 or 3.7 for unproven demand or positioning, or seek a budget decision before commitments.
- **Applicability:** Required as a route-to-adoption plan; paid campaigns, sales motions, partnerships and external marketing apply only when relevant to the product.

## 4. Development and Validation

Build and validate increments, prepare operations and produce a release candidate with explicit readiness evidence.

### 4.1. Prepare development environments and delivery foundations

- **Description:** Establish repositories, development and testing environments, configuration management, access controls and CI/CD pipelines. Define the engineering conventions and automated checks needed to build and validate product increments consistently.
- **Final Responsible:** CTAO.
- **Operational Owner:** Platform / DevOps Lead.
- **Who executes:** Tech Lead, Engineering team and Platform/DevOps Engineers, with Security input.
- **Inputs:** Initial architecture, security/quality requirements, delivery plan and environment/access needs.
- **Dependencies:** Upstream references: 3.6, 3.3, 3.11. Prepare only the foundations needed for safe incremental delivery; reusable organizational infrastructure can satisfy this activity after verification.
- **Deliverable:** Working development and testing environments, configured delivery pipelines, repository conventions and environment setup documentation.
- **Exit criteria:** The team can build and test reproducibly with appropriate access, secret/configuration handling and automated checks; environment setup and ownership are documented.
- **Decision / next step:** Enable 4.2–4.8; resolve environment or access blockers before affected development work.
- **Applicability:** Required; scale the depth to the product's uncertainty, impact and resources.

### 4.2. Implement product features incrementally

- **Description:** Implement prioritized features across frontend, backend and relevant platforms. Apply the agreed business rules, permissions, designs and acceptance criteria, including error handling and relevant interface states.
- **Final Responsible:** CTAO for implementation; CPAO for scope and requirement decisions.
- **Operational Owner:** Tech Lead.
- **Who executes:** Engineering team and Tech Lead, collaborating with Product Manager and Product Designer.
- **Inputs:** Prioritized backlog, behaviour and acceptance criteria, applicable UI specifications, architecture and delivery foundations.
- **Dependencies:** Upstream references: 3.2, 3.5, 3.6, 3.11, 4.1. Build small increments with ongoing reviews and tests in 4.4–4.7. Approved N/A for visual UI must not remove required API or workflow specifications.
- **Deliverable:** Working product increments, implementation-level tests, updated technical documentation and traceability to requirements.
- **Exit criteria:** An increment implements the agreed behaviour and includes relevant tests and documentation; its change set is ready for the applicable review and validation activities.
- **Decision / next step:** Route each increment through 4.4–4.9; clarify scope with Product or revise design rather than silently changing acceptance criteria.
- **Applicability:** Required; scale the depth to the product's uncertainty, impact and resources.

### 4.3. Implement integrations and data handling

- **Description:** Connect internal components and external services. Implement data storage, validation, synchronization and failure handling. Prepare and test imports or migrations where required, including data reconciliation and recovery procedures.
- **Final Responsible:** CTAO.
- **Operational Owner:** Backend / Integration Lead.
- **Who executes:** Backend/Integration Engineers, Data Engineers and relevant specialists, with QA and Security input.
- **Inputs:** Interface contracts, data model and lifecycle rules, external-service constraints, test environments and failure requirements.
- **Dependencies:** Upstream references: 3.2, 3.6, 3.3, 4.1. Coordinate with feature implementation. Plan import/migration verification and recovery only when relevant, including vendor or external-system dependencies.
- **Deliverable:** Tested integrations and data flows, verified interface contracts, and migration or import procedures where applicable.
- **Exit criteria:** Applicable integrations and data paths work under expected and significant failure conditions; contracts, reconciliation checks and recovery implications are documented and tested.
- **Decision / next step:** Feed 4.5–4.7 and release preparation; escalate incompatible external constraints to technical or product design.
- **Applicability:** Required for applicable data handling and integrations; external-service, import and migration work is conditional on actual product needs.

### 4.4. Review code quality and maintainability

- **Description:** Review changes continuously for correctness, clarity, architectural consistency and maintainability. Run appropriate automated checks, address review findings and document significant implementation decisions or accepted technical debt.
- **Final Responsible:** CTAO.
- **Operational Owner:** Tech Lead.
- **Who executes:** Peer Engineers, Tech Lead and Software Architect where applicable.
- **Inputs:** Incremental changes, engineering conventions, architecture decisions, automated checks and affected requirements.
- **Dependencies:** Upstream references: 4.1, 4.2. Review throughout implementation, not after all features are finished. Request additional specialist review for changes affecting critical boundaries.
- **Deliverable:** Reviewed changes, automated quality-check results, documented technical decisions and tracked technical debt.
- **Exit criteria:** Required peer and automated checks pass for the reviewed change; blocking findings are resolved and accepted debt or exceptions have owners.
- **Decision / next step:** Allow eligible changes into the release candidate; return findings to 4.2 or 4.3 and update relevant technical decisions.
- **Applicability:** Required; scale the depth to the product's uncertainty, impact and resources.

### 4.5. Perform functional and regression testing

- **Description:** Verify that features, business rules, permissions and integrations behave as specified. Test critical end-to-end journeys, failure scenarios and regressions, combining automated and exploratory testing according to risk.
- **Final Responsible:** CTAO, with CPAO clarifying expected product behaviour.
- **Operational Owner:** QA Lead.
- **Who executes:** QA Engineers, Engineering team and Product Manager.
- **Inputs:** Functional requirements and acceptance criteria, testable increments, relevant integrations, test data and risk-based validation approach.
- **Dependencies:** Upstream references: 3.2, 4.1, 4.2, 4.3. Run unit/component, integration, end-to-end and exploratory checks where they provide useful coverage. Conditional integrations require recorded N/A when absent.
- **Deliverable:** Test results linked to requirements, reusable automated tests, defect reports and verified fixes.
- **Exit criteria:** Critical behaviours and significant failure scenarios have evidence of correct operation; blocking defects are resolved and retested, with residual limitations recorded.
- **Decision / next step:** Provide evidence to 4.9 and 4.11; return defects to implementation and clarify ambiguous requirements with Product.
- **Applicability:** Required; scale the depth to the product's uncertainty, impact and resources.

### 4.6. Validate non-functional requirements

- **Description:** Evaluate the implemented product against agreed performance, capacity, reliability, accessibility and compatibility requirements. Test relevant failure and recovery scenarios under representative conditions.
- **Final Responsible:** CTAO, in collaboration with CPAO and COAO.
- **Operational Owner:** QA / Performance Test Lead.
- **Who executes:** QA Engineers, Engineering team, Platform/SRE Engineers and Accessibility Specialists where needed.
- **Inputs:** Measurable quality requirements, representative test conditions, implemented product and applicable integrations.
- **Dependencies:** Upstream references: 3.3, 4.2, 4.3. Validate relevant load, compatibility, accessibility and recovery conditions; align results with the assumptions and thresholds agreed in 3.3.
- **Deliverable:** Non-functional validation results, identified limitations, remediation actions and documented residual risks.
- **Exit criteria:** Applicable quality criteria are met under stated conditions or explicit, authorized exceptions exist; material limitations and corrective actions are visible.
- **Decision / next step:** Provide evidence to 4.11; remediate implementation or revisit 3.3 when the required service level or investment must change.
- **Applicability:** Required; scale the depth to the product's uncertainty, impact and resources.

### 4.7. Implement and verify security and privacy controls

- **Description:** Implement and assess controls for authentication, authorization, secrets, sensitive data and relevant privacy requirements. Perform risk-appropriate security testing, investigate findings and verify remediation of critical issues.
- **Final Responsible:** CTAO for implementation; CISAO for security assessment and security-risk recommendations, with the privacy/legal owner consulted where applicable.
- **Operational Owner:** Security Lead.
- **Who executes:** Engineering team, Security Engineers and relevant privacy specialists.
- **Inputs:** Security/privacy requirements, threat and data-flow design, implemented changes, dependency inventory and test environments.
- **Dependencies:** Upstream references: 3.3, 3.6, 4.1, 4.2. Assess throughout delivery and proportionately to risk. Applicable legal/privacy issues go to their designated owner; security specialists do not substitute for legal authority.
- **Deliverable:** Implemented controls, security assessment findings, verified remediation evidence and documented unresolved risks with assigned owners.
- **Exit criteria:** Required controls and significant findings have verification evidence; release-blocking findings are resolved, and residual risks have an authorized decision and accountable owner.
- **Decision / next step:** Provide security evidence to 4.11 and 5.2; remediate defects or revisit design before dependent release.
- **Applicability:** Required at proportionate depth; specialist assessments or independent testing are conditional on exposure, obligations and product risk.

### 4.8. Implement analytics and observability

- **Description:** Implement the agreed product events and business metrics alongside technical logs, metrics, traces and alerts. Verify data accuracy, useful diagnostic context and appropriate handling of sensitive information.
- **Final Responsible:** CTAO for instrumentation and technical observability; CPAO for product measurement acceptance.
- **Operational Owner:** Analytics / Instrumentation Lead.
- **Who executes:** Engineering team, Product/Data Analyst and Platform/SRE Engineers, with Growth Marketing and Security input.
- **Inputs:** Measurement plan, event specifications, technical architecture, relevant product increments and operating requirements.
- **Dependencies:** Upstream references: 3.10, 3.6, 4.1, 4.2. Coordinate analytics with technical observability; validate event meaning and data quality rather than assuming collection equals trustworthy measurement.
- **Deliverable:** Validated analytics instrumentation, operational dashboards, configured alerts and measurement-quality checks.
- **Exit criteria:** Critical events and operational signals are verified end to end in the available environment; dashboards, alert routing and sensitive-data handling meet agreed criteria.
- **Decision / next step:** Feed 4.10 and 4.11, then verify production signals in 5.5; correct collection or interpretation gaps before relying on the metrics.
- **Applicability:** Required; scale the depth to the product's uncertainty, impact and resources.

### 4.9. Validate product acceptance and usability

- **Description:** Evaluate the implemented experience against user needs, designs and acceptance criteria. Conduct product acceptance reviews and usability sessions with representative users, then prioritize and resolve material gaps.
- **Final Responsible:** CPAO.
- **Operational Owner:** Product Manager.
- **Who executes:** Product Manager, Product Designer, UX Researcher and QA, with relevant stakeholders and representative users participating.
- **Inputs:** Implemented increment, acceptance criteria, prototype findings, functional-test evidence and representative user scenarios.
- **Dependencies:** Upstream references: 3.2, 3.8, 4.2, 4.5. Validate the real implemented experience, not just the earlier prototype. Product acceptance and technical quality evidence remain distinct.
- **Deliverable:** Product acceptance report, usability findings, prioritized adjustments and an explicit acceptance status for the release scope.
- **Exit criteria:** Product acceptance is explicitly recorded for the release scope; critical user tasks work and material usability gaps are resolved or accepted with documented consequences.
- **Decision / next step:** Feed 4.11 and accurate launch materials; route experience issues to Design and Engineering or revisit scope.
- **Applicability:** Required; scale the depth to the product's uncertainty, impact and resources.

### 4.10. Prepare operations and support

- **Description:** Prepare the people and procedures needed to operate and support the product. Define ownership, support workflows, incident response, escalation, backup and recovery processes, and operational training.
- **Final Responsible:** COAO for service and support readiness; CTAO for technical operations readiness.
- **Operational Owner:** Operations Lead.
- **Who executes:** Operations, Customer Support/Success, Platform/SRE and Engineering teams, with Product and Security input.
- **Inputs:** Service and recovery expectations, release scope, observability, expected customer journeys and likely support demand.
- **Dependencies:** Upstream references: 3.3, 3.11, 4.8. Prepare support, incident response and technical operations before launch; coordinate with release planning and verify recovery procedures at appropriate depth.
- **Deliverable:** Operational runbooks, support documentation, ownership and escalation paths, recovery procedures and training materials.
- **Exit criteria:** Named operators can use the runbooks, alerts, escalation paths and support materials; necessary recovery checks and training are complete, with coverage and residual gaps explicit.
- **Decision / next step:** Provide readiness evidence to 4.11 and operational inputs to phase 5; address staffing, process or technical gaps before the affected rollout.
- **Applicability:** Required; scale the depth to the product's uncertainty, impact and resources.

### 4.11. Verify release readiness

- **Description:** Consolidate product, engineering, security and operational validation evidence. Prepare the release candidate, deployment and rollback procedures, migration sequence where relevant, and explicit go/no-go criteria. Review outstanding issues before authorizing progression to launch.
- **Final Responsible:** CTAO for technical release readiness, with CPAO, COAO and CISAO approving readiness within their respective areas.
- **Operational Owner:** Engineering Manager / Release Lead.
- **Who executes:** Engineering Manager/Tech Lead, QA Lead, Product Manager, Platform/DevOps and Operations representatives.
- **Inputs:** Release candidate, code-review and test evidence, security assessment, instrumentation checks, product acceptance and operational readiness.
- **Dependencies:** Upstream references: 4.4, 4.5, 4.6, 4.7, 4.8, 4.9, 4.10. This checks release readiness; 5.1 coordinates the broader launch. Apply all evidence to the actual candidate/version and repeat affected checks after material changes.
- **Deliverable:** Release candidate, consolidated readiness assessment, deployment and rollback plan, known-issues register and a recorded decision to proceed or address remaining blockers.
- **Exit criteria:** The specific release candidate has a recorded technical readiness decision, domain sign-offs, deployment/recovery plan and no unresolved release blockers under agreed criteria.
- **Decision / next step:** Feed 5.1 and 5.5 when ready; otherwise return each blocker to its owner and re-evaluate after remediation.
- **Applicability:** Required; scale the depth to the product's uncertainty, impact and resources.

## 5. Launch

Deploy and introduce the approved product to its intended audience, stabilize the launch and establish ongoing ownership.

### 5.1. Coordinate the launch and confirm readiness

- **Description:** Coordinate the technical, product, commercial and operational launch. Consolidate readiness evidence from the previous phase, confirm dependencies, assign owners and establish launch timing, rollout stages and go/no-go criteria.
- **Final Responsible:** CPAO for cross-functional launch coordination, with CTAO, CMAO and COAO approving readiness within their areas.
- **Operational Owner:** Product Manager / Launch Lead.
- **Who executes:** Product Manager, Product Marketing Manager, Engineering Lead and Operations Lead.
- **Inputs:** Release readiness evidence, GTM strategy, delivery timing, operational capacity and applicable domain approvals.
- **Dependencies:** Upstream references: 3.13, 3.11, 4.11, 5.2. Launch planning can start earlier using drafts. The decision authorizes a specified rollout stage; wider exposure is reassessed after pilot or production evidence.
- **Deliverable:** Integrated launch plan, ownership and dependency map, agreed launch criteria and a recorded readiness decision.
- **Exit criteria:** The intended rollout stage has an owner, timing, audience, readiness evidence, dependencies, stop conditions and a recorded go/no-go decision.
- **Decision / next step:** Proceed with the authorized deployment/rollout stage; postpone, reduce exposure or return blockers to the responsible activity.
- **Applicability:** Required; scale the depth to the product's uncertainty, impact and resources.

### 5.2. Confirm legal, privacy and security readiness

- **Description:** Review applicable terms, privacy notices, licensing, commercial claims and contractual requirements. Confirm that agreed security controls are operational and that unresolved legal or security issues have been assessed before release.
- **Final Responsible:** CLAO for legal readiness; CISAO for security readiness, with CTAO responsible for technical remediation.
- **Operational Owner:** Legal / Privacy Lead.
- **Who executes:** Legal Counsel, Privacy Specialists and Security Engineers, collaborating with Product, Engineering and Marketing.
- **Inputs:** Applicable constraints, reviewed technical controls, data practices, proposed commercial terms and current product/marketing claims.
- **Dependencies:** Upstream references: 1.5, 3.3, 3.6, 3.7, 4.7. Legal/privacy and security owners assess their domains. Review evolving launch materials from 5.3 and confirm the versions actually published; earlier design review remains essential.
- **Deliverable:** Reviewed legal materials, legal and security readiness assessments, documented outstanding issues and applicable release conditions.
- **Exit criteria:** Applicable launch requirements are addressed or an authorized disposition is recorded; release-blocking issues are closed and the relevant notices, terms and controls are ready.
- **Decision / next step:** Supply domain readiness to 5.1 and publication in 5.7; route issues to Product, Engineering, Marketing or the designated legal owner.
- **Applicability:** Required as an applicability/readiness check; the depth and specialist involvement depend on the product, audience, data and obligations.

### 5.3. Finalize marketing and launch design assets

- **Description:** Prepare and verify the public-facing materials needed to explain and promote the released product. Ensure visual identity, messaging, screenshots, demonstrations and commercial promises match the actual release.
- **Final Responsible:** CMAO, with CPAO confirming product accuracy.
- **Operational Owner:** Brand / Creative Lead.
- **Who executes:** Product Marketing Manager, Brand/Visual Designer, Copywriter and Content team, with Product Designer input.
- **Inputs:** Approved brand direction, offer and messaging, GTM plan, accepted product capabilities and release details.
- **Dependencies:** Upstream references: 3.12, 3.7, 3.13, 4.9. Prepare assets while development progresses; finalize claims and demonstrations against the accepted release, with applicable reviews from 5.2.
- **Deliverable:** Launch website or landing pages, campaign creatives, product demonstrations, release notes, email and social content, and store listings where applicable.
- **Exit criteria:** Required launch materials are accurate, accessible at the agreed level, consistent with the brand and ready in the needed formats and destinations.
- **Decision / next step:** Feed 5.4 and 5.7; revise unsupported claims, asset gaps or inconsistent experiences before publication.
- **Applicability:** Required at the appropriate scale; external campaigns, app-store listings, PR and specific creative formats are conditional.

### 5.4. Prepare acquisition and commercial channels

- **Description:** Configure and verify the channels through which users discover, access, trial or purchase the product. Confirm pricing presentation, conversion paths, lead handling and sales readiness where relevant to the business model.
- **Final Responsible:** CMAO for acquisition channels; CRAO for sales readiness where a sales function exists.
- **Operational Owner:** Growth / Marketing Operations Lead.
- **Who executes:** Growth Marketing, Marketing Operations, Sales Operations and Product Marketing, with Engineering and Finance support.
- **Inputs:** GTM strategy, offer and pricing decisions, conversion-flow requirements, tracking and applicable sales materials.
- **Dependencies:** Upstream references: 3.13, 3.7, 4.8. Configure and test channels before activation. Use production checks from 5.5 for live destinations; coordinate asset completion with 5.3.
- **Deliverable:** Ready-to-activate acquisition channels, verified conversion paths, commercial materials and defined lead or sales handoffs.
- **Exit criteria:** Relevant discovery-to-access/purchase paths, attribution, lead ownership and commercial handoffs are verified, with budget and activation authority recorded.
- **Decision / next step:** Activate eligible channels in 5.7 after production and rollout checks; correct broken paths or missing ownership before spending or outreach.
- **Applicability:** Required for relevant acquisition/adoption channels; paid media, sales, billing and CRM apply only where the business model needs them.

### 5.5. Deploy the approved release to production

- **Description:** Deploy the approved release, execute required migrations and verify production configuration. Run smoke tests on critical journeys, confirm monitoring and recovery readiness, and control access according to the rollout plan.
- **Final Responsible:** CTAO.
- **Operational Owner:** Platform / DevOps Lead.
- **Who executes:** Platform/DevOps Engineers, Engineering team, Tech Lead and QA, with Security support.
- **Inputs:** Approved release candidate, rollout authorization, domain readiness, migration procedures and deployment/recovery plans.
- **Dependencies:** Upstream references: 4.11, 5.1, 5.2. Deploy only the authorized candidate and exposure level; verify production configuration, smoke tests, monitoring and migration integrity before expanding access.
- **Deliverable:** Deployed production release, deployment and migration records, production verification results and an operational rollback or recovery procedure.
- **Exit criteria:** Production verification passes for the exposed scope, required migration checks succeed and a supported rollback or forward-recovery path is available.
- **Decision / next step:** Proceed to controlled rollout or authorized broader release, start support and monitoring; halt or recover if deployment criteria fail.
- **Applicability:** Required; scale the depth to the product's uncertainty, impact and resources.

### 5.6. Conduct a pilot or controlled rollout

- **Description:** Where appropriate, introduce the product to a limited audience before broader exposure. Observe real usage, validate operational assumptions, collect feedback and assess whether to expand, pause or revise the rollout.
- **Final Responsible:** CPAO for audience expansion decisions, with CTAO and COAO confirming technical and operational readiness.
- **Operational Owner:** Product Manager.
- **Who executes:** Product Manager, Engineering, QA, Customer Success/Support and UX Researcher.
- **Inputs:** Deployed release, controlled audience, rollout criteria, monitoring and operational/support coverage.
- **Dependencies:** Upstream references: 5.5, 4.10. Use a pilot when it meaningfully reduces uncertainty. A skipped pilot needs an explicit rationale and appropriate production safeguards.
- **Deliverable:** Pilot or rollout findings, prioritized issues, user feedback and a recorded decision on the next rollout stage.
- **Exit criteria:** Pilot outcomes and limitations are recorded; predefined expansion criteria and technical/operational checks support an explicit expand, pause, revise or stop decision.
- **Decision / next step:** Authorize the next audience stage and 5.7 where appropriate; route problems to the responsible design, development or operational activity.
- **Applicability:** Conditional: use when risk, uncertainty, audience or deployment context benefits from limited exposure. Controlled production verification remains required even if a separate pilot is skipped.

### 5.7. Activate public launch and acquisition campaigns

- **Description:** Execute the approved launch communications and acquisition activities in coordination with product availability. Activate relevant paid, organic, partnership, community and sales initiatives, adapting exposure to operational capacity.
- **Final Responsible:** CMAO, in coordination with CRAO where applicable.
- **Operational Owner:** Growth Marketing Lead.
- **Who executes:** Growth Marketers, Content and Social teams, PR/Communications, Partnership Managers and Sales.
- **Inputs:** Authorized rollout status, approved communications, working acquisition channels, production availability and relevant pilot findings.
- **Dependencies:** Upstream references: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6. Coordinate campaigns with real product capacity and support readiness; use the recorded N/A route if a distinct pilot is not needed.
- **Deliverable:** Published launch communications, active campaigns and commercial initiatives, and initial channel-performance results.
- **Exit criteria:** Agreed communications and acquisition activities are live for the authorized audience, with owners, spend controls and functioning measurement.
- **Decision / next step:** Monitor outcomes and direct users into 5.8; pause or adjust campaigns if capacity, accuracy or conversion paths fail.
- **Applicability:** Required as product availability/adoption communication; external public launch, paid campaigns and sales activation are conditional.

### 5.8. Onboard and support the first users

- **Description:** Help initial users access the product, understand its value and complete their first meaningful tasks. Operate support and escalation processes, resolve adoption barriers and feed recurring issues back to Product and Engineering.
- **Final Responsible:** COAO for onboarding and support operations; CPAO for the in-product onboarding experience.
- **Operational Owner:** Customer Success / Support Lead.
- **Who executes:** Customer Success, Customer Support, Product Manager and Engineering, with Lifecycle Marketing input.
- **Inputs:** Available product, onboarding experience, runbooks, support coverage and the actual launch audience.
- **Dependencies:** Upstream references: 5.5, 4.10. Start with the first pilot users rather than waiting for a public campaign; Product owns in-product changes and Operations owns service workflows.
- **Deliverable:** Operational onboarding and support workflows, initial activation findings, support records and prioritized adoption issues.
- **Exit criteria:** Initial users can obtain support and reach the intended first-value experience; major onboarding barriers and unresolved requests have owners and escalation paths.
- **Decision / next step:** Feed issues into 5.9 and learning into 5.10; transition the service workflow into 6.2.
- **Applicability:** Required; scale the depth to the product's uncertainty, impact and resources.

### 5.9. Monitor and stabilize the launch

- **Description:** Closely monitor service health, security signals, data quality, critical user journeys and support demand. Triage incidents and defects, deliver necessary fixes, and pause or reverse rollout when agreed thresholds are breached.
- **Final Responsible:** CTAO for technical stability, with CISAO overseeing security response and COAO coordinating customer-facing operations.
- **Operational Owner:** Engineering Manager / Incident Lead.
- **Who executes:** Engineering, Platform/SRE, Security, QA, Support and Product/Data Analysts.
- **Inputs:** Production release, operational signals, launch thresholds, incident runbooks and incoming customer reports.
- **Dependencies:** Upstream references: 5.5, 4.8, 4.10. Monitor from first production exposure. Coordinate engineering, security and customer communication according to incident type and impact.
- **Deliverable:** Launch monitoring reports, incident and defect records, verified fixes and an explicit stabilization status.
- **Exit criteria:** For the agreed observation window, launch-critical incidents are resolved or under an accepted plan, service criteria are satisfied and ongoing ownership is assigned.
- **Decision / next step:** Support wider rollout where justified and feed 5.10; pause exposure or initiate recovery if stop conditions are reached.
- **Applicability:** Required; scale the depth to the product's uncertainty, impact and resources.

### 5.10. Evaluate launch outcomes and transition to ongoing operations

- **Description:** Compare initial outcomes with launch objectives, accounting for sample size and observation time. Review acquisition, activation, customer feedback, service quality and commercial results where available. Assign ongoing ownership and prioritize follow-up improvements.
- **Final Responsible:** CPAO for product outcome evaluation; COAO for the transition to ongoing service operations.
- **Operational Owner:** Product Manager.
- **Who executes:** Product Manager, Product/Data Analyst, Marketing, Engineering, Operations and Finance representatives.
- **Inputs:** Launch/adoption results, early user outcomes, support evidence, stability findings and the original launch objectives.
- **Dependencies:** Upstream references: 5.7, 5.8, 5.9. Use a meaningful observation window and label unavailable long-term metrics. Early results are not proof of durable retention or product-market fit.
- **Deliverable:** Launch review, initial performance baseline, prioritized improvement backlog, ongoing ownership assignments and an agreed transition to Operation and Evolution.
- **Exit criteria:** The launch review records outcomes, limitations, outstanding work and named steady-state owners; operational transition is explicitly accepted.
- **Decision / next step:** Continue into phase 6 with a baseline and prioritized follow-up; return significant issues to the relevant phase or escalate strategic concerns.
- **Applicability:** Required; scale the depth to the product's uncertainty, impact and resources.

## 6. Operation and Evolution

Operate the product continuously, learn from outcomes and deliver proportionate improvements through repeated iterations.

### 6.1. Operate and monitor the service

- **Description:** Keep the product available and functioning within agreed service objectives. Monitor infrastructure, application health, integrations, capacity and critical user journeys, and respond to operational deviations.
- **Final Responsible:** CTAO for technical service operation, in coordination with COAO.
- **Operational Owner:** Platform / SRE Lead.
- **Who executes:** Platform/SRE Engineers, Engineering team and Operations.
- **Inputs:** Production service, agreed service objectives, runbooks, observability and assigned operating capacity.
- **Dependencies:** Upstream references: 5.5, 4.10, 4.8. Starts during launch and continues after 5.10. Coordinate capacity and incidents with support, security and engineering maintenance.
- **Deliverable:** Service-health dashboards, service-level reports, capacity assessments and operational records.
- **Exit criteria:** Each operating review confirms service status, coverage and owned deviations from objectives; unresolved issues have an action or escalation.
- **Decision / next step:** Continue monitoring, trigger 6.3 for incidents and feed capacity/health findings into 6.4, 6.9 and 6.11.
- **Applicability:** Ongoing while the product operates; apply the exit criterion to each review or work cycle, not to permanent completion of the activity.

### 6.2. Provide customer support and customer success

- **Description:** Resolve user questions and problems, support onboarding and adoption, and help customers achieve their intended outcomes. Maintain support resources and identify recurring issues requiring product or operational improvements.
- **Final Responsible:** COAO.
- **Operational Owner:** Customer Success / Support Lead.
- **Who executes:** Customer Support, Customer Success and Operations, with Product and Engineering support.
- **Inputs:** Active users, onboarding/support workflows, knowledge resources, service commitments and customer requests.
- **Dependencies:** Upstream references: 5.8, 4.10. Coordinate with Product and Engineering for recurring issues; distinguish one customer's request from evidence supporting a wider product decision.
- **Deliverable:** Support resolutions, updated knowledge resources, customer-success plans where relevant, and categorized customer feedback.
- **Exit criteria:** Requests in the work cycle are resolved, clearly communicated or assigned with next actions; recurring themes and customer risks are recorded.
- **Decision / next step:** Continue service delivery; feed incidents to 6.3 and unmet needs or adoption problems to 6.7 and 6.8.
- **Applicability:** Ongoing while the product operates; apply the exit criterion to each review or work cycle, not to permanent completion of the activity.

### 6.3. Manage incidents and recovery

- **Description:** Detect, triage and resolve service disruptions. Coordinate technical response, customer communication and recovery, then investigate significant incidents and assign preventive actions.
- **Final Responsible:** CTAO for technical incident response, with CISAO leading security incidents and COAO coordinating customer-facing operations.
- **Operational Owner:** Designated Incident Commander.
- **Who executes:** On-call Engineers, Platform/SRE, Security, Support and relevant service owners.
- **Inputs:** Triggered incident, impact evidence, operational/security signals, runbooks, escalation paths and relevant service owners.
- **Dependencies:** Upstream references: 4.10, 6.1. Assign one incident coordinator; security and customer-facing leads retain their domain responsibilities. Prioritize containment and recovery according to the incident plan.
- **Deliverable:** Incident records, recovery verification, stakeholder communications, post-incident reviews and tracked corrective actions.
- **Exit criteria:** Service or security impact is controlled, recovery is verified, communications are complete for the incident stage and significant follow-up actions have owners.
- **Decision / next step:** Return to normal operations; feed preventive work into 6.4, 6.5 and 6.9 and escalate unresolved material impact.
- **Applicability:** Event-driven when an incident occurs; response preparedness and appropriate exercises remain part of normal operational readiness.

### 6.4. Maintain technical health

- **Description:** Maintain dependencies, infrastructure, integrations and automated tests. Address technical debt, compatibility changes, performance degradation and obsolete components according to business impact and risk.
- **Final Responsible:** CTAO.
- **Operational Owner:** Tech Lead.
- **Who executes:** Engineering team, Tech Lead, Platform Engineers and QA.
- **Inputs:** Technical-health findings, dependency/support lifecycle information, incident actions, code-quality evidence and capacity constraints.
- **Dependencies:** Upstream references: 4.4, 6.1. Maintain alongside feature delivery. Coordinate prioritization with 6.9 rather than allowing maintenance work or product work to become invisible.
- **Deliverable:** Maintenance updates, dependency and lifecycle tracking, prioritized technical-debt backlog and technical-health assessments.
- **Exit criteria:** Scheduled maintenance changes are reviewed and verified, applicable compatibility risks are addressed and remaining debt has priority and ownership.
- **Decision / next step:** Deliver approved changes through the relevant phase 3–5 controls; update the health backlog and escalate high-impact risks.
- **Applicability:** Ongoing while the product operates; apply the exit criterion to each review or work cycle, not to permanent completion of the activity.

### 6.5. Maintain security, privacy and compliance

- **Description:** Monitor threats and vulnerabilities, review access and data-handling practices, and maintain applicable security and privacy controls. Address findings and reassess obligations when the product, market or operating context changes.
- **Final Responsible:** CISAO for security oversight; CLAO or designated privacy/legal owner for applicable legal obligations; CTAO for technical remediation.
- **Operational Owner:** Security Lead.
- **Who executes:** Security Engineers, Engineering, Privacy Specialists, Legal and Operations.
- **Inputs:** Current controls and obligations, threat/vulnerability signals, access and data-use changes, and previous risk decisions.
- **Dependencies:** Upstream references: 5.2, 4.7. Operate with Engineering and the designated legal/privacy owner; changes in features, vendors or markets can trigger reassessment.
- **Deliverable:** Updated risk assessments, access reviews, vulnerability remediation records, control evidence and tracked compliance actions.
- **Exit criteria:** Each review records control status, findings, owner decisions and remediation priorities; critical issues receive a timely response under the agreed process.
- **Decision / next step:** Trigger 6.3 for security incidents, route remediation through 6.9/6.10 and revisit design where controls or data practices must change.
- **Applicability:** Ongoing while the product operates; apply the exit criterion to each review or work cycle, not to permanent completion of the activity.

### 6.6. Measure product and business outcomes

- **Description:** Evaluate activation, engagement, retention, customer satisfaction and relevant commercial results. Verify measurement quality, investigate changes and distinguish observed behaviour from assumptions or attribution estimates.
- **Final Responsible:** CPAO for product outcomes, with CMAO, CFAO and COAO owning metrics within their areas.
- **Operational Owner:** Product / Data Analyst.
- **Who executes:** Product/Data Analysts, Product Manager, Marketing Analysts, Finance and Operations Analysts.
- **Inputs:** Metric definitions, verified instrumentation, launch baseline, usage cohorts and available commercial/operational data.
- **Dependencies:** Upstream references: 3.10, 4.8, 5.10. Align measurement windows and populations; use financial and marketing owners for their definitions and label missing or unreliable data explicitly.
- **Deliverable:** Product and business dashboards, cohort and funnel analyses, measurement-quality findings and evidence-based performance reviews.
- **Exit criteria:** The review contains interpretable results, data-quality limitations and material changes, with sufficient context to support the stated decisions.
- **Decision / next step:** Feed 6.7–6.9 and economic/strategic reviews; repair measurement defects before making decisions that depend on them.
- **Applicability:** Ongoing while the product operates; apply the exit criterion to each review or work cycle, not to permanent completion of the activity.

### 6.7. Improve adoption, retention and commercial growth

- **Description:** Improve onboarding communications, lifecycle campaigns, acquisition channels and relevant sales or renewal processes. Coordinate these activities with product improvements to increase sustained customer value.
- **Final Responsible:** CMAO for marketing and lifecycle activities; CPAO for in-product adoption and retention; CRAO for sales and renewals where applicable.
- **Operational Owner:** Growth / Lifecycle Lead.
- **Who executes:** Growth Marketing, Lifecycle/CRM Marketing, Product, Customer Success and Sales.
- **Inputs:** Product and customer-success findings, funnel/cohort results, commercial objectives and the current GTM strategy.
- **Dependencies:** Upstream references: 3.13, 6.6, 6.2. Coordinate messaging, sales and in-product changes; use Engineering delivery controls for code changes and predefine relevant experiment outcomes.
- **Deliverable:** Growth and retention initiatives, campaign and funnel improvements, commercial playbooks and measured outcomes.
- **Exit criteria:** Each initiative has an evaluated outcome or justified continuation decision, with user impact, cost and evidence limitations visible.
- **Decision / next step:** Scale, adjust or stop initiatives; route product changes to 6.9 and unexplained customer behaviour to 6.8.
- **Applicability:** Applicable to adoption and sustained customer value; paid growth, revenue expansion and renewal initiatives depend on the product's objectives and business model.

### 6.8. Conduct continuous discovery

- **Description:** Continuously investigate user needs, usage patterns, support themes, churn reasons and market changes. Identify emerging problems and opportunities, and test whether proposed improvements address meaningful needs.
- **Final Responsible:** CPAO.
- **Operational Owner:** Product Manager.
- **Who executes:** Product Manager, UX Researcher, Product Designer and Product/Data Analyst, with Marketing and Customer Success input.
- **Inputs:** Usage and outcome evidence, support themes, churn/adoption findings, research and relevant market changes.
- **Dependencies:** Upstream references: 6.6, 6.2. Reuse Discovery methods from phase 2 at the needed depth. Research priorities should reflect significant uncertainty rather than simply request volume.
- **Deliverable:** Updated research findings, opportunity backlog, revised hypotheses and supporting evidence for potential improvements.
- **Exit criteria:** Investigated opportunities have evidence, an articulated problem, uncertainty and a decision on further research or consideration for delivery.
- **Decision / next step:** Feed 6.9; revisit phase 1 for strategic changes or continue targeted research where evidence is insufficient.
- **Applicability:** Ongoing while the product operates; apply the exit criterion to each review or work cycle, not to permanent completion of the activity.

### 6.9. Prioritize the evolution roadmap

- **Description:** Compare product opportunities, defects, technical debt and operational needs against strategic goals. Balance expected value, risk, effort and available capacity, and determine the next outcomes and increments to pursue.
- **Final Responsible:** CPAO for product priorities, in collaboration with CTAO, COAO, CMAO and CFAO.
- **Operational Owner:** Product Manager.
- **Who executes:** Product Manager, Engineering Manager, Tech Lead and relevant functional leads.
- **Inputs:** Opportunity evidence, performance findings, technical debt, operational/security needs and capacity/investment constraints.
- **Dependencies:** Upstream references: 6.8, 6.4, 6.6. Review material inputs from 6.3 and 6.5 when present; align priorities with technical capacity and the authorized budget.
- **Deliverable:** Updated outcome-based roadmap, prioritized backlog, capacity allocation and documented prioritization decisions.
- **Exit criteria:** The next work cycle has explicit priorities, rationale, scope boundaries, owners and capacity allocation, with mandatory remediation visible.
- **Decision / next step:** Route selected work to 6.10; commission further Discovery, change scope or request an investment decision where needed.
- **Applicability:** Ongoing while the product operates; apply the exit criterion to each review or work cycle, not to permanent completion of the activity.

### 6.10. Deliver and evaluate improvements

- **Description:** Route selected improvements through the appropriate discovery, design, development, validation and release activities. Use controlled experiments where suitable, measure results and decide whether to retain, expand, revise or reverse changes.
- **Final Responsible:** CTAO for technical delivery; CPAO for product acceptance and outcome evaluation.
- **Operational Owner:** Engineering Manager / Delivery Lead.
- **Who executes:** Product, Design, Engineering, QA and Data teams, with Marketing and Operations involved as needed.
- **Inputs:** Prioritized improvement scope, expected outcomes, current product context and relevant risk/acceptance evidence.
- **Dependencies:** Upstream references: 6.9. Use a new iteration of the applicable activities in phases 2–5; do not rebuild unchanged evidence or repeat every launch activity for minor changes.
- **Deliverable:** Released improvements, validation and experiment results, updated documentation and recorded follow-up decisions.
- **Exit criteria:** The change has passed proportionate design, engineering, acceptance and release checks; its outcome is assessed or has an assigned observation plan.
- **Decision / next step:** Retain, expand, revise or reverse the change based on evidence; return results to 6.6, 6.8 and 6.9.
- **Applicability:** Triggered by selected improvements or fixes; the depth of discovery, testing and rollout is tailored to the change's impact and uncertainty.

### 6.11. Optimize operational and economic efficiency

- **Description:** Review operating costs, infrastructure consumption, acquisition economics, support effort and vendor dependencies. Identify efficiencies while preserving agreed service quality, customer value and risk boundaries.
- **Final Responsible:** CFAO for economic oversight, with CTAO and COAO accountable for improvements within their areas.
- **Operational Owner:** Finance / Operations Analyst.
- **Who executes:** Finance Analysts, Platform/Engineering, Operations and Marketing Analysts.
- **Inputs:** Actual costs and revenue where relevant, operating usage, support effort, vendor commitments and outcome metrics.
- **Dependencies:** Upstream references: 6.6, 6.1. Assess savings against service, security and customer-value constraints. Label forecasts and allocation assumptions rather than treating them as realized savings.
- **Deliverable:** Cost and unit-economics reviews, efficiency initiatives, updated forecasts and measured savings or productivity improvements.
- **Exit criteria:** The review identifies feasible actions, baseline economics, owners and expected trade-offs; completed actions have measured outcomes where observable.
- **Decision / next step:** Route approved improvements into operating teams or 6.9/6.10; feed material investment implications into 6.12.
- **Applicability:** Ongoing while the product operates; apply the exit criterion to each review or work cycle, not to permanent completion of the activity.

### 6.12. Review strategic direction and lifecycle decisions

- **Description:** Periodically reassess whether the product continues to meet strategic, customer and economic objectives. Decide whether to maintain direction, increase investment, reposition, consolidate, replace or retire the product.
- **Final Responsible:** CEAO, in collaboration with CPAO, CFAO, CTAO, CMAO and COAO.
- **Operational Owner:** Product / Business Strategy Lead.
- **Who executes:** Product and Business/Strategy leads, supported by Finance, Data and relevant functional teams.
- **Inputs:** Product/business outcomes, customer and market evidence, economics, risk position and strategic alternatives.
- **Dependencies:** Upstream references: 6.6, 6.8, 6.11. Review on an agreed cadence or when material evidence changes; obtain executive decisions proportionate to the investment and strategic consequences.
- **Deliverable:** Strategic product review, updated investment decisions and direction, or an approved transition into Retirement or Replacement when appropriate.
- **Exit criteria:** A direction and investment decision is recorded with evidence, conditions, owners and the next review trigger.
- **Decision / next step:** Continue or adjust phase 6, revisit phases 1–2 for a changed direction, or initiate 7.1 for retirement or replacement.
- **Applicability:** Ongoing while the product operates; apply the exit criterion to each review or work cycle, not to permanent completion of the activity.

## 7. Retirement or Replacement

Carry out an authorized transition or closure while managing affected users, data, dependencies and residual obligations.

### 7.1. Decide and approve retirement or replacement

- **Description:** Assess whether to discontinue the product or replace it. Define the rationale, affected scope, customer impact and conditions for completing the transition.
- **Final Responsible:** CEAO, in collaboration with CPAO, CFAO and CTAO.
- **Operational Owner:** Product Manager.
- **Who executes:** Product Manager and Business/Strategy Lead, with Finance, Engineering and Operations input.
- **Inputs:** Strategic lifecycle decision, rationale, customer and dependency impact, economics and available replacement or exit options.
- **Dependencies:** Upstream references: 6.12. For an operating product, use 6.12. If an initiative stops before operation, an equivalent documented business decision is the alternative input; perform only relevant closure activities.
- **Deliverable:** Approved retirement or replacement decision, scope, rationale and completion criteria.
- **Exit criteria:** The authorized decision identifies the scope, affected parties, target conditions, funding/ownership and unresolved obligations for the transition.
- **Decision / next step:** Initiate 7.2; reconsider or defer closure if the impact or obligations cannot yet be managed.
- **Applicability:** Required once retirement or replacement is proposed; early project cancellation uses a proportionate closure path.

### 7.2. Plan and communicate the transition

- **Description:** Define timelines, responsibilities, support arrangements and available alternatives. Communicate the changes, deadlines and required actions to affected users, customers, partners and internal teams.
- **Final Responsible:** COAO, in collaboration with CPAO, CMAO and CLAO.
- **Operational Owner:** Operations Lead.
- **Who executes:** Product Manager, Operations, Customer Success, Marketing/Communications and Legal.
- **Inputs:** Approved lifecycle decision, affected customer/vendor inventory, service commitments, replacement options and legal/financial constraints.
- **Dependencies:** Upstream references: 7.1. Coordinate technical migration, communication, support and contractual work. A replacement product must have its own validated readiness through the applicable earlier phases.
- **Deliverable:** Transition plan, stakeholder communications, support arrangements and assigned responsibilities.
- **Exit criteria:** Transition timing, notice requirements, owners, support, migration/exit options and acceptance criteria are approved; required communications are delivered or scheduled before affected actions.
- **Decision / next step:** Execute 7.3 and prepare 7.4/7.5 in parallel; revise timing or options when stakeholders cannot transition under the agreed conditions.
- **Applicability:** Required for the affected scope; external notices and migration support depend on actual users, customers and commitments.

### 7.3. Transition users and data

- **Description:** Migrate users, workflows and required data to a validated replacement, or provide appropriate export and exit options. Verify data integrity, access and transition outcomes before disabling the original service.
- **Final Responsible:** CTAO for technical migration; COAO for customer transition.
- **Operational Owner:** Migration / Transition Lead.
- **Who executes:** Engineering, Data Engineers, QA and Customer Success, with Security and Privacy input.
- **Inputs:** Transition plan, affected users/data, validated destination where applicable, export/migration tooling and data-handling requirements.
- **Dependencies:** Upstream references: 7.2. Verify a replacement's readiness before moving users. Reconcile data and record exceptions; technical success alone does not prove customers have completed their transition.
- **Deliverable:** Verified migrations or exports, customer transition status and documented exceptions requiring follow-up.
- **Exit criteria:** Required migrations or exports are verified, access and continuity checks pass where applicable, and remaining cases have an authorized disposition before source shutdown.
- **Decision / next step:** Authorize the affected decommissioning scope in 7.4 only when transition conditions are met; remediate or defer unresolved migrations.
- **Applicability:** Conditional on affected users, workflows or data; record N/A and the supporting inventory if no transition/export is required.

### 7.4. Decommission the product securely

- **Description:** Disable the retired application, integrations, scheduled processes and product-specific infrastructure. Revoke obsolete access and credentials, protect shared dependencies, and archive or delete data according to approved retention requirements.
- **Final Responsible:** CTAO, with CISAO overseeing security and CLAO confirming applicable legal requirements.
- **Operational Owner:** Platform / DevOps Lead.
- **Who executes:** Engineering, Platform/DevOps, Security and Data teams.
- **Inputs:** Authorized decommissioning scope, transition evidence or approved N/A, dependency inventory, communication conditions and approved data disposition requirements.
- **Dependencies:** Upstream references: 7.1, 7.2, 7.3. Protect shared resources and required retained records. Coordinate access revocation, service removal and data disposition with Security and the designated legal/privacy owner.
- **Deliverable:** Decommissioning records, data disposition records and verification that retired components and access are inactive.
- **Exit criteria:** Retired components and obsolete access are inactive, shared dependencies remain functional and data archival/deletion actions are verified against the approved plan.
- **Decision / next step:** Feed closure evidence to 7.5; resolve residual resources, access or data-handling issues before declaring technical closure.
- **Applicability:** Required for deployed or provisioned product assets; tailor to actual infrastructure, accounts, integrations and retained data.

### 7.5. Complete commercial and operational closure

- **Description:** Resolve remaining customer and supplier obligations, final billing or refunds where applicable, and unnecessary recurring expenditure. Reassign resources, preserve essential knowledge and assign ownership of any residual obligations.
- **Final Responsible:** COAO for operational closure; CFAO for financial closure, with CLAO supporting contractual matters.
- **Operational Owner:** Operations Lead.
- **Who executes:** Operations, Finance, Legal, Customer Success and Product Manager.
- **Inputs:** Transition/decommissioning evidence, customer/vendor obligations, final financial records, resource assignments and essential knowledge.
- **Dependencies:** Upstream references: 7.2, 7.4. Contract and financial closure can start while transition runs; assign ongoing responsibility for obligations that legitimately survive shutdown.
- **Deliverable:** Closure report, reconciled financial records, resolved or assigned obligations, archived documentation and lessons learned.
- **Exit criteria:** Applicable billing/refunds and supplier actions are reconciled, unnecessary expenditure is stopped, residual obligations have owners and final closure is explicitly accepted.
- **Decision / next step:** Close the product record; transfer relevant knowledge to any replacement and continue only the documented residual obligations.
- **Applicability:** Required at proportionate depth for every closed initiative or product; specific financial/contractual actions apply only where obligations exist.
