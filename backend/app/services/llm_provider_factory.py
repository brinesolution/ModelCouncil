from __future__ import annotations

from dataclasses import dataclass

import httpx

from backend.app.core.config import Settings, resolve_deepseek_api_key
from backend.app.services.llm_catalog import (
    LLMProviderCatalog,
    discover_llm_provider,
)
from simulation.conversation.render_pipeline import DialoguePricing
from simulation.llm.base import LLMProvider
from simulation.llm.deepseek import DeepSeekProvider
from simulation.llm.ollama import OllamaProvider


class LLMProviderResolutionError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ResolvedLLMProvider:
    provider_id: str
    model_id: str
    label: str
    kind: str
    provider: LLMProvider
    concurrency: int
    pricing: DialoguePricing
    cache_telemetry_available: bool


async def resolve_llm_provider(
    provider_id: str,
    model_id: str,
    *,
    settings: Settings,
    catalog: LLMProviderCatalog | None = None,
    deepseek_api_key: str | None = None,
    transport: httpx.AsyncBaseTransport | None = None,
) -> ResolvedLLMProvider:
    resolved_key = (
        resolve_deepseek_api_key(settings)
        if deepseek_api_key is None
        else deepseek_api_key
    )
    if catalog is not None:
        descriptor = next(
            (provider for provider in catalog.providers if provider.id == provider_id),
            None,
        )
    else:
        descriptor = await discover_llm_provider(
            provider_id,
            settings,
            deepseek_api_key=resolved_key,
            transport=transport,
        )
    if descriptor is None:
        raise LLMProviderResolutionError(f"Unknown LLM provider: {provider_id}")
    if not descriptor.available:
        raise LLMProviderResolutionError(
            f"LLM provider {descriptor.label} is unavailable: {descriptor.status_message}"
        )
    if model_id not in {model.id for model in descriptor.models}:
        raise LLMProviderResolutionError(
            f"Model {model_id} is not available for provider {descriptor.label}. Refresh providers and choose an available model."
        )

    if provider_id == "deepseek":
        if not resolved_key:
            raise LLMProviderResolutionError("DeepSeek API key is not configured.")
        provider: LLMProvider = DeepSeekProvider(
            api_key=resolved_key,
            base_url=settings.deepseek_base_url,
            model=model_id,
            thinking=settings.deepseek_thinking,
            transport=transport,
        )
        return ResolvedLLMProvider(
            provider_id=provider_id,
            model_id=model_id,
            label=descriptor.label,
            kind=descriptor.kind,
            provider=provider,
            concurrency=settings.deepseek_full_live_concurrency,
            pricing=DialoguePricing(
                cache_hit_usd_per_million=settings.deepseek_cache_hit_usd_per_million,
                cache_miss_usd_per_million=settings.deepseek_cache_miss_usd_per_million,
                output_usd_per_million=settings.deepseek_output_usd_per_million,
            ),
            cache_telemetry_available=True,
        )

    if provider_id == "ollama":
        provider = OllamaProvider(
            base_url=settings.ollama_base_url,
            model=model_id,
            timeout_seconds=settings.ollama_request_timeout_seconds,
            context_window=settings.ollama_num_ctx,
            transport=transport,
        )
        return ResolvedLLMProvider(
            provider_id=provider_id,
            model_id=model_id,
            label=descriptor.label,
            kind=descriptor.kind,
            provider=provider,
            concurrency=settings.ollama_full_live_concurrency,
            pricing=DialoguePricing(
                cache_hit_usd_per_million=0.0,
                cache_miss_usd_per_million=0.0,
                output_usd_per_million=0.0,
            ),
            cache_telemetry_available=False,
        )

    raise LLMProviderResolutionError(f"Unknown LLM provider: {provider_id}")
