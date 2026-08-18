from __future__ import annotations

from dataclasses import dataclass

import httpx

from backend.app.core.config import Settings, resolve_deepseek_api_key


@dataclass(frozen=True, slots=True)
class LLMModelDescriptor:
    id: str
    label: str
    size_bytes: int | None = None
    parameter_size: str | None = None
    quantization: str | None = None


@dataclass(frozen=True, slots=True)
class LLMProviderDescriptor:
    id: str
    label: str
    kind: str
    available: bool
    reachable: bool
    status_message: str
    models: tuple[LLMModelDescriptor, ...]


@dataclass(frozen=True, slots=True)
class LLMProviderCatalog:
    providers: tuple[LLMProviderDescriptor, ...]


def _deepseek_descriptor(settings: Settings, api_key: str) -> LLMProviderDescriptor:
    available = bool(settings.deepseek_live_enabled and api_key.strip())
    models = (
        (LLMModelDescriptor(id=settings.deepseek_model, label=settings.deepseek_model),)
        if available
        else ()
    )
    return LLMProviderDescriptor(
        id="deepseek",
        label="DeepSeek",
        kind="cloud",
        available=available,
        reachable=available,
        status_message=(
            "Cloud API configured"
            if available
            else "DeepSeek live rendering is disabled or no API key is configured"
        ),
        models=models,
    )


async def _ollama_descriptor(
    settings: Settings,
    *,
    transport: httpx.AsyncBaseTransport | None,
) -> LLMProviderDescriptor:
    try:
        async with httpx.AsyncClient(
            timeout=settings.ollama_discovery_timeout_seconds,
            transport=transport,
        ) as client:
            response = await client.get(f"{settings.ollama_base_url.rstrip('/')}/api/tags")
            response.raise_for_status()
            body = response.json()

        raw_models = body.get("models", []) if isinstance(body, dict) else []
        models: list[LLMModelDescriptor] = []
        if isinstance(raw_models, list):
            for item in raw_models:
                if not isinstance(item, dict):
                    continue
                model_id = item.get("name") or item.get("model")
                if not isinstance(model_id, str) or not model_id.strip():
                    continue
                details = item.get("details")
                if not isinstance(details, dict):
                    details = {}
                size = item.get("size")
                models.append(
                    LLMModelDescriptor(
                        id=model_id.strip(),
                        label=model_id.strip(),
                        size_bytes=int(size) if isinstance(size, (int, float)) else None,
                        parameter_size=(
                            str(details["parameter_size"])
                            if details.get("parameter_size") is not None
                            else None
                        ),
                        quantization=(
                            str(details["quantization_level"])
                            if details.get("quantization_level") is not None
                            else None
                        ),
                    )
                )
        ordered = tuple(sorted(models, key=lambda model: model.id.lower()))
        if not ordered:
            return LLMProviderDescriptor(
                id="ollama",
                label="Ollama Local",
                kind="local",
                available=False,
                reachable=True,
                status_message="Ollama is running but no downloaded models were detected",
                models=(),
            )
        return LLMProviderDescriptor(
            id="ollama",
            label="Ollama Local",
            kind="local",
            available=True,
            reachable=True,
            status_message=f"{len(ordered)} local model{'s' if len(ordered) != 1 else ''} detected",
            models=ordered,
        )
    except (httpx.HTTPError, ValueError, TypeError):
        return LLMProviderDescriptor(
            id="ollama",
            label="Ollama Local",
            kind="local",
            available=False,
            reachable=False,
            status_message="Ollama local service is not reachable",
            models=(),
        )


async def discover_llm_provider(
    provider_id: str,
    settings: Settings,
    *,
    deepseek_api_key: str | None = None,
    transport: httpx.AsyncBaseTransport | None = None,
) -> LLMProviderDescriptor | None:
    resolved_key = (
        resolve_deepseek_api_key(settings)
        if deepseek_api_key is None
        else deepseek_api_key
    )
    if provider_id == "deepseek":
        return _deepseek_descriptor(settings, resolved_key)
    if provider_id == "ollama":
        return await _ollama_descriptor(settings, transport=transport)
    return None


async def discover_llm_providers(
    settings: Settings,
    *,
    deepseek_api_key: str | None = None,
    transport: httpx.AsyncBaseTransport | None = None,
) -> LLMProviderCatalog:
    resolved_key = (
        resolve_deepseek_api_key(settings)
        if deepseek_api_key is None
        else deepseek_api_key
    )
    ollama = await _ollama_descriptor(settings, transport=transport)
    return LLMProviderCatalog(
        providers=(
            _deepseek_descriptor(settings, resolved_key),
            ollama,
        )
    )
