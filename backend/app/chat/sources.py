"""Build verifiable citations from ranked document chunks."""

import re
from collections.abc import Sequence

from app.chat.models import Source
from app.retrieval.lexical import (
    TOP_K,
    WORD_PATTERN,
    RankedChunk,
    normalize_stems,
)

MAX_QUOTE_LENGTH = 300
SENTENCE_PATTERN = re.compile(r"[^.!?\r\n]+[.!?]?")


def _matching_positions(
    sentence: str,
    question_stems: set[str],
) -> list[int]:
    """Find positions of matching words in the unmodified sentence."""
    positions: list[int] = []

    for word in WORD_PATTERN.finditer(sentence):
        stems = normalize_stems(word.group())

        if stems and stems[0] in question_stems:
            positions.append(word.start())

    return positions


def _quote_from_chunk(
    chunk_text: str,
    question_stems: set[str],
) -> tuple[str, int] | None:
    """Return the best quote and its offset within the chunk."""
    best_sentence: re.Match[str] | None = None
    best_positions: list[int] = []

    for sentence in SENTENCE_PATTERN.finditer(chunk_text):
        positions = _matching_positions(
            sentence.group(),
            question_stems,
        )

        if len(positions) > len(best_positions):
            best_sentence = sentence
            best_positions = positions

    if best_sentence is None or not best_positions:
        return None

    sentence_text = best_sentence.group()
    quote_start = 0

    if len(sentence_text) > MAX_QUOTE_LENGTH:
        quote_start = min(
            max(0, best_positions[0] - 100),
            len(sentence_text) - MAX_QUOTE_LENGTH,
        )

    quote = sentence_text[quote_start : quote_start + MAX_QUOTE_LENGTH]

    offset_in_chunk = best_sentence.start() + quote_start

    return quote, offset_in_chunk


def build_sources(
    ranked_chunks: Sequence[RankedChunk],
    question: str,
) -> list[Source]:
    """Create real sources with absolute Unicode character offsets."""
    question_stems = set(normalize_stems(question))

    if not question_stems:
        return []

    sources: list[Source] = []
    seen_ranges: set[tuple[object, int, int]] = set()

    for candidate in ranked_chunks[:TOP_K]:
        block = candidate.block
        chunk = candidate.chunk
        document = candidate.document

        if (
            block.document_id != document.id
            or chunk.document_id != document.id
            or chunk.block_id != block.id
        ):
            continue

        # The saved chunk must exactly match its range in the saved block.
        if block.content[chunk.start_char : chunk.end_char] != chunk.content:
            continue

        selected = _quote_from_chunk(
            chunk.content,
            question_stems,
        )

        if selected is None:
            continue

        quote, offset_in_chunk = selected

        start_char = block.start_char + chunk.start_char + offset_in_chunk
        end_char = start_char + len(quote)

        range_key = (document.id, start_char, end_char)

        if range_key in seen_ranges:
            continue

        seen_ranges.add(range_key)

        sources.append(
            Source(
                document_id=document.id,
                filename=document.filename,
                block_id=block.id,
                chunk_id=chunk.id,
                start_char=start_char,
                end_char=end_char,
                quote=quote,
            )
        )

    return sources
