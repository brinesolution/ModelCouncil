import math

import pytest

from simulation.audit.logger import MemoryRunAuditLogger
from simulation.behaviour.purchase import derive_purchase_intent
from simulation.engine import SimulationConfig, SimulationEngine
from simulation.opinion.aggregator import TopicEvidence, aggregate_round_evidence
from simulation.population.generator import generate_population
from simulation.product.fit import consumer_product_fit
from simulation.product.knowledge import ProductKnowledge
from simulation.product.semantic_profile import build_product_semantic_profile


def test_aggregation_topic_trace_exposes_weight_and_delta_components():
    agent = generate_population(2, seed=66)[0]
    agent.state.beliefs.price = -0.25
    evidence = [
        TopicEvidence(
            topic="price",
            stance=0.35,
            argument_strength=0.8,
            trust=0.7,
            relationship_strength=0.6,
            similarity=0.5,
            speaker_confidence=0.75,
            speaker_knowledge=0.4,
            novelty=1.0,
        )
    ]
    audit = MemoryRunAuditLogger(run_id="aggregation")

    result = aggregate_round_evidence(
        agent,
        evidence,
        seed=99,
        noise_std=0.0,
        audit=audit,
        round_index=3,
    )

    events = [event for event in audit.events if event["event"] == "aggregation.topic"]
    assert len(events) == 1
    payload = events[0]["payload"]
    assert payload["topic"] == "price"
    item = payload["evidence_items"][0]
    for key in (
        "credibility",
        "receptivity",
        "bounded_confidence",
        "distance",
        "information_factor",
        "weight",
    ):
        assert key in item
    assert payload["target"] == pytest.approx(0.35)
    assert payload["noise_delta"] == 0.0
    assert payload["result"] == pytest.approx(result.belief_updates["price"])


def test_purchase_trace_recombines_value_penalties_and_logistic_probability():
    product = ProductKnowledge(
        name="Coach",
        category="Fitness Technology",
        pitch="Useful personalized coaching with a monthly subscription.",
        price=500,
        billing_cadence="monthly",
    )
    agent = generate_population(2, seed=81)[0]
    profile = build_product_semantic_profile(product)
    fit = consumer_product_fit(agent, product, profile, seed=81)
    agent.state.beliefs.usefulness = 0.4
    agent.state.beliefs.quality = 0.2
    agent.state.beliefs.trust = -0.1
    agent.state.beliefs.price = -0.15
    agent.state.beliefs.privacy = -0.2
    audit = MemoryRunAuditLogger(run_id="purchase")

    probability = derive_purchase_intent(
        agent,
        fit=fit,
        audit=audit,
        round_index=4,
        phase="round_commit",
    )

    events = [event for event in audit.events if event["event"] == "purchase.evaluation"]
    assert len(events) == 1
    payload = events[0]["payload"]
    value_signal = sum(payload["components"]["value_signal"].values())
    price_penalty = sum(payload["components"]["price_penalty"].values())
    trust_penalty = sum(payload["components"]["trust_penalty"].values())
    privacy_penalty = sum(payload["components"]["privacy_penalty"].values())
    assert payload["value_signal"] == pytest.approx(value_signal)
    assert payload["price_penalty"] == pytest.approx(price_penalty)
    assert payload["trust_penalty"] == pytest.approx(trust_penalty)
    assert payload["privacy_penalty"] == pytest.approx(privacy_penalty)
    expected_z = 5.4 * (value_signal - 0.50) - 2.4 * price_penalty - 2.0 * trust_penalty - 1.5 * privacy_penalty
    assert payload["z"] == pytest.approx(expected_z)
    assert payload["result"] == pytest.approx(1.0 / (1.0 + math.exp(-expected_z)))
    assert probability == pytest.approx(payload["result"])


def test_engine_audits_evidence_deltas_and_committed_before_after_state():
    product = ProductKnowledge(
        name="Coach",
        category="Fitness Technology",
        pitch="Useful coaching for a monthly subscription.",
        price=500,
        billing_cadence="monthly",
    )
    population = generate_population(24, seed=91)
    audit = MemoryRunAuditLogger(run_id="state")

    result = SimulationEngine().run(
        product,
        population,
        SimulationConfig(rounds=2, seed=91, k=4, initiator_rate=0.4),
        audit=audit,
    )

    baseline_states = [event for event in audit.events if event["event"] == "baseline.state_initialized"]
    evidence_events = [event for event in audit.events if event["event"] == "evidence.created"]
    delta_events = [event for event in audit.events if event["event"] == "state.delta"]
    commit_events = [event for event in audit.events if event["event"] == "state.committed"]
    assert len(baseline_states) == len(population)
    assert all("purchase_intent" in event["payload"]["state"] for event in baseline_states)
    assert len(evidence_events) == sum(len(entry.result.messages) for entry in result.conversations)
    assert len(delta_events) == len(population) * 2
    assert len(commit_events) == len(population) * 2
    changed = next(event for event in commit_events if event["payload"]["before"] != event["payload"]["after"])
    assert "beliefs" in changed["payload"]["before"]
    assert "purchase_intent" in changed["payload"]["after"]
