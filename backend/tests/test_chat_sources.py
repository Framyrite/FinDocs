"""Tests for exact citations and grounded mock chat answers."""

from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from app.chat.service import (
    INSUFFICIENT_INFO_ANSWER,
    ChatService,
    ChatServiceError,
)
from app.chat.sources import MAX_QUOTE_LENGTH, build_sources
from app.documents.models import Document, DocumentStatus
from app.documents.repository import LocalFileDocumentRepository
from app.llm.adapter import LLMAdapter
from app.llm.mock import MockLLM
from app.processing.models import Chunk, DocumentBlock, ProcessingResult
from app.processing.txt import decode_txt
from app.retrieval.lexical import RankedChunk


def make_ranked(
    text: str,
    *,
    start: int = 0,
    end: int | None = None,
) -> RankedChunk:
    """Build a candidate with real block-relative offsets."""
    document_id = uuid4()
    block_id = uuid4()
    end = len(text) if end is None else end

    document = Document(
        id=document_id,
        filename="Материал.txt",
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
        content=text[start:end],
        start_char=start,
        end_char=end,
    )

    return RankedChunk(
        document=document,
        block=block,
        chunk=chunk,
        coverage=1.0,
        match_count=2,
    )


def test_unicode_emoji_and_bom_offsets_are_exact() -> None:
    text = "Привет 😀\nОблигации приносят доход!"
    original = b"\xef\xbb\xbf" + text.encode("utf-8")
    decoded = decode_txt(original)

    sources = build_sources(
        [make_ranked(decoded)],
        "облигации доход",
    )

    assert len(sources) == 1

    source = sources[0]
    assert source.quote == "Облигации приносят доход!"
    assert source.start_char == decoded.index("Облигации")
    assert source.quote == decoded[source.start_char : source.end_char]


def test_best_sentence_uses_repeated_keyword_hits() -> None:
    text = "Кредит процент. Кредит процент кредит!"

    sources = build_sources(
        [make_ranked(text)],
        "кредит процент",
    )

    assert len(sources) == 1
    assert sources[0].quote == " Кредит процент кредит!"
    assert sources[0].quote == text[sources[0].start_char : sources[0].end_char]


def test_equal_score_chooses_first_sentence() -> None:
    text = "Кредит процент. Кредит процент!"

    sources = build_sources(
        [make_ranked(text)],
        "кредит процент",
    )

    assert len(sources) == 1
    assert sources[0].quote == "Кредит процент."


def test_long_sentence_uses_exact_300_character_window() -> None:
    text = "x" * 170 + " кредит процент " + "y" * 400

    sources = build_sources(
        [make_ranked(text)],
        "кредит процент",
    )

    assert len(sources) == 1

    source = sources[0]
    first_match = text.index("кредит")

    assert MAX_QUOTE_LENGTH == 300
    assert len(source.quote) == 300
    assert source.start_char == first_match - 100
    assert source.start_char <= first_match < source.end_char
    assert "кредит" in source.quote
    assert source.quote == text[source.start_char : source.end_char]


def test_identical_document_ranges_are_deduplicated() -> None:
    first = make_ranked("Кредит процент.")

    duplicate = replace(
        first,
        chunk=replace(
            first.chunk,
            id=uuid4(),
            position=1,
        ),
    )

    sources = build_sources(
        [first, duplicate],
        "кредит процент",
    )

    assert len(sources) == 1
    assert sources[0].chunk_id == first.chunk.id


def test_overlapping_but_different_ranges_are_allowed() -> None:
    text = "кредит процент кредит процент кредит процент"
    first = make_ranked(text, end=len(text) - 9)

    second = replace(
        first,
        chunk=replace(
            first.chunk,
            id=uuid4(),
            position=1,
            start_char=7,
            end_char=len(text),
            content=text[7:],
        ),
    )

    sources = build_sources(
        [first, second],
        "кредит процент",
    )

    assert len(sources) == 2
    assert sources[0].start_char < sources[1].start_char
    assert sources[1].start_char < sources[0].end_char

    for source in sources:
        assert source.quote == text[source.start_char : source.end_char]


def test_inconsistent_chunk_content_is_rejected() -> None:
    ranked = make_ranked("Кредит процент.")

    damaged = replace(
        ranked,
        chunk=replace(
            ranked.chunk,
            content="x" * len(ranked.chunk.content),
        ),
    )

    assert (
        build_sources(
            [damaged],
            "кредит процент",
        )
        == []
    )


def make_ready_repository(
    tmp_path: Path,
) -> tuple[LocalFileDocumentRepository, Document, str]:
    """Persist one real ready document without rerunning the tokenizer."""
    text = "Кредит приносит процент."
    ranked = make_ranked(text)

    repository = LocalFileDocumentRepository(tmp_path)

    uploaded = replace(
        ranked.document,
        status=DocumentStatus.UPLOADED,
    )

    repository.create(
        uploaded,
        text.encode("utf-8"),
    )

    assert repository.mark_processing(uploaded.id)

    assert repository.complete(
        uploaded.id,
        ProcessingResult(
            document_id=uploaded.id,
            blocks=[ranked.block],
            chunks=[ranked.chunk],
        ),
    )

    return repository, uploaded, text


def test_chat_answer_uses_real_persisted_sources(
    tmp_path: Path,
) -> None:
    repository, document, text = make_ready_repository(tmp_path)
    service = ChatService(repository, MockLLM())

    response = service.ask(
        "кредит процент",
        [document.id],
    )

    assert response.status == "answered"
    assert len(response.sources) == 1

    source = response.sources[0]
    assert source.document_id == document.id
    assert source.quote == text[source.start_char : source.end_char]

    original = repository.read_original(document.id)
    assert original is not None

    decoded = decode_txt(original)
    assert source.quote == decoded[source.start_char : source.end_char]

    assert response.answer == (
        f"[MOCK] Найдены фрагменты по ключевым словам вопроса:\n1. «{source.quote}»"
    )


class NeverCallLLM(LLMAdapter):
    """Fail the test if a model is called without sources."""

    def generate(self, question: str, context: str) -> str:
        raise AssertionError("LLM must not be called")


@pytest.mark.parametrize(
    "question",
    ["облигация", "как что это"],
)
def test_insufficient_info_never_calls_llm(
    tmp_path: Path,
    question: str,
) -> None:
    repository, document, _ = make_ready_repository(tmp_path)
    service = ChatService(repository, NeverCallLLM())

    response = service.ask(question, [document.id])

    assert response.status == "insufficient_info"
    assert response.answer == INSUFFICIENT_INFO_ANSWER
    assert response.sources == []


class BrokenLLM(LLMAdapter):
    """Simulate a technical adapter failure."""

    def generate(self, question: str, context: str) -> str:
        raise RuntimeError("LLM is unavailable")


def test_adapter_failure_is_not_insufficient_info(
    tmp_path: Path,
) -> None:
    repository, document, _ = make_ready_repository(tmp_path)
    service = ChatService(repository, BrokenLLM())

    with pytest.raises(ChatServiceError) as error:
        service.ask("кредит процент", [document.id])

    assert error.value.status_code == 503
    assert error.value.code == "llm_unavailable"


class BlankLLM(LLMAdapter):
    """Return a blank answer to test adapter validation."""

    def __init__(self, answer: str) -> None:
        self.answer = answer

    def generate(self, question: str, context: str) -> str:
        return self.answer


@pytest.mark.parametrize("blank_answer", ["", "   ", "\n\t"])
def test_blank_llm_answer_returns_503(
    tmp_path: Path,
    blank_answer: str,
) -> None:
    repository, document, _ = make_ready_repository(tmp_path)

    service = ChatService(
        repository,
        BlankLLM(blank_answer),
    )

    with pytest.raises(ChatServiceError) as error:
        service.ask(
            "кредит процент",
            [document.id],
        )

    assert error.value.status_code == 503
    assert error.value.code == "llm_unavailable"
