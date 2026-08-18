from __future__ import annotations

import numpy as np

from simulation.domain.agent import ConsumerAgent
from simulation.audit.logger import RunAuditSink


_TOPICS = ("price", "usefulness", "quality", "trust", "novelty", "privacy")


def _score_conversation_topic_details(
    speaker: ConsumerAgent,
    listener: ConsumerAgent,
    *,
    recent_topics: tuple[str, ...] = (),
) -> tuple[dict[str, float], dict[str, dict[str, float]]]:
    speaker_beliefs = speaker.state.beliefs.as_dict()
    listener_beliefs = listener.state.beliefs.as_dict()

    scores: dict[str, float] = {}
    details: dict[str, dict[str, float]] = {}
    for topic in _TOPICS:
        stance = float(speaker_beliefs[topic])
        listener_stance = float(listener_beliefs[topic])
        salience = abs(stance)
        disagreement = abs(stance - listener_stance) / 2.0
        relevance = _topic_relevance(topic, speaker, listener)
        objection = max(0.0, -stance) * (0.55 + 0.45 * relevance)
        components = {
            "salience": 0.28 * salience,
            "disagreement": 0.34 * disagreement,
            "relevance": 0.22 * relevance,
            "objection": 0.16 * objection,
        }
        raw_score = sum(components.values())
        repeat_count = recent_topics[-4:].count(topic)
        repetition_multiplier = max(0.28, 0.70 ** repeat_count) if repeat_count else 1.0
        repeated_score = raw_score * repetition_multiplier
        final_score = max(0.01, float(repeated_score))
        scores[topic] = final_score
        details[topic] = {
            **components,
            "raw_score": raw_score,
            "repeat_count": float(repeat_count),
            "repetition_multiplier": repetition_multiplier,
            "score_after_repetition": repeated_score,
            "final_score": final_score,
        }
    return scores, details


def score_conversation_topics(
    speaker: ConsumerAgent,
    listener: ConsumerAgent,
    *,
    recent_topics: tuple[str, ...] = (),
) -> dict[str, float]:
    scores, _ = _score_conversation_topic_details(
        speaker,
        listener,
        recent_topics=recent_topics,
    )
    return scores


def select_conversation_topic(
    speaker: ConsumerAgent,
    listener: ConsumerAgent,
    rng: np.random.Generator,
    *,
    recent_topics: tuple[str, ...] = (),
    audit: RunAuditSink | None = None,
    round_index: int | None = None,
    conversation_id: str | None = None,
) -> tuple[str, float]:
    scores, score_components = _score_conversation_topic_details(
        speaker,
        listener,
        recent_topics=recent_topics,
    )
    topics = list(_TOPICS)
    weights = np.asarray([scores[topic] for topic in topics], dtype=float)
    # A small bounded jitter keeps repeated conversations from becoming mechanically
    # identical while the seeded RNG preserves reproducibility.
    jitter = rng.uniform(0.90, 1.10, size=len(weights))
    weights *= jitter
    weights = np.power(np.maximum(weights, 0.001), 1.20)
    weights /= weights.sum()
    topic = str(rng.choice(topics, p=weights))
    stance = float(speaker.state.beliefs.as_dict()[topic])
    if audit is not None:
        audit.emit(
            "conversation.topic_selected",
            {
                "speaker_id": speaker.agent_id,
                "listener_id": listener.agent_id,
                "recent_topics": recent_topics,
                "topic_scores": scores,
                "score_components": score_components,
                "jitter_multipliers": {
                    name: float(value) for name, value in zip(topics, jitter, strict=True)
                },
                "normalized_weights": {
                    name: float(value) for name, value in zip(topics, weights, strict=True)
                },
                "selected_topic": topic,
                "speaker_stance": stance,
            },
            round_index=round_index,
            conversation_id=conversation_id,
            agent_ids=[speaker.agent_id, listener.agent_id],
        )
    return topic, stance


def _topic_relevance(
    topic: str,
    speaker: ConsumerAgent,
    listener: ConsumerAgent,
) -> float:
    if topic == "price":
        return _mean(
            speaker.traits.price_sensitivity,
            listener.traits.price_sensitivity,
            1.0 - speaker.income_score,
            1.0 - listener.income_score,
        )
    if topic == "usefulness":
        return _mean(speaker.traits.product_need, listener.traits.product_need)
    if topic == "quality":
        return _mean(
            speaker.traits.logicality,
            listener.traits.logicality,
            speaker.traits.brand_loyalty,
            listener.traits.brand_loyalty,
        )
    if topic == "trust":
        return _mean(
            1.0 - speaker.traits.risk_tolerance,
            1.0 - listener.traits.risk_tolerance,
            speaker.traits.logicality,
            listener.traits.logicality,
        )
    if topic == "novelty":
        return _mean(
            speaker.traits.technology_adoption,
            listener.traits.technology_adoption,
            speaker.traits.risk_tolerance,
            listener.traits.risk_tolerance,
        )
    if topic == "privacy":
        return _mean(
            1.0 - speaker.traits.risk_tolerance,
            1.0 - listener.traits.risk_tolerance,
            speaker.traits.logicality,
            listener.traits.logicality,
        )
    return 0.5


def _mean(*values: float) -> float:
    return float(np.clip(sum(values) / len(values), 0.0, 1.0))
