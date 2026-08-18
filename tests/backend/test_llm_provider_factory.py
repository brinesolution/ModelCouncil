import httpx
import pytest

from backend.app.core.config import Settings
from backend.app.services.llm_catalog import (
    LLMModelDescriptor,
    LLMProviderCatalog,
    LLMProviderDescriptor,
)
from backend.app.services.llm_provider_factory import (
    LLMProviderResolutionError,
    resolve_llm_provider,
)
from simulation.llm.deepseek import DeepSeekProvider
from simulation.llm.ollama import OllamaProvider


def _catalog() -> LLMProviderCatalog:
    return LLMProviderCatalog(
        providers=(
            LLMProviderDescriptor(
                id="deepseek",
                label="DeepSeek",
                kind="cloud",
                available=True,
                reachable=True,
                status_message="configured",
                models=(LLMModelDescriptor(id="deepseek-v4-flash", label="deepseek-v4-flash"),),
            ),
            LLMProviderDescriptor(
                id="ollama",
                label="Ollama Local",
                kind="local",
                available=True,
                reachable=True,
                status_message="1 local model detected",
                models=(
                    LLMModelDescriptor(
                        id="qwen3:8b",
                        label="qwen3:8b",
                        size_bytes=5_000_000_000,
                        parameter_size="8B",
                        quantization="Q4_K_M",
                    ),
                ),
            ),
        )
    )


@pytest.mark.asyncio
async def test_factory_resolves_deepseek_with_cloud_pricing_and_concurrency():
    settings = Settings(
        _env_file=None,
        DEEPSEEK_LIVE_ENABLED=True,
        DEEPSEEK_FULL_LIVE_CONCURRENCY=5,
    )
    resolved = await resolve_llm_provider(
        "deepseek",
        "deepseek-v4-flash",
        settings=settings,
        catalog=_catalog(),
        deepseek_api_key="test-key",
    )

    assert isinstance(resolved.provider, DeepSeekProvider)
    assert resolved.provider_id == "deepseek"
    assert resolved.model_id == "deepseek-v4-flash"
    assert resolved.concurrency == 5
    assert resolved.pricing.cache_miss_usd_per_million > 0
    assert resolved.cache_telemetry_available is True


@pytest.mark.asyncio
async def test_factory_resolves_ollama_without_deepseek_configuration():
    settings = Settings(
        _env_file=None,
        DEEPSEEK_LIVE_ENABLED=False,
        OLLAMA_FULL_LIVE_CONCURRENCY=2,
        OLLAMA_BASE_URL="http://ollama.test",
        OLLAMA_NUM_CTX=1536,
    )
    resolved = await resolve_llm_provider(
        "ollama",
        "qwen3:8b",
        settings=settings,
        catalog=_catalog(),
        deepseek_api_key="",
        transport=httpx.MockTransport(lambda _request: httpx.Response(200, json={})),
    )

    assert isinstance(resolved.provider, OllamaProvider)
    assert resolved.provider_id == "ollama"
    assert resolved.model_id == "qwen3:8b"
    assert resolved.concurrency == 2
    assert resolved.provider.context_window == 1536
    assert resolved.pricing.cache_hit_usd_per_million == 0
    assert resolved.pricing.cache_miss_usd_per_million == 0
    assert resolved.pricing.output_usd_per_million == 0
    assert resolved.cache_telemetry_available is False


@pytest.mark.asyncio
async def test_factory_rejects_unknown_or_stale_model():
    settings = Settings(_env_file=None)

    with pytest.raises(LLMProviderResolutionError, match="Unknown LLM provider"):
        await resolve_llm_provider(
            "other",
            "model",
            settings=settings,
            catalog=_catalog(),
            deepseek_api_key="",
        )

    with pytest.raises(LLMProviderResolutionError, match="not available"):
        await resolve_llm_provider(
            "ollama",
            "removed:7b",
            settings=settings,
            catalog=_catalog(),
            deepseek_api_key="",
        )


@pytest.mark.asyncio
async def test_factory_resolving_deepseek_does_not_probe_ollama():
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise AssertionError("DeepSeek resolution must not probe Ollama")

    settings = Settings(
        _env_file=None,
        DEEPSEEK_LIVE_ENABLED=True,
        DEEPSEEK_MODEL="deepseek-v4-flash",
    )
    resolved = await resolve_llm_provider(
        "deepseek",
        "deepseek-v4-flash",
        settings=settings,
        deepseek_api_key="test-key",
        transport=httpx.MockTransport(handler),
    )

    assert resolved.provider_id == "deepseek"
    assert calls == 0


@pytest.mark.asyncio
async def test_factory_rejects_unavailable_provider():
    unavailable = LLMProviderCatalog(
        providers=(
            LLMProviderDescriptor(
                id="ollama",
                label="Ollama Local",
                kind="local",
                available=False,
                reachable=False,
                status_message="offline",
                models=(),
            ),
        )
    )

    with pytest.raises(LLMProviderResolutionError, match="unavailable"):
        await resolve_llm_provider(
            "ollama",
            "qwen3:8b",
            settings=Settings(_env_file=None),
            catalog=unavailable,
            deepseek_api_key="",
        )
