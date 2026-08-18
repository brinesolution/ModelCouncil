import json

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services import full_live_service, run_audit_service
from backend.app.services.full_live_jobs import FullLiveJobManager, FullLiveJobStatus
from backend.app.services.llm_provider_factory import ResolvedLLMProvider
from simulation.conversation.render_pipeline import DialoguePricing
from simulation.llm.mock import MockLLMProvider
from simulation.audit.logger import MemoryRunAuditLogger


client = TestClient(app)


@pytest.fixture(autouse=True)
def disable_normal_live_provider(monkeypatch):
    monkeypatch.setattr(
        "backend.app.services.simulation_service._deepseek_provider_or_none",
        lambda: None,
    )


def _payload(
    dialogue_mode: str = "economy",
    *,
    rounds: int = 1,
    advanced: dict | None = None,
) -> dict:
    payload = {
        "product": {
            "name": "AI Fitness Coach",
            "category": "Fitness Technology",
            "pitch": "Personalized workouts and progress tracking for a monthly subscription.",
            "price": 200,
            "currency": "INR",
            "billing_cadence": "monthly",
        },
        "population_mode": "small",
        "dialogue_mode": dialogue_mode,
        "rounds": rounds,
        "seed": 42,
    }
    if advanced is not None:
        payload["advanced_config"] = advanced
    return payload


def _events(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_normal_run_creates_jsonl_and_markdown_terminal_trace(tmp_path, monkeypatch):
    monkeypatch.setattr(run_audit_service, "AUDIT_ROOT", tmp_path)

    response = client.post("/api/v1/simulations/run", json=_payload())

    assert response.status_code == 200
    jsonl_files = list(tmp_path.glob("*.jsonl"))
    md_files = list(tmp_path.glob("*.md"))
    assert len(jsonl_files) == 1
    assert len(md_files) == 1
    events = _events(jsonl_files[0])
    assert events[0]["event"] == "run.started"
    assert events[-1]["event"] == "run.summary_written"
    assert any(event["event"] == "run.completed" for event in events)
    configuration = next(event for event in events if event["event"] == "run.configuration")
    assert configuration["payload"]["advanced_config_enabled"] is False
    assert configuration["payload"]["effective_preset"] == {
        "name": "small",
        "population_size": 250,
        "base_k": 10,
        "max_conversations_per_round": 2,
        "initiator_rate": 0.2,
        "weak_tie_rate": 0.05,
        "simulated_minutes_per_round": 5,
    }
    assert configuration["payload"]["workload_upper_bound"] == 250
    assert any(event["event"] == "population.agent_generated" for event in events)
    assert any(event["event"] == "product.semantic_profile" for event in events)
    assert any(event["event"] == "round.started" for event in events)
    assert any(event["event"] == "conversation.semantic_completed" for event in events)
    assert any(event["event"] == "state.committed" for event in events)
    raw = jsonl_files[0].read_text(encoding="utf-8")
    assert "AI Fitness Coach" in raw
    assert "DEEPSEEK_API_KEY" not in raw
    summary = md_files[0].read_text(encoding="utf-8")
    assert "# ModelCouncil Run Audit" in summary
    assert "completed" in summary
    assert jsonl_files[0].name in summary


def test_advanced_run_audit_records_exact_effective_configuration(tmp_path, monkeypatch):
    monkeypatch.setattr(run_audit_service, "AUDIT_ROOT", tmp_path)
    payload = _payload(
        rounds=2,
        advanced={
            "population_size": 20,
            "base_k": 4,
            "max_conversations_per_round": 1,
            "initiator_rate": 0.15,
            "weak_tie_rate": 0.08,
            "simulated_minutes_per_round": 2,
        },
    )

    response = client.post("/api/v1/simulations/run", json=payload)

    assert response.status_code == 200
    jsonl_path = next(tmp_path.glob("*.jsonl"))
    configuration = next(
        event for event in _events(jsonl_path) if event["event"] == "run.configuration"
    )
    assert configuration["payload"]["advanced_config_enabled"] is True
    assert configuration["payload"]["population_mode"] == "small"
    assert configuration["payload"]["rounds"] == 2
    assert configuration["payload"]["seed"] == 42
    assert configuration["payload"]["effective_preset"] == {
        "name": "small-advanced",
        "population_size": 20,
        "base_k": 4,
        "max_conversations_per_round": 1,
        "initiator_rate": 0.15,
        "weak_tie_rate": 0.08,
        "simulated_minutes_per_round": 2,
    }
    assert configuration["payload"]["workload_upper_bound"] == 20


def test_run_fails_clearly_when_audit_file_cannot_be_created(tmp_path, monkeypatch):
    blocked = tmp_path / "blocked"
    blocked.write_text("not-a-directory", encoding="utf-8")
    monkeypatch.setattr(run_audit_service, "AUDIT_ROOT", blocked)

    with pytest.raises(Exception):
        run_audit_service.create_run_audit_from_payload(_payload(), run_kind="normal")


def _full_live_request():
    payload = _payload("full_live")
    payload.update(
        {
            "full_live_confirmed": True,
            "llm_provider": "deepseek",
            "llm_model": "deepseek-v4-flash",
        }
    )
    from backend.app.schemas.simulation import FullLiveSimulationRequest

    return FullLiveSimulationRequest.model_validate(payload)


@pytest.mark.asyncio
async def test_full_live_manager_emits_cancel_requested_to_attached_audit_sink():
    manager = FullLiveJobManager()
    audit = MemoryRunAuditLogger(run_id="cancel-manager")
    job = await manager.create(
        product_name="Coach",
        population_mode="small",
        rounds=2,
        seed=42,
        estimated_upper_bound_conversations=500,
        llm_provider="deepseek",
        llm_model="model-x",
        audit=audit,
    )
    await manager.update_status(job.job_id, FullLiveJobStatus.rendering)

    updated = await manager.request_cancel(job.job_id)

    assert updated is not None
    assert updated.cancel_requested is True
    assert any(event["event"] == "run.cancel_requested" for event in audit.events)


@pytest.mark.asyncio
async def test_full_live_completed_job_retains_internal_audit_paths(tmp_path, monkeypatch):
    monkeypatch.setattr(run_audit_service, "AUDIT_ROOT", tmp_path)
    manager = FullLiveJobManager()

    async def resolve(provider_id, model_id, **_kwargs):
        return ResolvedLLMProvider(
            provider_id=provider_id,
            model_id=model_id,
            label="DeepSeek",
            kind="cloud",
            provider=MockLLMProvider(),
            concurrency=2,
            pricing=DialoguePricing(),
            cache_telemetry_available=True,
        )

    monkeypatch.setattr(full_live_service, "resolve_llm_provider", resolve)

    job = await full_live_service.start_full_live_job(_full_live_request(), manager=manager)
    finished = await manager.wait(job.job_id)

    assert finished is not None
    assert finished.status is FullLiveJobStatus.completed
    assert finished.audit_jsonl_path is not None
    assert finished.audit_summary_path is not None
    events = _events(__import__("pathlib").Path(finished.audit_jsonl_path))
    assert any(event["event"] == "run.completed" for event in events)
    assert any(event["event"] == "language.render.request" for event in events)
    assert any(event["event"] == "language.render.completed" for event in events)
    assert events[-1]["event"] == "run.summary_written"
