import pytest
from fastapi.testclient import TestClient

@pytest.fixture
def client(tmp_path, monkeypatch):
    """
    Изолированный клиент для QA-тестов.
    Подменяет хранилище на временную папку, чтобы не менять backend/data.
    """
    monkeypatch.setenv("FINDOCS_DATA_DIR", str(tmp_path / "data"))
    
    from backend.app.main import app
    with TestClient(app) as test_client:
        yield test_client

def test_document_deletion_during_processing(client, monkeypatch):
    """QA: Удаление документа во время фоновой обработки."""
    import time
    
    def slow_processor(*args, **kwargs):
        time.sleep(0.5)
        from backend.app.processing.models import ProcessingResult
        return ProcessingResult(document_id=args[1], blocks=[], chunks=[])
        
    monkeypatch.setattr("backend.app.documents.service.process_txt", slow_processor)

    files = {"file": ("slow.txt", b"Long processing test", "text/plain")}
    response = client.post("/documents", files=files)
    assert response.status_code == 202
    doc_id = response.json()["id"]

    delete_resp = client.delete(f"/documents/{doc_id}")
    assert delete_resp.status_code == 204

    time.sleep(1)

    assert client.get(f"/documents/{doc_id}").status_code == 404
    assert len(client.get("/documents").json()["items"]) == 0

def test_app_restart_recovers_uploaded_status(tmp_path, monkeypatch):
    """QA: Перезапуск приложения при зависшем статусе uploaded/processing."""
    data_dir = tmp_path / "data"
    monkeypatch.setenv("FINDOCS_DATA_DIR", str(data_dir))
    
    from backend.app.main import create_app
    app = create_app()

    with TestClient(app) as test_client:
        monkeypatch.setattr("backend.app.documents.service.DocumentService.process_document", lambda self, uid: None)
        response = test_client.post("/documents", files={"file": ("stuck.txt", b"Stuck doc", "text/plain")})
        doc_id = response.json()["id"]
        assert test_client.get(f"/documents/{doc_id}").json()["status"] == "uploaded"

    new_app = create_app()
    with TestClient(new_app) as new_client:
        recovered_doc = new_client.get(f"/documents/{doc_id}").json()
        assert recovered_doc["status"] == "error"
        assert recovered_doc["error_code"] == "processing_failed"