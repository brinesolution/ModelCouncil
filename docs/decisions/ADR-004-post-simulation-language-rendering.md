# ADR-004 — Post-Simulation Language Rendering

**Status:** Accepted locally for Phase 2  
**Date:** 2026-08-17

## Context

ModelCouncil needs visible natural-language conversations while preserving deterministic/reproducible social-state transitions. Calling an external LLM inside the round update loop would make simulation behavior vulnerable to provider latency, failure, nondeterministic wording, and API availability. It would also make state debugging and replay much harder.

## Decision

Natural-language LLM rendering occurs **after** the deterministic semantic simulation completes.

```text
frozen round state
    -> semantic conversation
    -> synchronous numerical aggregation
    -> committed simulation history
    -> importance ranking
    -> bounded optional LLM transcript rendering
    -> replay UI
```

The semantic conversation remains authoritative for:

- topics;
- stance/topic effects;
- argument strength;
- confidence;
- opinion updates;
- knowledge/salience changes;
- purchase intent.

The LLM may only replace the human-readable transcript associated with an already-computed semantic conversation.

## Conversation context

Each conversation ledger entry captures a compact participant language profile from the frozen start-of-round state. Post-simulation rendering uses this historical profile rather than final agent state.

## Cost/runtime policy

Dialogue modes control how many already-computed conversations are eligible for LLM transcript upgrades:

| Mode | Fraction | Synchronous maximum |
|---|---:|---:|
| Economy | 5% | 6 |
| Balanced | 20% | 20 |
| Full | 100% | 48 |

Every interaction still has deterministic background wording, so disabling or losing the provider never removes conversation visibility.

## Live-provider safety

A configured API key does not automatically enable paid requests. External rendering requires:

```text
DEEPSEEK_LIVE_ENABLED=true
```

The default is false. Tests additionally replace the provider factory with an offline mock/none path and never require a live API call.

## Failure behavior

Malformed output, wrong speaker order, missing utterances, excessive utterance size, HTTP errors, or provider exceptions fail closed to the deterministic transcript. Semantic messages are retained unchanged.

## Consequences

### Positive

- numerical simulation stays reproducible;
- state updates are independent from network/API latency;
- failed LLM calls cannot corrupt opinion dynamics;
- API cost is explicitly bounded;
- important conversations can receive richer wording without rendering every interaction;
- replay can explain historical conversations using the correct start-of-round context.

### Trade-offs

- the generated wording does not causally drive the already-computed state transition;
- language rendering happens after core simulation rather than as a truly interactive linguistic feedback loop;
- future research that intentionally studies linguistic content as a causal variable would require a separate, explicitly versioned simulation mode and ADR.

## Rejected alternatives

### One permanent LLM per consumer

Rejected because agent identity belongs in persistent structured state; permanent model sessions are unnecessary, expensive, and harder to reproduce.

### LLM inside every round interaction

Rejected for Phase 2 because it couples behavioral correctness to external generation and creates uncontrolled latency/cost.

### Generate transcripts only when clicked

Useful as a later optimization, but insufficient for the initial replay contract because selected conversations should be reproducibly stored with the run response.
