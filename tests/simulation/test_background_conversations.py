from simulation.conversation.background_engine import generate_background_conversation
from simulation.conversation.models import ConversationPair
from simulation.network.knn_graph import build_knn_graph
from simulation.population.generator import generate_population


def first_graph_pair(graph, round_index: int = 1) -> ConversationPair:
    agent_a_id, agent_b_id = next(iter(graph.edges))
    return ConversationPair("test", round_index, int(agent_a_id), int(agent_b_id), 0.8)


def test_background_conversation_is_reproducible():
    agents = generate_population(10, seed=5)
    graph = build_knn_graph(agents, k=3, seed=5)
    pair = first_graph_pair(graph)
    snapshot = {agent.agent_id: agent for agent in agents}

    first = generate_background_conversation(pair, snapshot, graph, seed=77)
    second = generate_background_conversation(pair, snapshot, graph, seed=77)

    assert first.messages == second.messages
    assert first.transcript == []
    assert len(first.messages) == 2


def test_background_conversation_keeps_topic_effects_bounded():
    agents = generate_population(10, seed=9)
    graph = build_knn_graph(agents, k=3, seed=9)
    pair = first_graph_pair(graph)
    result = generate_background_conversation(
        pair, {agent.agent_id: agent for agent in agents}, graph, seed=12
    )

    for message in result.messages:
        assert message.topic_effects
        assert all(-1.0 <= value <= 1.0 for value in message.topic_effects.values())
        assert 0.0 <= message.argument_strength <= 1.0
