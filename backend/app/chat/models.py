"""Request, response and source models for the chat API."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    document_ids: list[UUID] | None = None

    @field_validator("question", mode="before")
    @classmethod
    def strip_question(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("document_ids")
    @classmethod
    def reject_empty_scope(cls, value: list[UUID] | None) -> list[UUID] | None:
        if value is not None and not value:
            raise ValueError("document_ids cannot be empty")
        return value


class Source(BaseModel):
    document_id: UUID
    filename: str
    block_id: UUID
    chunk_id: UUID
    start_char: int
    end_char: int
    quote: str


class ChatResponse(BaseModel):
    status: Literal["answered", "partial", "insufficient_info"]
    answer: str
    sources: list[Source]
