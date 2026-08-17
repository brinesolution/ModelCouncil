from simulation.conversation.background_engine import generate_background_conversation
from simulation.conversation.models import ConversationPair
from simulation.network.knn_graph import build_knn_graph
from simulation.population.generator import generate_population


def test_background_conversation_is_reproducible():
    agents = generate_population(10, seed=5)
    graph = build_knn_graph(agents, k=3, seed=5)
    pair = ConversationPair("test", 1, 0, 1, 0.8)
    snapshot = {agent.agent_id: agent for agent in agents}

    first = generate_background_conversation(pair, snapshot, graph, seed=77)
    second = generate_background_conversation(pair, snapshot, graph, seed=77)

    assert first.messages == second.messages
    assert first.transcript == []
    assert len(first.messages) == 2


def test_background_conversation_keeps_topic_effects_bounded():
    agents = generate_population(10, seed=9)
    graph = build_knn_graph(agents, k=3, seed=9)
    pair = ConversationPair("test", 1, 0, 1, 0.8)
    result = generate_background_conversation(
        pair, {agent.agent_id: agent for agent in agents}, graph, seed=12
    )

    for message in result.messages:
        assert message.topic_effects
        assert all(-1.0 <= value <= 1.0 for value in message.topic_effects.values())
        assert 0.0 <= message.argument_strength <= 1.0
