from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


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
