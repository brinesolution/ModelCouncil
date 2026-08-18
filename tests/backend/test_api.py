import asyncio
import time

import pytest
from fastapi.testclient import TestClient

from backend.app.core.config import Settings, resolve_deepseek_api_key
from backend.app.main import app
from backend.app.schemas.simulation import FullLiveSimulationRequest, SimulationPreviewRequest
from backend.app.services import full_live_service, simulation_service
from backend.app.services.llm_provider_factory import (
    LLMProviderResolutionError,
    ResolvedLLMProvider,
)
from simulation.conversation.render_pipeline import DialoguePricing
from simulation.llm.base import LLMJsonResponse, LLMUsage
from simulation.llm.mock import MockLLMProvider

client = TestClient(app)


def test_project_env_deepseek_key_wins_over_stale_process_key(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-stale-process-key")
    env_file = tmp_path / ".env"
    env_file.write_text("DEEPSEEK_API_KEY=project-test-key\n", encoding="utf-8")
    settings = Settings(_env_file=None)

    assert settings.deepseek_api_key == "test-stale-process-key"
    assert resolve_deepseek_api_key(settings, env_file=env_file) == "project-test-key"


@pytest.fixture(autouse=True)
def disable_live_llm(monkeypatch):
    monkeypatch.setattr(
        "backend.app.services.simulation_service._deepseek_provider_or_none",
        lambda: None,
    )


def test_conversation_view_builder_uses_diversity_selector(monkeypatch) -> None:
    sentinel = object()
    captured = {}

    def fake_selector(entries, *, limit=12):
        captured["entries"] = entries
        captured["limit"] = limit
        return []

    monkeypatch.setattr(
        simulation_service,
        "select_replay_conversations",
        fake_selector,
        raising=False,
    )

    assert simulation_service._conversation_views([sentinel], limit=7) == []
    assert captured == {"entries": [sentinel], "limit": 7}


def test_full_live_dialogue_mode_parses_in_request_contract() -> None:
    request = SimulationPreviewRequest.model_validate(
        {
            "product": {
                "name": "AI Fitness Coach",
                "category": "Fitness Technology",
                "pitch": "Personalized workouts, nutrition guidance, and progress tracking.",
                "price": 999,
                "currency": "INR",
            },
            "population_mode": "small",
            "dialogue_mode": "full_live",
            "rounds": 2,
            "seed": 42,
        }
    )

    assert request.dialogue_mode.value == "full_live"


def _full_live_payload(
    *,
    rounds: int = 1,
    confirmed: bool = True,
    provider: str = "deepseek",
    model: str = "deepseek-v4-flash",
) -> dict:
    return {
        "product": {
            "name": "PulseDesk Focus Lamp",
            "category": "Smart Home / Productivity",
            "pitch": "Adaptive desk lighting with focus controls and no required subscription.",
            "price": 3499,
            "currency": "INR",
        },
        "population_mode": "small",
        "dialogue_mode": "full_live",
        "rounds": rounds,
        "seed": 42,
        "full_live_confirmed": confirmed,
        "llm_provider": provider,
        "llm_model": model,
    }


def _resolved_full_live_provider(
    provider_id: str = "deepseek",
    model_id: str = "deepseek-v4-flash",
    *,
    provider=None,
) -> ResolvedLLMProvider:
    return ResolvedLLMProvider(
        provider_id=provider_id,
        model_id=model_id,
        label="DeepSeek" if provider_id == "deepseek" else "Ollama Local",
        kind="cloud" if provider_id == "deepseek" else "local",
        provider=provider or MockLLMProvider(),
        concurrency=2,
        pricing=DialoguePricing(),
        cache_telemetry_available=provider_id == "deepseek",
    )


class SlowMockLLMProvider(MockLLMProvider):
    async def generate_json(self, **kwargs):
        await asyncio.sleep(0.01)
        return await super().generate_json(**kwargs)


def _wait_for_terminal_status(test_client: TestClient, job_id: str, timeout: float = 5.0) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        response = test_client.get(f"/api/v1/simulations/full-live/{job_id}")
        assert response.status_code == 200
        body = response.json()
        if body["status"] in {"completed", "failed", "cancelled"}:
            return body
        time.sleep(0.02)
    raise AssertionError("Full Live job did not reach a terminal state")


def test_full_live_request_requires_provider_and_model() -> None:
    payload = _full_live_payload()
    payload.pop("llm_provider")
    payload.pop("llm_model")

    with pytest.raises(ValueError):
        FullLiveSimulationRequest.model_validate(payload)


def test_full_live_start_requires_explicit_confirmation() -> None:
    with TestClient(app) as test_client:
        response = test_client.post(
            "/api/v1/simulations/full-live",
            json=_full_live_payload(confirmed=False),
        )
    assert response.status_code == 422


def test_full_live_start_rejects_when_live_provider_is_unavailable(monkeypatch) -> None:
    async def reject(*_args, **_kwargs):
        raise LLMProviderResolutionError("provider unavailable")

    monkeypatch.setattr(full_live_service, "resolve_llm_provider", reject)
    with TestClient(app) as test_client:
        response = test_client.post(
            "/api/v1/simulations/full-live",
            json=_full_live_payload(),
        )
    assert response.status_code == 503
    assert "unavailable" in response.json()["detail"].lower()


def test_full_live_lifecycle_start_status_result_and_unknown_job(monkeypatch) -> None:
    async def resolve(provider_id, model_id, **_kwargs):
        return _resolved_full_live_provider(provider_id, model_id)

    monkeypatch.setattr(full_live_service, "resolve_llm_provider", resolve)
    with TestClient(app) as test_client:
        start = test_client.post(
            "/api/v1/simulations/full-live",
            json=_full_live_payload(),
        )
        assert start.status_code == 202
        start_body = start.json()
        assert start_body["status"] == "queued"
        assert start_body["estimated_upper_bound_conversations"] == 250
        assert start_body["llm_provider"] == "deepseek"
        assert start_body["llm_model"] == "deepseek-v4-flash"
        job_id = start_body["job_id"]

        terminal = _wait_for_terminal_status(test_client, job_id)
        assert terminal["status"] == "completed"
        assert terminal["processed_conversations"] == terminal["total_conversations"]
        assert terminal["successful_renders"] == terminal["total_conversations"]
        assert terminal["llm_provider"] == "deepseek"
        assert terminal["llm_model"] == "deepseek-v4-flash"

        result = test_client.get(f"/api/v1/simulations/full-live/{job_id}/result")
        assert result.status_code == 200
        body = result.json()
        assert body["dialogue_mode"] == "full_live"
        assert body["llm_provider"] == "deepseek"
        assert body["llm_model"] == "deepseek-v4-flash"
        assert body["dialogue_stats"]["selected_for_llm"] == body["summary"]["conversation_count"]

        missing = test_client.get("/api/v1/simulations/full-live/not-a-job")
        assert missing.status_code == 404


def test_full_live_ollama_lifecycle_uses_selected_local_model(monkeypatch) -> None:
    async def resolve(provider_id, model_id, **_kwargs):
        assert provider_id == "ollama"
        assert model_id == "qwen3:8b"
        return _resolved_full_live_provider(provider_id, model_id)

    monkeypatch.setattr(full_live_service, "resolve_llm_provider", resolve)
    with TestClient(app) as test_client:
        start = test_client.post(
            "/api/v1/simulations/full-live",
            json=_full_live_payload(provider="ollama", model="qwen3:8b"),
        )
        assert start.status_code == 202
        assert start.json()["llm_provider"] == "ollama"
        assert start.json()["llm_model"] == "qwen3:8b"
        job_id = start.json()["job_id"]

        terminal = _wait_for_terminal_status(test_client, job_id)
        assert terminal["status"] == "completed"
        assert terminal["llm_provider"] == "ollama"
        assert terminal["llm_model"] == "qwen3:8b"

        result = test_client.get(f"/api/v1/simulations/full-live/{job_id}/result")
        assert result.status_code == 200
        assert result.json()["llm_provider"] == "ollama"
        assert result.json()["llm_model"] == "qwen3:8b"


def test_full_live_result_is_unavailable_while_job_is_active(monkeypatch) -> None:
    async def resolve(provider_id, model_id, **_kwargs):
        return _resolved_full_live_provider(
            provider_id,
            model_id,
            provider=SlowMockLLMProvider(),
        )

    monkeypatch.setattr(full_live_service, "resolve_llm_provider", resolve)
    with TestClient(app) as test_client:
        start = test_client.post(
            "/api/v1/simulations/full-live",
            json=_full_live_payload(rounds=2),
        )
        job_id = start.json()["job_id"]
        result = test_client.get(f"/api/v1/simulations/full-live/{job_id}/result")
        assert result.status_code == 409
        test_client.post(f"/api/v1/simulations/full-live/{job_id}/cancel")
        terminal = _wait_for_terminal_status(test_client, job_id)
        assert terminal["status"] == "cancelled"
        cancelled_result = test_client.get(
            f"/api/v1/simulations/full-live/{job_id}/result"
        )
        assert cancelled_result.status_code == 410


def test_normal_run_rejects_full_live_mode() -> None:
    payload = _full_live_payload()
    payload.pop("full_live_confirmed")
    response = client.post("/api/v1/simulations/run", json=payload)
    assert response.status_code == 400


def test_health_endpoint() -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_simulation_preview_returns_standard_preset() -> None:
    response = client.post(
        "/api/v1/simulations/preview",
        json={
            "product": {
                "name": "AI Fitness Coach",
                "category": "Fitness Technology",
                "pitch": "Personalized workouts, nutrition guidance, and progress tracking.",
                "price": 999,
                "currency": "INR",
            },
            "population_mode": "standard",
            "dialogue_mode": "balanced",
            "rounds": 20,
            "seed": 42,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["preset"]["population_size"] == 1000
    assert body["preset"]["base_k"] == 14


def test_preview_resolves_auto_billing_and_manual_override() -> None:
    base = {
        "name": "AI Fitness Coach",
        "category": "Fitness Technology",
        "pitch": "Personalized coaching with a monthly subscription.",
        "price": 200,
        "currency": "INR",
    }
    auto_response = client.post(
        "/api/v1/simulations/preview",
        json={
            "product": {**base, "billing_cadence": "auto"},
            "population_mode": "small",
            "dialogue_mode": "economy",
            "rounds": 2,
            "seed": 42,
        },
    )
    manual_response = client.post(
        "/api/v1/simulations/preview",
        json={
            "product": {**base, "billing_cadence": "one_time"},
            "population_mode": "small",
            "dialogue_mode": "economy",
            "rounds": 2,
            "seed": 42,
        },
    )

    assert auto_response.status_code == 200
    assert manual_response.status_code == 200
    assert auto_response.json()["billing_cadence"] == "monthly"
    assert manual_response.json()["billing_cadence"] == "one_time"


def test_preview_rejects_unknown_billing_cadence() -> None:
    response = client.post(
        "/api/v1/simulations/preview",
        json={
            "product": {
                "name": "AI Fitness Coach",
                "category": "Fitness Technology",
                "pitch": "Personalized coaching.",
                "price": 200,
                "currency": "INR",
                "billing_cadence": "weekly",
            },
            "population_mode": "small",
            "dialogue_mode": "economy",
            "rounds": 2,
            "seed": 42,
        },
    )

    assert response.status_code == 422


def test_large_web_run_budget_rejects_more_than_twenty_rounds() -> None:
    response = client.post(
        "/api/v1/simulations/preview",
        json={
            "product": {
                "name": "AI Fitness Coach",
                "category": "Fitness Technology",
                "pitch": "Personalized workouts, nutrition guidance, and progress tracking.",
                "price": 999,
                "currency": "INR",
            },
            "population_mode": "large",
            "dialogue_mode": "economy",
            "rounds": 21,
            "seed": 42,
        },
    )

    assert response.status_code == 422


def test_run_simulation_with_mock_provider_upgrades_bounded_dialogue(monkeypatch) -> None:
    monkeypatch.setattr(
        "backend.app.services.simulation_service._deepseek_provider_or_none",
        lambda: MockLLMProvider(),
    )
    response = client.post(
        "/api/v1/simulations/run",
        json={
            "product": {
                "name": "AI Fitness Coach",
                "category": "Fitness Technology",
                "pitch": "Personalized workouts, nutrition guidance, and progress tracking.",
                "price": 999,
                "currency": "INR",
            },
            "population_mode": "small",
            "dialogue_mode": "balanced",
            "rounds": 1,
            "seed": 77,
        },
    )

    assert response.status_code == 200
    stats = response.json()["dialogue_stats"]
    assert stats["provider_available"] is True
    assert 0 < stats["selected_for_llm"] <= 20
    assert stats["llm_rendered"] == stats["selected_for_llm"]
    assert stats["fallback_count"] == 0


class ApiTelemetryProvider:
    async def generate_json(self, **_kwargs):
        return LLMJsonResponse(
            data={
                "conversation": [
                    {"speaker": "A", "text": "The product could be useful."},
                    {"speaker": "B", "text": "I would still compare the price."},
                ]
            },
            usage=LLMUsage(
                prompt_tokens=100,
                prompt_cache_hit_tokens=75,
                prompt_cache_miss_tokens=25,
                completion_tokens=20,
                total_tokens=120,
            ),
            latency_ms=30.0,
            model="deepseek-v4-flash",
        )


def test_run_simulation_serializes_live_dialogue_telemetry(monkeypatch) -> None:
    monkeypatch.setattr(
        "backend.app.services.simulation_service._deepseek_provider_or_none",
        lambda: ApiTelemetryProvider(),
    )
    response = client.post(
        "/api/v1/simulations/run",
        json={
            "product": {
                "name": "AI Fitness Coach",
                "category": "Fitness Technology",
                "pitch": "Personalized workouts, nutrition guidance, and progress tracking.",
                "price": 999,
                "currency": "INR",
            },
            "population_mode": "small",
            "dialogue_mode": "balanced",
            "rounds": 1,
            "seed": 78,
        },
    )

    assert response.status_code == 200
    stats = response.json()["dialogue_stats"]
    assert 0 < stats["selected_for_llm"] <= 10
    assert stats["provider_model"] == "deepseek-v4-flash"
    assert stats["prompt_tokens"] == stats["selected_for_llm"] * 100
    assert stats["prompt_cache_hit_tokens"] == stats["selected_for_llm"] * 75
    assert stats["prompt_cache_miss_tokens"] == stats["selected_for_llm"] * 25
    assert stats["completion_tokens"] == stats["selected_for_llm"] * 20
    assert stats["cache_hit_ratio"] == pytest.approx(0.75)
    assert stats["average_latency_ms"] == pytest.approx(30.0)
    assert stats["max_latency_ms"] == pytest.approx(30.0)
    assert stats["estimated_cost_usd"] > 0


def test_run_simulation_returns_timeline_and_synthetic_label() -> None:
    response = client.post(
        "/api/v1/simulations/run",
        json={
            "product": {
                "name": "AI Fitness Coach",
                "category": "Fitness Technology",
                "pitch": "Personalized workouts, nutrition guidance, and progress tracking.",
                "price": 200,
                "currency": "INR",
                "billing_cadence": "monthly",
            },
            "population_mode": "small",
            "dialogue_mode": "economy",
            "rounds": 3,
            "seed": 42,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["synthetic"] is True
    assert body["billing_cadence"] == "monthly"
    assert body["rounds"] == 3
    assert len(body["timeline"]) == 4
    assert body["summary"]["population_size"] == 250
    assert body["summary"]["conversation_count"] >= 0
    assert len(body["network"]["nodes"]) <= 80
    assert body["selected_conversations"]
    conversation = body["selected_conversations"][0]
    assert conversation["language_source"] == "background"
    assert len(conversation["transcript"]) >= 2
    assert all(message["text"] for message in conversation["transcript"])
    assert 0.0 <= conversation["importance"] <= 1.0
    assert conversation["llm_selected"] is False

    analytics = body["analytics"]
    purchase = analytics["purchase_intent_distribution"]
    assert purchase["low"] + purchase["medium"] + purchase["high"] == body["summary"]["population_size"]
    assert [point["topic"] for point in analytics["topic_pressure"]] == [
        "price",
        "usefulness",
        "quality",
        "trust",
        "novelty",
        "privacy",
    ]
    assert all(0.0 <= point["normalized_score"] <= 1.0 for point in analytics["topic_pressure"])
    assert all(
        {"support_score", "criticism_score", "net_score", "normalized_support", "normalized_criticism"}
        <= point.keys()
        for point in analytics["topic_pressure"]
    )
    assert all(
        0.0 <= point["normalized_support"] <= 1.0
        and 0.0 <= point["normalized_criticism"] <= 1.0
        for point in analytics["topic_pressure"]
    )

    stats = body["dialogue_stats"]
    assert stats["total_conversations"] == body["summary"]["conversation_count"]
    assert stats["selected_for_llm"] == 0
    assert stats["llm_rendered"] == 0
    assert stats["provider_available"] is False

    assert len(body["replay"]) == 4
    assert body["replay"][0]["round"] == 0
    assert body["replay"][0]["active_conversations"] == []
    baseline_ids = [node["id"] for node in body["replay"][0]["nodes"]]
    assert baseline_ids
    for checkpoint in body["replay"]:
        assert [node["id"] for node in checkpoint["nodes"]] == baseline_ids
