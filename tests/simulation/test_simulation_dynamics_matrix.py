from collections import Counter

from simulation.engine import SimulationConfig, SimulationEngine
from simulation.population.generator import generate_population
from simulation.product.knowledge import ProductKnowledge


def _run(*, pitch: str, category: str, price: float, seed: int = 1579, size: int = 360):
    population = generate_population(size, seed=seed)
    product = ProductKnowledge(
        name="Dynamics Scenario",
        category=category,
        pitch=pitch,
        price=price,
        currency="INR",
    )
    return SimulationEngine().run(
        product,
        population,
        SimulationConfig(
            rounds=20,
            seed=seed,
            k=12,
            max_conversations_per_agent=2,
            initiator_rate=0.20,
            weak_tie_rate=0.05,
        ),
    )


GOOD_PITCH = (
    "A useful reliable durable device with responsive customer support, warranty coverage, "
    "transparent pricing, and proven convenience."
)
BAD_PITCH = (
    "An unnecessary unreliable fragile device with frequent failures, poor support, hidden fees, "
    "misleading claims, and little value."
)
MIXED_PITCH = (
    "An AI-powered fitness coach with personalized workout guidance and progress tracking for a "
    "monthly subscription, requiring an account and cloud health data storage."
)


def test_controlled_bad_product_can_generate_meaningful_negative_segment_without_forcing_good_product_negative():
    good = _run(pitch=GOOD_PITCH, category="Consumer Electronics", price=3499)
    bad = _run(pitch=BAD_PITCH, category="Consumer Electronics", price=3499)

    assert bad.timeline[-1].negative_share >= 0.25
    assert bad.timeline[-1].mean_opinion < -0.20
    assert good.timeline[-1].mean_opinion > 0.20
    assert good.timeline[-1].negative_share < 0.05


def test_realistic_mixed_product_contains_both_advocates_and_skeptics():
    result = _run(
        pitch=MIXED_PITCH,
        category="Fitness Technology",
        price=999,
    )
    final = result.timeline[-1]

    assert final.positive_share >= 0.01
    assert final.negative_share >= 0.01
    assert final.neutral_share < 0.98


def test_conversations_include_both_support_and_criticism_across_many_topics():
    result = _run(
        pitch=MIXED_PITCH,
        category="Fitness Technology",
        price=999,
    )
    signs = Counter()
    topics = Counter()
    for entry in result.conversations:
        for message in entry.result.messages:
            for topic, stance in message.topic_effects.items():
                topics[topic] += 1
                signs["positive" if stance > 0.05 else "negative" if stance < -0.05 else "neutral"] += 1

    total_signed = signs["positive"] + signs["negative"]
    assert len(topics) >= 5
    assert signs["positive"] > 0
    assert signs["negative"] > 0
    assert signs["negative"] / total_signed >= 0.15
    assert topics["price"] > 0
    assert topics["privacy"] > 0
    assert topics["trust"] > 0


def test_social_rounds_produce_measurable_individual_state_movement():
    result = _run(
        pitch=MIXED_PITCH,
        category="Fitness Technology",
        price=999,
    )
    baseline = {state.agent_id: state.overall_opinion for state in result.checkpoints[0].agent_states}
    final = {state.agent_id: state.overall_opinion for state in result.checkpoints[-1].agent_states}
    common = baseline.keys() & final.keys()
    mean_absolute_change = sum(abs(final[agent_id] - baseline[agent_id]) for agent_id in common) / len(common)

    assert mean_absolute_change >= 0.008


def test_same_seed_reproduces_and_product_effect_exceeds_seed_jitter():
    first = _run(pitch=MIXED_PITCH, category="Fitness Technology", price=999, seed=42, size=260)
    repeated = _run(pitch=MIXED_PITCH, category="Fitness Technology", price=999, seed=42, size=260)
    other_seed = _run(pitch=MIXED_PITCH, category="Fitness Technology", price=999, seed=43, size=260)
    poor = _run(pitch=BAD_PITCH, category="Fitness Technology", price=999, seed=42, size=260)

    assert first.timeline == repeated.timeline
    seed_jitter = abs(first.timeline[-1].mean_opinion - other_seed.timeline[-1].mean_opinion)
    product_effect = abs(first.timeline[-1].mean_opinion - poor.timeline[-1].mean_opinion)
    assert product_effect > seed_jitter * 3 + 0.10
