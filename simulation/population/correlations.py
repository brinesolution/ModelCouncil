from __future__ import annotations

import numpy as np


def clip01(value: float) -> float:
    return float(np.clip(value, 0.0, 1.0))


def jitter_normalized(rng: np.random.Generator, center: float, sigma: float = 0.08) -> float:
    return clip01(float(rng.normal(center, sigma)))


def correlated_price_sensitivity(
    rng: np.random.Generator,
    base_price_sensitivity: float,
    income_score: float,
) -> float:
    """Apply a modest income relationship without erasing the sampled economic profile."""
    income_adjustment = (income_score - 0.5) * 0.22
    return clip01(base_price_sensitivity - income_adjustment + rng.normal(0.0, 0.05))


def correlated_influence_power(
    rng: np.random.Generator,
    sociability: float,
    base_persuasion: float,
) -> float:
    center = 0.12 + 0.45 * sociability + 0.28 * base_persuasion
    return jitter_normalized(rng, center, sigma=0.06)


def correlated_logicality(
    rng: np.random.Generator,
    base_logicality: float,
    emotionality: float,
) -> float:
    center = 0.78 * base_logicality + 0.22 * (1.0 - emotionality)
    return jitter_normalized(rng, center, sigma=0.05)


def sample_income(
    rng: np.random.Generator,
    minimum: float,
    maximum: float,
    occupation_key: str,
) -> float:
    low = clip01(min(minimum, maximum))
    high = clip01(max(minimum, maximum))
    value = float(rng.uniform(low, high))
    if occupation_key == "student":
        value = min(value, 0.55)
    return clip01(value)
