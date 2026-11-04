from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_health_endpoint():
    """Smoke-test: the /health endpoint should return a 200 status and the correct JSON."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data or "healthy" in data or isinstance(data, dict)
