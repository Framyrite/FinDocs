"""Deterministic lexical retrieval over persisted document chunks."""

import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol

from app.documents.models import Document, DocumentStatus
from app.processing.models import Chunk, DocumentBlock, ProcessingResult

TOP_K = 3
MIN_COVERAGE = 0.6
FALLBACK_COVERAGE = 0.5
MIN_FALLBACK_MATCHES = 3

# Query-only grammatical terms. Stored chunks keep their original normalization.
QUERY_FILLER_STEMS = frozenset({"был", "были", "было", "каком", "кем", "году"})
ROMAN_DIGITS = frozenset("IVXLCDM")
ACRONYM_WORD = re.compile(r"([A-Z]{2,5})(?:[1-9])?", re.ASCII)

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


def _latin_acronyms(text: str) -> set[str]:
    """Find Latin abbreviations, including a trailing one-digit footnote."""
    acronyms = set()
    for word in WORD_PATTERN.findall(text):
        match = ACRONYM_WORD.fullmatch(word)
        if match is None:
            continue
        acronym = match.group(1)
        if not set(acronym) <= ROMAN_DIGITS:
            acronyms.add(acronym.lower())
    return acronyms


def _missing_named_terms(question: str, corpus_text: str) -> bool:
    """Avoid fallback when an explicitly named Latin entity is absent."""
    corpus_lower = corpus_text.casefold()
    return any(
        word.casefold() not in corpus_lower
        for word in WORD_PATTERN.findall(question)
        if len(word) >= 3 and word.isascii() and word.isalpha() and word.istitle()
    )


def _is_compound(question: str) -> bool:
    """Treat coordinated questions conservatively during fallback."""
    return "&" in question or "и" in [word.casefold() for word in WORD_PATTERN.findall(question)]


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
    """Rank trusted TXT chunks with strict and guarded fallback passes."""

    def retrieve(
        self,
        question: str,
        documents: Iterable[SearchableDocument],
    ) -> list[RankedChunk]:
        """Prefer 0.6 coverage; expand only with multiple meaningful matches."""
        acronyms = _latin_acronyms(question)
        question_stems = (set(normalize_stems(question)) - QUERY_FILLER_STEMS) | acronyms

        if not question_stems:
            return []

        # Materialize the iterable once; scope and readiness are never expanded.
        valid_chunks: list[tuple[Document, DocumentBlock, Chunk, list[str]]] = []
        for selected in documents:
            document = selected.document
            if document.status != DocumentStatus.READY:
                continue

            blocks_by_id = {block.id: block for block in selected.result.blocks}
            for chunk in selected.result.chunks:
                block = blocks_by_id.get(chunk.block_id)
                if (
                    block is None
                    or chunk.document_id != document.id
                    or block.document_id != document.id
                ):
                    continue
                # Never rank corrupted chunk text as evidence.
                if block.content[chunk.start_char : chunk.end_char] != chunk.content:
                    continue

                terms = normalize_stems(chunk.content)
                for acronym in _latin_acronyms(chunk.content):
                    if acronym not in terms:
                        terms.append(acronym)
                valid_chunks.append((document, block, chunk, terms))

        if not valid_chunks:
            return []

        named_term_missing = _missing_named_terms(
            question,
            "\n".join(chunk.content for _, _, chunk, _ in valid_chunks),
        )
        compound = _is_compound(question)
        strict: list[RankedChunk] = []
        fallback: list[RankedChunk] = []
        anchor_hits: dict[tuple[object, object], int] = {}

        for document, block, chunk, terms in valid_chunks:
            matched = question_stems & set(terms)
            if not matched:
                continue

            coverage = len(matched) / len(question_stems)
            count = sum(term in question_stems for term in terms)
            acronym_hits = len(acronyms & matched)
            result = RankedChunk(
                document=document,
                block=block,
                chunk=chunk,
                coverage=coverage,
                match_count=count,
            )
            anchor_hits[(document.id, chunk.id)] = acronym_hits

            if coverage >= MIN_COVERAGE:
                strict.append(result)
            elif (
                coverage >= FALLBACK_COVERAGE
                and len(matched) >= MIN_FALLBACK_MATCHES
                and not named_term_missing
                and (
                    acronym_hits == len(acronyms)
                    if acronyms and compound
                    else acronym_hits > 0 or not compound
                )
            ):
                fallback.append(result)

        # Keep strict results, but allow a missing acronym's evidence to enter
        # the pool even when generic strict matches exist (e.g. FIFO vs SJF).
        best_strict_acronyms = max(
            (anchor_hits[(item.document.id, item.chunk.id)] for item in strict),
            default=0,
        )
        use_fallback = not strict or (bool(acronyms) and best_strict_acronyms < len(acronyms))

        candidates = strict + (fallback if use_fallback else [])

        # Prefer explicitly requested acronyms over generic keyword matches.
        if acronyms:
            anchored = [
                item for item in candidates if anchor_hits[(item.document.id, item.chunk.id)] > 0
            ]
            if anchored:
                candidates = anchored

        # Stable sorting, applied from lowest to highest priority.
        candidates.sort(key=lambda item: item.chunk.position)
        candidates.sort(key=lambda item: item.block.position)
        candidates.sort(key=lambda item: item.document.id)
        candidates.sort(key=lambda item: item.document.created_at, reverse=True)
        candidates.sort(key=lambda item: item.match_count, reverse=True)
        candidates.sort(key=lambda item: item.coverage, reverse=True)
        if acronyms:
            candidates.sort(
                key=lambda item: anchor_hits[(item.document.id, item.chunk.id)],
                reverse=True,
            )

        return candidates[:TOP_K]
