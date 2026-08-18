import networkx as nx

from simulation.conversation.scheduler import _edge_score_components, schedule_conversations
from simulation.opinion.dynamics_config import InfluenceDynamicsConfig
from simulation.population.generator import generate_population


def _mixed_graph(agents):
    graph = nx.Graph()
    for agent in agents:
        graph.add_node(agent.agent_id)
    for left in range(len(agents)):
        for right in range(left + 1, len(agents)):
            weak = (left + right) % 2 == 0
            graph.add_edge(
                left,
                right,
                similarity=0.15 if weak else 0.82,
                relationship_strength=0.18 if weak else 0.72,
                trust=0.22 if weak else 0.75,
                weak_tie=weak,
                last_interaction_round=None,
            )
    return graph


def test_information_difference_adds_small_candidate_value_without_overpowering_relationship():
    agents = generate_population(3, seed=301)
    source, trusted, distant = agents
    source.state.overall_opinion = 0.0
    trusted.state.overall_opinion = 0.10
    distant.state.overall_opinion = -0.80
    dynamics = InfluenceDynamicsConfig(disagreement_information_weight=0.08)

    trusted_score, trusted_components = _edge_score_components(
        source,
        trusted,
        {"similarity": 0.85, "relationship_strength": 0.80},
        dynamics,
    )
    distant_score, distant_components = _edge_score_components(
        source,
        distant,
        {"similarity": 0.15, "relationship_strength": 0.15},
        dynamics,
    )

    assert distant_components["informational_difference"] > trusted_components["informational_difference"]
    assert trusted_score > distant_score


def test_weak_tie_exploration_prevents_weak_edges_from_collapsing_out_of_selection():
    agents = generate_population(30, seed=302)
    graph = _mixed_graph(agents)
    dynamics = InfluenceDynamicsConfig(weak_tie_exploration_weight=0.45)
    weak_selected = 0
    total_selected = 0

    for round_index in range(1, 81):
        pairs = schedule_conversations(
            agents,
            graph,
            round_index=round_index,
            max_conversations_per_agent=1,
            cooldown_rounds=0,
            seed=440,
            initiator_rate=0.50,
            dynamics=dynamics,
        )
        for pair in pairs:
            total_selected += 1
            if graph.edges[pair.agent_a_id, pair.agent_b_id]["weak_tie"]:
                weak_selected += 1

    selected_share = weak_selected / total_selected
    graph_share = sum(1 for _, _, data in graph.edges(data=True) if data["weak_tie"]) / graph.number_of_edges()

    assert total_selected > 300
    assert selected_share / graph_share >= 0.70
