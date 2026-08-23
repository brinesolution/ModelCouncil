import networkx as nx

from simulation.analytics.network_distribution import compute_network_distribution_metrics
from simulation.audit.logger import MemoryRunAuditLogger
from simulation.engine import SimulationConfig, SimulationEngine
from simulation.population.generator import generate_population
from simulation.product.knowledge import ProductKnowledge


def test_network_distribution_metrics_capture_structure_and_edge_spread():
    graph = nx.Graph()
    for node, target in enumerate((4, 5, 7, 9, 12)):
        graph.add_node(node, target_social_degree=target)
    edges = (
        (0, 1, 0.85, 0.70, False, ("occupation", "age_band"), {"0": 0.75, "1": 0.55}),
        (1, 2, 0.62, 0.52, False, ("age_band",), {"1": 0.60, "2": 0.42}),
        (2, 3, 0.40, 0.38, True, ("language",), {"2": 0.32, "3": 0.28}),
        (3, 4, 0.28, 0.22, True, (), {"3": 0.20, "4": 0.18}),
        (0, 2, 0.72, 0.58, False, ("life_stage",), {"0": 0.66, "2": 0.51}),
    )
    for left, right, similarity, relationship, weak, overlap, trust in edges:
        graph.add_edge(
            left,
            right,
            similarity=similarity,
            relationship_strength=relationship,
            weak_tie=weak,
            community_overlap=overlap,
            directional_trust=trust,
            formation_source="weak_two_hop" if weak else "social_candidate",
        )

    metrics = compute_network_distribution_metrics(graph)

    assert metrics.node_count == 5
    assert metrics.edge_count == 5
    assert metrics.connected_components == 1
    assert metrics.largest_component_share == 1.0
    assert metrics.max_degree == 3
    assert metrics.degree_p90 >= metrics.degree_p10
    assert metrics.target_degree_std > 0
    assert metrics.weak_tie_share == 0.4
    assert metrics.cross_community_edge_share > 0
    assert metrics.similarity_std > 0.15
    assert metrics.relationship_std > 0.15
    assert metrics.directional_trust_std > 0.15


def test_network_distribution_metrics_capture_v3_layer_and_membership_coverage():
    graph = nx.Graph()
    graph.add_node(
        0,
        target_social_degree=6,
        household_id="h1",
        workplace_id="w1",
        education_id=None,
        online_interest_ids=("o1",),
    )
    graph.add_node(
        1,
        target_social_degree=6,
        household_id="h1",
        workplace_id="w1",
        education_id=None,
        online_interest_ids=("o1",),
    )
    graph.add_node(
        2,
        target_social_degree=6,
        household_id="h2",
        workplace_id=None,
        education_id="e1",
        online_interest_ids=("o2",),
    )
    graph.add_edge(
        0,
        1,
        similarity=0.7,
        relationship_strength=0.8,
        weak_tie=False,
        community_overlap=("household", "workplace", "online"),
        directional_trust={"0": 0.7, "1": 0.7},
        formation_source="layer_household",
        social_layers=("household", "workplace", "online"),
    )
    graph.add_edge(
        1,
        2,
        similarity=0.4,
        relationship_strength=0.3,
        weak_tie=False,
        community_overlap=(),
        directional_trust={"1": 0.4, "2": 0.4},
        formation_source="social_candidate",
        social_layers=("social_affinity",),
    )

    metrics = compute_network_distribution_metrics(graph)

    assert metrics.household_edge_share == 0.5
    assert metrics.workplace_edge_share == 0.5
    assert metrics.online_edge_share == 0.5
    assert metrics.affinity_edge_share == 0.5
    assert metrics.multi_layer_edge_share == 0.5
    assert metrics.household_membership_share == 1.0
    assert metrics.workplace_membership_share == 2 / 3
    assert metrics.education_membership_share == 1 / 3
    assert metrics.online_membership_share == 1.0


def test_engine_exposes_and_audits_network_distribution_metrics():
    population = generate_population(80, seed=2301)
    product = ProductKnowledge(
        name="Network Metrics",
        category="Consumer Electronics",
        pitch="A useful reliable device with transparent pricing.",
        price=3499,
        currency="INR",
    )
    audit = MemoryRunAuditLogger(run_id="network-metrics")

    result = SimulationEngine().run(
        product,
        population,
        SimulationConfig(rounds=2, seed=2301, k=8, weak_tie_rate=0.05),
        audit=audit,
    )

    assert result.network_metrics is not None
    assert result.network_metrics.node_count == 80
    assert result.network_metrics.edge_count == result.graph.number_of_edges()
    events = [event for event in audit.events if event["event"] == "network.distribution"]
    assert [event["payload"]["stage"] for event in events] == ["initial", "final"]
    assert events[-1]["payload"]["metrics"]["mean_degree"] == result.network_metrics.mean_degree
