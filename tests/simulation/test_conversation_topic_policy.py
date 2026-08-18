import numpy as np

from simulation.conversation.topic_policy import (
    score_conversation_topics,
    select_conversation_topic,
)
from simulation.domain.agent import ProductBeliefs
from simulation.population.generator import generate_population


def _agents():
    speaker, listener = generate_population(2, seed=55)
    speaker.traits.price_sensitivity = 0.75
    speaker.traits.product_need = 0.55
    speaker.traits.risk_tolerance = 0.35
    speaker.traits.technology_adoption = 0.65
    listener.traits.price_sensitivity = 0.9
    listener.traits.product_need = 0.45
    listener.traits.risk_tolerance = 0.2
    listener.traits.technology_adoption = 0.55
    return speaker, listener


def test_disagreement_raises_topic_priority():
    speaker, listener = _agents()
    speaker.state.beliefs = ProductBeliefs(price=-0.45, usefulness=0.20, quality=0.18, trust=0.12, novelty=0.15, privacy=-0.10)
    listener.state.beliefs = ProductBeliefs(price=0.55, usefulness=0.20, quality=0.18, trust=0.12, novelty=0.15, privacy=-0.10)

    scores = score_conversation_topics(speaker, listener)

    assert scores["price"] > scores["quality"]
    assert scores["price"] > scores["novelty"]


def test_listener_trait_relevance_promotes_price_and_privacy_objections():
    speaker, listener = _agents()
    speaker.state.beliefs = ProductBeliefs(price=-0.35, usefulness=0.25, quality=0.25, trust=-0.25, novelty=0.25, privacy=-0.35)
    listener.state.beliefs = ProductBeliefs(price=-0.05, usefulness=0.25, quality=0.25, trust=0.05, novelty=0.25, privacy=0.05)

    scores = score_conversation_topics(speaker, listener)

    assert scores["price"] > scores["quality"]
    assert scores["privacy"] > scores["novelty"]
    assert scores["trust"] > 0


def test_skeptical_stance_gets_objection_salience():
    speaker, listener = _agents()
    speaker.state.beliefs = ProductBeliefs(price=-0.7, usefulness=0.1, quality=0.1, trust=0.1, novelty=0.1, privacy=0.1)
    listener.state.beliefs = ProductBeliefs(price=-0.4, usefulness=0.1, quality=0.1, trust=0.1, novelty=0.1, privacy=0.1)

    scores = score_conversation_topics(speaker, listener)

    assert scores["price"] == max(scores.values())


def test_selection_is_deterministic_for_same_rng_seed_and_preserves_speaker_stance():
    speaker, listener = _agents()
    speaker.state.beliefs = ProductBeliefs(price=-0.6, usefulness=0.35, quality=-0.15, trust=0.25, novelty=0.3, privacy=-0.3)
    listener.state.beliefs = ProductBeliefs(price=0.2, usefulness=0.1, quality=0.2, trust=-0.1, novelty=0.1, privacy=0.25)

    first = select_conversation_topic(speaker, listener, np.random.default_rng(99))
    second = select_conversation_topic(speaker, listener, np.random.default_rng(99))

    assert first == second
    topic, stance = first
    assert stance == speaker.state.beliefs.as_dict()[topic]


def test_recent_topic_history_softly_penalizes_repetition_without_blacklisting():
    speaker, listener = _agents()
    speaker.state.beliefs = ProductBeliefs(price=-0.45, usefulness=0.42, quality=0.25, trust=-0.30, novelty=0.30, privacy=-0.35)
    listener.state.beliefs = ProductBeliefs(price=0.35, usefulness=0.15, quality=0.10, trust=0.15, novelty=0.05, privacy=0.20)

    baseline = score_conversation_topics(speaker, listener)
    repeated = score_conversation_topics(
        speaker,
        listener,
        recent_topics=("price", "price", "price"),
    )

    assert repeated["price"] < baseline["price"] * 0.50
    assert repeated["usefulness"] == baseline["usefulness"]
    assert repeated["price"] > 0


def test_overwhelming_price_salience_can_still_dominate_after_repetition_penalty():
    speaker, listener = _agents()
    speaker.state.beliefs = ProductBeliefs(price=-1.0, usefulness=0.02, quality=0.01, trust=0.01, novelty=0.01, privacy=0.01)
    listener.state.beliefs = ProductBeliefs(price=0.9, usefulness=0.02, quality=0.01, trust=0.01, novelty=0.01, privacy=0.01)

    scores = score_conversation_topics(
        speaker,
        listener,
        recent_topics=("price", "price"),
    )

    assert scores["price"] == max(scores.values())


def test_mixed_scenario_selection_uses_multiple_topics_including_critical_topics():
    speaker, listener = _agents()
    speaker.state.beliefs = ProductBeliefs(price=-0.55, usefulness=0.45, quality=0.20, trust=-0.35, novelty=0.40, privacy=-0.50)
    listener.state.beliefs = ProductBeliefs(price=0.25, usefulness=0.15, quality=-0.15, trust=0.25, novelty=0.05, privacy=0.20)

    counts: dict[str, int] = {}
    for seed in range(300):
        topic, _ = select_conversation_topic(speaker, listener, np.random.default_rng(seed))
        counts[topic] = counts.get(topic, 0) + 1

    assert len(counts) >= 5
    assert counts.get("price", 0) > 20
    assert counts.get("privacy", 0) > 20
    assert counts.get("trust", 0) > 10
