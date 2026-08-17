from __future__ import annotations

import hashlib

import networkx as nx
import numpy as np

from simulation.conversation.models import ConversationPair, ConversationResult, SemanticMessage
from simulation.domain.agent import ConsumerAgent, clamp01, clamp_opinion


def generate_background_conversation(
    pair: ConversationPair,
    snapshot: dict[int, ConsumerAgent],
    graph: nx.Graph,
    seed: int,
) -> ConversationResult:
    """Generate deterministic semantic interaction without an LLM call."""
    first = snapshot[pair.agent_a_id]
    second = snapshot[pair.agent_b_id]
    edge = graph.edges[pair.agent_a_id, pair.agent_b_id]
    rng = np.random.default_rng(_mixed_seed(seed, pair.conversation_id))

    messages = [
        _message(first, second, edge, rng),
        _message(second, first, edge, rng),
    ]
    return ConversationResult(
        conversation_id=pair.conversation_id,
        messages=messages,
        transcript=[],
    )


def _message(
    speaker: ConsumerAgent,
    listener: ConsumerAgent,
    edge: dict[str, object],
    rng: np.random.Generator,
) -> SemanticMessage:
    beliefs = speaker.state.beliefs.as_dict()
    ranked = sorted(beliefs.items(), key=lambda item: abs(item[1]), reverse=True)
    candidates = ranked[: max(1, min(3, len(ranked)))]
    topic, stance = candidates[int(rng.integers(0, len(candidates)))]

    if abs(stance) < 0.05:
        fallback = (
            speaker.traits.product_need
            + speaker.traits.technology_adoption
            - speaker.traits.price_sensitivity
        ) / 2.0
        stance = clamp_opinion(fallback)

    trust = float(edge.get("trust", 0.4))
    relationship = float(edge.get("relationship_strength", 0.4))
    argument_strength = clamp01(
        0.30
        + 0.28 * speaker.state.confidence
        + 0.22 * speaker.traits.logicality
        + 0.20 * relationship
        + float(rng.normal(0.0, 0.04))
    )
    conveyed = clamp_opinion(float(stance) + float(rng.normal(0.0, 0.025)))

    return SemanticMessage(
        speaker_id=speaker.agent_id,
        listener_id=listener.agent_id,
        topic_effects={topic: conveyed},
        argument_strength=argument_strength,
        confidence=clamp01(0.65 * speaker.state.confidence + 0.35 * trust),
        text=None,
    )


def _mixed_seed(seed: int, conversation_id: str) -> int:
    digest = hashlib.blake2b(
        f"{seed}:{conversation_id}".encode("utf-8"), digest_size=8
    ).digest()
    return int.from_bytes(digest, "big") % (2**32)
