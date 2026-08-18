from collections import Counter
from dataclasses import replace

from simulation.conversation.importance import score_conversation
from simulation.conversation.replay_selector import select_replay_conversations
from simulation.engine import SimulationConfig, SimulationEngine
from simulation.population.generator import generate_population
from simulation.product.knowledge import ProductKnowledge


PITCH = (
    "AI-powered personalized workouts, nutrition guidance, and progress tracking."
)


def _run(price: float, cadence: str, *, seed: int = 1579, size: int = 280):
    product = ProductKnowledge(
        name="AI Fitness Coach",
        category="Fitness Technology",
        pitch=PITCH,
        price=price,
        currency="INR",
        billing_cadence=cadence,
    )
    return SimulationEngine().run(
        product,
        generate_population(size, seed=seed),
        SimulationConfig(
            rounds=7,
            seed=seed,
            k=10,
            max_conversations_per_agent=2,
            initiator_rate=0.25,
            weak_tie_rate=0.05,
        ),
    )


def _mean_price(result) -> float:
    values = [agent.state.beliefs.price for agent in result.population]
    return sum(values) / len(values)


def _price_direction_counts(result) -> Counter[str]:
    counts: Counter[str] = Counter()
    for entry in result.conversations:
        for message in entry.result.messages:
            if "price" not in message.topic_effects:
                continue
            stance = float(message.topic_effects["price"])
            counts["supportive" if stance > 0.12 else "critical" if stance < -0.12 else "mixed"] += 1
    return counts


def _primary_topics(entries) -> list[str]:
    topics: list[str] = []
    for entry in entries:
        totals: dict[str, float] = {}
        for message in entry.result.messages:
            for topic, stance in message.topic_effects.items():
                totals[topic] = totals.get(topic, 0.0) + abs(float(stance))
        topics.append(max(totals, key=totals.get) if totals else "general")
    return topics


def test_fitness_pricing_matrix_is_amount_and_cadence_sensitive():
    cheap = _run(200, "monthly")
    normal = _run(500, "monthly")
    premium = _run(900, "monthly")
    expensive = _run(1500, "monthly")
    one_time = _run(1500, "one_time")

    means = [
        _mean_price(cheap),
        _mean_price(normal),
        _mean_price(premium),
        _mean_price(expensive),
    ]

    assert means == sorted(means, reverse=True)
    assert means[0] > 0.25
    assert -0.15 < means[1] < 0.30
    assert means[2] < 0.05
    assert means[3] < -0.35
    assert _mean_price(one_time) > means[3] + 0.65


def test_mid_price_conversation_population_is_not_a_single_price_narrative():
    result = _run(500, "monthly", seed=42, size=320)
    topic_counts: Counter[str] = Counter()
    for entry in result.conversations:
        for message in entry.result.messages:
            topic_counts.update(message.topic_effects)

    price_directions = _price_direction_counts(result)

    assert len(topic_counts) >= 5
    assert price_directions["supportive"] > 0
    assert price_directions["mixed"] > 0
    assert topic_counts["price"] < sum(topic_counts.values()) * 0.35


def test_replay_sample_keeps_non_price_conversations_when_comparable_entries_exist():
    result = _run(500, "monthly", seed=73, size=320)
    scored = [
        replace(entry, importance=score_conversation(entry))
        for entry in result.conversations
    ]

    selected = select_replay_conversations(scored, limit=12)
    topics = _primary_topics(selected)

    assert len(selected) == 12
    assert len(set(topics)) >= 4
    assert topics.count("price") <= 7


def test_same_pricing_inputs_and_seed_are_fully_deterministic():
    first = _run(500, "monthly", seed=91, size=180)
    second = _run(500, "monthly", seed=91, size=180)

    assert first.timeline == second.timeline
    assert [agent.state.beliefs.price for agent in first.population] == [
        agent.state.beliefs.price for agent in second.population
    ]
    assert [entry.result for entry in first.conversations] == [
        entry.result for entry in second.conversations
    ]
