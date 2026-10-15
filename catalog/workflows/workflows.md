> Historical design notes. The runtime loads the canonical [SPDLC definitions](spdlc/workflow.json) and [organization](../organizations/spdlc/organization.json), not this outline. Earlier acronyms, modes and integrations below are design history. Use the [SPADO usage manual](../../USAGE.md) for current commands and supported behavior.

# Claude Workspace Init 

## Workflows

# 1. Full Stack Development Workflow

- Chief Agent Orquestrator Officer (CAOO)

    - General Product Idea      (all the documentation about the project; functionality, goals, features..)
    - General Project Set Up    (rules, guidelines, style, stack, architecture)
   
    - Agent coordinator / Agent orquestrator / feed agents 
    - Report to Human ( Human in the loop + Human actions (mcp via slack, whatsapp or others) )
    - Roadmap knowledge / Planner (agent planner helps CEOlf)
    - Execution Planner:
        - All agents reports to their Leads (Agent-Leads: A2A?? ).
        - CAOO & Agent-Leads discuss and define the roadmap and priorities (define backlog). | Human approval.

    # CAOO Tools:
    - Retrieve Documentation (Read Filesystem / MCP (google drive, notion, other))
    - Write / Reaad files
    - Bash

    # CAOO Configuration:

    The workflow can be executed with the following optional configuration:

        - auto: the agent takes the decision based on the definitions/requirements/rules/guidelines and reports to the General Director.
        - human: the agent stops its execution and waits for human approval. v

        - *engineering-dev-plan-mode:* auto | human
        All matters related to engineering and technical development.

        - engineering-architecture-plan-mode: auto | human
        All matters related to the architecture design & software engineering desing / plan.

        - product-plan-mode: auto | human 
        All matters related to product, narrative, idea, usage, features, mvp, backlog.

        - designer-detail-mode: poor | full | empty
        
            - poor:     it helps you creating the full specs, ask you questions, review the exsiting definitions etc.
            - full:     reviews and helps shaping the final documentation.
            - empty:    ask questions and helps building the product.

        - designer-plan-mode: auto | human | mcp
        All matters related to product, narrative, idea, usage
    
    # Sub-Agents Behaviour:
        - Agents reports to the General Director and they write into the DB: what, why, when and how it took a certain decision, with the context to perform that action.
        - Model Selector: depening on the task, the agent will use a specific model. (sonnet, haiku, opus, fable)
        
    # Sub-Agents:

        # Product Team:

            - product-designer: Given a full documentation project, helps understanding the idea, signals inconsistency, checks the different flows,     

            - product-engineer: Given a full reviewed product documentation by the `product-engineer`, translates it into technical requirements (functional and non functional) by generating the full documentation inside the folder '/docs/', so the `arquitecture-designer can consume it.


        # Design Team:

            - design-engineer: If visual materials given such as screenshots / mockups, it translates them into into pixel perfect code.
            - design-verifier: Given screenshots / mockups.. Compares with the screenshots

        # Software Architecture Team:

            - architecture-designer: Designs and plans the architecture of the whole system. If the parent invoker has the 'plan-mode:auto' the agent will accept the proposed plan and jump into the next step: `architecture-reviewer` otherwise if 'engineering-architecture-plan-moed:human' it waits until human approval.

            - architecture-reviewer: reviews the architecture and propose changes if any.
            Triggers the `archify`skill to generate the visual diagram. Ig  for approval (if --engineering-plan-mode: human) or 

            - api-designer: helps you design & plan the API following the best practices and REST/gRPC standards.

        # Backend Team: 

            - tdd-engineer: implements features and code through the TDD methodology.

            - qa-engineer: tests the whole system. unit test, e2e tests, integrity tests, integration tests etc..

            - code-reviewer: reviews the code, and fixes if any bug encountered. 
                - python-review (skill)
                - react-review
                - fastapi-review (skill)
                - django-review (skill)
                - nextjs-review (skill)
                - express-review (skill)
                - flask-review (skill)
                - nodejs-review (skill)
                ..

            - software-engineer: reads all the documentation and features, indentifying dependencies, patterns, repetitions, potential bottlenecks, data-structures,  

            - software-optimizer: optimize functions, processes, trying to use the best big-o complexity, without changing the behaviour and output.

            - software-refractorer: 

            - git-workflow


        # DevOps Team

            - ci-cd:
            - docker: 
            - infra-planner:
            - infra-engineer: build on cloud.
        
        # Security Team
            - pentest
            - ddos
            - ...


    # Workflow: Software Development Life Cycle (SDLC):
    - *Planning & Feasibility:* Define project goals, scope, timelines, budget, and technical or financial viability.
        - 
    - *Requirements Analysis:* Gather functional and non-functional specifications, often producing a Software Requirements        Specification (SRS) document.
        -
    - *System Design:* Create high-level design (HLD) and low-level design (LLD) blueprints, database schemas, and architecture plans.
        -
    - *Implementation (Coding):* Write source code, build components, and integrate APIs based on the design documents.
        -
    - *Testing:* Run unit, integration, system, and User Acceptance Testing (UAT) to catch and fix defects.
        -
    - *Deployment:* Release the software to production or cloud/on-premise environments, frequently using Continuous Integration/Continuous Delivery (CI/CD) pipelines.
        -
    - *Maintenance & Operations:* Monitor system performance, fix post-release bugs, and roll out updates or new features.
        -
    
        