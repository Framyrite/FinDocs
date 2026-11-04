"""Split TXT content into overlapping token-based character ranges."""

from tokenizers import Tokenizer

from .errors import EmptyDocumentError, TokenizerContractError

CHUNK_SIZE = 350
CHUNK_OVERLAP = 50
CHUNK_STEP = CHUNK_SIZE - CHUNK_OVERLAP


def split_into_chunk_ranges(
    text: str,
    tokenizer: Tokenizer,
) -> list[tuple[int, int]]:
    """Return character ranges for overlapping token windows."""
    if not text.strip():
        raise EmptyDocumentError("TXT document is empty or contains only whitespace")

    tokenizer.no_truncation()
    tokenizer.no_padding()

    encoding = tokenizer.encode(
        text,
        add_special_tokens=False,
    )

    offsets: list[tuple[int, int]] = []

    for start, end in encoding.offsets:
        # Empty token offsets are ignored by the contract.
        if start == end:
            continue

        if not 0 <= start < end <= len(text):
            raise TokenizerContractError("Tokenizer returned an invalid character range")

        if offsets and start < offsets[-1][1]:
            raise TokenizerContractError("Tokenizer offsets are overlapping or out of order")

        offsets.append((start, end))

    if not offsets:
        raise TokenizerContractError("Tokenizer returned no valid tokens")

    token_count = len(offsets)

    if token_count <= CHUNK_SIZE:
        return [(0, len(text))]

    ranges: list[tuple[int, int]] = []

    for token_start in range(0, token_count, CHUNK_STEP):
        token_end = min(
            token_start + CHUNK_SIZE,
            token_count,
        )

        start_char = 0 if token_start == 0 else offsets[token_start][0]

        end_char = len(text) if token_end == token_count else offsets[token_end - 1][1]

        ranges.append((start_char, end_char))

        if token_end == token_count:
            break

    return ranges
