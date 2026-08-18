from simulation.audit.logger import MemoryRunAuditLogger
from simulation.conversation.background_engine import generate_background_conversation
from simulation.conversation.models import ConversationPair
from simulation.conversation.scheduler import schedule_conversations
from simulation.engine import SimulationConfig, SimulationEngine
from simulation.network.knn_graph import build_knn_graph
from simulation.population.generator import generate_population
from simulation.product.knowledge import ProductKnowledge
import pytest


def test_network_and_scheduler_events_match_returned_graph_and_pairs():
    agents = generate_population(16, seed=101)
    audit = MemoryRunAuditLogger(run_id="network")
    graph = build_knn_graph(agents, k=4, weak_tie_rate=0.1, seed=101, audit=audit)

    built = [event for event in audit.events if event["event"] == "network.built"]
    vectors = [event for event in audit.events if event["event"] == "network.agent_vector"]
    edges = [event for event in audit.events if event["event"] == "network.edge"]
    assert len(built) == 1
    assert built[0]["payload"]["node_count"] == graph.number_of_nodes()
    assert built[0]["payload"]["edge_count"] == graph.number_of_edges()
    assert len(vectors) == len(agents)
    assert all(len(event["payload"]["weighted_vector"]) == len(built[0]["payload"]["feature_weights"]) for event in vectors)
    assert len(edges) == graph.number_of_edges()
    assert all("formation_source" in event["payload"] for event in edges)
    assert all("knn_distance" in event["payload"] for event in edges)

    pairs = schedule_conversations(
        agents,
        graph,
        round_index=1,
        max_conversations_per_agent=2,
        cooldown_rounds=2,
        seed=101,
        initiator_rate=0.5,
        audit=audit,
    )
    initiators = [event for event in audit.events if event["event"] == "scheduler.initiators_selected"]
    selected = [event for event in audit.events if event["event"] == "scheduler.pair_selected"]
    candidates = [event for event in audit.events if event["event"] == "scheduler.candidates"]
    assert len(initiators) == 1
    assert candidates
    assert [event["conversation_id"] for event in selected] == [pair.conversation_id for pair in pairs]
    assert all("candidate_weight" in event["payload"] for event in selected)
    candidate_records = [record for event in candidates for record in event["payload"]["candidates"]]
    assert candidate_records
    for record in candidate_records:
        assert sum(record["score_components"].values()) == pytest.approx(record["base_score"])


def test_semantic_conversation_audit_contains_topic_scores_styles_and_fallback_text():
    agents = generate_population(10, seed=22)
    graph = build_knn_graph(agents, k=3, seed=22)
    a, b = next(iter(graph.edges))
    pair = ConversationPair("r2-a%d-a%d" % (a, b), 2, int(a), int(b), 0.8)
    snapshot = {agent.agent_id: agent for agent in agents}
    audit = MemoryRunAuditLogger(run_id="conversation")

    result = generate_background_conversation(
        pair,
        snapshot,
        graph,
        seed=22,
        recent_topics_by_agent={int(a): ("price", "price"), int(b): ("trust",)},
        audit=audit,
    )

    started = [event for event in audit.events if event["event"] == "conversation.semantic_started"]
    messages = [event for event in audit.events if event["event"] == "conversation.semantic_message"]
    completed = [event for event in audit.events if event["event"] == "conversation.semantic_completed"]
    topic_choices = [event for event in audit.events if event["event"] == "conversation.topic_selected"]
    calculations = [event for event in audit.events if event["event"] == "conversation.semantic_calculation"]
    assert len(started) == 1
    assert len(messages) == len(result.messages) == 2
    assert len(completed) == 1
    assert len(topic_choices) == 2
    assert len(calculations) == 2
    for event, message in zip(messages, result.messages, strict=True):
        payload = event["payload"]
        assert payload["speaker_id"] == message.speaker_id
        assert payload["listener_id"] == message.listener_id
        assert payload["topic_effects"] == message.topic_effects
        assert payload["argument_strength"] == message.argument_strength
        assert payload["confidence"] == message.confidence
        assert payload["fallback_text"] == message.text
        assert payload["dialogue_shape"]
        assert payload["speaking_style"]
    assert all("topic_scores" in event["payload"] for event in topic_choices)
    assert all("normalized_weights" in event["payload"] for event in topic_choices)
    assert all("score_components" in event["payload"] for event in topic_choices)
    for event in calculations:
        payload = event["payload"]
        assert sum(payload["argument_components"].values()) == pytest.approx(payload["argument_raw"])
        assert payload["conveyed_raw"] == pytest.approx(payload["speaker_stance"] + payload["conveyed_noise"])


def test_engine_emits_round_boundary_and_all_semantic_conversations():
    product = ProductKnowledge(
        name="Test Coach",
        category="Fitness Technology",
        pitch="Personalized fitness guidance for a monthly subscription.",
        price=500,
        billing_cadence="monthly",
    )
    population = generate_population(30, seed=55)
    audit = MemoryRunAuditLogger(run_id="engine")

    result = SimulationEngine().run(
        product,
        population,
        SimulationConfig(rounds=3, seed=55, k=5, initiator_rate=0.3),
        audit=audit,
    )

    starts = [event for event in audit.events if event["event"] == "round.started"]
    ends = [event for event in audit.events if event["event"] == "round.completed"]
    completed_conversations = [
        event for event in audit.events if event["event"] == "conversation.semantic_completed"
    ]
    assert [event["round"] for event in starts] == [1, 2, 3]
    assert [event["round"] for event in ends] == [1, 2, 3]
    assert len(completed_conversations) == result.conversation_count
    assert sum(event["payload"]["conversation_count"] for event in ends) == result.conversation_count
