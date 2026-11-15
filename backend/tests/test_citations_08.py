"""Regression tests for Backend 0.8.3 answer-aware, verifiable citations."""

from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from app.chat.context import prepare_llm_context
from app.chat.sources import MAX_QUOTE_LENGTH, build_answer_sources, build_context_sources
from app.documents.models import Document, DocumentStatus
from app.processing.models import Chunk, DocumentBlock, ProcessingResult
from app.retrieval.lexical import LexicalRetriever, RankedChunk, _latin_acronyms

QA_DIR = Path(__file__).resolve().parents[2] / "qa" / "test_data"


def make_ranked(text: str, *, block_start: int = 0) -> RankedChunk:
    """Construct a valid stored chunk with independent document coordinates."""
    document_id = uuid4()
    block_id = uuid4()
    document = Document(
        id=document_id,
        filename="материал.txt",
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
        start_char=block_start,
        end_char=block_start + len(text),
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
    return RankedChunk(document=document, block=block, chunk=chunk, coverage=1, match_count=2)


def assert_exact(sources, ranked: RankedChunk) -> None:
    """All returned quotes must have original Unicode offsets inside their chunks."""
    for source in sources:
        assert source.document_id == ranked.document.id
        assert source.block_id == ranked.block.id
        assert source.chunk_id == ranked.chunk.id
        assert 0 < len(source.quote) <= MAX_QUOTE_LENGTH
        assert ranked.block.start_char <= source.start_char < source.end_char
        left = source.start_char - ranked.block.start_char
        right = source.end_char - ranked.block.start_char
        assert source.quote == ranked.block.content[left:right]
        assert ranked.chunk.start_char <= left < right <= ranked.chunk.end_char


def test_footnote_number_is_recognized_only_on_uppercase_acronym() -> None:
    assert _latin_acronyms("FIFO1, RR, XIV, p01, fifo1, CPU100") == {"fifo", "rr"}


def test_fifo1_retrieval_prioritizes_fcfs_over_generic_planning() -> None:
    relevant = (
        "Алгоритм FCFS планирования является невытесняющим и работает по принципу очереди FIFO1. "
    )
    irrelevant = "Алгоритм планирования работает с процессами и невытесняющими задачами."
    ranked = make_ranked(relevant + irrelevant)
    first, second = (
        replace(ranked.chunk, content=relevant, end_char=len(relevant)),
        replace(
            ranked.chunk,
            id=uuid4(),
            content=irrelevant,
            start_char=len(relevant),
            end_char=len(relevant + irrelevant),
            position=1,
        ),
    )
    result = ProcessingResult(
        document_id=ranked.document.id, blocks=[ranked.block], chunks=[first, second]
    )

    ready = SimpleNamespace(document=ranked.document, result=result)

    matches = LexicalRetriever().retrieve(
        "Какой алгоритм планирования является невытесняющим и работает по принципу FIFO?",
        [ready],
    )
    assert matches
    assert "FIFO1" in matches[0].chunk.content


def test_d01_answer_quote_contains_definition_and_explanation() -> None:
    text = (QA_DIR / "only_text.txt").read_text(encoding="utf-8")
    ranked = make_ranked(text)
    sources = build_answer_sources(
        prepare_llm_context([ranked]),
        "Что такое стохастическая реконсолидация?",
        "Исследователи назвали процесс стохастической реконсолидацией. "
        "Поломка шаблона позволяет абстрагировать навык и перенести его в долговременную память.",
    )
    assert sources
    assert "стохастической реконсолидацией" in sources[0].quote
    assert "абстрагировать навык" in sources[0].quote
    assert_exact(sources, ranked)


def test_d04_first_quote_explains_practical_sjf_limit() -> None:
    text = (QA_DIR / "на_русском.txt").read_text(encoding="utf-8")
    ranked = make_ranked(text)
    sources = build_answer_sources(
        prepare_llm_context([ranked], max_chars=50000),
        "Из-за чего алгоритм Shortest-Job-First (SJF) сложно применить с точностью?",
        "Для реализации SJF необходимо знать время CPU burst всех процессов; "
        "в реальности точное время исполнения неизвестно.",
    )
    assert sources
    assert "невозможность точного знания" in sources[0].quote
    assert_exact(sources, ranked)


def test_year_abbreviation_keeps_1534_in_quote() -> None:
    text = "Первый период длится с 1534 г. (принятие акта о супрематии, рождение церкви)."
    ranked = make_ranked(text, block_start=15)
    sources = build_answer_sources(
        prepare_llm_context([ranked]),
        "Когда принят акт о супрематии?",
        "Акт о супрематии принят в 1534 году.",
    )
    assert sources
    assert "1534 г." in sources[0].quote
    assert_exact(sources, ranked)


def test_answer_quote_cannot_use_chunk_not_sent_to_llm() -> None:
    first = make_ranked("Кредит выдан банком. Процент выплачивается клиенту.")
    second = make_ranked("Секретная ставка кредита составляет девять процентов.")
    prepared = prepare_llm_context([first, second], max_chars=160)
    assert len(prepared.entries) == 1
    sources = build_answer_sources(
        prepared,
        "Какая ставка кредита?",
        "Ставка кредита составляет девять процентов.",
    )
    assert all(source.document_id == first.document.id for source in sources)
    assert_exact(sources, first)


def test_overlapping_chunks_cannot_cite_hidden_prefix_of_second() -> None:
    text = "Кредит и процент. Номинал и доходность. Облигация и купон."
    first = make_ranked(text)
    left = replace(first, chunk=replace(first.chunk, content=text[:38], end_char=38))
    right = replace(
        first,
        chunk=replace(
            first.chunk,
            id=uuid4(),
            position=1,
            start_char=30,
            end_char=len(text),
            content=text[30:],
        ),
    )
    prepared = prepare_llm_context([left, right])
    assert len(prepared.entries) == 2
    assert prepared.entries[1].ranges == ((38, len(text)),)
    sources = build_answer_sources(prepared, "Облигация купон", "Облигация даёт купон.")
    for source in sources:
        if source.chunk_id == right.chunk.id:
            assert source.start_char >= 38
            assert_exact([source], right)


def test_query_fallback_sources_still_refer_to_sent_text() -> None:
    ranked = make_ranked("Кредит приносит процент. Второе предложение разъясняет детали.")
    prepared = prepare_llm_context([ranked])
    sources = build_context_sources(prepared, "кредит процент")
    assert sources
    assert_exact(sources, ranked)


def test_d02_quotes_cover_fcfs_fifo_and_nonpreemptive_behavior() -> None:
    """Answer citations should cover the name, queue and scheduling mode."""
    text = (QA_DIR / "на_русском.txt").read_text(encoding="utf-8")[:1600]
    ranked = make_ranked(text)
    question = "Какой алгоритм планирования является невытесняющим и работает по принципу FIFO?"
    answer = (
        "Алгоритмом планирования, который является невытесняющим "
        "и работает по принципу FIFO (First In, First Out), является FCFS "
        "(First-Come, First-Served)."
    )
    sources = build_answer_sources(prepare_llm_context([ranked]), question, answer)
    assert any("FIFO1" in source.quote for source in sources)
    assert any("FCFS" in source.quote for source in sources)
    assert any("невытесняющее планирование" in source.quote for source in sources)
    assert 1 <= len(sources) <= 3
    assert_exact(sources, ranked)
