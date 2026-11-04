"""Smoke tests for the backend HTTP API."""

from backend.app.main import app
from fastapi.testclient import TestClient


def test_health_endpoint():
    """Require the exact HTTP status and JSON response defined by the API contract."""
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
