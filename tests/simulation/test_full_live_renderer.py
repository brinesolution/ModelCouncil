import asyncio
import json

import pytest

from simulation.conversation.full_live_renderer import render_all_conversations_live
from simulation.conversation.ledger import (
    AgentLanguageProfile,
    ConversationLanguageContext,
    ConversationLedgerEntry,
    ProductLanguageContext,
)
from simulation.conversation.models import ConversationPair, ConversationResult, SemanticMessage
from simulation.llm.base import LLMJsonResponse, LLMUsage


def _profile(agent_id: int, opinion: float) -> AgentLanguageProfile:
    return AgentLanguageProfile(
        agent_id=agent_id,
        age=31,
        occupation="Professional",
        primary_language="English",
        locale="Indian English",
        logicality=0.65,
        emotionality=0.45,
        sociability=0.62,
        stubbornness=0.32,
        influence_power=0.71,
        confidence=0.66,
        knowledge=0.52,
        overall_opinion=opinion,
        income_score=0.7,
        price_sensitivity=0.4,
        technology_adoption=0.8,
        product_need=0.65,
        risk_tolerance=0.6,
        brand_loyalty=0.3,
    )


def _entry(index: int) -> ConversationLedgerEntry:
    conversation_id = f"conversation-{index:03d}"
    pair = ConversationPair(conversation_id, 1, 1, 2, 0.8)
    result = ConversationResult(
        conversation_id=conversation_id,
        messages=[
            SemanticMessage(1, 2, {"price": 0.45}, 0.75, 0.7),
            SemanticMessage(2, 1, {"usefulness": 0.55}, 0.7, 0.65),
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
            agent_a=_profile(1, 0.25),
            agent_b=_profile(2, -0.1),
        ),
        trust=0.65,
        relationship_strength=0.6,
        similarity=0.8,
        weak_tie=False,
    )


def _conversation_id(user_prompt: str) -> str:
    payload = json.loads(user_prompt)
    return str(payload["dynamic_conversation"]["conversation_id"])


class TrackingProvider:
    def __init__(self, *, fail_ids: set[str] | None = None, delay: float = 0.002):
        self.fail_ids = fail_ids or set()
        self.delay = delay
        self.calls: list[str] = []
        self.active = 0
        self.max_active = 0
        self.active_at_start: list[tuple[str, int]] = []

    async def generate_json(
        self,
        *,
        system_prompt,
        user_prompt,
        max_tokens=700,
        json_schema=None,
    ):
        del json_schema
        conversation_id = _conversation_id(user_prompt)
        self.calls.append(conversation_id)
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        self.active_at_start.append((conversation_id, self.active))
        try:
            await asyncio.sleep(self.delay)
            if conversation_id in self.fail_ids:
                raise RuntimeError("simulated provider failure")
            return LLMJsonResponse(
                data={
                    "conversation": [
                        {"speaker": "A", "text": f"Live A {conversation_id}"},
                        {"speaker": "B", "text": f"Live B {conversation_id}"},
                    ]
                },
                usage=LLMUsage(
                    prompt_tokens=100,
                    prompt_cache_hit_tokens=60,
                    prompt_cache_miss_tokens=40,
                    completion_tokens=20,
                    total_tokens=120,
                ),
                latency_ms=25.0,
                model="deepseek-v4-flash",
            )
        finally:
            self.active -= 1


_PRODUCT = ProductLanguageContext(
    name="PulseDesk Focus Lamp",
    category="Smart Home / Productivity",
    price=3499,
    currency="INR",
    pitch_excerpt="Adaptive desk lighting and focus controls.",
)


@pytest.mark.asyncio
async def test_full_live_renderer_uses_selected_provider_as_language_source():
    outcome = await render_all_conversations_live(
        entries=[_entry(1)],
        provider=TrackingProvider(),
        product_context=_PRODUCT,
        concurrency=1,
        cache_prime_requests=0,
        language_source="ollama",
    )

    assert outcome.entries[0].result.language_source == "ollama"


@pytest.mark.asyncio
async def test_full_live_renderer_attempts_every_entry_without_total_cap_and_preserves_semantics():
    entries = [_entry(index) for index in range(25)]
    provider = TrackingProvider()
    original_messages = {
        entry.conversation_id: list(entry.result.messages) for entry in entries
    }

    outcome = await render_all_conversations_live(
        entries=entries,
        provider=provider,
        product_context=_PRODUCT,
        concurrency=4,
        cache_prime_requests=2,
    )

    assert len(provider.calls) == 25
    assert outcome.processed_conversations == 25
    assert outcome.cancelled is False
    assert outcome.stats.selected_for_llm == 25
    assert outcome.stats.llm_rendered == 25
    assert outcome.stats.fallback_count == 0
    assert [entry.conversation_id for entry in outcome.entries] == [
        entry.conversation_id for entry in entries
    ]
    assert all(entry.llm_selected for entry in outcome.entries)
    for entry in outcome.entries:
        assert entry.result.messages == original_messages[entry.conversation_id]


@pytest.mark.asyncio
async def test_full_live_renderer_primes_serially_then_bounds_concurrency():
    entries = [_entry(index) for index in range(12)]
    provider = TrackingProvider(delay=0.01)

    await render_all_conversations_live(
        entries=entries,
        provider=provider,
        product_context=_PRODUCT,
        concurrency=3,
        cache_prime_requests=2,
    )

    assert provider.active_at_start[0][1] == 1
    assert provider.active_at_start[1][1] == 1
    assert provider.max_active <= 3
    assert provider.max_active > 1


@pytest.mark.asyncio
async def test_full_live_renderer_falls_back_one_call_and_continues_later_entries():
    entries = [_entry(index) for index in range(5)]
    provider = TrackingProvider(fail_ids={"conversation-002"})

    outcome = await render_all_conversations_live(
        entries=entries,
        provider=provider,
        product_context=_PRODUCT,
        concurrency=2,
        cache_prime_requests=1,
    )

    assert len(provider.calls) == 5
    assert outcome.processed_conversations == 5
    assert outcome.stats.llm_rendered == 4
    assert outcome.stats.fallback_count == 1
    assert outcome.stats.average_latency_ms == pytest.approx(25.0)
    failed = next(
        entry for entry in outcome.entries if entry.conversation_id == "conversation-002"
    )
    assert failed.llm_selected is True
    assert failed.result.language_source == "background"


@pytest.mark.asyncio
async def test_full_live_renderer_stops_claiming_new_work_after_cancellation():
    entries = [_entry(index) for index in range(10)]
    provider = TrackingProvider(delay=0.001)
    cancelled = False
    progress_counts: list[int] = []

    def is_cancelled() -> bool:
        return cancelled

    async def on_progress(progress) -> None:
        nonlocal cancelled
        progress_counts.append(progress.processed_conversations)
        if progress.processed_conversations >= 3:
            cancelled = True

    outcome = await render_all_conversations_live(
        entries=entries,
        provider=provider,
        product_context=_PRODUCT,
        concurrency=1,
        cache_prime_requests=1,
        on_progress=on_progress,
        is_cancelled=is_cancelled,
    )

    assert outcome.cancelled is True
    assert outcome.processed_conversations == 3
    assert len(provider.calls) == 3
    assert progress_counts == [1, 2, 3]
    assert sum(entry.llm_selected for entry in outcome.entries) == 3
