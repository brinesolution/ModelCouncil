from dataclasses import replace

from simulation.conversation.dialogue_policy import select_for_llm
from simulation.conversation.ledger import (
    AgentLanguageProfile,
    ConversationLanguageContext,
    ConversationLedgerEntry,
)
from simulation.conversation.models import ConversationPair, ConversationResult


def _profile(agent_id: int) -> AgentLanguageProfile:
    return AgentLanguageProfile(
        agent_id=agent_id,
        age=30,
        occupation="Professional",
        primary_language="English",
        locale="Indian English",
        logicality=0.5,
        emotionality=0.5,
        sociability=0.5,
        stubbornness=0.5,
        influence_power=0.5,
        confidence=0.5,
        knowledge=0.5,
        overall_opinion=0.0,
    )


def _entries(count: int) -> list[ConversationLedgerEntry]:
    context = ConversationLanguageContext(_profile(1), _profile(2))
    base = ConversationLedgerEntry(
        round_index=1,
        pair=ConversationPair("base", 1, 1, 2, 0.5),
        result=ConversationResult("base"),
        language_context=context,
        trust=0.5,
        relationship_strength=0.5,
        similarity=0.5,
        weak_tie=False,
    )
    return [
        replace(
            base,
            pair=ConversationPair(f"conversation-{index:03d}", 1, 1, 2, 0.5),
            result=ConversationResult(f"conversation-{index:03d}"),
            importance=(count - index) / max(1, count),
        )
        for index in range(count)
    ]


def test_dialogue_modes_apply_bounded_call_budgets():
    entries = _entries(100)

    assert len(select_for_llm(entries, "economy")) == 5
    assert len(select_for_llm(entries, "balanced")) == 20
    assert len(select_for_llm(entries, "full")) == 48


def test_dialogue_policy_is_deterministic_and_uses_conversation_id_as_tiebreak():
    entries = _entries(20)
    equal = [replace(entry, importance=0.5) for entry in reversed(entries)]

    first = select_for_llm(equal, "balanced")
    second = select_for_llm(equal, "balanced")

    assert first == second
    assert first == tuple(sorted(first))


def test_dialogue_policy_handles_empty_and_small_inputs():
    assert select_for_llm([], "balanced") == ()

    one = _entries(1)
    assert select_for_llm(one, "economy") == ("conversation-000",)
