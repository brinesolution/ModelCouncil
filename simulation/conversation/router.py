from __future__ import annotations

from dataclasses import dataclass, field

import networkx as nx

from simulation.conversation.background_engine import generate_background_conversation
from simulation.conversation.models import ConversationPair, ConversationResult
from simulation.domain.agent import ConsumerAgent
from simulation.product.pricing import ConsumerPriceContext
from simulation.audit.logger import RunAuditSink


@dataclass(frozen=True, slots=True)
class ConversationContext:
    snapshot: dict[int, ConsumerAgent]
    graph: nx.Graph
    seed: int
    price_contexts: dict[int, ConsumerPriceContext] = field(default_factory=dict)
    recent_topics_by_agent: dict[int, tuple[str, ...]] = field(default_factory=dict)
    recent_topics_by_edge: dict[tuple[int, int], tuple[str, ...]] = field(default_factory=dict)
    audit: RunAuditSink | None = None


class ConversationRouter:
    """Routes simulation interactions without coupling the engine to an LLM provider.

    The numerical round loop always uses deterministic background semantic
    conversations. Phase 2 language promotion happens after the core simulation
    through render_pipeline.py so provider availability cannot affect state updates.
    """

    def generate(
        self,
        pair: ConversationPair,
        context: ConversationContext,
    ) -> ConversationResult:
        return generate_background_conversation(
            pair=pair,
            snapshot=context.snapshot,
            graph=context.graph,
            seed=context.seed,
            price_contexts=context.price_contexts,
            recent_topics_by_agent=context.recent_topics_by_agent,
            recent_topics_by_edge=context.recent_topics_by_edge,
            audit=context.audit,
        )
