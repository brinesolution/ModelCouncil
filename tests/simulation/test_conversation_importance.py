from simulation.conversation.importance import score_conversation
from simulation.conversation.ledger import (
    AgentLanguageProfile,
    ConversationLanguageContext,
    ConversationLedgerEntry,
)
from simulation.conversation.models import ConversationPair, ConversationResult, SemanticMessage


def _profile(
    agent_id: int,
    *,
    influence: float,
    stubbornness: float,
    opinion: float,
) -> AgentLanguageProfile:
    return AgentLanguageProfile(
        agent_id=agent_id,
        age=30,
        occupation="Professional",
        primary_language="English",
        locale="Indian English",
        logicality=0.6,
        emotionality=0.5,
        sociability=0.6,
        stubbornness=stubbornness,
        influence_power=influence,
        confidence=0.7,
        knowledge=0.5,
        overall_opinion=opinion,
    )


def _entry(
    conversation_id: str,
    *,
    edge_score: float,
    influence: float,
    stubbornness: float,
    trust: float,
    relationship: float,
    stance: float,
    disagreement: float,
    weak_tie: bool,
) -> ConversationLedgerEntry:
    pair = ConversationPair(conversation_id, 1, 1, 2, edge_score)
    context = ConversationLanguageContext(
        agent_a=_profile(
            1,
            influence=influence,
            stubbornness=stubbornness,
            opinion=disagreement,
        ),
        agent_b=_profile(
            2,
            influence=influence,
            stubbornness=stubbornness,
            opinion=-disagreement,
        ),
    )
    result = ConversationResult(
        conversation_id=conversation_id,
        messages=[
            SemanticMessage(
                speaker_id=1,
                listener_id=2,
                topic_effects={"price": stance},
                argument_strength=0.8,
                confidence=0.7,
            ),
            SemanticMessage(
                speaker_id=2,
                listener_id=1,
                topic_effects={"price": -stance},
                argument_strength=0.8,
                confidence=0.7,
            ),
        ],
    )
    return ConversationLedgerEntry(
        round_index=1,
        pair=pair,
        result=result,
        language_context=context,
        trust=trust,
        relationship_strength=relationship,
        similarity=edge_score,
        weak_tie=weak_tie,
    )


def test_high_impact_conversation_scores_above_low_impact_conversation():
    high = _entry(
        "high",
        edge_score=0.95,
        influence=0.9,
        stubbornness=0.1,
        trust=0.9,
        relationship=0.8,
        stance=0.9,
        disagreement=0.8,
        weak_tie=True,
    )
    low = _entry(
        "low",
        edge_score=0.2,
        influence=0.1,
        stubbornness=0.9,
        trust=0.1,
        relationship=0.1,
        stance=0.05,
        disagreement=0.05,
        weak_tie=False,
    )

    assert score_conversation(high) > score_conversation(low)


def test_conversation_importance_is_bounded_and_deterministic():
    entry = _entry(
        "stable",
        edge_score=0.8,
        influence=0.7,
        stubbornness=0.35,
        trust=0.75,
        relationship=0.65,
        stance=0.6,
        disagreement=0.5,
        weak_tie=False,
    )

    first = score_conversation(entry)
    second = score_conversation(entry)

    assert first == second
    assert 0.0 <= first <= 1.0
