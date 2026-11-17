"""Build bounded LLM context from verified document chunks."""

import re
from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from app.documents.models import DocumentStatus
from app.retrieval.lexical import (
    TOP_K,
    RankedChunk,
    SearchableDocument,
    _latin_acronyms,
    normalize_stems,
)

# Conservative character guard for MVP; not an exact model-token measurement.
MAX_LLM_CONTEXT_CHARS = 6000

# Add at most the remaining TOP_K slots, without widening document scope.
EXPLANATION_QUESTION = re.compile(
    r"\b(?:почему|зачем|сложн\w*|причин\w*|проблем\w*|объясн\w*)\b|из-за",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class ContextEntry:
    """Exactly the spans of a ranked chunk that were sent to the model."""

    candidate: RankedChunk
    ranges: tuple[tuple[int, int], ...]


@dataclass(frozen=True, slots=True)
class PreparedContext:
    """Text for Ollama plus provenance for answer-aware citations."""

    text: str
    entries: tuple[ContextEntry, ...]


def expand_context_candidates(
    ranked_chunks: Sequence[RankedChunk],
    documents: Sequence[SearchableDocument],
    question: str,
) -> list[RankedChunk]:
    """Add at most adjacent evidence for explanatory questions, within selected scope.

    The lexical TOP_K selection is untouched. Neighbors are only context
    candidates, never search results, and must be valid persisted chunks.
    """
    primary = list(ranked_chunks[:TOP_K])
    if not primary or len(primary) >= TOP_K or EXPLANATION_QUESTION.search(question) is None:
        return primary

    by_block: dict[tuple[UUID, UUID], dict[int, RankedChunk]] = {}
    for selected in documents:
        document = selected.document
        if document.status != DocumentStatus.READY:
            continue
        blocks = {block.id: block for block in selected.result.blocks}
        for chunk in selected.result.chunks:
            block = blocks.get(chunk.block_id)
            if (
                block is None
                or block.document_id != document.id
                or chunk.document_id != document.id
                or not 0 <= chunk.start_char < chunk.end_char <= len(block.content)
                or block.content[chunk.start_char : chunk.end_char] != chunk.content
            ):
                continue
            by_block.setdefault((document.id, block.id), {})[chunk.position] = RankedChunk(
                document=document,
                block=block,
                chunk=chunk,
                coverage=0.0,
                match_count=0,
            )

    terms = set(normalize_stems(question)) | _latin_acronyms(question)
    seen = {(item.document.id, item.chunk.id) for item in primary}
    expanded = list(primary)

    # Prefer the next chunk: explanations often follow a definition or heading.
    for candidate in primary:
        for offset in (1, -1):
            if len(expanded) >= TOP_K:
                return expanded
            neighbor = by_block.get((candidate.document.id, candidate.block.id), {}).get(
                candidate.chunk.position + offset
            )
            if neighbor is None:
                continue
            key = (neighbor.document.id, neighbor.chunk.id)
            if key in seen:
                continue
            neighbor_terms = set(normalize_stems(neighbor.chunk.content)) | (
                _latin_acronyms(neighbor.chunk.content)
            )
            if not (terms & neighbor_terms):
                continue
            seen.add(key)
            expanded.append(neighbor)

    return expanded


def _uncovered_ranges(
    start: int,
    end: int,
    covered: list[tuple[int, int]],
) -> list[tuple[int, int]]:
    """Exclude already included character ranges within one document block."""
    remaining = [(start, end)]

    for old_start, old_end in covered:
        next_remaining = []

        for left, right in remaining:
            if old_end <= left or old_start >= right:
                next_remaining.append((left, right))
            else:
                if left < old_start:
                    next_remaining.append((left, old_start))
                if old_end < right:
                    next_remaining.append((old_end, right))

        remaining = next_remaining

    return remaining


def prepare_llm_context(
    ranked_chunks: Sequence[RankedChunk],
    *,
    max_chars: int = MAX_LLM_CONTEXT_CHARS,
) -> PreparedContext:
    """Select valid, non-duplicated spans without changing source coordinates."""
    if max_chars <= 0:
        raise ValueError("max_chars must be positive")

    parts: list[str] = []
    entries: list[ContextEntry] = []
    used = 0
    covered: dict[tuple[UUID, UUID], list[tuple[int, int]]] = {}

    for candidate in ranked_chunks[:TOP_K]:
        document = candidate.document
        block = candidate.block
        chunk = candidate.chunk

        if document.status != DocumentStatus.READY:
            continue

        if (
            block.document_id != document.id
            or chunk.document_id != document.id
            or chunk.block_id != block.id
            or not 0 <= chunk.start_char < chunk.end_char <= len(block.content)
            or block.content[chunk.start_char : chunk.end_char] != chunk.content
        ):
            continue

        key = (document.id, block.id)
        ranges = _uncovered_ranges(
            chunk.start_char,
            chunk.end_char,
            covered.get(key, []),
        )
        if not ranges:
            continue

        body = "\n".join(block.content[left:right] for left, right in ranges)
        header = f"[document_id={document.id}; chunk_id={chunk.id}]\n"
        part = f"{header}{body}"
        additional = len(part) + (2 if parts else 0)

        # Never silently truncate a passage in the middle of evidence.
        if used + additional > max_chars:
            continue

        parts.append(part)
        entries.append(ContextEntry(candidate=candidate, ranges=tuple(ranges)))
        used += additional
        covered.setdefault(key, []).extend(ranges)

    return PreparedContext(text="\n\n".join(parts), entries=tuple(entries))


def build_llm_context(
    ranked_chunks: Sequence[RankedChunk],
    *,
    max_chars: int = MAX_LLM_CONTEXT_CHARS,
) -> str:
    """Preserve the existing string-returning context builder API."""
    return prepare_llm_context(ranked_chunks, max_chars=max_chars).text
