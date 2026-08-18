# ADR-006: Uncapped Full Live DeepSeek Uses In-Process Jobs

**Status:** Accepted locally  
**Date:** 2026-08-17

## Context

ModelCouncil already supports selective post-simulation DeepSeek transcript rendering. Those ordinary web runs deliberately cap live requests so a synchronous HTTP request cannot unexpectedly issue hundreds or thousands of model calls.

A new user-controlled mode is required: **Full Live DeepSeek**, where every conversation already scheduled by the deterministic simulator is rendered through DeepSeek. The scheduler must not change, but Small, Standard, and Large runs must be allowed without a hidden total-call cap after explicit user confirmation.

Keeping such work inside the existing synchronous `/simulations/run` request would make large runs fragile and would prevent useful progress/cancellation controls.

## Decision

Full Live DeepSeek uses a dedicated in-process asynchronous job path.

```text
confirmed Full Live request
        ↓
job record created
        ↓
deterministic simulation in worker thread
        ↓
exact scheduled ledger known
        ↓
all scheduled conversations attempted through DeepSeek
        ↓
bounded worker concurrency, no total-call cap
        ↓
progress/token/cache/cost telemetry
        ↓
normal SimulationRunResponse
```

The frontend uses four lifecycle endpoints:

- `POST /api/v1/simulations/full-live`
- `GET /api/v1/simulations/full-live/{job_id}`
- `GET /api/v1/simulations/full-live/{job_id}/result`
- `POST /api/v1/simulations/full-live/{job_id}/cancel`

The ordinary `/simulations/run` endpoint rejects `dialogue_mode=full_live`.

## Rendering invariants

- The normal scheduler remains authoritative.
- Full Live never creates additional conversations.
- Numerical state is committed before DeepSeek rendering begins.
- DeepSeek may change transcript wording only.
- Every scheduled conversation is attempted exactly once unless cancellation prevents it from being claimed.
- Per-conversation provider or validation failure falls back to deterministic language and does not fail the job.
- Billable invalid responses still contribute usage telemetry.
- The first configured cache-prime requests run serially; remaining work uses a fixed worker pool.
- Concurrency is a simultaneous-request limit, not a total-call limit.

## Safety and user control

The simulation UI displays an explicit warning before starting Full Live. It shows a conservative call upper bound based on current population size and rounds. Every Full Live run requires confirmation; upper bounds greater than 5,000 require typing `FULL LIVE` before the start action is enabled.

Cancellation is best-effort. It stops workers from claiming new conversations; already in-flight requests may finish and remain billable.

`DEEPSEEK_LIVE_ENABLED` remains a server-side prerequisite. The UI cannot enable it and the DeepSeek key is never returned to the browser or stored in a job record.

## Persistence decision

Jobs are stored in process memory for this phase. Restarting FastAPI loses running and completed Full Live job records. The progress UI states this explicitly.

Durable job execution belongs to the later persistence/background-job phase and will require a database/queue architecture rather than quietly expanding this in-memory manager.

## Alternatives considered

### Keep Full Live synchronous

Rejected. An uncapped Standard or Large run could keep one HTTP request open for a long time and offers poor cancellation/progress behavior.

### Browser-managed rendering batches

Rejected. It would move orchestration and recovery logic into the frontend, complicate security and make the browser responsible for a backend workload.

### Redis/Celery/external queue now

Deferred. This would provide durable execution but adds infrastructure before the project has reached its persistence phase. The in-process job abstraction establishes the API/state model without prematurely choosing queue infrastructure.

## Consequences

Positive:

- Full Live can attempt every scheduled conversation without weakening the normal safety cap.
- The browser receives real progress, cache, usage, latency and cost telemetry.
- Users can stop new model calls during a long run.
- The final response remains compatible with the existing Results dashboard.
- Future durable workers can replace the in-memory executor behind the same lifecycle API.

Negative:

- FastAPI restart loses job state.
- Horizontal multi-process deployment would require shared persistence before Full Live can be considered production-safe.
- A user who explicitly confirms a very large run can still incur substantial cost because the mode is intentionally uncapped.
