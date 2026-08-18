import asyncio

import pytest

from simulation.conversation.ledger import (
    AgentLanguageProfile,
    ConversationLanguageContext,
    ConversationLedgerEntry,
)
from simulation.conversation.models import ConversationPair, ConversationResult, SemanticMessage
from simulation.conversation.render_pipeline import DialoguePricing, render_conversation_ledger
from simulation.llm.base import LLMJsonResponse, LLMUsage
from simulation.llm.mock import MockLLMProvider


def _profile(agent_id: int, opinion: float) -> AgentLanguageProfile:
    return AgentLanguageProfile(
        agent_id=agent_id,
        age=28,
        occupation="Professional",
        primary_language="English",
        locale="Indian English",
        logicality=0.65,
        emotionality=0.55,
        sociability=0.6,
        stubbornness=0.35,
        influence_power=0.7,
        confidence=0.65,
        knowledge=0.5,
        overall_opinion=opinion,
    )


def _entry(index: int) -> ConversationLedgerEntry:
    conversation_id = f"conversation-{index:03d}"
    pair = ConversationPair(conversation_id, 1, 1, 2, 0.8 - index * 0.01)
    result = ConversationResult(
        conversation_id=conversation_id,
        messages=[
            SemanticMessage(1, 2, {"price": 0.7}, 0.8, 0.7),
            SemanticMessage(2, 1, {"usefulness": 0.6}, 0.75, 0.65),
        ],
        transcript=[
            {"speaker_id": 1, "text": "Background A"},
            {"speaker_id": 2, "text": "Background B"},
        ],
        language_source="background",
    )
    return ConversationLedgerEntry(
        round_index=1,
        pair=pair,
        result=result,
        language_context=ConversationLanguageContext(
            _profile(1, 0.4),
            _profile(2, -0.3),
        ),
        trust=0.7,
        relationship_strength=0.65,
        similarity=0.8,
        weak_tie=False,
    )


@pytest.mark.asyncio
async def test_render_pipeline_without_provider_keeps_everything_background():
    entries = [_entry(index) for index in range(10)]

    rendered, stats = await render_conversation_ledger(
        entries=entries,
        dialogue_mode="balanced",
        provider=None,
    )

    assert [entry.conversation_id for entry in rendered] == [
        entry.conversation_id for entry in entries
    ]
    assert stats.total_conversations == 10
    assert stats.selected_for_llm == 0
    assert stats.llm_rendered == 0
    assert stats.fallback_count == 0
    assert stats.background_count == 10
    assert stats.provider_available is False
    assert all(entry.result.language_source == "background" for entry in rendered)
    assert all(entry.importance > 0 for entry in rendered)


@pytest.mark.asyncio
async def test_balanced_pipeline_upgrades_only_selected_conversations_and_preserves_semantics():
    entries = [_entry(index) for index in range(10)]
    original_messages = {
        entry.conversation_id: list(entry.result.messages) for entry in entries
    }

    rendered, stats = await render_conversation_ledger(
        entries=entries,
        dialogue_mode="balanced",
        provider=MockLLMProvider(),
    )

    assert stats.selected_for_llm == 2
    assert stats.llm_rendered == 2
    assert stats.fallback_count == 0
    assert stats.background_count == 8
    assert stats.provider_available is True
    assert sum(entry.llm_selected for entry in rendered) == 2
    assert sum(entry.result.language_source == "deepseek" for entry in rendered) == 2
    for entry in rendered:
        assert entry.result.messages == original_messages[entry.conversation_id]


class TelemetryProvider:
    def __init__(self):
        self.calls = 0
        self.active = 0
        self.max_active = 0
        self.events: list[str] = []

    async def generate_json(self, **_kwargs):
        index = self.calls
        self.calls += 1
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        self.events.append(f"start-{index}")
        await asyncio.sleep(0.01)
        self.events.append(f"end-{index}")
        self.active -= 1
        return LLMJsonResponse(
            data={
                "conversation": [
                    {"speaker": "A", "text": f"Rendered A {index}"},
                    {"speaker": "B", "text": f"Rendered B {index}"},
                ]
            },
            usage=LLMUsage(
                prompt_tokens=100,
                prompt_cache_hit_tokens=60,
                prompt_cache_miss_tokens=40,
                completion_tokens=20,
                total_tokens=120,
            ),
            latency_ms=20.0 + index,
            model="telemetry-model",
        )


@pytest.mark.asyncio
async def test_full_pipeline_respects_hard_live_request_budget():
    entries = [_entry(index) for index in range(30)]
    provider = TelemetryProvider()

    rendered, stats = await render_conversation_ledger(
        entries=entries,
        dialogue_mode="full",
        provider=provider,
        max_live_requests=10,
        cache_prime_requests=2,
    )

    assert provider.calls == 10
    assert stats.selected_for_llm == 10
    assert stats.llm_rendered == 10
    assert sum(entry.llm_selected for entry in rendered) == 10


@pytest.mark.asyncio
async def test_pipeline_primes_first_two_requests_before_concurrent_bulk():
    entries = [_entry(index) for index in range(20)]
    provider = TelemetryProvider()

    await render_conversation_ledger(
        entries=entries,
        dialogue_mode="full",
        provider=provider,
        max_live_requests=6,
        cache_prime_requests=2,
        concurrency=4,
    )

    assert provider.events[:4] == ["start-0", "end-0", "start-1", "end-1"]
    assert provider.max_active > 1


@pytest.mark.asyncio
async def test_pipeline_aggregates_cache_latency_and_estimated_cost():
    entries = [_entry(index) for index in range(10)]
    provider = TelemetryProvider()
    pricing = DialoguePricing(
        cache_hit_usd_per_million=0.0028,
        cache_miss_usd_per_million=0.14,
        output_usd_per_million=0.28,
    )

    _rendered, stats = await render_conversation_ledger(
        entries=entries,
        dialogue_mode="balanced",
        provider=provider,
        max_live_requests=10,
        cache_prime_requests=2,
        pricing=pricing,
    )

    assert stats.selected_for_llm == 2
    assert stats.prompt_tokens == 200
    assert stats.prompt_cache_hit_tokens == 120
    assert stats.prompt_cache_miss_tokens == 80
    assert stats.completion_tokens == 40
    assert stats.total_tokens == 240
    assert stats.cache_hit_ratio == pytest.approx(0.60)
    assert stats.average_latency_ms == pytest.approx(20.5)
    assert stats.max_latency_ms == pytest.approx(21.0)
    expected_cost = (120 * 0.0028 + 80 * 0.14 + 40 * 0.28) / 1_000_000
    assert stats.estimated_cost_usd == pytest.approx(expected_cost)
    assert stats.provider_model == "telemetry-model"


class BrokenProvider:
    async def generate_json(self, **_kwargs):
        raise RuntimeError("provider unavailable")


@pytest.mark.asyncio
async def test_render_pipeline_counts_fail_closed_llm_fallbacks():
    entries = [_entry(index) for index in range(10)]

    rendered, stats = await render_conversation_ledger(
        entries=entries,
        dialogue_mode="economy",
        provider=BrokenProvider(),
    )

    assert stats.selected_for_llm == 1
    assert stats.llm_rendered == 0
    assert stats.fallback_count == 1
    assert stats.background_count == 10
    selected = [entry for entry in rendered if entry.llm_selected]
    assert len(selected) == 1
    assert selected[0].result.language_source == "background"
