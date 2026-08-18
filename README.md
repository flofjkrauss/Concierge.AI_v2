# Concierge.AI_v2

Concierge.AI_v2 is a local multilingual hotel chatbot for the fictional
**Harbour Light Hotel**. It combines natural-language interaction with
deterministic controls for availability, booking, cancellation, and hotel
information workflows.

## Installation

### Requirements

- Windows with PowerShell. The launcher uses Windows process-management APIs.
- Python 3.12 or 3.13. The bundled installer selects Python 3.13.
- An internet connection during the first start so missing models can be
  downloaded.
- At least 8 GiB of free space for model artifacts, plus space for Python
  packages and temporary download data. The current model set occupies about
  7.4 GiB after download.

### Recommended installation

Clone the repository and run the provided PowerShell installer:

```powershell
git clone <repository-url>
cd Concierge.AI_v2
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

The per-command execution-policy override is useful when local policy blocks
project scripts. The current installer invokes `python -3.13` to create the
environment. If the installed Python launcher does not support that form, use
the manual installation below with `py -3.13`.

### Manual installation

From the repository root in PowerShell:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install --only-binary=llama-cpp-python "llama-cpp-python==0.3.34" --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu
python -m pip install hf_xet
python -m pip install -e .
python .\run.py
```

Python 3.12 is also supported; replace `-3.13` with `-3.12` if required. Use
`.venv\Scripts\activate.bat` in Command Prompt or
`source .venv/Scripts/activate` in Git Bash. The editable installation keeps
the project-local data, client assets, and model paths available at runtime.

For development and quality checks, install the optional dependencies:

```powershell
python -m pip install -e ".[dev]"
```

`pyproject.toml` is the source of truth for Python dependencies. Installing the
pre-built CPU wheel for `llama-cpp-python` before the project avoids requiring a
local C/C++ compiler when that wheel is available for the selected Python
version.

## Model Downloads

Large model files are not included in the submission archive. Before starting
the API and client, `run.py` checks the configured local paths and downloads
each missing artifact. Progress and failure reasons are printed to the console.

| Purpose | Source | Local path |
| --- | --- | --- |
| Translation | [NLLB-200 distilled 600M](https://huggingface.co/facebook/nllb-200-distilled-600M) | `src/conversation/models/translation/model_data/nllb-200-distilled-600M/` |
| Language identification | [fastText lid.176](https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.bin) | `src/conversation/models/translation/model_data/lid.176.bin` |
| Intent classification | [Concierge intent detector](https://huggingface.co/floriankrauss/intent_detector_concierge) | `src/conversation/models/intent/model_data/intent-classifier/` |
| Information extraction | [Qwen3-8B GGUF](https://huggingface.co/Qwen/Qwen3-8B-GGUF) | `src/conversation/models/information/model_data/Qwen3-8B-Q4_K_M.gguf` |

The same check can be run without starting the application:

```powershell
python -m conversation.models.translation.download_models
```

After download, model inference is local. The first startup can take
considerably longer because it includes downloads, model loading, and warm-up.

## Running the Application

Start the complete application from the repository root:

```powershell
python .\run.py
```

The launcher checks that the configured ports are available, starts FastAPI at
`http://127.0.0.1:8000`, waits for its health endpoint, and then starts the
Streamlit client. Open:

`http://127.0.0.1:8501`

FastAPI and Streamlit are supervised as a pair. If either process exits, the
launcher stops the other and starts both again. Press `Ctrl+C` in the launcher
terminal to stop the application.

## Using the Chatbot

- Opening the client creates a conversation automatically.
- Enter natural-language requests for availability, booking lookup, booking,
  cancellation, or hotel information.
- Use the room cards and hotel-information topics for deterministic choices.
- Use the confirmation buttons before creating or cancelling a booking.
- If a conversation has ended, the next submitted message opens a new
  server-side session automatically.

## Project Overview

The application supports five primary guest workflows:

- room availability checks;
- booking lookup;
- booking requests;
- booking cancellation;
- hotel information.

Language detection, translation, intent classification, and structured
information extraction run locally. LangGraph coordinates the conversation,
while domain services and the JSON data layer remain authoritative for dates,
availability, prices, booking records, and cancellation results. The Streamlit
client combines free text with room cards, information-topic controls, and
explicit confirmation actions.

See [Technical Documentation](docs/technical_documentation.md) for the current
architecture, conversation flow, validation boundaries, and model management.

## Quality Checks

Install the development dependencies, then run:

```powershell
python -m pytest
python -m mypy src
python -m ruff check .
```

At the final documentation pass, all three checks were green. Pytest collected
and passed 630 unit tests.

## Known Limitations

- Local CPU inference can be slow, especially during model initialization and
  longer generative extraction requests.
- The first startup requires downloading approximately 7.4 GiB of model data.
- Translation and generative extraction can still misinterpret unusual or
  ambiguous input; deterministic validation reduces but cannot eliminate this.
- Conversation checkpoints are in memory, while hotel and booking data use
  local JSON files. This is suitable for a local prototype, not multi-process
  production persistence.
- The included hotel, inventory, customer, and booking data are fictional.
