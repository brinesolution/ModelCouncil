from __future__ import annotations

import hashlib

import numpy as np

from simulation.domain.agent import ConsumerAgent, ProductBeliefs, clamp_opinion
from simulation.product.knowledge import ProductKnowledge


def evaluate_baseline(
    agent: ConsumerAgent,
    product: ProductKnowledge,
    seed: int,
) -> ProductBeliefs:
    """Create interpretable first-exposure beliefs for one consumer.

    The seed is mixed with agent identity so results are reproducible without giving
    every consumer identical noise. The function is pure and does not mutate agent.
    """
    rng = np.random.default_rng(_mixed_seed(seed, agent.agent_id, product.name))
    need = agent.traits.product_need
    tech = agent.traits.technology_adoption
    risk = agent.traits.risk_tolerance
    price_sensitivity = agent.traits.price_sensitivity
    income = agent.income_score

    price_pressure = _price_pressure(product.price)
    affordability = 0.55 * income + 0.45 * (1.0 - price_sensitivity)
    price = _bounded(
        0.75 * affordability - 0.70 * price_pressure * price_sensitivity + rng.normal(0, 0.05)
    )
    usefulness = _bounded(-0.30 + 1.25 * need + 0.18 * tech + rng.normal(0, 0.05))
    quality = _bounded(0.10 + 0.32 * need + 0.18 * agent.traits.logicality + rng.normal(0, 0.06))
    trust = _bounded(
        -0.05
        + 0.24 * tech
        + 0.18 * agent.traits.logicality
        - 0.16 * (1.0 - risk)
        + rng.normal(0, 0.06)
    )
    novelty = _bounded(-0.10 + 0.72 * tech + 0.28 * risk + rng.normal(0, 0.06))
    privacy = _bounded(0.12 * tech - 0.28 * (1.0 - risk) + rng.normal(0, 0.06))

    return ProductBeliefs(
        price=price,
        usefulness=usefulness,
        quality=quality,
        trust=trust,
        novelty=novelty,
        privacy=privacy,
    )


def _price_pressure(price: float | None) -> float:
    if price is None or price <= 0:
        return 0.0
    # Smoothly maps common INR subscription / consumer-product prices into 0..1.
    return float(np.clip(np.log1p(price) / np.log1p(5000.0), 0.0, 1.0))


def _bounded(value: float) -> float:
    return clamp_opinion(float(value))


def _mixed_seed(seed: int, agent_id: int, product_name: str) -> int:
    digest = hashlib.blake2b(
        f"{seed}:{agent_id}:{product_name}".encode("utf-8"), digest_size=8
    ).digest()
    return int.from_bytes(digest, "big") % (2**32)
