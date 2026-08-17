from __future__ import annotations

from collections import defaultdict

import networkx as nx
import numpy as np

from simulation.conversation.models import ConversationPair
from simulation.domain.agent import ConsumerAgent


def _edge_score(
    source: ConsumerAgent,
    target: ConsumerAgent,
    edge: dict[str, object],
) -> float:
    similarity = float(edge.get("similarity", 0.0))
    relationship = float(edge.get("relationship_strength", 0.0))
    salience = (source.state.product_salience + target.state.product_salience) / 2
    sociability = (source.traits.sociability + target.traits.sociability) / 2
    return (
        0.30 * similarity
        + 0.25 * relationship
        + 0.25 * salience
        + 0.20 * sociability
    )


def schedule_conversations(
    agents: list[ConsumerAgent],
    graph: nx.Graph,
    round_index: int,
    max_conversations_per_agent: int = 2,
    cooldown_rounds: int = 2,
    seed: int = 42,
    initiator_rate: float = 0.20,
) -> list[ConversationPair]:
    """Schedule a sparse set of conversations for one round.

    K defines candidate neighbours. `initiator_rate` controls how many agents try to
    start a conversation in the current round. A non-initiator can still receive a
    conversation. This avoids turning KNN into an unrealistic all-neighbours chat.
    """
    if max_conversations_per_agent < 1 or not agents:
        return []
    if not 0.0 <= initiator_rate <= 1.0:
        raise ValueError("initiator_rate must be between 0 and 1.")

    by_id = {agent.agent_id: agent for agent in agents}
    rng = np.random.default_rng(seed + round_index)
    capacity: dict[int, int] = defaultdict(int)
    selected: list[ConversationPair] = []
    selected_edges: set[tuple[int, int]] = set()

    desired_initiators = int(round(len(agents) * initiator_rate))
    if desired_initiators == 0:
        return []

    activity_weights = np.asarray(
        [
            max(
                0.001,
                0.55 * agent.traits.sociability
                + 0.45 * agent.state.product_salience,
            )
            for agent in agents
        ],
        dtype=float,
    )
    activity_weights /= activity_weights.sum()

    initiator_indexes = rng.choice(
        len(agents),
        size=min(desired_initiators, len(agents)),
        replace=False,
        p=activity_weights,
    )
    initiators = [agents[int(index)] for index in initiator_indexes]
    rng.shuffle(initiators)

    for source in initiators:
        if capacity[source.agent_id] >= max_conversations_per_agent:
            continue

        neighbor_options: list[tuple[int, float]] = []
        for target_id in graph.neighbors(source.agent_id):
            target_id = int(target_id)
            if capacity[target_id] >= max_conversations_per_agent:
                continue

            edge_key = tuple(sorted((source.agent_id, target_id)))
            if edge_key in selected_edges:
                continue

            edge = graph.edges[source.agent_id, target_id]
            last_round = edge.get("last_interaction_round")
            if last_round is not None and round_index - int(last_round) <= cooldown_rounds:
                continue

            score = _edge_score(source, by_id[target_id], edge)
            score *= float(rng.uniform(0.90, 1.10))
            if score > 0:
                neighbor_options.append((target_id, score))

        if not neighbor_options:
            continue

        target_ids = [item[0] for item in neighbor_options]
        weights = np.asarray([item[1] for item in neighbor_options], dtype=float)
        weights /= weights.sum()
        target_id = int(rng.choice(target_ids, p=weights))
        chosen_score = next(score for candidate, score in neighbor_options if candidate == target_id)

        capacity[source.agent_id] += 1
        capacity[target_id] += 1
        edge_key = tuple(sorted((source.agent_id, target_id)))
        selected_edges.add(edge_key)

        selected.append(
            ConversationPair(
                conversation_id=f"r{round_index}-a{source.agent_id}-a{target_id}",
                round_index=round_index,
                agent_a_id=source.agent_id,
                agent_b_id=target_id,
                edge_score=float(chosen_score),
            )
        )

    return selected
