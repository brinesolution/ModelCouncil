# ADR-013 — Active Consumer Context and Life-Context Product Need

**Status:** Accepted / implemented locally  
**Date:** 2026-08-18

## Context

The 50-run ModelCouncil diagnostic showed that the Excel trait catalog was materially richer than the active numerical consumer. Population generation sampled only a subset of the available workbooks, demographic age ranges did not control generated age, five catalog categories were effectively inert, and generic `product_need` dominated need across unrelated products. In the controlled same-population test, average pairwise need correlation across unrelated categories was about 0.79. Students were not meaningfully more likely to need tutoring and business/technology workers were not meaningfully more likely to need B2B productivity software.

The generated population also contained near-proxy trait relationships: emotionality/logicality about -0.93, sociability/influence about +0.83, and stubbornness/risk tolerance about -0.74. These relationships reduced consumer multidimensionality.

## Decision

### 1. Keep established scalar AgentTraits, add nested active context

`ConsumerAgent` retains the existing `AgentTraits` fields for compatibility and gains a defaulted `ConsumerContext` containing:

```text
demographic
occupation
economic
decision
emotion
behaviour
technology
social
archetype_key
```

The nested context prevents dozens of additional workbook fields from being flattened into one undifferentiated trait structure. Existing direct `ConsumerAgent(...)` callers remain valid because every context has neutral defaults.

### 2. Demographics become causal

Population generation now samples a demographic profile. Occupation is sampled only from rows compatible with that demographic's maximum age. Generated age is sampled from:

```text
max(demographic.age_min, occupation.min_age)
..
demographic.age_max
```

The previous fixed maximum around age 55 is removed. The current catalog can therefore generate consumers into their 60s.

### 3. Archetypes are soft priors, not personas

An archetype may increase the probability of preferred personality/economic/social/technology/decision rows, but all enabled alternatives remain possible. This preserves diversity and honors the catalog's declaration that archetypes are priors rather than fixed personas.

### 4. Rich workbook fields have an explicit activation contract

`simulation/population/activation.py` classifies every loaded workbook attribute as:

```text
active
derived
provenance_only
```

A loaded field is never assumed to affect simulation merely because it exists in Excel. Tests fail if a newly loaded column has no activation declaration.

### 5. Existing compatibility rules are executable

The current declarative rule grammar supports conditions with `=`, `>`, `<` and effects:

```text
cap_max
floor_min
shift
```

Supported targets are mapped explicitly into `ConsumerAgent`, `AgentTraits`, state, or nested context. Invalid condition fields, targets, operators, or effects fail catalog validation. Applied rules are recorded per agent in the audit trace.

### 6. Product need is taxonomy/form + life-context specific

The old family-affinity formula is replaced by `assess_product_need()`. Generic `product_need` remains a modest general motivation prior, while known product forms use relevant context such as:

```text
education software   -> student/education occupation, research, evidence orientation, digital comfort
business SaaS        -> business/software/entrepreneur occupation, time pressure, convenience, digital comfort
meal planning        -> household context, time pressure, convenience
VPN/security         -> security preference, privacy concern, digital exposure
personal care/luxury -> luxury preference, status motivation, income, brand/quality orientation
electronics          -> form-specific technology, quality, income, convenience and household context
```

Every need assessment is deterministic and logs its named components.

### 7. Reduce near-proxy trait coupling

Derived logicality, influence power, and risk tolerance now blend multiple independently sampled active contexts and wider idiosyncratic variation. The goal is plausible association rather than statistical independence or near-determinism.

The fixed 5,000-agent calibration currently yields approximately:

```text
emotionality ↔ logicality       -0.62
sociability ↔ influence power   +0.45
stubbornness ↔ risk tolerance   -0.48
```

### 8. Decision/emotion context modifies purchase sensitivity modestly

Purchase intent keeps the established value/penalty structure. Centered multiplicative modifiers make price-oriented decision styles more sensitive to price downside, evidence/fear-sensitive consumers more sensitive to negative trust, and security/privacy-sensitive consumers more sensitive to negative privacy. With default context values of 0.5, every modifier equals 1.0, preserving legacy/default manual-agent behavior.

## Consequences

### Positive

- The demographics, archetypes, decision styles, emotions, compatibility rules, and richer workbook columns are now explicitly modeled rather than appearing active only in data files.
- Generated age follows demographic ranges and can include older consumers.
- Product need becomes meaningfully category/life-context dependent.
- The society supports more multidimensional trait combinations.
- Compatibility-rule effects and need components are fully auditable.
- Existing external agent construction remains source-compatible.

### Tradeoffs

- Population RNG sequence intentionally changes because additional profile categories are now sampled.
- Existing fixed-seed expected snapshots that encoded the old population algorithm must be updated only where the old behavior itself was the subject of the repair.
- Context formulas remain synthetic priors pending empirical calibration.
- Some workbook fields remain intentionally provenance-only; the activation manifest makes this explicit rather than silently pretending otherwise.

## Rejected alternatives

### Flatten every workbook column into AgentTraits

Rejected because it would make the domain model unwieldy, obscure provenance, and create naming/coupling problems.

### Force archetype preferred rows

Rejected because this would create rigid personas and lower diversity.

### Keep generic product_need and add larger random noise

Rejected because the observed problem was structural cross-category correlation, not insufficient stochastic variation.

### Make every Excel column active immediately

Rejected because fields should become causal only at an explicit model seam with tests and audit components.

## Verification contract

Phase 2J-B requires:

- backward-compatible consumer context tests;
- demographic age/range tests;
- soft-prior distribution/determinism tests;
- rich context activation tests;
- activation-manifest coverage for every loaded workbook column;
- compatibility-rule parser/execution/audit tests;
- same-population multi-category need correlation below 0.60;
- life-context ordering tests for tutoring, business SaaS, and meal planning;
- 5,000-agent trait-correlation guardrails;
- purchase-context directional tests;
- full Python suite, audit equivalence, and repository hygiene before Phase 2J-C begins.
