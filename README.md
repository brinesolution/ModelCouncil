# ModelCouncil

ModelCouncil is a web-first synthetic consumer society simulator for product and pitch analysis. It combines structured consumer traits, weighted K-nearest-neighbour social networks, deterministic background conversations, synchronous opinion dynamics, purchase-intent modelling, and browser-visible analytics.

## Current stage

**Phase 1 vertical slice implemented on `phase-1-vertical-slice`.**

The current branch supports an end-to-end synthetic run:

```text
Product pitch in Next.js
  -> FastAPI /api/v1/simulations/run
  -> Excel-backed synthetic population
  -> baseline product beliefs
  -> weighted KNN + weak ties
  -> capacity-limited conversation scheduling
  -> deterministic semantic conversations
  -> synchronous topic-belief aggregation
  -> overall opinion + purchase intent
  -> timeline / network / conversation DTOs
  -> browser result view
```

Phase 1 deliberately does **not** require live DeepSeek calls. The DeepSeek provider and root secret configuration remain available for the next dialogue phase, where selected interactions can be promoted from semantic background events to visible language conversations without changing agent identity/state ownership.

## Core rules

- Agent identity lives in deterministic traits, state, relationships, memories, and history.
- The LLM gives selected interactions language; it does not directly overwrite final opinion or purchase intent.
- KNN defines candidate social neighbourhoods, not automatic conversations with every neighbour.
- Round updates are synchronous: all conversations read the same start-of-round snapshot, then one combined state delta is committed.
- Results are synthetic simulation outputs, not validated real-market forecasts.

## Repository map

- `frontend/` — Next.js 16 App Router web application and result views.
- `backend/` — FastAPI API, schemas, and orchestration services.
- `simulation/` — framework-independent population/network/conversation/opinion engine.
- `data/traits/` — generated editable `.xlsx` trait workbooks, canonical JSON source, and integrity manifest.
- `scripts/generate_trait_workbooks.py` — deterministic trait-workbook generator.
- `tests/` — simulation, trait-integrity, and backend API regression tests.
- `docs/` — architecture, ADRs, specifications, and implementation plans.
- `idea.md` — full concept history and future direction.
- `project coding.md` — codebase map and development responsibilities.
- `context.md` — master context for Codex/AI coding sessions.

## Trait workbooks

`data/traits/` contains these generated workbooks:

- `archetypes.xlsx`
- `compatibility_rules.xlsx`
- `consumer_behaviour.xlsx`
- `decision_styles.xlsx`
- `demographics.xlsx`
- `economic_traits.xlsx`
- `emotions.xlsx`
- `occupations.xlsx`
- `personality.xlsx`
- `social_behaviour.xlsx`
- `technology.xlsx`

`catalog.source.json` is the versioned canonical seed definition used by `scripts/generate_trait_workbooks.py`. `catalog.manifest.json` stores the SHA-256 and size of every generated workbook. Tests fail if a workbook is missing or the manifest no longer matches its bytes.

To regenerate:

```powershell
python scripts\generate_trait_workbooks.py
```

## Prerequisites

- Python 3.12+
- Node.js 20.9+
- npm

On the Windows development machine, use `npm.cmd` if PowerShell blocks the `npm.ps1` shim.

## Local setup

From the repository root:

```powershell
.\scripts\bootstrap.ps1
```

This creates `.venv`, installs `backend/requirements.txt`, and installs frontend packages.

### Backend

```powershell
.\.venv\Scripts\Activate.ps1
python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

API docs: `http://127.0.0.1:8000/docs`

### Frontend

```powershell
cd frontend
npm.cmd run dev
```

Web app: `http://localhost:3000`

### Verification

```powershell
.\scripts\check.ps1
```

CI additionally runs Python tests plus frontend lint/build.

## Secrets / DeepSeek

The real API key belongs only in the root `.env`:

```text
DEEPSEEK_API_KEY=your_key_here
```

`.env` is Git-ignored. Never copy the key into frontend code, committed configuration, screenshots, test fixtures, or documentation.

Phase 1 uses deterministic background semantic conversations. Live DeepSeek dialogue is a later phase behind the existing provider/router abstraction.

## Population presets

| Mode | Population | Base K | Initiator rate | Max conversations per agent/round | Weak ties |
|---|---:|---:|---:|---:|---:|
| Small | 250 | 10 | 20% | 2 | 5% |
| Standard | 1,000 | 14 | 20% | 2 | 5% |
| Large | 5,000 | 18 | 20% | 2 | 5% |

Default round duration is five simulated minutes.

## Planned next phase

The next development stage should add selective DeepSeek-backed visible conversations, conversation-memory summaries, transcript replay on the network view, dialogue-mode routing/cost controls, and richer product/segment analytics. Multimodal product image/document ingestion remains a later normalized input layer.

## Planned deployment direction

```text
GitHub
  |- Vercel -> Next.js frontend
  |- container host -> FastAPI backend
  `- Supabase/PostgreSQL -> later persistence/authentication
```

The simulation package stays independent from deployment infrastructure so it can be tested, profiled, and reproduced without the web stack.
