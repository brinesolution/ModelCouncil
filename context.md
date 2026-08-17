# ModelCouncil — Master Context for Codex and Contributors

**Project root:** `E:\model counsel`  
**Current phase:** Initialization / web-first architecture foundation  
**Project version:** `0.1.0` foundation  
**Primary purpose of this file:** Read this before making architecture-level changes.

---

## 1. What ModelCouncil is

ModelCouncil is a web-based synthetic consumer society and product-intelligence simulator. A user enters a product and product pitch in the website. The system creates a heterogeneous synthetic consumer population from structured traits, builds a weighted similarity/social network, schedules realistic neighbour conversations, optionally renders selected conversations with an LLM, aggregates the resulting evidence synchronously, and tracks how product beliefs, confidence, trust, knowledge, overall opinion, and purchase intent evolve through time.

The portfolio-level visual idea is:

> **Watch a product idea enter a synthetic society, move through conversations, mutate slightly as people reinterpret it, and produce measurable changes in consumer behaviour.**

The system is for synthetic experimentation and hypothesis generation. It must not claim that simulated percentages are statistically representative predictions of real populations unless later calibrated and validated against real data.

---

## 2. How the idea evolved

The project began as an AI-agents analytics idea for population simulation and opinion analysis. It was then narrowed toward **consumer behaviour and product analysis**: a user supplies a product/pitch and the system studies how different synthetic consumers react.

The population design then became explicit rather than LLM-invented. Consumer traits will be maintained in large Excel trait libraries containing demographic, emotional, economic, decision-making, social, technology, personality, and consumer-behaviour variations. Agents are sampled from those distributions with compatibility/dependency rules and controlled random variation.

The next major change was social interaction. Consumers are represented as normalized trait vectors. Weighted K-nearest neighbours create likely social/behavioural neighbourhoods. Agents do not automatically talk to all K neighbours. A separate scheduler chooses a small number of actual conversations each round.

Opinion is allowed to travel through the network while changing slightly. A message can be interpreted, partially accepted, rejected, strengthened, weakened, or retold differently. This enables word-of-mouth, social proof, opinion clusters, echo chambers, influencers, misinformation experiments, corrections, and product adoption dynamics in later phases.

The language layer was then added. Consumers should be viewable on a map/graph and selected active pairs should visibly converse, initially in English / ordinary Indian English. Hindi, Hinglish, and additional Indian-language/code-switching profiles are later extensions. The language should be natural without forced stereotypes or repetitive slang.

The important architecture decision is that **agents are stateful individuals, but they are not separate permanent LLM processes**. Agent identity is stored in Python state: traits, beliefs, confidence, knowledge, relationships, memories, and history. A shared LLM conversation service temporarily gives selected agents language.

Finally, the project was changed from a local-first prototype to a **web-first implementation from initialization**. The simulator remains a framework-independent Python package, but the project begins with a Next.js website and FastAPI backend so every feature can eventually be viewed from the browser.

---

## 3. Core invariants

These are architectural rules, not suggestions.

1. **The simulation engine is authoritative for numerical state.**
2. **The LLM gives language/semantic interpretation, not final state values.**
3. **K defines candidate neighbours, not number of conversations per round.**
4. **Normal agents talk to only a small number of people per round.**
5. **All default round updates are synchronous.** Every conversation in round `t` reads the same start-of-round snapshot, then effects are aggregated once before committing `S(t+1)`.
6. **Conversation effects are topic-specific.** Price discussion should not directly overwrite privacy or quality beliefs.
7. **Overall opinion is derived from topic beliefs.**
8. **Purchase intent is derived from product need/value/trust/price/etc.; it is not the same as sentiment.**
9. **Randomness is seeded and reproducible where practical.**
10. **All normalized state is bounded.**
11. **Facts and opinions are different data types.** Unsupported LLM-generated product facts cannot silently become truth.
12. **Simulation and web frameworks remain decoupled.** `simulation/` must be runnable/testable without FastAPI or Next.js.
13. **Secrets stay server-side.** DeepSeek keys must never reach browser JavaScript.
14. **Synthetic outputs are labelled as synthetic.**

---

## 4. Initial population presets

Three user-facing presets are defined:

| mode | population | base K | normal max conversations / agent / round | potential initiators / round | weak ties | simulated minutes / round |
|---|---:|---:|---:|---:|---:|---:|
| Small | 250 | 10 | 2 | 20% | 5% | 5 |
| Standard | 1,000 | 14 | 2 | 20% | 5% | 5 |
| Large | 5,000 | 18 | 2 | 20% | 5% | 5 |

**Standard (1,000)** is the recommended normal mode.

Population size and dialogue-generation cost are separate settings. Later dialogue modes are:

- `economy` — most interactions mathematical, language generated only selectively;
- `balanced` — selected meaningful/visible conversations get language;
- `full` — every actual scheduled pair can receive generated dialogue; intended mainly for small/medium populations.

---

## 5. Agent structure

An agent contains several kinds of state.

### Relatively stable identity

- demographics;
- occupation/income;
- personality;
- emotional tendencies;
- sociability;
- risk tolerance;
- stubbornness;
- influence power;
- price sensitivity;
- technology adoption;
- brand loyalty;
- product need;
- communication/language profile.

### Dynamic product state

- topic beliefs: price, usefulness, quality, trust, novelty, privacy, later more dimensions;
- overall opinion;
- confidence;
- product knowledge;
- product salience;
- purchase intent;
- later emotions, product lifecycle stage, satisfaction, memories, and factual beliefs.

Most behavioural numeric traits use `0..1`. Opinion dimensions use `-1..1`.

---

## 6. Trait system

The planned editable source is `data/traits/*.xlsx`.

Expected categories include:

- demographics;
- age groups;
- occupations;
- income;
- education;
- personality;
- emotions;
- decision styles;
- economic traits;
- consumer behaviour;
- social behaviour;
- technology;
- interests;
- lifestyle;
- relationships;
- archetypes;
- compatibility rules.

Do not independently randomize every trait. Use dependency chains and correlations. Examples:

- age influences possible education/occupation;
- occupation/age influence income distribution;
- income influences but does not dictate price sensitivity;
- stubbornness tends to reduce susceptibility;
- novelty seeking tends to increase early adoption;
- privacy concern can reduce AI trust for relevant products.

Noise should preserve diversity and avoid deterministic stereotypes.

The current `simulation/population/generator.py` is a bootstrap generator only. It exists to establish contracts/tests before the Excel loader is implemented.

---

## 7. Social network model

Consumers are normalized into feature vectors. Weighted distance is used to build a KNN graph. Not every trait must appear in distance, and product categories may later alter feature weights.

The graph contains candidate interaction edges with fields such as:

- similarity;
- relationship strength;
- trust;
- weak-tie flag;
- last interaction round;
- interaction count.

Pure KNN can create closed bubbles, so the base graph adds a small weak-tie fraction (currently 5%).

Similarity and trust are not identical. Two dissimilar people may have a strong trusted relationship.

The candidate graph should remain mostly stable during MVP. Later versions may evolve relationship strengths and edges slowly.

---

## 8. Conversation scheduling

`K` is not conversation count.

For each round:

1. freeze start-of-round state;
2. inspect eligible social edges;
3. apply cooldown to recently used pairs;
4. select a seeded, weighted subset of potential initiators (20% by default) using sociability and product salience;
5. score eligible neighbours using similarity, relationship, salience, sociability and seeded jitter;
6. perform capacity-aware matching;
7. limit ordinary agents to at most two conversations in the round;
8. create unique conversation IDs;
9. route selected interactions to mathematical or language conversation modes.

Do not always select the nearest neighbour. Weighted randomness prevents one pair from talking continuously.

Influencers should later use broadcast/reach mechanics rather than thousands of one-to-one chats.

---

## 9. Round update model

Never update an agent after each conversation in sequence by default. That creates last-speaker/iteration-order bias.

Instead:

```text
S(t) snapshot
   -> conversation A
   -> conversation B
   -> conversation C
   -> topic evidence ledger
   -> credibility/receptivity weighting
   -> bounded-confidence filtering
   -> saturating aggregation
   -> one combined topic-belief update
   -> update confidence/knowledge/trust/memory
   -> derive overall opinion
   -> derive purchase intent
   -> commit S(t+1)
```

Multiple agreeing conversations should increase pressure but with diminishing returns. Conflicting evidence may move opinion only slightly while reducing confidence.

A normal topic update is capped (current initial target: approximately `0.20` per round) and includes only small seeded behavioural noise.

---

## 10. Language conversations

Every consumer is an individual agent, but there is **one shared conversation service/provider layer**.

Example:

```text
Agent A state + Agent B state + product facts + recent memories
     -> shared conversation engine
     -> short natural dialogue
     -> structured semantic topic effects
     -> Python simulation aggregation
```

Initial language policy:

- English;
- natural Indian English where appropriate;
- no forced slang/stereotypes;
- typically 2–5 short utterances;
- personalities/communication styles remain stable;
- not every conversation changes an opinion;
- consumers may partially agree, disagree, remain uncertain, or change only one belief dimension.

Later languages can include Hindi, Hinglish, Tamil and other profiles, but should be introduced through explicit agent language/communication settings.

---

## 11. LLM architecture

Primary intended provider for current implementation: DeepSeek Flash through a generic `LLMProvider` interface.

Current root `.env` variables include:

```text
DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-flash
DEEPSEEK_THINKING=disabled
```

`simulation/llm/deepseek.py` performs server-side JSON requests. `simulation/llm/mock.py` exists for offline deterministic development and tests.

Do not spread DeepSeek-specific calls across the simulator. Future providers should be interchangeable.

Use LLMs for:

- natural dialogue;
- pitch interpretation;
- objections;
- semantic retelling;
- explanations;
- final human-readable analysis.

Do not use them as the sole mechanism for:

- KNN;
- neighbour choice;
- influence magnitude;
- numerical state transition;
- population generation;
- purchase probability;
- graph analytics.

---

## 12. Future input ingestion

Initial version accepts text product/pitch input.

Later web versions should allow:

- product photos;
- screenshots;
- PDFs;
- DOCX/other product documents;
- landing-page captures;
- marketing images.

Those inputs should pass through an ingestion pipeline:

```text
upload
 -> type validation
 -> text/image/document extraction
 -> product fact extraction
 -> normalized ProductKnowledge record
 -> user review/correction
 -> simulation
```

The simulation should consume normalized product knowledge, not raw files directly.

LLM-generated claims must be checked against product knowledge. If unsupported claims are allowed in a misinformation experiment, they must be explicitly marked unverified/rumour state.

---

## 13. Web architecture

Current stack:

- Next.js 16 App Router + TypeScript frontend;
- FastAPI backend;
- Python simulation core;
- DeepSeek via server-side httpx;
- PostgreSQL/Supabase planned later for persistence/auth;
- GitHub planned as source of truth;
- Vercel planned for frontend;
- backend container host planned separately.

Current web route:

- `/` — product overview;
- `/simulate` — product-pitch + simulation configuration form.

Current API route:

- `GET /api/v1/health`;
- `POST /api/v1/simulations/preview`.

The preview endpoint is deliberately honest: it returns configuration, not fake finished analytics.

---

## 14. Planned visualization

A major future interface is an interactive social map/graph.

Potential encoding:

- node = consumer;
- node position = graph layout or behavioural projection;
- node colour = opinion;
- node size = influence;
- edge thickness = relationship/similarity;
- active conversation edge = highlighted/animated;
- click agent = inspect traits/state/history;
- click active/past edge = inspect conversation transcript and before/after effects.

Large simulations should use level-of-detail/clustering rather than blindly rendering every edge.

Another signature feature is simulation replay: a timeline slider changes network colours, active conversations, segments, and aggregate metrics across saved checkpoints.

---

## 15. Analytics direction

Minimum later metrics:

- mean/median opinion;
- opinion variance;
- positive/neutral/negative share;
- purchase-intent distribution;
- trust;
- price acceptance;
- usefulness;
- segment response;
- opinion over time;
- graph centrality/community metrics;
- influential/bridge agents;
- local consensus;
- polarization/convergence measures;
- top objections and features;
- event impact.

A/B comparisons must use the same population seed unless the experiment explicitly studies population variance.

---

## 16. Development sequence

The project is web-first in presentation but simulation-first in domain correctness.

### Initialization — current

- repository structure;
- root secret/config contract;
- Next.js shell;
- FastAPI shell;
- product-pitch form;
- population presets;
- bootstrap population;
- KNN graph;
- conversation scheduler;
- synchronous opinion aggregation;
- purchase-intent derivation;
- LLM abstraction;
- tests;
- documentation.

### Phase 1

- Excel trait loader + validation;
- product model normalization;
- baseline product evaluation;
- complete round engine;
- semantic interaction ledger;
- first analytics payload;
- web simulation run/status/results pages.

### Phase 2

- real DeepSeek dialogue generation;
- batch conversations;
- conversation cache;
- memory summaries;
- active graph visualization;
- transcript inspector;
- simulation replay.

### Phase 3

- persistence/auth;
- projects/products/saved experiments;
- A/B pitch comparisons;
- events/influencers/reviews;
- richer behavioural modules.

### Later

- image/document ingestion;
- multilingual/code-switching agents;
- misinformation/correction;
- dynamic networks;
- product lifecycle;
- empirical calibration/research extensions.

---

## 17. Known edge cases that the code must respect

- `K <= N-1` for custom small populations;
- isolated agents may legitimately have no conversation;
- no pair duplicated in the same round;
- agent conversation capacity enforced;
- pair cooldown prevents repetitive chat loops;
- synchronous updates avoid order dependence;
- disagreement may reduce confidence instead of flipping opinion;
- repeated argument novelty should later decay while social proof can still rise;
- categorical facts must not be numerically averaged;
- all LLM JSON must be validated;
- LLM failure must fall back to mathematical interaction rather than killing the run;
- one high-influence agent cannot affect everyone unless reach/trust/network exposure permit it;
- relationship state changes slower than product beliefs;
- graph should not rebuild completely each round;
- large graph UI requires clustering/LOD;
- unsupported product facts cannot silently propagate;
- identical seeds/config should reproduce deterministic behavior.

---

## 18. Current source-of-truth files

- `idea.md` — full idea/history/roadmap;
- `project coding.md` — exact code structure and responsibilities;
- `context.md` — this condensed architecture contract;
- `docs/architecture/` — focused architecture notes;
- `docs/decisions/` — architecture decision records;
- `tests/` — executable behavioural invariants.

When a future decision materially changes architecture, update these documents instead of leaving contradictory old assumptions in place.
