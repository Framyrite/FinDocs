"""Tests for document processing and lifecycle management."""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from threading import Event
from uuid import UUID, uuid4

import pytest

from app.documents.models import Document, DocumentStatus
from app.documents.repository import LocalFileDocumentRepository
from app.documents.service import DocumentService
from app.processing.models import ProcessingResult


def make_document(data: bytes) -> Document:
    """Create document metadata for service tests."""
    return Document(
        id=uuid4(),
        filename="example.txt",
        size_bytes=len(data),
        created_at=datetime.now(UTC),
    )


def test_service_processes_document_successfully(tmp_path: Path) -> None:
    """Process TXT and persist the ready status and result."""
    repository = LocalFileDocumentRepository(tmp_path)
    service = DocumentService(repository)

    data = "Привет, FinDocs! 👋".encode("utf-8")
    document = make_document(data)
    repository.create(document, data)

    service.process_document(document.id)

    saved = repository.get(document.id)
    result = repository.get_result(document.id)

    assert saved is not None
    assert saved.status == DocumentStatus.READY
    assert saved.error_code is None
    assert saved.error_message is None

    assert result is not None
    assert result.document_id == document.id
    assert result.blocks[0].content == "Привет, FinDocs! 👋"
    assert result.chunks


@pytest.mark.parametrize(
    ("data", "expected_code"),
    [
        (b"\xff", "invalid_encoding"),
        (b" \t\n", "empty_document"),
    ],
)
def test_service_records_processing_errors(
    tmp_path: Path,
    data: bytes,
    expected_code: str,
) -> None:
    """Save expected TXT errors in document metadata."""
    repository = LocalFileDocumentRepository(tmp_path)
    service = DocumentService(repository)

    document = make_document(data)
    repository.create(document, data)

    service.process_document(document.id)

    saved = repository.get(document.id)

    assert saved is not None
    assert saved.status == DocumentStatus.ERROR
    assert saved.error_code == expected_code
    assert saved.error_message
    assert repository.get_result(document.id) is None


def test_service_records_unexpected_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Record unexpected processing failures without crashing the task."""
    repository = LocalFileDocumentRepository(tmp_path)
    service = DocumentService(repository)

    document = make_document(b"hello")
    repository.create(document, b"hello")

    def broken_processor(
        data: bytes,
        document_id: UUID,
    ) -> ProcessingResult:
        raise RuntimeError("Tokenizer failed")

    monkeypatch.setattr(
        "app.documents.service.process_txt",
        broken_processor,
    )

    service.process_document(document.id)

    saved = repository.get(document.id)

    assert saved is not None
    assert saved.status == DocumentStatus.ERROR
    assert saved.error_code == "processing_failed"
    assert saved.error_message == "Document processing failed"


def test_service_ignores_deleted_document(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Do not start processing a document deleted before the task begins."""
    repository = LocalFileDocumentRepository(tmp_path)
    service = DocumentService(repository)

    document = make_document(b"hello")
    repository.create(document, b"hello")
    assert repository.delete(document.id) is True

    def unexpected_processor(
        data: bytes,
        document_id: UUID,
    ) -> ProcessingResult:
        raise AssertionError("Deleted document must not be processed")

    monkeypatch.setattr(
        "app.documents.service.process_txt",
        unexpected_processor,
    )

    service.process_document(document.id)

    assert repository.get(document.id) is None
    assert repository.get_result(document.id) is None


def test_service_does_not_restore_document_deleted_during_processing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Discard processing results when the document is deleted mid-task."""
    repository = LocalFileDocumentRepository(tmp_path)
    service = DocumentService(repository)

    document = make_document(b"hello")
    repository.create(document, b"hello")

    def delete_during_processing(
        data: bytes,
        document_id: UUID,
    ) -> ProcessingResult:
        assert data == b"hello"
        assert repository.get(document_id).status == DocumentStatus.PROCESSING
        assert repository.delete(document_id) is True

        return ProcessingResult(
            document_id=document_id,
            blocks=[],
            chunks=[],
        )

    monkeypatch.setattr(
        "app.documents.service.process_txt",
        delete_during_processing,
    )

    service.process_document(document.id)

    assert repository.get(document.id) is None
    assert repository.get_result(document.id) is None
    assert repository.list() == []


def test_delete_while_processing_in_another_thread(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Prevent a running background task from restoring a deleted document."""
    repository = LocalFileDocumentRepository(tmp_path)
    service = DocumentService(repository)

    document = make_document(b"hello")
    repository.create(document, b"hello")

    processing_started = Event()
    allow_processing_to_finish = Event()

    def slow_processor(
        data: bytes,
        document_id: UUID,
    ) -> ProcessingResult:
        assert data == b"hello"
        processing_started.set()

        if not allow_processing_to_finish.wait(timeout=5):
            raise TimeoutError("Processing was not released in time")

        return ProcessingResult(
            document_id=document_id,
            blocks=[],
            chunks=[],
        )

    monkeypatch.setattr(
        "app.documents.service.process_txt",
        slow_processor,
    )

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(service.process_document, document.id)

        try:
            assert processing_started.wait(timeout=5)

            saved = repository.get(document.id)
            assert saved is not None
            assert saved.status == DocumentStatus.PROCESSING

            assert repository.delete(document.id) is True
        finally:
            allow_processing_to_finish.set()

        future.result(timeout=5)

    assert repository.get(document.id) is None
    assert repository.get_result(document.id) is None
    assert repository.list() == []

    document_dir = tmp_path / "documents" / str(document.id)
    assert not document_dir.exists()
