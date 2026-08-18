import numpy as np
import pytest

from simulation.audit.logger import MemoryRunAuditLogger
from simulation.opinion.aggregator import TopicEvidence, aggregate_round_evidence, social_noise_std
from simulation.population.generator import generate_population


def test_social_noise_std_scales_with_signal_and_collapses_to_floor():
    assert social_noise_std(
        0.04,
        base_noise_std=0.012,
        noise_floor=0.001,
        max_noise_to_signal_ratio=0.35,
    ) == pytest.approx(0.012)
    assert social_noise_std(
        0.004,
        base_noise_std=0.012,
        noise_floor=0.001,
        max_noise_to_signal_ratio=0.35,
    ) == pytest.approx(0.0014)
    assert social_noise_std(
        0.0,
        base_noise_std=0.012,
        noise_floor=0.001,
        max_noise_to_signal_ratio=0.35,
    ) == pytest.approx(0.001)


def test_aggregation_audit_records_effective_noise_std_and_ratio():
    agent = generate_population(2, seed=920)[0]
    agent.state.beliefs.trust = 0.20
    audit = MemoryRunAuditLogger(run_id="noise")
    evidence = TopicEvidence(
        topic="trust",
        stance=-0.25,
        argument_strength=0.8,
        trust=0.8,
        relationship_strength=0.7,
        similarity=0.6,
        speaker_confidence=0.8,
        speaker_knowledge=0.7,
    )

    aggregate_round_evidence(agent, [evidence], seed=55, audit=audit)

    event = next(event for event in audit.events if event["event"] == "aggregation.topic")
    assert 0 <= event["payload"]["noise_std"] <= 0.012
    assert event["payload"]["noise_to_signal_ratio"] >= 0


def test_scaled_noise_rarely_exceeds_or_reverses_nontrivial_social_signal():
    exceed = 0
    reverse = 0
    considered = 0
    for index in range(1500):
        raw_delta = float(np.random.default_rng(index).uniform(-0.05, 0.05))
        if abs(raw_delta) < 0.003:
            continue
        std = social_noise_std(
            raw_delta,
            base_noise_std=0.012,
            noise_floor=0.001,
            max_noise_to_signal_ratio=0.35,
        )
        noise = float(np.random.default_rng(50_000 + index).normal(0.0, std))
        considered += 1
        if abs(noise) > abs(raw_delta):
            exceed += 1
        if raw_delta * (raw_delta + noise) < 0:
            reverse += 1

    assert considered > 1000
    assert exceed / considered < 0.20
    assert reverse / considered < 0.08
