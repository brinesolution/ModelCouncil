from simulation.analytics.dashboard import CANONICAL_TOPICS, build_dashboard_analytics
from simulation.engine import SimulationConfig, SimulationEngine
from simulation.population.generator import generate_population
from simulation.conversation.models import SemanticMessage
from simulation.product.knowledge import ProductKnowledge


def _result():
    population = generate_population(60, seed=91)
    product = ProductKnowledge(
        name="AI Fitness Coach",
        pitch="Personalized workouts, nutrition guidance, and progress tracking.",
        price=999,
        currency="INR",
    )
    return SimulationEngine().run(
        product=product,
        population=population,
        config=SimulationConfig(
            rounds=3,
            seed=91,
            k=6,
            max_conversations_per_agent=2,
            initiator_rate=0.25,
            weak_tie_rate=0.05,
        ),
    )


def test_purchase_intent_distribution_partitions_full_population():
    result = _result()

    analytics = build_dashboard_analytics(result)

    distribution = analytics.purchase_intent_distribution
    assert distribution.low + distribution.medium + distribution.high == len(result.population)
    assert distribution.low >= 0
    assert distribution.medium >= 0
    assert distribution.high >= 0


def test_topic_pressure_emits_all_canonical_topics_and_normalizes_scores():
    analytics = build_dashboard_analytics(_result())

    assert tuple(point.topic for point in analytics.topic_pressure) == CANONICAL_TOPICS
    assert all(point.raw_score >= 0 for point in analytics.topic_pressure)
    assert all(0.0 <= point.normalized_score <= 1.0 for point in analytics.topic_pressure)
    assert max(point.normalized_score for point in analytics.topic_pressure) <= 1.0


def test_topic_pressure_is_deterministic_for_same_result():
    result = _result()

    first = build_dashboard_analytics(result)
    second = build_dashboard_analytics(result)

    assert first == second


def test_topic_pressure_separates_support_criticism_and_net_direction():
    result = _result()
    for entry in result.conversations:
        entry.result.messages = []
    first = result.conversations[0]
    first.result.messages = [
        SemanticMessage(
            speaker_id=first.agent_a_id,
            listener_id=first.agent_b_id,
            topic_effects={"price": 0.40, "trust": -0.60},
            argument_strength=0.50,
            confidence=0.60,
        )
    ]

    analytics = build_dashboard_analytics(result)
    by_topic = {point.topic: point for point in analytics.topic_pressure}

    assert by_topic["price"].support_score == 0.20
    assert by_topic["price"].criticism_score == 0.0
    assert by_topic["price"].net_score == 0.20
    assert by_topic["trust"].support_score == 0.0
    assert by_topic["trust"].criticism_score == 0.30
    assert by_topic["trust"].net_score == -0.30
    assert by_topic["price"].raw_score == 0.20
    assert by_topic["trust"].raw_score == 0.30
    assert 0.0 <= by_topic["price"].normalized_support <= 1.0
    assert 0.0 <= by_topic["trust"].normalized_criticism <= 1.0
