from __future__ import annotations

import hashlib
from collections import defaultdict
from collections.abc import Mapping
from itertools import combinations

import networkx as nx
import numpy as np
from sklearn.neighbors import NearestNeighbors

from simulation.audit.logger import RunAuditSink
from simulation.domain.agent import ConsumerAgent
from simulation.network.social_topology import (
    community_affinity,
    community_overlap,
    explicit_social_layers,
    social_feature_vector,
    target_social_degree,
)

SOCIAL_FEATURE_NAMES: tuple[str, ...] = (
    "age_stage",
    "urbanity",
    "sociability",
    "occupation_tech_exposure",
    "occupation_time_pressure",
    "peer_influence",
    "family_influence",
    "social_proof",
    "influencer_susceptibility",
)

DEFAULT_FEATURE_WEIGHTS: dict[str, float] = {
    "age_stage": 0.15,
    "urbanity": 0.10,
    "sociability": 0.18,
    "occupation_tech_exposure": 0.10,
    "occupation_time_pressure": 0.06,
    "peer_influence": 0.12,
    "family_influence": 0.12,
    "social_proof": 0.10,
    "influencer_susceptibility": 0.07,
}

LAYER_RELATIONSHIP_PRIOR: dict[str, float] = {
    "household": 0.68,
    "education": 0.48,
    "workplace": 0.45,
    "local": 0.34,
    "online": 0.28,
    "triadic_closure": 0.23,
    "social_affinity": 0.18,
    "weak_bridge": 0.08,
}

LAYER_INTERACTION_OPPORTUNITY: dict[str, float] = {
    "household": 0.96,
    "education": 0.82,
    "workplace": 0.78,
    "local": 0.60,
    "online": 0.50,
    "triadic_closure": 0.48,
    "social_affinity": 0.42,
    "weak_bridge": 0.20,
}

_LAYER_ORDER: tuple[str, ...] = tuple(LAYER_RELATIONSHIP_PRIOR)


def _stable_seed(seed: int, *parts: object) -> int:
    digest = hashlib.blake2b(
        ":".join(str(part) for part in (seed, *parts)).encode("utf-8"),
        digest_size=8,
    ).digest()
    return int.from_bytes(digest, "big")


def _clip01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _matrix(
    agents: list[ConsumerAgent],
    weights: Mapping[str, float],
) -> np.ndarray:
    unknown = set(weights) - set(SOCIAL_FEATURE_NAMES)
    if unknown:
        raise ValueError(f"unsupported social feature weights: {sorted(unknown)}")
    weight_vector = np.asarray(
        [np.sqrt(max(0.0, float(weights.get(name, 0.0)))) for name in SOCIAL_FEATURE_NAMES],
        dtype=float,
    )
    if not np.any(weight_vector):
        raise ValueError("at least one social feature weight must be positive")
    rows = np.asarray([social_feature_vector(agent) for agent in agents], dtype=float)
    return rows * weight_vector


def _similarity_from_distance(distance: float, sigma: float) -> float:
    if sigma <= 1e-12:
        return 1.0
    return _clip01(float(np.exp(-((float(distance) ** 2) / (2.0 * sigma * sigma)))))


def _directional_trust(
    *,
    left: ConsumerAgent,
    right: ConsumerAgent,
    relationship: float,
    similarity: float,
    affinity: float,
    seed: int,
) -> dict[str, float]:
    result: dict[str, float] = {}
    for truster, other in ((left, right), (right, left)):
        rng = np.random.default_rng(_stable_seed(seed, truster.agent_id, other.agent_id, "trust"))
        social = truster.context.social
        openness = 0.55 * social.peer_influence + 0.45 * social.message_accuracy
        noise = float(rng.normal(0.0, 0.085))
        value = _clip01(
            0.10
            + 0.40 * relationship
            + 0.16 * similarity
            + 0.14 * affinity
            + 0.10 * openness
            + noise
        )
        result[str(truster.agent_id)] = value
    return result


def _logical_layer_for_formation(formation_source: str, weak_tie: bool) -> str:
    if weak_tie or formation_source.startswith("weak_"):
        return "weak_bridge"
    if formation_source.startswith("layer_"):
        layer = formation_source.removeprefix("layer_")
        if layer in LAYER_RELATIONSHIP_PRIOR:
            return layer
    if formation_source == "triadic_closure":
        return "triadic_closure"
    return "social_affinity"


def _ordered_layers(values: set[str]) -> tuple[str, ...]:
    return tuple(
        layer
        for layer in _LAYER_ORDER
        if layer in values
    )


def _edge_layer_metadata(
    left: ConsumerAgent,
    right: ConsumerAgent,
    *,
    formation_sources: tuple[str, ...],
    weak_tie: bool,
) -> tuple[tuple[str, ...], dict[str, float], str, float]:
    layers = set(explicit_social_layers(left, right))
    for source in formation_sources:
        layers.add(_logical_layer_for_formation(source, weak_tie))
    if not layers:
        layers.add("weak_bridge" if weak_tie else "social_affinity")
    ordered = _ordered_layers(layers)
    strengths = {layer: LAYER_RELATIONSHIP_PRIOR[layer] for layer in ordered}
    primary = max(ordered, key=lambda layer: LAYER_RELATIONSHIP_PRIOR[layer])
    opportunity = _clip01(
        max(LAYER_INTERACTION_OPPORTUNITY[layer] for layer in ordered)
        + 0.035 * max(0, len(ordered) - 1)
    )
    return ordered, strengths, primary, opportunity


def _relationship_from_layers(
    *,
    left: ConsumerAgent,
    right: ConsumerAgent,
    layers: tuple[str, ...],
    similarity: float,
    affinity: float,
    seed: int,
    weak_tie: bool,
) -> float:
    strongest = max(LAYER_RELATIONSHIP_PRIOR[layer] for layer in layers)
    multi_layer_bonus = 0.035 * max(0, len(layers) - 1)
    rng = np.random.default_rng(
        _stable_seed(
            seed,
            min(left.agent_id, right.agent_id),
            max(left.agent_id, right.agent_id),
            "relationship-v3",
        )
    )
    noise = float(rng.normal(0.0, 0.045 if not weak_tie else 0.025))
    return _clip01(
        strongest
        + multi_layer_bonus
        + 0.10 * affinity
        + 0.05 * similarity
        + noise
    )


def _add_social_edge(
    graph: nx.Graph,
    left: ConsumerAgent,
    right: ConsumerAgent,
    *,
    distance: float,
    sigma: float,
    seed: int,
    weak_tie: bool,
    formation_source: str,
) -> None:
    existing = graph.get_edge_data(left.agent_id, right.agent_id)
    similarity = _similarity_from_distance(distance, sigma)
    if existing is not None:
        similarity = max(float(existing.get("similarity", 0.0)), similarity)
        distance = min(float(existing.get("social_distance", distance)), float(distance))
        existing_sources = tuple(str(value) for value in existing.get("formation_sources", ()))
        if not existing_sources:
            existing_sources = (str(existing.get("formation_source", formation_source)),)
        formation_sources = tuple(dict.fromkeys((*existing_sources, formation_source)))
        effective_weak_tie = bool(existing.get("weak_tie", False)) and weak_tie
        first_source = str(existing.get("formation_source", formation_source))
        last_round = existing.get("last_interaction_round")
        interaction_count = int(existing.get("interaction_count", 0))
    else:
        formation_sources = (formation_source,)
        effective_weak_tie = weak_tie
        first_source = formation_source
        last_round = None
        interaction_count = 0

    affinity = community_affinity(left, right)
    overlap = community_overlap(left, right)
    layers, layer_strengths, primary_layer, opportunity = _edge_layer_metadata(
        left,
        right,
        formation_sources=formation_sources,
        weak_tie=effective_weak_tie,
    )
    relationship = _relationship_from_layers(
        left=left,
        right=right,
        layers=layers,
        similarity=similarity,
        affinity=affinity,
        seed=seed,
        weak_tie=effective_weak_tie,
    )
    directional = _directional_trust(
        left=left,
        right=right,
        relationship=relationship,
        similarity=similarity,
        affinity=affinity,
        seed=seed,
    )
    if effective_weak_tie:
        directional = {
            key: _clip01(0.65 * value + 0.05)
            for key, value in directional.items()
        }
    trust = sum(directional.values()) / len(directional)

    graph.add_edge(
        left.agent_id,
        right.agent_id,
        similarity=similarity,
        social_distance=float(distance),
        community_affinity=affinity,
        community_overlap=overlap,
        relationship_strength=relationship,
        trust=float(trust),
        directional_trust=directional,
        weak_tie=effective_weak_tie,
        formation_source=first_source,
        formation_sources=formation_sources,
        social_layers=layers,
        layer_strengths=layer_strengths,
        primary_layer=primary_layer,
        interaction_opportunity=opportunity,
        last_interaction_round=last_round,
        interaction_count=interaction_count,
    )


def _crosses_community(left: ConsumerAgent, right: ConsumerAgent) -> bool:
    overlap = set(community_overlap(left, right))
    explicit = set(explicit_social_layers(left, right))
    return not explicit and ("occupation" not in overlap or "life_stage" not in overlap)


def _layer_formation_degree(graph: nx.Graph, agent_id: int, layer: str) -> int:
    source = f"layer_{layer}"
    return sum(
        1
        for neighbor_id in graph.neighbors(agent_id)
        if source in graph.edges[agent_id, neighbor_id].get("formation_sources", ())
    )


def _explicit_formation_degree(graph: nx.Graph, agent_id: int) -> int:
    return sum(
        1
        for neighbor_id in graph.neighbors(agent_id)
        if any(
            str(source).startswith("layer_")
            for source in graph.edges[agent_id, neighbor_id].get("formation_sources", ())
        )
    )


def _membership_groups(
    agents: list[ConsumerAgent],
) -> dict[str, dict[str, list[ConsumerAgent]]]:
    groups: dict[str, dict[str, list[ConsumerAgent]]] = {
        layer: defaultdict(list)
        for layer in ("household", "workplace", "local", "education", "online")
    }
    for agent in agents:
        memberships = agent.context.memberships
        if memberships.household_id:
            groups["household"][memberships.household_id].append(agent)
        if memberships.workplace_id:
            groups["workplace"][memberships.workplace_id].append(agent)
        if memberships.locality_id and memberships.locality_id != "unspecified":
            groups["local"][memberships.locality_id].append(agent)
        if memberships.education_id:
            groups["education"][memberships.education_id].append(agent)
        for interest_id in memberships.online_interest_ids:
            groups["online"][interest_id].append(agent)
    return groups


def _add_explicit_layer_edges(
    graph: nx.Graph,
    *,
    agents: list[ConsumerAgent],
    matrix: np.ndarray,
    sigma: float,
    target_degrees: Mapping[int, int],
    seed: int,
) -> None:
    row_by_id = {agent.agent_id: index for index, agent in enumerate(agents)}
    groups = _membership_groups(agents)
    layer_degrees: dict[str, defaultdict[int, int]] = {
        layer: defaultdict(int)
        for layer in ("household", "workplace", "local", "education", "online")
    }
    explicit_neighbors: defaultdict[int, set[int]] = defaultdict(set)

    for group_id, members in sorted(groups["household"].items()):
        if len(members) < 2:
            continue
        for left, right in combinations(sorted(members, key=lambda agent: agent.agent_id), 2):
            left_row = row_by_id[left.agent_id]
            right_row = row_by_id[right.agent_id]
            distance = float(np.linalg.norm(matrix[left_row] - matrix[right_row]))
            _add_social_edge(
                graph,
                left,
                right,
                distance=distance,
                sigma=sigma,
                seed=seed,
                weak_tie=False,
                formation_source="layer_household",
            )
            layer_degrees["household"][left.agent_id] += 1
            layer_degrees["household"][right.agent_id] += 1
            explicit_neighbors[left.agent_id].add(right.agent_id)
            explicit_neighbors[right.agent_id].add(left.agent_id)

    caps = {
        "workplace": 4,
        "education": 5,
        "local": 3,
        "online": 4,
    }
    for layer, cap in caps.items():
        for group_id, members in sorted(groups[layer].items()):
            if len(members) < 2:
                continue
            pairs = list(combinations(sorted(members, key=lambda agent: agent.agent_id), 2))
            rng = np.random.default_rng(_stable_seed(seed, layer, group_id, "layer-pairs"))
            if len(pairs) > 1:
                order = rng.permutation(len(pairs))
                pairs = [pairs[int(index)] for index in order]
            for left, right in pairs:
                if layer_degrees[layer][left.agent_id] >= cap:
                    continue
                if layer_degrees[layer][right.agent_id] >= cap:
                    continue
                source_name = f"layer_{layer}"
                already_layer = graph.has_edge(left.agent_id, right.agent_id) and source_name in graph.edges[
                    left.agent_id, right.agent_id
                ].get("formation_sources", ())
                if already_layer:
                    continue
                already_explicit = right.agent_id in explicit_neighbors[left.agent_id]
                if not already_explicit:
                    left_budget = max(
                        layer_degrees["household"][left.agent_id],
                        max(2, int(round(target_degrees[left.agent_id] * 0.62))),
                    )
                    right_budget = max(
                        layer_degrees["household"][right.agent_id],
                        max(2, int(round(target_degrees[right.agent_id] * 0.62))),
                    )
                    if len(explicit_neighbors[left.agent_id]) >= left_budget:
                        continue
                    if len(explicit_neighbors[right.agent_id]) >= right_budget:
                        continue
                left_row = row_by_id[left.agent_id]
                right_row = row_by_id[right.agent_id]
                distance = float(np.linalg.norm(matrix[left_row] - matrix[right_row]))
                _add_social_edge(
                    graph,
                    left,
                    right,
                    distance=distance,
                    sigma=sigma,
                    seed=seed,
                    weak_tie=False,
                    formation_source=source_name,
                )
                layer_degrees[layer][left.agent_id] += 1
                layer_degrees[layer][right.agent_id] += 1
                explicit_neighbors[left.agent_id].add(right.agent_id)
                explicit_neighbors[right.agent_id].add(left.agent_id)


def _add_triadic_closure(
    graph: nx.Graph,
    *,
    agents: list[ConsumerAgent],
    matrix: np.ndarray,
    sigma: float,
    target_degrees: Mapping[int, int],
    seed: int,
) -> None:
    by_id = {agent.agent_id: agent for agent in agents}
    row_by_id = {agent.agent_id: index for index, agent in enumerate(agents)}

    for source in agents:
        target_degree = int(target_degrees[source.agent_id])
        soft_cap = min(len(agents) - 1, max(target_degree + 1, int(round(target_degree * 1.45))))
        remaining = soft_cap - graph.degree(source.agent_id)
        if remaining <= 0:
            continue
        budget = min(remaining, max(1, int(round(target_degree * 0.10))))

        direct = set(int(value) for value in graph.neighbors(source.agent_id))
        common_counts: dict[int, int] = {}
        for neighbor_id in direct:
            for candidate_id in graph.neighbors(neighbor_id):
                candidate_id = int(candidate_id)
                if candidate_id == source.agent_id or candidate_id in direct:
                    continue
                common_counts[candidate_id] = common_counts.get(candidate_id, 0) + 1
        if not common_counts:
            continue

        candidate_ids = list(common_counts)
        source_row = row_by_id[source.agent_id]
        rows = np.asarray([row_by_id[candidate_id] for candidate_id in candidate_ids], dtype=int)
        distances = np.linalg.norm(matrix[rows] - matrix[source_row], axis=1)
        weights: list[float] = []
        for index, candidate_id in enumerate(candidate_ids):
            similarity = _similarity_from_distance(float(distances[index]), sigma)
            affinity = community_affinity(source, by_id[candidate_id])
            closure = min(1.0, common_counts[candidate_id] / 4.0)
            weights.append(max(1e-6, 0.15 * similarity + 0.30 * affinity + 0.75 * closure))

        rng = np.random.default_rng(_stable_seed(seed, source.agent_id, "triadic-closure"))
        jitter = rng.uniform(0.98, 1.02, size=len(weights))
        ranked = np.argsort(-(np.asarray(weights, dtype=float) * jitter))
        choose_count = min(budget, len(candidate_ids))
        chosen = ranked[:choose_count]
        for local_index in np.atleast_1d(chosen):
            candidate_id = int(candidate_ids[int(local_index)])
            if graph.has_edge(source.agent_id, candidate_id):
                continue
            _add_social_edge(
                graph,
                source,
                by_id[candidate_id],
                distance=float(distances[int(local_index)]),
                sigma=sigma,
                seed=seed,
                weak_tie=False,
                formation_source="triadic_closure",
            )


def _add_structured_weak_ties(
    graph: nx.Graph,
    *,
    agents: list[ConsumerAgent],
    matrix: np.ndarray,
    sigma: float,
    target_edges: int,
    seed: int,
) -> None:
    if target_edges <= 0:
        return
    by_id = {agent.agent_id: agent for agent in agents}
    row_by_id = {agent.agent_id: index for index, agent in enumerate(agents)}
    ids = [agent.agent_id for agent in agents]
    rng = np.random.default_rng(_stable_seed(seed, "weak-ties"))
    added = 0
    attempts = 0
    max_attempts = max(200, target_edges * 40)

    while added < target_edges and attempts < max_attempts:
        attempts += 1
        source_id = int(rng.choice(ids))
        source_neighbors = set(int(value) for value in graph.neighbors(source_id))
        two_hop: set[int] = set()
        for neighbor_id in source_neighbors:
            two_hop.update(int(value) for value in graph.neighbors(neighbor_id))
        two_hop.discard(source_id)
        two_hop.difference_update(source_neighbors)
        candidates = [
            target_id
            for target_id in two_hop
            if _crosses_community(by_id[source_id], by_id[target_id])
        ]
        formation_source = "weak_two_hop"

        if not candidates:
            sampled = rng.choice(ids, size=min(len(ids), 24), replace=False).tolist()
            candidates = [
                int(target_id)
                for target_id in sampled
                if int(target_id) != source_id
                and int(target_id) not in source_neighbors
                and _crosses_community(by_id[source_id], by_id[int(target_id)])
            ]
            formation_source = "weak_cross_community"

        if not candidates:
            candidates = [
                int(target_id)
                for target_id in rng.choice(ids, size=min(len(ids), 24), replace=False).tolist()
                if int(target_id) != source_id and int(target_id) not in source_neighbors
            ]
            formation_source = "weak_random_fallback"
        if not candidates:
            continue

        source_row = row_by_id[source_id]
        candidate_rows = np.asarray([row_by_id[target_id] for target_id in candidates], dtype=int)
        distances = np.linalg.norm(matrix[candidate_rows] - matrix[source_row], axis=1)
        affinities = np.asarray(
            [community_affinity(by_id[source_id], by_id[target_id]) for target_id in candidates],
            dtype=float,
        )
        bridge_weights = 0.35 + 0.65 * (1.0 - affinities)
        bridge_weights = bridge_weights / bridge_weights.sum()
        chosen_index = int(rng.choice(len(candidates), p=bridge_weights))
        target_id = int(candidates[chosen_index])
        if graph.has_edge(source_id, target_id):
            continue
        _add_social_edge(
            graph,
            by_id[source_id],
            by_id[target_id],
            distance=float(distances[chosen_index]),
            sigma=sigma,
            seed=seed,
            weak_tie=True,
            formation_source=formation_source,
        )
        added += 1


def build_knn_graph(
    agents: list[ConsumerAgent],
    k: int,
    weak_tie_rate: float = 0.05,
    seed: int = 42,
    feature_weights: Mapping[str, float] | None = None,
    audit: RunAuditSink | None = None,
) -> nx.Graph:
    """Build the V2 persistent social graph.

    `k` defines social-candidate search breadth/scale. Final degree is heterogeneous
    and is not constrained to exactly `k`.
    """
    if len(agents) < 2:
        raise ValueError("At least two agents are required to build a social graph.")
    if not 0 <= weak_tie_rate <= 1:
        raise ValueError("weak_tie_rate must be between 0 and 1.")
    if k < 1:
        raise ValueError("k must be at least 1")

    weights = dict(feature_weights or DEFAULT_FEATURE_WEIGHTS)
    matrix = _matrix(agents, weights)
    population_size = len(agents)
    effective_k = min(max(1, k), population_size - 1)
    target_degrees = {
        agent.agent_id: target_social_degree(
            agent,
            base_k=effective_k,
            population_size=population_size,
            seed=seed,
        )
        for agent in agents
    }
    max_target = max(target_degrees.values())
    candidate_count = min(
        population_size - 1,
        max(effective_k * 5, max_target + effective_k),
    )
    nearest = NearestNeighbors(n_neighbors=candidate_count + 1, metric="euclidean")
    nearest.fit(matrix)
    distances, indexes = nearest.kneighbors(matrix)
    candidate_distances = distances[:, 1:].reshape(-1)
    positive_distances = candidate_distances[candidate_distances > 1e-12]
    sigma = float(np.median(positive_distances)) if positive_distances.size else 1.0

    graph = nx.Graph()
    for agent in agents:
        memberships = agent.context.memberships
        graph.add_node(
            agent.agent_id,
            target_social_degree=int(target_degrees[agent.agent_id]),
            region_id=memberships.region_id,
            city_id=memberships.city_id,
            city_tier=memberships.city_tier,
            locality_id=memberships.locality_id,
            household_id=memberships.household_id,
            workplace_id=memberships.workplace_id,
            education_id=memberships.education_id,
            online_interest_ids=memberships.online_interest_ids,
        )

    _add_explicit_layer_edges(
        graph,
        agents=agents,
        matrix=matrix,
        sigma=sigma,
        target_degrees=target_degrees,
        seed=seed,
    )

    for row, source in enumerate(agents):
        remaining_degree = max(0, target_degrees[source.agent_id] - graph.degree(source.agent_id))
        if remaining_degree <= 0:
            continue
        local_distances = distances[row][1:]
        local_indexes = indexes[row][1:]
        eligible_positions = [
            index
            for index, target_index in enumerate(local_indexes)
            if not graph.has_edge(source.agent_id, agents[int(target_index)].agent_id)
        ]
        if not eligible_positions:
            continue
        eligible_distances = np.asarray(
            [local_distances[index] for index in eligible_positions],
            dtype=float,
        )
        eligible_indexes = np.asarray(
            [local_indexes[index] for index in eligible_positions],
            dtype=int,
        )
        similarities = np.asarray(
            [_similarity_from_distance(float(distance), sigma) for distance in eligible_distances],
            dtype=float,
        )
        affinities = np.asarray(
            [community_affinity(source, agents[int(index)]) for index in eligible_indexes],
            dtype=float,
        )
        candidate_weights = 0.55 * similarities + 0.45 * affinities
        candidate_weights = np.maximum(candidate_weights, 1e-6)
        candidate_weights = candidate_weights / candidate_weights.sum()

        nomination_target = min(
            len(eligible_indexes),
            max(1, int(round(remaining_degree * 0.62))),
        )
        rng = np.random.default_rng(_stable_seed(seed, source.agent_id, "nominations"))
        chosen = rng.choice(
            len(eligible_indexes),
            size=nomination_target,
            replace=False,
            p=candidate_weights,
        )
        for local_index in np.atleast_1d(chosen):
            target = agents[int(eligible_indexes[int(local_index)])]
            _add_social_edge(
                graph,
                source,
                target,
                distance=float(eligible_distances[int(local_index)]),
                sigma=sigma,
                seed=seed,
                weak_tie=False,
                formation_source="social_candidate",
            )

    _add_triadic_closure(
        graph,
        agents=agents,
        matrix=matrix,
        sigma=sigma,
        target_degrees=target_degrees,
        seed=seed,
    )

    target_weak_edges = int(round(graph.number_of_edges() * weak_tie_rate))
    _add_structured_weak_ties(
        graph,
        agents=agents,
        matrix=matrix,
        sigma=sigma,
        target_edges=target_weak_edges,
        seed=seed,
    )

    if audit is not None:
        audit.emit(
            "network.built",
            {
                "version": "layered-social-topology-v3",
                "node_count": graph.number_of_nodes(),
                "edge_count": graph.number_of_edges(),
                "requested_k": k,
                "effective_k": effective_k,
                "candidate_count": candidate_count,
                "distance_sigma": sigma,
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
                        name: float(value)
                        for name, value in zip(SOCIAL_FEATURE_NAMES, social_feature_vector(agent), strict=True)
                    },
                    "weighted_vector": [float(value) for value in vector],
                    "feature_order": list(SOCIAL_FEATURE_NAMES),
                    "target_social_degree": target_degrees[agent.agent_id],
                },
                agent_ids=[agent.agent_id],
            )
        for source_id, target_id, data in graph.edges(data=True):
            audit.emit(
                "network.edge",
                {
                    "source": int(source_id),
                    "target": int(target_id),
                    "formation_source": data.get("formation_source", "social_candidate"),
                    "knn_distance": data.get("social_distance"),
                    **dict(data),
                },
                agent_ids=[int(source_id), int(target_id)],
            )

    return graph
