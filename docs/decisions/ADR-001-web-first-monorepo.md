# ADR-001 — Web-First Distributed Monorepo

**Status:** Accepted for initialization  
**Date:** 2026-08-17

## Decision

ModelCouncil begins with a web surface from the first implementation round, while preserving a framework-independent Python simulation package.

Repository boundaries:

```text
frontend/   Next.js
backend/    FastAPI
simulation/ domain engine
data/       traits/generated artifacts
tests/      executable contracts
docs/       architecture/decisions
```

## Why

A notebook-only start would make later map/conversation visualization and product input flows a migration task. Putting simulation math directly in FastAPI would make research/testing difficult. The monorepo keeps one project history while maintaining clean boundaries.

## Consequences

- every meaningful feature can eventually be exposed in the browser;
- simulation remains independently testable;
- frontend/backend contracts must be explicit;
- setup has both Python and Node dependencies;
- deployment can split frontend/backend without splitting repositories.

## Rejected alternatives

### Single Python/Streamlit application

Faster prototype but weaker long-term control over complex graph UI, replay, and app architecture.

### Next.js-only application

Would place numerical/ML simulation in an unsuitable primary runtime or require hidden server complexity.

### Multiple repositories

Unnecessary operational overhead for the current solo/portfolio phase.
