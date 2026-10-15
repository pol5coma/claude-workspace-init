> Historical design reference. Executable v1 definitions live in `catalog/organizations/spdlc/organization.json` and `catalog/workflows/spdlc/`. The maintained master document is [Full SPDLC](Full_SPDLC_Workflow.md); this earlier outline is not loaded by SPADO.

# Claude Workspace Init for Product Development Life Cycle (PDLC)

Provisioned claude workspace with C-suite Agents & sub-agents, skills and tools for the different phases of the PDLC.

## How it works:

### 1. bash: `cwi-init`

### 2. `cwi-init`:

#### 2.1. Select the desired workflow within the PDLC:

##### Workflow 1: Full-PDLC

###### 1. Idea & Strategy:

**1.1. Initial ideation and opportunity assessment:**

- **Description:** Generate, collect and screen product ideas. Identify the opportunity behind each idea and assess its strategic fit, potential impact, differentiation and obvious constraints using available information.
- **Final Responsible:** CEO, in collaboration with CPO.
- **Who executes:** Founder/Business Lead, Product Manager and relevant stakeholders, with Marketing, Finance and Engineering input.
- **Deliverable:** Shortlisted ideas, initial opportunity statements, selection criteria and rationale for the opportunity chosen for investigation.

**1.2. Define product vision and strategic goals:**

- **Description:** Define the intended long-term direction of the product, its connection to business objectives and the outcomes it should achieve. Establish initial success criteria and strategic boundaries.
- **Final Responsible:** CEO for business direction; CPO for product vision and goals.
- **Who executes:** Product Manager and Business/Strategy Lead, working with executive stakeholders.
- **Deliverable:** Product vision statement, strategic objectives, initial outcome metrics and guiding product principles.

**1.3. Define initial target audience and value proposition:**

- **Description:** Form initial hypotheses about target users, buyers and their problems. Describe the value the product could provide, why customers might choose it and how it could differ from existing alternatives.
- **Final Responsible:** CPO, in collaboration with CMO.
- **Who executes:** Product Manager and Product Marketing Manager, with UX Researcher input.
- **Deliverable:** Initial user and buyer segment hypotheses, problem statements, value proposition and differentiation hypotheses.

**1.4. Define the business model:**

- **Description:** Outline how the product could create, deliver and capture value. Identify potential revenue streams, pricing approaches, distribution channels, key partners and major cost drivers. Keep assumptions explicit until evidence is available.
- **Final Responsible:** CEO, in collaboration with CFO, CPO and CMO.
- **Who executes:** Business/Strategy Analyst, Finance Analyst, Product Manager and Product Marketing Manager.
- **Deliverable:** Initial business model, monetization and pricing hypotheses, cost structure and preliminary economic assumptions.

**1.5. Identify strategic assumptions, risks and constraints:**

- **Description:** Identify what must be true for the opportunity to succeed. Surface major market, adoption, economic, technical and operational uncertainties, alongside budget, timing or organizational constraints. Prioritize the assumptions that Discovery should investigate first.
- **Final Responsible:** CPO for consolidating discovery priorities, with CEO, CFO, CTO and CMO owning decisions within their areas.
- **Who executes:** Product Manager, UX Researcher, Business/Finance Analyst and Tech Lead, with relevant specialists.
- **Deliverable:** Prioritized assumptions and risks, known constraints, initial validation questions and decision criteria for continuing, changing direction or stopping.

**1.6. Define the initial budget and resource allocation:**

- **Description:** Allocate the funding, people and time needed for Discovery and early validation. Establish spending boundaries, decision checkpoints and an indicative investment envelope for later stages, subject to discovery findings.
- **Final Responsible:** CEO for investment approval; CFO for financial planning.
- **Who executes:** Finance Analyst, Product Manager and relevant functional leads, with CTO and CMO input.
- **Deliverable:** Approved discovery budget, initial resource allocation, indicative timeline, funding assumptions and agreed investment review checkpoints.

###### 2. Discovery:

**2.1. Market research / investigation (problem & potential / involved users)**

- **Description:** Investigate the market, potential user segments, relevant stakeholders, existing alternatives and competitors. Understand users’ contexts, behaviours, needs and current ways of addressing the problem.
- **Final Responsible:** CPO, in collaboration with CMO.
- **Who executes:** UX Researcher, Product Manager and Product Marketing Manager, with Market/Data Analyst support when needed
- **Deliverable:** Market and competitor analysis, initial user segmentation, stakeholder map, research findings and problem hypotheses.

**2.2. Problem validation:**

- **Description:** Test whether the identified problem exists for the target users and assess its frequency, severity and impact. Understand dissatisfaction with existing alternatives and identify which problems are worth prioritizing.
- **Final responsible:** CPO
- **Who executes:** UX Researcher and Product Manager, with Product/Data Analyst support.
- **Deliverable:** Evidence-backed problem statements, prioritized user needs, findings that support or challenge the hypotheses, and remaining uncertainties.

**2.3. Solution Exploration:**

- **Description:** Identify and compare alternative solution concepts and candidate functionalities/features addressing the prioritized problems. Explore their expected user value, assumptions and risks before committing to a specific solution.
- **Final responsible:** CPO
- **Who executes:** Product Manager, Product Designer and UX Researcher, with Tech Lead and Product Marketing Manager input.
- **Deliverable:** Solution concepts, candidate feature hypotheses, lightweight sketches or concept prototypes, and a shortlist of options to investigate further.

**2.4. Evaluate demand:**

- **Description:** Assess whether target users would adopt the proposed solution and whether buyers would pay where applicable. Test the value proposition, willingness to switch, pricing assumptions and ability to reach the intended audience through appropriate experiments.
- **Final responsible:** CMO, in collaboration with CPO.
- **Who executes:** Product Marketing Manager, Product Manager and Growth Marketer, with UX Researcher and Data Analyst support.
- **Deliverable:** Demand-validation findings, evidence of adoption or purchase interest, initial acquisition-channel hypotheses, and documented limitations distinguishing stated intent from actual commitments.

**2.5. Economic and technical viability and feasability:**

- **Description:** Assess whether the proposed solution could support a sustainable business and be built and operated within realistic constraints. Estimate revenue potential, acquisition and operating costs, development effort, critical dependencies and major technical risks.
- **Final responsible:** CFO for economic viability; CTO for technical feasibility, in collaboration with CPO.
- **Who executes:** Finance/Business Analyst, Product Manager, Tech Lead and Software Architect, with Engineering and Operations input.
- **Deliverable:** Preliminary business case, assumption-based unit economics and financial scenarios, initial technical feasibility assessment, major risks and a recommendation to proceed, revise or stop.

###### 3. Definition and Design:

**3.1. Scope priority:**

- **Description:** Define the scope, what's included, what's excluded and which is the minimal value to deliver first.
- **Final Responsible:** CPO
- **Who executes:** Product Manager + Design team + Engineering team
- **Deliverable:** Scope and priorities.

**3.2. Specify behaviour:**

- **Description:** Specify funcionality/features, permissions and acceptance criteria.
- **Final Responsible:** CPO
- **Who exeutes:** Product Manager / Business Analyst
- **Deliverable:** Functional Requirements (FRQ) and business flows.

**3.3. Define quality requirements:**

- **Description:** Define the quality requirements; availability, security, privacy, accessibility.
- **Final Responsible:** CTO (in collaboration with CPO and specialists)
- **Who executes:** Tech Lead, Security team, design team, and operations team.
- **Deliverable:** Non-functional verifable requirements (NFRQ)

**3.4. Design the experience (UX):**

- **Description:** Design the user experience, navigation, paths, interactions, content and error handling.
- **Final Responsible:** CPO
- **Who executes:** UX Designer, UX Researcher and UX Writer.
- **Deliverable:** Information architecture, user flows, and wireframes.

**3.5. Desing the user interface:**

- **Description:** Design screens, visual hierarchy, reusable components, interaction states and responsive behaviour, ensuring consistency with the brand and accessibility requirements.
- **Final Responsible:** CPO, in coordination with CMO.
- **Who executes:** Product/UI Designer and Brand Designer, with Engineering input on feasibility.
- **Deliverable:** Visual designs, screen and component states, responsive specifications and a design system.

**3.6. Design the technical solution:**

- **Description:** Define the initial software architecture, system components, data model, interfaces and integrations. Evaluate technical trade-offs against functional and non-functional requirements
- **Final responsible:** CTO
- **Who executes:** Software Architects, Tech Lead and Engineering team, with Security and Operations input.
- **Deliverable:** Initial technical architecture, data model, API and integration contracts, and documented technical decisions and trade-offs.

**3.7. Align product & offer:**

- **Description:** Align features per plan, pricing and packaging proposals, positioning, messaging and commercial promises with the defined product scope and business model.
- **Final responsible:** CMO, in collaboration with CPO and CFO; final pricing approval follows the agreed business decision authority.
- **Who executes:** Product Marketing Manager and Product Manager, with Finance input.
- **Deliverable:** Product offering and packaging proposal, feature-to-plan mapping, positioning and messaging aligned with the product’s actual capabilities.

**3.8. Prototyping and validate experience:**

- **Description:** Prototype and validate the experience. Understand the comprehension, utility and usability.
- **Final responsible:** CPO
- **Who executes:** Design team, UX Research and Product Manager.
- **Deliverable:** Tested & probed prototype, results and adjustments.

**3.9. Resolve technical uncertaintinity:**

- **Description:** Identify and investigate critical technical assumptions, integration constraints and feasibility risks. Use focused technical spikes or proofs of concept where evidence is needed before committing to implementation.
- **Final responsible:** CTO
- **Who executes:** Tech Lead, Software Architects and relevant engineers, with specialists as needed
- **Deliverable:** Technical feasibility findings, proof-of-concept results, recommended approaches, and remaining risks with mitigation actions.

**3.10. Define measurement:**

- **Description:** Define how product success and user behaviour will be measured. Specify outcome metrics, activation criteria, funnel stages, events and data requirements, distinguishing observed results from assumptions.
- **Final responsible:** CPO, in collaboration with CMO and CTO.
- **Who executes:** Product/Data Analyst and Product Manager, with Growth Marketing and Engineering input.
- **Deliverable:** Measurement plan, metric definitions, analytics event specifications and an initial reporting plan.

**3.11. Plan Development:**

- **Description:** Break the agreed scope into incremental deliveries. Identify dependencies, estimate effort and uncertainty, allocate capacity, and define acceptance and release criteria. Prepare sufficient detail for the first increment.
- **Final Responsible:** CPO for product priorities and scope; CTO for technical delivery planning and engineering capacity.
- **Who executes:** Product Manager, Engineering Manager and Tech Lead, with Design, Engineering, QA and Operations input.
- **Deliverable:** Prioritized backlog, initial delivery plan, dependency map, effort estimates, resource allocation and agreed acceptance and release criteria.

###### 4. Development and Validation:

**4.1. Prepare development environments and delivery foundations:**

- **Description:** Establish repositories, development and testing environments, configuration management, access controls and CI/CD pipelines. Define the engineering conventions and automated checks needed to build and validate product increments consistently.
- **Final Responsible:** CTO.
- **Who executes:** Tech Lead, Engineering team and Platform/DevOps Engineers, with Security input.
- **Deliverable:** Working development and testing environments, configured delivery pipelines, repository conventions and environment setup documentation.

**4.2. Implement product features incrementally:**

- **Description:** Implement prioritized features across frontend, backend and relevant platforms. Apply the agreed business rules, permissions, designs and acceptance criteria, including error handling and relevant interface states.
- **Final Responsible:** CTO for implementation; CPO for scope and requirement decisions.
- **Who executes:** Engineering team and Tech Lead, collaborating with Product Manager and Product Designer.
- **Deliverable:** Working product increments, implementation-level tests, updated technical documentation and traceability to requirements.

**4.3. Implement integrations and data handling:**

- **Description:** Connect internal components and external services. Implement data storage, validation, synchronization and failure handling. Prepare and test imports or migrations where required, including data reconciliation and recovery procedures.
- **Final Responsible:** CTO.
- **Who executes:** Backend/Integration Engineers, Data Engineers and relevant specialists, with QA and Security input.
- **Deliverable:** Tested integrations and data flows, verified interface contracts, and migration or import procedures where applicable.

**4.4. Review code quality and maintainability:**

- **Description:** Review changes continuously for correctness, clarity, architectural consistency and maintainability. Run appropriate automated checks, address review findings and document significant implementation decisions or accepted technical debt.
- **Final Responsible:** CTO.
- **Who executes:** Peer Engineers, Tech Lead and Software Architect where applicable.
- **Deliverable:** Reviewed changes, automated quality-check results, documented technical decisions and tracked technical debt.

**4.5. Perform functional and regression testing:**

- **Description:** Verify that features, business rules, permissions and integrations behave as specified. Test critical end-to-end journeys, failure scenarios and regressions, combining automated and exploratory testing according to risk.
- **Final Responsible:** CTO, with CPO clarifying expected product behaviour.
- **Who executes:** QA Engineers, Engineering team and Product Manager.
- **Deliverable:** Test results linked to requirements, reusable automated tests, defect reports and verified fixes.

**4.6. Validate non-functional requirements:**

- **Description:** Evaluate the implemented product against agreed performance, capacity, reliability, accessibility and compatibility requirements. Test relevant failure and recovery scenarios under representative conditions.
- **Final Responsible:** CTO, in collaboration with CPO and COO.
- **Who executes:** QA Engineers, Engineering team, Platform/SRE Engineers and Accessibility Specialists where needed.
- **Deliverable:** Non-functional validation results, identified limitations, remediation actions and documented residual risks.

**4.7. Implement and verify security and privacy controls:**

- **Description:** Implement and assess controls for authentication, authorization, secrets, sensitive data and relevant privacy requirements. Perform risk-appropriate security testing, investigate findings and verify remediation of critical issues.
- **Final Responsible:** CTO for implementation; CISO for security assessment and security-risk recommendations, with the privacy/legal owner consulted where applicable.
- **Who executes:** Engineering team, Security Engineers and relevant privacy specialists.
- **Deliverable:** Implemented controls, security assessment findings, verified remediation evidence and documented unresolved risks with assigned owners.

**4.8. Implement analytics and observability:**

- **Description:** Implement the agreed product events and business metrics alongside technical logs, metrics, traces and alerts. Verify data accuracy, useful diagnostic context and appropriate handling of sensitive information.
- **Final Responsible:** CTO for instrumentation and technical observability; CPO for product measurement acceptance.
- **Who executes:** Engineering team, Product/Data Analyst and Platform/SRE Engineers, with Growth Marketing and Security input.
- **Deliverable:** Validated analytics instrumentation, operational dashboards, configured alerts and measurement-quality checks.

**4.9. Validate product acceptance and usability:**

- **Description:** Evaluate the implemented experience against user needs, designs and acceptance criteria. Conduct product acceptance reviews and usability sessions with representative users, then prioritize and resolve material gaps.
- **Final Responsible:** CPO.
- **Who executes:** Product Manager, Product Designer, UX Researcher and QA, with relevant stakeholders and representative users participating.
- **Deliverable:** Product acceptance report, usability findings, prioritized adjustments and an explicit acceptance status for the release scope.

**4.10. Prepare operations and support:**

- **Description:** Prepare the people and procedures needed to operate and support the product. Define ownership, support workflows, incident response, escalation, backup and recovery processes, and operational training.
- **Final Responsible:** COO for service and support readiness; CTO for technical operations readiness.
- **Who executes:** Operations, Customer Support/Success, Platform/SRE and Engineering teams, with Product and Security input.
- **Deliverable:** Operational runbooks, support documentation, ownership and escalation paths, recovery procedures and training materials.

**4.11. Verify release readiness:**

- **Description:** Consolidate product, engineering, security and operational validation evidence. Prepare the release candidate, deployment and rollback procedures, migration sequence where relevant, and explicit go/no-go criteria. Review outstanding issues before authorizing progression to launch.
- **Final Responsible:** CTO for technical release readiness, with CPO, COO and CISO approving readiness within their respective areas.
- **Who executes:** Engineering Manager/Tech Lead, QA Lead, Product Manager, Platform/DevOps and Operations representatives.
- **Deliverable:** Release candidate, consolidated readiness assessment, deployment and rollback plan, known-issues register and a recorded decision to proceed or address remaining blockers.

###### 5. Launch

**5.1. Coordinate the launch and confirm readiness:**

- **Description:** Coordinate the technical, product, commercial and operational launch. Consolidate readiness evidence from the previous phase, confirm dependencies, assign owners and establish launch timing, rollout stages and go/no-go criteria.
- **Final Responsible:** CPO for cross-functional launch coordination, with CTO, CMO and COO approving readiness within their areas.
- **Who executes:** Product Manager, Product Marketing Manager, Engineering Lead and Operations Lead.
- **Deliverable:** Integrated launch plan, ownership and dependency map, agreed launch criteria and a recorded readiness decision.

**5.2. Confirm legal, privacy and security readiness:**

- **Description:** Review applicable terms, privacy notices, licensing, commercial claims and contractual requirements. Confirm that agreed security controls are operational and that unresolved legal or security issues have been assessed before release.
- **Final Responsible:** CLO for legal readiness; CISO for security readiness, with CTO responsible for technical remediation.
- **Who executes:** Legal Counsel, Privacy Specialists and Security Engineers, collaborating with Product, Engineering and Marketing.
- **Deliverable:** Reviewed legal materials, legal and security readiness assessments, documented outstanding issues and applicable release conditions.

**5.3. Finalize marketing and launch design assets:**

- **Description:** Prepare and verify the public-facing materials needed to explain and promote the released product. Ensure visual identity, messaging, screenshots, demonstrations and commercial promises match the actual release.
- **Final Responsible:** CMO, with CPO confirming product accuracy.
- **Who executes:** Product Marketing Manager, Brand/Visual Designer, Copywriter and Content team, with Product Designer input.
- **Deliverable:** Launch website or landing pages, campaign creatives, product demonstrations, release notes, email and social content, and store listings where applicable.

**5.4. Prepare acquisition and commercial channels:**

- **Description:** Configure and verify the channels through which users discover, access, trial or purchase the product. Confirm pricing presentation, conversion paths, lead handling and sales readiness where relevant to the business model.
- **Final Responsible:** CMO for acquisition channels; CRO for sales readiness where a sales function exists.
- **Who executes:** Growth Marketing, Marketing Operations, Sales Operations and Product Marketing, with Engineering and Finance support.
- **Deliverable:** Ready-to-activate acquisition channels, verified conversion paths, commercial materials and defined lead or sales handoffs.

**5.5. Deploy the approved release to production:**

- **Description:** Deploy the approved release, execute required migrations and verify production configuration. Run smoke tests on critical journeys, confirm monitoring and recovery readiness, and control access according to the rollout plan.
- **Final Responsible:** CTO.
- **Who executes:** Platform/DevOps Engineers, Engineering team, Tech Lead and QA, with Security support.
- **Deliverable:** Deployed production release, deployment and migration records, production verification results and an operational rollback or recovery procedure.

**5.6. Conduct a pilot or controlled rollout:**

- **Description:** Where appropriate, introduce the product to a limited audience before broader exposure. Observe real usage, validate operational assumptions, collect feedback and assess whether to expand, pause or revise the rollout.
- **Final Responsible:** CPO for audience expansion decisions, with CTO and COO confirming technical and operational readiness.
- **Who executes:** Product Manager, Engineering, QA, Customer Success/Support and UX Researcher.
- **Deliverable:** Pilot or rollout findings, prioritized issues, user feedback and a recorded decision on the next rollout stage.

**5.7. Activate public launch and acquisition campaigns:**

- **Description:** Execute the approved launch communications and acquisition activities in coordination with product availability. Activate relevant paid, organic, partnership, community and sales initiatives, adapting exposure to operational capacity.
- **Final Responsible:** CMO, in coordination with CRO where applicable.
- **Who executes:** Growth Marketers, Content and Social teams, PR/Communications, Partnership Managers and Sales.
- **Deliverable:** Published launch communications, active campaigns and commercial initiatives, and initial channel-performance results.

**5.8. Onboard and support the first users:**

- **Description:** Help initial users access the product, understand its value and complete their first meaningful tasks. Operate support and escalation processes, resolve adoption barriers and feed recurring issues back to Product and Engineering.
- **Final Responsible:** COO for onboarding and support operations; CPO for the in-product onboarding experience.
- **Who executes:** Customer Success, Customer Support, Product Manager and Engineering, with Lifecycle Marketing input.
- **Deliverable:** Operational onboarding and support workflows, initial activation findings, support records and prioritized adoption issues.

**5.9. Monitor and stabilize the launch:**

- **Description:** Closely monitor service health, security signals, data quality, critical user journeys and support demand. Triage incidents and defects, deliver necessary fixes, and pause or reverse rollout when agreed thresholds are breached.
- **Final Responsible:** CTO for technical stability, with CISO overseeing security response and COO coordinating customer-facing operations.
- **Who executes:** Engineering, Platform/SRE, Security, QA, Support and Product/Data Analysts.
- **Deliverable:** Launch monitoring reports, incident and defect records, verified fixes and an explicit stabilization status.

**5.10. Evaluate launch outcomes and transition to ongoing operations:**

- **Description:** Compare initial outcomes with launch objectives, accounting for sample size and observation time. Review acquisition, activation, customer feedback, service quality and commercial results where available. Assign ongoing ownership and prioritize follow-up improvements.
- **Final Responsible:** CPO for product outcome evaluation; COO for the transition to ongoing service operations.
- **Who executes:** Product Manager, Product/Data Analyst, Marketing, Engineering, Operations and Finance representatives.
- **Deliverable:** Launch review, initial performance baseline, prioritized improvement backlog, ongoing ownership assignments and an agreed transition to Operation and Evolution.

###### 6. Operation and evolution

**6.1. Operate and monitor the service:**

- **Description:** Keep the product available and functioning within agreed service objectives. Monitor infrastructure, application health, integrations, capacity and critical user journeys, and respond to operational deviations.
- **Final Responsible:** CTO for technical service operation, in coordination with COO.
- **Who executes:** Platform/SRE Engineers, Engineering team and Operations.
- **Deliverable:** Service-health dashboards, service-level reports, capacity assessments and operational records.

**6.2. Provide customer support and customer success:**

- **Description:** Resolve user questions and problems, support onboarding and adoption, and help customers achieve their intended outcomes. Maintain support resources and identify recurring issues requiring product or operational improvements.
- **Final Responsible:** COO.
- **Who executes:** Customer Support, Customer Success and Operations, with Product and Engineering support.
- **Deliverable:** Support resolutions, updated knowledge resources, customer-success plans where relevant, and categorized customer feedback.

**6.3. Manage incidents and recovery:**

- **Description:** Detect, triage and resolve service disruptions. Coordinate technical response, customer communication and recovery, then investigate significant incidents and assign preventive actions.
- **Final Responsible:** CTO for technical incident response, with CISO leading security incidents and COO coordinating customer-facing operations.
- **Who executes:** On-call Engineers, Platform/SRE, Security, Support and relevant service owners.
- **Deliverable:** Incident records, recovery verification, stakeholder communications, post-incident reviews and tracked corrective actions.

**6.4. Maintain technical health:**

- **Description:** Maintain dependencies, infrastructure, integrations and automated tests. Address technical debt, compatibility changes, performance degradation and obsolete components according to business impact and risk.
- **Final Responsible:** CTO.
- **Who executes:** Engineering team, Tech Lead, Platform Engineers and QA.
- **Deliverable:** Maintenance updates, dependency and lifecycle tracking, prioritized technical-debt backlog and technical-health assessments.

**6.5. Maintain security, privacy and compliance:**

- **Description:** Monitor threats and vulnerabilities, review access and data-handling practices, and maintain applicable security and privacy controls. Address findings and reassess obligations when the product, market or operating context changes.
- **Final Responsible:** CISO for security oversight; CLO or designated privacy/legal owner for applicable legal obligations; CTO for technical remediation.
- **Who executes:** Security Engineers, Engineering, Privacy Specialists, Legal and Operations.
- **Deliverable:** Updated risk assessments, access reviews, vulnerability remediation records, control evidence and tracked compliance actions.

**6.6. Measure product and business outcomes:**

- **Description:** Evaluate activation, engagement, retention, customer satisfaction and relevant commercial results. Verify measurement quality, investigate changes and distinguish observed behaviour from assumptions or attribution estimates.
- **Final Responsible:** CPO for product outcomes, with CMO, CFO and COO owning metrics within their areas.
- **Who executes:** Product/Data Analysts, Product Manager, Marketing Analysts, Finance and Operations Analysts.
- **Deliverable:** Product and business dashboards, cohort and funnel analyses, measurement-quality findings and evidence-based performance reviews.

**6.7. Improve adoption, retention and commercial growth:**

- **Description:** Improve onboarding communications, lifecycle campaigns, acquisition channels and relevant sales or renewal processes. Coordinate these activities with product improvements to increase sustained customer value.
- **Final Responsible:** CMO for marketing and lifecycle activities; CPO for in-product adoption and retention; CRO for sales and renewals where applicable.
- **Who executes:** Growth Marketing, Lifecycle/CRM Marketing, Product, Customer Success and Sales.
- **Deliverable:** Growth and retention initiatives, campaign and funnel improvements, commercial playbooks and measured outcomes.

**6.8. Conduct continuous discovery:**

- **Description:** Continuously investigate user needs, usage patterns, support themes, churn reasons and market changes. Identify emerging problems and opportunities, and test whether proposed improvements address meaningful needs.
- **Final Responsible:** CPO.
- **Who executes:** Product Manager, UX Researcher, Product Designer and Product/Data Analyst, with Marketing and Customer Success input.
- **Deliverable:** Updated research findings, opportunity backlog, revised hypotheses and supporting evidence for potential improvements.

**6.9. Prioritize the evolution roadmap:**

- **Description:** Compare product opportunities, defects, technical debt and operational needs against strategic goals. Balance expected value, risk, effort and available capacity, and determine the next outcomes and increments to pursue.
- **Final Responsible:** CPO for product priorities, in collaboration with CTO, COO, CMO and CFO.
- **Who executes:** Product Manager, Engineering Manager, Tech Lead and relevant functional leads.
- **Deliverable:** Updated outcome-based roadmap, prioritized backlog, capacity allocation and documented prioritization decisions.

**6.10. Deliver and evaluate improvements:**

- **Description:** Route selected improvements through the appropriate discovery, design, development, validation and release activities. Use controlled experiments where suitable, measure results and decide whether to retain, expand, revise or reverse changes.
- **Final Responsible:** CTO for technical delivery; CPO for product acceptance and outcome evaluation.
- **Who executes:** Product, Design, Engineering, QA and Data teams, with Marketing and Operations involved as needed.
- **Deliverable:** Released improvements, validation and experiment results, updated documentation and recorded follow-up decisions.

**6.11. Optimize operational and economic efficiency:**

- **Description:** Review operating costs, infrastructure consumption, acquisition economics, support effort and vendor dependencies. Identify efficiencies while preserving agreed service quality, customer value and risk boundaries.
- **Final Responsible:** CFO for economic oversight, with CTO and COO accountable for improvements within their areas.
- **Who executes:** Finance Analysts, Platform/Engineering, Operations and Marketing Analysts.
- **Deliverable:** Cost and unit-economics reviews, efficiency initiatives, updated forecasts and measured savings or productivity improvements.

**6.12. Review strategic direction and lifecycle decisions:**

- **Description:** Periodically reassess whether the product continues to meet strategic, customer and economic objectives. Decide whether to maintain direction, increase investment, reposition, consolidate, replace or retire the product.
- **Final Responsible:** CEO, in collaboration with CPO, CFO, CTO, CMO and COO.
- **Who executes:** Product and Business/Strategy leads, supported by Finance, Data and relevant functional teams.
- **Deliverable:** Strategic product review, updated investment decisions and direction, or an approved transition into Retirement or Replacement when appropriate.

###### 7. Quit or Replace.

**7.1. Decide and approve retirement or replacement:**

- **Description:** Assess whether to discontinue the product or replace it. Define the rationale, affected scope, customer impact and conditions for completing the transition.
- **Final Responsible:** CEO, in collaboration with CPO, CFO and CTO.
- **Who executes:** Product Manager and Business/Strategy Lead, with Finance, Engineering and Operations input.
- **Deliverable:** Approved retirement or replacement decision, scope, rationale and completion criteria.

**7.2. Plan and communicate the transition:**

- **Description:** Define timelines, responsibilities, support arrangements and available alternatives. Communicate the changes, deadlines and required actions to affected users, customers, partners and internal teams.
- **Final Responsible:** COO, in collaboration with CPO, CMO and CLO.
- **Who executes:** Product Manager, Operations, Customer Success, Marketing/Communications and Legal.
- **Deliverable:** Transition plan, stakeholder communications, support arrangements and assigned responsibilities.

**7.3. Transition users and data:**

- **Description:** Migrate users, workflows and required data to a validated replacement, or provide appropriate export and exit options. Verify data integrity, access and transition outcomes before disabling the original service.
- **Final Responsible:** CTO for technical migration; COO for customer transition.
- **Who executes:** Engineering, Data Engineers, QA and Customer Success, with Security and Privacy input.
- **Deliverable:** Verified migrations or exports, customer transition status and documented exceptions requiring follow-up.

**7.4. Decommission the product securely:**

- **Description:** Disable the retired application, integrations, scheduled processes and product-specific infrastructure. Revoke obsolete access and credentials, protect shared dependencies, and archive or delete data according to approved retention requirements.
- **Final Responsible:** CTO, with CISO overseeing security and CLO confirming applicable legal requirements.
- **Who executes:** Engineering, Platform/DevOps, Security and Data teams.
- **Deliverable:** Decommissioning records, data disposition records and verification that retired components and access are inactive.

**7.5. Complete commercial and operational closure:**

- **Description:** Resolve remaining customer and supplier obligations, final billing or refunds where applicable, and unnecessary recurring expenditure. Reassign resources, preserve essential knowledge and assign ownership of any residual obligations.
- **Final Responsible:** COO for operational closure; CFO for financial closure, with CLO supporting contractual matters.
- **Who executes:** Operations, Finance, Legal, Customer Success and Product Manager.
- **Deliverable:** Closure report, reconciled financial records, resolved or assigned obligations, archived documentation and lessons learned.

##### Workflow 2: Partial PDDL: Product definition -> (type:product)

** From "Workflow 1: Full-PDLC", include the following phases by default. And ask the user whether they want all sub-phases, or just some of them.

- Phase 1: Idea and Strategy
- Phase 2: Discovery
- Phase 3: Definition and design

##### Workflow 3: Partial PDLC: Development-only -> (type:dev)

- (type:dev-full) Full-Stack (preset)
- (type:dev-back) Backend (preset)
- (type:dev-front) Frontend (preset)

##### General (Plan / Conversational / Helper) -> (type:general)

- (type:general-architecture) Architecture (preset)
- (type:general-product) Plan / Idea (preset)

#### 2.2. Set up Project:

##### 2.2.1. Empty Project

- 2.2.1.1. If (type:dev) Select the technologies
- 2.2.1.1. If (type:product) Specify the scope (plan, conversation, support & help)

##### 2.2.2. Existing Project

- 2.2.2.1. Explore Codeabase

#### 2.3. Show presets + current configuration + suggestions. (documentation, code, backlog..)

#### 2.4. Accept / Modify / Cancel

#### 2.5 (continue with the existing flow)

## `/CAOO-kickoff` -> starts / resumes / open the current Claude workflow..

1. Show the pre-configured setup during cwi: development | general... stack...
2. Allow modifications:
    - General CWI init cofiguration.
    - Check / Ask for / Set the documentation path (requirements, specs, features...)
    - Change the setup type ( development | general | .. )
    - Change CAOO configuration:
        - engineering-dev-plan-mode: auto | human
        - engineering-architecture-plan-mode: auto | human
        - product-plan-mode: auto | human
        - designer-detail-mode: poor | empty | full
        - designer-plan-mode: auto | human | mcp
3.
