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
