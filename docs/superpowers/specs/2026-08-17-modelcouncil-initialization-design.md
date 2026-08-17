# ModelCouncil Web-First Initialization Design

**Date:** 2026-08-17  
**Status:** Implemented foundation pending verification

## Goal

Create a distributed web-first foundation for ModelCouncil at `E:\model counsel` that can accept product-pitch configuration in a browser, expose typed FastAPI contracts, preserve server-only DeepSeek secrets, and establish the first independently testable consumer population/social/opinion modules without pretending the full simulator is complete.

## Scope

Initialization includes:

- root configuration/secrets contract;
- Next.js App Router frontend;
- FastAPI API;
- simulation domain package;
- population presets;
- deterministic bootstrap population generation;
- weighted KNN candidate graph;
- weak social ties;
- capacity/cooldown-aware pair scheduling;
- synchronous topic evidence aggregation;
- overall opinion/purchase derivation;
- DeepSeek provider abstraction and mock provider;
- regression tests;
- project/architecture documentation;
- Docker/CI scaffolding.

Initialization explicitly excludes:

- production Excel trait workbooks;
- complete multi-round orchestrator;
- live DeepSeek conversations in simulation;
- database/authentication;
- graph visualization;
- image/document ingestion;
- multilingual agents.

## Architecture

```text
Next.js browser UI
      |
      v
FastAPI /api/v1
      |
      v
application service
      |
      v
simulation/ Python package
   |      |       |
 population network opinion
      |
      +--> generic LLM provider -> DeepSeek/Mock
```

## Web experience

The initialization must already be viewable in the browser.

`/` introduces the system and links to the tool.

`/simulate` contains a working product-pitch form with:

- product name;
- category;
- price;
- pitch;
- population preset;
- dialogue mode;
- rounds;
- random seed.

Submitting calls `POST /api/v1/simulations/preview` and displays the authoritative simulation preset. This endpoint does not invoke an LLM or claim a simulation has run.

## Population specification

```text
Small:    N=250,  K=10
Standard: N=1000, K=14
Large:    N=5000, K=18
```

All initial presets:

```text
max conversations / normal agent / round = 2
potential conversation initiators / round = 20%
weak tie rate = 5%
simulated minutes / round = 5
```

## Agent contract

Stable-ish traits initially include:

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

Dynamic state includes:

- topic beliefs;
- overall opinion;
- confidence;
- knowledge;
- purchase intent;
- product salience.

The full trait catalog will later come from validated Excel sources.

## Network contract

KNN builds candidate social connections using normalized weighted features. K is capped at `N-1`. Graph edges store similarity, relationship strength, trust, weak-tie status, interaction count, and last interaction round.

A small weak-tie fraction reduces perfectly sealed similarity bubbles.

## Conversation scheduler contract

The scheduler, not KNN, chooses active pairs. It:

- filters cooldown edges;
- selects a seeded weighted subset of potential initiators (20% by default) using sociability and salience;
- scores eligible neighbours by similarity, relationship, salience and sociability;
- adds seeded jitter;
- uses weighted neighbour selection;
- enforces per-agent capacity;
- creates unique conversation IDs.

## Opinion contract

All default round interactions use one start-of-round state snapshot.

Topic evidence is weighted by credibility/receptivity/bounded confidence. Social pressure saturates. Topic movement is capped. Small seeded noise is allowed. Agreement/disagreement can adjust confidence.

Overall opinion is derived from topic beliefs.

Purchase intent is derived separately and may differ strongly from overall sentiment.

## LLM contract

Agents do not own LLM processes. A shared provider generates selected language interactions.

`LLMProvider.generate_json()` is the dependency boundary.

DeepSeek is a provider implementation; Mock is an offline/test implementation.

DeepSeek key lives only in the root `.env` and is never exposed to Next.js/browser code.

## Error handling direction

- invalid HTTP input -> Pydantic validation;
- unknown preset -> explicit ValueError/service failure mapping later;
- invalid DeepSeek response -> provider raises structured error;
- future conversation router -> mathematical fallback on provider failure;
- state values -> clamp/validate domain bounds;
- custom K -> cap at `N-1`;
- isolated consumers -> valid zero-conversation state.

## Testing

Initialization must test:

- preset values;
- seeded population reproducibility;
- trait/value bounds;
- graph construction;
- conversation capacity;
- no duplicate same-round pairs;
- order-independent evidence aggregation;
- API health;
- preview contract.

## Future extension boundaries

### Excel traits

Add repository/loader interfaces under `simulation/population/`; do not expose pandas DataFrames throughout domain code.

### Live conversations

Add router/prompt/schema/claim validation modules under `simulation/conversation/`; do not put prompt code in API routes.

### Persistence

Add backend repository layer and PostgreSQL/Supabase only when run persistence/auth is implemented.

### Multimodal inputs

Add ingestion layer that produces normalized `ProductKnowledge`; the simulator should never depend on raw uploaded file formats.

## Acceptance criteria

The foundation is acceptable when project structure exists, browser/API contracts are wired, secrets are isolated, the first simulation modules have executable tests, docs describe current vs future scope, and verification records clearly state which checks were actually run.
