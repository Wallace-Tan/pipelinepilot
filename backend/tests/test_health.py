from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint_returns_fixture_mode() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "app_name": "PipelinePilot",
        "status": "ok",
        "mode": "fixture",
    }
