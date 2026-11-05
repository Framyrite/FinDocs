"""Tests for document storage initialization and FastAPI lifespan."""

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.documents.models import Document, DocumentStatus
from app.documents.repository import LocalFileDocumentRepository
from app.documents.service import DocumentService
from app.main import create_app


def test_lifespan_initializes_repository_and_service(tmp_path: Path) -> None:
    """Initialize document dependencies using the configured storage path."""
    settings = Settings(
        _env_file=None,
        data_dir=tmp_path,
        max_documents=5,
    )

    application = create_app(settings=settings)

    assert not (tmp_path / "documents").exists()

    with TestClient(application) as client:
        assert client.get("/health").json() == {"status": "ok"}

        repository = application.state.document_repository
        service = application.state.document_service

        assert isinstance(repository, LocalFileDocumentRepository)
        assert isinstance(service, DocumentService)

        document = Document(
            id=uuid4(),
            filename="example.txt",
            size_bytes=5,
            created_at=datetime.now(UTC),
        )

        repository.create(document, b"hello")

        assert repository.get(document.id) == document

    document_dir = tmp_path / "documents" / str(document.id)

    assert (document_dir / "original.bin").read_bytes() == b"hello"
    assert (document_dir / "meta.json").is_file()


def test_lifespan_recovers_documents_with_injected_repository(
    tmp_path: Path,
) -> None:
    """Recover interrupted processing using the injected repository."""
    repository = LocalFileDocumentRepository(tmp_path)

    document = Document(
        id=uuid4(),
        filename="interrupted.txt",
        size_bytes=5,
        created_at=datetime.now(UTC),
    )

    repository.create(document, b"hello")
    assert repository.mark_processing(document.id) is True

    settings = Settings(
        _env_file=None,
        data_dir=tmp_path / "unused",
    )

    application = create_app(
        settings=settings,
        document_repository=repository,
    )

    with TestClient(application) as client:
        assert client.get("/health").status_code == 200

        assert application.state.document_repository is repository

        saved = repository.get(document.id)

        assert saved is not None
        assert saved.status == DocumentStatus.ERROR
        assert saved.error_code == "processing_failed"
        assert saved.error_message == ("Processing interrupted by server restart")

    assert not (tmp_path / "unused").exists()


def test_recovery_runs_once_per_application_startup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Run recovery once at startup, not on each HTTP request."""
    repository = LocalFileDocumentRepository(tmp_path)

    calls = 0
    original_recovery = repository.recover_incomplete

    def counted_recovery() -> None:
        nonlocal calls
        calls += 1
        original_recovery()

    monkeypatch.setattr(
        repository,
        "recover_incomplete",
        counted_recovery,
    )

    application = create_app(
        settings=Settings(_env_file=None, data_dir=tmp_path),
        document_repository=repository,
    )

    with TestClient(application) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/health").status_code == 200
        assert client.get("/health").status_code == 200

    assert calls == 1
