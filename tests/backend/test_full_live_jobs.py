import pytest

from backend.app.core.config import Settings
from backend.app.schemas.simulation import FullLiveSimulationRequest
from backend.app.services import full_live_service
from backend.app.services.full_live_jobs import FullLiveJobManager, FullLiveJobStatus
from backend.app.services.llm_provider_factory import (
    LLMProviderResolutionError,
    ResolvedLLMProvider,
)
from simulation.conversation.render_pipeline import DialoguePricing
from simulation.llm.mock import MockLLMProvider


def test_full_live_concurrency_setting_defaults_and_validates():
    settings = Settings(_env_file=None)
    assert settings.deepseek_full_live_concurrency == 4

    with pytest.raises(ValueError):
        Settings(_env_file=None, DEEPSEEK_FULL_LIVE_CONCURRENCY=0)


@pytest.mark.asyncio
async def test_job_manager_creates_unique_queued_jobs_and_retrieves_them():
    manager = FullLiveJobManager()

    first = await manager.create(
        product_name="PulseDesk",
        population_mode="small",
        rounds=2,
        seed=42,
        estimated_upper_bound_conversations=500,
        llm_provider="deepseek",
        llm_model="deepseek-v4-flash",
    )
    second = await manager.create(
        product_name="PulseDesk",
        population_mode="small",
        rounds=2,
        seed=43,
        estimated_upper_bound_conversations=500,
        llm_provider="deepseek",
        llm_model="deepseek-v4-flash",
    )

    assert first.job_id != second.job_id
    assert first.status is FullLiveJobStatus.queued
    assert first.cancel_requested is False
    assert first.llm_provider == "deepseek"
    assert first.llm_model == "deepseek-v4-flash"
    assert await manager.get(first.job_id) is first
    assert await manager.get("missing") is None


@pytest.mark.asyncio
async def test_job_manager_cancellation_marks_active_job_cancelling():
    manager = FullLiveJobManager()
    job = await manager.create(
        product_name="PulseDesk",
        population_mode="standard",
        rounds=10,
        seed=42,
        estimated_upper_bound_conversations=10000,
        llm_provider="ollama",
        llm_model="qwen3:8b",
    )
    await manager.update_status(job.job_id, FullLiveJobStatus.rendering)

    updated = await manager.request_cancel(job.job_id)

    assert updated is not None
    assert updated.cancel_requested is True
    assert updated.status is FullLiveJobStatus.cancelling


@pytest.mark.asyncio
async def test_job_manager_failure_message_is_sanitized():
    manager = FullLiveJobManager()
    job = await manager.create(
        product_name="PulseDesk",
        population_mode="small",
        rounds=2,
        seed=42,
        estimated_upper_bound_conversations=500,
        llm_provider="deepseek",
        llm_model="deepseek-v4-flash",
    )

    await manager.fail(job.job_id, RuntimeError("Bearer secret-test-value upstream exploded"))
    failed = await manager.get(job.job_id)

    assert failed is not None
    assert failed.status is FullLiveJobStatus.failed
    assert failed.error_message == "Full Live job failed during backend processing."
    assert "secret" not in failed.error_message.lower()


def _request(
    *,
    rounds: int = 1,
    seed: int = 42,
    provider: str = "deepseek",
    model: str = "deepseek-v4-flash",
    advanced: dict | None = None,
) -> FullLiveSimulationRequest:
    payload = {
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
            "seed": seed,
            "full_live_confirmed": True,
            "llm_provider": provider,
            "llm_model": model,
        }
    if advanced is not None:
        payload["advanced_config"] = advanced
    return FullLiveSimulationRequest.model_validate(payload)


def _resolved(provider_id: str = "deepseek", model_id: str = "deepseek-v4-flash") -> ResolvedLLMProvider:
    return ResolvedLLMProvider(
        provider_id=provider_id,
        model_id=model_id,
        label="DeepSeek" if provider_id == "deepseek" else "Ollama Local",
        kind="cloud" if provider_id == "deepseek" else "local",
        provider=MockLLMProvider(),
        concurrency=2,
        pricing=DialoguePricing(),
        cache_telemetry_available=provider_id == "deepseek",
    )


def test_full_live_upper_bound_uses_effective_advanced_configuration():
    request = _request(
        rounds=3,
        advanced={
            "population_size": 40,
            "base_k": 6,
            "max_conversations_per_round": 1,
            "initiator_rate": 0.20,
            "weak_tie_rate": 0.05,
            "simulated_minutes_per_round": 2,
        },
    )

    assert full_live_service.estimate_upper_bound_conversations(request) == 60


@pytest.mark.asyncio
async def test_full_live_service_uses_advanced_configuration_for_job_and_result(monkeypatch):
    manager = FullLiveJobManager()

    async def resolve(provider_id, model_id, **_kwargs):
        return _resolved(provider_id, model_id)

    monkeypatch.setattr(full_live_service, "resolve_llm_provider", resolve)
    request = _request(
        rounds=3,
        advanced={
            "population_size": 40,
            "base_k": 6,
            "max_conversations_per_round": 1,
            "initiator_rate": 0.20,
            "weak_tie_rate": 0.05,
            "simulated_minutes_per_round": 2,
        },
    )

    job = await full_live_service.start_full_live_job(request, manager=manager)
    assert job.estimated_upper_bound_conversations == 60
    finished = await manager.wait(job.job_id)

    assert finished is not None
    assert finished.status is FullLiveJobStatus.completed
    assert finished.result is not None
    assert finished.result.advanced_config_enabled is True
    assert finished.result.summary.population_size == 40
    assert finished.result.summary.base_k == 6
    assert finished.result.preset.max_conversations_per_round == 1
    assert finished.result.preset.simulated_minutes_per_round == 2
    assert finished.result.dialogue_stats.selected_for_llm == finished.result.summary.conversation_count


@pytest.mark.asyncio
async def test_full_live_service_runs_simulation_then_renders_every_conversation(monkeypatch):
    manager = FullLiveJobManager()

    async def resolve(provider_id, model_id, **_kwargs):
        return _resolved(provider_id, model_id)

    monkeypatch.setattr(full_live_service, "resolve_llm_provider", resolve)

    job = await full_live_service.start_full_live_job(_request(), manager=manager)
    finished = await manager.wait(job.job_id)

    assert finished is not None
    assert finished.status is FullLiveJobStatus.completed
    assert finished.total_conversations is not None
    assert finished.total_conversations > 0
    assert finished.processed_conversations == finished.total_conversations
    assert finished.successful_renders == finished.total_conversations
    assert finished.result is not None
    assert finished.result.dialogue_mode.value == "full_live"
    assert finished.result.llm_provider == "deepseek"
    assert finished.result.llm_model == "deepseek-v4-flash"
    assert finished.llm_provider == "deepseek"
    assert finished.llm_model == "deepseek-v4-flash"
    assert finished.result.summary.conversation_count == finished.total_conversations
    assert finished.result.dialogue_stats.selected_for_llm == finished.total_conversations


@pytest.mark.asyncio
async def test_full_live_service_rejects_creation_without_live_provider(monkeypatch):
    manager = FullLiveJobManager()

    async def reject(*_args, **_kwargs):
        raise LLMProviderResolutionError("provider unavailable")

    monkeypatch.setattr(full_live_service, "resolve_llm_provider", reject)

    with pytest.raises(full_live_service.FullLiveConfigurationError, match="provider unavailable"):
        await full_live_service.start_full_live_job(_request(), manager=manager)


@pytest.mark.asyncio
async def test_full_live_service_accepts_ollama_without_deepseek_configuration(monkeypatch):
    manager = FullLiveJobManager()

    async def resolve(provider_id, model_id, **_kwargs):
        assert provider_id == "ollama"
        assert model_id == "qwen3:8b"
        return _resolved(provider_id, model_id)

    monkeypatch.setattr(full_live_service, "resolve_llm_provider", resolve)

    job = await full_live_service.start_full_live_job(
        _request(provider="ollama", model="qwen3:8b"),
        manager=manager,
    )
    finished = await manager.wait(job.job_id)

    assert finished is not None
    assert finished.status is FullLiveJobStatus.completed
    assert finished.llm_provider == "ollama"
    assert finished.llm_model == "qwen3:8b"
    assert finished.result is not None
    assert finished.result.llm_provider == "ollama"
    assert finished.result.llm_model == "qwen3:8b"


@pytest.mark.asyncio
async def test_full_live_service_sanitizes_orchestration_failure(monkeypatch):
    manager = FullLiveJobManager()

    async def resolve(provider_id, model_id, **_kwargs):
        return _resolved(provider_id, model_id)

    monkeypatch.setattr(full_live_service, "resolve_llm_provider", resolve)

    def explode(_request):
        raise RuntimeError("sensitive internal backend detail")

    monkeypatch.setattr(full_live_service, "_run_core_simulation", explode)

    job = await full_live_service.start_full_live_job(_request(seed=99), manager=manager)
    failed = await manager.wait(job.job_id)

    assert failed is not None
    assert failed.status is FullLiveJobStatus.failed
    assert failed.error_message == "Full Live job failed during backend processing."
    assert failed.result is None
