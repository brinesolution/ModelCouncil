import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend.app.main import app
from backend.app.schemas.simulation import SimulationPreviewRequest
from backend.app.services import simulation_service
from backend.app.services.simulation_config_service import (
    MAX_SIMULATION_WORKLOAD,
    estimate_conversation_upper_bound,
    resolve_effective_preset,
)


client = TestClient(app)


def _payload(*, population_mode: str = "standard", rounds: int = 20, advanced: dict | None = None) -> dict:
    payload = {
        "product": {
            "name": "Debug Product",
            "category": "Software",
            "pitch": "A deterministic product used to test advanced simulation controls.",
            "price": 500,
            "currency": "INR",
            "billing_cadence": "monthly",
        },
        "population_mode": population_mode,
        "dialogue_mode": "economy",
        "rounds": rounds,
        "seed": 42,
    }
    if advanced is not None:
        payload["advanced_config"] = advanced
    return payload


def _advanced(**overrides) -> dict:
    values = {
        "population_size": 20,
        "base_k": 4,
        "max_conversations_per_round": 1,
        "initiator_rate": 0.20,
        "weak_tie_rate": 0.05,
        "simulated_minutes_per_round": 2,
    }
    values.update(overrides)
    return values


def test_omitted_advanced_config_uses_registered_standard_preset() -> None:
    request = SimulationPreviewRequest.model_validate(_payload())

    preset = resolve_effective_preset(request)

    assert request.advanced_config is None
    assert preset.name == "standard"
    assert preset.population_size == 1000
    assert preset.base_k == 14
    assert preset.max_conversations_per_round == 2
    assert preset.initiator_rate == pytest.approx(0.20)
    assert preset.weak_tie_rate == pytest.approx(0.05)
    assert preset.simulated_minutes_per_round == 5


def test_valid_advanced_config_resolves_exact_custom_values() -> None:
    request = SimulationPreviewRequest.model_validate(
        _payload(
            rounds=3,
            advanced=_advanced(
                population_size=24,
                base_k=6,
                max_conversations_per_round=2,
                initiator_rate=0.15,
                weak_tie_rate=0.08,
                simulated_minutes_per_round=3,
            ),
        )
    )

    preset = resolve_effective_preset(request)

    assert request.advanced_config is not None
    assert preset.name == "standard-advanced"
    assert preset.population_size == 24
    assert preset.base_k == 6
    assert preset.max_conversations_per_round == 2
    assert preset.initiator_rate == pytest.approx(0.15)
    assert preset.weak_tie_rate == pytest.approx(0.08)
    assert preset.simulated_minutes_per_round == 3
    assert estimate_conversation_upper_bound(request) == 72


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("population_size", 1),
        ("population_size", 5001),
        ("base_k", 0),
        ("base_k", 129),
        ("max_conversations_per_round", 0),
        ("max_conversations_per_round", 9),
        ("initiator_rate", -0.01),
        ("initiator_rate", 1.01),
        ("weak_tie_rate", -0.01),
        ("weak_tie_rate", 1.01),
        ("simulated_minutes_per_round", 0),
        ("simulated_minutes_per_round", 1441),
    ],
)
def test_advanced_field_bounds_are_rejected(field: str, value: object) -> None:
    with pytest.raises(ValidationError):
        SimulationPreviewRequest.model_validate(
            _payload(rounds=2, advanced=_advanced(**{field: value}))
        )


def test_advanced_k_must_be_less_than_population() -> None:
    with pytest.raises(ValidationError, match="base_k must be less than population_size"):
        SimulationPreviewRequest.model_validate(
            _payload(advanced=_advanced(population_size=20, base_k=20))
        )


def test_preset_round_limit_remains_when_advanced_is_absent() -> None:
    with pytest.raises(ValidationError, match="standard population is limited to 50"):
        SimulationPreviewRequest.model_validate(_payload(rounds=51))


def test_advanced_can_use_one_hundred_rounds_when_workload_is_safe() -> None:
    request = SimulationPreviewRequest.model_validate(
        _payload(rounds=100, advanced=_advanced(population_size=20, base_k=4))
    )

    assert request.rounds == 100
    assert estimate_conversation_upper_bound(request) == 1000


def test_rounds_above_global_hard_maximum_are_rejected() -> None:
    with pytest.raises(ValidationError):
        SimulationPreviewRequest.model_validate(
            _payload(rounds=101, advanced=_advanced())
        )


def test_workload_at_exact_limit_is_allowed() -> None:
    request = SimulationPreviewRequest.model_validate(
        _payload(
            population_mode="large",
            rounds=20,
            advanced=_advanced(
                population_size=5000,
                base_k=18,
                max_conversations_per_round=2,
            ),
        )
    )

    assert estimate_conversation_upper_bound(request) == MAX_SIMULATION_WORKLOAD == 100_000


def test_workload_above_limit_is_rejected_with_computed_bound() -> None:
    with pytest.raises(ValidationError, match="105000.*100000"):
        SimulationPreviewRequest.model_validate(
            _payload(
                population_mode="large",
                rounds=14,
                advanced=_advanced(
                    population_size=5000,
                    base_k=18,
                    max_conversations_per_round=3,
                ),
            )
        )


def test_preview_returns_effective_advanced_values() -> None:
    response = client.post(
        "/api/v1/simulations/preview",
        json=_payload(
            rounds=3,
            advanced=_advanced(
                population_size=24,
                base_k=6,
                max_conversations_per_round=2,
                initiator_rate=0.15,
                weak_tie_rate=0.08,
                simulated_minutes_per_round=3,
            ),
        ),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["advanced_config_enabled"] is True
    assert body["preset"] == {
        "population_size": 24,
        "base_k": 6,
        "max_conversations_per_round": 2,
        "initiator_rate": 0.15,
        "weak_tie_rate": 0.08,
        "simulated_minutes_per_round": 3,
    }


def test_preview_without_advanced_reports_registered_preset_mode() -> None:
    response = client.post("/api/v1/simulations/preview", json=_payload())

    assert response.status_code == 200
    body = response.json()
    assert body["advanced_config_enabled"] is False
    assert body["preset"]["population_size"] == 1000
    assert body["preset"]["base_k"] == 14


def test_ordinary_run_uses_advanced_values_end_to_end(monkeypatch) -> None:
    monkeypatch.setattr(simulation_service, "_deepseek_provider_or_none", lambda: None)
    response = client.post(
        "/api/v1/simulations/run",
        json=_payload(
            population_mode="small",
            rounds=2,
            advanced=_advanced(
                population_size=20,
                base_k=4,
                max_conversations_per_round=1,
                initiator_rate=0.25,
                weak_tie_rate=0.10,
                simulated_minutes_per_round=2,
            ),
        ),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["advanced_config_enabled"] is True
    assert body["population_mode"] == "small"
    assert body["summary"]["population_size"] == 20
    assert body["summary"]["base_k"] == 4
    assert body["preset"] == {
        "population_size": 20,
        "base_k": 4,
        "max_conversations_per_round": 1,
        "initiator_rate": 0.25,
        "weak_tie_rate": 0.10,
        "simulated_minutes_per_round": 2,
    }
    assert len(body["timeline"]) == 3
    assert [point["round"] for point in body["replay"]] == [0, 1, 2]
    assert body["replay"][1]["simulated_minutes"] == 2


def test_equivalent_preset_and_advanced_values_produce_same_numerical_result() -> None:
    preset_request = SimulationPreviewRequest.model_validate(
        _payload(population_mode="small", rounds=2)
    )
    advanced_request = SimulationPreviewRequest.model_validate(
        _payload(
            population_mode="small",
            rounds=2,
            advanced=_advanced(
                population_size=250,
                base_k=10,
                max_conversations_per_round=2,
                initiator_rate=0.20,
                weak_tie_rate=0.05,
                simulated_minutes_per_round=5,
            ),
        )
    )

    preset_run = simulation_service._run_core_simulation(preset_request)[3]
    advanced_run = simulation_service._run_core_simulation(advanced_request)[3]

    assert preset_run.timeline == advanced_run.timeline
    assert preset_run.conversation_count == advanced_run.conversation_count
    assert [agent.state for agent in preset_run.population] == [
        agent.state for agent in advanced_run.population
    ]
