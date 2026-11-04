"""Data models for TXT document blocks, chunks, and processing results."""

from dataclasses import dataclass
from typing import Literal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class DocumentBlock:
    id: UUID
    document_id: UUID
    type: Literal["text"]
    position: int
    content: str
    start_char: int
    end_char: int

    def __post_init__(self) -> None:
        if self.position < 0:
            raise ValueError("Block position cannot be negative")

        if self.type != "text":
            raise ValueError("Unsupported block type")

        if self.start_char < 0 or self.end_char <= self.start_char:
            raise ValueError("Invalid block character range")

        if len(self.content) != self.end_char - self.start_char:
            raise ValueError("Block content length does not match range")


@dataclass(frozen=True, slots=True)
class Chunk:
    id: UUID
    document_id: UUID
    block_id: UUID
    position: int
    content: str
    start_char: int
    end_char: int

    def __post_init__(self) -> None:
        if self.position < 0:
            raise ValueError("Chunk position cannot be negative")

        if self.start_char < 0 or self.end_char <= self.start_char:
            raise ValueError("Invalid chunk character range")

        if len(self.content) != self.end_char - self.start_char:
            raise ValueError("Chunk content length does not match range")


@dataclass(slots=True)
class ProcessingResult:
    document_id: UUID
    blocks: list[DocumentBlock]
    chunks: list[Chunk]
