from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from simulation.engine import SimulationResult

CANONICAL_TOPICS = (
    "price",
    "usefulness",
    "quality",
    "trust",
    "novelty",
    "privacy",
)


@dataclass(frozen=True, slots=True)
class PurchaseIntentDistribution:
    low: int
    medium: int
    high: int


@dataclass(frozen=True, slots=True)
class TopicPressurePoint:
    topic: str
    raw_score: float
    normalized_score: float
    support_score: float
    criticism_score: float
    net_score: float
    normalized_support: float
    normalized_criticism: float


@dataclass(frozen=True, slots=True)
class DashboardAnalytics:
    purchase_intent_distribution: PurchaseIntentDistribution
    topic_pressure: tuple[TopicPressurePoint, ...]


def build_dashboard_analytics(result: SimulationResult) -> DashboardAnalytics:
    purchases = [agent.state.purchase_intent for agent in result.population]
    low = sum(value < 0.35 for value in purchases)
    medium = sum(0.35 <= value <= 0.70 for value in purchases)
    high = sum(value > 0.70 for value in purchases)

    support_totals: dict[str, float] = defaultdict(float)
    criticism_totals: dict[str, float] = defaultdict(float)
    for entry in result.conversations:
        for message in entry.result.messages:
            strength = float(message.argument_strength)
            for topic, stance in message.topic_effects.items():
                if topic not in CANONICAL_TOPICS:
                    continue
                signed = float(stance)
                support_totals[topic] += max(0.0, signed) * strength
                criticism_totals[topic] += max(0.0, -signed) * strength

    pressure_totals = {
        topic: support_totals[topic] + criticism_totals[topic]
        for topic in CANONICAL_TOPICS
    }
    max_score = max(pressure_totals.values(), default=0.0)
    max_directional = max(
        (
            max(support_totals[topic], criticism_totals[topic])
            for topic in CANONICAL_TOPICS
        ),
        default=0.0,
    )
    topic_pressure = tuple(
        TopicPressurePoint(
            topic=topic,
            raw_score=pressure_totals[topic],
            normalized_score=(pressure_totals[topic] / max_score if max_score > 0 else 0.0),
            support_score=support_totals[topic],
            criticism_score=criticism_totals[topic],
            net_score=support_totals[topic] - criticism_totals[topic],
            normalized_support=(
                support_totals[topic] / max_directional if max_directional > 0 else 0.0
            ),
            normalized_criticism=(
                criticism_totals[topic] / max_directional if max_directional > 0 else 0.0
            ),
        )
        for topic in CANONICAL_TOPICS
    )

    return DashboardAnalytics(
        purchase_intent_distribution=PurchaseIntentDistribution(
            low=low,
            medium=medium,
            high=high,
        ),
        topic_pressure=topic_pressure,
    )
