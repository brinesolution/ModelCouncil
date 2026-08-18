# ADR-012 — Stable Product Taxonomy and Contextual Semantic Evidence

**Status:** Accepted / implemented locally  
**Date:** 2026-08-18

## Context

The 50-run ModelCouncil diagnostic campaign showed that product sensitivity existed, but several incorrect outcomes originated before social simulation began. The previous semantic parser classified a product from one concatenated string containing category, pitch, and features. Incidental pitch words such as `app`, `subscription`, `security`, or `study` could therefore change the category family even when the explicit product category was unchanged. Because category family also selected consumer affinity and price references, this contaminated downstream need, price, beliefs, opinion, and purchase intent.

The same parser used exact phrase dictionaries with inconsistent normalization and no local contextual blocking. This caused failures such as `warranty exclusions` receiving a positive warranty signal, `no offline map export` receiving a positive offline signal, `works without a cloud subscription` receiving recurring-cost burden, and hyphenated `on-device` text failing to match an intended local-processing rule.

The diagnostic campaign also showed that rich problematic descriptions frequently collapsed to neutral semantic fields. Reliability, repairability/serviceability, safety, data practices, and cancellation friction were not represented explicitly enough to affect the existing six belief topics.

Finally, a single broad `consumer_electronics` reference price caused materially different forms such as power banks, earbuds, and robot vacuums to share one calibration anchor.

## Decision

### 1. Explicit category is authoritative

ModelCouncil now resolves a deterministic `ProductTaxonomy` containing:

```text
family
form
```

Recognized explicit categories resolve first. Product pitch/features may only provide fallback classification for unknown/general categories. A recognized category can no longer change family because the description happens to mention another domain.

Examples:

```text
Consumer Audio Electronics   -> consumer_electronics / audio_earbuds
Portable Electronics         -> consumer_electronics / portable_power_bank
Home Appliance Robotics      -> consumer_electronics / robot_vacuum
Smart Home Security          -> security_privacy / indoor_security_camera
Beauty and Personal Care     -> personal_care_luxury / beauty_device
Business Productivity SaaS   -> software_subscription / business_saas
```

### 2. Semantic matching uses one canonical normalization path

Source text and evidence phrases now share the same deterministic normalization:

```text
lowercase
punctuation / hyphens / underscores -> token boundaries
whitespace compaction
```

The contextual matcher evaluates local token windows and blocks normally positive phrases when directly negated or qualified, including `no`, `not`, `never`, `without`, `limited`, and nearby exclusion/unsupported/restriction wording. Clause boundaries prevent a negation attached to one statement from suppressing an unrelated later statement.

This is a deterministic bounded rule engine, not a general NLP parser and not an LLM call.

### 3. ProductSemanticProfile contains structured underlying risks

The public numerical belief topics remain unchanged:

```text
price
usefulness
quality
trust
novelty
privacy
```

The semantic profile now adds underlying bounded signals:

```text
reliability_risk
serviceability_risk
safety_risk
data_practice_risk
cancellation_friction
```

These signals feed the existing quality/trust/privacy and consumer risk-fit equations. They do not create a second opinion-state system.

Examples of recognized evidence include connection failures, inconsistent capacity, sealed/non-serviceable hardware, difficult returns, overheating/uncertified battery language, data logging/sharing/retention/deletion problems, and difficult cancellation/long commitment.

### 4. Product form selects the primary price reference

Price references are now data-like simulation calibration anchors at product-form granularity. A form-specific reference is used when available, with the historical family reference retained as fallback for unknown forms.

The anchors are simulation parameters, not claims of current retail market prices. They exist so clearly different product forms are not compared to the same broad-family amount.

### 5. Audit records the resolved interpretation

Product/price audit events record the resolved category family, product form, reference price, and whether the reference came from a form rule or family fallback. Audit remains observational and does not change the numerical result.

### 6. Private provider reasoning is outside the audit contract

The provider-private reasoning redaction set now also recognizes Ollama's `thinking` field. Visible `message.content` remains available for debugging while raw private reasoning is replaced before JSONL persistence.

## Consequences

### Positive

- Same explicit category is stable across favorable/premium/problematic descriptions.
- Product price context is less sensitive to unrelated pitch wording.
- Known negation/qualifier failures are regression-tested.
- Detailed reliability/safety/data/cancellation problems become causal numerical evidence.
- Existing six-topic opinion state remains intact.
- No model/provider call is required for deterministic product semantics.
- Product interpretation and price-reference provenance are auditable.

### Tradeoffs

- The taxonomy and semantic rule catalog are explicit calibration code/data and must be maintained as new product forms are added.
- Unknown categories still require descriptive fallback and therefore have less certainty than recognized categories.
- Form reference prices require future calibration if ModelCouncil targets a different market or currency context.
- A deterministic contextual matcher cannot understand arbitrary natural-language nuance; uncertain cases should remain conservative rather than inventing semantics.

## Rejected alternatives

### Let the LLM interpret product semantics

Rejected because numerical state must remain deterministic, replayable, provider-independent, and usable without external inference.

### Keep family inference from category + pitch but change rule ordering

Rejected because ordering cannot prevent future incidental-word collisions. Explicit category authority is the stable boundary.

### Fix only the sentiment threshold

Rejected because the diagnostic logs showed genuinely mis-scored products upstream. Changing the final positive/neutral/negative bins would hide rather than correct those causes.

### Use one electronics reference price and rely on income/price sensitivity

Rejected because the 50-run traces showed form-scale mismatch could overwhelm quality/safety evidence before consumer economics were applied.

## Verification contract

Phase 2J-A includes:

- nested Ollama private-reasoning redaction tests;
- twelve-family taxonomy stability tests;
- contextual normalization/negation regression tests;
- problematic product semantic-risk tests;
- form-reference price tests;
- twelve-family x three-severity semantic matrix;
- same-seed numerical comparisons for earbuds, cameras, and power banks;
- audit on/off equivalence tests;
- complete repository test/hygiene gate before Phase 2J-B begins.
