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
    assert len(first.messages) == 2
    assert len(first.transcript) == 2
    assert all(entry["text"] for entry in first.transcript)
    assert all(message.text for message in first.messages)


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
            for phrase in ("concern", "hesitate", "higher", "too high", "obstacle", "paying")
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
