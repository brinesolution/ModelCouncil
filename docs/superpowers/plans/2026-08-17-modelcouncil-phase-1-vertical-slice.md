# ModelCouncil Phase 1 Vertical Slice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the initialization skeleton into the first complete browser-visible multi-round synthetic consumer simulation without requiring live LLM calls.

**Architecture:** Keep the simulation engine framework-independent. Product input enters through FastAPI, becomes a domain product, generates/loads a population, creates initial topic beliefs, builds a KNN graph, schedules background semantic interactions, aggregates round evidence synchronously, recalculates purchase intent, and returns timeline/network analytics to Next.js. Live DeepSeek dialogue remains disabled in this phase except isolated provider tests.

**Tech Stack:** Python 3.13, FastAPI, Pydantic, NumPy, pandas/openpyxl, scikit-learn, NetworkX, pytest, Next.js 16, React 19, TypeScript.

## Global Constraints

- Project root is `E:\model counsel`.
- DeepSeek secret remains only in root `.env`.
- Standard preset remains `N=1000`, `K=14`, max 2 conversations/agent/round, 20% potential initiators/round, 5% weak ties, 5 simulated minutes/round.
- Default updates remain synchronous.
- LLM output never directly overwrites final agent state.
- Simulation outputs are labelled synthetic.
- `simulation/` must not import FastAPI.
- Phase 1 must run with `MockLLM`/no external LLM credit spend.

---

### Task 1: Excel Trait Repository Contract

**Files:**
- Create: `simulation/population/trait_repository.py`
- Create: `simulation/population/excel_repository.py`
- Create: `simulation/population/validator.py`
- Create: `tests/simulation/test_excel_repository.py`
- Modify: `data/traits/README.md`

**Interfaces:**
- Produces: `TraitRepository.load_catalog() -> TraitCatalog`
- Produces: `ExcelTraitRepository(root: Path)`
- Produces: `validate_trait_catalog(catalog: TraitCatalog) -> None`

- [ ] **Step 1: Write the failing repository test**

```python
def test_excel_repository_normalizes_sampling_weights(tmp_path):
    workbook = tmp_path / "personality.xlsx"
    create_test_workbook(workbook, rows=[
        {"key": "analytical", "weight": 2.0, "enabled": True},
        {"key": "emotional", "weight": 1.0, "enabled": True},
    ])
    catalog = ExcelTraitRepository(tmp_path).load_catalog()
    values = catalog.category("personality")
    assert values[0].probability == pytest.approx(2 / 3)
    assert values[1].probability == pytest.approx(1 / 3)
```

- [ ] **Step 2: Run focused test and confirm failure**

```powershell
$env:PYTHONDONTWRITEBYTECODE="1"
python -m pytest -p no:cacheprovider tests/simulation/test_excel_repository.py -q
```

Expected: import/implementation failure because repository classes do not yet exist.

- [ ] **Step 3: Implement typed trait catalog and Excel loader**

Implement stable keys, normalized weights, enabled filtering, numeric range validation, schema-version metadata, and actionable workbook/column errors. Keep pandas confined to the repository implementation.

- [ ] **Step 4: Run focused and existing simulation tests**

```powershell
python -m pytest -p no:cacheprovider tests/simulation -q
```

Expected: all tests pass.

- [ ] **Step 5: Commit logical slice**

```powershell
git add simulation/population data/traits tests/simulation/test_excel_repository.py
git commit -m "feat: add validated Excel trait repository"
```

---

### Task 2: Population Generator Uses Repository

**Files:**
- Modify: `simulation/population/generator.py`
- Create: `simulation/population/correlations.py`
- Create: `tests/simulation/test_population_correlations.py`

**Interfaces:**
- Consumes: `TraitRepository`
- Produces: `generate_population(size: int, seed: int, traits: TraitRepository | None = None) -> list[ConsumerAgent]`

- [ ] **Step 1: Add failing compatibility/correlation tests**

```python
def test_student_generation_does_not_use_senior_executive_income_profile():
    population = generate_population(1000, seed=8, traits=fixed_test_repository())
    students = [agent for agent in population if agent.occupation == "Student"]
    assert students
    assert max(agent.income_score for agent in students) < 0.90
```

- [ ] **Step 2: Run and confirm failure or missing interface**

```powershell
python -m pytest -p no:cacheprovider tests/simulation/test_population_correlations.py -q
```

- [ ] **Step 3: Implement dependency/correlation layer**

Use one `numpy.random.Generator` per population run. Keep compatibility rules in one module rather than scattering conditionals. Preserve the existing no-repository bootstrap path for development.

- [ ] **Step 4: Run population regression suite**

```powershell
python -m pytest -p no:cacheprovider tests/simulation/test_population.py tests/simulation/test_population_correlations.py -q
```

- [ ] **Step 5: Commit**

```powershell
git add simulation/population tests/simulation
git commit -m "feat: generate correlated consumer populations"
```

---

### Task 3: Product Knowledge and Baseline Beliefs

**Files:**
- Create: `simulation/product/knowledge.py`
- Create: `simulation/product/baseline_evaluation.py`
- Create: `tests/simulation/test_baseline_evaluation.py`
- Modify: `simulation/domain/product.py`

**Interfaces:**
- Produces: `ProductKnowledge`
- Produces: `evaluate_baseline(agent: ConsumerAgent, product: ProductKnowledge, seed: int) -> ProductBeliefs`

- [ ] **Step 1: Write failing behavioural tests**

```python
def test_higher_price_sensitivity_penalizes_price_belief():
    low = make_agent(price_sensitivity=0.1)
    high = make_agent(price_sensitivity=0.9)
    product = ProductKnowledge(name="Test", pitch="Useful service", price=999, currency="INR")
    low_belief = evaluate_baseline(low, product, seed=1)
    high_belief = evaluate_baseline(high, product, seed=1)
    assert high_belief.price < low_belief.price
```

- [ ] **Step 2: Verify test fails**

```powershell
python -m pytest -p no:cacheprovider tests/simulation/test_baseline_evaluation.py -q
```

- [ ] **Step 3: Implement interpretable baseline model**

Use consumer need, price sensitivity, technology adoption, risk, initial trust and controlled noise. Return topic beliefs only; derive overall opinion/purchase intent through existing behaviour functions.

- [ ] **Step 4: Run focused tests**

```powershell
python -m pytest -p no:cacheprovider tests/simulation/test_baseline_evaluation.py tests/simulation/test_opinion_aggregation.py -q
```

- [ ] **Step 5: Commit**

```powershell
git add simulation/product simulation/domain/product.py tests/simulation/test_baseline_evaluation.py
git commit -m "feat: add baseline product belief model"
```

---

### Task 4: Background Semantic Conversation Engine

**Files:**
- Create: `simulation/conversation/background_engine.py`
- Create: `simulation/conversation/router.py`
- Create: `tests/simulation/test_background_conversations.py`

**Interfaces:**
- Produces: `generate_background_conversation(pair, snapshot, graph, seed) -> ConversationResult`
- Produces: `ConversationRouter.generate(pair, context) -> ConversationResult`

- [ ] **Step 1: Write deterministic semantic interaction test**

```python
def test_background_conversation_is_reproducible():
    first = generate_background_conversation(pair, snapshot, graph, seed=77)
    second = generate_background_conversation(pair, snapshot, graph, seed=77)
    assert first.messages == second.messages
```

- [ ] **Step 2: Confirm failure**

```powershell
python -m pytest -p no:cacheprovider tests/simulation/test_background_conversations.py -q
```

- [ ] **Step 3: Implement background semantic messages**

Select topics from strongest current beliefs/objections, create bounded stance and argument-strength payloads, and leave `text=None`. Do not use LLM calls.

- [ ] **Step 4: Run conversation/scheduler tests**

```powershell
python -m pytest -p no:cacheprovider tests/simulation/test_background_conversations.py tests/simulation/test_network_scheduler.py -q
```

- [ ] **Step 5: Commit**

```powershell
git add simulation/conversation tests/simulation
git commit -m "feat: add deterministic background conversations"
```

---

### Task 5: Pure Round Delta and Simulation Engine

**Files:**
- Create: `simulation/opinion/delta.py`
- Modify: `simulation/opinion/aggregator.py`
- Create: `simulation/engine.py`
- Create: `tests/simulation/test_engine.py`

**Interfaces:**
- Produces: `AgentStateDelta`
- Produces: `SimulationConfig`
- Produces: `SimulationResult`
- Produces: `SimulationEngine.run(product, population, config) -> SimulationResult`

- [ ] **Step 1: Write failing round-order and replay tests**

```python
def test_engine_same_seed_produces_same_timeline():
    first = run_small_simulation(seed=42, rounds=3)
    second = run_small_simulation(seed=42, rounds=3)
    assert first.timeline == second.timeline
```

```python
def test_round_commit_does_not_mutate_snapshot():
    snapshot = make_snapshot()
    engine.run_round(snapshot, round_index=1)
    assert snapshot == make_snapshot()
```

- [ ] **Step 2: Run and confirm failure**

```powershell
python -m pytest -p no:cacheprovider tests/simulation/test_engine.py -q
```

- [ ] **Step 3: Promote pure round aggregation into a complete state delta**

The initialization already returns immutable `RoundAggregation(belief_updates, confidence_delta)` without mutating the input agent. Extend this into `AgentStateDelta` so knowledge, trust, salience/memory effects, and derived state can also be committed through one explicit end-of-round boundary.

- [ ] **Step 4: Implement multi-round orchestrator**

Each round freezes state, schedules pairs, creates semantic interactions, accumulates `TopicEvidence`, applies state deltas once, derives purchase intent, records conversation/round ledgers, and saves aggregate timeline metrics.

- [ ] **Step 5: Run full simulation tests**

```powershell
python -m pytest -p no:cacheprovider tests/simulation -q
```

- [ ] **Step 6: Commit**

```powershell
git add simulation tests/simulation
git commit -m "feat: add reproducible multi-round simulation engine"
```

---

### Task 6: Simulation API Vertical Slice

**Files:**
- Modify: `backend/app/schemas/simulation.py`
- Modify: `backend/app/services/simulation_service.py`
- Modify: `backend/app/api/routes/simulations.py`
- Modify: `tests/backend/test_api.py`

**Interfaces:**
- Produces: `POST /api/v1/simulations/run`
- Produces: response containing configuration, summary, timeline, graph DTO, selected conversations.

- [ ] **Step 1: Write failing API test**

```python
def test_run_simulation_returns_timeline():
    response = client.post("/api/v1/simulations/run", json=small_request())
    assert response.status_code == 200
    body = response.json()
    assert len(body["timeline"]) == body["rounds"] + 1
    assert body["synthetic"] is True
```

- [ ] **Step 2: Verify failure**

```powershell
python -m pytest -p no:cacheprovider tests/backend/test_api.py -q
```

- [ ] **Step 3: Add domain-to-API serializers and service orchestration**

Keep route body thin. Cap synchronous web population/round limits if profiling demonstrates a latency issue; any cap must be explicit in schema/configuration.

- [ ] **Step 4: Run backend + simulation tests**

```powershell
python -m pytest -p no:cacheprovider tests -q
```

- [ ] **Step 5: Commit**

```powershell
git add backend tests/backend
git commit -m "feat: expose first full simulation API"
```

---

### Task 7: Web Results Screen

**Files:**
- Create: `frontend/types/results.ts`
- Modify: `frontend/lib/api.ts`
- Create: `frontend/features/simulation/results-summary.tsx`
- Create: `frontend/features/simulation/opinion-timeline.tsx`
- Create: `frontend/features/simulation/network-preview.tsx`
- Modify: `frontend/components/product-pitch-form.tsx`
- Create: `frontend/app/simulations/result/page.tsx`

**Interfaces:**
- Consumes: simulation run API response.
- Produces: browser-visible summary/timeline/network representation.

- [ ] **Step 1: Add typed result contracts and API call**

```ts
export interface SimulationTimelinePoint {
  round: number;
  meanOpinion: number;
  meanPurchaseIntent: number;
  positiveShare: number;
  neutralShare: number;
  negativeShare: number;
}
```

- [ ] **Step 2: Implement results summary**

Show synthetic label, population, rounds, K, mean opinion, purchase intent, and conversation count. Avoid fake metrics not returned by the API.

- [ ] **Step 3: Implement first timeline visualization using code-native SVG/CSS**

Do not add a chart dependency until the required interactions justify it.

- [ ] **Step 4: Implement basic network preview**

Render a bounded sample/cluster representation from returned neutral graph DTO; do not attempt 5,000-node full rendering in the first slice.

- [ ] **Step 5: Run frontend checks**

```powershell
cd frontend
npm.cmd run lint
npm.cmd run build
```

- [ ] **Step 6: Commit**

```powershell
git add frontend
git commit -m "feat: show simulation results in web UI"
```

---

### Task 8: End-to-End Verification and Documentation Update

**Files:**
- Modify: `README.md`
- Modify: `context.md`
- Modify: `idea.md`
- Modify: `project coding.md`
- Add focused ADR only if the implementation changed an architecture decision.

- [ ] **Step 1: Run Python suite**

```powershell
cd "E:\model counsel"
$env:PYTHONDONTWRITEBYTECODE="1"
python -m pytest -p no:cacheprovider tests -q
```

Expected: all tests pass.

- [ ] **Step 2: Run frontend lint/build**

```powershell
cd "E:\model counsel\frontend"
npm.cmd run lint
npm.cmd run build
```

Expected: both succeed.

- [ ] **Step 3: Start API and manually verify health/docs**

```powershell
cd "E:\model counsel"
python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

Verify `GET /api/v1/health` and OpenAPI docs.

- [ ] **Step 4: Start web app and exercise full pitch-to-results flow**

```powershell
cd "E:\model counsel\frontend"
npm.cmd run dev
```

Verify product input, run action, timeline result, synthetic labeling, and API failure messaging.

- [ ] **Step 5: Update master documents with exact completed state**

Remove stale "planned" wording for implemented features and preserve future-scope separation.

- [ ] **Step 6: Commit verification/documentation**

```powershell
git add README.md context.md idea.md "project coding.md" docs
git commit -m "docs: record phase one vertical slice"
```

---

## Plan Self-Review

- Every current core architecture requirement maps to a task.
- DeepSeek is intentionally not required for Phase 1 success.
- The plan preserves web-first delivery while simulation logic stays independently testable.
- Multimodal input, database/auth, advanced psychology modules, and live LLM dialogue remain outside this vertical slice.
- The final verification step distinguishes tests/builds actually run from assumptions.
