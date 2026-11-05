"""Deterministic lexical retrieval over persisted document chunks."""

import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol

from app.documents.models import Document, DocumentStatus
from app.processing.models import Chunk, DocumentBlock, ProcessingResult

TOP_K = 3
MIN_COVERAGE = 0.6

STOP_WORDS = frozenset(
    [
        "без",
        "для",
        "если",
        "или",
        "как",
        "какой",
        "когда",
        "который",
        "между",
        "может",
        "над",
        "надо",
        "наш",
        "него",
        "нее",
        "нет",
        "они",
        "она",
        "оно",
        "при",
        "про",
        "сам",
        "свой",
        "так",
        "также",
        "там",
        "тогда",
        "того",
        "тоже",
        "уже",
        "чем",
        "чего",
        "через",
        "что",
        "эта",
        "это",
        "этот",
        "эти",
    ]
)

WORD_PATTERN = re.compile(r"[^\W_]+", re.UNICODE)


def normalize_stems(text: str) -> list[str]:
    """Normalize Unicode words according to the MVP 0.2 contract."""
    normalized = text.lower().replace("ё", "е")

    return [
        word[:5]
        for word in WORD_PATTERN.findall(normalized)
        if len(word) >= 3 and word not in STOP_WORDS
    ]


class SearchableDocument(Protocol):
    """A ready document paired with its persisted processing result."""

    document: Document
    result: ProcessingResult


@dataclass(frozen=True, slots=True)
class RankedChunk:
    """A matching chunk with its original block and ranking metrics."""

    document: Document
    block: DocumentBlock
    chunk: Chunk
    coverage: float
    match_count: int


class LexicalRetriever:
    """Rank stored chunks using deterministic keyword coverage."""

    def retrieve(
        self,
        question: str,
        documents: Iterable[SearchableDocument],
    ) -> list[RankedChunk]:
        """Return up to three chunks with coverage of at least 0.6."""
        question_stems = set(normalize_stems(question))

        if not question_stems:
            return []

        candidates: list[RankedChunk] = []

        for selected in documents:
            document = selected.document

            if document.status != DocumentStatus.READY:
                continue

            blocks_by_id = {block.id: block for block in selected.result.blocks}

            for chunk in selected.result.chunks:
                block = blocks_by_id.get(chunk.block_id)

                if block is None:
                    continue

                if chunk.document_id != document.id or block.document_id != document.id:
                    continue

                chunk_stems = normalize_stems(chunk.content)
                chunk_set = set(chunk_stems)

                matched_stems = question_stems & chunk_set
                coverage = len(matched_stems) / len(question_stems)

                if coverage < MIN_COVERAGE:
                    continue

                match_count = sum(stem in question_stems for stem in chunk_stems)

                candidates.append(
                    RankedChunk(
                        document=document,
                        block=block,
                        chunk=chunk,
                        coverage=coverage,
                        match_count=match_count,
                    )
                )

        # Stable sorting, applied from lowest to highest priority.
        candidates.sort(key=lambda item: item.chunk.position)
        candidates.sort(key=lambda item: item.block.position)
        candidates.sort(key=lambda item: item.document.id)
        candidates.sort(
            key=lambda item: item.document.created_at,
            reverse=True,
        )
        candidates.sort(
            key=lambda item: item.match_count,
            reverse=True,
        )
        candidates.sort(
            key=lambda item: item.coverage,
            reverse=True,
        )

        return candidates[:TOP_K]
