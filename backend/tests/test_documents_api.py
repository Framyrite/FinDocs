"""Integration tests for the document library HTTP API."""

from collections.abc import Iterator
from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.processing.models import ProcessingResult


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    """Start an isolated application with small upload and library limits."""
    settings = Settings(
        _env_file=None,
        data_dir=tmp_path,
        max_txt_size_mb=1,
        max_documents=2,
    )

    with TestClient(create_app(settings=settings)) as test_client:
        yield test_client


def upload(
    client: TestClient,
    filename: str,
    data: bytes,
    content_type: str = "text/plain",
):
    """Send a single multipart TXT upload."""
    return client.post(
        "/documents",
        files={"file": (filename, data, content_type)},
    )


def test_upload_get_list_and_delete(client: TestClient) -> None:
    """Exercise the complete lifecycle of one TXT document."""
    response = upload(client, "Пример.txt", "Привет!".encode())

    assert response.status_code == 202
    created = response.json()

    assert created["filename"] == "Пример.txt"
    assert created["format"] == "txt"
    assert created["status"] == "uploaded"
    assert created["created_at"].endswith("Z")

    document_id = created["id"]

    detail = client.get(f"/documents/{document_id}")
    assert detail.status_code == 200
    assert detail.json()["status"] == "ready"

    listing = client.get("/documents")
    assert listing.status_code == 200
    assert listing.json()["total"] == 1
    assert listing.json()["items"][0]["id"] == document_id

    deleted = client.delete(f"/documents/{document_id}")
    assert deleted.status_code == 204
    assert deleted.content == b""

    assert client.get(f"/documents/{document_id}").status_code == 404

    repeated = client.delete(f"/documents/{document_id}")
    assert repeated.status_code == 404
    assert repeated.json()["error"]["code"] == "document_not_found"

    assert client.get("/documents").json() == {
        "items": [],
        "total": 0,
    }


@pytest.mark.parametrize(
    ("filename", "data", "content_type", "http_status", "error_code"),
    [
        ("report.pdf", b"hello", "application/pdf", 415, "unsupported_format"),
        ("report.txt", b"hello", "application/pdf", 415, "unsupported_format"),
        ("empty.txt", b"", "text/plain", 422, "empty_file"),
        (
            "large.txt",
            b"x" * (1024 * 1024 + 1),
            "text/plain",
            413,
            "file_too_large",
        ),
    ],
)
def test_upload_rejects_invalid_files(
    client: TestClient,
    filename: str,
    data: bytes,
    content_type: str,
    http_status: int,
    error_code: str,
) -> None:
    """Reject unsupported, empty, and oversized uploads."""
    response = upload(client, filename, data, content_type)

    assert response.status_code == http_status
    assert response.json()["error"]["code"] == error_code
    assert response.json()["error"]["message"]
    assert client.get("/documents").json()["total"] == 0


@pytest.mark.parametrize(
    ("data", "expected_status", "expected_error"),
    [
        (b"\xef\xbb\xbfHello", "ready", None),
        (b"\xff", "error", "invalid_encoding"),
        (b" \t\n", "error", "empty_document"),
    ],
)
def test_background_processing_status(
    client: TestClient,
    data: bytes,
    expected_status: str,
    expected_error: str | None,
) -> None:
    """Persist successful processing or its error in document metadata."""
    response = upload(client, "document.txt", data)

    assert response.status_code == 202

    document_id = response.json()["id"]
    document = client.get(f"/documents/{document_id}").json()

    assert document["status"] == expected_status
    assert document["error_code"] == expected_error


def test_duplicate_filenames_and_search(client: TestClient) -> None:
    """Allow duplicate names and search without regard to case."""
    first = upload(client, "Отчёт.txt", b"First").json()
    second = upload(client, "Отчёт.txt", b"Second").json()

    assert first["id"] != second["id"]

    listing = client.get("/documents", params={"q": "ОТЧЁТ"}).json()

    assert listing["total"] == 2
    assert {item["id"] for item in listing["items"]} == {
        first["id"],
        second["id"],
    }

    ready = client.get(
        "/documents",
        params={"status": "ready"},
    ).json()

    assert ready["total"] == 2


def test_document_limit_returns_409(client: TestClient) -> None:
    """Reject the next upload after the configured document limit."""
    assert upload(client, "one.txt", b"one").status_code == 202
    assert upload(client, "two.txt", b"two").status_code == 202

    response = upload(client, "three.txt", b"three")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "document_limit_reached"
    assert client.get("/documents").json()["total"] == 2


def test_validation_errors_use_shared_format(client: TestClient) -> None:
    """Use the common error structure for invalid request parameters."""
    response = client.get("/documents/not-a-uuid")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert response.json()["error"]["message"]


def test_delete_releases_document_capacity(client: TestClient) -> None:
    """Allow new uploads after deleting a document from a full library."""
    first = upload(client, "first.txt", b"first")
    second = upload(client, "second.txt", b"second")

    assert first.status_code == 202
    assert second.status_code == 202

    rejected = upload(client, "third.txt", b"third")
    assert rejected.status_code == 409

    document_id = first.json()["id"]
    assert client.delete(f"/documents/{document_id}").status_code == 204

    accepted = upload(client, "third.txt", b"third")
    assert accepted.status_code == 202

    assert client.get("/documents").json()["total"] == 2


def test_upload_preserves_original_bom_bytes(client: TestClient) -> None:
    """Store the original UTF-8 BOM without modifying the uploaded bytes."""
    data = b"\xef\xbb\xbf" + "Привет!".encode()

    response = upload(client, "bom.txt", data)
    assert response.status_code == 202

    document_id = UUID(response.json()["id"])
    repository = client.app.state.document_repository

    assert repository.read_original(document_id) == data

    saved = client.get(f"/documents/{document_id}").json()
    assert saved["status"] == "ready"
    assert saved["size_bytes"] == len(data)


def test_bom_only_document_fails_during_processing(
    client: TestClient,
) -> None:
    """Accept nonempty uploaded bytes but report empty decoded content."""
    response = upload(client, "bom-only.txt", b"\xef\xbb\xbf")

    assert response.status_code == 202

    document_id = response.json()["id"]
    saved = client.get(f"/documents/{document_id}").json()

    assert saved["status"] == "error"
    assert saved["error_code"] == "empty_document"


def test_list_filters_ready_and_failed_documents(
    client: TestClient,
) -> None:
    """Combine status filtering and case-insensitive filename search."""
    assert upload(client, "Отчёт.txt", b"valid").status_code == 202
    assert upload(client, "Ошибка.txt", b"\xff").status_code == 202

    ready = client.get(
        "/documents",
        params={"status": "ready", "q": "ОТЧЁТ"},
    )
    failed = client.get(
        "/documents",
        params={"status": "error"},
    )

    assert ready.status_code == 200
    assert ready.json()["total"] == 1
    assert ready.json()["items"][0]["filename"] == "Отчёт.txt"

    assert failed.status_code == 200
    assert failed.json()["total"] == 1
    assert failed.json()["items"][0]["error_code"] == "invalid_encoding"


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/documents?status=unknown"),
        ("DELETE", "/documents/not-a-uuid"),
    ],
)
def test_invalid_parameters_use_common_error_format(
    client: TestClient,
    method: str,
    path: str,
) -> None:
    """Return the common JSON envelope for invalid parameters."""
    response = client.request(method, path)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert response.json()["error"]["message"]


def test_missing_upload_field_uses_common_error_format(
    client: TestClient,
) -> None:
    """Do not expose FastAPI's default validation response structure."""
    response = client.post("/documents")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_upload_accepts_exact_size_limit(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Accept a file exactly at the configured one-MiB boundary."""

    def fake_processor(
        data: bytes,
        document_id: UUID,
    ) -> ProcessingResult:
        return ProcessingResult(
            document_id=document_id,
            blocks=[],
            chunks=[],
        )

    monkeypatch.setattr(
        "app.documents.service.process_txt",
        fake_processor,
    )

    data = b"A" * (1024 * 1024)
    response = upload(client, "exact-limit.txt", data)

    assert response.status_code == 202
    assert response.json()["size_bytes"] == len(data)

    document_id = UUID(response.json()["id"])
    repository = client.app.state.document_repository

    assert repository.read_original(document_id) == data
