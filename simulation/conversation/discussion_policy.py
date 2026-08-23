from __future__ import annotations

import numpy as np

from simulation.domain.agent import ConsumerAgent


MIN_DISCUSSION_TURNS = 4
MAX_DISCUSSION_TURNS = 8


def discussion_turn_novelty(turn_index: int) -> float:
    if turn_index < 0:
        raise ValueError("turn_index cannot be negative")
    return max(0.45, 1.0 - 0.12 * turn_index)


def choose_discussion_turn_count(
    first: ConsumerAgent,
    second: ConsumerAgent,
    edge: dict[str, object],
    rng: np.random.Generator,
) -> int:
    """Choose a deterministic-seeded 4-8 turn discussion depth.

    Longer conversations become more likely when both consumers are engaged,
    sociable, confident, or materially disagree about the product. The caller
    owns the seeded RNG, so identical runs remain reproducible.
    """
    first_beliefs = first.state.beliefs.as_dict()
    second_beliefs = second.state.beliefs.as_dict()
    disagreement = sum(
        abs(first_beliefs[topic] - second_beliefs[topic]) / 2.0
        for topic in first_beliefs
    ) / max(1, len(first_beliefs))
    sociability = (first.traits.sociability + second.traits.sociability) / 2.0
    salience = (first.state.product_salience + second.state.product_salience) / 2.0
    confidence = (first.state.confidence + second.state.confidence) / 2.0
    relationship = float(edge.get("relationship_strength", 0.4))

    engagement = float(
        np.clip(
            0.24 * sociability
            + 0.24 * salience
            + 0.18 * confidence
            + 0.16 * relationship
            + 0.18 * min(1.0, disagreement * 2.2),
            0.0,
            1.0,
        )
    )

    extra_turns = 0
    for multiplier in (1.0, 0.82, 0.64, 0.46):
        if float(rng.random()) < engagement * multiplier:
            extra_turns += 1

    return min(MAX_DISCUSSION_TURNS, MIN_DISCUSSION_TURNS + extra_turns)
