from fastapi.testclient import TestClient

from app.config.settings import get_settings
from app.main import create_app


def test_configured_frontend_origin_is_allowed(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("PIPELINEPILOT_DATABASE_PATH", str(tmp_path / "cors.sqlite3"))
    monkeypatch.setenv("PIPELINEPILOT_CORS_ORIGINS", "https://app.example.com, https://preview.example.com/")
    get_settings.cache_clear()

    try:
        client = TestClient(create_app())
        response = client.options(
            "/v1/demo/status",
            headers={
                "Origin": "https://app.example.com",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "x-actor-role",
            },
        )
    finally:
        get_settings.cache_clear()

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://app.example.com"
