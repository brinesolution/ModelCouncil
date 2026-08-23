from __future__ import annotations

from collections import Counter
from pathlib import Path

import networkx as nx

from simulation.analytics.network_distribution import compute_network_distribution_metrics
from simulation.domain.consumer_context import SocialMembershipContext
from simulation.network import knn_graph, social_topology
from simulation.population.excel_repository import ExcelTraitRepository
from simulation.population.generator import generate_population


TRAIT_ROOT = Path("data/traits")


def _base_pair(seed: int = 1201):
    left, right = generate_population(2, seed=seed)
    left.occupation = right.occupation = "Software Professional"
    left.context.occupation.key = right.context.occupation.key = "software_tech"
    left.context.demographic.household_tendency = "family"
    right.context.demographic.household_tendency = "family"
    return left, right


def test_same_occupation_and_household_tendency_do_not_fake_explicit_membership() -> None:
    left, right = _base_pair()
    left.context.memberships = SocialMembershipContext(
        region_id="region-000",
        city_id="city-t1-0000",
        city_tier=1,
        locality_id="locality-a",
        household_id="household-a",
        workplace_id="workplace-a",
        online_interest_ids=("online-technology-000",),
    )
    right.context.memberships = SocialMembershipContext(
        region_id="region-000",
        city_id="city-t1-0000",
        city_tier=1,
        locality_id="locality-b",
        household_id="household-b",
        workplace_id="workplace-b",
        online_interest_ids=("online-learning-000",),
    )

    layers = social_topology.explicit_social_layers(left, right)
    overlap = set(social_topology.community_overlap(left, right))

    assert "household" not in layers
    assert "workplace" not in layers
    assert "local" not in layers
    assert "online" not in layers
    assert "occupation" in overlap
    assert "household_tendency" in overlap
    assert "household" not in overlap


def test_explicit_social_layers_detect_shared_persistent_memberships() -> None:
    left, right = _base_pair(seed=1202)
    shared = SocialMembershipContext(
        region_id="region-000",
        city_id="city-t1-0000",
        city_tier=1,
        locality_id="locality-a",
        household_id="household-a",
        workplace_id="workplace-a",
        education_id="education-a",
        online_interest_ids=("online-technology-000", "online-learning-000"),
    )
    left.context.memberships = shared
    right.context.memberships = SocialMembershipContext(
        region_id=shared.region_id,
        city_id=shared.city_id,
        city_tier=shared.city_tier,
        locality_id=shared.locality_id,
        household_id=shared.household_id,
        workplace_id=shared.workplace_id,
        education_id=shared.education_id,
        online_interest_ids=("online-technology-000",),
    )

    layers = set(social_topology.explicit_social_layers(left, right))

    assert layers == {"household", "workplace", "local", "education", "online"}


def test_explicit_membership_affinity_is_stronger_than_coarse_similarity_only() -> None:
    shared_left, shared_right = _base_pair(seed=1203)
    coarse_left, coarse_right = _base_pair(seed=1204)

    shared_left.context.memberships.household_id = "household-shared"
    shared_right.context.memberships.household_id = "household-shared"
    shared_left.context.memberships.locality_id = "locality-shared"
    shared_right.context.memberships.locality_id = "locality-shared"

    coarse_left.context.memberships.household_id = "household-left"
    coarse_right.context.memberships.household_id = "household-right"
    coarse_left.context.memberships.locality_id = "locality-left"
    coarse_right.context.memberships.locality_id = "locality-right"

    assert social_topology.community_affinity(shared_left, shared_right) > social_topology.community_affinity(
        coarse_left,
        coarse_right,
    )


def test_edge_metadata_merges_multiple_social_layers_for_one_pair() -> None:
    left, right = _base_pair(seed=1205)
    left.context.memberships.household_id = right.context.memberships.household_id = "household-shared"
    left.context.memberships.locality_id = right.context.memberships.locality_id = "locality-shared"
    graph = nx.Graph()
    graph.add_nodes_from((left.agent_id, right.agent_id))

    knn_graph._add_social_edge(
        graph,
        left,
        right,
        distance=0.30,
        sigma=0.40,
        seed=1205,
        weak_tie=False,
        formation_source="social_candidate",
    )
    knn_graph._add_social_edge(
        graph,
        left,
        right,
        distance=0.30,
        sigma=0.40,
        seed=1205,
        weak_tie=False,
        formation_source="triadic_closure",
    )

    edge = graph.edges[left.agent_id, right.agent_id]
    assert {"household", "local", "social_affinity", "triadic_closure"} <= set(edge["social_layers"])
    assert set(edge["layer_strengths"]) == set(edge["social_layers"])
    assert edge["primary_layer"] == "household"
    assert 0.0 < edge["interaction_opportunity"] <= 1.0
    assert set(edge["formation_sources"]) == {"social_candidate", "triadic_closure"}


def test_household_edge_starts_stronger_than_generic_affinity_and_weak_edge() -> None:
    household_left, household_right = _base_pair(seed=1206)
    household_left.context.memberships.household_id = "shared-household"
    household_right.context.memberships.household_id = "shared-household"
    generic_left, generic_right = _base_pair(seed=1207)
    generic_left.context.memberships = SocialMembershipContext(
        region_id="r1", city_id="c1", locality_id="l1", household_id="h1"
    )
    generic_right.context.memberships = SocialMembershipContext(
        region_id="r2", city_id="c2", locality_id="l2", household_id="h2"
    )

    household_graph = nx.Graph()
    generic_graph = nx.Graph()
    weak_graph = nx.Graph()
    for graph, pair in (
        (household_graph, (household_left, household_right)),
        (generic_graph, (generic_left, generic_right)),
        (weak_graph, (generic_left, generic_right)),
    ):
        graph.add_nodes_from((pair[0].agent_id, pair[1].agent_id))

    knn_graph._add_social_edge(
        household_graph,
        household_left,
        household_right,
        distance=0.45,
        sigma=0.40,
        seed=1206,
        weak_tie=False,
        formation_source="layer_household",
    )
    knn_graph._add_social_edge(
        generic_graph,
        generic_left,
        generic_right,
        distance=0.45,
        sigma=0.40,
        seed=1207,
        weak_tie=False,
        formation_source="social_candidate",
    )
    knn_graph._add_social_edge(
        weak_graph,
        generic_left,
        generic_right,
        distance=0.45,
        sigma=0.40,
        seed=1207,
        weak_tie=True,
        formation_source="weak_cross_community",
    )

    household_strength = household_graph.edges[household_left.agent_id, household_right.agent_id]["relationship_strength"]
    generic_strength = generic_graph.edges[generic_left.agent_id, generic_right.agent_id]["relationship_strength"]
    weak_strength = weak_graph.edges[generic_left.agent_id, generic_right.agent_id]["relationship_strength"]

    assert household_strength > generic_strength > weak_strength


def test_v3_graph_forms_edges_through_every_explicit_social_layer() -> None:
    agents = generate_population(
        1000,
        seed=1210,
        traits=ExcelTraitRepository(TRAIT_ROOT),
    )
    graph = knn_graph.build_knn_graph(agents, k=14, weak_tie_rate=0.05, seed=1210)
    formation_counts = Counter(
        source
        for _, _, data in graph.edges(data=True)
        for source in data.get("formation_sources", ())
    )

    assert formation_counts["layer_household"] > 0
    assert formation_counts["layer_workplace"] > 0
    assert formation_counts["layer_local"] > 0
    assert formation_counts["layer_education"] > 0
    assert formation_counts["layer_online"] > 0
    assert formation_counts["social_candidate"] > 0


def test_small_population_does_not_collapse_into_mostly_multi_layer_edges() -> None:
    agents = generate_population(
        250,
        seed=1212,
        traits=ExcelTraitRepository(TRAIT_ROOT),
    )
    graph = knn_graph.build_knn_graph(agents, k=10, weak_tie_rate=0.05, seed=1212)
    metrics = compute_network_distribution_metrics(graph)

    assert metrics.multi_layer_edge_share < 0.65


def test_large_explicit_layers_use_bounded_degree_instead_of_group_cliques() -> None:
    agents = generate_population(
        1000,
        seed=1211,
        traits=ExcelTraitRepository(TRAIT_ROOT),
    )
    graph = knn_graph.build_knn_graph(agents, k=14, weak_tie_rate=0.05, seed=1211)

    caps = {
        "workplace": 4,
        "education": 5,
        "local": 3,
        "online": 4,
    }
    for layer, cap in caps.items():
        source = f"layer_{layer}"
        explicit_degree = Counter()
        for left_id, right_id, data in graph.edges(data=True):
            if source not in data.get("formation_sources", ()):
                continue
            explicit_degree[int(left_id)] += 1
            explicit_degree[int(right_id)] += 1
        assert explicit_degree
        assert max(explicit_degree.values()) <= cap
