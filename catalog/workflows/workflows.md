# Claude Workspace Init 

## Workflows

# 1. Full Stack Workflow

- SelfAI: General Director.
    - General project documentation.
    - Global Idea
    - Idea Breakdown: detailed features
    - Architecture & Stack
    - Global Rules
    - Global Guidelines
    - Agent coordinator / agent orquestrator / feed agents (human in the loop)

    - # Config:
        - engineering-dev-plan-mode: auto | human

        All matters related to engineering development and technical questions.

        - engineering-architecture-plan-mode: auto | human
        All matters related to the architecture design & software engineering desing / plan.

        - product-plan-mode: auto | human 
        All matters related to product, narrative, idea, usage, features, mvp, backlog.


        - designer-detail-mode: poor | full | empty
        * poor: it helps you creating the full specs, ask you questions, review the exsiting definitions etc.
        * full: reviews and helps shaping the final documentation.
        * empty: ask questions and helps building the product.
        

        - designer-plan-mode: auto | human | mcp
        All matters related to product, narrative, idea, usage


** Product 

- product-designer: Given a full documentation project, helps understanding the idea, signals inconsistency, checks the different flows,    

- product-engineer: Given a full reviewed product documentation by the `product-engineer`, translates it into technical requirements (functional and non functional) by generating the full documentation inside the folder '/docs/', so the `arquitecture-designer can consume it.

** Designers 

- 

** Architect & Software Engineering Team

- architecture-designer: Designs & plans the architecture of the whole system. If the parent invoker has the 'plan-mode:auto' the agent will accept the proposed plan and jump into the next step: `architecture-reviewer` otherwise if 'engineering-architecture-plan-moed:human' it waits until human approval.

- architecture-reviewer: reviews the architecture and propose changes if any.
Triggers the `archify`skill to generate the visual diagram. Ig  for approval (if --engineering-plan-mode: human) or 

- api-designer: helps you design & plan the API following the best practices and REST/gRPC standards.


** Backend Team

- software-engineer: reads all the documentation and features, indentifying dependencies, patterns, repetitions, potential bottlenecks, data-structures,  

- software-optimizer: optimize functions, processes, trying to use the bes big-o complexity.
