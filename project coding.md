# ModelCouncil — Project Coding Map and File Responsibilities

**Project root after local checkout:** `E:\model counsel`  
**Repository:** `brinesolution/ModelCouncil`  
**Current branch:** local `main`; Phase 2 changes are intentionally local-only and not pushed
**Current phase:** Phase 2J reliability repair program — 2J-A semantic correctness/audit privacy is implemented first and must pass its full gate before 2J-B active population context, 2J-C social dynamics, and 2J-D conversation/provider validation. Phase 2I Advanced controls remain the fast-debug runtime layer.
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
logs/           Git-ignored local runtime run-audit traces
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
│   │       ├── result/
│   │       │   └── page.tsx
│   │       └── full-live/
│   │           └── [jobId]/
│   │               └── page.tsx
│   │
│   ├── components/
│   │   ├── product-pitch-form.tsx
│   │   ├── full-live-confirmation-dialog.tsx
│   │   └── industrial/
│   │       ├── led-status.tsx
│   │       └── panel-details.tsx
│   │
│   ├── features/
│   │   ├── home/
│   │   │   └── society-monitor.tsx
│   │   ├── analytics/
│   │   │   ├── analytics-grid.tsx
│   │   │   ├── chart-frame.tsx
│   │   │   ├── chart-utils.ts
│   │   │   ├── sentiment-donut.tsx
│   │   │   ├── purchase-bars.tsx
│   │   │   ├── trend-lines.tsx
│   │   │   ├── conversation-volume.tsx
│   │   │   ├── topic-pressure.tsx
│   │   │   └── influence-scatter.tsx
│   │   └── simulation/
│   │       ├── results-summary.tsx
│   │       ├── opinion-timeline.tsx
│   │       ├── network-preview.tsx
│   │       ├── conversation-ledger.tsx
│   │       ├── simulation-replay.tsx
│   │       └── full-live-progress.tsx
│   │
│   ├── lib/
│   │   └── api.ts
│   │
│   └── types/
│       ├── simulation.ts
│       ├── full-live.ts
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
│           ├── simulation_service.py
│           ├── full_live_jobs.py
│           └── full_live_service.py
│
├── simulation/
│   ├── engine.py
│   ├── analytics/
│   │   ├── __init__.py
│   │   └── dashboard.py
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
│   │   ├── ledger.py
│   │   ├── scheduler.py
│   │   ├── background_engine.py
│   │   ├── background_language.py
│   │   ├── importance.py
│   │   ├── dialogue_policy.py
│   │   ├── language_renderer.py
│   │   ├── render_pipeline.py
│   │   ├── full_live_renderer.py
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

Industrial landing/entry surface. It uses an asymmetric hero, the CSS/SVG Society Monitor device, bolted explanatory modules, and a dark process strip to explain the real simulation pipeline without fake proof/marketing data.

## `frontend/app/simulate/page.tsx`

Simulation creation page. It provides the industrial control-console framing/status and hosts the product-pitch form rather than containing domain logic itself.

## `frontend/components/product-pitch-form.tsx`

Owns interactive product/simulation input fields:

- product name;
- category;
- pitch;
- price/currency;
- population preset/template;
- dialogue mode;
- optional Advanced population/K/chat/rate/minutes overrides;
- rounds;
- seed.

Dialogue mode remains the primary language/rendering control. Advanced numerical controls are opt-in and derive effective values through `frontend/lib/simulation-config.ts`; invalid custom values disable Run rather than being silently clamped. It calls the typed frontend API helper and sends ordinary run results to the result route. `full_live` branches into the explicit confirmation dialog, shows the exact conservative `floor(population × max chats / 2) × rounds` upper bound from the effective configuration, requires typed `FULL LIVE` acknowledgement above 5,000 calls, starts the asynchronous job only after confirmation, and routes to the job progress page. Presentation stays separate from simulation math.

## `frontend/components/full-live-confirmation-dialog.tsx`

Industrial warning dialog for uncapped Full Live execution. It states external-model use, cost/latency risk, no hidden call cap, deterministic numerical-state protection, and the conservative upper-bound call count. Closing/Escape/cancelling starts no job.

## `frontend/components/industrial/led-status.tsx`

Reusable text-paired LED indicator. LEDs are never the only status signal; labels preserve accessibility.

## `frontend/components/industrial/panel-details.tsx`

Reusable manufacturing-detail primitive for corner screws and optional vent slots. This keeps skeuomorphic details consistent rather than copied into every panel.

## `frontend/features/home/society-monitor.tsx`

Dependency-free CSS/SVG hero device showing a stylized synthetic network and opinion trace. It is illustrative UI, not a fake live simulation metric.

## `frontend/lib/simulation-config.ts`

Pure frontend configuration helpers for Phase 2I. It mirrors the registered Small/Standard/Large numerical defaults, converts Advanced percentage inputs into backend fractions, derives effective PRESET/ADVANCED values, computes the conservative workload bound, and performs immediate browser validation. It does not authorize a run; FastAPI validation remains authoritative.

## `frontend/lib/api.ts`

The browser's API boundary. All calls to FastAPI belong here or in future feature-specific service modules. It now includes provider discovery through `GET /api/v1/llm/providers`; the browser never queries Ollama directly.

Rules:

- never call DeepSeek directly from the browser;
- never read `DEEPSEEK_API_KEY` here;
- surface HTTP errors in user-friendly form;
- use shared TypeScript contracts.

## `frontend/types/llm-provider.ts`

Typed provider catalog/model descriptors plus the validated Full Live selection shape used by the conditional source/model selector.

## `frontend/components/full-live-provider-selector.tsx`

Full-Live-only provider/model discovery UI. It fetches the backend catalog on mount, prefers an available DeepSeek model then the first available provider, supports explicit refresh, displays Ollama model size/parameter/quantization metadata, and blocks Full Live until a valid selection exists.

## `frontend/types/simulation.ts`

Input/preview contracts shared by UI code.

## `frontend/types/full-live.ts`

Typed Full Live job start/status contracts and the explicit job-state union (`queued`, `simulating`, `rendering`, `cancelling`, `cancelled`, `completed`, `failed`).

## `frontend/types/results.ts`

Typed representation of the current run response: timeline, summary, network sample, ranked conversations, dialogue-render statistics, dashboard analytics, and replay checkpoints.

## `frontend/app/simulations/full-live/[jobId]/page.tsx`

Dynamic Full Live job route. It mounts the progress console for one in-memory backend job.

## `frontend/features/simulation/full-live-progress.tsx`

Polls job status about every 1.5 seconds without overlapping requests. Shows exact/upper-bound conversations, processed/rendered/fallback counts, provider cache/token/latency/cost telemetry, local in-memory persistence warning, and best-effort cancellation. On completion it fetches the normal `SimulationRunResponse`, stores it in sessionStorage, and redirects to the standard Results page.

## `frontend/app/simulations/result/page.tsx`

Assembles the browser-visible result screen from the returned simulation data.

## `frontend/features/simulation/results-summary.tsx`

Displays high-level run metrics. Do not invent metrics that the backend did not return.

## `frontend/features/analytics/`

Dependency-free SVG analytics package for the Phase 2E.5 command center. `analytics-grid.tsx` owns the strict six-panel composition; `chart-frame.tsx` provides shared physical instrumentation framing; individual files render final sentiment, purchase-intent bins, opinion/purchase trend, conversation volume, semantic topic pressure, and influence-vs-purchase scatter.

Desktop layout is exactly 3 columns × 2 rows, falling to 2×3 on tablet and 1×6 on mobile. Do not replace these charts with fake values or duplicate API metrics.

## `frontend/features/simulation/opinion-timeline.tsx`

Legacy standalone code-native timeline visualization retained for compatibility/reference. The active Results page now uses `features/analytics/trend-lines.tsx` inside the six-chart matrix.

## `frontend/features/simulation/network-preview.tsx`

Bounded graph/network renderer. It accepts optional replay node state and active conversation edges; it still does **not** attempt to render every node/edge for a 5,000-agent population.

## `frontend/features/simulation/simulation-replay.tsx`

Client-side round slider over compact backend checkpoints. It keeps graph layout stable while changing opinion/purchase state and highlighting active conversation edges.

## `frontend/features/simulation/conversation-ledger.tsx`

Displays the highest-importance returned conversations as chat bubbles, including importance, LLM-selection status, and actual language source.

---

# 4. Backend responsibilities

## `backend/app/main.py`

FastAPI application creation, CORS middleware, root endpoint, API router mounting.

No simulation formulas belong here.

## `backend/app/core/config.py`

Loads server-only root `.env` configuration with Pydantic settings.

Current provider configuration:

```text
DEEPSEEK_API_KEY
DEEPSEEK_BASE_URL
DEEPSEEK_MODEL
DEEPSEEK_THINKING
DEEPSEEK_LIVE_ENABLED
DEEPSEEK_RENDER_CONCURRENCY
DEEPSEEK_FULL_LIVE_CONCURRENCY
DEEPSEEK_MAX_LIVE_REQUESTS_PER_RUN
DEEPSEEK_CACHE_PRIME_REQUESTS
DEEPSEEK_CACHE_HIT_USD_PER_MILLION
DEEPSEEK_CACHE_MISS_USD_PER_MILLION
DEEPSEEK_OUTPUT_USD_PER_MILLION
OLLAMA_BASE_URL
OLLAMA_DISCOVERY_TIMEOUT_SECONDS
OLLAMA_REQUEST_TIMEOUT_SECONDS
OLLAMA_NUM_CTX
OLLAMA_FULL_LIVE_CONCURRENCY
```

`.env.example` keeps `DEEPSEEK_LIVE_ENABLED=false` as the safe default. The current private local `.env` is live-enabled with a 10-request hard ceiling. `resolve_deepseek_api_key()` deliberately prefers the project-root `.env` DeepSeek key over a stale inherited Windows key while leaving normal runtime setting precedence intact.

Secrets must never be serialized back to the frontend.

## `backend/app/api/router.py`

Central API router composition.

## `backend/app/api/routes/health.py`

Health endpoint.

## `backend/app/api/routes/llm.py`

Provider catalog endpoint: `GET /api/v1/llm/providers`. It always returns known provider entries and represents unavailable Ollama/DeepSeek states as data rather than crashing discovery.

## `backend/app/api/routes/simulations.py`

HTTP route definitions for preview/ordinary run plus the Full Live lifecycle. `dialogue_mode=full_live` is rejected by `/simulations/run` and must use start/status/result/cancel job endpoints. Full Live start/status now carries the validated `llm_provider` and `llm_model`. Keep request handling thin; orchestration remains in services.

## `backend/app/schemas/simulation.py`

Pydantic input/output contracts.

Preset requests retain the original synchronous round limits:

```text
Small web runs      ≤ 100 rounds
Standard web runs   ≤ 50 rounds
Large web runs      ≤ 20 rounds
```

Phase 2I adds optional `AdvancedSimulationConfig` with global hard bounds and `K < population`. Advanced requests may use up to 100 rounds only while the shared conservative workload remains `≤ 100,000` conversations. These are runtime safety controls, not empirical model limits.

## `backend/app/services/simulation_config_service.py`

Single authoritative Phase 2I effective-configuration boundary. `resolve_effective_preset(request)` returns the registered Small/Standard/Large preset when `advanced_config` is absent or a run-local immutable `PopulationPreset` populated from validated overrides when enabled. `estimate_conversation_upper_bound()` implements the shared `floor(population × max chats / 2) × rounds` workload formula. Preview, ordinary runs, Full Live and audit logging must use this service rather than independently reconstructing values.

## `backend/app/services/simulation_service.py`

Application orchestration boundary:

1. resolve the effective preset through `simulation_config_service`;
2. resolve Excel trait repository;
3. generate population;
4. build ProductKnowledge;
5. configure/run SimulationEngine;
6. serialize domain result into API DTOs;
7. expose whether traits came from `excel` or bootstrap fallback.

This file may coordinate domain components but should not become a second simulation engine. `build_run_response()` is shared by ordinary and Full Live orchestration so Results serialization stays identical. Actual runs create one audit sink and thread it through population generation, `SimulationEngine`, and the render pipeline; preview-only requests do not create audit files.

## `backend/app/services/run_audit_service.py`

Backend lifecycle owner for Phase 2H run traces. It creates `logs/model-runs/YYYY-MM-DD_HH-MM-SS-ffffff_DayName.jsonl`, emits safe run lifecycle/configuration metadata, writes the matching Markdown summary, and closes the audit sink on completed/failed/cancelled paths. Audit-file creation is required before an actual run begins. Raw backend exception text is intentionally not persisted.

## `backend/app/services/full_live_jobs.py`

In-process Full Live job domain/store. Owns job IDs, state transitions, progress telemetry, cancellation events, sanitized failures, final result storage, and task references. It never stores the DeepSeek API key or provider object. Phase 2H keeps an internal audit-sink reference per active job so the user cancellation request itself emits `run.cancel_requested`; audit file paths are retained internally but are not browser API fields. Restarting FastAPI clears this store.

## `backend/app/services/llm_catalog.py`

Provider/model discovery boundary. DeepSeek availability comes from server configuration; Ollama scans the configured local service through `/api/tags`. Discovery returns sanitized reachable/unavailable/empty-model states and model metadata without exposing local paths or credentials.

## `backend/app/services/llm_provider_factory.py`

Validates an exact `(provider_id, model_id)` and constructs the corresponding `LLMProvider` with provider-specific concurrency/pricing/telemetry capability. Full Live depends on this factory rather than provider-specific branches. Resolving DeepSeek does not probe Ollama.

## `backend/app/services/full_live_service.py`

Full Live orchestration boundary. It resolves the confirmed provider/model through `llm_provider_factory`, creates the job with source metadata, uses `simulation_config_service` for the same effective preset/workload estimate as ordinary simulation, runs the deterministic core simulation in `asyncio.to_thread`, records the exact scheduled conversation count, invokes the same uncapped renderer with provider-specific concurrency/pricing, streams progress, honors cancellation, and completes using the shared Results serializer.

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

Version-controlled canonical seed definition used to generate the Excel files. Phase 2A enforces exactly 10 rows per category with unique stable keys so trait depth cannot silently regress.

It is not intended to replace Excel as the human-editable modeling interface permanently.

## `scripts/generate_trait_workbooks.py`

Deterministically constructs the current workbook layout from `catalog.source.json`, rejects any category that is not exactly 10 rows, then regenerates `catalog.manifest.json`.

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

## `simulation/audit/`

Phase 2H framework-independent audit package. `logger.py` defines the explicit `RunAuditSink` protocol plus null, memory, and production JSONL implementations; `serializer.py` converts domain/Pydantic/NumPy values into JSON-safe payloads; `redaction.py` recursively removes credential/private-reasoning fields and supports exact credential-string scrubbing; `summary.py` writes the bounded Markdown companion; `events.py` owns the audit schema/version sentinels.

Production JSONL writes are append-only, flushed per event, and protected by a lock around sequence assignment/write so Full Live workers cannot corrupt the stream. The production writer keeps only bounded event counters/round summaries—not a duplicate event list in RAM. Audit sinks must remain observational: adding/removing tracing must not change RNG draws, simulation state, scheduler choices, or provider request payloads.

Runtime traces live under Git-ignored `logs/model-runs/`. They may contain confidential product pitches and synthetic-agent state even though secrets/private model reasoning are redacted.

---

# 8. Product baseline evaluation

## `simulation/product/knowledge.py`

Normalized product input consumed by the simulation engine.

Future photo/document parsing should normalize into this product-knowledge layer instead of adding image-specific branches throughout the simulator.

## `simulation/product/taxonomy.py`

Phase 2J-A authoritative product classification boundary. `resolve_product_taxonomy()` returns stable `family + form` from the explicit user category first; pitch/features are fallback classification only for unknown/general categories. Recognized categories must not change family because a pitch mentions `app`, `security`, `study`, `subscription`, or another incidental domain word.

## `simulation/product/text_evidence.py`

Shared deterministic evidence normalization/context layer. Source text and phrase rules pass through the same token normalization, while local prefix/suffix blockers prevent false positives such as `not reliable`, `warranty exclusions`, or `no offline export`. This is a bounded rule engine, not general NLP and not an LLM semantic scorer.

## `simulation/product/semantic_profile.py`

Builds one immutable deterministic `ProductSemanticProfile` per run from user-supplied category, pitch, and features. It exposes bounded usefulness/quality/trust/novelty evidence, privacy exposure, complexity, recurring cost, support/reliability, claim uncertainty, plus Phase 2J-A underlying `reliability_risk`, `serviceability_risk`, `safety_risk`, `data_practice_risk`, and `cancellation_friction`. Those underlying risks feed the existing six belief topics; they do not create a parallel state model. Phrase/risk rules are explicit synthetic assumptions and must not be presented as verified facts.

## `simulation/product/price_catalog.py`

Phase 2J-A form-aware synthetic price-reference catalog. Known product forms such as earbuds, power banks, robot vacuums, cameras, beauty devices, fragrance, education software, VPN, and business SaaS receive separate cadence-aware calibration anchors. Unknown forms fall back to historical family anchors. Values are simulator calibration parameters, not current market-price claims.

## `simulation/product/pricing.py`

Owns `BillingCadence` (`auto`, `one_time`, `monthly`, `yearly`), deterministic cadence inference/override, and per-agent `ConsumerPriceContext`. Product execution resolves category taxonomy and form-aware price reference; family-only `reference_price_for()` remains a compatibility fallback. Amount/reference ratio sets the population baseline; centered income, price-sensitivity, and product-need terms create individual spread. Occupation, age, student status, locale, and other demographic labels are not affordability inputs. Audit inputs record form/reference source. `with_stance()` refreshes only dialogue-facing current price stance while preserving economic context.

These calibration anchors are simulator priors, not market-price claims.

## `simulation/product/fit.py`

Builds deterministic per-agent `ConsumerProductFit`: category-conditioned need, affordability, adoption fit, risk fit, privacy concern, and canonical cadence-aware price context. Phase 2J-A risk fit now includes named reliability/serviceability/safety/data/cancellation burden from the product semantic profile. Existing generic `product_need` is still active here; Phase 2J-B replaces its current dominance with category/life-context need.

## `simulation/product/baseline_evaluation.py`

Produces neutral-centered initial topic beliefs before social influence. It combines the immutable product semantic profile, consumer-product fit, correlated consumer-specific outlook, and bounded seeded variation. Favorable evidence can generate advocates while poor reliability/support, low fit, privacy exposure, uncertainty, and high cost can generate skeptics/negative segments. No sentiment quota is imposed.

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

Deterministic semantic interaction generator. It selects topic beliefs using salience/disagreement/relevance plus completed-prior-round topic memory, fixes both semantic messages first, derives a dialogue shape, then renders deterministic wording. Price wording receives the refreshed current `ConsumerPriceContext`; presentation cannot modify `topic_effects`.

## `simulation/conversation/background_language.py`

Deterministic, zero-API-cost language renderer with seven stance-strength bands, multiple phrasing families, price-cadence-aware wording, and optional second-sentence elaboration based on speaking style/dialogue shape. It never invents market comparisons and remains reproducible for the same conversation inputs.

## `simulation/conversation/dialogue_realism.py`

Pure presentation-semantic helpers. `SpeakingStyle` derives from normalized logicality/emotionality/sociability/stubbornness/confidence; `DialogueShape` derives from already-fixed semantic messages. Occupation/age do not determine speaking style, affordability, or factual conclusions.

## `simulation/conversation/ledger.py`

Owns compact start-of-round `AgentLanguageProfile`, `ConversationLanguageContext`, and `ConversationLedgerEntry` records. Language context includes current per-agent `ConsumerPriceContext`: stable affordability/pressure plus price stance refreshed from the current Python belief each round.

## `simulation/conversation/importance.py`

Pure deterministic importance scorer used only for presentation/render prioritization. It combines edge score, influence, receptivity, trust, relationship, semantic intensity, disagreement, and weak-tie status; it does not change whether a conversation happened.

## `simulation/conversation/replay_selector.py`

Display-only deterministic selector for the 12 returned conversation cards. Raw importance stays primary, with bounded topic/stance-direction/round/weak-tie diversity adjustments when comparable alternatives exist. It does not change ledger history, ordinary LLM selection, or Full Live coverage.

## `simulation/conversation/dialogue_policy.py`

Defines mode-level candidate budgets: Economy 5%/max 6, Balanced 20%/max 20, Full max 48. `render_pipeline.py` then applies the stricter global live-request ceiling (currently 10 by default). Selection is deterministic by importance then conversation ID.

## `simulation/conversation/language_renderer.py`

Provider-agnostic async language renderer for selected conversations. It consumes compact historical language context, current price context, speaking style, dialogue shape, and stance bands; validates speaker order and bounded utterances; ignores model-proposed semantic changes; and fails closed to deterministic background wording. The contract asks for normally 1–2 sentences and up to 3 when useful, while explicitly forbidding affordability inference from occupation/age/student status and unsupported competitor/free-alternative/gym/market/review claims. The prompt remains ordered stable renderer contract → stable product context → dynamic conversation context for cache reuse. Phase 2H emits the exact safe system/user prompt, schema, semantic input, provider request ID, accepted transcript, validation failure, and deterministic fallback through the optional audit sink.

## `simulation/conversation/render_pipeline.py`

Post-simulation async renderer for ordinary Economy/Balanced/Full modes. It scores the ledger, applies dialogue policy plus the global request ceiling, renders the first selected requests serially as cache primers, then uses bounded concurrency for the remainder. It preserves ledger order and returns `DialogueRenderStats` with provider model, prompt/cache-hit/cache-miss/output tokens, cache-hit ratio, average/max latency, fallbacks, and configurable estimated cost.

## `simulation/conversation/full_live_renderer.py`

Dedicated uncapped renderer for `full_live`. It does not use importance selection and applies no total-request slice. After serial cache priming, a fixed worker pool claims ledger indexes so memory remains bounded even for large histories. Every scheduled entry is attempted unless cancellation stops new claims; in-flight calls drain, failures fall back, usage remains counted, ledger order/semantic messages are preserved, and progress is emitted after each attempt.

## `simulation/conversation/router.py`

Synchronous semantic conversation boundary used by `SimulationEngine`. It always produces the deterministic semantic/background result in the numerical round loop. External LLM rendering is intentionally performed after the core simulation by `render_pipeline.py` (ADR-004).

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

Returns an aggregation/delta without mutating the start snapshot. With Phase 2H tracing enabled it also emits formula-versioned credibility, receptivity, bounded-confidence distance/factor, information factor, effective weight, weighted target, saturation pressure, clipped delta, noise, and resulting belief without adding RNG calls.

## `simulation/opinion/delta.py`

Explicit state-delta representation used at the synchronous commit boundary.

## `simulation/behaviour/purchase.py`

Derives overall opinion and purchase intent after topic state updates.

Purchase intent must not be copied directly from LLM sentiment or one conversation. Phase 2H traces named value-signal, price, trust, and privacy penalty components plus logistic `z`/probability for baseline and round-commit phases.

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

The engine records initial state plus every round, enabling a timeline of `rounds + 1` points. Its optional Phase 2H audit sink records baseline state, round boundaries, all semantic/evidence events, state deltas, and exact before/after commits while preserving synchronous state authority.

## `simulation/analytics/dashboard.py`

Framework-independent dashboard analytics serializer used by the API/UI interphase. It derives full-population purchase-intent bins and signed topic-conversation pressure from the final population plus the complete semantic conversation ledger. The six canonical topics are `price`, `usefulness`, `quality`, `trust`, `novelty`, and `privacy`.

Each topic now exposes support, criticism, and net signed pressure. `raw_score`/`normalized_score` retain total magnitude for compatibility, while `normalized_support` and `normalized_criticism` drive the centered chart. These are synthetic semantic conversation-pressure measures, not validated causal market importance.

---

# 13. LLM provider layer

## `simulation/llm/base.py`

Generic LLM abstraction. `ProviderAuditContext` carries per-call round/conversation/agent/request correlation without storing mutable audit state on shared providers.

## `simulation/llm/deepseek.py`

Server-side DeepSeek provider for configured cloud execution. Phase 2H logs sanitized HTTP request/visible-response/error metadata, redacts Authorization, strips private reasoning fields, and replaces the exact configured API-key string if a remote response echoes it under an ordinary field name. Audit instrumentation does not alter the actual DeepSeek request payload.

## `simulation/llm/ollama.py`

Native Ollama Local provider implementing the same `LLMProvider` protocol. It uses non-streaming `/api/chat`, maps `prompt_eval_count`/`eval_count` into generic usage telemetry, does not add local authentication, and never owns simulation state.

Responsibilities:

- native `/api/chat` requests without browser-side access to port 11434;
- bounded context allocation through `OLLAMA_NUM_CTX` (default 2048) so short ModelCouncil conversations do not reserve unnecessarily large local model context memory;
- native Ollama JSON Schema structured output when the caller supplies a response schema;
- timeout handling through `httpx`;
- JSON response validation;
- typed provider usage telemetry (`LLMUsage` / `LLMJsonResponse`);
- request latency measurement;
- Phase 2H safe HTTP request/visible-response/error tracing with the same per-call audit correlation used by cloud providers.

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

## `start-dev.ps1`

Root local launcher for FastAPI + Next.js. It verifies dependencies, repairs the frontend API base URL, runs quick backend checks, starts both development servers, and opens the browser unless disabled.

## `scripts/deepseek_smoke.py`

Bounded live DeepSeek connectivity/cache verifier. It refuses more than 10 calls, never prints the key, keeps a long stable prompt prefix, reports per-call cache hit/miss/output tokens and latency, and prints aggregate cache-hit ratio plus estimated cost. It uses the same project-root DeepSeek key resolver as the backend.

---

# 17. Current Phase 2 output

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
dialogue_stats
analytics
replay
trait_source
```

The frontend consumes exactly these fields. `dialogue_stats` includes provider model/status, selected/rendered/fallback counts, prompt/cache-hit/cache-miss/output/total tokens, cache-hit ratio, average/max render latency, and estimated API cost. `analytics` contains full-population purchase-intent bins and six normalized semantic topic-pressure points for the dashboard.

The `network` DTO is intentionally sampled/bounded for browser rendering; the backend simulation can still contain the full internal graph.

---

# 18. Next Phase 2 file direction

The importance/policy/render/replay files now exist. The next additions should focus on memory and provenance rather than duplicating the current conversation stack:

```text
simulation/memory/
├── models.py
├── importance.py
└── decay.py

simulation/opinion/
└── influence_ledger.py

frontend/features/simulation/
├── agent-inspector.tsx
└── influence-breakdown.tsx

simulation/llm/
└── optional application cache only if later workloads justify reuse beyond DeepSeek's automatic prefix cache
```

Define/test behavior before adding these modules.

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

- Live LLM rendering is post-simulation wording, not a causal linguistic state-transition model.
- Live external rendering remains controlled by `DEEPSEEK_LIVE_ENABLED`; the current private local `.env` enables it, while `.env.example` defaults it off.
- Economy/Balanced/Full define mode-level candidate budgets, but the stricter global `DEEPSEEK_MAX_LIVE_REQUESTS_PER_RUN` ceiling currently defaults to 10.
- Ordinary `/simulations/run` remains synchronous. Full Live has an asynchronous in-process job manager, but it is not durable: FastAPI restart loses job state and production multi-worker deployment will need shared persistence/queue infrastructure.
- No authentication/project persistence/rate limiting yet.
- Behavioral coefficients and trait distributions are explicit synthetic assumptions, not empirically calibrated market truth.
- Replay uses a stable bounded sample (up to 80 state nodes; current SVG shows up to 36) rather than all 5,000 agents.
- No agent memory/influence-provenance inspector yet.
- No multilingual/Hinglish/Hindi conversation layer yet.

These are phase boundaries, not reasons to bypass current safety constraints.

---

# 21. Local handoff rule

Phase 1 has already been merged. The current Phase 2A–2E.6 edits are intentionally local and uncommitted on `main` in `E:\model counsel`.

Do **not** commit, push, or open a pull request unless the project owner explicitly requests it.
