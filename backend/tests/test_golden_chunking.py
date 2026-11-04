"""Golden tests for TXT chunking with the pinned tokenizer."""

import json
from pathlib import Path
from uuid import UUID

from app.processing import process_txt
from app.processing.chunking import split_into_chunk_ranges
from app.processing.tokenizer import load_tokenizer

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "synthetic_long_txt.json"

DOCUMENT_ID = UUID("12345678-1234-5678-1234-567812345678")


def test_synthetic_long_txt_golden() -> None:
    """Verify exact offsets produced by the pinned tokenizer."""

    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    text = fixture["text_unit"] * fixture["repeat"]

    expected_ranges = [tuple(item) for item in fixture["expected_ranges"]]

    tokenizer = load_tokenizer()

    actual_ranges = split_into_chunk_ranges(
        text,
        tokenizer,
    )

    assert actual_ranges == expected_ranges

    result = process_txt(
        text.encode("utf-8"),
        DOCUMENT_ID,
    )

    assert len(result.blocks) == 1
    assert len(result.chunks) == len(expected_ranges)

    for chunk, (start, end) in zip(
        result.chunks,
        expected_ranges,
    ):
        assert chunk.start_char == start
        assert chunk.end_char == end
        assert chunk.content == text[start:end]
