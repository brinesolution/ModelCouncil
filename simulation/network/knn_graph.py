from __future__ import annotations

from collections.abc import Mapping

import networkx as nx
import numpy as np
from sklearn.neighbors import NearestNeighbors

from simulation.domain.agent import ConsumerAgent
from simulation.audit.logger import RunAuditSink

DEFAULT_FEATURE_WEIGHTS: dict[str, float] = {
    "price_sensitivity": 0.17,
    "technology_adoption": 0.17,
    "emotionality": 0.10,
    "logicality": 0.10,
    "stubbornness": 0.08,
    "product_need": 0.16,
    "risk_tolerance": 0.08,
    "brand_loyalty": 0.06,
    "income_score": 0.08,
}


def _vector(agent: ConsumerAgent, weights: Mapping[str, float]) -> list[float]:
    values: dict[str, float] = {
        **agent.traits.as_dict(),
        "income_score": agent.income_score,
    }
    return [values[name] * np.sqrt(weight) for name, weight in weights.items()]


def build_knn_graph(
    agents: list[ConsumerAgent],
    k: int,
    weak_tie_rate: float = 0.05,
    seed: int = 42,
    feature_weights: Mapping[str, float] | None = None,
    audit: RunAuditSink | None = None,
) -> nx.Graph:
    if len(agents) < 2:
        raise ValueError("At least two agents are required to build a social graph.")
    if not 0 <= weak_tie_rate <= 1:
        raise ValueError("weak_tie_rate must be between 0 and 1.")

    weights = feature_weights or DEFAULT_FEATURE_WEIGHTS
    effective_k = min(max(1, k), len(agents) - 1)
    matrix = np.asarray([_vector(agent, weights) for agent in agents], dtype=float)

    nearest = NearestNeighbors(n_neighbors=effective_k + 1, metric="euclidean")
    nearest.fit(matrix)
    distances, indexes = nearest.kneighbors(matrix)

    graph = nx.Graph()
    for agent in agents:
        graph.add_node(agent.agent_id)

    for row, source in enumerate(agents):
        for distance, neighbor_index in zip(distances[row][1:], indexes[row][1:], strict=True):
            target = agents[int(neighbor_index)]
            similarity = float(np.exp(-float(distance)))
            graph.add_edge(
                source.agent_id,
                target.agent_id,
                similarity=similarity,
                relationship_strength=0.35 + 0.45 * similarity,
                trust=0.30 + 0.45 * similarity,
                weak_tie=False,
                last_interaction_round=None,
                interaction_count=0,
            )

    rng = np.random.default_rng(seed)
    target_weak_edges = int(round(graph.number_of_edges() * weak_tie_rate))
    ids = [agent.agent_id for agent in agents]
    attempts = 0
    added = 0
    max_attempts = max(100, target_weak_edges * 30)

    while added < target_weak_edges and attempts < max_attempts:
        attempts += 1
        source_id, target_id = rng.choice(ids, size=2, replace=False).tolist()
        if graph.has_edge(source_id, target_id):
            continue
        graph.add_edge(
            int(source_id),
            int(target_id),
            similarity=0.15,
            relationship_strength=0.20,
            trust=0.20,
            weak_tie=True,
            last_interaction_round=None,
            interaction_count=0,
        )
        added += 1

    if audit is not None:
        audit.emit(
            "network.built",
            {
                "node_count": graph.number_of_nodes(),
                "edge_count": graph.number_of_edges(),
                "requested_k": k,
                "effective_k": effective_k,
                "weak_tie_rate": weak_tie_rate,
                "weak_tie_edges": sum(
                    1 for _, _, data in graph.edges(data=True) if data.get("weak_tie")
                ),
                "feature_weights": dict(weights),
            },
        )
        for agent, vector in zip(agents, matrix, strict=True):
            audit.emit(
                "network.agent_vector",
                {
                    "agent_id": agent.agent_id,
                    "raw_features": {
                        **agent.traits.as_dict(),
                        "income_score": agent.income_score,
                    },
                    "weighted_vector": [float(value) for value in vector],
                    "feature_order": list(weights),
                },
                agent_ids=[agent.agent_id],
            )
        for source_id, target_id, data in graph.edges(data=True):
            weak_tie = bool(data.get("weak_tie", False))
            similarity = float(data.get("similarity", 0.0))
            knn_distance = (
                float(-np.log(similarity)) if not weak_tie and similarity > 0 else None
            )
            audit.emit(
                "network.edge",
                {
                    "source": int(source_id),
                    "target": int(target_id),
                    "formation_source": "weak_tie" if weak_tie else "knn",
                    "knn_distance": knn_distance,
                    **dict(data),
                },
                agent_ids=[int(source_id), int(target_id)],
            )

    return graph
