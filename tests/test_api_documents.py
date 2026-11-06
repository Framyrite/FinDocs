import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    """
    Isolated client for QA tests.
    """
    monkeypatch.setenv("FINDOCS_DATA_DIR", str(tmp_path / "data"))

    from app.main import app 
    with TestClient(app) as test_client:
        yield test_client


def test_document_deletion_in_uploaded_state(client, monkeypatch):
    """
    QA: Deleting a document before processing is complete (while in the 'uploaded' status).
    """
    monkeypatch.setattr("app.documents.service.DocumentService.process_document", lambda self, uid: None)

    files = {"file": ("stuck_delete.txt", b"Test", "text/plain")}
    response = client.post("/documents", files=files)
    assert response.status_code == 202
    doc_id = response.json()["id"]

    assert client.get(f"/documents/{doc_id}").json()["status"] == "uploaded"

    delete_resp = client.delete(f"/documents/{doc_id}")
    assert delete_resp.status_code == 204

    assert client.get(f"/documents/{doc_id}").status_code == 404
    assert len(client.get("/documents").json()["items"]) == 0


def test_app_restart_recovers_uploaded_status(tmp_path, monkeypatch):
    """QA: Restarting the application when it gets stuck in an "uploaded/processing" status."""
    data_dir = tmp_path / "data"
    monkeypatch.setenv("FINDOCS_DATA_DIR", str(data_dir))

    from app.main import create_app
    app = create_app()

    with TestClient(app) as test_client:
        monkeypatch.setattr("app.documents.service.DocumentService.process_document", lambda self, uid: None)

        response = test_client.post("/documents", files={"file": ("stuck.txt", b"Stuck doc", "text/plain")})
        doc_id = response.json()["id"]

        assert test_client.get(f"/documents/{doc_id}").json()["status"] == "uploaded"

    new_app = create_app()
    with TestClient(new_app) as new_client:
        recovered_doc = new_client.get(f"/documents/{doc_id}").json()
        assert recovered_doc["status"] == "error"
        assert recovered_doc["error_code"] == "processing_failed"