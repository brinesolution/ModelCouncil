import httpx
import pytest

from backend.app.core.config import Settings
from backend.app.services.llm_catalog import discover_llm_providers


@pytest.mark.asyncio
async def test_catalog_returns_configured_deepseek_and_populated_ollama():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/tags"
        return httpx.Response(
            200,
            json={
                "models": [
                    {
                        "name": "qwen3:8b",
                        "model": "qwen3:8b",
                        "size": 5_200_000_000,
                        "details": {
                            "family": "qwen3",
                            "parameter_size": "8B",
                            "quantization_level": "Q4_K_M",
                        },
                    },
                    {
                        "name": "llama3.2:3b",
                        "size": 2_000_000_000,
                        "details": {
                            "parameter_size": "3B",
                            "quantization_level": "Q4_K_M",
                        },
                    },
                ]
            },
        )

    settings = Settings(
        _env_file=None,
        DEEPSEEK_LIVE_ENABLED=True,
        DEEPSEEK_MODEL="deepseek-v4-flash",
        OLLAMA_BASE_URL="http://ollama.test",
    )
    catalog = await discover_llm_providers(
        settings,
        deepseek_api_key="test-key",
        transport=httpx.MockTransport(handler),
    )

    by_id = {provider.id: provider for provider in catalog.providers}
    assert set(by_id) == {"deepseek", "ollama"}
    assert by_id["deepseek"].available is True
    assert [model.id for model in by_id["deepseek"].models] == ["deepseek-v4-flash"]
    assert by_id["ollama"].available is True
    assert [model.id for model in by_id["ollama"].models] == ["llama3.2:3b", "qwen3:8b"]
    qwen = next(model for model in by_id["ollama"].models if model.id == "qwen3:8b")
    assert qwen.size_bytes == 5_200_000_000
    assert qwen.parameter_size == "8B"
    assert qwen.quantization == "Q4_K_M"


@pytest.mark.asyncio
async def test_catalog_keeps_unavailable_deepseek_visible():
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"models": []})

    settings = Settings(_env_file=None, DEEPSEEK_LIVE_ENABLED=False)
    catalog = await discover_llm_providers(
        settings,
        deepseek_api_key="",
        transport=httpx.MockTransport(handler),
    )

    deepseek = next(provider for provider in catalog.providers if provider.id == "deepseek")
    assert deepseek.available is False
    assert deepseek.models == ()


@pytest.mark.asyncio
async def test_catalog_marks_ollama_reachable_but_unusable_when_no_models():
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"models": []})

    catalog = await discover_llm_providers(
        Settings(_env_file=None),
        deepseek_api_key="",
        transport=httpx.MockTransport(handler),
    )

    ollama = next(provider for provider in catalog.providers if provider.id == "ollama")
    assert ollama.available is False
    assert ollama.reachable is True
    assert ollama.models == ()
    assert "no downloaded models" in ollama.status_message.lower()


@pytest.mark.asyncio
async def test_catalog_marks_ollama_unavailable_when_request_fails():
    def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline")

    catalog = await discover_llm_providers(
        Settings(_env_file=None),
        deepseek_api_key="",
        transport=httpx.MockTransport(handler),
    )

    ollama = next(provider for provider in catalog.providers if provider.id == "ollama")
    assert ollama.available is False
    assert ollama.reachable is False
    assert ollama.models == ()
    assert "not reachable" in ollama.status_message.lower()
