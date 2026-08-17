# ModelCouncil — Master Context for Codex and Contributors

**Project root after local checkout:** `E:\model counsel`  
**Repository:** `brinesolution/ModelCouncil`  
**Current development branch:** `phase-1-vertical-slice`  
**Current phase:** Phase 1 web simulation vertical slice implemented and under merge-safety verification  
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

The `phase-1-vertical-slice` branch implements this complete browser/API/simulation path:

```text
Next.js product-pitch form
        ↓
FastAPI POST /api/v1/simulations/run
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
TopicEvidence for both participants
        ↓
Synchronous round aggregation
        ↓
One AgentStateDelta commit per agent
        ↓
Derived overall opinion + purchase intent
        ↓
Timeline / sampled network / selected conversation DTOs
        ↓
Browser results screen
```

Phase 1 intentionally does **not** require a live LLM call. The DeepSeek provider exists behind the LLM abstraction for the next phase.

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

`catalog.source.json` is the canonical reproducible seed definition for the initial workbooks. `scripts/generate_trait_workbooks.py` generates the `.xlsx` files. `catalog.manifest.json` records size/SHA-256 integrity metadata for each workbook.

Regression tests verify:

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

## 10. Phase 1 semantic conversations

`simulation/conversation/background_engine.py` generates deterministic semantic interaction payloads. These interactions have topics/stances/argument strengths but do not need natural-language text.

`ConversationRouter` currently keeps Phase 1 on the background engine. Live LLM promotion is intentionally reserved for Phase 2.

The user-facing dialogue modes (`economy`, `balanced`, `full`) remain part of the API contract for future routing/cost control, but Phase 1 does not yet spend DeepSeek credits per interaction.

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

`simulation/product/baseline_evaluation.py` creates initial topic beliefs from product knowledge plus consumer traits.

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

Run responses include:

- synthetic label;
- product/configuration;
- preset;
- summary;
- timeline;
- bounded sampled network DTO;
- selected conversation metadata;
- trait source.

Routes should remain thin. Domain work belongs in `simulation/`; orchestration/serialization belongs in backend services.

### Frontend

Next.js App Router currently provides:

- landing page;
- `/simulate` pitch/config form;
- `/simulations/result` result view;
- summary cards;
- code-native opinion timeline;
- bounded network preview.

The current network view is a preview, not the final animated conversation map.

---

## 14. DeepSeek boundary

The current provider is `simulation/llm/deepseek.py`.

Server-side configuration comes from the root `.env` through `backend/app/core/config.py`:

```text
DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-flash
DEEPSEEK_THINKING=disabled
```

Never commit the real key. `.env` and frontend local env files are Git-ignored.

Phase 2 should use the LLM selectively for visible/important dialogue, message interpretation, objections, semantic retelling, and aggregate explanations. The numerical engine remains authoritative.

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

Product ideas may be confidential. Future external LLM usage must be transparent/configurable and must avoid unnecessary logging of user product content.

---

## 17. Phase 2 direction

Next major development stage:

1. selective DeepSeek-backed language conversations;
2. structured transcript schema;
3. agent conversation/memory summaries;
4. visible active conversation edges on the network map;
5. click-to-view conversation transcript;
6. map replay by simulation round;
7. cost-aware `economy` / `balanced` / `full` dialogue routing;
8. stronger segment/product analytics;
9. later product image/document ingestion into normalized product knowledge.

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

## 19. Branch handoff

`phase-1-vertical-slice` is intended to be reviewed and manually merged by the project owner. Do not automatically merge it into `main` without explicit instruction.

After merge, the user will pull the merged `main` branch to `E:\model counsel` and continue local development from there.
