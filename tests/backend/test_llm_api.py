import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.llm_catalog import (
    LLMModelDescriptor,
    LLMProviderCatalog,
    LLMProviderDescriptor,
)


client = TestClient(app)


def _catalog() -> LLMProviderCatalog:
    return LLMProviderCatalog(
        providers=(
            LLMProviderDescriptor(
                id="deepseek",
                label="DeepSeek",
                kind="cloud",
                available=True,
                reachable=True,
                status_message="Cloud API configured",
                models=(
                    LLMModelDescriptor(
                        id="deepseek-v4-flash",
                        label="deepseek-v4-flash",
                    ),
                ),
            ),
            LLMProviderDescriptor(
                id="ollama",
                label="Ollama Local",
                kind="local",
                available=False,
                reachable=False,
                status_message="Ollama local service is not reachable",
                models=(),
            ),
        )
    )


def test_llm_provider_catalog_endpoint_serializes_known_sources(monkeypatch):
    async def fake_discover(*_args, **_kwargs):
        return _catalog()

    monkeypatch.setattr(
        "backend.app.api.routes.llm.discover_llm_providers",
        fake_discover,
    )

    response = client.get("/api/v1/llm/providers")

    assert response.status_code == 200
    body = response.json()
    assert [provider["id"] for provider in body["providers"]] == ["deepseek", "ollama"]
    assert body["providers"][0]["models"][0]["id"] == "deepseek-v4-flash"
    assert body["providers"][1]["available"] is False
    assert body["providers"][1]["models"] == []
