from fastapi.testclient import TestClient

from fpw_api import app, create_app


def test_health_endpoint() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "functional-proteomics-api",
    }


def test_app_startup_smoke() -> None:
    candidate = create_app()

    with TestClient(candidate) as client:
        response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "service": "functional-proteomics-api",
        "checks": {"app": "ok"},
    }
