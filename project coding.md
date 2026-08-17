# ModelCouncil — Project Coding Map and File Responsibilities

**Project root after local checkout:** `E:\model counsel`  
**Repository:** `brinesolution/ModelCouncil`  
**Current branch:** `phase-1-vertical-slice`  
**Current phase:** Phase 1 web simulation vertical slice implemented; branch under final merge-safety verification.  
**Purpose:** Define the codebase boundaries, important files, execution flow, and where future features belong.

---

# 1. Architectural boundary

ModelCouncil is a distributed monorepo.

```text
frontend/       Next.js browser UI
backend/        FastAPI HTTP/application boundary
simulation/     framework-independent simulation/domain engine
data/           trait inputs + generated local data
tests/          executable behavioral and API contracts
docs/           architecture, decisions, plans, phase records
scripts/        developer/build/data-generation utilities
```

Hard rules:

- `simulation/` must not import FastAPI or browser code.
- `frontend/` must never contain DeepSeek/server secrets.
- Backend routes stay thin; orchestration goes into backend services.
- LLM providers do not own agent state.
- Round state changes remain synchronous unless a future ADR explicitly changes that model.

---

# 2. Current repository tree

```text
model counsel/
│
├── .env.example
├── .gitignore
├── README.md
├── context.md
├── idea.md
├── project coding.md
├── docker-compose.yml
│
├── .github/
│   └── workflows/
│       └── ci.yml
│
├── frontend/
│   ├── .env.example
│   ├── package.json
│   ├── package-lock.json
│   ├── tsconfig.json
│   ├── next.config.ts
│   ├── eslint.config.mjs
│   │
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── globals.css
│   │   ├── results.css
│   │   ├── page.tsx
│   │   ├── simulate/
│   │   │   └── page.tsx
│   │   └── simulations/
│   │       └── result/
│   │           └── page.tsx
│   │
│   ├── components/
│   │   └── product-pitch-form.tsx
│   │
│   ├── features/
│   │   └── simulation/
│   │       ├── results-summary.tsx
│   │       ├── opinion-timeline.tsx
│   │       └── network-preview.tsx
│   │
│   ├── lib/
│   │   └── api.ts
│   │
│   └── types/
│       ├── simulation.ts
│       └── results.ts
│
├── backend/
│   ├── requirements.txt
│   └── app/
│       ├── main.py
│       ├── core/
│       │   └── config.py
│       ├── api/
│       │   ├── router.py
│       │   └── routes/
│       │       ├── health.py
│       │       └── simulations.py
│       ├── schemas/
│       │   └── simulation.py
│       └── services/
│           └── simulation_service.py
│
├── simulation/
│   ├── engine.py
│   ├── config/
│   │   └── presets.py
│   ├── domain/
│   │   ├── agent.py
│   │   └── product.py
│   ├── population/
│   │   ├── trait_repository.py
│   │   ├── excel_repository.py
│   │   ├── validator.py
│   │   ├── correlations.py
│   │   └── generator.py
│   ├── product/
│   │   ├── knowledge.py
│   │   └── baseline_evaluation.py
│   ├── network/
│   │   └── knn_graph.py
│   ├── conversation/
│   │   ├── models.py
│   │   ├── scheduler.py
│   │   ├── background_engine.py
│   │   └── router.py
│   ├── opinion/
│   │   ├── aggregator.py
│   │   └── delta.py
│   ├── behaviour/
│   │   └── purchase.py
│   └── llm/
│       ├── base.py
│       ├── deepseek.py
│       └── mock.py
│
├── data/
│   ├── generated/
│   └── traits/
│       ├── README.md
│       ├── catalog.source.json
│       ├── catalog.manifest.json
│       ├── archetypes.xlsx
│       ├── compatibility_rules.xlsx
│       ├── consumer_behaviour.xlsx
│       ├── decision_styles.xlsx
│       ├── demographics.xlsx
│       ├── economic_traits.xlsx
│       ├── emotions.xlsx
│       ├── occupations.xlsx
│       ├── personality.xlsx
│       ├── social_behaviour.xlsx
│       └── technology.xlsx
│
├── scripts/
│   ├── bootstrap.ps1
│   ├── check.ps1
│   └── generate_trait_workbooks.py
│
├── tests/
│   ├── backend/
│   │   └── test_api.py
│   └── simulation/
│       ├── test_population.py
│       ├── test_excel_repository.py
│       ├── test_population_correlations.py
│       ├── test_trait_manifest_integrity.py
│       ├── test_baseline_evaluation.py
│       ├── test_network_scheduler.py
│       ├── test_background_conversations.py
│       ├── test_opinion_aggregation.py
│       ├── test_engine.py
│       └── test_presets.py
│
├── docker/
│   ├── backend.Dockerfile
│   └── frontend.Dockerfile
│
└── docs/
    ├── architecture/
    ├── decisions/
    └── superpowers/
```

A real `.env` exists only on the user's local machine and is ignored by Git.

---

# 3. Frontend responsibilities

## `frontend/app/page.tsx`

Landing/entry surface. It explains ModelCouncil and routes users toward the simulation flow.

## `frontend/app/simulate/page.tsx`

Simulation creation page. It hosts the product-pitch form rather than containing domain logic itself.

## `frontend/components/product-pitch-form.tsx`

Owns interactive product/simulation input fields:

- product name;
- category;
- pitch;
- price/currency;
- population mode;
- dialogue mode;
- rounds;
- seed.

It calls the typed frontend API helper and sends the run result to the result route. It should remain a form/UI component rather than calculate simulation behavior.

## `frontend/lib/api.ts`

The browser's API boundary. All calls to FastAPI belong here or in future feature-specific service modules.

Rules:

- never call DeepSeek directly from the browser;
- never read `DEEPSEEK_API_KEY` here;
- surface HTTP errors in user-friendly form;
- use shared TypeScript contracts.

## `frontend/types/simulation.ts`

Input/preview contracts shared by UI code.

## `frontend/types/results.ts`

Typed representation of the Phase 1 run response: timeline, summary, network sample, conversations, presets, etc.

## `frontend/app/simulations/result/page.tsx`

Assembles the browser-visible result screen from the returned simulation data.

## `frontend/features/simulation/results-summary.tsx`

Displays high-level run metrics. Do not invent metrics that the backend did not return.

## `frontend/features/simulation/opinion-timeline.tsx`

Code-native timeline visualization. It intentionally avoids an unnecessary chart dependency in Phase 1.

## `frontend/features/simulation/network-preview.tsx`

Bounded graph/network preview. It does **not** attempt to render every node/edge for a 5,000-agent population.

Future Phase 2 work should replace/extend this with an interactive active-conversation map and replay controls.

---

# 4. Backend responsibilities

## `backend/app/main.py`

FastAPI application creation, CORS middleware, root endpoint, API router mounting.

No simulation formulas belong here.

## `backend/app/core/config.py`

Loads server-only root `.env` configuration with Pydantic settings.

Current DeepSeek configuration:

```text
DEEPSEEK_API_KEY
DEEPSEEK_BASE_URL
DEEPSEEK_MODEL
DEEPSEEK_THINKING
```

Secrets must never be serialized back to the frontend.

## `backend/app/api/router.py`

Central API router composition.

## `backend/app/api/routes/health.py`

Health endpoint.

## `backend/app/api/routes/simulations.py`

HTTP route definitions for preview/run. Keep request handling thin; delegate real work to `simulation_service.py`.

## `backend/app/schemas/simulation.py`

Pydantic input/output contracts.

Important Phase 1 safety rule implemented here:

```text
Small web runs      ≤ 100 rounds
Standard web runs   ≤ 50 rounds
Large web runs      ≤ 20 rounds
```

These protect the current synchronous endpoint from pathological workloads. A future async job queue can support larger experiments without removing these synchronous safeguards.

## `backend/app/services/simulation_service.py`

Application orchestration boundary:

1. choose population preset;
2. resolve Excel trait repository;
3. generate population;
4. build ProductKnowledge;
5. configure/run SimulationEngine;
6. serialize domain result into API DTOs;
7. expose whether traits came from `excel` or bootstrap fallback.

This file may coordinate domain components but should not become a second simulation engine.

---

# 5. Core simulation responsibilities

## `simulation/config/presets.py`

Owns official Small/Standard/Large population presets.

Current presets:

```text
Small:     N=250,  K=10
Standard:  N=1000, K=14
Large:     N=5000, K=18

initiator_rate = 0.20
weak_tie_rate = 0.05
max_conversations_per_round = 2
simulated_minutes_per_round = 5
```

Do not conflate K with actual chat count.

## `simulation/domain/agent.py`

Core agent/domain dataclasses:

- `AgentTraits`
- `ProductBeliefs`
- `AgentState`
- `ConsumerAgent`
- clamp helpers

This is the authoritative representation of an individual consumer's state.

## `simulation/domain/product.py`

Core product domain object. Keep transport-specific Pydantic models out of this package.

---

# 6. Trait repository and population generation

## `simulation/population/trait_repository.py`

Abstract repository contract and typed catalog/value structures. Simulation code depends on this abstraction, not directly on pandas/Excel.

## `simulation/population/excel_repository.py`

Only module that should understand Excel/pandas loading details.

Responsibilities:

- discover `.xlsx` trait workbooks;
- read `Traits` and `Metadata` sheets;
- filter disabled rows;
- validate weights;
- normalize weights into probabilities;
- preserve category-specific extra columns in parameter dictionaries;
- validate full catalog.

## `simulation/population/validator.py`

Cross-workbook catalog validation. Invalid keys/weights/ranges/schema issues should fail early with actionable errors.

## `simulation/population/correlations.py`

Central place for population compatibility/correlation behavior. Examples include income/occupation and behavior coupling. Do not scatter such conditions throughout network or API code.

## `simulation/population/generator.py`

Seeded consumer generation.

It can use a supplied `TraitRepository` or the bootstrap fallback. The backend uses Excel when the committed trait workbooks are present.

The same seed/configuration should reproduce the deterministic population path.

---

# 7. Trait data files

## `data/traits/catalog.source.json`

Version-controlled canonical seed definition used to generate the initial Excel files. This exists so workbook creation is reproducible and recoverable.

It is not intended to replace Excel as the human-editable modeling interface permanently.

## `scripts/generate_trait_workbooks.py`

Deterministically constructs the current workbook layout from `catalog.source.json`, then regenerates `catalog.manifest.json`.

Run manually when the canonical source is changed:

```powershell
python scripts\generate_trait_workbooks.py
```

## `data/traits/catalog.manifest.json`

Integrity ledger containing generated workbook filenames, byte sizes, and SHA-256 hashes.

## `.xlsx` workbooks

Current categories cover:

- archetypes;
- compatibility rules;
- consumer behavior;
- decision styles;
- demographics;
- economic traits;
- emotions;
- occupations;
- personality;
- social behavior;
- technology/AI adoption.

Stable `key` values are machine identifiers. Labels/descriptions/weights can evolve without changing keys unnecessarily.

---

# 8. Product baseline evaluation

## `simulation/product/knowledge.py`

Normalized product input consumed by the simulation engine.

Future photo/document parsing should normalize into this product-knowledge layer instead of adding image-specific branches throughout the simulator.

## `simulation/product/baseline_evaluation.py`

Produces initial topic beliefs before social influence.

Current signals include consumer need, price sensitivity, technology adoption, risk/trust behavior, product price/category text and seeded noise.

It returns topic beliefs, not a final purchase decision.

---

# 9. Network and scheduling

## `simulation/network/knn_graph.py`

Builds the weighted KNN candidate interaction graph.

Current responsibilities:

- convert selected traits to vectors;
- calculate weighted distance/similarity;
- create K-neighbour edges;
- seed trust/relationship strength;
- introduce the configured weak-tie fraction.

K is candidate neighbourhood size only.

## `simulation/conversation/scheduler.py`

Chooses actual conversations each round.

Responsibilities:

- choose a limited set of potential initiators;
- weight them by sociability/salience;
- apply edge cooldown;
- respect per-agent capacity;
- avoid duplicate unordered pairs;
- choose partners probabilistically rather than always taking nearest neighbour.

This layer solves the “one person has multiple neighbours” problem without making every neighbour talk every round.

---

# 10. Conversation engine

## `simulation/conversation/models.py`

Typed semantic conversation/message structures.

## `simulation/conversation/background_engine.py`

Phase 1 deterministic semantic interaction generator.

It selects relevant topic beliefs and returns message/evidence semantics with seeded variation. Natural-language transcripts are not required for these background interactions.

## `simulation/conversation/router.py`

Conversation routing boundary.

Current Phase 1 behavior:

```text
use_llm=False -> background semantic engine
use_llm=True  -> intentionally not implemented yet
```

Phase 2 adds selective DeepSeek promotion here rather than embedding provider calls in the scheduler or engine.

---

# 11. Opinion and purchase updates

## `simulation/opinion/aggregator.py`

Pure round-level evidence aggregation.

Inputs:

- agent start-of-round state;
- all incoming topic evidence;
- seeded RNG.

Uses:

- trust;
- relationship strength;
- speaker influence/confidence;
- listener stubbornness/confidence;
- message relevance;
- bounded-confidence acceptance;
- saturating influence;
- small bounded noise.

Returns an aggregation/delta without mutating the start snapshot.

## `simulation/opinion/delta.py`

Explicit state-delta representation used at the synchronous commit boundary.

## `simulation/behaviour/purchase.py`

Derives overall opinion and purchase intent after topic state updates.

Purchase intent must not be copied directly from LLM sentiment or one conversation.

---

# 12. Simulation engine

## `simulation/engine.py`

Top-level framework-independent multi-round orchestrator.

Per round:

```text
freeze state
  ↓
schedule pairs
  ↓
generate semantic interactions
  ↓
produce evidence both directions
  ↓
update relationship interaction metadata
  ↓
aggregate all evidence per agent
  ↓
commit one state delta per agent
  ↓
derive overall opinion + purchase intent
  ↓
record metrics and conversation ledger
```

The engine records initial state plus every round, enabling a timeline of `rounds + 1` points.

---

# 13. LLM provider layer

## `simulation/llm/base.py`

Generic LLM abstraction.

## `simulation/llm/deepseek.py`

Server-side DeepSeek V4 Flash provider.

Responsibilities:

- bearer authentication;
- `/chat/completions` request;
- non-thinking/structured JSON configuration;
- timeout handling through `httpx`;
- JSON response validation.

Do not instantiate or call this from browser code.

## `simulation/llm/mock.py`

Deterministic provider for development/tests without API spend.

---

# 14. Testing responsibilities

## `tests/simulation/test_population.py`

Seeded population/basic trait-bound checks.

## `test_excel_repository.py`

Excel loader, normalization, disabled rows, validation errors.

## `test_population_correlations.py`

Compatibility/correlation behavior.

## `test_trait_manifest_integrity.py`

Critical trait-data safety contract:

- all manifest workbooks exist;
- no undeclared workbook exists;
- size/hash match;
- real workbook catalog loads;
- required categories exist;
- normalized probabilities sum correctly.

## `test_baseline_evaluation.py`

Baseline product-response behavior.

## `test_network_scheduler.py`

KNN/scheduling capacity and pair constraints.

## `test_background_conversations.py`

Deterministic background semantic interactions.

## `test_opinion_aggregation.py`

Synchronous/pure aggregation behavior.

## `test_engine.py`

Multi-round reproducibility and snapshot immutability.

## `tests/backend/test_api.py`

Health, preview, full run response, and safe synchronous workload budgets.

---

# 15. CI

`.github/workflows/ci.yml` is read-only and runs on push/PR.

Python job:

```text
Python 3.13
pip install -r backend/requirements.txt
pytest tests
```

Frontend job:

```text
Node 22
npm ci
npm run lint
npm run build
```

Use `npm ci` because the lockfile is committed. Do not grant the verification workflow repository write permissions.

A temporary write-enabled workbook-generation workflow was used to recover the interrupted binary-data commit and was removed afterward. It must not be reintroduced casually.

---

# 16. Local developer scripts

## `scripts/bootstrap.ps1`

Creates Python virtual environment, installs backend dependencies, and installs frontend packages.

## `scripts/check.ps1`

Runs local Python tests and frontend checks when dependencies exist.

---

# 17. Current Phase 1 output

A current run API result contains:

```text
synthetic
status
product_name
population_mode
dialogue_mode
rounds
seed
preset
summary
timeline
network
selected_conversations
trait_source
```

The frontend consumes exactly these fields.

The `network` DTO is intentionally sampled/bounded for browser rendering; the backend simulation can still contain the full internal graph.

---

# 18. Phase 2 file direction

Likely additions/changes:

```text
simulation/conversation/
├── language_engine.py
├── prompt_builder.py
├── memory_context.py
└── transcript_policy.py

simulation/llm/
├── router.py                 # provider/model/cost routing if needed
└── cache.py

frontend/features/simulation/
├── conversation-map.tsx
├── conversation-panel.tsx
├── replay-controls.tsx
└── agent-inspector.tsx

backend/app/schemas/
└── conversation/replay DTO extensions
```

Do not create these files until their behavior is defined and tested.

---

# 19. Later multimodal input direction

Product images/screenshots/documents should enter through an ingestion layer:

```text
upload
  ↓
file validation
  ↓
image/document extraction
  ↓
structured product facts + pitch text
  ↓
ProductKnowledge
  ↓
existing simulation engine
```

Do not make image-based products use a separate simulation algorithm.

---

# 20. Known current limitations

- Phase 1 does not generate live natural-language conversations during the run.
- Dialogue modes are API/UI contracts reserved for Phase 2 routing behavior.
- The web run endpoint is synchronous; heavy research workloads need a future queue/worker architecture.
- No authentication/project persistence/rate limiting yet.
- Behavioral coefficients and trait distributions are explicit synthetic assumptions, not empirically calibrated market truth.
- The network visualization is a bounded preview, not the final animated map.
- No multilingual/Hinglish/Hindi conversation layer yet.

These are phase boundaries, not reasons to bypass current safety constraints.

---

# 21. Merge/handoff rule

The project owner will manually merge `phase-1-vertical-slice` into `main` after reviewing the final safety status.

Do **not** automatically merge this branch.

After the manual merge, the owner will pull the final `main` branch into `E:\model counsel` and continue from there.
