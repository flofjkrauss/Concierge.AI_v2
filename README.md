# Concierge.AI_v2
Multi-language, modular based chat support for guest-hotel interactions

# ConciergeAI Architecture

The diagram below is intentionally simplified for README use. The editable draw.io version contains the full framework mapping, intent lifecycle, and response routing.

```mermaid
flowchart TD
    U["User"] --> UI["Client UI<br/>Streamlit or web frontend"]
    UI --> API["HTTP boundary<br/>FastAPI + Pydantic"]
    API --> WF["Conversation workflow<br/>LangGraph"]
    WF --> NLP["Translate / classify / extract<br/>Translation adapter + NLP models"]
    NLP --> TYPE{"Intent type?"}

    TYPE -->|"Unknown / simple"| RESPONSE["Compose response"]
    TYPE -->|"Direct"| DISPATCH["Application dispatcher"]
    TYPE -->|"Stateful"| STATE["Merge and validate intent state"]
    STATE -->|"Missing fields"| ASK["Ask a focused follow-up"]
    ASK --> RESPONSE
    STATE -->|"Qualified"| DISPATCH

    DISPATCH --> DOMAIN["Deterministic domain services"]
    DOMAIN --> DATA[("Repositories / database")]
    DATA --> RESPONSE

    DOMAIN --> OPTIONS["AvailabilityResult / RoomOption"]
    OPTIONS --> SELECT["User selects an offered room"]
    SELECT --> SUMMARY["Trusted BookingSummary"]
    SUMMARY --> CONFIRM{"Explicit confirmation?"}
    CONFIRM -->|"Not yet"| RESPONSE
    CONFIRM -->|"Yes"| CREATE["Create reservation"]
    CREATE --> DATA

    RESPONSE --> RETURN["Translate response / persist state / return HTTP"]
    RETURN --> UI

    NLP -.->|"language interpretation only"| BOUNDARY["Prices, availability, booking IDs, status, and policy remain server-controlled"]

    classDef client fill:#dae8fc,stroke:#6c8ebf,color:#1f2937;
    classDef api fill:#d5e8d4,stroke:#82b366,color:#1f2937;
    classDef workflow fill:#ffe6cc,stroke:#d79b00,color:#1f2937;
    classDef model fill:#e1d5e7,stroke:#9673a6,color:#1f2937;
    classDef service fill:#f8cecc,stroke:#b85450,color:#1f2937;
    classDef storage fill:#f5f5f5,stroke:#666666,color:#1f2937;
    classDef output fill:#d5e8e3,stroke:#0e8088,color:#1f2937;
    classDef decision fill:#fff2cc,stroke:#d6b656,color:#1f2937;

    class U,UI,SELECT client;
    class API api;
    class WF,TYPE,STATE,ASK,DISPATCH workflow;
    class NLP model;
    class DOMAIN,CREATE service;
    class DATA storage;
    class RESPONSE,RETURN,OPTIONS,SUMMARY output;
    class CONFIRM,BOUNDARY decision;
```
