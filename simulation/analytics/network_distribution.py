from __future__ import annotations

from dataclasses import dataclass

import networkx as nx
import numpy as np


@dataclass(frozen=True, slots=True)
class NetworkDistributionMetrics:
    node_count: int
    edge_count: int
    mean_degree: float
    median_degree: float
    degree_std: float
    degree_p10: float
    degree_p90: float
    degree_p99: float
    max_degree: int
    degree_gini: float
    target_degree_mean: float
    target_degree_std: float
    connected_components: int
    largest_component_share: float
    clustering_coefficient: float
    weak_tie_share: float
    structured_weak_tie_share: float
    cross_community_edge_share: float
    similarity_mean: float
    similarity_std: float
    similarity_p10: float
    similarity_p90: float
    relationship_mean: float
    relationship_std: float
    directional_trust_mean: float
    directional_trust_std: float
    household_edge_share: float
    workplace_edge_share: float
    local_edge_share: float
    education_edge_share: float
    online_edge_share: float
    affinity_edge_share: float
    multi_layer_edge_share: float
    household_membership_share: float
    workplace_membership_share: float
    education_membership_share: float
    online_membership_share: float


def _mean(values: list[float]) -> float:
    return float(np.mean(values)) if values else 0.0


def _std(values: list[float]) -> float:
    return float(np.std(values)) if values else 0.0


def _percentile(values: list[float], percentile: float) -> float:
    return float(np.percentile(values, percentile)) if values else 0.0


def _gini(values: list[float]) -> float:
    if not values:
        return 0.0
    array = np.asarray(values, dtype=float)
    if np.allclose(array, 0.0):
        return 0.0
    array = np.sort(np.maximum(array, 0.0))
    count = array.size
    index = np.arange(1, count + 1, dtype=float)
    return float((np.sum((2.0 * index - count - 1.0) * array)) / (count * np.sum(array)))


def compute_network_distribution_metrics(graph: nx.Graph) -> NetworkDistributionMetrics:
    node_count = graph.number_of_nodes()
    edge_count = graph.number_of_edges()
    degrees = [float(degree) for _, degree in graph.degree()]
    target_degrees = [
        float(data.get("target_social_degree", 0.0))
        for _, data in graph.nodes(data=True)
        if data.get("target_social_degree") is not None
    ]
    edge_rows = list(graph.edges(data=True))
    similarities = [float(data.get("similarity", 0.0)) for _, _, data in edge_rows]
    relationships = [float(data.get("relationship_strength", 0.0)) for _, _, data in edge_rows]
    directional_trust: list[float] = []
    for _, _, data in edge_rows:
        values = data.get("directional_trust")
        if isinstance(values, dict):
            directional_trust.extend(float(value) for value in values.values())
        elif data.get("trust") is not None:
            directional_trust.append(float(data.get("trust", 0.0)))

    weak_edges = [data for _, _, data in edge_rows if bool(data.get("weak_tie", False))]
    layer_counts = {
        layer: sum(
            1
            for _, _, data in edge_rows
            if layer in set(data.get("social_layers", ()))
        )
        for layer in ("household", "workplace", "local", "education", "online", "social_affinity")
    }
    multi_layer_edges = sum(
        1
        for _, _, data in edge_rows
        if len(tuple(data.get("social_layers", ()))) > 1
    )
    node_rows = list(graph.nodes(data=True))
    household_members = sum(1 for _, data in node_rows if data.get("household_id"))
    workplace_members = sum(1 for _, data in node_rows if data.get("workplace_id"))
    education_members = sum(1 for _, data in node_rows if data.get("education_id"))
    online_members = sum(1 for _, data in node_rows if tuple(data.get("online_interest_ids", ())))
    structured_weak = [
        data
        for data in weak_edges
        if str(data.get("formation_source", "")) in {"weak_two_hop", "weak_cross_community"}
    ]
    cross_community = 0
    for _, _, data in edge_rows:
        overlap = set(data.get("community_overlap", ()))
        if "occupation" not in overlap and "life_stage" not in overlap:
            cross_community += 1

    if node_count:
        components = list(nx.connected_components(graph))
        connected_components = len(components)
        largest_component_share = max((len(component) for component in components), default=0) / node_count
    else:
        connected_components = 0
        largest_component_share = 0.0

    return NetworkDistributionMetrics(
        node_count=node_count,
        edge_count=edge_count,
        mean_degree=_mean(degrees),
        median_degree=float(np.median(degrees)) if degrees else 0.0,
        degree_std=_std(degrees),
        degree_p10=_percentile(degrees, 10),
        degree_p90=_percentile(degrees, 90),
        degree_p99=_percentile(degrees, 99),
        max_degree=int(max(degrees, default=0.0)),
        degree_gini=_gini(degrees),
        target_degree_mean=_mean(target_degrees),
        target_degree_std=_std(target_degrees),
        connected_components=connected_components,
        largest_component_share=float(largest_component_share),
        clustering_coefficient=(float(nx.average_clustering(graph)) if node_count > 1 else 0.0),
        weak_tie_share=(len(weak_edges) / edge_count if edge_count else 0.0),
        structured_weak_tie_share=(len(structured_weak) / len(weak_edges) if weak_edges else 0.0),
        cross_community_edge_share=(cross_community / edge_count if edge_count else 0.0),
        similarity_mean=_mean(similarities),
        similarity_std=_std(similarities),
        similarity_p10=_percentile(similarities, 10),
        similarity_p90=_percentile(similarities, 90),
        relationship_mean=_mean(relationships),
        relationship_std=_std(relationships),
        directional_trust_mean=_mean(directional_trust),
        directional_trust_std=_std(directional_trust),
        household_edge_share=(layer_counts["household"] / edge_count if edge_count else 0.0),
        workplace_edge_share=(layer_counts["workplace"] / edge_count if edge_count else 0.0),
        local_edge_share=(layer_counts["local"] / edge_count if edge_count else 0.0),
        education_edge_share=(layer_counts["education"] / edge_count if edge_count else 0.0),
        online_edge_share=(layer_counts["online"] / edge_count if edge_count else 0.0),
        affinity_edge_share=(layer_counts["social_affinity"] / edge_count if edge_count else 0.0),
        multi_layer_edge_share=(multi_layer_edges / edge_count if edge_count else 0.0),
        household_membership_share=(household_members / node_count if node_count else 0.0),
        workplace_membership_share=(workplace_members / node_count if node_count else 0.0),
        education_membership_share=(education_members / node_count if node_count else 0.0),
        online_membership_share=(online_members / node_count if node_count else 0.0),
    )
