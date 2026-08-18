from __future__ import annotations

import numpy as np

from simulation.population.trait_repository import TraitValue


def sample_weighted(values: tuple[TraitValue, ...], rng: np.random.Generator) -> TraitValue:
    if not values:
        raise ValueError("Cannot sample an empty trait category.")
    probabilities = np.asarray([item.probability for item in values], dtype=float)
    total = float(probabilities.sum())
    if total <= 0:
        raise ValueError("Trait category probabilities must sum to a positive value.")
    probabilities /= total
    return values[int(rng.choice(len(values), p=probabilities))]


def sample_with_soft_preference(
    values: tuple[TraitValue, ...],
    rng: np.random.Generator,
    *,
    preferred_key: str | None,
    preference_multiplier: float = 2.0,
) -> TraitValue:
    if not values:
        raise ValueError("Cannot sample an empty trait category.")
    if preference_multiplier <= 0:
        raise ValueError("preference_multiplier must be positive.")

    probabilities = np.asarray([item.probability for item in values], dtype=float)
    if preferred_key:
        for index, item in enumerate(values):
            if item.key == preferred_key:
                probabilities[index] *= preference_multiplier
                break
    total = float(probabilities.sum())
    if total <= 0:
        raise ValueError("Trait category probabilities must sum to a positive value.")
    probabilities /= total
    return values[int(rng.choice(len(values), p=probabilities))]


def sample_occupation_for_demographic(
    occupations: tuple[TraitValue, ...],
    demographic: TraitValue,
    rng: np.random.Generator,
) -> TraitValue:
    demographic_max = _int_attribute(demographic, "age_max", 120)
    eligible = tuple(
        occupation
        for occupation in occupations
        if _int_attribute(occupation, "min_age", 18) <= demographic_max
    )
    if not eligible:
        raise ValueError(
            f"No occupation is age-compatible with demographic profile {demographic.key!r}."
        )
    return sample_weighted(eligible, rng)


def _int_attribute(value: TraitValue, key: str, default: int) -> int:
    raw = value.attributes.get(key, default)
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default
