
"""Process TXT documents into blocks and overlapping chunks."""

from uuid import UUID, uuid5

from .chunking import split_into_chunk_ranges
from .models import Chunk, DocumentBlock, ProcessingResult
from .tokenizer import load_tokenizer
from .txt import decode_txt


def process_txt(
    data: bytes,
    document_id: UUID,
) -> ProcessingResult:
    """Decode TXT data and create deterministic blocks and chunks."""

    text = decode_txt(data)

    block_id = uuid5(document_id, "block:0")

    block = DocumentBlock(
        id=block_id,
        document_id=document_id,
        type="text",
        position=0,
        content=text,
        start_char=0,
        end_char=len(text),
    )

    tokenizer = load_tokenizer()
    ranges = split_into_chunk_ranges(text, tokenizer)

    chunks: list[Chunk] = []

    for position, (start_char, end_char) in enumerate(ranges):
        chunk = Chunk(
            id=uuid5(document_id, f"chunk:{position}"),
            document_id=document_id,
            block_id=block.id,
            position=position,
            content=block.content[start_char:end_char],
            start_char=start_char,
            end_char=end_char,
        )

        chunks.append(chunk)

    return ProcessingResult(
        document_id=document_id,
        blocks=[block],
        chunks=chunks,
    )
