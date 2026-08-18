from __future__ import annotations

import hashlib

import numpy as np

from simulation.domain.agent import ConsumerAgent, ProductBeliefs, clamp_opinion
from simulation.product.fit import ConsumerProductFit, consumer_product_fit
from simulation.product.knowledge import ProductKnowledge
from simulation.product.semantic_profile import (
    ProductSemanticProfile,
    build_product_semantic_profile,
)
from simulation.audit.logger import RunAuditSink


def evaluate_baseline(
    agent: ConsumerAgent,
    product: ProductKnowledge,
    seed: int,
    *,
    profile: ProductSemanticProfile | None = None,
    fit: ConsumerProductFit | None = None,
    audit: RunAuditSink | None = None,
) -> ProductBeliefs:
    """Create deterministic product-sensitive first-exposure beliefs."""
    resolved_profile = profile or build_product_semantic_profile(product, audit=audit)
    resolved_fit = fit or consumer_product_fit(
        agent,
        product,
        resolved_profile,
        seed=seed,
        audit=audit,
    )
    rng = np.random.default_rng(_mixed_seed(seed, agent.agent_id, product.name))
    consumer_outlook = _consumer_outlook(agent, resolved_fit)

    price_noise = float(rng.normal(0.0, 0.06))
    if resolved_fit.price_context is not None:
        price_components = {
            "price_context_stance": 0.92 * resolved_fit.price_context.stance,
            "affordability": 0.12 * (resolved_fit.affordability - 0.50),
            "noise": price_noise,
        }
    else:
        price_components = {
            "affordability": 0.85 * (resolved_fit.affordability - 0.50),
            "price_pressure": -0.80 * resolved_fit.price_pressure,
            "noise": price_noise,
        }
    price_raw = sum(price_components.values())
    price = _bounded(price_raw)

    usefulness_components = {
        "product_evidence": 0.58 * resolved_profile.usefulness_evidence,
        "need_fit": 0.92 * (resolved_fit.need - 0.50),
        "adoption_fit": 0.24 * (resolved_fit.adoption_fit - 0.50),
        "complexity_friction": -0.34
        * resolved_profile.complexity
        * (1.0 - agent.traits.technology_adoption),
        "consumer_outlook": 0.35 * consumer_outlook,
        "noise": float(rng.normal(0.0, 0.085)),
    }
    usefulness_raw = sum(usefulness_components.values())
    usefulness = _bounded(usefulness_raw)

    quality_components = {
        "quality_evidence": 0.64 * resolved_profile.quality_evidence,
        "support_reliability": 0.43 * resolved_profile.support_reliability,
        "logicality": 0.13 * (agent.traits.logicality - 0.50),
        "claim_uncertainty": -0.38 * resolved_profile.claim_uncertainty,
        "consumer_outlook": 0.75 * consumer_outlook,
        "noise": float(rng.normal(0.0, 0.085)),
    }
    quality_raw = sum(quality_components.values())
    quality = _bounded(quality_raw)

    trust_components = {
        "trust_evidence": 0.56 * resolved_profile.trust_evidence,
        "support_reliability": 0.34 * resolved_profile.support_reliability,
        "risk_fit": 0.22 * (resolved_fit.risk_fit - 0.50),
        "claim_uncertainty": -0.42 * resolved_profile.claim_uncertainty,
        "privacy_exposure": -0.38
        * resolved_profile.privacy_exposure
        * resolved_fit.privacy_concern,
        "consumer_outlook": 0.75 * consumer_outlook,
        "noise": float(rng.normal(0.0, 0.085)),
    }
    trust_raw = sum(trust_components.values())
    trust = _bounded(trust_raw)

    novelty_signal = resolved_profile.novelty_evidence
    novelty_components = {
        "novelty_adoption": 0.68
        * novelty_signal
        * (0.34 + 0.66 * agent.traits.technology_adoption),
        "complexity_friction": -0.24
        * resolved_profile.complexity
        * (1.0 - agent.traits.technology_adoption),
        "risk_friction": -0.16
        * novelty_signal
        * (1.0 - agent.traits.risk_tolerance),
        "consumer_outlook": 0.60 * consumer_outlook,
        "noise": float(rng.normal(0.0, 0.08)),
    }
    novelty_raw = sum(novelty_components.values())
    novelty = _bounded(novelty_raw)

    privacy_components = {
        "privacy_exposure": -0.92
        * resolved_profile.privacy_exposure
        * resolved_fit.privacy_concern,
        "trust_protection": 0.20
        * max(0.0, resolved_profile.trust_evidence)
        * (1.0 - resolved_profile.privacy_exposure),
        "consumer_outlook": 0.55 * consumer_outlook,
        "noise": float(rng.normal(0.0, 0.075)),
    }
    privacy_raw = sum(privacy_components.values())
    privacy = _bounded(privacy_raw)

    beliefs = ProductBeliefs(
        price=price,
        usefulness=usefulness,
        quality=quality,
        trust=trust,
        novelty=novelty,
        privacy=privacy,
    )
    if audit is not None:
        topic_data = {
            "price": ("baseline-price-v2h", price_components, price_raw, price),
            "usefulness": ("baseline-usefulness-v2h", usefulness_components, usefulness_raw, usefulness),
            "quality": ("baseline-quality-v2h", quality_components, quality_raw, quality),
            "trust": ("baseline-trust-v2h", trust_components, trust_raw, trust),
            "novelty": ("baseline-novelty-v2h", novelty_components, novelty_raw, novelty),
            "privacy": ("baseline-privacy-v2h", privacy_components, privacy_raw, privacy),
        }
        for topic, (version, components, raw_value, result) in topic_data.items():
            audit.emit(
                "baseline.topic_evaluation",
                {
                    "agent_id": agent.agent_id,
                    "topic": topic,
                    "formula_version": version,
                    "inputs": {
                        "consumer_outlook": consumer_outlook,
                        "profile": resolved_profile,
                        "fit": resolved_fit,
                    },
                    "components": components,
                    "raw_value": raw_value,
                    "result": result,
                },
                agent_ids=[agent.agent_id],
            )
        audit.emit(
            "baseline.completed",
            {"agent_id": agent.agent_id, "beliefs": beliefs},
            agent_ids=[agent.agent_id],
        )
    return beliefs


def _consumer_outlook(
    agent: ConsumerAgent,
    fit: ConsumerProductFit,
) -> float:
    return clamp_opinion(
        0.70 * (fit.need - 0.50)
        + 0.35 * (fit.adoption_fit - 0.50)
        + 0.30 * (fit.risk_fit - 0.50)
        + 0.25 * (fit.affordability - 0.50)
        - 0.25 * (agent.traits.price_sensitivity - 0.50)
    )


def _bounded(value: float) -> float:
    return clamp_opinion(float(value))


def _mixed_seed(seed: int, agent_id: int, product_name: str) -> int:
    digest = hashlib.blake2b(
        f"{seed}:{agent_id}:{product_name}".encode("utf-8"), digest_size=8
    ).digest()
    return int.from_bytes(digest, "big") % (2**32)
