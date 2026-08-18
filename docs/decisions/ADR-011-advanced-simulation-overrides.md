# ADR-011 — Preset-Based Advanced Simulation Overrides

**Date:** 2026-08-18  
**Status:** Accepted / implemented locally

## Context

ModelCouncil's Small, Standard, and Large presets are intentionally simple and safe for normal product experiments, but they make iterative debugging expensive because population size, K, conversation capacity, initiator rate, weak-tie rate, and simulated round duration are fixed. Testing Full Live providers, audit traces, conversation behavior, and backend/UI changes often needs a 20–100 agent run for only a few rounds.

A frontend-only unlock would be unsafe because the browser could display one configuration while FastAPI, Full Live estimates, the deterministic engine, and Phase 2H audit traces still use registered preset values. Replacing presets entirely with custom values would also weaken the default user workflow.

## Decision

Keep `small | standard | large` as the only population modes and add an optional `advanced_config` request object. The selected named preset remains the default configuration and the template used when Advanced controls are enabled.

FastAPI resolves exactly one effective `PopulationPreset` through `backend/app/services/simulation_config_service.py`. Preview, ordinary simulation, Full Live upper-bound estimates, population generation, `SimulationConfig`, Results metadata, and audit logging all consume that resolved configuration.

When `advanced_config` is absent, the existing registered preset is returned unchanged. When present, the resolver creates a run-local `PopulationPreset` containing the supplied numerical values; lower simulation layers do not branch on whether those values came from a preset or an override.

## Validation and workload guard

Advanced values remain bounded by server-side operational safety limits:

```text
population_size                 2 .. 5,000
base_k                          1 .. 128 and < population_size
max_conversations_per_round     1 .. 8
initiator_rate                  0.0 .. 1.0
weak_tie_rate                   0.0 .. 1.0
simulated_minutes_per_round     1 .. 1,440
rounds                          1 .. 100
seed                            0 .. 2,147,483,647
```

These are runtime safety controls, not empirical model limits.

The authoritative conservative workload formula is:

```text
per_round_upper_bound = floor(population_size * max_conversations_per_round / 2)
run_upper_bound = per_round_upper_bound * rounds
```

A request is rejected when `run_upper_bound > 100,000`.

Preset-specific round caps remain when Advanced is off:

```text
Small       100
Standard     50
Large        20
```

Advanced mode may use up to 100 rounds when the workload guard is satisfied.

## UI behavior

Dialogue mode remains the primary language/rendering control and is independent of Advanced numerical configuration.

The Simulation form exposes an opt-in **Advanced simulation controls** switch. Turning it on copies the selected preset values into editable controls. Changing the named preset while Advanced is active reloads that preset's numerical defaults as a new template. Turning Advanced off returns execution/display to the named preset; active override values are no longer sent.

The browser validates custom values for immediate feedback, but backend validation remains authoritative. Invalid custom values are surfaced rather than silently clamped on submission.

The Run Console displays effective values and explicitly labels the configuration as `PRESET` or `ADVANCED`.

## Full Live

Full Live confirmation and job metadata use the same shared conservative upper bound from the effective configuration. This replaces the previous frontend approximation based only on population size × rounds.

Provider/model selection, semantic-state ownership, render concurrency, cancellation, and all-scheduled-conversation behavior are unchanged.

## Audit and reproducibility

Phase 2H `run.configuration` records:

```text
advanced_config_enabled
population_mode
rounds
seed
effective_preset
workload_upper_bound
```

This preserves enough numerical configuration to reproduce a run if registered preset defaults change later.

Advanced configuration is not a second simulation engine. Same product, seed, and exact effective numerical configuration must reproduce the same deterministic numerical result whether those values originated from a registered preset or equivalent Advanced overrides.

## Consequences

### Positive

- very small, fast debugging runs are first-class without weakening normal defaults;
- one backend resolver prevents preview/run/Full Live/audit disagreement;
- existing clients that omit `advanced_config` remain compatible;
- Full Live warnings use a more accurate bound;
- audit traces contain exact effective runtime values;
- simulation mathematics remain independent of UI configuration source.

### Trade-offs

- the Simulation form has a larger secondary control surface;
- custom configurations can still be computationally expensive up to the hard workload ceiling;
- presets and frontend preset metadata must remain synchronized with backend defaults;
- Advanced values are not persisted as named custom presets in this phase.

## Rejected alternatives

### Frontend-only unlock

Rejected because displayed settings could diverge from backend/runtime behavior and safety validation.

### Replace Small/Standard/Large with fully custom configuration

Rejected because presets are useful safe defaults and existing API/UI compatibility depends on them.

### Add a fourth `custom` population mode

Rejected because it would introduce unnecessary branching in analytics/results and duplicate the role of the optional override object.
