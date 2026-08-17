# System Architecture

## Purpose

ModelCouncil is web-first at the product boundary but domain-first internally. The browser is the control and visualization surface; FastAPI is the server/application boundary; `simulation/` is the authoritative agent-based simulation engine.

## Runtime topology

```text
Browser
  |
  v
Next.js frontend :3000
  |
  | JSON / later WebSocket/SSE
  v
FastAPI backend :8000
  |
  +--> Simulation engine
  |      +--> population
  |      +--> KNN/social graph
  |      +--> conversation scheduler
  |      +--> opinion dynamics
  |      +--> purchase model
  |      `--> analytics
  |
  +--> Shared LLM provider
  |      `--> DeepSeek / Mock / future providers
  |
  `--> Persistence later
         `--> PostgreSQL/Supabase
```

## Boundaries

### Frontend

Owns user interaction and visualization only. It may display agent state but must never independently calculate authoritative social/opinion transitions.

### Backend

Owns HTTP validation, orchestration, authorization/persistence later, secret access, LLM-provider construction, and serialization.

### Simulation

Owns all domain rules. It does not import web frameworks. Tests must be able to instantiate and run simulation components directly.

### Data

Excel trait workbooks are editable input/configuration. They are loaded through an explicit repository layer so spreadsheet layout is not coupled to behavioural code.

## Secret flow

```text
root .env
  -> backend settings
  -> DeepSeekProvider
```

No DeepSeek secret enters `NEXT_PUBLIC_*` or browser source.

## Product input evolution

Current:

```text
text pitch -> normalized HTTP request -> Product domain data
```

Later:

```text
photo/screenshot/PDF/DOCX
  -> validated upload
  -> extraction
  -> ProductKnowledge
  -> user review/correction
  -> simulation
```

This keeps multimodal ingestion separate from consumer dynamics.

## Simulation execution evolution

Initialization returns a preset preview.

Phase 1 runs a synchronous simulation in-process for manageable population sizes.

If profiling later shows that request duration is unsuitable, introduce a background job boundary:

```text
POST simulation -> job id -> worker -> checkpoints/results
```

Do not introduce Redis/queues before this is demonstrated as necessary.

## Large population UI

The backend may simulate thousands of agents, but the frontend should not automatically render every network edge. Use level-of-detail:

- small: most nodes and selected edges;
- standard: nodes + selective/active edges;
- large: cluster view by default, expand on zoom/selection.

## Conversation execution

Every consumer is stateful, but there is no permanent LLM instance per consumer.

```text
Agent A + Agent B + product knowledge + compact memories
   -> conversation router
   -> mathematical interaction OR shared LLM
   -> validated semantic evidence
   -> opinion aggregation
```

This controls cost and preserves deterministic domain rules.

## Reliability principles

- seeded randomness;
- immutable/frozen round snapshots in the full engine;
- structured LLM responses;
- fallback mathematical interactions;
- explicit state ranges;
- thin API handlers;
- regression tests for behavioural invariants;
- no synthetic-to-real prediction claims without validation.
