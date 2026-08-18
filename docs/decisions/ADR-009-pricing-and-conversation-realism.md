# ADR-009: Billing-Aware Pricing and Conversation Realism

**Date:** 2026-08-17  
**Status:** Accepted for local Phase 2G implementation

## Context

Phase 2F made numerical product state sensitive to pitch/category semantics, but one important pricing artifact remained. The semantic profile treated a recurring subscription as a strong generic burden while price amount used one broad category anchor. In the observed AI-fitness case, ₹200/month, ₹499/month, and ₹999/month all produced nearly the same strongly negative price belief. Language renderers then correctly verbalized that bad semantic input as repeated variants of “₹200 is steep.”

The conversation surface also amplified the problem: concise two-line rendering, demographic labels such as `Student`, raw high-intensity replay ranking, and a small deterministic fallback template set encouraged repetitive objections and unsupported comparisons.

## Decision

### Billing cadence is first-class product state

Product input carries one of:

- `auto`
- `one_time`
- `monthly`
- `yearly`

Auto resolution is deterministic. Explicit non-recurring phrases such as `no subscription` take precedence over the substring `subscription`. Manual override always wins.

### Category × cadence anchors are synthetic priors

Price comparison uses category-family and resolved billing cadence. These anchors are simulator calibration assumptions only; they must never be presented as observed market averages or verified prices.

For example, the local fitness/wellness monthly anchor is deliberately different from the one-time fitness/wellness anchor so ₹1,500 one-time and ₹1,500/month do not mean the same thing.

### ConsumerPriceContext is the price authority

Each consumer receives a deterministic `ConsumerPriceContext` containing:

- resolved cadence;
- category/cadence reference ratio;
- qualitative position (`inexpensive`, `typical`, `premium`, `expensive`);
- affordability;
- price pressure;
- current price stance and stance band.

Amount/reference ratio provides the population baseline. Income, price sensitivity, and need are centered individual modifiers. Occupation, age, student status, locale, and other demographic labels are excluded from numerical affordability.

Affordability/pressure remain stable economic context. Dialogue-facing stance is refreshed from the agent's current Python price belief each round so social belief changes cannot conflict with stale round-0 language context.

### Personality affects expression, not facts

`SpeakingStyle` derives from normalized logicality, emotionality, sociability, stubbornness, and confidence. `DialogueShape` derives from already-fixed semantic turns. Neither may change topic effects or numerical state.

The LLM renderer explicitly forbids:

- inferring affordability from occupation, age, or student status;
- inventing competitor prices or products;
- claiming free alternatives exist;
- inventing gym prices, market averages, reviews, adoption statistics, or unsupported product facts.

Most rendered utterances should be one or two sentences; complex/important turns may use up to three. Length must not be padded with filler.

### Topic memory is soft and round-bounded

Recent topic history applies a modest repetition penalty. It never blacklists a genuinely dominant topic. Only completed prior-round history affects the next round, preserving same-round snapshot semantics.

### Replay selection is diversity-aware and display-only

The 12-card replay surface uses a deterministic selector starting from importance and adding bounded bonuses/penalties for topic, stance direction, round, and weak-tie diversity. This does not change simulation history, ordinary LLM selection, or Full Live rendering.

## Consequences

### Positive

- Low monthly amounts no longer collapse with much higher monthly prices.
- Monthly and one-time amounts can have different economic meaning.
- Explicit economic traits create legitimate price disagreement without occupation stereotypes.
- DeepSeek/Ollama receive the same Python-owned price interpretation that drove numerical state.
- Deterministic fallback and LLM rendering share stance/style/shape semantics.
- Replay better represents the ledger instead of overexposing one intense topic.

### Trade-offs

- Synthetic category/cadence anchors require explicit maintenance and future calibration if empirical data becomes available.
- Auto billing inference is intentionally conservative and may require user override for ambiguous pitches.
- More language context slightly increases prompt size and token use for live rendering.
- Replay order is no longer identical to raw importance order because the UI sample has a diversity objective.

## Invariants

1. Python remains the sole numerical authority.
2. LLM wording never changes semantic messages or state.
3. Billing/price anchors are synthetic priors, not market facts.
4. Demographic labels cannot determine numerical affordability.
5. Current semantic price stance overrides stale initial wording stance.
6. Same input and seed remain deterministic for numerical state and deterministic fallback.
7. Full Live still attempts every scheduled conversation; replay diversity never changes Full Live coverage.
