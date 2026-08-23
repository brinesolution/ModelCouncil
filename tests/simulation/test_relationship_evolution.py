from copy import deepcopy

import networkx as nx

from simulation.conversation.models import ConversationPair, ConversationResult, SemanticMessage
from simulation.engine import SimulationConfig, SimulationEngine
from simulation.network.knn_graph import build_knn_graph
from simulation.network.social_topology import (
    relationship_floor_for_edge,
    update_relationship_after_conversation,
)
from simulation.population.generator import generate_population
from simulation.product.knowledge import ProductKnowledge


def _graph() -> nx.Graph:
    graph = nx.Graph()
    graph.add_edge(
        0,
        1,
        relationship_strength=0.40,
        trust=0.40,
        directional_trust={"0": 0.40, "1": 0.40},
        interaction_count=0,
        last_interaction_round=None,
    )
    return graph


def _result(*, left_stance: float, right_stance: float) -> ConversationResult:
    return ConversationResult(
        conversation_id="evolution",
        messages=[
            SemanticMessage(0, 1, {"quality": left_stance}, 0.75, 0.75),
            SemanticMessage(1, 0, {"quality": right_stance}, 0.75, 0.75),
            SemanticMessage(0, 1, {"trust": left_stance}, 0.72, 0.72),
            SemanticMessage(1, 0, {"trust": right_stance}, 0.72, 0.72),
        ],
    )


def test_persistent_layer_relationship_floors_are_ordered_by_social_closeness():
    household = relationship_floor_for_edge({"social_layers": ("household",)})
    workplace = relationship_floor_for_edge({"social_layers": ("workplace",)})
    local = relationship_floor_for_edge({"social_layers": ("local",)})
    affinity = relationship_floor_for_edge({"social_layers": ("social_affinity",)})
    weak = relationship_floor_for_edge({"social_layers": ("weak_bridge",), "weak_tie": True})

    assert household > workplace > local > affinity > weak >= 0.0


def test_aligned_discussion_strengthens_relationship_more_than_severe_disagreement():
    agents = generate_population(2, seed=2201)
    for agent in agents:
        agent.state.beliefs.quality = 0.45
        agent.state.beliefs.trust = 0.40
        agent.state.knowledge = 0.75
    by_id = {agent.agent_id: agent for agent in agents}
    pair = ConversationPair("evolution", 2, 0, 1, 0.8)

    aligned = _graph()
    opposed = _graph()
    update_relationship_after_conversation(aligned, pair, _result(left_stance=0.50, right_stance=0.45), by_id)
    update_relationship_after_conversation(opposed, pair, _result(left_stance=0.90, right_stance=-0.90), by_id)

    aligned_delta = aligned.edges[0, 1]["relationship_strength"] - 0.40
    opposed_delta = opposed.edges[0, 1]["relationship_strength"] - 0.40
    assert 0.0 < opposed_delta < aligned_delta < 0.03
    assert aligned.edges[0, 1]["trust"] > 0.40


def test_relationship_evolution_is_deterministic_slow_and_bounded():
    agents = generate_population(2, seed=2202)
    for agent in agents:
        agent.state.knowledge = 0.90
        agent.state.beliefs.quality = 0.60
        agent.state.beliefs.trust = 0.60
    by_id = {agent.agent_id: agent for agent in agents}
    pair = ConversationPair("evolution", 3, 0, 1, 0.8)
    result = _result(left_stance=0.65, right_stance=0.60)

    first = _graph()
    second = deepcopy(first)
    for _ in range(80):
        update_relationship_after_conversation(first, pair, result, by_id)
        update_relationship_after_conversation(second, pair, result, by_id)

    assert first.edges[0, 1] == second.edges[0, 1]
    edge = first.edges[0, 1]
    assert 0.40 < edge["relationship_strength"] <= 1.0
    assert all(0.0 <= float(value) <= 1.0 for value in edge["directional_trust"].values())
    assert 0.0 <= edge["trust"] <= 1.0


def test_engine_persists_relationship_evolution_for_future_rounds():
    population = generate_population(50, seed=2203)
    config = SimulationConfig(
        rounds=3,
        seed=2203,
        k=7,
        max_conversations_per_agent=2,
        initiator_rate=0.30,
        weak_tie_rate=0.05,
        cooldown_rounds=0,
    )
    initial = build_knn_graph(population, k=config.k, weak_tie_rate=config.weak_tie_rate, seed=config.seed)
    product = ProductKnowledge(
        name="Relationship Test",
        category="Consumer Electronics",
        pitch="A useful reliable device with transparent pricing and responsive support.",
        price=3499,
        currency="INR",
    )

    result = SimulationEngine().run(product, population, config)
    interacted = [
        (left, right, data)
        for left, right, data in result.graph.edges(data=True)
        if int(data.get("interaction_count", 0)) > 0
    ]

    assert interacted
    assert all(
        float(data["relationship_strength"]) >= float(initial.edges[left, right]["relationship_strength"])
        for left, right, data in interacted
    )
    assert any(
        data.get("directional_trust") != initial.edges[left, right].get("directional_trust")
        for left, right, data in interacted
    )
