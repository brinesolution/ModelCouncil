# ADR-002 — Persistent Agents, Shared LLM Conversation Service

**Status:** Accepted for initialization  
**Date:** 2026-08-17

## Decision

Every consumer is a persistent individual agent, but consumers do not own permanent LLM instances. Agent identity is stored as structured state and a shared provider service generates selected language interactions.

```text
Agent A state + Agent B state
        ↓
Shared LLM provider
        ↓
Transcript + semantic response
        ↓
Simulation influence rules
```

## Agent identity lives in

- traits;
- dynamic beliefs;
- confidence;
- knowledge;
- product salience;
- relationships;
- memory/history later;
- language/communication profile.

## Why

This preserves individuality without multiplying runtime/model cost by population size. It also allows deterministic/mock development and provider switching.

## Consequences

- LLM output is an input to the simulator, not the agent database;
- conversations can be generated selectively/batched;
- background interactions can remain mathematical;
- provider failures can fall back without destroying agent state;
- DeepSeek-specific code remains isolated under `simulation/llm/`.

## Rejected alternative

One permanent agent/LLM process per consumer is unnecessary, expensive, difficult to reproduce, and would make large populations operationally fragile.
