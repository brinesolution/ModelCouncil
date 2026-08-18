from __future__ import annotations

import math

from simulation.domain.agent import ConsumerAgent, clamp01, clamp_opinion
from simulation.product.fit import ConsumerProductFit
from simulation.audit.logger import RunAuditSink

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


def derive_purchase_intent(
    agent: ConsumerAgent,
    *,
    fit: ConsumerProductFit | None = None,
    audit: RunAuditSink | None = None,
    round_index: int | None = None,
    phase: str | None = None,
) -> float:
    beliefs = agent.state.beliefs
    opinion = derive_overall_opinion(agent)
    resolved = fit or _fallback_fit(agent)

    value_components = {
        "need": 0.30 * resolved.need,
        "usefulness": 0.18 * _unit(beliefs.usefulness),
        "quality": 0.12 * _unit(beliefs.quality),
        "trust": 0.12 * _unit(beliefs.trust),
        "overall_opinion": 0.08 * _unit(opinion),
        "affordability": 0.10 * resolved.affordability,
        "income": 0.10 * agent.income_score,
    }
    value_signal = sum(value_components.values())

    price_weight_factor = 0.75 + 0.50 * agent.context.decision.price_weight
    trust_context_factor = (
        0.75
        + 0.35 * agent.context.decision.evidence_requirement
        + 0.15 * agent.context.emotion.fear_sensitivity
    )
    privacy_context_factor = (
        0.70
        + 0.30 * agent.context.emotion.security_preference
        + 0.30 * agent.context.technology.privacy_concern
    )
    modifiers = {
        "price_weight_factor": price_weight_factor,
        "trust_context_factor": trust_context_factor,
        "privacy_context_factor": privacy_context_factor,
    }

    price_penalty_components = {
        "price_pressure": price_weight_factor * 0.38 * resolved.price_pressure,
        "negative_price_belief": price_weight_factor
        * 0.24
        * agent.traits.price_sensitivity
        * max(0.0, -beliefs.price),
    }
    price_penalty = sum(price_penalty_components.values())
    trust_penalty_components = {
        "risk_aversion_negative_trust": trust_context_factor
        * 0.35
        * (1.0 - agent.traits.risk_tolerance)
        * max(0.0, -beliefs.trust)
    }
    trust_penalty = sum(trust_penalty_components.values())
    privacy_penalty_components = {
        "privacy_concern_negative_privacy": privacy_context_factor
        * 0.26
        * resolved.privacy_concern
        * max(0.0, -beliefs.privacy)
    }
    privacy_penalty = sum(privacy_penalty_components.values())

    z = (
        5.4 * (value_signal - 0.50)
        - 2.4 * price_penalty
        - 2.0 * trust_penalty
        - 1.5 * privacy_penalty
    )
    probability = 1.0 / (1.0 + math.exp(-z))

    agent.state.overall_opinion = opinion
    agent.state.purchase_intent = clamp01(probability)
    if audit is not None:
        audit.emit(
            "purchase.evaluation",
            {
                "formula_version": "purchase-intent-v2h",
                "agent_id": agent.agent_id,
                "phase": phase,
                "beliefs": beliefs,
                "fit": resolved,
                "components": {
                    "value_signal": value_components,
                    "price_penalty": price_penalty_components,
                    "trust_penalty": trust_penalty_components,
                    "privacy_penalty": privacy_penalty_components,
                },
                "modifiers": modifiers,
                "value_signal": value_signal,
                "price_penalty": price_penalty,
                "trust_penalty": trust_penalty,
                "privacy_penalty": privacy_penalty,
                "z": z,
                "result": agent.state.purchase_intent,
            },
            round_index=round_index,
            agent_ids=[agent.agent_id],
        )
    return agent.state.purchase_intent


def _fallback_fit(agent: ConsumerAgent) -> ConsumerProductFit:
    privacy_concern = clamp01(
        0.65 * (1.0 - agent.traits.risk_tolerance)
        + 0.35 * agent.traits.logicality
    )
    affordability = clamp01(
        0.60 * agent.income_score
        + 0.40 * (1.0 - agent.traits.price_sensitivity)
    )
    return ConsumerProductFit(
        need=agent.traits.product_need,
        affordability=affordability,
        adoption_fit=agent.traits.technology_adoption,
        risk_fit=agent.traits.risk_tolerance,
        privacy_concern=privacy_concern,
        price_pressure=clamp01(
            agent.traits.price_sensitivity
            * max(0.0, -agent.state.beliefs.price)
        ),
    )


def _unit(opinion: float) -> float:
    return clamp01((clamp_opinion(opinion) + 1.0) / 2.0)
