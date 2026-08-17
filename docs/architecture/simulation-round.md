# Simulation Round Specification v0.1

## Time

Default: one round represents five simulated minutes.

## Inputs

At the start of round `t` the engine has:

- immutable/frozen snapshot of all agent states `S(t)`;
- candidate social graph;
- product knowledge;
- active global events;
- experiment configuration;
- seed/random generator state.

## Round sequence

```text
1. Freeze S(t)
2. Update/measure product salience
3. Determine availability/capacity
4. Find eligible social edges
5. Apply pair cooldowns
6. Score candidate edges
7. Capacity-aware conversation matching
8. Route each selected pair
   - background mathematical interaction, or
   - LLM language interaction
9. Validate semantic messages/claims
10. Build influence ledger by listener/topic
11. Aggregate all evidence synchronously
12. Update topic beliefs
13. Update confidence/knowledge/trust/emotion as enabled
14. Derive overall opinion
15. Derive purchase intent
16. Apply memory/relationship changes
17. Commit S(t+1)
18. Calculate round analytics
19. Save checkpoint if configured
```

## Candidate network versus active interaction

`K` describes candidate neighbours. It never implies `K` conversations per round.

Current normal conversation capacity is two per agent per round.

## Pair selection

Before neighbour selection, the scheduler chooses a seeded weighted subset of potential initiators. The initialization default is 20% of the population per round, weighted by sociability and product salience. Other agents can still participate as recipients.

For an initiator, candidate neighbour scores are influenced by:

- similarity;
- relationship strength;
- product salience;
- sociability;
- later topic relevance/activity/event context;
- cooldown;
- small seeded random jitter.

Neighbour selection is probabilistic/weighted, not always nearest-neighbour-first.

## Synchronous state rule

All interactions read the same `S(t)` state. No conversation should permanently mutate another agent before the round aggregation stage.

This prevents code iteration order from acting like an invisible social rule.

The initialization aggregator is already pure: it returns `RoundAggregation(belief_updates, confidence_delta)` without mutating the input agent. When the full round engine is implemented, this should be promoted into a complete `AgentStateDelta` and committed in a separate end-of-round stage.

## Topic evidence

Each listener receives evidence per topic.

Example:

```text
price:
  stance = -0.40
  argument_strength = 0.65
  trust = 0.70
  relationship = 0.55
  similarity = 0.80
  speaker_confidence = 0.60
  speaker_knowledge = 0.50
  novelty = 1.00
```

## Credibility and receptivity

Initial credibility combines source trust, relationship, speaker confidence/knowledge, and similarity.

Listener receptivity depends primarily on stubbornness and confidence in the initialization model.

These coefficients are model assumptions and should eventually be configuration/versioned parameters.

## Bounded confidence

Incoming stances far outside the listener's acceptance range receive little influence rather than being averaged blindly.

Reactance/backfire is not part of the first implementation.

## Saturation

Total social pressure uses a saturating function so influence has diminishing returns as more evidence arrives.

Repeated arguments should later split into two mechanisms:

- argument novelty decreases;
- social proof may still increase.

## Conflicting evidence

If credible neighbours disagree strongly, the listener may:

- move only slightly;
- lose confidence;
- remain undecided;
- change one topic belief without changing purchase intent.

## State ranges

```text
belief/opinion: -1 .. +1
confidence:      0 .. 1
knowledge:       0 .. 1
salience:        0 .. 1
purchase intent: 0 .. 1
traits:          0 .. 1 unless explicitly categorical
```

Every commit must clamp/validate legal ranges.

## Purchase intent

Purchase intent is recomputed after belief/opinion changes. It is not directly copied from a conversation's sentiment.

## Conversation transcript

A visible transcript and the semantic state effect are related but separate records.

An LLM-generated transcript must not be considered authoritative state. The semantic payload is validated and passed through domain influence rules.

## Failure behavior

If language generation fails:

1. retry only when a bounded retry policy exists;
2. otherwise use mathematical/background interaction;
3. record that fallback occurred;
4. do not fail the full simulation merely because one conversation failed.

## Debug ledger

Development mode should be able to preserve:

```text
agent id
round
before state
incoming evidence
weights
bounded-confidence factors
aggregate targets
state delta
after state
```

This is essential for diagnosing emergent behaviour.
