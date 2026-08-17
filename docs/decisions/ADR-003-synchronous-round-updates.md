# ADR-003 — Synchronous Default Round Updates

**Status:** Accepted for initialization  
**Date:** 2026-08-17

## Decision

All conversations in round `t` read the same start-of-round agent state. Their effects are aggregated and committed once to form `S(t+1)`.

## Why

Sequential mutation makes simulation output depend on arbitrary iteration order and gives the last processed conversation implicit extra importance.

## Required flow

```text
snapshot S(t)
  -> all selected conversations
  -> evidence ledger
  -> topic aggregation
  -> one state delta
  -> commit S(t+1)
```

## Consequences

- conversation processing may be parallelized later more safely;
- debugging is easier because every round has a clear before/after boundary;
- multiple conflicting opinions can reduce confidence rather than overwrite each other;
- the full engine should use immutable snapshots/deltas.

## Future exception

Asynchronous opinion dynamics may be implemented as an explicit alternative experiment mode later. It must never be introduced accidentally through loop ordering.
