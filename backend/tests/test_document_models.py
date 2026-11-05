"""Tests for document metadata and processing statuses."""

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.documents.models import Document, DocumentStatus


def test_document_status_values() -> None:
    """Verify the four processing statuses defined by the contract."""
    assert [status.value for status in DocumentStatus] == [
        "uploaded",
        "processing",
        "ready",
        "error",
    ]


def test_document_defaults() -> None:
    """Verify metadata is preserved and new documents start as uploaded."""
    document_id = uuid4()
    created_at = datetime.now(UTC)

    document = Document(
        id=document_id,
        filename="example.txt",
        size_bytes=128,
        created_at=created_at,
    )

    assert document.id == document_id
    assert document.filename == "example.txt"
    assert document.size_bytes == 128
    assert document.created_at == created_at
    assert document.format == "txt"
    assert document.status == DocumentStatus.UPLOADED
    assert document.error_code is None
    assert document.error_message is None


def test_document_error_metadata() -> None:
    """Allow storing an error status with its diagnostic details."""
    document = Document(
        id=uuid4(),
        filename="invalid.txt",
        size_bytes=10,
        created_at=datetime.now(UTC),
        status=DocumentStatus.ERROR,
        error_code="invalid_encoding",
        error_message="TXT must be UTF-8",
    )

    assert document.status == DocumentStatus.ERROR
    assert document.error_code == "invalid_encoding"
    assert document.error_message == "TXT must be UTF-8"


def test_document_is_immutable() -> None:
    """Prevent accidental mutation of stored document metadata."""
    document = Document(
        id=uuid4(),
        filename="example.txt",
        size_bytes=128,
        created_at=datetime.now(UTC),
    )

    with pytest.raises(FrozenInstanceError):
        document.filename = "changed.txt"
