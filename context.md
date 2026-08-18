# ModelCouncil — Master Context for Codex and Contributors

**Project root after local checkout:** `E:\model counsel`  
**Repository:** `brinesolution/ModelCouncil`  
**Current development branch:** local `main` checkout; Phase 2 changes are currently local-only and not pushed
**Current phase:** Phase 2J reliability repair program — 2J-A semantic correctness/audit privacy is being implemented first, followed only after its green gate by 2J-B active population context, 2J-C social dynamics calibration, and 2J-D conversation/provider validation; Phase 2I Advanced controls remain available for fast debugging.
**Project version:** `0.1.x` pre-release  
**Purpose:** Read this file before architecture-level changes.

---

## 1. What ModelCouncil is

ModelCouncil is a web-based synthetic consumer society and product-intelligence simulator. A user enters a product and pitch in the website. The system creates a heterogeneous synthetic consumer population from structured trait libraries, generates baseline product beliefs, builds a weighted K-nearest-neighbour social graph, schedules a limited number of realistic neighbour interactions, aggregates those interactions synchronously, and tracks how topic beliefs, confidence, knowledge, overall opinion, and purchase intent evolve through simulated time.

Portfolio-level concept:

> **Watch a product idea enter a synthetic society, move through conversations, mutate through individual interpretation, and produce measurable changes in consumer behaviour.**

All current outputs are synthetic experiments. They must not be described as statistically validated predictions of real consumers unless a later phase calibrates the system against real empirical data.

---

## 2. Current implemented pipeline

The merged Phase 1 implementation plus the current local Phase 2 work provides this browser/API/simulation path:

```text
Next.js product-pitch form
        ↓
FastAPI POST /api/v1/simulations/run
        ↓
resolve preset or validated Advanced effective configuration
        ↓
Excel-backed TraitRepository
        ↓
Seeded synthetic population
        ↓
Baseline product beliefs
        ↓
Weighted KNN graph + weak ties
        ↓
Capacity-limited conversation scheduler
        ↓
Deterministic background semantic conversations
        ↓
Deterministic natural-English transcript rendering
        ↓
TopicEvidence for both participants
        ↓
Synchronous round aggregation
        ↓
One AgentStateDelta commit per agent
        ↓
Derived overall opinion + purchase intent
        ↓
Compact round replay checkpoint
        ↓
[after all numerical rounds]
conversation importance ranking
        ↓
bounded Economy / Balanced / Full render policy
        ↓
optional post-simulation DeepSeek wording with fail-closed fallback
        ↓
Timeline / replay network / selected conversation DTOs
        ↓
Dashboard analytics serialization
        ↓
Six-chart 3×2 analytics matrix
        ↓
Industrial results command center + round replay + conversation log
```

Live LLM rendering is intentionally outside the synchronous numerical round loop. A configured key does not spend credits unless `DEEPSEEK_LIVE_ENABLED=true`; tests always disable/replace the live provider. The local project `.env` is currently live-enabled with a hard per-run ceiling of 10 requests, while `.env.example` remains disabled by default for fresh checkouts.

---

## 3. Architectural invariants

These are hard project rules.

1. **The simulation engine owns numerical state.**
2. **The LLM gives selected interactions language/semantic interpretation; it does not directly set final opinion or purchase intent.**
3. **An agent is a persistent stateful individual, not a permanent LLM process.**
4. **K defines candidate neighbours, not conversations per round.**
5. **Normal agents have limited conversation capacity.** Current maximum is two scheduled conversations per agent per round.
6. **Default round updates are synchronous.** Every conversation in round `t` reads the same frozen start-of-round state. Effects are aggregated, then `S(t+1)` is committed once.
7. **Conversation effects are topic-specific.** Price discussion does not directly overwrite privacy or quality.
8. **Overall opinion is derived from topic beliefs.**
9. **Purchase intent is a separate derived state.** Liking a product does not imply ability/willingness to buy it.
10. **Randomness is explicitly seeded where practical.**
11. **Normalized state is bounded.**
12. **Facts and opinions are distinct.** Future LLM-created unsupported product facts cannot silently become truth.
13. **`simulation/` stays framework-independent.** It must not import FastAPI or Next.js.
14. **Secrets stay server-side.** DeepSeek keys must never enter browser bundles or Git.
15. **Synthetic outputs are labelled synthetic.**

---

## 4. Population and web-run presets

| Mode | Population | Base K | Initiator rate | Max conversations / agent / round | Weak ties | Minutes / round |
|---|---:|---:|---:|---:|---:|---:|
| Small | 250 | 10 | 20% | 2 | 5% | 5 |
| Standard | 1,000 | 14 | 20% | 2 | 5% | 5 |
| Large | 5,000 | 18 | 20% | 2 | 5% | 5 |

**Standard (1,000)** is the normal recommended mode.

Because the current web API executes simulations synchronously, request-level round budgets are intentionally stricter:

- Small: maximum 100 web rounds
- Standard: maximum 50 web rounds
- Large: maximum 20 web rounds

The default 20-round scenario remains valid for all three modes. Larger research experiments should later use an asynchronous worker/job system rather than loosening synchronous HTTP limits.

---

## 5. Trait system

Current trait source directory:

```text
data/traits/
├── archetypes.xlsx
├── compatibility_rules.xlsx
├── consumer_behaviour.xlsx
├── decision_styles.xlsx
├── demographics.xlsx
├── economic_traits.xlsx
├── emotions.xlsx
├── occupations.xlsx
├── personality.xlsx
├── social_behaviour.xlsx
├── technology.xlsx
├── catalog.source.json
├── catalog.manifest.json
└── README.md
```

`catalog.source.json` is the canonical reproducible seed definition for the initial workbooks. Phase 2A requires **exactly 10 rows in every trait category** with unique stable keys. `scripts/generate_trait_workbooks.py` now rejects any category that does not contain exactly 10 rows. The `.xlsx` files are generated derivatives, while `catalog.manifest.json` records size/SHA-256 integrity metadata for each workbook.

Regression tests verify:

- every source category contains exactly 10 rows and has unique keys;
- every declared workbook physically exists;
- no undeclared workbook is silently added;
- workbook bytes match manifest hashes/sizes;
- the actual Excel files load through `ExcelTraitRepository`;
- required categories are present;
- category probabilities normalize correctly.

The workbooks are editable model assumptions, not empirical truth. Stable `key` values should be preserved when labels/descriptions/weights are edited.

---

## 6. Agent state

### Stable/slow identity

Current `AgentTraits` includes:

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

`ConsumerAgent` additionally includes agent ID, age, occupation, normalized income score, primary language, and locale.

### Dynamic product state

Current `AgentState` includes:

- `ProductBeliefs`: price, usefulness, quality, trust, novelty, privacy;
- overall opinion;
- confidence;
- knowledge;
- purchase intent;
- product salience.

Opinion dimensions use `-1..1`. Most other normalized variables use `0..1`.

Future state can add explicit memories, emotions, product lifecycle stage, factual beliefs, satisfaction, and richer relationship types without changing the Phase 1 architecture.

---

## 7. Population generation

`simulation/population/generator.py` supports seeded generation using either:

- `ExcelTraitRepository` from `data/traits/*.xlsx`; or
- bootstrap distributions when no repository is supplied (test/development fallback).

The backend uses the Excel repository when real workbooks are present. API responses expose `trait_source` so the UI/debugger can see whether a run used `excel` or `bootstrap` traits.

Correlation/compatibility behavior belongs in `simulation/population/correlations.py`, not scattered through API or UI code.

---

## 8. KNN social graph

`simulation/network/knn_graph.py` creates a weighted similarity graph over selected normalized agent features.

Important interpretation:

> KNN represents candidate social/behavioural neighbourhoods, not literal guaranteed friendships and not conversations with all K people.

The graph also receives a small number of weak ties. Weak ties allow cross-cluster propagation and reduce deterministic echo chambers.

Relationship strength, trust, similarity, weak-tie status, and interaction recency are graph-edge state.

Do not rebuild the entire social graph every round in the current model.

---

## 9. Conversation scheduling

`simulation/conversation/scheduler.py` is separate from graph construction.

A typical round:

1. Determine potential initiators using sociability/product salience and the preset initiator rate.
2. Examine eligible graph neighbours.
3. Apply cooldown/availability/capacity rules.
4. Weight candidates instead of always choosing the single closest neighbour.
5. Schedule unique unordered pairs.
6. Do not exceed the per-agent conversation capacity.

This prevents unrealistic behavior where all K neighbours talk simultaneously or one high-similarity node is selected by everyone.

---

## 10. Semantic conversations and Phase 2 language rendering

`simulation/conversation/background_engine.py` generates deterministic semantic interaction payloads plus deterministic background wording. The semantic payload remains authoritative for state changes.

Each `ConversationLedgerEntry` stores compact start-of-round participant language profiles, edge metadata, and per-agent `ConsumerPriceContext`. The price context carries cadence, affordability, price pressure, and the current Python-owned price stance; its stance is refreshed from the current belief every round so wording cannot use stale baseline price sentiment. Demographic labels remain available for identity/context but are not numerical affordability inputs.

`simulation/conversation/dialogue_realism.py` derives `SpeakingStyle` from normalized personality/state traits and `DialogueShape` from already-fixed semantic messages. Completed prior-round topic history creates a soft repetition penalty without changing same-round synchronous snapshot semantics. `background_language.py` uses seven stance-strength bands and the same current price context for deterministic wording.

`simulation/conversation/importance.py` assigns a deterministic bounded importance score; `dialogue_policy.py` applies Economy/Balanced/Full budgets; `render_pipeline.py` upgrades selected transcripts after the numerical simulation. The provider prompt forbids occupation/age/student affordability inference and unsupported competitor/free-alternative/gym/market/review claims, while allowing normally 1–2 sentence turns and up to 3 sentences when useful. Initial synchronous render budgets remain Economy 5% capped at 6, Balanced 20% capped at 20, and Full capped at 48 before the stricter normal global live ceiling.

`simulation/conversation/full_live_renderer.py` is a separate path for `full_live`. It applies no importance selection and no total-request cap: every scheduled ledger entry is attempted unless cancellation stops new worker claims. It uses serial cache priming followed by a fixed bounded worker pool. Provider failure or invalid output keeps the deterministic background transcript and continues.

---

## 11. Opinion update model

Do **not** update agents sequentially as each conversation executes.

Phase 1 uses:

```text
freeze S(t)
   ↓
all scheduled conversations read S(t)
   ↓
produce TopicEvidence
   ↓
aggregate by listener/topic
   ↓
credibility × receptivity × bounded confidence
   ↓
saturating influence + small seeded noise
   ↓
AgentStateDelta
   ↓
one commit → S(t+1)
```

The aggregator accounts for trust, relationship strength, speaker confidence/influence, listener stubbornness/confidence, message relevance, and bounded-confidence acceptance. Influence saturates so many repeated conversations are not linearly unlimited.

---

## 12. Product evaluation and purchase intent

`simulation/product/semantic_profile.py` deterministically converts user-supplied category/pitch/features into bounded synthetic signals for usefulness, quality, trust, novelty, privacy exposure, complexity, recurring cost, support/reliability, claim uncertainty, and category family. These are explicit modeling assumptions, not verified product facts or empirical market calibration.

`simulation/product/pricing.py` owns billing cadence (`auto`, `one_time`, `monthly`, `yearly`), deterministic Auto inference, synthetic category × cadence INR anchors, and `ConsumerPriceContext`. Amount/reference ratio establishes the population price baseline; centered income, price-sensitivity, and need terms create individual disagreement. Occupation, age, student status, locale, and other demographic labels do not participate in numerical affordability. Synthetic anchors must never be presented as observed market averages.

`simulation/product/fit.py` combines the semantic profile with each consumer to derive category-conditioned need, affordability, adoption fit, risk fit, privacy concern, and the canonical cadence-aware price context.

`simulation/product/baseline_evaluation.py` creates neutral-centered first-exposure beliefs from product evidence, consumer-product fit, correlated individual outlook, and bounded seeded variation. The same pitch can therefore create advocates and skeptics based on fit; no fixed negative quota exists.

`simulation/behaviour/purchase.py` separately derives:

- overall product opinion;
- purchase intent.

A consumer may like a product while remaining unlikely to buy it because of price, need, risk, or other constraints.

---

## 13. Web/API implementation

### Backend

FastAPI routes:

- `GET /api/v1/health`
- `POST /api/v1/simulations/preview`
- `POST /api/v1/simulations/run`
- `POST /api/v1/simulations/full-live`
- `GET /api/v1/simulations/full-live/{job_id}`
- `GET /api/v1/simulations/full-live/{job_id}/result`
- `POST /api/v1/simulations/full-live/{job_id}/cancel`

Run responses include:

- synthetic label;
- product/configuration;
- preset;
- summary;
- timeline;
- bounded sampled network DTO;
- selected conversation metadata including importance/LLM selection;
- dialogue-render statistics;
- compact round replay checkpoints with active sampled conversation edges;
- trait source.

Routes should remain thin. Domain work belongs in `simulation/`; orchestration/serialization belongs in backend services.

### Frontend

Next.js App Router currently provides:

- landing page;
- `/simulate` pitch/config form;
- `/simulations/result` result view;
- `/simulations/full-live/[jobId]` Full Live progress/cancellation console;
- summary cards;
- code-native opinion timeline;
- replayable network with a round slider;
- active conversation-edge highlighting;
- readable conversation cards with source/importance metadata.

The network still uses a bounded sampled layout rather than a production-scale zoomable graph renderer.

---

## 14. DeepSeek boundary

The current provider is `simulation/llm/deepseek.py`.

Server-side configuration comes from the root `.env` through `backend/app/core/config.py`:

```text
DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-flash
DEEPSEEK_THINKING=disabled
DEEPSEEK_LIVE_ENABLED=false
DEEPSEEK_RENDER_CONCURRENCY=4
DEEPSEEK_FULL_LIVE_CONCURRENCY=4
DEEPSEEK_MAX_LIVE_REQUESTS_PER_RUN=10
DEEPSEEK_CACHE_PRIME_REQUESTS=2
DEEPSEEK_CACHE_HIT_USD_PER_MILLION=0.0028
DEEPSEEK_CACHE_MISS_USD_PER_MILLION=0.14
DEEPSEEK_OUTPUT_USD_PER_MILLION=0.28
```

Never commit the real key. `.env` and frontend local env files are Git-ignored. `DEEPSEEK_LIVE_ENABLED` is an explicit cost/safety switch. The project-root `.env` is the authoritative local source for `DEEPSEEK_API_KEY`; ModelCouncil resolves that key ahead of a stale inherited Windows `DEEPSEEK_API_KEY`, while runtime controls keep normal environment-variable precedence.

Phase 2 uses language models only after numerical state is committed. Ordinary Economy/Balanced/Full modes remain selective/bounded. The separate `full_live` mode requires explicit UI confirmation and runs through in-process asynchronous jobs; it attempts every scheduled conversation with no hidden total-call cap. Full Live now resolves an explicit `(provider, model)` through a backend catalog/factory. DeepSeek uses configured cloud credentials/concurrency/pricing; Ollama Local discovers downloaded models through the server-local Ollama API and uses its own local concurrency/zero configured API pricing. The browser never connects to Ollama directly. See ADR-004, ADR-006, and ADR-007.

Live validation on 2026-08-17 succeeded with a 250-agent, 2-round Economy run: 100 semantic conversations, 5 selected DeepSeek renders, 5 successful, 0 fallbacks, 768 cache-hit tokens, 1,975 cache-miss tokens, 388 output tokens, 28.0% aggregate cache-hit ratio, approximately 1.80 s average render latency, and approximately $0.000387 estimated API cost using the configured V4 Flash rates.

---

## 15. Testing and CI

CI runs two independent jobs:

### Python

- Python 3.13
- install `backend/requirements.txt`
- run all `tests/` with pytest

### Frontend

- Node 22
- install exactly from `frontend/package-lock.json` using `npm ci`
- `npm run lint`
- `npm run build`

The CI workflow is read-only (`contents: read`). A temporary write-enabled workbook-generation workflow was used only to repair the interrupted trait-data commit and was removed before merge readiness.

Important regression areas include:

- seeded population reproducibility;
- trait correlation/compatibility;
- workbook integrity/loading;
- KNN/scheduler capacity;
- deterministic background conversations;
- order-independent synchronous aggregation;
- engine replay/reproducibility;
- API result/timeline behavior;
- safe synchronous web-run budgets.

---

## 16. Security/current limitations

Before public deployment, add authentication, user/project isolation, rate limiting, asynchronous job execution for heavy runs, persistence, and stronger abuse controls.

Current synchronous workload bounds are a safety guard, not a substitute for production rate limiting.

No real `.env`, `.venv`, `node_modules`, or `.next` artifacts should ever be tracked.

Product ideas may be confidential. External LLM usage must remain transparent/configurable. Phase 2H intentionally stores product content and synthetic run state in local Git-ignored audit files for debugging, so `logs/model-runs/` must be treated as sensitive local data even though credentials/private model reasoning are redacted.

---

## 17. Phase 2 direction

Implemented locally through Phase 2I plus the current Phase 2J-A semantic-correctness slice:

1. deterministic importance scoring;
2. bounded `economy` / `balanced` / `full` dialogue routing;
3. post-simulation DeepSeek transcript rendering with a global live-request ceiling;
4. stable-prefix cache optimization plus serial cache priming;
5. provider usage/cache/latency/cost telemetry;
6. fail-closed deterministic transcript fallback;
7. project `.env` DeepSeek-key precedence over stale inherited Windows key values;
8. compact round checkpoints;
9. round-slider network replay;
10. active conversation-edge highlighting;
11. live provider/token/cache metrics in the result UI;
12. centralized industrial-skeuomorphic design tokens and physical interaction states;
13. redesigned Home, Simulation, and Results surfaces under one visual system;
14. dashboard analytics API for full-population purchase-intent bins and semantic topic pressure;
15. six semantic charts in a strict 3×2 desktop matrix: final sentiment, purchase-intent distribution, opinion/purchase trend, conversation volume, topic pressure, and influence-vs-purchase scatter;
16. dark technical analytics instruments mounted on the light graphite chassis, with 2×3 tablet and 1×6 mobile fallbacks;
17. explicit `full_live` dialogue mode that never executes through the ordinary synchronous endpoint;
18. uncapped all-scheduled-conversation renderer with fixed worker concurrency and cancellation-aware work claiming;
19. in-memory Full Live job state machine: queued → simulating → rendering/cancelling → completed/cancelled/failed;
20. Full Live start/status/result/cancel API lifecycle plus actual token/cache/latency/cost progress telemetry;
21. warning modal with conservative call upper bound and typed `FULL LIVE` acknowledgement above 5,000 calls;
22. Full Live progress route with cancellation and completed-result handoff into the normal Results dashboard;
23. provider catalog/factory boundary with stable `deepseek` and `ollama` IDs;
24. server-side `GET /api/v1/llm/providers` discovery for configured DeepSeek and installed Ollama models;
25. native Ollama `/api/chat` provider implementing the same semantic-preserving `LLMProvider` protocol;
26. Full-Live-only source/model selector, provider-aware warning copy, and provider/model progress/result metadata;
27. Ollama local-compute telemetry semantics (`N/A` cache reuse, zero configured API pricing) without changing numerical simulation state;
28. deterministic `ProductSemanticProfile` derived from pitch/category/features rather than an LLM scorer;
29. `ConsumerProductFit` with category-conditioned need, affordability, privacy concern, adoption/risk fit, and category-relative price pressure;
30. neutral-centered product-sensitive baseline beliefs capable of genuine positive/neutral/negative segments without forced quotas;
31. disagreement-, relevance-, and objection-aware conversation topic selection across all six topics;
32. bounded moderate-disagreement information factor while preserving synchronous state commits and extreme-contradiction damping;
33. purchase-intent rework with explicit affordability/price, negative-trust/risk-aversion, and privacy penalties;
34. signed topic analytics exposing support, criticism, and net conversation pressure while retaining magnitude fields for compatibility;
35. first-class billing cadence with deterministic Auto inference and manual override;
36. synthetic category × cadence price calibration plus `ConsumerPriceContext` with demographic-invariant affordability;
37. current-round price stance refresh so language rendering cannot use stale baseline price sentiment;
38. deterministic `SpeakingStyle`, semantic `DialogueShape`, and completed-prior-round topic repetition memory;
39. seven-band deterministic fallback wording with price-aware, stereotype-free phrasing;
40. LLM renderer anti-stereotype/anti-invention contract and natural variable-length turns;
41. diversity-aware 12-card replay selection while preserving raw importance and Full Live coverage;
42. Simulation billing selector plus resolved billing metadata in API/Results;
43. per-run `logs/model-runs/<timestamp>.jsonl` canonical append-only audit streams plus matching Markdown summaries;
44. explicit `RunAuditSink` boundary with null, memory, and thread-safe JSONL implementations;
45. Excel workbook SHA-256/schema/source-row provenance plus per-agent sampled source records and final normalized traits;
46. formula-versioned price/fit/baseline, scheduler/topic, semantic argument, bounded-confidence, state-delta/commit, and purchase-intent trace events;
47. weighted KNN vectors and edge-formation audit plus every semantic conversation/message for every round;
48. exact safe language-render prompt/schema and DeepSeek/Ollama HTTP request/visible-response tracing with per-call correlation IDs;
49. recursive credential/private-reasoning redaction plus exact configured DeepSeek-key scrubbing from echoed provider response strings;
50. Full Live thread-safe concurrent audit writes, explicit cancellation-request/terminal events, degraded writer behavior, and audit-on/off deterministic-equivalence tests;
51. opt-in Advanced simulation controls layered on top of Small/Standard/Large rather than introducing a separate custom engine or population mode;
52. one backend effective-configuration resolver shared by preview, ordinary simulation, Full Live bounds, Results, and Phase 2H audit metadata;
53. Advanced hard validation for population/K/chat capacity/rates/minutes/rounds plus the shared 100,000-conversation conservative workload ceiling;
54. exact Full Live upper-bound estimation using `floor(population × max chats / 2) × rounds` from effective configuration;
55. industrial Advanced UI control bank with PRESET/ADVANCED Run Console metadata, immediate browser validation, and tiny 20–100 agent debug-run support;
56. deterministic-equivalence regression proving registered-preset values and equivalent Advanced values produce the same numerical simulation;
57. explicit-category-authoritative product taxonomy with stable family + product-form resolution;
58. one canonical contextual evidence normalizer/matcher covering hyphenation, local negation, exclusions, and non-recurring qualifiers;
59. structured reliability, serviceability, safety, data-practice, and cancellation-friction signals mapped into existing quality/trust/privacy/risk-fit mechanics;
60. form-aware synthetic price-reference catalog so power banks, earbuds, robot vacuums, cameras, software forms, beauty devices, and fragrance do not share overly broad anchors;
61. Ollama `thinking` response fields treated as private reasoning and omitted from Phase 2H audit persistence;
62. twelve-family × three-severity semantic regression plus same-seed numerical product comparisons.

The active next sequence is fixed by the Phase 2J program: finish/verify 2J-A, then 2J-B active population/life context, then 2J-C social dynamics, then 2J-D provider-language validation/replay observability. Do not tune later layers to compensate for an earlier semantic/population defect.

Multilingual support should start with English / ordinary Indian English. Hindi, Hinglish, and additional Indian-language/code-switch profiles are later extensions.

---

## 18. Development rules for future Codex sessions

- Read `context.md`, `idea.md`, `project coding.md`, and relevant ADRs first.
- Do not replace the simulation with an LLM-only persona system.
- Do not make one permanent LLM process per consumer.
- Preserve seeded reproducibility.
- Add tests before behavioral changes.
- Keep simulation code independent of FastAPI/Next.js.
- Keep provider-specific LLM code behind the provider/router layer.
- Do not silently loosen synchronous web workload limits.
- Do not treat Excel assumptions as empirically validated distributions.
- Update master documents when a phase changes.

---

## 19. Local-development handoff

Phase 1 has already been merged into `main`. The current Phase 2A–2I work is intentionally uncommitted and local in `E:\model counsel`. Do not commit, push, or open a pull request unless the project owner explicitly requests it.
