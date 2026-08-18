# ModelCouncil

ModelCouncil is a web-first synthetic consumer-society simulator for testing product ideas, pricing, positioning, and conversation dynamics against a reproducible population of simulated consumers.

The current build combines structured consumer traits, deterministic product interpretation, weighted social networks, bounded opinion propagation, purchase-intent modelling, replayable conversations, optional LLM language rendering, and browser-visible analytics. Numerical simulation state remains Python-owned; language models can render conversations but cannot directly rewrite beliefs, product semantics, final opinion, or purchase intent.

> ModelCouncil produces **synthetic simulation outputs**. It is not an empirically calibrated market forecast, survey replacement, or claim about real consumer behaviour.

## Current build

A normal browser run currently follows this pipeline:

```text
Product / pitch / price / billing cadence
        |
        v
Next.js simulation form
        |
        v
FastAPI validation + preset/Advanced configuration resolution
        |
        v
Excel-backed synthetic population
        |
        +--> explicit trait activation + compatibility rules
        |
        v
Deterministic product taxonomy + semantic evidence
        |
        +--> usefulness / quality / trust / novelty
        +--> privacy / complexity / recurring-cost signals
        +--> reliability / serviceability / safety / data-practice risk
        +--> cancellation friction + reference-price context
        |
        v
Consumer-product fit + price context + baseline beliefs
        |
        v
Weighted KNN social graph + weak ties
        |
        v
Capacity-limited conversation scheduling
        |
        v
Semantic conversations + synchronous topic evidence aggregation
        |
        v
Bounded belief updates + purchase intent
        |
        +--> deterministic readable dialogue
        +--> optional DeepSeek rendering for selected conversations
        +--> optional Full Live rendering through DeepSeek or Ollama Local
        |
        v
Timeline + replay + network + conversation ledger + analytics
        |
        v
Local append-only run audit under logs/model-runs/
```

## Implemented capabilities

### Synthetic population

- Three built-in population presets: 250, 1,000, and 5,000 consumers.
- Deterministic seeded generation from editable Excel trait workbooks.
- Explicit activation manifest distinguishes active, derived, and provenance-only workbook fields.
- Compatibility rules and soft priors shape generated consumers without making every trait independent.
- Consumer context includes demographic, economic, decision-style, behavioural, emotional, social, occupation, and technology dimensions.
- Generated populations remain reproducible for the same input data and seed.

### Product-sensitive modelling

The simulator does not treat every pitch as the same generic product. It builds a deterministic product semantic profile from the submitted category, pitch, price, and billing cadence.

Current semantic signals include:

- usefulness, quality, trust, and novelty evidence;
- privacy exposure and data-practice risk;
- complexity and recurring-cost burden;
- reliability, serviceability, and safety risk;
- cancellation friction;
- claim uncertainty;
- category/form-aware synthetic reference pricing.

Each consumer then receives a product-fit and price context that influences baseline beliefs and purchase intent. Price interpretation is cadence-aware, so monthly services are not evaluated as though they were one-time physical purchases.

These coefficients and price anchors are simulator assumptions, not observed market averages.

### Social network and opinion dynamics

- Weighted K-nearest-neighbour network built from consumer similarity.
- Seeded weak ties introduce bounded cross-cluster exposure.
- Conversation scheduling is capacity-limited rather than assuming every neighbour talks every round.
- Recent edge/topic history reduces repetitive conversations without permanently blocking important topics.
- All conversations in a round read the same start-of-round snapshot.
- Evidence is aggregated first, then one synchronous state update is committed.
- Influence dynamics use explicit caps, saturation, bounded noise, trust/relationship information, and disagreement signals.
- Social-dynamics diagnostics can measure opinion movement, dispersion, contact gaps, and weak-tie participation without changing the simulation itself.

### Conversation language

ModelCouncil separates **semantic state** from **visible wording**.

Python decides the conversation pair, topic, stance, argument strength, confidence, price interpretation, and resulting numerical effects. A renderer may then express that fixed interaction as natural dialogue.

Rendered provider output is checked before acceptance. Validation rejects or falls back when wording contains problems such as:

- internal simulation-state leakage;
- visible renderer/agent labels;
- demographic or occupation-based affordability assumptions;
- unsupported external product/market facts;
- strong wording that contradicts the Python-owned semantic direction.

If rendering fails or violates the contract, the deterministic transcript remains available and the run continues.

### Dialogue modes

| Mode | Behaviour |
|---|---|
| `Economy` | Deterministic simulation with a small importance-selected set eligible for live DeepSeek wording when live rendering is enabled. |
| `Balanced` | Deterministic simulation with broader selective DeepSeek rendering when enabled. |
| `Full` | Deterministic simulation with the broadest bounded selective DeepSeek rendering, still subject to the configured per-run live-request ceiling. |
| `Full Live` | Separate confirmed asynchronous job that attempts **every conversation already scheduled by the simulator** through the selected DeepSeek or Ollama model, using bounded provider concurrency. |

Ordinary Economy/Balanced/Full runs remain usable without a live API key and fall back to deterministic wording.

`Full Live` does not create extra social interactions. It renders the exact conversations the scheduler produced. There is no hidden total LLM-call cap inside Full Live, but the simulation request itself is still protected by the global workload limit and the UI requires explicit confirmation.

### DeepSeek and Ollama Local

The backend exposes a provider catalog through `GET /api/v1/llm/providers`.

- **DeepSeek** uses the configured cloud API key/model and reports token, cache, latency, fallback, and estimated-cost telemetry.
- **Ollama Local** discovers models from the backend machine's Ollama service and uses local compute. ModelCouncil does not install, start, pull, update, or delete Ollama models.
- The browser never receives the DeepSeek API key and never connects directly to Ollama.
- Provider concurrency is bounded independently for cloud and local execution.

Full Live jobs currently live in FastAPI process memory. Restarting the backend clears their job records.

### Advanced simulation controls

The standard Small/Standard/Large presets remain the default execution path. An optional Advanced mode uses the chosen preset as a template and allows run-local overrides for:

- population size;
- K-neighbour count;
- maximum conversations per agent per round;
- conversation initiator rate;
- weak-tie rate;
- simulated minutes per round;
- rounds;
- seed.

Backend validation is authoritative.

```text
Population                  2 .. 5,000
K                           1 .. 128 and < population
Max chats / agent / round   1 .. 8
Initiator rate              0 .. 100%
Weak-tie rate               0 .. 100%
Minutes / round             1 .. 1,440
Rounds                      1 .. 100
Conversation upper bound    <= 100,000
```

When Advanced mode is off, preset-specific synchronous round limits remain enforced.

## Population presets

| Preset | Population | Base K | Initiator rate | Max chats / agent / round | Weak ties | Max web rounds |
|---|---:|---:|---:|---:|---:|---:|
| Small | 250 | 10 | 20% | 2 | 5% | 100 |
| Standard | 1,000 | 14 | 20% | 2 | 5% | 50 |
| Large | 5,000 | 18 | 20% | 2 | 5% | 20 |

Default simulated round duration is five minutes.

## Results and analytics

The current Results command center includes:

- run summary and final aggregate metrics;
- opinion/purchase timeline;
- network replay with active-conversation edges;
- selected conversation replay with source/importance metadata;
- dialogue/provider telemetry;
- six dashboard views:
  1. final sentiment composition;
  2. purchase-intent distribution;
  3. opinion and purchase trend;
  4. conversation volume by round;
  5. signed topic conversation pressure;
  6. influence-vs-purchase scatter.

The replay/network payload is deliberately bounded so a 5,000-consumer run does not require rendering every graph node and edge in the browser.

## Run-audit tracing

Actual simulation runs create local audit artifacts under:

```text
logs/model-runs/
```

The canonical trace is append-only JSONL with a matching bounded Markdown summary. Depending on the run, events cover product interpretation, workbook provenance, population generation, graph formation, scheduling, semantic messages, evidence aggregation, state commits, purchase-intent math, language-render requests/responses, validation/fallbacks, provider telemetry, and terminal status.

Audit logging is intended to be observational: enabling it must not change seeded numerical results or provider request payloads. Credentials and authorization secrets are not intentionally persisted. Run logs can still contain confidential product pitches and detailed synthetic-agent state, so `logs/` is excluded from Git and should be treated as local sensitive debugging data.

## Repository structure

```text
frontend/          Next.js 16 + React 19 browser UI
backend/           FastAPI API, schemas, configuration, orchestration
simulation/        Framework-independent simulation/domain engine
data/traits/       Canonical trait source, manifest, generated Excel workbooks
tests/             Backend and simulation regression/contract tests
docs/decisions/    Architecture decision records
scripts/           Bootstrap, verification, trait generation, smoke utilities
docker/            Frontend/backend container definitions
```

The main architectural boundary is intentional: `simulation/` does not depend on FastAPI or browser code, frontend code never owns server secrets, and LLM providers do not own consumer state.

## Trait workbooks

`data/traits/` contains the editable generated workbooks used by population construction:

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

`catalog.source.json` is the versioned canonical seed definition. `catalog.manifest.json` stores each generated workbook's SHA-256 and byte size, and tests detect missing or modified generated workbooks.

Regenerate them with:

```powershell
python scripts\generate_trait_workbooks.py
```

## API surface

The current API is mounted under `/api/v1`.

```text
GET  /api/v1/health
GET  /api/v1/llm/providers

POST /api/v1/simulations/preview
POST /api/v1/simulations/run

POST /api/v1/simulations/full-live
GET  /api/v1/simulations/full-live/{job_id}
GET  /api/v1/simulations/full-live/{job_id}/result
POST /api/v1/simulations/full-live/{job_id}/cancel
```

FastAPI's local interactive documentation is available at `http://127.0.0.1:8000/docs` while the backend is running.

## Prerequisites

- Python 3.12+
- Node.js 20.9+
- npm
- Windows PowerShell for the included helper scripts

On Windows, use `npm.cmd` if the PowerShell `npm.ps1` shim is blocked by execution policy.

## Local setup

From the repository root:

```powershell
.\scripts\bootstrap.ps1
```

This creates `.venv`, installs `backend/requirements.txt`, and installs frontend packages.

For the normal local development launcher:

```powershell
.\start-dev.ps1
```

It starts:

```text
Frontend       http://localhost:3000
Simulation     http://localhost:3000/simulate
Backend        http://127.0.0.1:8000
FastAPI docs   http://127.0.0.1:8000/docs
```

You can also start both sides manually.

### Backend

```powershell
.\.venv\Scripts\Activate.ps1
python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

### Frontend

```powershell
cd frontend
npm.cmd run dev
```

## DeepSeek configuration

Copy `.env.example` to a local root `.env` and add the real credential there:

```text
DEEPSEEK_API_KEY=your_key_here
DEEPSEEK_LIVE_ENABLED=true
```

Useful controls already exposed in `.env.example` include:

```text
DEEPSEEK_MODEL
DEEPSEEK_THINKING
DEEPSEEK_RENDER_CONCURRENCY
DEEPSEEK_FULL_LIVE_CONCURRENCY
DEEPSEEK_MAX_LIVE_REQUESTS_PER_RUN
DEEPSEEK_CACHE_PRIME_REQUESTS
```

The project-root `.env` is local-only. Never place provider credentials in frontend environment files, source code, screenshots, fixtures, or documentation.

A bounded DeepSeek connectivity/cache smoke utility is available:

```powershell
.\.venv\Scripts\python.exe scripts\deepseek_smoke.py --calls 3
```

The smoke script refuses more than 10 calls and does not print the API key.

## Ollama Local configuration

Default local settings are defined in `.env.example`:

```text
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_DISCOVERY_TIMEOUT_SECONDS=2
OLLAMA_REQUEST_TIMEOUT_SECONDS=120
OLLAMA_NUM_CTX=2048
OLLAMA_FULL_LIVE_CONCURRENCY=1
```

Start and manage Ollama separately, then use **Refresh providers** in the Full Live selector. Only models reported by the backend's local Ollama discovery are selectable.

## Verification

Run the repository checks with:

```powershell
.\scripts\check.ps1
```

The script runs the Python test suite and, when frontend dependencies are installed, frontend lint and production build checks.

Individual commands are also available:

```powershell
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider tests -q
cd frontend
npm.cmd run lint
npm.cmd run build
```

## Reproducibility and safety boundaries

- The same input, seed, trait data, and configuration are intended to produce the same numerical simulation result.
- LLM wording is downstream of semantic computation and cannot author numerical consumer state.
- Provider failures and semantic-language validation failures fall back instead of corrupting the run.
- Web and Advanced modes enforce hard workload limits.
- Full Live requires explicit confirmation because cloud execution can create API cost and Ollama can consume significant local compute.
- Real secrets, local runtime logs, generated caches, and local development-tool metadata are excluded from source control.

## Current limitations

- Consumer coefficients, semantic lexicons, compatibility rules, and price anchors are synthetic assumptions rather than empirically fitted market parameters.
- Full Live job state is in-process and not durable across backend restarts.
- Persistence, user authentication, saved projects, and durable job workers are not implemented yet.
- Multimodal image/document ingestion is not part of the current normalized product-input path.
- Results should be interpreted as controlled synthetic experiments, not predicted sales or real-population survey statistics.

## Deployment direction

The intended deployment boundary remains:

```text
GitHub
  |- Vercel / equivalent        -> Next.js frontend
  |- container host             -> FastAPI backend
  `- PostgreSQL / Supabase      -> later persistence/authentication
```

The simulation package remains independent from deployment infrastructure so it can be tested, profiled, and reproduced without the web stack.
