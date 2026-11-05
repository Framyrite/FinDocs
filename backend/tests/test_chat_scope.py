"""Tests for chat request validation and document scope."""

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.chat.models import ChatRequest
from app.chat.service import ChatService, ChatServiceError
from app.documents.models import Document
from app.documents.repository import LocalFileDocumentRepository
from app.llm.mock import MockLLM
from app.processing.models import ProcessingResult


def make_document(
    repository: LocalFileDocumentRepository,
    *,
    ready: bool = False,
) -> Document:
    data = b"Sample document text"

    document = Document(
        id=uuid4(),
        filename="sample.txt",
        size_bytes=len(data),
        created_at=datetime.now(UTC),
    )

    repository.create(document, data)

    if ready:
        assert repository.mark_processing(document.id)
        assert repository.complete(
            document.id,
            ProcessingResult(
                document_id=document.id,
                blocks=[],
                chunks=[],
            ),
        )

    return document


def test_request_strips_question_and_parses_uuids() -> None:
    document_id = uuid4()

    request = ChatRequest.model_validate(
        {
            "question": "  Что такое облигация?  ",
            "document_ids": [str(document_id)],
        }
    )

    assert request.question == "Что такое облигация?"
    assert request.document_ids == [document_id]


@pytest.mark.parametrize(
    "question",
    ["", " \t ", "x" * 2001],
)
def test_request_rejects_invalid_question(question: str) -> None:
    with pytest.raises(ValidationError):
        ChatRequest(question=question)


def test_request_rejects_empty_document_ids() -> None:
    with pytest.raises(ValidationError):
        ChatRequest(
            question="Тестовый вопрос",
            document_ids=[],
        )


def test_implicit_scope_uses_only_ready_documents(
    tmp_path: Path,
) -> None:
    repository = LocalFileDocumentRepository(tmp_path)
    ready = make_document(repository, ready=True)
    make_document(repository)

    service = ChatService(repository, MockLLM())
    selected = service.select_documents(None)

    assert len(selected) == 1
    assert selected[0].document.id == ready.id
    assert selected[0].result.document_id == ready.id


def test_explicit_scope_deduplicates_and_excludes_other_documents(
    tmp_path: Path,
) -> None:
    repository = LocalFileDocumentRepository(tmp_path)
    first = make_document(repository, ready=True)
    make_document(repository, ready=True)

    service = ChatService(repository, MockLLM())
    selected = service.select_documents([first.id, first.id])

    assert len(selected) == 1
    assert selected[0].document.id == first.id


def test_missing_document_returns_404(tmp_path: Path) -> None:
    repository = LocalFileDocumentRepository(tmp_path)
    service = ChatService(repository, MockLLM())

    with pytest.raises(ChatServiceError) as error:
        service.select_documents([uuid4()])

    assert error.value.status_code == 404
    assert error.value.code == "document_not_found"


def test_non_ready_document_returns_409(tmp_path: Path) -> None:
    repository = LocalFileDocumentRepository(tmp_path)
    document = make_document(repository)
    service = ChatService(repository, MockLLM())

    with pytest.raises(ChatServiceError) as error:
        service.select_documents([document.id])

    assert error.value.status_code == 409
    assert error.value.code == "document_not_ready"


def test_no_ready_documents_returns_409(tmp_path: Path) -> None:
    repository = LocalFileDocumentRepository(tmp_path)
    make_document(repository)
    service = ChatService(repository, MockLLM())

    with pytest.raises(ChatServiceError) as error:
        service.select_documents(None)

    assert error.value.status_code == 409
    assert error.value.code == "no_ready_documents"
