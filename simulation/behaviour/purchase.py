from __future__ import annotations

import math

from simulation.domain.agent import ConsumerAgent, clamp01, clamp_opinion

BELIEF_IMPORTANCE = {
    "price": 0.20,
    "usefulness": 0.24,
    "quality": 0.18,
    "trust": 0.18,
    "novelty": 0.10,
    "privacy": 0.10,
}


def derive_overall_opinion(agent: ConsumerAgent) -> float:
    beliefs = agent.state.beliefs.as_dict()
    weighted = sum(BELIEF_IMPORTANCE[name] * beliefs[name] for name in BELIEF_IMPORTANCE)
    return clamp_opinion(weighted)


def derive_purchase_intent(agent: ConsumerAgent) -> float:
    beliefs = agent.state.beliefs
    opinion = derive_overall_opinion(agent)

    value_signal = (
        0.28 * agent.traits.product_need
        + 0.20 * ((beliefs.usefulness + 1.0) / 2.0)
        + 0.12 * ((beliefs.quality + 1.0) / 2.0)
        + 0.12 * ((beliefs.trust + 1.0) / 2.0)
        + 0.10 * ((opinion + 1.0) / 2.0)
        + 0.08 * agent.income_score
        + 0.10 * (1.0 - agent.traits.risk_tolerance * max(0.0, -beliefs.trust))
    )

    price_resistance = agent.traits.price_sensitivity * max(0.0, -beliefs.price)
    z = 4.2 * (value_signal - 0.52) - 2.0 * price_resistance
    probability = 1.0 / (1.0 + math.exp(-z))

    agent.state.overall_opinion = opinion
    agent.state.purchase_intent = clamp01(probability)
    return agent.state.purchase_intent
