# ModelCouncil

ModelCouncil is a web-first synthetic consumer society simulator for product and pitch analysis. It combines structured consumer traits, weighted K-nearest-neighbour social networks, language conversations, opinion dynamics, purchase-intent modelling, and interactive analytics.

## Current stage

Initialization / architecture foundation. The repository contains a bootable web/API skeleton and the first simulation-domain contracts. The complete behavioural engine will be implemented incrementally after the initialization review.

## Core rule

The LLM gives agents language. It does **not** own agent identity or directly overwrite opinion/purchase state. Agent identity lives in deterministic state, traits, memories, relationships, and simulation history.

## Repository map

- `frontend/` — Next.js 16 App Router web application.
- `backend/` — FastAPI web API and application services.
- `simulation/` — framework-independent Python simulation engine.
- `data/traits/` — editable trait/distribution source definitions.
- `data/generated/` — generated local simulation artifacts; ignored by Git.
- `tests/` — simulation and API tests.
- `docs/` — architecture, decisions, specifications, and implementation plans.
- `idea.md` — complete product/concept history and current vision.
- `project coding.md` — codebase map, file responsibilities, execution flow, and development rules.
- `context.md` — compact master context for Codex/AI coding sessions.

## Prerequisites

- Python 3.12+ (current machine: Python 3.13)
- Node.js 20.9+ (Next.js 16 minimum)
- npm

On this Windows machine, PowerShell blocks the `npm.ps1` shim. Use `npm.cmd` instead of changing the system execution policy.

## Initial local setup

### One-command dependency bootstrap

From `E:\model counsel`:

```powershell
.\scripts\bootstrap.ps1
```

This creates `.venv`, installs Python dependencies, and runs `npm.cmd install` in `frontend/`.

### Backend / simulation

From `E:\model counsel`:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

API docs will be available at `http://127.0.0.1:8000/docs`.

### Frontend

Open a second terminal:

```powershell
cd "E:\model counsel\frontend"
npm.cmd install
npm.cmd run dev
```

Open `http://localhost:3000`.

### Verification

```powershell
.\scripts\check.ps1
```

The script always runs Python tests and runs frontend lint/build when `frontend/node_modules` is installed.

## Secrets

Put the DeepSeek key only in the root `.env`:

```text
DEEPSEEK_API_KEY=your_key_here
```

Never put the key in `frontend/`, browser code, Git, screenshots, or documentation.

## Initial web flow

```text
Browser
  -> Next.js product-pitch form
  -> FastAPI preview endpoint
  -> simulation configuration/preset layer
  -> response shown in the web UI
```

The first development phase will replace the preview response with the actual population -> KNN -> conversation -> synchronous opinion-update engine.

## Planned deployment

```text
GitHub
  |- Vercel -> Next.js frontend
  |- container host -> FastAPI backend
  `- Supabase/PostgreSQL -> later persistence/authentication
```

The simulation package remains independent from deployment infrastructure so it can be tested and benchmarked locally.
