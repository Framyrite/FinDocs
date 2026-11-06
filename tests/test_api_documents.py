import pytest
from fastapi.testclient import TestClient

@pytest.fixture
def client(tmp_path, monkeypatch):
    """
    Изолированный клиент для QA-тестов.
    Подменяет хранилище на временную папку.
    """
    monkeypatch.setenv("FINDOCS_DATA_DIR", str(tmp_path / "data"))
    
    # Строго импортируем как app.main, чтобы избежать дублирования путей в памяти
    from app.main import app 
    with TestClient(app) as test_client:
        yield test_client

def test_document_deletion_in_uploaded_state(client, monkeypatch):
    """
    QA: Удаление документа до завершения обработки (в статусе uploaded).
    Так как TestClient синхронно ждет фоновые задачи, мы полностью глушим обработчик.
    """
    # Патчим по правильному пути, как это видит само приложение
    monkeypatch.setattr("app.documents.service.DocumentService.process_document", lambda self, uid: None)

    files = {"file": ("stuck_delete.txt", b"Test", "text/plain")}
    response = client.post("/documents", files=files)
    assert response.status_code == 202
    doc_id = response.json()["id"]

    # Убеждаемся, что статус завис на uploaded, так как заглушка сработала
    assert client.get(f"/documents/{doc_id}").json()["status"] == "uploaded"

    # Удаляем документ во время "зависания"
    delete_resp = client.delete(f"/documents/{doc_id}")
    assert delete_resp.status_code == 204

    # Проверяем, что удаление успешно
    assert client.get(f"/documents/{doc_id}").status_code == 404
    assert len(client.get("/documents").json()["items"]) == 0

def test_app_restart_recovers_uploaded_status(tmp_path, monkeypatch):
    """QA: Перезапуск приложения при зависшем статусе uploaded/processing."""
    data_dir = tmp_path / "data"
    monkeypatch.setenv("FINDOCS_DATA_DIR", str(data_dir))
    
    from app.main import create_app
    app = create_app()

    with TestClient(app) as test_client:
        monkeypatch.setattr("app.documents.service.DocumentService.process_document", lambda self, uid: None)
        
        response = test_client.post("/documents", files={"file": ("stuck.txt", b"Stuck doc", "text/plain")})
        doc_id = response.json()["id"]
        
        assert test_client.get(f"/documents/{doc_id}").json()["status"] == "uploaded"

    # Имитируем жесткий рестарт приложения
    new_app = create_app()
    with TestClient(new_app) as new_client:
        recovered_doc = new_client.get(f"/documents/{doc_id}").json()
        assert recovered_doc["status"] == "error"
        assert recovered_doc["error_code"] == "processing_failed"