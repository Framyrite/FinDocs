"""Tests for local document storage."""

import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Barrier
from uuid import uuid4

import pytest

from app.documents.models import Document, DocumentStatus
from app.documents.repository import (
    DocumentLimitExceededError,
    LocalFileDocumentRepository,
)
from app.processing.models import Chunk, DocumentBlock, ProcessingResult


def make_document(
    data: bytes,
    size_bytes: int | None = None,
) -> Document:
    """Create document metadata for repository tests."""
    return Document(
        id=uuid4(),
        filename="Пример.txt",
        size_bytes=len(data) if size_bytes is None else size_bytes,
        created_at=datetime.now(UTC),
    )


def test_create_saves_original_and_metadata(tmp_path: Path) -> None:
    """Save original bytes unchanged alongside valid JSON metadata."""
    repository = LocalFileDocumentRepository(tmp_path)
    data = "Привет, FinDocs! 👋".encode("utf-8")
    document = make_document(data)

    repository.create(document, data)

    document_dir = tmp_path / "documents" / str(document.id)
    original_path = document_dir / "original.bin"
    metadata_path = document_dir / "meta.json"

    assert original_path.read_bytes() == data
    assert metadata_path.is_file()

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    assert metadata["id"] == str(document.id)
    assert metadata["filename"] == "Пример.txt"
    assert metadata["size_bytes"] == len(data)
    assert metadata["created_at"] == document.created_at.isoformat()
    assert metadata["format"] == "txt"
    assert metadata["status"] == "uploaded"
    assert metadata["error_code"] is None
    assert metadata["error_message"] is None


def test_create_rejects_duplicate_id(tmp_path: Path) -> None:
    """Reject duplicate UUIDs without overwriting the existing document."""
    repository = LocalFileDocumentRepository(tmp_path)
    document = make_document(b"first")

    repository.create(document, b"first")

    with pytest.raises(FileExistsError):
        repository.create(document, b"later")

    original_path = tmp_path / "documents" / str(document.id) / "original.bin"

    assert original_path.read_bytes() == b"first"


def test_create_rejects_incorrect_size(tmp_path: Path) -> None:
    """Reject inconsistent metadata without creating a document directory."""
    repository = LocalFileDocumentRepository(tmp_path)
    document = make_document(b"hello", size_bytes=100)

    with pytest.raises(ValueError, match="size"):
        repository.create(document, b"hello")

    document_dir = tmp_path / "documents" / str(document.id)

    assert not document_dir.exists()


def test_get_restores_document_after_repository_restart(tmp_path: Path) -> None:
    """Restore persisted metadata using a new repository instance."""
    repository = LocalFileDocumentRepository(tmp_path)
    data = "Привет, FinDocs!".encode("utf-8")
    document = make_document(data)

    repository.create(document, data)

    restarted_repository = LocalFileDocumentRepository(tmp_path)

    assert restarted_repository.get(document.id) == document
    assert restarted_repository.read_original(document.id) == data


def test_get_missing_document_returns_none(tmp_path: Path) -> None:
    """Return None when requested document files do not exist."""
    repository = LocalFileDocumentRepository(tmp_path)
    missing_id = uuid4()

    assert repository.get(missing_id) is None
    assert repository.read_original(missing_id) is None


def test_list_empty_repository(tmp_path: Path) -> None:
    """Return an empty list when no documents are stored."""
    repository = LocalFileDocumentRepository(tmp_path)

    assert repository.list() == []


def test_list_filters_and_sorts_documents(tmp_path: Path) -> None:
    """Filter by status and filename, returning newest documents first."""
    repository = LocalFileDocumentRepository(tmp_path)

    first = replace(
        make_document(b"first"),
        filename="Отчёт 2025.txt",
        created_at=datetime.now(UTC) - timedelta(days=2),
    )
    second = replace(
        make_document(b"second"),
        filename="Отчёт 2026.txt",
        created_at=datetime.now(UTC) - timedelta(days=1),
        status=DocumentStatus.ERROR,
        error_code="processing_failed",
        error_message="Processing failed",
    )
    third = replace(
        make_document(b"third"),
        filename="notes.txt",
        created_at=datetime.now(UTC),
    )

    for document, data in [
        (first, b"first"),
        (second, b"second"),
        (third, b"third"),
    ]:
        repository.create(document, data)

    assert [doc.id for doc in repository.list()] == [
        third.id,
        second.id,
        first.id,
    ]

    assert [doc.id for doc in repository.list(status=DocumentStatus.ERROR)] == [
        second.id,
    ]

    assert [doc.id for doc in repository.list(q="ОТЧЁТ")] == [
        second.id,
        first.id,
    ]

    assert [
        doc.id
        for doc in repository.list(
            status=DocumentStatus.ERROR,
            q="отчёт",
        )
    ] == [second.id]

    assert repository.list(q="несуществующий") == []


def test_list_after_repository_restart(tmp_path: Path) -> None:
    """Discover persisted documents without relying on in-memory state."""
    repository = LocalFileDocumentRepository(tmp_path)
    document = make_document(b"hello")

    repository.create(document, b"hello")

    restarted_repository = LocalFileDocumentRepository(tmp_path)

    assert restarted_repository.list() == [document]


def test_mark_processing_persists_status(tmp_path: Path) -> None:
    """Persist the processing status and reject repeated transitions."""
    repository = LocalFileDocumentRepository(tmp_path)
    document = make_document(b"hello")

    repository.create(document, b"hello")

    assert repository.mark_processing(document.id) is True
    assert repository.mark_processing(document.id) is False

    restarted_repository = LocalFileDocumentRepository(tmp_path)

    assert restarted_repository.get(document.id) == replace(
        document,
        status=DocumentStatus.PROCESSING,
    )


def test_mark_processing_rejects_missing_and_invalid_status(
    tmp_path: Path,
) -> None:
    """Reject missing documents and documents outside the uploaded state."""
    repository = LocalFileDocumentRepository(tmp_path)

    assert repository.mark_processing(uuid4()) is False

    document = replace(
        make_document(b"invalid"),
        status=DocumentStatus.ERROR,
        error_code="processing_failed",
        error_message="Previous processing failed",
    )

    repository.create(document, b"invalid")

    assert repository.mark_processing(document.id) is False
    assert repository.get(document.id) == document


def test_complete_saves_result_and_ready_status(tmp_path: Path) -> None:
    """Persist blocks, chunks, and ready status across repository restarts."""
    repository = LocalFileDocumentRepository(tmp_path)
    document = make_document(b"hello")
    repository.create(document, b"hello")

    assert repository.mark_processing(document.id) is True

    block_id = uuid4()
    result = ProcessingResult(
        document_id=document.id,
        blocks=[
            DocumentBlock(
                id=block_id,
                document_id=document.id,
                type="text",
                position=0,
                content="hello",
                start_char=0,
                end_char=5,
            )
        ],
        chunks=[
            Chunk(
                id=uuid4(),
                document_id=document.id,
                block_id=block_id,
                position=0,
                content="hello",
                start_char=0,
                end_char=5,
            )
        ],
    )

    assert repository.complete(document.id, result) is True

    restarted_repository = LocalFileDocumentRepository(tmp_path)
    saved_document = restarted_repository.get(document.id)

    assert restarted_repository.get_result(document.id) == result
    assert saved_document is not None
    assert saved_document.status == DocumentStatus.READY

    result_path = tmp_path / "documents" / str(document.id) / "result.json"
    saved_result = json.loads(result_path.read_text(encoding="utf-8"))

    assert saved_result["document_id"] == str(document.id)
    assert saved_result["blocks"][0]["content"] == "hello"
    assert saved_result["chunks"][0]["content"] == "hello"
    assert saved_result["chunks"][0]["block_id"] == str(block_id)


def test_complete_rejects_invalid_transitions(tmp_path: Path) -> None:
    """Do not save a result unless the document is processing."""
    repository = LocalFileDocumentRepository(tmp_path)
    document = make_document(b"hello")
    repository.create(document, b"hello")

    result = ProcessingResult(
        document_id=document.id,
        blocks=[],
        chunks=[],
    )

    assert repository.complete(document.id, result) is False

    result_path = tmp_path / "documents" / str(document.id) / "result.json"
    assert not result_path.exists()

    assert repository.mark_processing(document.id) is True

    with pytest.raises(ValueError, match="another document"):
        repository.complete(
            document.id,
            ProcessingResult(document_id=uuid4(), blocks=[], chunks=[]),
        )

    assert not result_path.exists()

    assert repository.complete(document.id, result) is True
    assert repository.complete(document.id, result) is False


def test_get_result_returns_none_before_processing(tmp_path: Path) -> None:
    """Do not return a processing result before one has been saved."""
    repository = LocalFileDocumentRepository(tmp_path)
    document = make_document(b"hello")

    assert repository.get_result(uuid4()) is None

    repository.create(document, b"hello")
    assert repository.get_result(document.id) is None

    assert repository.mark_processing(document.id) is True
    assert repository.get_result(document.id) is None


def test_fail_persists_error_after_restart(tmp_path: Path) -> None:
    """Preserve the failure status and diagnostics across repository restarts."""
    repository = LocalFileDocumentRepository(tmp_path)
    document = make_document(b"hello")

    repository.create(document, b"hello")
    assert repository.mark_processing(document.id) is True

    assert (
        repository.fail(
            document.id,
            code="processing_failed",
            message="Tokenizer unavailable",
        )
        is True
    )

    restarted_repository = LocalFileDocumentRepository(tmp_path)

    assert restarted_repository.get(document.id) == replace(
        document,
        status=DocumentStatus.ERROR,
        error_code="processing_failed",
        error_message="Tokenizer unavailable",
    )

    assert restarted_repository.get_result(document.id) is None
    assert restarted_repository.fail(document.id, "other_error", "Other") is False


def test_fail_rejects_invalid_transitions(tmp_path: Path) -> None:
    """Reject failures for missing, uploaded, and ready documents."""
    repository = LocalFileDocumentRepository(tmp_path)

    assert repository.fail(uuid4(), "error", "Missing document") is False

    document = make_document(b"hello")
    repository.create(document, b"hello")

    assert repository.fail(document.id, "error", "Not processing") is False
    assert repository.get(document.id) == document

    assert repository.mark_processing(document.id) is True

    result = ProcessingResult(
        document_id=document.id,
        blocks=[],
        chunks=[],
    )

    assert repository.complete(document.id, result) is True
    assert repository.fail(document.id, "error", "Already ready") is False

    saved_document = repository.get(document.id)

    assert saved_document is not None
    assert saved_document.status == DocumentStatus.READY
    assert saved_document.error_code is None


def test_delete_removes_document_and_result(tmp_path: Path) -> None:
    """Remove all document files and keep the deletion after restart."""
    repository = LocalFileDocumentRepository(tmp_path)
    document = make_document(b"hello")

    repository.create(document, b"hello")
    assert repository.mark_processing(document.id) is True

    result = ProcessingResult(
        document_id=document.id,
        blocks=[],
        chunks=[],
    )

    assert repository.complete(document.id, result) is True

    document_dir = tmp_path / "documents" / str(document.id)
    assert (document_dir / "original.bin").exists()
    assert (document_dir / "meta.json").exists()
    assert (document_dir / "result.json").exists()

    assert repository.delete(document.id) is True
    assert repository.delete(document.id) is False

    assert not document_dir.exists()
    assert repository.get(document.id) is None
    assert repository.read_original(document.id) is None
    assert repository.get_result(document.id) is None
    assert repository.list() == []

    restarted_repository = LocalFileDocumentRepository(tmp_path)
    assert restarted_repository.get(document.id) is None


def test_delete_during_processing_prevents_late_result(tmp_path: Path) -> None:
    """Prevent completed background work from restoring a deleted document."""
    repository = LocalFileDocumentRepository(tmp_path)
    document = make_document(b"hello")

    repository.create(document, b"hello")
    assert repository.mark_processing(document.id) is True

    assert repository.delete(document.id) is True

    late_result = ProcessingResult(
        document_id=document.id,
        blocks=[],
        chunks=[],
    )

    assert repository.complete(document.id, late_result) is False
    assert repository.fail(document.id, "processing_failed", "Late error") is False

    document_dir = tmp_path / "documents" / str(document.id)

    assert not document_dir.exists()
    assert repository.get(document.id) is None


def test_recover_incomplete_documents(tmp_path: Path) -> None:
    """Mark uploaded and processing documents as interrupted after restart."""
    repository = LocalFileDocumentRepository(tmp_path)

    uploaded = make_document(b"uploaded")
    processing = make_document(b"processing")

    repository.create(uploaded, b"uploaded")
    repository.create(processing, b"processing")
    assert repository.mark_processing(processing.id) is True

    restarted = LocalFileDocumentRepository(tmp_path)
    restarted.recover_incomplete()

    for document in (uploaded, processing):
        assert restarted.get(document.id) == replace(
            document,
            status=DocumentStatus.ERROR,
            error_code="processing_failed",
            error_message="Processing interrupted by server restart",
        )

    assert restarted.read_original(uploaded.id) == b"uploaded"
    assert restarted.read_original(processing.id) == b"processing"

    restarted.recover_incomplete()
    assert restarted.get(uploaded.id).status == DocumentStatus.ERROR


def test_recover_preserves_ready_and_error(tmp_path: Path) -> None:
    """Leave completed and previously failed documents unchanged."""
    repository = LocalFileDocumentRepository(tmp_path)

    ready = make_document(b"ready")
    failed = make_document(b"failed")

    repository.create(ready, b"ready")
    repository.create(failed, b"failed")

    assert repository.mark_processing(ready.id) is True
    assert (
        repository.complete(
            ready.id,
            ProcessingResult(document_id=ready.id, blocks=[], chunks=[]),
        )
        is True
    )

    assert repository.mark_processing(failed.id) is True
    assert repository.fail(failed.id, "invalid_encoding", "Invalid UTF-8") is True

    saved_ready = repository.get(ready.id)
    saved_failed = repository.get(failed.id)

    restarted = LocalFileDocumentRepository(tmp_path)
    restarted.recover_incomplete()

    assert restarted.get(ready.id) == saved_ready
    assert restarted.get(failed.id) == saved_failed
    assert restarted.get_result(ready.id) is not None


def test_recover_removes_incomplete_directories(tmp_path: Path) -> None:
    """Clean orphaned document and temporary creation directories."""
    LocalFileDocumentRepository(tmp_path)

    orphan_dir = tmp_path / "documents" / str(uuid4())
    orphan_dir.mkdir()
    (orphan_dir / "original.bin").write_bytes(b"incomplete")

    temporary_dir = tmp_path / "documents" / ".unfinished-create"
    temporary_dir.mkdir()
    (temporary_dir / "meta.json").write_text("{}", encoding="utf-8")

    restarted = LocalFileDocumentRepository(tmp_path)
    restarted.recover_incomplete()

    assert not orphan_dir.exists()
    assert not temporary_dir.exists()


def test_create_enforces_document_limit(tmp_path: Path) -> None:
    """Reject new documents when the library reaches its capacity."""
    repository = LocalFileDocumentRepository(tmp_path, max_documents=2)

    first = make_document(b"first")
    second = make_document(b"second")
    third = make_document(b"third")

    repository.create(first, b"first")
    repository.create(second, b"second")

    with pytest.raises(DocumentLimitExceededError):
        repository.create(third, b"third")

    assert len(repository.list()) == 2
    assert repository.get(third.id) is None
    assert not (tmp_path / "documents" / str(third.id)).exists()


def test_document_limit_survives_restart_and_deletion(tmp_path: Path) -> None:
    """Count persisted documents and release capacity after deletion."""
    repository = LocalFileDocumentRepository(tmp_path, max_documents=1)

    first = make_document(b"first")
    second = make_document(b"second")

    repository.create(first, b"first")

    restarted = LocalFileDocumentRepository(tmp_path, max_documents=1)

    with pytest.raises(DocumentLimitExceededError):
        restarted.create(second, b"second")

    assert restarted.delete(first.id) is True

    restarted.create(second, b"second")

    assert restarted.list() == [second]


def test_concurrent_create_respects_document_limit(tmp_path: Path) -> None:
    """Allow only one concurrent creation when one storage slot remains."""
    repository = LocalFileDocumentRepository(tmp_path, max_documents=1)

    first = make_document(b"first")
    second = make_document(b"second")
    barrier = Barrier(2)

    def attempt_create(document: Document, data: bytes) -> bool:
        barrier.wait(timeout=10)

        try:
            repository.create(document, data)
        except DocumentLimitExceededError:
            return False

        return True

    with ThreadPoolExecutor(max_workers=2) as executor:
        first_future = executor.submit(attempt_create, first, b"first")
        second_future = executor.submit(attempt_create, second, b"second")

        results = [
            first_future.result(),
            second_future.result(),
        ]

    assert sorted(results) == [False, True]

    saved_documents = repository.list()
    assert len(saved_documents) == 1

    saved_document = saved_documents[0]
    assert saved_document.id in {first.id, second.id}

    expected_data = b"first" if saved_document.id == first.id else b"second"

    assert repository.read_original(saved_document.id) == expected_data

    document_directories = list((tmp_path / "documents").iterdir())
    assert len(document_directories) == 1
