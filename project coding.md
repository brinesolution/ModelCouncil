# ModelCouncil — Project Coding Map and File Responsibilities

**Project root:** `E:\model counsel`  
**Current phase:** Web-first initialization  
**Purpose:** This document explains how the codebase is divided, what every important file owns, how data flows through the system, and where future functionality should be added.

---

# 1. Architectural Rule

ModelCouncil is a distributed monorepo, not a single notebook or single Python application file.

The primary boundaries are:

```text
frontend/       browser/UI only
backend/        HTTP/API/application boundary
simulation/     framework-independent domain/simulation engine
data/           trait inputs + generated local artifacts
tests/          executable behavioural contracts
docs/           architecture/decisions/plans
```

The simulation package must not import FastAPI or Next.js.

The frontend must never directly import Python simulation code or hold server secrets.

The backend acts as the orchestration boundary between web requests, simulation services, future persistence, and external LLM providers.

---

# 2. Current Project Tree

```text
model counsel/
│
├── .env
├── .env.example
├── .gitignore
├── README.md
├── context.md
├── idea.md
├── project coding.md
│
├── frontend/
│   ├── .env.example
│   ├── package.json
│   ├── tsconfig.json
│   ├── next.config.ts
│   ├── next-env.d.ts
│   ├── eslint.config.mjs
│   │
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── globals.css
│   │   ├── page.tsx
│   │   └── simulate/
│   │       └── page.tsx
│   │
│   ├── components/
│   │   └── product-pitch-form.tsx
│   │
│   ├── lib/
│   │   └── api.ts
│   │
│   └── types/
│       └── simulation.ts
│
├── backend/
│   ├── requirements.txt
│   └── app/
│       ├── __init__.py
│       ├── main.py
│       │
│       ├── core/
│       │   └── config.py
│       │
│       ├── api/
│       │   ├── router.py
│       │   └── routes/
│       │       ├── health.py
│       │       └── simulations.py
│       │
│       ├── schemas/
│       │   └── simulation.py
│       │
│       └── services/
│           └── simulation_service.py
│
├── simulation/
│   ├── __init__.py
│   │
│   ├── config/
│   │   └── presets.py
│   │
│   ├── domain/
│   │   ├── agent.py
│   │   └── product.py
│   │
│   ├── population/
│   │   └── generator.py
│   │
│   ├── network/
│   │   └── knn_graph.py
│   │
│   ├── conversation/
│   │   ├── models.py
│   │   └── scheduler.py
│   │
│   ├── opinion/
│   │   └── aggregator.py
│   │
│   ├── behaviour/
│   │   └── purchase.py
│   │
│   └── llm/
│       ├── base.py
│       ├── deepseek.py
│       └── mock.py
│
├── data/
│   ├── traits/
│   │   └── README.md
│   └── generated/
│       └── .gitkeep
│
├── scripts/
│   ├── bootstrap.ps1
│   └── check.ps1
│
├── tests/
│   ├── backend/
│   │   └── test_api.py
│   └── simulation/
│       ├── test_presets.py
│       ├── test_population.py
│       ├── test_network_scheduler.py
│       └── test_opinion_aggregation.py
│
└── docs/
    ├── architecture/
    ├── decisions/
    └── superpowers/
        ├── specs/
        └── plans/
```

Additional files/directories listed in later sections are planned next-phase additions, not hidden current implementation.

---

# 3. Root Files

## `.env`

Local secret/runtime configuration.

Contains:

- DeepSeek API key;
- DeepSeek endpoint/model;
- API host/port;
- frontend CORS origin;
- later database URL.

**Rules:**

- never commit;
- never expose to frontend;
- never put API key inside screenshots/docs/source;
- backend reads it from the project root.

## `.env.example`

Safe committed template documenting required variables without real secrets.

## `.gitignore`

Protects:

- `.env` secrets;
- virtual environments;
- Python caches;
- Node modules;
- Next.js builds;
- generated runtime artifacts;
- IDE/OS files.

## `README.md`

Human entry point containing:

- project summary;
- architecture summary;
- local setup commands;
- web/backend launch commands;
- secret location;
- current stage.

## `context.md`

Compact architecture contract for Codex/AI development sessions.

Read before architecture changes.

## `idea.md`

Long-form product idea and chronological evolution from initial AI population analytics through consumer modelling, KNN, visible conversations, web-first architecture, and planned future phases.

## `project coding.md`

This file. It is the code-navigation map.

---

# 4. Frontend

The frontend uses **Next.js App Router + TypeScript**.

It is responsible for:

- user interaction;
- input forms;
- simulation configuration;
- later graph rendering;
- charts;
- conversation transcript UI;
- timeline/replay;
- project/experiment screens later.

It is **not** responsible for simulation math.

---

## `frontend/package.json`

Defines:

- Next.js;
- React;
- TypeScript;
- ESLint;
- run/build scripts.

Current commands:

```text
npm.cmd run dev
npm.cmd run build
npm.cmd run start
npm.cmd run lint
```

On the current Windows machine use `npm.cmd` because PowerShell blocks the unsigned `npm.ps1` shim.

---

## `frontend/app/layout.tsx`

Global website shell.

Owns:

- metadata;
- global CSS import;
- top navigation;
- main page wrapper.

Do not place simulation logic here.

---

## `frontend/app/globals.css`

Initialization design tokens and global UI styles.

Current style is deliberately simple/neutral and is not yet the final product design system.

Later this can be replaced/refined after dedicated UI design review.

---

## `frontend/app/page.tsx`

Home/landing application entry.

Current purpose:

- state what ModelCouncil does;
- explain structured population/social conversation/auditable dynamics;
- link to `/simulate`;
- link to API documentation.

It is not intended to become a marketing-heavy homepage that hides the actual tool.

---

## `frontend/app/simulate/page.tsx`

First web workflow page.

Currently renders the product-pitch configuration component.

Later this route may become a multi-step simulation wizard:

```text
Product
 -> Population
 -> Social model
 -> Dialogue
 -> Events
 -> Review
 -> Run
```

Avoid putting all wizard state directly into the page when it grows; use feature-specific components/state.

---

## `frontend/components/product-pitch-form.tsx`

Client-side interactive form.

Current inputs:

- product name;
- category;
- price;
- pitch;
- population mode;
- dialogue mode;
- rounds;
- seed.

Calls `previewSimulation()` from `frontend/lib/api.ts`.

Displays returned preset values.

Current endpoint spends no LLM credits.

Later this form should split into smaller feature components when new population/events/media options are added.

---

## `frontend/lib/api.ts`

Browser API client.

Current responsibility:

```text
SimulationPreviewRequest
 -> POST FastAPI
 -> typed SimulationPreviewResponse
```

All browser calls to backend should eventually be centralized in API-client modules instead of raw `fetch()` calls scattered through components.

---

## `frontend/types/simulation.ts`

Frontend TypeScript contracts matching API request/response shapes.

Later consider generated OpenAPI TypeScript clients if API surface becomes large. Do not introduce generation prematurely.

---

# 5. Backend

FastAPI is the server/application boundary.

Responsibilities:

- HTTP validation;
- authentication later;
- user ownership later;
- request-to-domain conversion;
- simulation job orchestration;
- LLM provider creation;
- persistence later;
- file ingestion later;
- result serialization.

FastAPI routes should remain thin.

Business/simulation logic belongs outside route handlers.

---

## `backend/requirements.txt`

Python dependencies for API and simulation development.

Current groups:

### API/config

- FastAPI;
- Uvicorn;
- Pydantic;
- pydantic-settings;
- httpx.

### Data/simulation

- pandas;
- openpyxl;
- NumPy;
- scikit-learn;
- NetworkX.

### Tests

- pytest;
- pytest-asyncio.

Later dependencies should be added only when required.

---

## `backend/app/main.py`

FastAPI application factory/current application entry.

Owns:

- app metadata;
- CORS middleware;
- root endpoint;
- API router inclusion.

Do not add simulation calculations here.

Run from project root:

```powershell
python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

---

## `backend/app/core/config.py`

Authoritative runtime settings loader.

Important implementation detail:

```text
PROJECT_ROOT = Path(__file__).resolve().parents[3]
```

This ensures the backend loads the root `.env` rather than requiring a duplicate secret file under `backend/`.

Current settings:

- environment;
- log level;
- DeepSeek key/base URL/model/thinking mode;
- API host/port;
- web origin.

Later add database/storage settings here, keeping secrets server-side.

---

## `backend/app/api/router.py`

Combines route modules under:

```text
/api/v1
```

Versioning the API now avoids painful route changes later.

---

## `backend/app/api/routes/health.py`

Simple health endpoint:

```text
GET /api/v1/health
```

Used for local/deployment checks.

---

## `backend/app/api/routes/simulations.py`

Current simulation API routes.

Initialization route:

```text
POST /api/v1/simulations/preview
```

The route validates input and delegates to `simulation_service`.

Planned additions:

```text
POST /api/v1/simulations
GET  /api/v1/simulations/{id}
GET  /api/v1/simulations/{id}/results
GET  /api/v1/simulations/{id}/network
GET  /api/v1/simulations/{id}/timeline
GET  /api/v1/simulations/{id}/conversations
```

Do not add these until the underlying domain service exists.

---

## `backend/app/schemas/simulation.py`

Pydantic HTTP contracts.

Current enums:

```text
PopulationMode
DialogueMode
```

Current request:

```text
SimulationPreviewRequest
```

Current response:

```text
SimulationPreviewResponse
```

Pydantic models at this layer represent API contracts, not necessarily complete internal domain models.

---

## `backend/app/services/simulation_service.py`

Application service between route handlers and simulation package.

Current task:

- resolve population preset;
- return initialization preview.

Later it should call a simulation orchestrator/job service rather than accumulating the full simulation engine inside itself.

---

# 6. Simulation Package

`simulation/` is the most important architectural boundary.

It owns consumer behaviour, social graph, conversations, state transitions, analytics, and LLM domain interfaces.

It must remain usable from:

- API;
- tests;
- scripts;
- future research notebooks;
- benchmarks.

---

# 7. Simulation Configuration

## `simulation/config/presets.py`

Defines user-facing population presets.

Current values:

```text
small:
    population = 250
    K = 10

standard:
    population = 1000
    K = 14

large:
    population = 5000
    K = 18
```

All currently use:

```text
max normal conversations / agent / round = 2
potential conversation initiators / round = 0.20
weak tie rate = 0.05
simulated minutes / round = 5
```

These are explicit model assumptions and may later move into versioned experiment configuration.

---

# 8. Domain Models

## `simulation/domain/agent.py`

Current core classes:

### `AgentTraits`

Stable-ish normalized behavioural traits.

Current fields:

- sociability;
- price sensitivity;
- technology adoption;
- emotionality;
- logicality;
- stubbornness;
- influence power;
- product need;
- risk tolerance;
- brand loyalty.

The trait set is intentionally smaller than the full idea. Excel-backed development will expand it carefully.

### `ProductBeliefs`

Current topic-specific opinion dimensions:

- price;
- usefulness;
- quality;
- trust;
- novelty;
- privacy.

Range:

```text
-1 .. +1
```

### `AgentState`

Dynamic state:

- beliefs;
- overall opinion;
- confidence;
- knowledge;
- purchase intent;
- product salience.

### `ConsumerAgent`

Top-level agent record combining ID, demographics, traits, state, and language/locale.

Future additions should prefer nested coherent structures over continuously adding 100 fields to `ConsumerAgent`.

---

## `simulation/domain/product.py`

Framework-independent product model.

Current fields:

- name;
- pitch;
- category;
- price;
- currency;
- features.

Later this will likely be replaced/extended by a normalized `ProductKnowledge` structure after multimodal/document ingestion is designed.

---

# 9. Population

## `simulation/population/generator.py`

Bootstrap deterministic population generator.

Current purpose:

- make domain contracts executable before real Excel trait data exists;
- create reproducible agents;
- include some basic correlations;
- support KNN/scheduler/opinion tests.

Examples already modeled:

- age/occupation have some effect on income;
- income affects price sensitivity;
- age loosely affects technology adoption;
- emotionality loosely affects logicality;
- sociability influences influence power.

**This file is not the final population science.**

Planned replacement architecture:

```text
ExcelTraitRepository
    ↓
validated distributions
    ↓
PopulationGenerator
    ↓
ConsumerAgent contracts
```

The rest of the simulator should not need to care whether traits came from hard-coded bootstrap distributions, Excel, database, or empirical calibration.

---

# 10. KNN Social Graph

## `simulation/network/knn_graph.py`

Builds the candidate social graph.

Current steps:

1. convert each agent to weighted numerical vector;
2. use square-rooted feature weights before Euclidean KNN so weights affect squared distance correctly;
3. cap K at `N-1`;
4. build NetworkX undirected graph;
5. convert distance to similarity using `exp(-distance)`;
6. initialize relationship/trust;
7. add a small number of weak/random ties.

Current feature weights are initial assumptions and should later become product-category/configuration data.

Important:

**Graph edge != conversation.**

It only means the pair is an eligible social connection.

---

# 11. Conversation Models

## `simulation/conversation/models.py`

Contains transport/domain records for conversation execution.

### `ConversationPair`

Scheduled pair with:

- conversation ID;
- round;
- agent IDs;
- edge score.

### `SemanticMessage`

Machine-readable interaction payload:

- speaker/listener IDs;
- topic effects;
- argument strength;
- confidence;
- optional visible text;
- claims.

### `ConversationResult`

Groups semantic messages and visible transcript.

Future factual-claim verification can attach additional claim metadata rather than hiding it inside plain text.

---

# 12. Conversation Scheduler

## `simulation/conversation/scheduler.py`

Solves "who actually talks this round?"

This is separate from KNN.

The scheduler first selects a seeded weighted subset of potential initiators. The current default is 20% of the population per round, weighted by sociability and product salience. Non-initiators can still receive conversations.

Eligible neighbour scores use:

- similarity;
- relationship strength;
- product salience;
- sociability;
- seeded jitter.

Rules:

- cooldown blocks very recent same-pair repetition;
- weighted neighbour choice avoids always picking the absolute nearest neighbour;
- one initiation attempt is made per selected initiator in the current implementation;
- recipients and initiators share the same per-round capacity limit;
- conversation IDs include round and agent IDs;
- no ordinary agent exceeds max conversations per round.

Later enhancements:

- topic relevance;
- availability/activity schedules;
- conversation continuation;
- relationship type;
- event salience;
- dynamic individual conversation capacity.

---

# 13. Opinion Aggregation

## `simulation/opinion/aggregator.py`

This file owns one of the most important correctness rules.

### `TopicEvidence`

Represents one piece of incoming evidence:

- topic;
- stance;
- argument strength;
- trust;
- relationship;
- similarity;
- speaker confidence;
- speaker knowledge;
- novelty.

### `aggregate_round_evidence()`

Combines all evidence for an agent against one start-of-round belief state.

Current mechanics:

- group by topic;
- compute credibility;
- compute listener receptivity;
- bounded-confidence factor;
- weighted stance target;
- saturating social pressure;
- max per-topic change;
- small seeded noise;
- confidence shift from agreement/disagreement.

This prevents sequential last-speaker bias.

`aggregate_round_evidence()` now behaves as a pure aggregation step: it reads the supplied start-of-round agent state and returns an immutable `RoundAggregation` containing `belief_updates` and `confidence_delta` without mutating the input agent. When the full round engine is connected, this result should be promoted into a broader `AgentStateDelta` covering knowledge/trust/memory and committed through one explicit end-of-round state boundary.

---

# 14. Purchase Behaviour

## `simulation/behaviour/purchase.py`

Owns:

- overall opinion derivation;
- purchase-intent derivation.

Current implementation is an initial baseline formula, not a calibrated model.

Important domain rule:

```text
purchase_intent != overall_opinion
```

A consumer can like the product but not buy because of price/need/risk.

Later purchase models may become configurable and segment/category-specific, but should remain interpretable before introducing complex ML.

---

# 15. LLM Provider Layer

## `simulation/llm/base.py`

Defines the generic provider protocol:

```text
generate_json(system_prompt, user_prompt, max_tokens)
```

All LLM-backed components should depend on this interface.

---

## `simulation/llm/deepseek.py`

Server-side DeepSeek provider.

Current behavior:

- requires API key;
- calls `/chat/completions`;
- model configurable via `.env`;
- JSON response mode;
- non-thinking mode by default;
- parses returned content;
- rejects invalid structured output.

This file should eventually gain:

- retry policy for transient failures;
- rate/concurrency control;
- request IDs/logging without sensitive content;
- batch conversation calls;
- validated Pydantic schemas;
- cache integration.

Do not let provider errors terminate an entire simulation; the future conversation router needs mathematical fallback.

---

## `simulation/llm/mock.py`

Offline deterministic provider.

Use for:

- tests;
- CI;
- development without credit spend;
- deterministic replay;
- frontend/API development before live LLM integration.

Never remove the mock provider just because DeepSeek works.

---

# 16. Data Directory

## `data/traits/`

Future Excel trait knowledge base.

See `data/traits/README.md` for workbook/sheet contracts.

Planned workbooks include demographics, occupations, income, personality, emotions, social behaviour, technology, archetypes, and compatibility rules.

## `data/generated/`

Local generated simulation artifacts.

Ignored by Git except `.gitkeep`.

Possible development artifacts later:

- population snapshots;
- graph snapshots;
- debug ledgers;
- benchmark results.

Production persistence should use proper storage/database rather than treating this directory as a production database.

---

# 17. Tests

Tests are not optional because agent simulations can produce attractive but logically incorrect output.

## `tests/simulation/test_presets.py`

Locks the standard population/K/conversation specification.

## `tests/simulation/test_population.py`

Checks:

- same seed reproducibility;
- age bounds;
- normalized income;
- normalized traits.

## `tests/simulation/test_network_scheduler.py`

Checks:

- graph contains all agents;
- graph has social edges;
- no pair is repeated in a round;
- no consumer exceeds conversation capacity.

## `tests/simulation/test_opinion_aggregation.py`

Checks the major synchronous-update invariant:

- reversing conversation/evidence order should not change the aggregated result.

## `tests/backend/test_api.py`

Checks:

- health endpoint;
- standard simulation preview API contract.

---

# 18. Planned Next Simulation Files

These are planned additions for the next implementation round.

```text
simulation/
├── population/
│   ├── trait_repository.py
│   ├── excel_repository.py
│   ├── distributions.py
│   ├── correlations.py
│   └── validator.py
│
├── product/
│   ├── knowledge.py
│   ├── baseline_evaluation.py
│   └── fact_registry.py
│
├── conversation/
│   ├── router.py
│   ├── background_engine.py
│   ├── language_engine.py
│   ├── prompt_builder.py
│   ├── claim_validator.py
│   └── transcript.py
│
├── opinion/
│   ├── delta.py
│   ├── social_proof.py
│   └── confidence.py
│
├── memory/
│   ├── models.py
│   ├── store.py
│   └── summarizer.py
│
├── analytics/
│   ├── summary.py
│   ├── segments.py
│   ├── timeline.py
│   └── network_metrics.py
│
├── events/
│   ├── models.py
│   └── engine.py
│
└── engine.py
```

Do not create all files empty. Add them with a concrete implementation task.

---

# 19. Planned Backend Files

When real run persistence begins:

```text
backend/app/
├── api/routes/
│   ├── products.py
│   ├── simulations.py
│   ├── conversations.py
│   └── uploads.py
│
├── services/
│   ├── product_service.py
│   ├── simulation_service.py
│   ├── result_service.py
│   └── ingestion_service.py
│
├── persistence/
│   ├── repositories.py
│   └── models.py
│
└── workers/
    └── simulation_worker.py
```

Background queues should only be introduced when synchronous execution becomes a demonstrated bottleneck.

---

# 20. Planned Frontend Feature Structure

As the UI grows, avoid one giant `components/` directory.

Preferred direction:

```text
frontend/features/
├── experiment-builder/
├── population/
├── network-map/
├── conversations/
├── analytics/
├── replay/
└── product-ingestion/
```

Possible future pages:

```text
/dashboard
/projects/[id]
/products/[id]
/simulations/[id]
/simulations/[id]/replay
```

---

# 21. Planned Web Graph

Recommended library decision can be made during the visualization phase. Likely candidates are Cytoscape.js or a D3-based implementation.

Do not bind simulation graph objects directly to rendering-library objects.

Backend should return a neutral graph DTO:

```text
nodes[]
edges[]
active_conversations[]
round
```

Frontend transforms DTO into renderer-specific format.

---

# 22. Planned Conversation UI

Each visible conversation should eventually provide:

```text
conversation_id
round
agent A
agent B
messages
semantic topics
before states
after states
influence contributions
```

The map can animate only active edges while preserving a history inspector.

Large simulations should not display every graph edge at once.

---

# 23. Planned Input Ingestion

Text-only is current.

Later media flow:

```text
browser upload
  ↓
backend validation
  ↓
file storage
  ↓
extract text/image/product facts
  ↓
normalized ProductKnowledge
  ↓
user review
  ↓
simulation
```

Expected later inputs:

- product images;
- screenshots;
- PDFs;
- DOCX;
- marketing documents.

Raw files should never be passed blindly into every agent conversation.

---

# 24. Database/Persistence Direction

Planned later storage: PostgreSQL/Supabase.

Potential entities:

```text
users
projects
products
product_assets
product_knowledge
population_configs
populations
experiments
simulation_runs
simulation_checkpoints
agents
network_edges
conversations
events
analytics
llm_cache
```

Avoid storing every full state for every agent at every round by default. Prefer checkpoints + round aggregates, with detailed history enabled when required.

---

# 25. Security Boundary

DeepSeek key:

```text
root .env
 -> backend/server only
 -> simulation LLM provider
```

Never:

```text
root .env
 -> NEXT_PUBLIC_ variable
 -> browser
```

Future product documents may be confidential. Authentication/authorization must eventually be enforced server-side, not only hidden in UI.

---

# 26. Development Rules

1. Read `context.md`, `idea.md`, and this file before major architecture work.
2. Do not rewrite the project into a single notebook/file.
3. Keep simulation independent from web frameworks.
4. Keep routes thin.
5. Use explicit domain contracts.
6. Prefer deterministic seeded randomness.
7. Add tests for behaviour changes.
8. No magic constants without an explicit owner/configuration path.
9. No direct LLM final-state overwrite.
10. Do not silently change population/K/conversation defaults.
11. LLM output is untrusted and must be validated.
12. Preserve transcript/semantic separation.
13. Facts and opinions require different validation/update rules.
14. Prefer synchronous state commit for default rounds.
15. Avoid speculative microservices/queues/frameworks.
16. Keep real market claims out of synthetic-only analytics.

---

# 27. Verification Commands

Once dependencies are installed, run from root:

```powershell
$env:PYTHONDONTWRITEBYTECODE="1"
python -m pytest -p no:cacheprovider tests -q
```

Backend:

```powershell
python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

Frontend:

```powershell
cd frontend
npm.cmd run lint
npm.cmd run build
npm.cmd run dev
```

Manual web check:

```text
http://localhost:3000
http://localhost:3000/simulate
http://127.0.0.1:8000/docs
```

---

# 28. Initialization Acceptance Criteria

This initialization round is considered structurally successful when:

- distributed project directories exist;
- root secret handling exists;
- frontend is not coupled to DeepSeek secret;
- FastAPI has health/preview API;
- web form calls API;
- simulation has explicit domain models;
- population presets exist;
- deterministic bootstrap population exists;
- KNN network exists;
- conversation scheduler exists;
- synchronous evidence aggregator exists;
- purchase intent is derived separately;
- LLM provider abstraction exists;
- DeepSeek implementation exists;
- mock provider exists;
- core regression tests exist;
- idea/context/coding documentation exists.

The initialization does **not** claim that a complete end-to-end social simulation is finished. That is Phase 1.

---

# 29. Current Next Task

The next round should convert the current skeleton into the first fully running simulation vertical slice:

```text
web pitch
 -> product domain
 -> generated/Excel-backed population
 -> baseline product beliefs
 -> KNN graph
 -> schedule conversations
 -> semantic background conversations
 -> aggregate evidence
 -> purchase update
 -> round metrics
 -> repeat N rounds
 -> API result
 -> web charts/network
```

Only after this vertical slice works should live LLM dialogue become part of the simulation loop.
