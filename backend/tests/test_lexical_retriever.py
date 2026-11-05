"""Unit tests for deterministic lexical chunk retrieval."""

from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.chat.service import ReadyDocument
from app.documents.models import Document, DocumentStatus
from app.processing.models import Chunk, DocumentBlock, ProcessingResult
from app.retrieval.lexical import (
    MIN_COVERAGE,
    TOP_K,
    LexicalRetriever,
    normalize_stems,
)


def make_ready_document(
    blocks_texts: list[list[str]],
    *,
    document_id: UUID | None = None,
    created_at: datetime | None = None,
) -> ReadyDocument:
    """Build real blocks and chunks with valid character ranges."""
    doc_id = document_id or uuid4()
    blocks: list[DocumentBlock] = []
    chunks: list[Chunk] = []
    absolute_start = 0

    for block_position, chunk_texts in enumerate(blocks_texts):
        block_id = uuid4()
        block_content = " ".join(chunk_texts)

        blocks.append(
            DocumentBlock(
                id=block_id,
                document_id=doc_id,
                type="text",
                position=block_position,
                content=block_content,
                start_char=absolute_start,
                end_char=absolute_start + len(block_content),
            )
        )

        local_start = 0

        for chunk_position, content in enumerate(chunk_texts):
            chunks.append(
                Chunk(
                    id=uuid4(),
                    document_id=doc_id,
                    block_id=block_id,
                    position=chunk_position,
                    content=content,
                    start_char=local_start,
                    end_char=local_start + len(content),
                )
            )

            local_start += len(content) + 1

        absolute_start += len(block_content) + 1

    document = Document(
        id=doc_id,
        filename=f"{doc_id}.txt",
        size_bytes=100,
        created_at=created_at or datetime.now(UTC),
        status=DocumentStatus.READY,
    )

    result = ProcessingResult(
        document_id=doc_id,
        blocks=blocks,
        chunks=chunks,
    )

    return ReadyDocument(document=document, result=result)


def test_unicode_normalization_and_word_boundaries() -> None:
    stems = normalize_stems("ЁЛОЧКА ёлочка БАНК_2026 12 123 АБ")

    assert stems == [
        "елочк",
        "елочк",
        "банк",
        "2026",
        "123",
    ]


def test_exact_stop_words_and_five_character_stems() -> None:
    stems = normalize_stems("как какой что между КАКОЕ Процентная")

    assert stems == ["какое", "проце"]


def test_empty_normalized_question_returns_no_matches() -> None:
    document = make_ready_document([["банк кредит процент"]])

    found = LexicalRetriever().retrieve(
        "как что это",
        [document],
    )

    assert found == []


def test_coverage_threshold_accepts_exactly_06() -> None:
    document = make_ready_document(
        [
            [
                "кредитная ставка доходность",
                "кредитная ставка",
            ]
        ]
    )

    found = LexicalRetriever().retrieve(
        "кредит ставка доход процент риск",
        [document],
    )

    assert MIN_COVERAGE == 0.6
    assert len(found) == 1
    assert found[0].coverage == 0.6
    assert found[0].match_count == 3
    assert found[0].chunk.content == "кредитная ставка доходность"


def test_match_frequency_has_priority_over_creation_date() -> None:
    older = make_ready_document(
        [["кредит ставка кредит"]],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
    )
    newer = make_ready_document(
        [["кредит ставка"]],
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )

    found = LexicalRetriever().retrieve(
        "кредит ставка",
        [newer, older],
    )

    assert [item.document.id for item in found] == [
        older.document.id,
        newer.document.id,
    ]
    assert [item.match_count for item in found] == [3, 2]


def test_creation_date_breaks_equal_score_ties() -> None:
    older = make_ready_document(
        [["банк процент"]],
        document_id=UUID(int=1),
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
    )
    newer = make_ready_document(
        [["банк процент"]],
        document_id=UUID(int=2),
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )

    found = LexicalRetriever().retrieve(
        "банк процент",
        [older, newer],
    )

    assert [item.document.id for item in found] == [
        newer.document.id,
        older.document.id,
    ]


def test_document_id_breaks_equal_timestamp_ties() -> None:
    timestamp = datetime(2026, 1, 1, tzinfo=UTC)

    greater_id = make_ready_document(
        [["банк процент"]],
        document_id=UUID(int=20),
        created_at=timestamp,
    )
    smaller_id = make_ready_document(
        [["банк процент"]],
        document_id=UUID(int=10),
        created_at=timestamp,
    )

    found = LexicalRetriever().retrieve(
        "банк процент",
        [greater_id, smaller_id],
    )

    assert [item.document.id for item in found] == [
        smaller_id.document.id,
        greater_id.document.id,
    ]


def test_block_and_chunk_position_break_remaining_ties() -> None:
    document = make_ready_document(
        [
            ["банк процент", "банк процент"],
            ["банк процент"],
        ]
    )

    found = LexicalRetriever().retrieve(
        "банк процент",
        [document],
    )

    assert [(item.block.position, item.chunk.position) for item in found] == [
        (0, 0),
        (0, 1),
        (1, 0),
    ]


def test_top_k_is_three_and_results_are_repeatable() -> None:
    document = make_ready_document([[f"банк процент {number}" for number in range(5)]])
    retriever = LexicalRetriever()

    first = retriever.retrieve("банк процент", [document])
    second = retriever.retrieve("банк процент", [document])

    assert TOP_K == 3
    assert len(first) == 3
    assert first == second
    assert [item.chunk.position for item in first] == [0, 1, 2]


def test_non_ready_document_is_not_searched() -> None:
    ready = make_ready_document([["банк процент"]])

    not_ready = ReadyDocument(
        document=replace(
            ready.document,
            status=DocumentStatus.PROCESSING,
        ),
        result=ready.result,
    )

    found = LexicalRetriever().retrieve(
        "банк процент",
        [not_ready],
    )

    assert found == []
