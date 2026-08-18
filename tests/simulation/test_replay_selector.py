from simulation.conversation.ledger import (
    AgentLanguageProfile,
    ConversationLanguageContext,
    ConversationLedgerEntry,
)
from simulation.conversation.models import ConversationPair, ConversationResult, SemanticMessage
from simulation.conversation.replay_selector import select_replay_conversations


def _profile(agent_id: int, opinion: float) -> AgentLanguageProfile:
    return AgentLanguageProfile(
        agent_id=agent_id,
        age=30,
        occupation="Synthetic Consumer",
        primary_language="English",
        locale="Indian English",
        logicality=0.6,
        emotionality=0.5,
        sociability=0.6,
        stubbornness=0.4,
        influence_power=0.6,
        confidence=0.6,
        knowledge=0.5,
        overall_opinion=opinion,
    )


def _entry(
    index: int,
    *,
    topic: str,
    stance: float,
    importance: float,
    round_index: int,
    weak_tie: bool = False,
) -> ConversationLedgerEntry:
    conversation_id = f"c-{index:02d}-{topic}"
    pair = ConversationPair(conversation_id, round_index, index * 2, index * 2 + 1, 0.7)
    result = ConversationResult(
        conversation_id=conversation_id,
        messages=[
            SemanticMessage(
                pair.agent_a_id,
                pair.agent_b_id,
                {topic: stance},
                0.75,
                0.65,
            ),
            SemanticMessage(
                pair.agent_b_id,
                pair.agent_a_id,
                {topic: stance * 0.85},
                0.70,
                0.60,
            ),
        ],
    )
    return ConversationLedgerEntry(
        round_index=round_index,
        pair=pair,
        result=result,
        language_context=ConversationLanguageContext(
            agent_a=_profile(pair.agent_a_id, stance),
            agent_b=_profile(pair.agent_b_id, stance * 0.7),
        ),
        trust=0.6,
        relationship_strength=0.6,
        similarity=0.7,
        weak_tie=weak_tie,
        importance=importance,
    )


def _topics(entries: list[ConversationLedgerEntry]) -> list[str]:
    return [next(iter(entry.result.messages[0].topic_effects)) for entry in entries]


def test_replay_selector_preserves_importance_but_breaks_comparable_price_monoculture():
    entries = [
        _entry(
            index,
            topic="price",
            stance=-0.70,
            importance=0.95 - index * 0.008,
            round_index=(index % 10) + 1,
        )
        for index in range(10)
    ]
    entries.extend(
        [
            _entry(20, topic="usefulness", stance=0.70, importance=0.90, round_index=12),
            _entry(21, topic="trust", stance=-0.45, importance=0.89, round_index=15, weak_tie=True),
            _entry(22, topic="privacy", stance=-0.55, importance=0.88, round_index=18),
            _entry(23, topic="quality", stance=0.50, importance=0.87, round_index=20),
            _entry(24, topic="novelty", stance=0.45, importance=0.86, round_index=8),
        ]
    )

    selected = select_replay_conversations(entries, limit=12)
    topics = _topics(selected)

    assert len(selected) == 12
    assert selected[0].conversation_id == "c-00-price"
    assert len(set(topics)) >= 5
    assert topics.count("price") <= 7
    assert any(entry.weak_tie for entry in selected)
    assert len({entry.round_index for entry in selected}) >= 8


def test_replay_selector_allows_repetition_when_ledger_really_has_one_topic():
    entries = [
        _entry(
            index,
            topic="price",
            stance=-0.6 if index % 2 else 0.4,
            importance=0.90 - index * 0.01,
            round_index=(index % 6) + 1,
        )
        for index in range(16)
    ]

    selected = select_replay_conversations(entries, limit=12)

    assert len(selected) == 12
    assert set(_topics(selected)) == {"price"}


def test_replay_selector_is_deterministic():
    entries = [
        _entry(
            index,
            topic=("price", "usefulness", "trust", "privacy")[index % 4],
            stance=(-0.6, 0.5, -0.3, 0.4)[index % 4],
            importance=0.9 - index * 0.01,
            round_index=(index % 8) + 1,
        )
        for index in range(20)
    ]

    first = select_replay_conversations(entries, limit=12)
    second = select_replay_conversations(entries, limit=12)

    assert [entry.conversation_id for entry in first] == [
        entry.conversation_id for entry in second
    ]
