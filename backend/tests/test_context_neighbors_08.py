"""Context-neighbor regression tests for Backend 0.8.3."""

from dataclasses import replace
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from app.chat.context import expand_context_candidates, prepare_llm_context
from app.chat.sources import build_answer_sources
from app.documents.models import Document, DocumentStatus
from app.processing.models import Chunk, DocumentBlock, ProcessingResult
from app.retrieval.lexical import RankedChunk


def make_ranked(text: str) -> RankedChunk:
    """Construct a valid ready chunk with original-text offsets."""
    document_id = uuid4()
    block_id = uuid4()
    document = Document(
        id=document_id,
        filename="sample.txt",
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


def make_two_chunks() -> tuple[RankedChunk, RankedChunk, SimpleNamespace]:
    """Produce overlapping persisted chunks around an SJF explanation."""
    text = (
        "SJF выбирает кратчайшую задачу. Квантование времени не применяется. "
        "Причина сложности SJF: невозможность точного знания длительности "
        "CPU burst исполняющихся процессов."
    )
    first = make_ranked(text)
    split = text.index("Причина сложности")
    left = replace(
        first,
        chunk=replace(
            first.chunk,
            content=text[:split],
            end_char=split,
        ),
    )
    right = replace(
        first,
        chunk=replace(
            first.chunk,
            id=uuid4(),
            position=1,
            start_char=split - 15,
            end_char=len(text),
            content=text[split - 15 :],
        ),
    )
    stored = SimpleNamespace(
        document=first.document,
        result=ProcessingResult(
            document_id=first.document.id,
            blocks=[first.block],
            chunks=[left.chunk, right.chunk],
        ),
    )
    return left, right, stored


def test_explanation_uses_same_block_next_chunk() -> None:
    left, right, selected = make_two_chunks()
    expanded = expand_context_candidates(
        [left], [selected], "Из-за чего SJF сложно применить на практике?"
    )
    assert [item.chunk.id for item in expanded] == [left.chunk.id, right.chunk.id]
    prepared = prepare_llm_context(expanded)
    assert "невозможность точного знания" in prepared.text
    assert len(prepared.entries) == 2
    assert prepared.entries[1].candidate.chunk.id == right.chunk.id

    sources = build_answer_sources(
        prepared,
        "Из-за чего SJF сложно применить на практике?",
        "В SJF невозможно точно знать длительность CPU burst.",
    )
    assert any("невозможность" in source.quote for source in sources)
    for source in sources:
        assert (
            source.quote == selected.result.blocks[0].content[source.start_char : source.end_char]
        )


def test_non_explanation_question_keeps_only_retrieved_chunk() -> None:
    left, _, selected = make_two_chunks()
    expanded = expand_context_candidates([left], [selected], "Что такое алгоритм SJF?")
    assert expanded == [left]


def test_does_not_follow_into_another_document() -> None:
    left, _, selected = make_two_chunks()
    foreign = make_ranked("SJF: невозможность точного знания CPU burst.")
    foreign_document = SimpleNamespace(
        document=foreign.document,
        result=ProcessingResult(
            document_id=foreign.document.id,
            blocks=[foreign.block],
            chunks=[foreign.chunk],
        ),
    )
    expanded = expand_context_candidates(
        [left], [selected, foreign_document], "Почему SJF сложно использовать?"
    )
    assert all(item.document.id == left.document.id for item in expanded)


def test_corrupted_neighbor_is_not_included() -> None:
    left, right, selected = make_two_chunks()
    bad_right = replace(right.chunk, content="x" * len(right.chunk.content))
    selected.result.chunks[1] = bad_right
    expanded = expand_context_candidates([left], [selected], "Почему SJF сложно?")
    assert expanded == [left]


def test_no_expansion_over_top_k_limit() -> None:
    left, right, selected = make_two_chunks()
    three = [left, right, replace(right, chunk=replace(right.chunk, id=uuid4()))]
    expanded = expand_context_candidates(three, [selected], "Почему SJF сложно?")
    assert expanded == three
