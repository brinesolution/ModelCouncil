from __future__ import annotations

from dataclasses import replace
import hashlib

import networkx as nx
import numpy as np

from simulation.conversation.background_language import render_background_text
from simulation.conversation.dialogue_realism import (
    derive_dialogue_shape,
    derive_speaking_style,
)
from simulation.conversation.ledger import ConversationLanguageContext
from simulation.conversation.models import ConversationPair, ConversationResult, SemanticMessage
from simulation.conversation.topic_policy import select_conversation_topic
from simulation.domain.agent import ConsumerAgent, clamp01, clamp_opinion
from simulation.product.pricing import ConsumerPriceContext
from simulation.audit.logger import RunAuditSink


def generate_background_conversation(
    pair: ConversationPair,
    snapshot: dict[int, ConsumerAgent],
    graph: nx.Graph,
    seed: int,
    *,
    price_contexts: dict[int, ConsumerPriceContext] | None = None,
    recent_topics_by_agent: dict[int, tuple[str, ...]] | None = None,
    recent_topics_by_edge: dict[tuple[int, int], tuple[str, ...]] | None = None,
    audit: RunAuditSink | None = None,
) -> ConversationResult:
    """Generate deterministic semantic interaction without an LLM call.

    Numerical semantic messages are fixed before any wording is produced. Recent-topic
    memory changes only topic selection and is expected to contain completed prior-round
    history, preserving same-round snapshot semantics.
    """
    first = snapshot[pair.agent_a_id]
    second = snapshot[pair.agent_b_id]
    edge = graph.edges[pair.agent_a_id, pair.agent_b_id]
    rng = np.random.default_rng(_mixed_seed(seed, pair.conversation_id))
    edge_key = tuple(sorted((pair.agent_a_id, pair.agent_b_id)))
    agent_history = recent_topics_by_agent or {}
    edge_history = recent_topics_by_edge or {}
    if audit is not None:
        audit.emit(
            "conversation.semantic_started",
            {
                "pair": pair,
                "agent_a": first,
                "agent_b": second,
                "edge": dict(edge),
                "recent_topics_agent_a": agent_history.get(first.agent_id, ()),
                "recent_topics_agent_b": agent_history.get(second.agent_id, ()),
                "recent_topics_edge": edge_history.get(edge_key, ()),
            },
            round_index=pair.round_index,
            conversation_id=pair.conversation_id,
            agent_ids=[pair.agent_a_id, pair.agent_b_id],
        )

    first_message = _semantic_message(
        first,
        second,
        edge,
        rng,
        recent_topics=_merge_recent_topics(
            agent_history.get(first.agent_id, ()),
            edge_history.get(edge_key, ()),
        ),
        audit=audit,
        pair=pair,
    )
    second_message = _semantic_message(
        second,
        first,
        edge,
        rng,
        recent_topics=_merge_recent_topics(
            agent_history.get(second.agent_id, ()),
            edge_history.get(edge_key, ()),
        ),
        audit=audit,
        pair=pair,
    )
    semantic_result = ConversationResult(
        conversation_id=pair.conversation_id,
        messages=[first_message, second_message],
        transcript=[],
        language_source="background",
    )

    resolved_price_contexts = price_contexts or {}
    language_context = ConversationLanguageContext.from_agents(
        first,
        second,
        agent_a_price_context=resolved_price_contexts.get(first.agent_id),
        agent_b_price_context=resolved_price_contexts.get(second.agent_id),
    )
    dialogue_shape = derive_dialogue_shape(semantic_result, language_context)
    profiles = {
        first.agent_id: language_context.agent_a,
        second.agent_id: language_context.agent_b,
    }
    dialogue_price_contexts = {
        first.agent_id: language_context.agent_a_price_context,
        second.agent_id: language_context.agent_b_price_context,
    }
    listeners = {
        first.agent_id: second,
        second.agent_id: first,
    }

    rendered_messages: list[SemanticMessage] = []
    transcript: list[dict[str, str | int]] = []
    for message in semantic_result.messages:
        topic, stance = next(iter(message.topic_effects.items()))
        speaking_style = derive_speaking_style(profiles[message.speaker_id])
        text = render_background_text(
            speaker=snapshot[message.speaker_id],
            listener=listeners[message.speaker_id],
            topic=topic,
            stance=stance,
            conversation_id=pair.conversation_id,
            dialogue_shape=dialogue_shape,
            speaking_style=speaking_style,
            price_context=dialogue_price_contexts.get(message.speaker_id),
        )
        rendered = replace(message, text=text)
        rendered_messages.append(rendered)
        transcript.append({"speaker_id": message.speaker_id, "text": text})
        if audit is not None:
            audit.emit(
                "conversation.semantic_message",
                {
                    "speaker_id": rendered.speaker_id,
                    "listener_id": rendered.listener_id,
                    "topic_effects": rendered.topic_effects,
                    "argument_strength": rendered.argument_strength,
                    "confidence": rendered.confidence,
                    "claims": rendered.claims,
                    "fallback_text": text,
                    "dialogue_shape": dialogue_shape,
                    "speaking_style": speaking_style,
                    "price_context": dialogue_price_contexts.get(message.speaker_id),
                },
                round_index=pair.round_index,
                conversation_id=pair.conversation_id,
                agent_ids=[rendered.speaker_id, rendered.listener_id],
            )

    result = ConversationResult(
        conversation_id=pair.conversation_id,
        messages=rendered_messages,
        transcript=transcript,
        language_source="background",
    )
    if audit is not None:
        audit.emit(
            "conversation.semantic_completed",
            {
                "message_count": len(result.messages),
                "transcript": result.transcript,
                "language_source": result.language_source,
                "dialogue_shape": dialogue_shape,
            },
            round_index=pair.round_index,
            conversation_id=pair.conversation_id,
            agent_ids=[pair.agent_a_id, pair.agent_b_id],
        )
    return result


def _semantic_message(
    speaker: ConsumerAgent,
    listener: ConsumerAgent,
    edge: dict[str, object],
    rng: np.random.Generator,
    *,
    recent_topics: tuple[str, ...],
    audit: RunAuditSink | None,
    pair: ConversationPair,
) -> SemanticMessage:
    topic, stance = select_conversation_topic(
        speaker,
        listener,
        rng,
        recent_topics=recent_topics,
        audit=audit,
        round_index=pair.round_index,
        conversation_id=pair.conversation_id,
    )

    trust = float(edge.get("trust", 0.4))
    relationship = float(edge.get("relationship_strength", 0.4))
    argument_noise = float(rng.normal(0.0, 0.04))
    argument_components = {
        "base": 0.30,
        "speaker_confidence": 0.28 * speaker.state.confidence,
        "speaker_logicality": 0.22 * speaker.traits.logicality,
        "relationship": 0.20 * relationship,
        "noise": argument_noise,
    }
    argument_raw = sum(argument_components.values())
    argument_strength = clamp01(argument_raw)
    conveyed_noise = float(rng.normal(0.0, 0.025))
    conveyed_raw = float(stance) + conveyed_noise
    conveyed = clamp_opinion(conveyed_raw)
    confidence_components = {
        "speaker_confidence": 0.65 * speaker.state.confidence,
        "edge_trust": 0.35 * trust,
    }
    message_confidence = clamp01(sum(confidence_components.values()))

    if audit is not None:
        audit.emit(
            "conversation.semantic_calculation",
            {
                "speaker_id": speaker.agent_id,
                "listener_id": listener.agent_id,
                "selected_topic": topic,
                "speaker_stance": float(stance),
                "argument_components": argument_components,
                "argument_raw": argument_raw,
                "argument_strength": argument_strength,
                "conveyed_noise": conveyed_noise,
                "conveyed_raw": conveyed_raw,
                "conveyed_stance": conveyed,
                "confidence_components": confidence_components,
                "message_confidence": message_confidence,
            },
            round_index=pair.round_index,
            conversation_id=pair.conversation_id,
            agent_ids=[speaker.agent_id, listener.agent_id],
        )

    return SemanticMessage(
        speaker_id=speaker.agent_id,
        listener_id=listener.agent_id,
        topic_effects={topic: conveyed},
        argument_strength=argument_strength,
        confidence=message_confidence,
        text=None,
    )


def _merge_recent_topics(*histories: tuple[str, ...]) -> tuple[str, ...]:
    combined = tuple(topic for history in histories for topic in history)
    return combined[-6:]


def _mixed_seed(seed: int, conversation_id: str) -> int:
    digest = hashlib.blake2b(
        f"{seed}:{conversation_id}".encode("utf-8"), digest_size=8
    ).digest()
    return int.from_bytes(digest, "big") % (2**32)
