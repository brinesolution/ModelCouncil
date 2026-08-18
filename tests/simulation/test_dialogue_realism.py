from simulation.conversation.dialogue_realism import (
    DialogueShape,
    derive_dialogue_shape,
    derive_speaking_style,
)
from simulation.conversation.ledger import AgentLanguageProfile, ConversationLanguageContext
from simulation.conversation.models import ConversationResult, SemanticMessage


def _profile(
    agent_id: int,
    *,
    logicality: float = 0.5,
    emotionality: float = 0.5,
    sociability: float = 0.5,
    stubbornness: float = 0.5,
    confidence: float = 0.5,
    opinion: float = 0.0,
    occupation: str = "Synthetic Consumer",
    age: int = 29,
) -> AgentLanguageProfile:
    return AgentLanguageProfile(
        agent_id=agent_id,
        age=age,
        occupation=occupation,
        primary_language="English",
        locale="Indian English",
        logicality=logicality,
        emotionality=emotionality,
        sociability=sociability,
        stubbornness=stubbornness,
        influence_power=0.5,
        confidence=confidence,
        knowledge=0.5,
        overall_opinion=opinion,
    )


def _result(first_topic: str, first: float, second_topic: str, second: float) -> ConversationResult:
    return ConversationResult(
        conversation_id="shape-test",
        messages=[
            SemanticMessage(1, 2, {first_topic: first}, 0.7, 0.6),
            SemanticMessage(2, 1, {second_topic: second}, 0.7, 0.6),
        ],
    )


def test_speaking_style_is_derived_from_traits_not_demographic_labels():
    analytical = _profile(
        1,
        logicality=0.9,
        emotionality=0.25,
        sociability=0.8,
        stubbornness=0.25,
        confidence=0.85,
    )
    same_traits_other_identity = _profile(
        1,
        logicality=0.9,
        emotionality=0.25,
        sociability=0.8,
        stubbornness=0.25,
        confidence=0.85,
        occupation="Student",
        age=19,
    )

    first = derive_speaking_style(analytical)
    second = derive_speaking_style(same_traits_other_identity)

    assert first == second
    assert first.reasoning == "analytical"
    assert first.social == "sociable"
    assert first.confidence == "assertive"
    assert first.receptivity == "receptive"


def test_dialogue_shape_distinguishes_agreement_challenge_tradeoff_and_uncertainty():
    context = ConversationLanguageContext(
        agent_a=_profile(1, opinion=0.3),
        agent_b=_profile(2, opinion=0.2),
    )

    assert derive_dialogue_shape(_result("price", -0.6, "price", -0.5), context) is DialogueShape.agreement
    assert derive_dialogue_shape(_result("price", -0.6, "price", 0.55), context) is DialogueShape.challenge
    assert derive_dialogue_shape(_result("price", -0.5, "usefulness", 0.6), context) is DialogueShape.trade_off
    assert derive_dialogue_shape(_result("trust", 0.04, "trust", -0.02), context) is DialogueShape.uncertainty


def test_dialogue_shape_does_not_change_semantic_messages():
    result = _result("price", -0.5, "usefulness", 0.6)
    original = list(result.messages)
    context = ConversationLanguageContext(agent_a=_profile(1), agent_b=_profile(2))

    derive_dialogue_shape(result, context)

    assert result.messages == original
