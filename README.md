# Concierge.AI_v2
Multi-language, modular based chat support for guest-hotel interactions

## Installation

Concierge.AI_v2 supports Python 3.12 and Python 3.13. On a new Windows system,
clone the repository and run these commands in PowerShell:

```powershell
git clone <repository-url>
cd Concierge.AI_v2

python -3.13 -m venv .venv

.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip

python -m pip install --only-binary=llama-cpp-python "llama-cpp-python==0.3.34" --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu

python -m pip install -e .
python .\run.py
```

Use `.venv\Scripts\activate.bat` in Command Prompt or
`source .venv/Scripts/activate` in Git Bash. The editable installation is
required because the application loads its JSON data, README, favicon,
Streamlit entry point, and model artifacts from the source checkout.

For development and tests, install the optional development dependencies:

```powershell
python -m pip install -e ".[dev]"
```

`pyproject.toml` is the single source of truth for Python dependencies. When
`python run.py` starts, the application checks these project-local model paths:

- `src/conversation/models/translation/model_data/nllb-200-distilled-600M/`
- `src/conversation/models/translation/model_data/lid.176.bin`
- `src/conversation/models/intent/model_data/intent-classifier/`
- `src/conversation/models/information/model_data/Qwen3-8B-Q4_K_M.gguf`

Missing model files are downloaded automatically before the API and client
processes start. The first start therefore requires an internet connection and
approximately 8 GB of free disk space. Download progress and errors are written
to the console. The same check can be run manually:

```powershell
python -m conversation.models.translation.download_models
```

The default dependency resolves the standard PyPI build of PyTorch. If a CUDA
build is required, install the matching `torch==2.11.0` build for the target
system before installing Concierge.AI_v2. On Windows, `llama-cpp-python` may
require a C/C++ build toolchain when pip cannot find a compatible pre-built
wheel.

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

## Streamlit concierge client

Start the API and Streamlit client together from the repository root:

```shell
python run.py
```

The Streamlit server address, port, headless mode, development mode, and
usage-statistics setting are explicit in `ApplicationSettings` as
`streamlit_host`, `streamlit_port`, `streamlit_headless`,
`streamlit_development_mode`, and `streamlit_gather_usage_stats`. The default
client URL is `http://127.0.0.1:8501`.

The launcher supervises the API and client as one process pair. If either
process exits during development, the other process is stopped and both are
started again so their runtime state stays synchronized.

To run only the guest client in a separate terminal, use:

```shell
python -m streamlit run src/client/app.py --global.developmentMode false --server.address 127.0.0.1 --server.port 8501
```

The client uses `http://127.0.0.1:8000/api/conversation` by default. Set
`CONCIERGE_API_URL` to another absolute URL ending in `/api/conversation` when
the API is hosted elsewhere. The client rejects URLs outside that route family.

Opening the page initializes a session automatically. If the guest submits a
message after that session has ended or before a session ID is available, the
client initializes a fresh session and then sends the already-entered message.
Messages, room-card selections, confirmations, inactivity termination, and
tab-close termination all use endpoints below `/api/conversation`. A lightweight
Streamlit fragment checks for 10 minutes without a submitted message or shortcut
and then closes the session.

Tab-close delivery uses `navigator.sendBeacon` on `pagehide`, with a
`fetch(..., keepalive=True)` fallback. Browser shutdown and mobile lifecycle
events cannot guarantee that either request reaches the API. The 10-minute
watchdog reliably handles an open but idle Streamlit page, but it cannot run
after the page has been destroyed. Guaranteed cleanup after a failed unload
request would require a server-side session TTL or cleanup job.
