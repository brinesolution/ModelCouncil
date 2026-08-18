# ADR-010 — Append-Only Run Audit Tracing

**Status:** Accepted / implemented locally  
**Date:** 2026-08-18

## Context

ModelCouncil simulations are intentionally deterministic at the numerical layer, but a complete run crosses several independently testable boundaries: Excel-backed trait loading, population sampling/correlations, deterministic product semantics, consumer-product fit, KNN formation, conversation scheduling, semantic dialogue, bounded-confidence aggregation, state commits, purchase intent, selective or Full Live language rendering, and provider HTTP I/O.

The Results UI intentionally shows summaries and a small diverse conversation replay. That is not enough to debug a numerical or language anomaly after the run has finished. Reconstructing the run post-hoc also loses rejected provider responses, validation failures, scheduler candidate choices, intermediate formula components, and partial state from failed/cancelled runs.

## Decision

Every actual backend simulation run creates a dedicated audit trace before numerical execution begins.

Canonical location:

```text
<project-root>/logs/model-runs/
```

Canonical filename stem:

```text
YYYY-MM-DD_HH-MM-SS-ffffff_DayName
```

Each run produces:

```text
<stem>.jsonl   canonical append-only event stream
<stem>.md      human-readable bounded summary/index
```

Preview-only requests do not create run files.

### Audit architecture

The framework-independent simulation package owns an optional `RunAuditSink` protocol. Production backend services create one `JsonlRunAuditLogger` and pass the same sink through population generation, simulation execution, post-simulation rendering, and provider I/O.

Implementations:

- `NullRunAuditLogger` — zero-output domain/default path;
- `MemoryRunAuditLogger` — ordered events for tests;
- `JsonlRunAuditLogger` — thread-safe, flushed, append-only runtime trace.

No global simulation logger is used. The audit dependency is explicit and observational.

### Event envelope

Every JSONL line is one valid JSON object containing:

- schema version `modelcouncil-run-audit-v1`;
- monotonically increasing per-run sequence;
- timezone-aware timestamp;
- event type;
- run ID;
- payload;
- optional round, conversation ID, agent IDs, and provider request ID.

The writer uses a lock around sequence assignment and file writes so concurrent Full Live workers cannot interleave JSON records.

### Numerical trace

The trace records, as applicable:

- safe run/product/configuration metadata;
- Excel workbook filename/category/schema/file hash and active source records;
- per-agent sampled Excel source keys, probabilities, attributes, generated traits and initial state;
- deterministic product semantic profile;
- consumer price-context, fit, baseline topic formula inputs/components/results;
- weighted KNN vectors and edge formation metadata;
- scheduler initiator/candidate/skip/selection details and score components;
- semantic topic-selection weights, semantic argument/noise calculations, deterministic fallback text and dialogue shape/style;
- every `TopicEvidence` object;
- bounded-confidence credibility/receptivity/distance/information/weight/target/delta components;
- state deltas and exact before/after committed state;
- purchase-intent value/penalty/logistic components;
- round boundary summaries.

Formula events use stable formula-version labels to aid comparisons across future model revisions.

### Provider trace

Language rendering records the semantic input, exact system/user prompts, requested JSON schema and accepted/fallback output.

DeepSeek and Ollama provider implementations record safe HTTP request/response information including:

- endpoint/method;
- sanitized headers;
- exact JSON request body;
- status code;
- visible response body;
- parsed assistant JSON;
- usage/model/latency;
- HTTP/validation/fallback errors.

Audit instrumentation must not alter the actual provider request payload.

### Security boundary

The audit system must never persist:

- API keys;
- Authorization/Bearer credentials;
- access/refresh tokens;
- passwords/client secrets/cookies;
- `.env` contents;
- private model chain-of-thought/hidden reasoning text.

Recursive key-name redaction is applied to every audit payload. DeepSeek additionally scrubs the exact configured API-key string from any visible provider response/error value in case a remote endpoint echoes that credential under a non-secret field name.

Provider fields such as `reasoning_content`, `chain_of_thought`, `hidden_reasoning`, and equivalent private-reasoning fields are replaced by `[OMITTED_PRIVATE_REASONING]`. Visible assistant answer content remains auditable.

Raw backend exception strings are not written to terminal run events because upstream exceptions can contain credentials. Persisted failures record safe error type/stage messages instead.

### Failure semantics

Audit-file creation is required for an actual backend run. If the canonical trace cannot be created, the run does not begin.

After run execution starts, an audit-write failure must not change numerical state or provider request content. The production logger enters degraded mode and stops attempting ordinary events if it can no longer safely persist the stream.

JSONL is flushed after each event, so a process crash can still leave a useful partial trace without a terminal event or Markdown summary.

### Full Live cancellation

The Full Live job manager keeps an internal reference to the run audit sink. A user cancellation request emits `run.cancel_requested`; terminal cancellation emits `run.cancelled`. Audit file paths are retained internally on the job record but are not currently added to the browser API contract.

## Consequences

### Positive

- Numerical anomalies can be traced to exact inputs/components rather than inferred from final charts.
- All semantic conversations remain inspectable even when only twelve are shown in Results.
- Provider prompt/response/fallback behavior is reproducible without enabling external request logging.
- Partial failed/cancelled runs remain diagnosable.
- Full Live concurrency does not corrupt the trace.
- Logger implementations can be replaced in tests without coupling the simulation engine to the filesystem.

### Costs

- Large and Full Live runs can produce large local JSONL files, especially because per-agent state/formula events are intentionally verbose.
- Product pitches and synthetic-agent state may be confidential even though credentials are redacted. The `logs/` tree remains local/untracked and should be handled accordingly.
- No retention/compression/indexing policy exists yet; users manually manage old traces.

## Verification requirements

Changes to the audit subsystem must preserve:

1. audit-on/audit-off numerical equivalence for the same seed and input;
2. identical DeepSeek/Ollama request payloads with tracing enabled/disabled;
3. valid one-object-per-line JSONL under concurrent writers;
4. credential and private-reasoning redaction;
5. complete per-round/per-conversation semantic coverage;
6. a bounded Markdown summary rather than a second copy of the raw stream.
