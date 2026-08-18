# ADR-008: Deterministic Product-Sensitive Simulation Dynamics

**Date:** 2026-08-17  
**Status:** Accepted for local Phase 2F implementation

## Context

Diagnostics showed that materially different product pitches at the same price were producing nearly identical numerical societies. Negative sentiment was often exactly zero before the first conversation. The cause was structural: baseline beliefs were driven mainly by generic consumer traits and a global price curve, conversation topics favored the strongest absolute beliefs, purchase intent was compressed, and topic analytics discarded stance direction.

The LLM layer was not responsible: DeepSeek/Ollama rendering occurs only after the numerical simulation commits its state.

## Decision

ModelCouncil keeps Python as the sole numerical authority and introduces a deterministic product-sensitive layer.

`ProductSemanticProfile` converts user-supplied category/pitch/features into explicit bounded synthetic signals for usefulness, quality, trust, novelty, privacy exposure, complexity, recurring cost, support/reliability, claim uncertainty, category family, and a coarse synthetic INR reference-price anchor.

`ConsumerProductFit` combines that immutable profile with each synthetic consumer to derive category-conditioned need, affordability, adoption fit, risk fit, privacy concern, and category-relative price pressure.

Baseline beliefs are centered around neutral and combine product evidence, consumer fit, consumer-specific correlated outlook, and bounded seeded variation. Favorable evidence can produce advocates; mismatch, high cost, poor reliability/support, privacy exposure, uncertainty, and low need can produce skeptics/negative segments. No negative quota is imposed.

Conversation topic selection uses all six topics and scores speaker salience, speaker/listener disagreement, listener relevance, and objection salience. Synchronous bounded aggregation remains intact, with modestly higher information value for credible moderate disagreement while extreme contradictions remain heavily discounted.

Purchase intent uses the same product fit throughout the run and applies explicit price, trust/risk-aversion, and privacy penalties.

Topic analytics retain total pressure for compatibility but add signed support, criticism, and net pressure. The dashboard's fifth chart renders criticism left of zero and support right of zero.

## Synthetic assumptions

The semantic lexicons, category-family mapping, reference-price anchors, and coefficients are explicit synthetic modeling assumptions. They are not empirical market estimates and do not verify claims in the user's pitch.

Positive and negative pitch language is treated as supplied product description/marketing information for hypothesis exploration only.

## Consequences

### Positive

- Different products under the same population/seed can now create materially different numerical states.
- Negative segments emerge when consumer-product mismatch warrants them instead of being structurally suppressed.
- Product need and price burden are product/category-specific rather than generic.
- Conversation semantics contain both support and criticism and discuss relevant disagreement topics.
- Purchase-intent bins have wider natural spread.
- Signed analytics stop hiding criticism behind absolute-value aggregation.
- All numerical behavior remains deterministic and testable without LLM providers.

### Trade-offs

- More explicit coefficients/lexicons must be maintained and documented.
- Category/keyword rules are intentionally coarse and can miss nuanced language.
- Synthetic reference-price anchors are assumptions, not current market prices.
- The system remains a hypothesis simulator, not a calibrated survey/forecast model.

## Invariants preserved

- DeepSeek/Ollama do not change numerical state.
- Round updates remain synchronous.
- KNN remains the candidate social-neighborhood mechanism.
- Belief updates remain bounded.
- No fixed sentiment quota exists.
- Same seed/input remains reproducible.
