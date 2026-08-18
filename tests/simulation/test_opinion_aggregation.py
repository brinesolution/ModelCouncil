import pytest

from simulation.opinion.aggregator import TopicEvidence, aggregate_round_evidence
from simulation.population.generator import generate_population


def test_round_aggregation_is_not_conversation_order_dependent() -> None:
    first_agent = generate_population(1 + 1, seed=21)[0]
    second_agent = generate_population(1 + 1, seed=21)[0]
    first_agent.state.beliefs.price = -0.30
    second_agent.state.beliefs.price = -0.30

    positive = TopicEvidence(
        topic="price",
        stance=0.55,
        argument_strength=0.75,
        trust=0.70,
        relationship_strength=0.65,
        similarity=0.80,
        speaker_confidence=0.70,
        speaker_knowledge=0.60,
    )
    negative = TopicEvidence(
        topic="price",
        stance=-0.70,
        argument_strength=0.65,
        trust=0.60,
        relationship_strength=0.70,
        similarity=0.75,
        speaker_confidence=0.65,
        speaker_knowledge=0.55,
    )

    original_confidence = first_agent.state.confidence

    forward = aggregate_round_evidence(first_agent, [positive, negative], seed=99)
    reverse = aggregate_round_evidence(second_agent, [negative, positive], seed=99)

    assert forward.belief_updates["price"] == pytest.approx(reverse.belief_updates["price"])
    assert abs(forward.belief_updates["price"] - (-0.30)) <= 0.22
    assert first_agent.state.beliefs.price == -0.30
    assert first_agent.state.confidence == original_confidence


def _credible_evidence(*, stance: float, weak: bool = False) -> TopicEvidence:
    return TopicEvidence(
        topic="trust",
        stance=stance,
        argument_strength=0.90,
        trust=0.20 if weak else 0.85,
        relationship_strength=0.20 if weak else 0.80,
        similarity=0.15 if weak else 0.55,
        speaker_confidence=0.80,
        speaker_knowledge=0.75,
    )


def test_credible_moderate_disagreement_has_nontrivial_influence():
    agent = generate_population(2, seed=90)[0]
    agent.state.beliefs.trust = 0.30
    agent.traits.stubbornness = 0.70
    agent.state.confidence = 0.65

    result = aggregate_round_evidence(
        agent,
        [_credible_evidence(stance=-0.15)],
        noise_std=0.0,
        seed=7,
    )

    movement = abs(result.belief_updates["trust"] - 0.30)
    assert movement > 0.015
    assert movement <= 0.20


def test_extreme_contradiction_remains_more_bounded_than_moderate_disagreement():
    agent = generate_population(2, seed=90)[0]
    agent.state.beliefs.trust = 0.30
    agent.traits.stubbornness = 0.70
    agent.state.confidence = 0.65

    moderate = aggregate_round_evidence(
        agent,
        [_credible_evidence(stance=-0.15)],
        noise_std=0.0,
        seed=7,
    )
    extreme = aggregate_round_evidence(
        agent,
        [_credible_evidence(stance=-0.80)],
        noise_std=0.0,
        seed=7,
    )

    moderate_movement = abs(moderate.belief_updates["trust"] - 0.30)
    extreme_movement = abs(extreme.belief_updates["trust"] - 0.30)
    assert extreme_movement < moderate_movement


def test_weak_tie_can_still_produce_small_nonzero_information_update():
    agent = generate_population(2, seed=90)[0]
    agent.state.beliefs.trust = 0.30
    agent.traits.stubbornness = 0.70
    agent.state.confidence = 0.65

    result = aggregate_round_evidence(
        agent,
        [_credible_evidence(stance=-0.10, weak=True)],
        noise_std=0.0,
        seed=7,
    )

    movement = abs(result.belief_updates["trust"] - 0.30)
    assert 0.006 < movement < 0.05
