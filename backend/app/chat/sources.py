"""Build verifiable citations from ranked document chunks."""

import re
from collections.abc import Sequence

from app.chat.context import PreparedContext
from app.chat.models import Source
from app.retrieval.lexical import (
    TOP_K,
    WORD_PATTERN,
    RankedChunk,
    _latin_acronyms,
    normalize_stems,
)

INSTRUCTION_QUOTE_PATTERN = re.compile(
    r"\bсистемное\s+правило\s*:"
    r"|\b(?:игнорируй|проигнорируй)\b[^.!?\n]{0,120}\b(?:факт|инструкц|правил)\w*"
    r"|\b(?:ответь|выдай)\b[^.!?\n]{0,70}\b\d{2,}\b",
    re.IGNORECASE,
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
        stems = _answer_terms(word.group())

        if stems & question_stems:
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
    question_stems = _answer_terms(question)

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


def _answer_sentence_ranges(text: str) -> list[tuple[int, int]]:
    """Locate sentence-like ranges, keeping dates such as '1534 г.' intact."""
    spans: list[tuple[int, int]] = []
    left = 0

    def append_span(right: int) -> None:
        nonlocal left
        start = left
        end = right
        while start < end and text[start].isspace():
            start += 1
        while end > start and text[end - 1].isspace():
            end -= 1
        if end > start:
            spans.append((start, end))
        left = right

    for index, char in enumerate(text):
        if char in "\r\n":
            append_span(index)
            left = index + 1
            continue
        if char not in ".!?":
            continue
        if char == "." and re.search(r"\b\d{4}\s+г$", text[max(0, index - 12) : index]):
            continue
        if index + 1 < len(text) and not text[index + 1].isspace():
            continue
        append_span(index + 1)

    append_span(len(text))
    return spans


def _answer_terms(text: str) -> set[str]:
    """Use normal stems plus two-letter uppercase technical abbreviations."""
    return set(normalize_stems(text)) | _latin_acronyms(text)


def _quote_windows(
    text: str,
    left: int,
    right: int,
    focused_terms: set[str],
) -> list[tuple[int, int]]:
    """Extract exact ranges, including focused windows for long sentences."""
    if right - left <= MAX_QUOTE_LENGTH:
        return [(left, right)]

    windows: set[tuple[int, int]] = set()
    for word in WORD_PATTERN.finditer(text, left, right):
        if not (_answer_terms(word.group()) & focused_terms):
            continue
        start = min(max(left, word.start() - 90), right - MAX_QUOTE_LENGTH)
        end = start + MAX_QUOTE_LENGTH
        # Do not show clipped words if a 300-character window cuts through one.
        if start > left and text[start - 1].isalnum() and text[start].isalnum():
            while start < end and text[start].isalnum():
                start += 1
            while start < end and text[start].isspace():
                start += 1
        if end < right and text[end - 1].isalnum() and text[end].isalnum():
            while end > start and text[end - 1].isalnum():
                end -= 1
            while end > start and text[end - 1].isspace():
                end -= 1
        if end > start:
            windows.add((start, end))

    return sorted(windows)


def build_answer_sources(
    prepared: PreparedContext,
    question: str,
    answer: str,
) -> list[Source]:
    """Choose exact, answer-relevant quotes strictly from transmitted spans.

    Lexical similarity ranks excerpts; it does not prove logical entailment.
    """
    answer_terms = _answer_terms(answer)
    question_terms = _answer_terms(question)
    question_acronyms = _latin_acronyms(question)
    first_answer_sentence = _answer_sentence_ranges(answer)
    first_answer = (
        answer[first_answer_sentence[0][0] : first_answer_sentence[0][1]]
        if first_answer_sentence
        else answer
    )
    key_acronyms = question_acronyms | _latin_acronyms(first_answer)
    focused_terms = answer_terms - question_terms
    number_pattern = re.compile(r"(?<!\w)\d{2,}(?!\w)")
    answer_numbers = set(number_pattern.findall(answer))
    if not answer_terms:
        return []

    # Explanatory phrasing helps questions asking for a cause, not just a topic.
    why_question = bool(re.search(r"\b(почему|зачем|сложно|причина)\b|из-за", question.lower()))
    explanatory = frozenset({"невоз", "сложн", "позво", "необх", "благо", "поэто", "причи"})
    quoted_phrases = re.findall(r"[«\"]([^»\"]+)[»\"]", question)
    named_terms = set().union(*(_answer_terms(item) for item in quoted_phrases))

    # (candidate, absolute block-relative start/end, present answer terms, score)
    options: list[tuple[RankedChunk, int, int, set[str], float]] = []
    for entry in prepared.entries:
        candidate = entry.candidate
        block = candidate.block
        for range_start, range_end in entry.ranges:
            text = block.content[range_start:range_end]
            sentences = _answer_sentence_ranges(text)
            for index in range(len(sentences)):
                for step in (1, 2, 3):
                    if index + step > len(sentences):
                        break
                    left = sentences[index][0]
                    right = sentences[index + step - 1][1]
                    # Keep adjacent sentences from one paragraph only.
                    if "\n" in text[left:right]:
                        break
                    for start, end in _quote_windows(
                        text, left, right, focused_terms or answer_terms
                    ):
                        quote = text[start:end]
                        if INSTRUCTION_QUOTE_PATTERN.search(quote):
                            continue
                        quote_terms = _answer_terms(quote)
                        if question_acronyms and not (
                            key_acronyms & quote_terms
                            or (question_terms & answer_terms & quote_terms)
                            or (answer_numbers & set(number_pattern.findall(quote)))
                        ):
                            continue
                        terms = quote_terms & answer_terms
                        exclusive = terms & focused_terms
                        raw_score = 4 * len(exclusive) + len(terms)
                        if why_question:
                            raw_score += 7 * min(2, len(quote_terms & explanatory))
                        if named_terms and named_terms <= quote_terms:
                            raw_score += 12
                        # Normalize for length: a short precise explanation must
                        # not lose to a long list of unrelated keyword mentions.
                        score = raw_score * 200 / max(160, len(quote))
                        if score:
                            options.append(
                                (
                                    candidate,
                                    range_start + start,
                                    range_start + end,
                                    terms,
                                    score,
                                )
                            )

    # When the question quotes a term, prefer evidence naming that term.
    options.sort(
        key=lambda item: (
            -int(
                bool(named_terms)
                and named_terms <= _answer_terms(item[0].block.content[item[1] : item[2]])
            ),
            -item[4],
            item[1],
            str(item[0].chunk.id),
        )
    )

    sources: list[Source] = []
    covered_terms: set[str] = set()
    seen_ranges: set[tuple[object, int, int]] = set()

    def add_option(option: tuple[RankedChunk, int, int, set[str], float]) -> bool:
        candidate, left, right, terms, _ = option
        doc_start = candidate.block.start_char + left
        doc_end = candidate.block.start_char + right
        key = (candidate.document.id, doc_start, doc_end)
        if key in seen_ranges:
            return False
        if any(
            source.document_id == candidate.document.id
            and max(source.start_char, doc_start) < min(source.end_char, doc_end)
            and min(source.end_char, doc_end) - max(source.start_char, doc_start)
            > 0.7 * min(source.end_char - source.start_char, doc_end - doc_start)
            for source in sources
        ):
            return False

        seen_ranges.add(key)
        sources.append(
            Source(
                document_id=candidate.document.id,
                filename=candidate.document.filename,
                block_id=candidate.block.id,
                chunk_id=candidate.chunk.id,
                start_char=doc_start,
                end_char=doc_end,
                quote=candidate.block.content[left:right],
            )
        )
        covered_terms.update(terms)
        return True

    # Prioritize numerical facts, even when already present in the question.
    # Only the already-validated, actually transmitted spans are eligible.
    if answer_numbers:
        number_options = []
        for option in options:
            candidate, left, right, _, _ = option
            quote_numbers = set(number_pattern.findall(candidate.block.content[left:right]))
            if quote_numbers & answer_numbers:
                number_options.append((option, quote_numbers))
        number_options.sort(key=lambda item: (-len(item[1] & answer_numbers), -item[0][4]))

        remaining_numbers = answer_numbers.copy()
        for option, quote_numbers in number_options:
            if not remaining_numbers or len(sources) >= TOP_K:
                break
            if remaining_numbers & quote_numbers and add_option(option):
                remaining_numbers -= quote_numbers

    # Reserve evidence for acronyms requested by the user and those that the
    # answer introduces (for D02: FIFO in the question and FCFS in the answer).
    introduced = key_acronyms - question_acronyms
    if question_acronyms and introduced:
        ordered = sorted(question_acronyms) + sorted(introduced)
        for acronym in ordered:
            if any(acronym in _answer_terms(source.quote) for source in sources):
                continue
            anchored = [
                option
                for option in options
                if acronym in _answer_terms(option[0].block.content[option[1] : option[2]])
            ]
            if any(option[2] - option[1] >= 100 for option in anchored):
                anchored = [option for option in anchored if option[2] - option[1] >= 100]
            for option in anchored:
                if add_option(option):
                    break

        # Spend a free slot on facts from the question that were not yet cited.
        remaining = (question_terms & answer_terms) - covered_terms
        if len(sources) < TOP_K and remaining:
            for option in sorted(
                options,
                key=lambda item: (-len(item[3] & remaining), -item[4]),
            ):
                if option[3] & remaining and add_option(option):
                    break

    for option in options:
        if len(sources) >= TOP_K:
            break
        _, _, _, terms, _ = option
        novel = terms - covered_terms
        if sources and not novel:
            continue
        if sources and not ((novel & focused_terms) or len(novel) >= 2):
            continue
        add_option(option)

    return sources


def build_context_sources(prepared: PreparedContext, question: str) -> list[Source]:
    """Fallback to query citations restricted to what the model actually read."""
    question_terms = set(normalize_stems(question))
    if not question_terms:
        return []

    sources: list[Source] = []
    for entry in prepared.entries:
        candidate = entry.candidate
        block = candidate.block
        for left, right in entry.ranges:
            text = block.content[left:right]
            matched = _quote_from_chunk(text, question_terms)
            if matched is None:
                continue
            quote, offset = matched
            start = block.start_char + left + offset
            sources.append(
                Source(
                    document_id=candidate.document.id,
                    filename=candidate.document.filename,
                    block_id=block.id,
                    chunk_id=candidate.chunk.id,
                    start_char=start,
                    end_char=start + len(quote),
                    quote=quote,
                )
            )
            break
        if len(sources) >= TOP_K:
            break
    return sources


def citations_support_answer(question: str, answer: str, sources: Sequence[Source]) -> bool:
    """Require answer-specific citation overlap, including new numerical facts.

    Lexical overlap is not a proof of semantic entailment.
    """
    if not sources:
        return False

    quoted = "\n".join(source.quote for source in sources)
    focused = _answer_terms(answer) - _answer_terms(question)
    cited_terms = _answer_terms(quoted)
    if focused and not focused & cited_terms:
        return False

    # Prevent a model's invented monetary amount/year from acquiring a
    # decorative citation about the question's topic.
    number_pattern = r"(?<!\w)\d{2,}(?!\w)"
    numbers = set(re.findall(number_pattern, answer))
    cited_numbers = set(re.findall(number_pattern, quoted))
    return numbers <= cited_numbers
