from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

import numpy as np

from simulation.domain.agent import ConsumerAgent, clamp01, clamp_opinion


@dataclass(frozen=True, slots=True)
class TopicEvidence:
    topic: str
    stance: float
    argument_strength: float
    trust: float
    relationship_strength: float
    similarity: float
    speaker_confidence: float
    speaker_knowledge: float
    novelty: float = 1.0


@dataclass(frozen=True, slots=True)
class RoundAggregation:
    belief_updates: dict[str, float]
    confidence_delta: float


def _bounded_confidence_factor(
    current: float,
    incoming: float,
    stubbornness: float,
) -> float:
    acceptance_radius = 0.35 + 0.80 * (1.0 - stubbornness)
    distance = abs(current - incoming)
    if distance >= acceptance_radius:
        return 0.08
    return max(0.15, 1.0 - distance / acceptance_radius)


def aggregate_round_evidence(
    agent: ConsumerAgent,
    evidence: list[TopicEvidence],
    *,
    max_topic_delta: float = 0.20,
    saturation_beta: float = 0.65,
    noise_std: float = 0.012,
    seed: int = 42,
) -> RoundAggregation:
    """Return one aggregate delta from a start-of-round agent snapshot.

    This function never mutates the supplied agent. Every conversation for round t
    can therefore be evaluated against the same S(t), and the caller commits the
    combined delta only after all agents have been processed.
    """
    grouped: dict[str, list[TopicEvidence]] = defaultdict(list)
    for item in evidence:
        grouped[item.topic].append(item)

    current_beliefs = agent.state.beliefs.as_dict()
    updates: dict[str, float] = {}
    confidence_signals: list[float] = []
    rng = np.random.default_rng(seed + agent.agent_id)

    for topic, items in grouped.items():
        if topic not in current_beliefs:
            continue

        current = current_beliefs[topic]
        weighted_stances: list[float] = []
        weights: list[float] = []

        for item in items:
            credibility = (
                0.35 * clamp01(item.trust)
                + 0.20 * clamp01(item.relationship_strength)
                + 0.15 * clamp01(item.speaker_confidence)
                + 0.15 * clamp01(item.speaker_knowledge)
                + 0.15 * clamp01(item.similarity)
            )
            receptivity = (
                (1.0 - agent.traits.stubbornness)
                * (1.0 - 0.50 * agent.state.confidence)
            )
            bounded = _bounded_confidence_factor(
                current,
                clamp_opinion(item.stance),
                agent.traits.stubbornness,
            )
            weight = (
                credibility
                * receptivity
                * clamp01(item.argument_strength)
                * clamp01(item.novelty)
                * bounded
            )
            if weight <= 0:
                continue
            weighted_stances.append(clamp_opinion(item.stance))
            weights.append(weight)

        if not weights:
            continue

        weight_array = np.asarray(weights, dtype=float)
        stance_array = np.asarray(weighted_stances, dtype=float)
        target = float(np.average(stance_array, weights=weight_array))
        social_pressure = 1.0 - float(np.exp(-saturation_beta * weight_array.sum()))
        raw_delta = social_pressure * (target - current)
        delta = float(np.clip(raw_delta, -max_topic_delta, max_topic_delta))
        delta += float(rng.normal(0.0, noise_std))
        updates[topic] = clamp_opinion(current + delta)

        disagreement = float(np.average(np.abs(stance_array - target), weights=weight_array))
        agreement = 1.0 - min(1.0, disagreement)
        confidence_signals.append((agreement - 0.5) * min(1.0, weight_array.sum()))

    confidence_delta = 0.0
    if confidence_signals:
        confidence_delta = float(np.clip(np.mean(confidence_signals) * 0.08, -0.05, 0.05))

    return RoundAggregation(
        belief_updates=updates,
        confidence_delta=confidence_delta,
    )
