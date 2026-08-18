from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

import numpy as np

from simulation.domain.agent import ConsumerAgent, clamp01, clamp_opinion
from simulation.audit.logger import RunAuditSink


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
    acceptance_radius = 0.45 + 0.85 * (1.0 - stubbornness)
    distance = abs(current - incoming)
    if distance >= acceptance_radius:
        return 0.08
    return max(0.15, 1.0 - distance / acceptance_radius)


def social_noise_std(
    raw_delta: float,
    *,
    base_noise_std: float,
    noise_floor: float,
    max_noise_to_signal_ratio: float,
) -> float:
    if base_noise_std <= 0:
        return 0.0
    if noise_floor < 0 or max_noise_to_signal_ratio < 0:
        raise ValueError("social noise calibration values cannot be negative")
    signal_scaled = abs(float(raw_delta)) * max_noise_to_signal_ratio
    return min(float(base_noise_std), max(float(noise_floor), signal_scaled))


def aggregate_round_evidence(
    agent: ConsumerAgent,
    evidence: list[TopicEvidence],
    *,
    max_topic_delta: float = 0.20,
    saturation_beta: float = 0.65,
    noise_std: float = 0.012,
    noise_floor: float = 0.001,
    max_noise_to_signal_ratio: float = 0.35,
    seed: int = 42,
    audit: RunAuditSink | None = None,
    round_index: int | None = None,
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
        evidence_details: list[dict[str, float | bool]] = []

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
            distance = abs(current - clamp_opinion(item.stance))
            information_factor = 0.85 + 0.55 * min(1.0, distance / 0.55)
            weight = (
                credibility
                * receptivity
                * clamp01(item.argument_strength)
                * clamp01(item.novelty)
                * bounded
                * information_factor
            )
            evidence_details.append(
                {
                    "stance": clamp_opinion(item.stance),
                    "argument_strength": clamp01(item.argument_strength),
                    "credibility": credibility,
                    "receptivity": receptivity,
                    "bounded_confidence": bounded,
                    "distance": distance,
                    "information_factor": information_factor,
                    "novelty": clamp01(item.novelty),
                    "weight": weight,
                    "accepted": weight > 0,
                }
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
        clipped_delta = float(np.clip(raw_delta, -max_topic_delta, max_topic_delta))
        effective_noise_std = social_noise_std(
            clipped_delta,
            base_noise_std=noise_std,
            noise_floor=noise_floor,
            max_noise_to_signal_ratio=max_noise_to_signal_ratio,
        )
        noise_delta = (
            float(rng.normal(0.0, effective_noise_std))
            if effective_noise_std > 0
            else 0.0
        )
        delta = clipped_delta + noise_delta
        result_value = clamp_opinion(current + delta)
        updates[topic] = result_value

        if audit is not None:
            audit.emit(
                "aggregation.topic",
                {
                    "formula_version": "bounded-confidence-v2h",
                    "agent_id": agent.agent_id,
                    "topic": topic,
                    "current": current,
                    "evidence_items": evidence_details,
                    "weight_sum": float(weight_array.sum()),
                    "target": target,
                    "social_pressure": social_pressure,
                    "raw_delta": raw_delta,
                    "clipped_delta": clipped_delta,
                    "noise_std": effective_noise_std,
                    "noise_delta": noise_delta,
                    "noise_to_signal_ratio": (
                        abs(noise_delta) / abs(clipped_delta)
                        if abs(clipped_delta) > 1e-12
                        else 0.0
                    ),
                    "result": result_value,
                    "max_topic_delta": max_topic_delta,
                    "saturation_beta": saturation_beta,
                },
                round_index=round_index,
                agent_ids=[agent.agent_id],
            )

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
