from __future__ import annotations

from collections import defaultdict

import networkx as nx
import numpy as np

from simulation.conversation.models import ConversationPair
from simulation.domain.agent import ConsumerAgent
from simulation.audit.logger import RunAuditSink
from simulation.opinion.dynamics_config import (
    DEFAULT_INFLUENCE_DYNAMICS,
    InfluenceDynamicsConfig,
)


def _edge_score_components(
    source: ConsumerAgent,
    target: ConsumerAgent,
    edge: dict[str, object],
    dynamics: InfluenceDynamicsConfig = DEFAULT_INFLUENCE_DYNAMICS,
) -> tuple[float, dict[str, float]]:
    similarity = float(edge.get("similarity", 0.0))
    relationship = float(edge.get("relationship_strength", 0.0))
    salience = (source.state.product_salience + target.state.product_salience) / 2
    sociability = (source.traits.sociability + target.traits.sociability) / 2
    opinion_gap = abs(source.state.overall_opinion - target.state.overall_opinion) / 2.0
    components = {
        "similarity": 0.30 * similarity,
        "relationship": 0.25 * relationship,
        "salience": 0.25 * salience,
        "sociability": 0.20 * sociability,
        "informational_difference": dynamics.disagreement_information_weight * opinion_gap,
    }
    return sum(components.values()), components


def _edge_score(
    source: ConsumerAgent,
    target: ConsumerAgent,
    edge: dict[str, object],
    dynamics: InfluenceDynamicsConfig = DEFAULT_INFLUENCE_DYNAMICS,
) -> float:
    score, _ = _edge_score_components(source, target, edge, dynamics)
    return score


def schedule_conversations(
    agents: list[ConsumerAgent],
    graph: nx.Graph,
    round_index: int,
    max_conversations_per_agent: int = 2,
    cooldown_rounds: int = 2,
    seed: int = 42,
    initiator_rate: float = 0.20,
    dynamics: InfluenceDynamicsConfig = DEFAULT_INFLUENCE_DYNAMICS,
    audit: RunAuditSink | None = None,
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
    if audit is not None:
        audit.emit(
            "scheduler.initiators_selected",
            {
                "desired_initiators": desired_initiators,
                "initiator_ids": [agent.agent_id for agent in initiators],
                "activity_weights": {
                    agent.agent_id: float(activity_weights[index])
                    for index, agent in enumerate(agents)
                },
                "max_conversations_per_agent": max_conversations_per_agent,
                "cooldown_rounds": cooldown_rounds,
            },
            round_index=round_index,
            agent_ids=[agent.agent_id for agent in initiators],
        )

    for source in initiators:
        if capacity[source.agent_id] >= max_conversations_per_agent:
            continue

        neighbor_options: list[tuple[int, float]] = []
        candidate_details: list[dict[str, object]] = []
        skipped: list[dict[str, object]] = []
        for target_id in graph.neighbors(source.agent_id):
            target_id = int(target_id)
            if capacity[target_id] >= max_conversations_per_agent:
                skipped.append({"target_id": target_id, "reason": "target_capacity"})
                continue

            edge_key = tuple(sorted((source.agent_id, target_id)))
            if edge_key in selected_edges:
                skipped.append({"target_id": target_id, "reason": "edge_already_selected"})
                continue

            edge = graph.edges[source.agent_id, target_id]
            last_round = edge.get("last_interaction_round")
            if last_round is not None and round_index - int(last_round) <= cooldown_rounds:
                skipped.append(
                    {
                        "target_id": target_id,
                        "reason": "cooldown",
                        "last_interaction_round": int(last_round),
                    }
                )
                continue

            base_score, score_components = _edge_score_components(
                source, by_id[target_id], edge, dynamics
            )
            jitter = float(rng.uniform(0.90, 1.10))
            score = base_score * jitter
            if score > 0:
                neighbor_options.append((target_id, score))
                candidate_details.append(
                    {
                        "target_id": target_id,
                        "base_score": base_score,
                        "score_components": score_components,
                        "jitter_multiplier": jitter,
                        "candidate_weight": score,
                        "similarity": float(edge.get("similarity", 0.0)),
                        "relationship_strength": float(edge.get("relationship_strength", 0.0)),
                        "trust": float(edge.get("trust", 0.0)),
                        "weak_tie": bool(edge.get("weak_tie", False)),
                    }
                )

        if not neighbor_options:
            if audit is not None:
                audit.emit(
                    "scheduler.candidates",
                    {
                        "source_id": source.agent_id,
                        "candidates": candidate_details,
                        "skipped": skipped,
                        "eligible_weak_count": 0,
                        "eligible_normal_count": 0,
                    },
                    round_index=round_index,
                    agent_ids=[source.agent_id],
                )
            continue

        target_ids = [item[0] for item in neighbor_options]
        weights = np.asarray([item[1] for item in neighbor_options], dtype=float)
        weights /= weights.sum()
        weak_indexes = [
            index for index, detail in enumerate(candidate_details) if bool(detail["weak_tie"])
        ]
        normal_count = len(candidate_details) - len(weak_indexes)
        for detail, probability in zip(candidate_details, weights, strict=True):
            detail["selection_probability"] = float(probability)
        if audit is not None:
            audit.emit(
                "scheduler.candidates",
                {
                    "source_id": source.agent_id,
                    "candidates": candidate_details,
                    "skipped": skipped,
                    "eligible_weak_count": len(weak_indexes),
                    "eligible_normal_count": normal_count,
                },
                round_index=round_index,
                agent_ids=[source.agent_id],
            )

        selection_path = "normal"
        if weak_indexes and float(rng.random()) < dynamics.weak_tie_exploration_weight:
            weak_weights = weights[weak_indexes]
            weak_weights /= weak_weights.sum()
            local_index = int(rng.choice(len(weak_indexes), p=weak_weights))
            chosen_index = weak_indexes[local_index]
            selection_probability = float(weak_weights[local_index])
            selection_path = "weak_exploration"
        else:
            chosen_index = int(rng.choice(len(target_ids), p=weights))
            selection_probability = float(weights[chosen_index])
        target_id = int(target_ids[chosen_index])
        chosen_score = float(neighbor_options[chosen_index][1])

        capacity[source.agent_id] += 1
        capacity[target_id] += 1
        edge_key = tuple(sorted((source.agent_id, target_id)))
        selected_edges.add(edge_key)

        pair = ConversationPair(
            conversation_id=f"r{round_index}-a{source.agent_id}-a{target_id}",
            round_index=round_index,
            agent_a_id=source.agent_id,
            agent_b_id=target_id,
            edge_score=float(chosen_score),
        )
        selected.append(pair)
        if audit is not None:
            audit.emit(
                "scheduler.pair_selected",
                {
                    "source_id": source.agent_id,
                    "target_id": target_id,
                    "candidate_weight": float(chosen_score),
                    "selection_probability": selection_probability,
                    "selection_path": selection_path,
                    "weak_tie": bool(graph.edges[source.agent_id, target_id].get("weak_tie", False)),
                    "capacity_after": {
                        str(source.agent_id): capacity[source.agent_id],
                        str(target_id): capacity[target_id],
                    },
                },
                round_index=round_index,
                conversation_id=pair.conversation_id,
                agent_ids=[source.agent_id, target_id],
            )

    return selected
