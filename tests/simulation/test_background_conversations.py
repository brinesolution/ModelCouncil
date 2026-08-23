from simulation.conversation.background_engine import generate_background_conversation
from simulation.conversation.background_language import render_background_text
from simulation.conversation.dialogue_realism import DialogueShape, derive_speaking_style
from simulation.conversation.ledger import AgentLanguageProfile
from simulation.conversation.models import ConversationPair
from simulation.domain.agent import ProductBeliefs
from simulation.product.pricing import (
    BillingCadence,
    ConsumerPriceContext,
    PricePosition,
    PriceStanceBand,
)
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
    assert first.transcript == second.transcript
    assert 4 <= len(first.messages) <= 8
    assert len(first.transcript) == len(first.messages)
    assert all(entry["text"] for entry in first.transcript)
    assert all(message.text for message in first.messages)


def test_background_conversation_uses_listeners_directional_trust_for_message_confidence():
    agents = generate_population(10, seed=6)
    graph = build_knn_graph(agents, k=3, weak_tie_rate=0.0, seed=6)
    pair = first_graph_pair(graph)
    snapshot = {agent.agent_id: agent for agent in agents}
    baseline = generate_background_conversation(pair, snapshot, graph, seed=78)
    listener_id = baseline.messages[0].listener_id
    other_id = baseline.messages[0].speaker_id

    high_graph = graph.copy()
    high_edge = high_graph.edges[pair.agent_a_id, pair.agent_b_id]
    high_edge["trust"] = 0.50
    high_edge["directional_trust"] = {str(listener_id): 0.95, str(other_id): 0.20}

    low_graph = graph.copy()
    low_edge = low_graph.edges[pair.agent_a_id, pair.agent_b_id]
    low_edge["trust"] = 0.50
    low_edge["directional_trust"] = {str(listener_id): 0.05, str(other_id): 0.20}

    high = generate_background_conversation(pair, snapshot, high_graph, seed=78)
    low = generate_background_conversation(pair, snapshot, low_graph, seed=78)

    assert high.messages[0].confidence > low.messages[0].confidence + 0.20


def test_background_conversation_depth_varies_across_pairs_and_seeds():
    observed_lengths: set[int] = set()
    for seed in range(8, 24):
        agents = generate_population(12, seed=seed)
        graph = build_knn_graph(agents, k=4, seed=seed)
        pair = first_graph_pair(graph)
        result = generate_background_conversation(
            pair,
            {agent.agent_id: agent for agent in agents},
            graph,
            seed=seed + 100,
        )
        observed_lengths.add(len(result.messages))

    assert min(observed_lengths) >= 4
    assert max(observed_lengths) <= 8
    assert len(observed_lengths) >= 2


def test_favorable_monthly_price_context_never_uses_expensive_or_steep_wording():
    speaker, listener = generate_population(2, seed=44)
    context = ConsumerPriceContext(
        billing_cadence=BillingCadence.monthly,
        reference_price_inr=650.0,
        reference_ratio=200 / 650,
        position=PricePosition.inexpensive,
        affordability=0.82,
        price_pressure=0.14,
        stance=0.58,
        stance_band=PriceStanceBand.strongly_favorable,
    )
    style = derive_speaking_style(AgentLanguageProfile.from_agent(speaker))

    text = render_background_text(
        speaker=speaker,
        listener=listener,
        topic="price",
        stance=0.55,
        conversation_id="price-favorable",
        dialogue_shape=DialogueShape.agreement,
        speaking_style=style,
        price_context=context,
    ).lower()

    assert "expensive" not in text
    assert "steep" not in text
    assert "too much" not in text


def test_background_price_wording_varies_across_conversation_ids():
    speaker, listener = generate_population(2, seed=48)
    context = ConsumerPriceContext(
        billing_cadence=BillingCadence.monthly,
        reference_price_inr=650.0,
        reference_ratio=1500 / 650,
        position=PricePosition.expensive,
        affordability=0.28,
        price_pressure=0.76,
        stance=-0.50,
        stance_band=PriceStanceBand.strongly_unfavorable,
    )
    style = derive_speaking_style(AgentLanguageProfile.from_agent(speaker))

    variants = {
        render_background_text(
            speaker=speaker,
            listener=listener,
            topic="price",
            stance=-0.55,
            conversation_id=f"variant-{index}",
            dialogue_shape=DialogueShape.challenge,
            speaking_style=style,
            price_context=context,
        )
        for index in range(12)
    }

    assert len(variants) >= 4


def test_background_engine_refreshes_price_context_from_current_price_belief():
    agents = generate_population(10, seed=57)
    graph = build_knn_graph(agents, k=3, seed=57)
    pair = first_graph_pair(graph)
    snapshot = {agent.agent_id: agent for agent in agents}
    for agent_id in (pair.agent_a_id, pair.agent_b_id):
        snapshot[agent_id].state.beliefs = ProductBeliefs(price=-0.95)
    initially_favorable = ConsumerPriceContext(
        billing_cadence=BillingCadence.monthly,
        reference_price_inr=650.0,
        reference_ratio=200 / 650,
        position=PricePosition.inexpensive,
        affordability=0.80,
        price_pressure=0.16,
        stance=0.55,
        stance_band=PriceStanceBand.strongly_favorable,
    )

    result = generate_background_conversation(
        pair,
        snapshot,
        graph,
        seed=61,
        price_contexts={
            pair.agent_a_id: initially_favorable,
            pair.agent_b_id: initially_favorable,
        },
    )

    price_messages = [
        message for message in result.messages if "price" in message.topic_effects
    ]
    assert price_messages
    for message in price_messages:
        lowered = (message.text or "").lower()
        assert "manageable" not in lowered
        assert "strong positive" not in lowered
        assert any(
            phrase in lowered
            for phrase in (
                "concern",
                "hesitate",
                "higher",
                "too high",
                "obstacle",
                "paying",
                "comfortable paying",
                "walk away",
                "pass on this product",
            )
        )


def test_background_reply_explicitly_challenges_opposite_stance_on_same_topic():
    speaker, listener = generate_population(2, seed=74)

    text = render_background_text(
        speaker=speaker,
        listener=listener,
        topic="trust",
        stance=-0.62,
        conversation_id="direct-rebuttal",
        dialogue_shape=DialogueShape.challenge,
        reply_to_topic="trust",
        reply_to_stance=0.64,
    ).lower()

    assert any(
        phrase in text
        for phrase in (
            "i see that differently",
            "that's where i disagree",
            "i don't see that the same way",
            "i'm not convinced by that",
        )
    )


def test_low_purchase_intent_can_be_stated_as_an_explicit_no_buy_decision():
    speaker, listener = generate_population(2, seed=73)
    speaker.state.purchase_intent = 0.12
    speaker.state.overall_opinion = -0.42

    text = render_background_text(
        speaker=speaker,
        listener=listener,
        topic="trust",
        stance=-0.62,
        conversation_id="negative-decision",
        dialogue_shape=DialogueShape.challenge,
        decision_emphasis=True,
    ).lower()

    assert any(
        phrase in text
        for phrase in (
            "would not buy",
            "wouldn't buy",
            "i would pass",
            "i'd pass",
            "not buying",
            "walk away",
        )
    )


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
