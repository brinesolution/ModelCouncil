from collections import Counter

from simulation.conversation.scheduler import schedule_conversations
from simulation.network.knn_graph import build_knn_graph
from simulation.population.generator import generate_population


def test_knn_graph_and_scheduler_respect_conversation_capacity() -> None:
    agents = generate_population(80, seed=11)
    graph = build_knn_graph(agents, k=8, weak_tie_rate=0.05, seed=11)
    pairs = schedule_conversations(
        agents,
        graph,
        round_index=1,
        max_conversations_per_agent=2,
        seed=11,
    )

    assert graph.number_of_nodes() == 80
    assert graph.number_of_edges() > 0

    counts = Counter()
    seen_pairs: set[tuple[int, int]] = set()
    for pair in pairs:
        edge = tuple(sorted((pair.agent_a_id, pair.agent_b_id)))
        assert edge not in seen_pairs
        seen_pairs.add(edge)
        counts[pair.agent_a_id] += 1
        counts[pair.agent_b_id] += 1

    assert all(count <= 2 for count in counts.values())
    assert len(pairs) <= round(len(agents) * 0.20)
