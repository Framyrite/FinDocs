"""Tests for UTF-8 TXT decoding and processing results."""

from uuid import UUID, uuid5

import pytest

from app.processing import (
    EmptyDocumentError,
    InvalidTxtEncodingError,
    decode_txt,
    process_txt,
)

DOCUMENT_ID = UUID("12345678-1234-5678-1234-567812345678")


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        (b"Hello", "Hello"),
        ("Привет!".encode(), "Привет!"),
        (b"\xef\xbb\xbfHello", "Hello"),
        (b"Line 1\r\nLine 2\n", "Line 1\r\nLine 2\n"),
        ("Текст 👋📄".encode(), "Текст 👋📄"),
    ],
)
def test_decode_valid_txt(data: bytes, expected: str) -> None:
    assert decode_txt(data) == expected


@pytest.mark.parametrize(
    "data",
    [
        b"",
        b"   ",
        b"\n\r\n\t",
        b"\xef\xbb\xbf",
        b" \n\t ",
    ],
)
def test_decode_empty_txt(data: bytes) -> None:
    with pytest.raises(EmptyDocumentError):
        decode_txt(data)


@pytest.mark.parametrize(
    "data",
    [
        b"\xff",
        b"\xff\xfe",
        b"\xc3\x28",
    ],
)
def test_decode_invalid_utf8(data: bytes) -> None:
    with pytest.raises(InvalidTxtEncodingError):
        decode_txt(data)


def test_process_short_txt() -> None:
    text = "  Привет, FinDocs! 👋\r\n"

    result = process_txt(
        text.encode("utf-8"),
        DOCUMENT_ID,
    )

    assert result.document_id == DOCUMENT_ID
    assert len(result.blocks) == 1
    assert len(result.chunks) == 1

    block = result.blocks[0]
    chunk = result.chunks[0]

    assert block.document_id == DOCUMENT_ID
    assert block.type == "text"
    assert block.position == 0
    assert block.content == text
    assert block.start_char == 0
    assert block.end_char == len(text)

    assert chunk.document_id == DOCUMENT_ID
    assert chunk.block_id == block.id
    assert chunk.position == 0
    assert chunk.content == text
    assert chunk.start_char == 0
    assert chunk.end_char == len(text)


def test_process_long_txt() -> None:
    text = "Привет, FinDocs! 👋\r\n" * 100

    result = process_txt(
        text.encode("utf-8"),
        DOCUMENT_ID,
    )

    assert len(result.blocks) == 1
    assert len(result.chunks) > 1

    block = result.blocks[0]

    assert block.content == text
    assert result.chunks[0].start_char == 0
    assert result.chunks[-1].end_char == len(text)

    for position, chunk in enumerate(result.chunks):
        assert chunk.position == position
        assert chunk.document_id == DOCUMENT_ID
        assert chunk.block_id == block.id

        assert 0 <= chunk.start_char < chunk.end_char <= len(text)

        assert chunk.content == text[chunk.start_char : chunk.end_char]

        if position > 0:
            previous = result.chunks[position - 1]
            assert chunk.start_char < previous.end_char


def test_processing_is_deterministic() -> None:
    data = ("FinDocs 📄\n" * 100).encode("utf-8")

    first = process_txt(data, DOCUMENT_ID)
    second = process_txt(data, DOCUMENT_ID)

    assert first == second

    block_ids = [block.id for block in first.blocks]
    chunk_ids = [chunk.id for chunk in first.chunks]

    assert len(block_ids) == len(set(block_ids))
    assert len(chunk_ids) == len(set(chunk_ids))


def test_processing_rejects_invalid_input() -> None:
    with pytest.raises(InvalidTxtEncodingError):
        process_txt(b"\xff\xfe", DOCUMENT_ID)

    with pytest.raises(EmptyDocumentError):
        process_txt(b" \n\t ", DOCUMENT_ID)


def test_processing_uuid5_identifiers() -> None:
    """Verify deterministic UUID5 identifiers for blocks and chunks."""
    text = "Привет, FinDocs! 👋\r\n" * 100
    data = text.encode("utf-8")

    result = process_txt(data, DOCUMENT_ID)

    block = result.blocks[0]

    assert block.id == uuid5(DOCUMENT_ID, "block:0")

    for position, chunk in enumerate(result.chunks):
        assert chunk.id == uuid5(
            DOCUMENT_ID,
            f"chunk:{position}",
        )

        assert chunk.document_id == DOCUMENT_ID
        assert chunk.block_id == block.id
        assert chunk.position == position

    assert len({chunk.id for chunk in result.chunks}) == len(result.chunks)

    other_document_id = UUID("87654321-4321-5678-4321-876543218765")

    other_result = process_txt(
        data,
        other_document_id,
    )

    assert other_result.blocks[0].id != block.id

    print("OK: deterministic UUID5 identifiers")
