# ModelCouncil

ModelCouncil is a synthetic consumer-society simulator for evaluating product ideas, pricing, positioning, and market narratives before investing in real-world research or launch activity.

Instead of asking a single model for an opinion, ModelCouncil creates a population of persistent synthetic consumers with different traits, needs, budgets, attitudes, decision styles, and social relationships. Those consumers evaluate a product individually, interact through a social network, influence one another over simulated time, and produce aggregate behavioural and opinion signals that can be explored through a web interface.

> ModelCouncil is a simulation and experimentation system. Its outputs are synthetic and should not be treated as statistically validated forecasts of real-world consumers unless the model is separately calibrated against empirical data.

---

## Vision

The goal of ModelCouncil is to make product and market experimentation more dynamic than a conventional prompt, persona list, or static survey simulation.

A product should be able to enter a synthetic society where:

- different consumers interpret the same product differently;
- product need, affordability, risk tolerance, trust, privacy concerns, and adoption tendencies affect individual reactions;
- consumers exist inside a social network rather than as isolated personas;
- conversations spread information, objections, enthusiasm, and uncertainty;
- opinions evolve over multiple simulated rounds;
- purchase intent can diverge from general product liking;
- important conversations can be inspected and replayed;
- optional language models can turn already-computed semantic interactions into natural dialogue;
- the complete run can be audited and reproduced.

The intended outcome is an experimental environment for comparing product concepts, pricing strategies, pitches, positioning, target-market assumptions, and social-response dynamics before moving to more expensive forms of validation.

---

## What ModelCouncil Does

A user supplies a product concept through the web interface, including information such as:

- product name;
- category;
- pitch or description;
- price;
- currency;
- billing cadence;
- population size/configuration;
- number of simulation rounds;
- dialogue/rendering mode;
- deterministic random seed.

ModelCouncil then:

1. builds a synthetic consumer population from structured trait data;
2. interprets the supplied product using deterministic semantic rules;
3. calculates product-consumer fit and price context for each consumer;
4. generates initial topic beliefs and purchase intent;
5. constructs a weighted consumer social network;
6. schedules realistic, capacity-limited conversations;
7. propagates topic-specific evidence between consumers;
8. updates consumer state synchronously after each round;
9. tracks opinion and purchase-intent changes over time;
10. optionally renders selected or all scheduled conversations through an LLM;
11. exposes timelines, analytics, conversation replay, and network replay in the browser;
12. writes local audit traces for reproducibility and debugging.

---

## Core Modelling Principles

### Persistent synthetic consumers

Consumers are persistent stateful entities rather than one-off prompts.

A consumer can carry:

- demographics;
- economic characteristics;
- decision style;
- personality;
- social behaviour;
- technology adoption;
- emotional tendencies;
- price sensitivity;
- risk tolerance;
- brand loyalty;
- product need;
- topic-specific beliefs;
- confidence;
- product knowledge;
- purchase intent;
- social relationships and interaction history.

Structured traits are loaded from editable Excel workbooks in `data/traits/`.

### Product-sensitive evaluation

ModelCouncil does not apply the same generic scoring function to every product.

The product interpretation layer derives deterministic signals such as:

- usefulness;
- quality;
- trust;
- novelty;
- privacy exposure;
- complexity;
- recurring-cost burden;
- reliability risk;
- serviceability risk;
- safety risk;
- data-practice risk;
- cancellation friction;
- claim uncertainty;
- category/form-aware reference-price context.

These signals become inputs to each consumer's individual evaluation.

The semantic lexicons, rules, coefficients, and reference prices are modelling assumptions and can be refined or calibrated over time.

### Consumer-product fit

Different consumers can respond differently to the same product.

Fit can include factors such as:

- category-conditioned need;
- affordability;
- adoption readiness;
- risk compatibility;
- privacy concern;
- price pressure;
- behavioural and decision-style context.

This allows the same pitch to naturally create advocates, neutral consumers, skeptics, and non-buyers without forcing a fixed sentiment distribution.

### Social network simulation

Consumers are connected through a weighted K-nearest-neighbour graph.

The graph represents candidate social similarity and relationships, not guaranteed conversations.

ModelCouncil also introduces bounded weak ties so information can cross clusters rather than remaining trapped inside highly similar groups.

Conversation scheduling respects:

- per-agent conversation capacity;
- initiator probability;
- relationship information;
- conversation cooldowns;
- weak-tie exposure;
- recent interaction history;
- disagreement and relevance.

### Synchronous opinion updates

All conversations inside a round read the same start-of-round state.

The system then aggregates the resulting evidence and commits one combined state update per consumer.

Conceptually:

```text
freeze state S(t)
      |
schedule conversations
      |
all conversations read S(t)
      |
produce topic evidence
      |
aggregate evidence by consumer/topic
      |
calculate bounded state deltas
      |
commit once
      |
state S(t+1)
```

This prevents conversation ordering from arbitrarily changing the result.

### Opinion and purchase intent are separate

A consumer can like a product but still have low purchase intent because of:

- price;
- insufficient need;
- risk;
- privacy concerns;
- recurring cost;
- adoption friction;
- other consumer-product fit constraints.

This separation is important when comparing product desirability with commercial intent.

---

## Conversation System

ModelCouncil separates **simulation semantics** from **natural-language rendering**.

Python owns the authoritative interaction state:

- who talks;
- what topic is discussed;
- the stance of each participant;
- argument strength;
- confidence;
- price interpretation;
- resulting evidence;
- resulting numerical state changes.

Natural-language renderers only express those already-computed semantics.

### Deterministic dialogue

Every run can operate without external LLM calls.

ModelCouncil includes a deterministic background language renderer that produces readable conversations from semantic state.

### DeepSeek

DeepSeek can be used as an optional cloud language renderer.

The backend keeps credentials server-side and records useful provider telemetry such as:

- prompt tokens;
- cache-hit tokens;
- cache-miss tokens;
- completion tokens;
- latency;
- fallback count;
- estimated cost.

### Ollama Local

ModelCouncil can also discover and use locally installed Ollama models.

The browser never talks directly to Ollama. The FastAPI backend discovers available local models and exposes them through the provider catalogue.

ModelCouncil does not install, download, start, update, or remove Ollama models.

### Language validation

Provider-generated dialogue is checked before being accepted.

Validation can reject output containing:

- internal simulator-state terminology;
- renderer or agent implementation labels;
- demographic affordability stereotypes;
- unsupported external market/product facts;
- wording that contradicts the Python-owned semantic stance.

When a provider response fails validation or generation, ModelCouncil falls back to deterministic dialogue instead of allowing the language model to corrupt simulation state.

---

## Dialogue Modes

ModelCouncil supports several language-rendering modes.

| Mode | Purpose |
|---|---|
| `Economy` | Low-cost selective LLM rendering for a small set of important conversations. |
| `Balanced` | Broader selective rendering while keeping API usage bounded. |
| `Full` | The broadest bounded selective rendering for a normal simulation run. |
| `Full Live` | Attempts every conversation already scheduled by the simulator through the selected DeepSeek or Ollama model. |

Full Live does **not** create additional conversations. It renders the conversations the numerical simulator already scheduled.

Cloud providers may incur API costs. Local Ollama execution may require substantial CPU, GPU, RAM, and processing time.

---

## Population Presets

| Preset | Consumers | Base K | Initiator Rate | Max Chats / Agent / Round | Weak Ties |
|---|---:|---:|---:|---:|---:|
| Small | 250 | 10 | 20% | 2 | 5% |
| Standard | 1,000 | 14 | 20% | 2 | 5% |
| Large | 5,000 | 18 | 20% | 2 | 5% |

Default simulated round duration is five minutes.

The web API applies workload limits to prevent a synchronous request from creating an uncontrolled simulation.

---

## Advanced Simulation Controls

The built-in population presets are the default configuration.

Advanced mode allows run-specific overrides for:

- population size;
- K-neighbour count;
- maximum conversations per consumer per round;
- initiator rate;
- weak-tie rate;
- simulated minutes per round;
- number of rounds;
- seed.

Backend validation is authoritative.

Typical hard limits include:

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

---

## Analytics and Replay

The web results interface provides several views into a simulation.

### Run summary

High-level metrics include:

- population size;
- total conversations;
- final mean opinion;
- final mean purchase intent;
- active configuration and seed.

### Timeline

Shows how aggregate opinion, purchase intent, sentiment composition, and conversation volume evolve across rounds.

### Consumer network replay

A bounded social-network view allows the user to inspect:

- sampled consumers;
- social edges;
- influence;
- consumer opinion state;
- purchase intent;
- active conversation edges by round.

The browser intentionally renders a bounded sample rather than attempting to draw every node in a 5,000-consumer simulation.

### Conversation replay

Important conversations can be inspected with:

- participating consumer IDs;
- round;
- topics;
- transcript;
- language source;
- importance;
- LLM-selection information.

### Analytics dashboard

The dashboard includes views such as:

1. final sentiment composition;
2. purchase-intent distribution;
3. opinion and purchase trend;
4. conversation volume by round;
5. topic conversation pressure;
6. influence-vs-purchase distribution.

---

## Run Auditing and Reproducibility

Simulation runs can create detailed local audit traces under:

```text
logs/model-runs/
```

Audit events can include:

- product interpretation;
- trait-workbook provenance;
- generated consumer state;
- product-consumer fit;
- pricing calculations;
- graph construction;
- scheduled conversations;
- semantic messages;
- influence/evidence calculations;
- state updates;
- purchase-intent calculations;
- language-render requests and responses;
- provider telemetry;
- validation failures and fallbacks;
- terminal run status.

The canonical trace format is append-only JSONL with a bounded Markdown summary.

Audit logging is intended to be observational: enabling tracing should not change a seeded numerical simulation.

Because traces can contain confidential product descriptions and detailed synthetic consumer state, `logs/` is excluded from Git.

---

## Project Architecture

```text
ModelCouncil
|
|-- frontend/
|   `-- Next.js web application
|
|-- backend/
|   `-- FastAPI API and orchestration
|
|-- simulation/
|   |-- population/
|   |-- product/
|   |-- network/
|   |-- conversation/
|   |-- opinion/
|   |-- behaviour/
|   |-- analytics/
|   |-- audit/
|   `-- llm/
|
|-- data/
|   `-- traits/
|
|-- tests/
|   |-- backend/
|   `-- simulation/
|
|-- scripts/
|-- docker/
`-- docs/
```

### Architectural boundaries

- `simulation/` remains independent from FastAPI and browser code.
- Backend routes stay thin and delegate orchestration to services.
- Frontend code never owns provider secrets.
- LLM providers do not own or directly mutate consumer state.
- Product semantics and numerical influence remain deterministic Python logic.
- Randomness is seeded where practical for reproducibility.

---

## Technology Stack

### Frontend

- Next.js 16
- React 19
- TypeScript
- ESLint

### Backend

- Python 3.12+
- FastAPI
- Uvicorn
- Pydantic / Pydantic Settings
- HTTPX

### Simulation and data

- NumPy
- pandas
- scikit-learn
- NetworkX
- openpyxl

### Testing

- pytest
- pytest-asyncio
- frontend lint/build verification

### Optional language providers

- DeepSeek API
- Ollama Local

---

## Requirements

Install the following before running ModelCouncil locally:

- Python 3.12 or newer;
- Node.js 20.9 or newer;
- npm;
- PowerShell for the included Windows helper scripts.

Optional:

- a DeepSeek API key for cloud-rendered conversations;
- Ollama for local-model Full Live rendering;
- Docker if using the included container configuration.

---

## Local Installation

Clone the repository and enter the project directory.

Create the local development environment:

```powershell
.\scripts\bootstrap.ps1
```

The bootstrap script:

- creates `.venv`;
- installs `backend/requirements.txt`;
- installs frontend npm dependencies.

---

## Running ModelCouncil

### Development launcher

On Windows:

```powershell
.\start-dev.ps1
```

This starts the backend and frontend development servers.

```text
Frontend       http://localhost:3000
Simulation     http://localhost:3000/simulate
Backend        http://127.0.0.1:8000
FastAPI docs   http://127.0.0.1:8000/docs
```

### Start the backend manually

```powershell
.\.venv\Scripts\Activate.ps1
python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

### Start the frontend manually

```powershell
cd frontend
npm.cmd run dev
```

---

## Environment Configuration

Copy the example configuration into a local root `.env`.

```text
.env.example -> .env
```

Do not commit `.env`.

### DeepSeek

Example:

```text
DEEPSEEK_API_KEY=your_key_here
DEEPSEEK_LIVE_ENABLED=true
```

Additional controls are available in `.env.example`, including:

```text
DEEPSEEK_MODEL
DEEPSEEK_THINKING
DEEPSEEK_RENDER_CONCURRENCY
DEEPSEEK_FULL_LIVE_CONCURRENCY
DEEPSEEK_MAX_LIVE_REQUESTS_PER_RUN
DEEPSEEK_CACHE_PRIME_REQUESTS
```

### Ollama

Default local configuration:

```text
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_DISCOVERY_TIMEOUT_SECONDS=2
OLLAMA_REQUEST_TIMEOUT_SECONDS=120
OLLAMA_NUM_CTX=2048
OLLAMA_FULL_LIVE_CONCURRENCY=1
```

Start and manage Ollama separately. ModelCouncil will discover available models through the backend.

---

## Trait Data

Synthetic population definitions live in:

```text
data/traits/
```

The repository includes workbooks such as:

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

`catalog.source.json` is the canonical structured source used to generate the workbooks.

`catalog.manifest.json` records workbook integrity information.

Regenerate the workbooks with:

```powershell
python scripts\generate_trait_workbooks.py
```

---

## API

The backend API is mounted under `/api/v1`.

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

Interactive API documentation is available from FastAPI at:

```text
http://127.0.0.1:8000/docs
```

---

## Verification

Run the repository checks with:

```powershell
.\scripts\check.ps1
```

The verification workflow covers the Python test suite and, when frontend dependencies are installed, frontend linting and production build checks.

Individual commands:

```powershell
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider tests -q
```

```powershell
cd frontend
npm.cmd run lint
npm.cmd run build
```

---

## Security and Privacy

- Provider API keys remain server-side.
- `.env` files containing secrets are ignored by Git.
- Runtime audit logs are ignored by Git.
- Frontend code must never contain DeepSeek credentials.
- Provider output is validated before being shown as accepted rendered dialogue.
- Audit serialization is designed to avoid intentionally persisting credentials or authorization headers.
- Product pitches and run traces may contain confidential information and should be treated accordingly.

---

## Intended Use Cases

ModelCouncil can be used for synthetic experimentation around:

- early product concepts;
- product positioning;
- pricing;
- subscription vs. one-time purchase models;
- feature/pitch comparisons;
- trust and privacy concerns;
- market-message testing;
- adoption resistance;
- product-category fit;
- social propagation;
- consumer segmentation;
- conversation analysis;
- sensitivity testing across different population/network assumptions.

It is especially useful when the goal is to understand **how assumptions interact inside a simulated society**, rather than receive one aggregate opinion from a single model.

---

## Intended Outcome

The long-term outcome of ModelCouncil is a reproducible product-intelligence environment where a team can:

1. describe a product or market proposition;
2. place it inside a diverse synthetic population;
3. observe first-order consumer reactions;
4. watch social interaction change those reactions;
5. inspect why consumers changed;
6. compare configurations and alternative propositions;
7. identify assumptions worth testing with real customers;
8. export insights into a later empirical research or product-development process.

The project is designed to complement—not replace—real customer interviews, surveys, behavioural data, experimentation, and market validation.

---

## Limitations

ModelCouncil currently models a synthetic society using designed rules and priors.

Important limitations include:

- synthetic trait distributions are not automatically representative of a real population;
- semantic coefficients and price anchors are modelling assumptions;
- generated dialogue is not evidence that a real consumer would say the same thing;
- Full Live language rendering does not make the underlying numerical model more empirically valid;
- provider-generated wording can vary even when numerical state is deterministic;
- backend Full Live jobs use process memory rather than durable distributed job storage;
- saved user projects, authentication, and persistent historical runs require separate persistence infrastructure;
- results should not be described as predicted revenue, conversion, or statistically representative survey results without independent calibration.

---

## Development Direction

ModelCouncil is structured so future work can extend the simulator without changing its core boundaries.

Natural extension areas include:

- empirical calibration against real datasets;
- richer consumer memory and provenance;
- deeper explanation of individual belief changes;
- saved simulations and comparison workflows;
- durable background-job infrastructure;
- persistent projects and authentication;
- richer network exploration;
- product document/image ingestion;
- configurable geographic or demographic population models;
- scenario comparison and experiment management;
- external validation against surveys, experiments, and observed market behaviour.

---

## Deployment Model

The architecture supports a deployment split such as:

```text
GitHub
  |
  |-- Next.js frontend  -> Vercel or equivalent
  |
  |-- FastAPI backend   -> container/application host
  |
  `-- PostgreSQL        -> future persistence/authentication
```

The simulation engine remains independent from deployment infrastructure so it can be tested, profiled, and reproduced separately from the web stack.
