from __future__ import annotations

from dataclasses import dataclass

import networkx as nx

from simulation.conversation.background_engine import generate_background_conversation
from simulation.conversation.models import ConversationPair, ConversationResult
from simulation.domain.agent import ConsumerAgent


@dataclass(frozen=True, slots=True)
class ConversationContext:
    snapshot: dict[int, ConsumerAgent]
    graph: nx.Graph
    seed: int


class ConversationRouter:
    """Routes simulation interactions without coupling the engine to an LLM provider.

    Phase 1 always uses deterministic background semantic conversations. A later
    router version can promote selected interactions to DeepSeek while preserving
    the same ConversationResult contract.
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
        )
