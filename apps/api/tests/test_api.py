from fastapi.testclient import TestClient
from stalecheck_api.main import app


def test_health_check_and_run_history():
    with TestClient(app) as client:
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json()["status"] == "ok"

        response = client.post("/v1/check", json={"text": "GPT-4o is the latest OpenAI model."})
        assert response.status_code == 200
        data = response.json()
        assert data["verdict"] == "stale"
        assert data["claims"][0]["suggested_fix"]

        runs = client.get("/v1/runs")
        assert runs.status_code == 200
        assert len(runs.json()) == 1

        detail = client.get(f"/v1/runs/{data['run_id']}")
        assert detail.status_code == 200
        assert detail.json()["input_text"].startswith("GPT-4o")

        stats = client.get("/v1/stats")
        assert stats.status_code == 200
        assert stats.json()["runs"] == 1
        assert stats.json()["stale_claims"] == 1


def test_validation_error():
    with TestClient(app) as client:
        response = client.post("/v1/check", json={"text": ""})
        assert response.status_code == 422
