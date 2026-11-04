"""Tests for token-based TXT chunking and character offsets."""

import pytest

from app.processing.chunking import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    CHUNK_STEP,
    split_into_chunk_ranges,
)
from app.processing.errors import (
    EmptyDocumentError,
    TokenizerContractError,
)


class FakeEncoding:
    """Provide predictable token offsets for tests."""

    def __init__(self, offsets):
        self.offsets = offsets


class FakeTokenizer:
    """Treat each character as one token by default."""

    def __init__(self, offsets=None):
        self._offsets = offsets

    def no_truncation(self):
        pass

    def no_padding(self):
        pass

    def encode(self, text, add_special_tokens=False):
        assert add_special_tokens is False

        if self._offsets is not None:
            return FakeEncoding(self._offsets)

        return FakeEncoding([(i, i + 1) for i in range(len(text))])


@pytest.mark.parametrize(
    ("length", "expected"),
    [
        (1, [(0, 1)]),
        (349, [(0, 349)]),
        (350, [(0, 350)]),
        (351, [(0, 350), (300, 351)]),
        (650, [(0, 350), (300, 650)]),
        (
            651,
            [(0, 350), (300, 650), (600, 651)],
        ),
        (
            951,
            [
                (0, 350),
                (300, 650),
                (600, 950),
                (900, 951),
            ],
        ),
    ],
)
def test_chunk_boundaries(length, expected):
    """Verify exact window boundaries."""

    text = "a" * length
    tokenizer = FakeTokenizer()

    result = split_into_chunk_ranges(text, tokenizer)

    assert result == expected


def test_chunking_constants():
    """Verify the agreed chunking parameters."""

    assert CHUNK_SIZE == 350
    assert CHUNK_OVERLAP == 50
    assert CHUNK_STEP == 300


def test_chunk_ranges_cover_original_text():
    """Verify coverage and overlap for a long document."""

    text = "a" * 1200
    tokenizer = FakeTokenizer()

    ranges = split_into_chunk_ranges(text, tokenizer)

    assert ranges[0][0] == 0
    assert ranges[-1][1] == len(text)

    for start, end in ranges:
        assert 0 <= start < end <= len(text)
        assert end - start <= CHUNK_SIZE

    for previous, current in zip(ranges, ranges[1:]):
        assert current[0] <= previous[1]
        assert current[0] < previous[1]


def test_whitespace_is_preserved():
    """Include original whitespace in character ranges."""

    text = " A B C "

    tokenizer = FakeTokenizer(offsets=[(1, 2), (3, 4), (5, 6)])

    ranges = split_into_chunk_ranges(text, tokenizer)

    assert ranges == [(0, len(text))]
    assert text[ranges[0][0] : ranges[0][1]] == text


@pytest.mark.parametrize(
    "offsets",
    [
        [(-1, 1)],
        [(0, 10)],
        [(1, 2), (0, 1)],
        [(0, 3), (2, 4)],
        [(0, 0)],
    ],
)
def test_invalid_tokenizer_offsets(offsets):
    """Reject invalid, overlapping or unusable offsets."""

    tokenizer = FakeTokenizer(offsets=offsets)

    with pytest.raises(TokenizerContractError):
        split_into_chunk_ranges("abcd", tokenizer)


def test_empty_document_rejected():
    """Reject whitespace-only input."""

    tokenizer = FakeTokenizer()

    with pytest.raises(EmptyDocumentError):
        split_into_chunk_ranges(" \n\t ", tokenizer)


def test_zero_length_offsets_ignored():
    """Ignore zero-length offsets when valid tokens exist."""

    tokenizer = FakeTokenizer(offsets=[(0, 0), (0, 1), (1, 2)])

    assert split_into_chunk_ranges("ab", tokenizer) == [(0, 2)]
