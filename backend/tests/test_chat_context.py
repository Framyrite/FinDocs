"""Verify bounded LLM context and existing chat contracts."""

from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from app.chat.context import build_llm_context
from app.chat.service import ChatService
from app.documents.models import Document, DocumentStatus
from app.documents.repository import LocalFileDocumentRepository
from app.llm.adapter import LLMAdapter
from app.processing.models import Chunk, DocumentBlock, ProcessingResult
from app.retrieval.lexical import RankedChunk


def make_ranked(text: str) -> RankedChunk:
    """Create a valid persisted-style chunk and document."""
    document_id = uuid4()
    block_id = uuid4()
    document = Document(
        id=document_id,
        filename="example.txt",
        size_bytes=len(text.encode("utf-8")),
        created_at=datetime.now(UTC),
        status=DocumentStatus.READY,
    )
    block = DocumentBlock(
        id=block_id,
        document_id=document_id,
        type="text",
        position=0,
        content=text,
        start_char=0,
        end_char=len(text),
    )
    chunk = Chunk(
        id=uuid4(),
        document_id=document_id,
        block_id=block_id,
        position=0,
        content=text,
        start_char=0,
        end_char=len(text),
    )
    return RankedChunk(
        document=document,
        block=block,
        chunk=chunk,
        coverage=1.0,
        match_count=2,
    )


def test_context_contains_complete_verified_chunk() -> None:
    text = (
        "Алгоритм SJF выбирает минимальный CPU burst. "
        "Сложность в невозможности знать длительность следующего CPU burst."
    )
    ranked = make_ranked(text)
    context = build_llm_context([ranked])

    assert text in context
    assert str(ranked.document.id) in context
    assert str(ranked.chunk.id) in context


def test_context_removes_overlapping_characters() -> None:
    text = "Первое предложение. Второе предложение. Третье предложение."
    first = make_ranked(text)
    first = replace(
        first,
        chunk=replace(
            first.chunk,
            content=text[:35],
            end_char=35,
        ),
    )
    second = replace(
        first,
        chunk=replace(
            first.chunk,
            id=uuid4(),
            position=1,
            content=text[25:],
            start_char=25,
            end_char=len(text),
        ),
    )

    context = build_llm_context([first, second])

    assert text[:35] in context
    assert text[35:] in context
    parts = context.split("\n\n")
    assert len(parts) == 2
    assert parts[0].split("\n", 1)[1] == text[:35]
    assert parts[1].split("\n", 1)[1] == text[35:]


def test_context_rejects_corruption_and_non_ready_documents() -> None:
    ranked = make_ranked("Кредит приносит процент.")
    corrupted = replace(
        ranked,
        chunk=replace(ranked.chunk, content="x" * len(ranked.chunk.content)),
    )
    not_ready = replace(
        ranked,
        document=replace(ranked.document, status=DocumentStatus.PROCESSING),
    )

    assert build_llm_context([corrupted, not_ready]) == ""


def test_context_never_truncates_mid_chunk() -> None:
    ranked = make_ranked("Доказательство требует полного предложения.")

    assert build_llm_context([ranked], max_chars=30) == ""


class RecordingLLM(LLMAdapter):
    """Record the exact context given to a non-mock adapter."""

    def __init__(self) -> None:
        self.context: str | None = None

    def generate(self, question: str, context: str) -> str:
        self.context = context
        return "Кредит приносит процент."


def test_chat_service_sends_full_chunk_to_non_mock_adapter(tmp_path: Path) -> None:
    text = (
        "Кредит приносит процент. Второе предложение предоставляет дополнительное доказательство."
    )
    ranked = make_ranked(text)
    repository = LocalFileDocumentRepository(tmp_path)
    uploaded = replace(ranked.document, status=DocumentStatus.UPLOADED)
    repository.create(uploaded, text.encode("utf-8"))
    assert repository.mark_processing(uploaded.id)
    assert repository.complete(
        uploaded.id,
        ProcessingResult(
            document_id=uploaded.id,
            blocks=[ranked.block],
            chunks=[ranked.chunk],
        ),
    )
    llm = RecordingLLM()

    result = ChatService(repository, llm).ask("кредит процент", [uploaded.id])

    assert result.status == "answered"
    assert result.sources
    assert llm.context is not None
    assert text in llm.context
    assert "дополнительное доказательство" in llm.context
