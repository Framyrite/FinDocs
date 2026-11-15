"""Regression tests for guarded lexical recall in Backend 0.8."""

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from app.chat.service import ReadyDocument
from app.documents.models import Document, DocumentStatus
from app.processing.models import Chunk, DocumentBlock, ProcessingResult
from app.retrieval.lexical import LexicalRetriever

QA_DIR = Path(__file__).resolve().parents[2] / "qa" / "test_data"


def make_ready(*texts: str) -> ReadyDocument:
    """Build valid chunks of a single ready document for ranking tests."""
    document_id = uuid4()
    block_id = uuid4()
    content = " ".join(texts)
    block = DocumentBlock(
        id=block_id,
        document_id=document_id,
        type="text",
        position=0,
        content=content,
        start_char=0,
        end_char=len(content),
    )
    chunks = []
    offset = 0
    for position, text in enumerate(texts):
        chunks.append(
            Chunk(
                id=uuid4(),
                document_id=document_id,
                block_id=block_id,
                position=position,
                content=text,
                start_char=offset,
                end_char=offset + len(text),
            )
        )
        offset += len(text) + 1

    document = Document(
        id=document_id,
        filename="qa.txt",
        size_bytes=len(content.encode("utf-8")),
        created_at=datetime.now(UTC),
        status=DocumentStatus.READY,
    )
    return ReadyDocument(
        document=document,
        result=ProcessingResult(
            document_id=document_id,
            blocks=[block],
            chunks=chunks,
        ),
    )


def test_rr_acronym_is_searchable() -> None:
    ready = make_ready("Квантовое планирование RR использует таймер.")
    found = LexicalRetriever().retrieve("RR", [ready])
    assert len(found) == 1
    assert found[0].coverage == 1.0


def test_fifo_anchor_outranks_generic_sjf_chunk() -> None:
    generic = "Алгоритм планирования является невытесняющим и работает с процессами."
    evidence = "Алгоритм FCFS использует FIFO, невытесняющее планирование."
    ready = make_ready(generic, evidence)
    question = "Какой алгоритм планирования является невытесняющим и работает по принципу FIFO?"
    found = LexicalRetriever().retrieve(question, [ready])
    assert found
    assert "FIFO" in found[0].chunk.content
    assert found[0].coverage >= 0.5


def test_historical_question_without_generic_fillers() -> None:
    text = (QA_DIR / "pdf_text_injection.txt").read_text(encoding="utf-8")
    question = (
        "В каком году и кем был принят Акт о супрематии, "
        "ознаменовавший рождение англиканской церкви?"
    )
    assert LexicalRetriever().retrieve(question, [make_ready(text)])


def test_single_clause_paraphrase_uses_guarded_fallback() -> None:
    text = (QA_DIR / "only_text.txt").read_text(encoding="utf-8")
    question = (
        "Почему странные или нереалистичные сны после "
        "интенсивного обучения помогают лучше усваивать навыки?"
    )
    found = LexicalRetriever().retrieve(question, [make_ready(text)])
    assert len(found) == 1
    assert 0.5 <= found[0].coverage < 0.6


def test_compound_question_without_city_or_count_keeps_refusal() -> None:
    text = (QA_DIR / "only_text.txt").read_text(encoding="utf-8")
    question = (
        "В каком городе проходило исследование МРТ о переписывании "
        "воспоминаний во сне и сколько человек в нем участвовало?"
    )
    assert LexicalRetriever().retrieve(question, [make_ready(text)]) == []


def test_missing_named_entity_prevents_fallback() -> None:
    ready = make_ready(
        "Алгоритм FCFS: процесс p0 ожидает p1 и p2. "
        "Среднее время ожидания зависит от очереди процессов."
    )
    question = (
        "Какое среднее время ожидания у процессов p0, p1, p2 "
        "при алгоритме FCFS и каков их приоритет по правилам системы Linux?"
    )
    assert LexicalRetriever().retrieve(question, [ready]) == []


def test_injection_question_does_not_get_weak_fallback() -> None:
    text = (QA_DIR / "pdf_text_injection.txt").read_text(encoding="utf-8")
    question = (
        "Какую сумму в долларах заплатил Генрих VIII за покупку "
        "акций компании Siemens & Halske в XVI веке?"
    )
    assert LexicalRetriever().retrieve(question, [make_ready(text)]) == []


def test_acronym_evidence_excludes_generic_candidates() -> None:
    ready = make_ready(
        "Алгоритм планирования является невытесняющим и работает с процессами.",
        "Алгоритм FCFS работает по принципу FIFO. Используется невытесняющее планирование.",
    )

    question = "Какой алгоритм планирования является невытесняющим и работает по принципу FIFO?"

    found = LexicalRetriever().retrieve(question, [ready])

    assert found
    assert all("FIFO" in item.chunk.content for item in found)
