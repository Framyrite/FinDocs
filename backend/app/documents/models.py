"""Document metadata and processing statuses."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID


class DocumentStatus(StrEnum):
    """Possible states of a document during its lifecycle."""

    UPLOADED = "uploaded"
    PROCESSING = "processing"
    READY = "ready"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class Document:
    """Metadata for a locally stored TXT document."""

    id: UUID
    filename: str
    size_bytes: int
    created_at: datetime
    format: Literal["txt"] = "txt"
    status: DocumentStatus = DocumentStatus.UPLOADED
    error_code: str | None = None
    error_message: str | None = None
