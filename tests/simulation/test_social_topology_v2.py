from copy import deepcopy

import numpy as np

from pathlib import Path

from simulation.network.knn_graph import build_knn_graph
from simulation.network.social_topology import edge_trust, occupation_key, social_feature_vector, target_social_degree
from simulation.population.excel_repository import ExcelTraitRepository
from simulation.population.generator import generate_population


TRAIT_ROOT = Path("data/traits")


def test_social_feature_vector_excludes_purchase_response_fields():
    agent = generate_population(2, seed=2101)[0]
    changed = deepcopy(agent)
    changed.traits.product_need = 0.99 if agent.traits.product_need < 0.5 else 0.01
    changed.traits.price_sensitivity = 0.99 if agent.traits.price_sensitivity < 0.5 else 0.01
    changed.traits.brand_loyalty = 0.99 if agent.traits.brand_loyalty < 0.5 else 0.01
    changed.income_score = 0.99 if agent.income_score < 0.5 else 0.01

    assert social_feature_vector(agent) == social_feature_vector(changed)


def test_target_social_degree_is_deterministic_heterogeneous_and_socially_related():
    agents = generate_population(500, seed=2102)

    first = np.asarray(
        [target_social_degree(agent, base_k=14, population_size=len(agents), seed=77) for agent in agents],
        dtype=float,
    )
    second = np.asarray(
        [target_social_degree(agent, base_k=14, population_size=len(agents), seed=77) for agent in agents],
        dtype=float,
    )
    sociability = np.asarray([agent.traits.sociability for agent in agents], dtype=float)

    assert np.array_equal(first, second)
    assert len(set(first.tolist())) >= 12
    assert float(np.std(first)) >= 4.0
    correlation = float(np.corrcoef(first, sociability)[0, 1])
    assert 0.20 <= correlation <= 0.85
    assert first.min() >= 3
    assert first.max() <= 56


def test_graph_topology_is_invariant_to_purchase_response_fields_when_social_context_is_fixed():
    agents = generate_population(160, seed=2103, traits=ExcelTraitRepository(TRAIT_ROOT))
    changed = deepcopy(agents)
    for agent in changed:
        agent.traits.product_need = 1.0 - agent.traits.product_need
        agent.traits.price_sensitivity = 1.0 - agent.traits.price_sensitivity
        agent.traits.brand_loyalty = 1.0 - agent.traits.brand_loyalty
        agent.income_score = 1.0 - agent.income_score

    first = build_knn_graph(agents, k=12, weak_tie_rate=0.0, seed=88)
    second = build_knn_graph(changed, k=12, weak_tie_rate=0.0, seed=88)

    assert set(first.edges()) == set(second.edges())


def test_v2_graph_has_heterogeneous_degree_and_uncompressed_edge_strengths():
    agents = generate_population(600, seed=2104, traits=ExcelTraitRepository(TRAIT_ROOT))
    graph = build_knn_graph(agents, k=14, weak_tie_rate=0.05, seed=89)

    degrees = np.asarray([degree for _, degree in graph.degree()], dtype=float)
    target_degrees = np.asarray(
        [float(graph.nodes[node]["target_social_degree"]) for node in graph.nodes],
        dtype=float,
    )
    normal = [data for _, _, data in graph.edges(data=True) if not data.get("weak_tie")]
    similarities = np.asarray([float(data["similarity"]) for data in normal], dtype=float)
    relationships = np.asarray([float(data["relationship_strength"]) for data in normal], dtype=float)

    assert float(np.std(target_degrees)) >= 4.0
    assert float(np.percentile(degrees, 90) - np.percentile(degrees, 10)) >= 10.0
    assert float(np.percentile(degrees, 10)) <= 10.0
    assert float(np.median(degrees)) <= 18.0
    assert float(np.percentile(degrees, 90)) >= 24.0
    assert float(np.percentile(similarities, 90) - np.percentile(similarities, 10)) >= 0.12
    assert float(np.std(relationships)) >= 0.05

    import networkx as nx

    largest_component = max(len(component) for component in nx.connected_components(graph))
    assert largest_component / len(agents) >= 0.95


def test_social_graph_has_bounded_triadic_closure_for_local_community_structure():
    import networkx as nx

    agents = generate_population(600, seed=2108, traits=ExcelTraitRepository(TRAIT_ROOT))
    graph = build_knn_graph(agents, k=14, weak_tie_rate=0.05, seed=93)
    normal_edges = [data for _, _, data in graph.edges(data=True) if not data.get("weak_tie")]
    triadic_share = sum(data.get("formation_source") == "triadic_closure" for data in normal_edges) / len(normal_edges)

    assert triadic_share >= 0.03
    assert nx.average_clustering(graph) >= 0.18


def test_social_graph_is_more_occupation_assortative_than_random_pairing():
    agents = generate_population(700, seed=2105, traits=ExcelTraitRepository(TRAIT_ROOT))
    graph = build_knn_graph(agents, k=14, weak_tie_rate=0.0, seed=90)
    by_id = {agent.agent_id: agent for agent in agents}

    edge_match_share = sum(
        occupation_key(by_id[left]) == occupation_key(by_id[right])
        for left, right in graph.edges()
    ) / graph.number_of_edges()

    rng = np.random.default_rng(90)
    ids = np.asarray([agent.agent_id for agent in agents], dtype=int)
    random_matches = []
    for _ in range(graph.number_of_edges()):
        left, right = rng.choice(ids, size=2, replace=False).tolist()
        random_matches.append(occupation_key(by_id[int(left)]) == occupation_key(by_id[int(right)]))
    random_match_share = sum(random_matches) / len(random_matches)

    assert edge_match_share >= random_match_share + 0.05


def test_directional_trust_can_differ_and_legacy_trust_still_falls_back():
    agents = generate_population(120, seed=2106, traits=ExcelTraitRepository(TRAIT_ROOT))
    graph = build_knn_graph(agents, k=10, weak_tie_rate=0.0, seed=91)

    found_asymmetric = False
    for left, right, edge in graph.edges(data=True):
        left_trusts_right = edge_trust(edge, int(left))
        right_trusts_left = edge_trust(edge, int(right))
        assert 0.0 <= left_trusts_right <= 1.0
        assert 0.0 <= right_trusts_left <= 1.0
        if abs(left_trusts_right - right_trusts_left) >= 0.01:
            found_asymmetric = True
            break

    assert found_asymmetric
    assert edge_trust({"trust": 0.63}, 123) == 0.63


def test_weak_ties_are_structured_cross_community_bridges():
    agents = generate_population(700, seed=2107, traits=ExcelTraitRepository(TRAIT_ROOT))
    graph = build_knn_graph(agents, k=14, weak_tie_rate=0.08, seed=92)
    weak_edges = [(left, right, data) for left, right, data in graph.edges(data=True) if data.get("weak_tie")]

    assert len(weak_edges) > 100
    structured_share = sum(
        str(data.get("formation_source", "")).startswith(("weak_two_hop", "weak_cross_community"))
        for _, _, data in weak_edges
    ) / len(weak_edges)
    cross_community_share = sum(
        not ({"occupation", "life_stage"} <= set(data.get("community_overlap", ())))
        for _, _, data in weak_edges
    ) / len(weak_edges)

    assert structured_share >= 0.90
    assert cross_community_share >= 0.90
