# ADR-014 — Evidence-Scaled Social Influence and Cross-Cutting Exposure

**Status:** Accepted / implemented locally  
**Date:** 2026-08-18

## Context

The 50-run forensic campaign showed that ModelCouncil's social layer was not literally frozen, but its causal social update was often approximately the same magnitude as a fixed stochastic term. Across roughly 3,300 topic updates, median raw social delta was about 0.0088 while median noise was about 0.0082; noise exceeded signal in roughly 46% of updates and reversed direction in roughly 23%. Privacy/trust/novelty were especially affected.

The network also remained highly homophilous. Weak ties existed in the graph but were systematically under-selected because they competed in the same similarity/relationship-weighted lottery as strong normal ties. Increasing configured weak ties therefore did not reliably produce proportional cross-cutting conversations.

## Decision

### 1. Social calibration is explicit and versioned

`InfluenceDynamicsConfig` owns the engine's social calibration parameters. The active configuration is emitted into the run audit trace.

Current locally verified defaults:

```text
version                         2j-c-1
max_topic_delta                 0.20
saturation_beta                 0.95
base_noise_std                  0.012
noise_floor                     0.001
max_noise_to_signal_ratio       0.35
weak_tie_exploration_weight     0.45
disagreement_information_weight 0.08
```

### 2. Noise is evidence-scaled

The stochastic interpretation term no longer uses a fixed standard deviation regardless of causal signal. Effective noise standard deviation is bounded by:

```text
min(base_noise_std,
    max(noise_floor,
        abs(raw_social_delta) * max_noise_to_signal_ratio))
```

If noise is explicitly disabled (`base_noise_std=0`), no random noise is added. Audit records effective noise standard deviation and the realized noise-to-signal ratio.

### 3. Social pressure was calibrated only after noise was fixed

With fixed noise removed, some historical movement disappeared because it had been stochastic. `saturation_beta` was therefore calibrated separately using the established mixed-product movement regression and the final scheduler.

Matched final-scheduler measurements:

```text
beta 0.75 -> mean |opinion movement| 0.00681
beta 0.85 ->                         0.00767
beta 0.95 ->                         0.00846
beta 1.05 ->                         0.00935
```

0.95 was selected as the smallest tested value that restored the existing measurable-movement gate. The corresponding negative share remained essentially unchanged, so this was not a sentiment-targeting calibration.

### 4. Weak ties have an explicit exploration path

Eligible weak ties no longer depend solely on winning the normal homophily-weighted candidate lottery. When eligible weak candidates exist, a bounded probability selects through a weak-exploration path; candidates within that path are still weighted by their existing relationship/trust/salience score. Capacity and cooldown constraints remain authoritative.

Audit records:

```text
eligible weak count
eligible normal count
selection path: normal | weak_exploration
selected weak_tie flag
```

### 5. Informational difference is a small scheduler component

Candidate scoring includes a modest bounded opinion-gap component. It increases the chance of informative contact but cannot overpower a substantially stronger trusted relationship. The model remains mostly homophilous with some cross-cutting exposure rather than forcing disagreement.

### 6. Population mean is not the sole social-dynamics metric

The engine now emits `social_dynamics.summary` containing:

```text
mean/median absolute opinion movement
upward/downward/unchanged counts
initial/final opinion standard deviation
mean contact opinion gap
selected weak-tie share
```

A society can therefore have a stable mean while agents move symmetrically.

## Consequences

### Positive

- Random noise is normally a minority of a meaningful causal update.
- Higher interaction exposure produces greater individual movement in matched runs.
- Weak-tie configuration creates measurable cross-cutting conversational exposure.
- Social diagnostics distinguish true stasis from symmetric movement.
- All calibration values and per-update noise components are auditable.
- Synchronous round semantics remain unchanged.

### Tradeoffs

- The final social trajectory for a fixed historical seed intentionally changes because contact selection and noise magnitude are repaired.
- Weak exploration can reduce average selected similarity; this is an intentional exposure tradeoff rather than a network-generation defect.
- Current coefficients are synthetic calibration parameters and should eventually be validated against empirical diffusion/consumer-behavior data.

## Rejected alternatives

### Restore fixed noise to meet historical movement thresholds

Rejected because the forensic data showed much of that movement was stochastic rather than conversational.

### Increase every influence coefficient simultaneously

Rejected because it would make root-cause calibration unidentifiable. The implemented sequence was noise first, pressure second, scheduler exposure third.

### Force a configured percentage of all conversations to be weak ties

Rejected because capacity, cooldown, and actual graph eligibility must still matter. The exploration path raises exposure without inventing nonexistent/blocked edges.

### Add automatic backfire/repulsion from distant beliefs

Rejected for this phase because such a mechanism requires its own behavioral evidence and model specification.

## Verification contract

Phase 2J-C includes:

- deterministic noise-scaling/statistical tests;
- weak-tie exposure tests;
- information-value anti-conflict tests;
- symmetric-movement diagnostics;
- six-run matched social matrix;
- legacy movement regression;
- integrated product ordering regression;
- complete Python suite.

Final Phase 2J-C gate: **330 passed, 1 existing Starlette/httpx deprecation warning**.
