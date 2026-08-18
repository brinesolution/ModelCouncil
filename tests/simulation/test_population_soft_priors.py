from collections import Counter

import numpy as np

from simulation.population.sampling import sample_with_soft_preference
from simulation.population.trait_repository import TraitValue


def _values():
    return (
        TraitValue("a", "A", 1 / 3, {}),
        TraitValue("b", "B", 1 / 3, {}),
        TraitValue("c", "C", 1 / 3, {}),
    )


def test_soft_preference_biases_selection_without_forcing_a_persona():
    rng = np.random.default_rng(42)
    counts = Counter(
        sample_with_soft_preference(
            _values(),
            rng,
            preferred_key="b",
            preference_multiplier=2.0,
        ).key
        for _ in range(4000)
    )

    assert counts["b"] > counts["a"]
    assert counts["b"] > counts["c"]
    assert counts["a"] > 0
    assert counts["c"] > 0


def test_soft_preference_is_seed_deterministic():
    first_rng = np.random.default_rng(91)
    second_rng = np.random.default_rng(91)

    first = [
        sample_with_soft_preference(_values(), first_rng, preferred_key="c").key
        for _ in range(100)
    ]
    second = [
        sample_with_soft_preference(_values(), second_rng, preferred_key="c").key
        for _ in range(100)
    ]

    assert first == second


def test_missing_preference_falls_back_to_base_weights():
    rng = np.random.default_rng(10)
    selected = [
        sample_with_soft_preference(_values(), rng, preferred_key="missing").key
        for _ in range(100)
    ]

    assert set(selected) == {"a", "b", "c"}
