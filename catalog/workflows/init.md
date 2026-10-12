1. execute cwi-init

2. cwi-init: 

    2.1. Select the type of setup:
        - Full Product
            - Product (CEO + CPO)
            - Development (CTO + CISO + CLO) 
            - Marketing / Design (CMO)

        - Development-only -> (type:dev)
            - (type:dev-full)       Full-Stack      (preset)
            - (type:dev-back)       Backend         (preset)
            - (type:dev-front)      Frontend        (preset)

        - General (Plan / Conversational / Helper) -> (type:general)
            - (type:general-architecture)              Architecture    (preset)
            - (type:general-product)                   Plan / Idea     (preset)
        
    2.2. Set up Project: 
        2.2.1. Empty Project
            2.2.1.1. If (type:dev)      Select the technologies
            2.2.1.1. If (type:product)  Specify the scope (plan, conversation, support & help)
        
        2.2.2. Existing Project
            2.2.2.1. Explore Codeabase
    
    2.3. Show presets + current configuration + suggestions. (documentation, code, backlog..)
    2.4. Accept / Modify / Cancel
    
    2.5 (continue with the existing flow) 


    /CAOO-kickoff -> starts / resumes / open the current Claude workflow..

    1. Show the pre-configured setup during cwi: development | general... stack... 
    2. Allow modifications:
        - General CWI init cofiguration.
        - Check / Ask for / Set the documentation path (requirements, specs, features...)
        - Change the setup type ( development | general | .. )
        - Change CAOO configuration:
            - engineering-dev-plan-mode:            auto | human
            - engineering-architecture-plan-mode:   auto | human
            - product-plan-mode:                    auto | human
            - designer-detail-mode:                 poor | empty | full
            - designer-plan-mode:                   auto | human | mcp
    3. 