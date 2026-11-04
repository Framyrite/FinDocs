"""Smoke tests for the backend HTTP API."""

from fastapi.testclient import TestClient

from backend.app.main import app


def test_health_endpoint() -> None:
    """Require the exact HTTP status and JSON response defined by the API contract."""
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
