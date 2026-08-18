from __future__ import annotations

import asyncio
from dataclasses import dataclass, replace

from simulation.conversation.dialogue_policy import select_for_llm
from simulation.conversation.importance import score_conversation
from simulation.conversation.language_renderer import (
    LanguageRenderOutcome,
    render_conversation_language,
)
from simulation.conversation.ledger import ConversationLedgerEntry, ProductLanguageContext
from simulation.llm.base import LLMJsonResponse, LLMProvider
from simulation.audit.logger import RunAuditSink


@dataclass(frozen=True, slots=True)
class DialoguePricing:
    cache_hit_usd_per_million: float = 0.0028
    cache_miss_usd_per_million: float = 0.14
    output_usd_per_million: float = 0.28


@dataclass(frozen=True, slots=True)
class DialogueRenderStats:
    total_conversations: int
    selected_for_llm: int
    llm_rendered: int
    fallback_count: int
    background_count: int
    provider_available: bool
    provider_model: str | None = None
    prompt_tokens: int = 0
    prompt_cache_hit_tokens: int = 0
    prompt_cache_miss_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cache_hit_ratio: float = 0.0
    average_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    estimated_cost_usd: float = 0.0


async def render_conversation_ledger(
    *,
    entries: list[ConversationLedgerEntry],
    dialogue_mode: str,
    provider: LLMProvider | None,
    concurrency: int = 4,
    product_context: ProductLanguageContext | None = None,
    max_live_requests: int = 10,
    cache_prime_requests: int = 2,
    pricing: DialoguePricing = DialoguePricing(),
    audit: RunAuditSink | None = None,
) -> tuple[list[ConversationLedgerEntry], DialogueRenderStats]:
    if concurrency < 1:
        raise ValueError("concurrency must be at least 1")
    if max_live_requests < 0:
        raise ValueError("max_live_requests cannot be negative")
    if cache_prime_requests < 0:
        raise ValueError("cache_prime_requests cannot be negative")

    scored = [replace(entry, importance=score_conversation(entry)) for entry in entries]
    provider_available = provider is not None
    policy_ids = (
        set(select_for_llm(scored, dialogue_mode)) if provider_available else set()
    )
    selected_entries = sorted(
        (entry for entry in scored if entry.conversation_id in policy_ids),
        key=lambda entry: (-entry.importance, entry.conversation_id),
    )[:max_live_requests]
    selected_ids = {entry.conversation_id for entry in selected_entries}

    if not selected_entries:
        rendered = [replace(entry, llm_selected=False) for entry in scored]
        return rendered, _build_stats(
            rendered=rendered,
            selected_count=0,
            provider_available=provider_available,
            responses=[],
            pricing=pricing,
        )

    assert provider is not None
    semaphore = asyncio.Semaphore(concurrency)

    async def render_one(
        entry: ConversationLedgerEntry,
    ) -> tuple[ConversationLedgerEntry, LanguageRenderOutcome]:
        async with semaphore:
            outcome = await render_conversation_language(
                pair=entry.pair,
                semantic_result=entry.result,
                language_context=entry.language_context,
                provider=provider,
                language_source="deepseek",
                product_context=product_context,
                audit=audit,
            )
        return replace(entry, result=outcome.result, llm_selected=True), outcome

    updates: dict[str, ConversationLedgerEntry] = {}
    outcomes: list[LanguageRenderOutcome] = []
    prime_count = min(cache_prime_requests, len(selected_entries))

    # DeepSeek cache construction/common-prefix detection happens server-side. Running
    # the first few requests serially gives those prefix units time to become reusable
    # before we fan out the remaining selected conversations.
    for entry in selected_entries[:prime_count]:
        rendered_entry, outcome = await render_one(entry)
        updates[entry.conversation_id] = rendered_entry
        outcomes.append(outcome)

    bulk_entries = selected_entries[prime_count:]
    if bulk_entries:
        bulk_results = await asyncio.gather(*(render_one(entry) for entry in bulk_entries))
        for rendered_entry, outcome in bulk_results:
            updates[rendered_entry.conversation_id] = rendered_entry
            outcomes.append(outcome)

    rendered = [
        updates.get(entry.conversation_id, replace(entry, llm_selected=False))
        for entry in scored
    ]
    responses = [
        outcome.provider_response
        for outcome in outcomes
        if outcome.provider_response is not None
    ]
    return rendered, _build_stats(
        rendered=rendered,
        selected_count=len(selected_ids),
        provider_available=True,
        responses=responses,
        pricing=pricing,
    )


def _build_stats(
    *,
    rendered: list[ConversationLedgerEntry],
    selected_count: int,
    provider_available: bool,
    responses: list[LLMJsonResponse],
    pricing: DialoguePricing,
) -> DialogueRenderStats:
    successful = sum(
        entry.llm_selected and entry.result.language_source == "deepseek"
        for entry in rendered
    )
    fallbacks = sum(
        entry.llm_selected and entry.result.language_source != "deepseek"
        for entry in rendered
    )

    prompt_tokens = sum(response.usage.prompt_tokens for response in responses)
    hit_tokens = sum(response.usage.prompt_cache_hit_tokens for response in responses)
    miss_tokens = sum(response.usage.prompt_cache_miss_tokens for response in responses)
    completion_tokens = sum(response.usage.completion_tokens for response in responses)
    total_tokens = sum(response.usage.total_tokens for response in responses)
    cache_input_tokens = hit_tokens + miss_tokens
    cache_hit_ratio = hit_tokens / cache_input_tokens if cache_input_tokens else 0.0
    latencies = [response.latency_ms for response in responses]
    average_latency = sum(latencies) / len(latencies) if latencies else 0.0
    max_latency = max(latencies, default=0.0)
    estimated_cost = (
        hit_tokens * pricing.cache_hit_usd_per_million
        + miss_tokens * pricing.cache_miss_usd_per_million
        + completion_tokens * pricing.output_usd_per_million
    ) / 1_000_000
    models = {response.model for response in responses if response.model}
    provider_model = next(iter(models)) if len(models) == 1 else ("mixed" if models else None)

    return DialogueRenderStats(
        total_conversations=len(rendered),
        selected_for_llm=selected_count,
        llm_rendered=successful,
        fallback_count=fallbacks,
        background_count=len(rendered) - successful,
        provider_available=provider_available,
        provider_model=provider_model,
        prompt_tokens=prompt_tokens,
        prompt_cache_hit_tokens=hit_tokens,
        prompt_cache_miss_tokens=miss_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        cache_hit_ratio=cache_hit_ratio,
        average_latency_ms=average_latency,
        max_latency_ms=max_latency,
        estimated_cost_usd=estimated_cost,
    )
