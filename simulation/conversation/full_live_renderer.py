from __future__ import annotations

import asyncio
import inspect
from dataclasses import dataclass, replace
from typing import Awaitable, Callable

from simulation.conversation.importance import score_conversation
from simulation.conversation.language_renderer import (
    LanguageRenderOutcome,
    render_conversation_language,
)
from simulation.conversation.ledger import ConversationLedgerEntry, ProductLanguageContext
from simulation.conversation.render_pipeline import DialoguePricing, DialogueRenderStats
from simulation.llm.base import LLMJsonResponse, LLMProvider
from simulation.audit.logger import RunAuditSink


@dataclass(frozen=True, slots=True)
class FullLiveProgress:
    total_conversations: int
    processed_conversations: int
    successful_renders: int
    fallback_count: int
    prompt_tokens: int
    prompt_cache_hit_tokens: int
    prompt_cache_miss_tokens: int
    completion_tokens: int
    total_tokens: int
    cache_hit_ratio: float
    average_latency_ms: float
    max_latency_ms: float
    estimated_cost_usd: float
    provider_model: str | None


@dataclass(frozen=True, slots=True)
class FullLiveRenderOutcome:
    entries: list[ConversationLedgerEntry]
    stats: DialogueRenderStats
    processed_conversations: int
    cancelled: bool


ProgressCallback = Callable[[FullLiveProgress], Awaitable[None] | None]
CancellationCheck = Callable[[], bool]


async def render_all_conversations_live(
    *,
    entries: list[ConversationLedgerEntry],
    provider: LLMProvider,
    product_context: ProductLanguageContext,
    concurrency: int,
    cache_prime_requests: int,
    language_source: str = "deepseek",
    pricing: DialoguePricing = DialoguePricing(),
    on_progress: ProgressCallback | None = None,
    is_cancelled: CancellationCheck | None = None,
    audit: RunAuditSink | None = None,
) -> FullLiveRenderOutcome:
    """Render every scheduled conversation unless cancellation stops new claims.

    The function never creates conversation tasks for the entire ledger at once. After
    serial cache priming it runs a fixed number of workers that claim the next ledger
    index, keeping memory bounded even for very large conversation histories.
    """
    if concurrency < 1:
        raise ValueError("concurrency must be at least 1")
    if cache_prime_requests < 0:
        raise ValueError("cache_prime_requests cannot be negative")

    rendered = [replace(entry, importance=score_conversation(entry)) for entry in entries]
    processed = 0
    successful = 0
    fallbacks = 0
    prompt_tokens = 0
    hit_tokens = 0
    miss_tokens = 0
    completion_tokens = 0
    total_tokens = 0
    latency_total = 0.0
    latency_samples = 0
    max_latency = 0.0
    models: set[str] = set()
    progress_lock = asyncio.Lock()

    def cancelled_now() -> bool:
        return bool(is_cancelled and is_cancelled())

    def provider_model() -> str | None:
        if len(models) == 1:
            return next(iter(models))
        if len(models) > 1:
            return "mixed"
        return None

    def current_progress() -> FullLiveProgress:
        cache_input = hit_tokens + miss_tokens
        cache_ratio = hit_tokens / cache_input if cache_input else 0.0
        average_latency = latency_total / latency_samples if latency_samples else 0.0
        estimated_cost = (
            hit_tokens * pricing.cache_hit_usd_per_million
            + miss_tokens * pricing.cache_miss_usd_per_million
            + completion_tokens * pricing.output_usd_per_million
        ) / 1_000_000
        return FullLiveProgress(
            total_conversations=len(rendered),
            processed_conversations=processed,
            successful_renders=successful,
            fallback_count=fallbacks,
            prompt_tokens=prompt_tokens,
            prompt_cache_hit_tokens=hit_tokens,
            prompt_cache_miss_tokens=miss_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cache_hit_ratio=cache_ratio,
            average_latency_ms=average_latency,
            max_latency_ms=max_latency,
            estimated_cost_usd=estimated_cost,
            provider_model=provider_model(),
        )

    async def notify() -> None:
        if on_progress is None:
            return
        maybe_awaitable = on_progress(current_progress())
        if inspect.isawaitable(maybe_awaitable):
            await maybe_awaitable

    async def record(
        index: int,
        outcome: LanguageRenderOutcome,
    ) -> None:
        nonlocal processed, successful, fallbacks
        nonlocal prompt_tokens, hit_tokens, miss_tokens, completion_tokens, total_tokens
        nonlocal latency_total, latency_samples, max_latency

        async with progress_lock:
            rendered[index] = replace(
                rendered[index],
                result=outcome.result,
                llm_selected=True,
            )
            processed += 1
            if outcome.succeeded:
                successful += 1
            else:
                fallbacks += 1

            response: LLMJsonResponse | None = outcome.provider_response
            if response is not None:
                prompt_tokens += response.usage.prompt_tokens
                hit_tokens += response.usage.prompt_cache_hit_tokens
                miss_tokens += response.usage.prompt_cache_miss_tokens
                completion_tokens += response.usage.completion_tokens
                total_tokens += response.usage.total_tokens
                latency_total += response.latency_ms
                latency_samples += 1
                max_latency = max(max_latency, response.latency_ms)
                if response.model:
                    models.add(response.model)

            await notify()

    async def render_index(index: int) -> None:
        entry = rendered[index]
        outcome = await render_conversation_language(
            pair=entry.pair,
            semantic_result=entry.result,
            language_context=entry.language_context,
            provider=provider,
            language_source=language_source,
            product_context=product_context,
            audit=audit,
        )
        await record(index, outcome)

    prime_count = min(cache_prime_requests, len(rendered))
    for index in range(prime_count):
        if cancelled_now():
            break
        await render_index(index)

    next_index = processed
    claim_lock = asyncio.Lock()

    async def claim_next() -> int | None:
        nonlocal next_index
        async with claim_lock:
            if cancelled_now() or next_index >= len(rendered):
                return None
            index = next_index
            next_index += 1
            return index

    async def worker() -> None:
        while True:
            index = await claim_next()
            if index is None:
                return
            await render_index(index)

    if next_index < len(rendered) and not cancelled_now():
        worker_count = min(concurrency, len(rendered) - next_index)
        await asyncio.gather(*(worker() for _ in range(worker_count)))

    progress = current_progress()
    cancelled = cancelled_now() and processed < len(rendered)
    stats = DialogueRenderStats(
        total_conversations=len(rendered),
        selected_for_llm=processed,
        llm_rendered=successful,
        fallback_count=fallbacks,
        background_count=len(rendered) - successful,
        provider_available=True,
        provider_model=progress.provider_model,
        prompt_tokens=prompt_tokens,
        prompt_cache_hit_tokens=hit_tokens,
        prompt_cache_miss_tokens=miss_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        cache_hit_ratio=progress.cache_hit_ratio,
        average_latency_ms=progress.average_latency_ms,
        max_latency_ms=progress.max_latency_ms,
        estimated_cost_usd=progress.estimated_cost_usd,
    )
    return FullLiveRenderOutcome(
        entries=rendered,
        stats=stats,
        processed_conversations=processed,
        cancelled=cancelled,
    )
