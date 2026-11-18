"""Document processing service and lifecycle management."""

import logging
from uuid import UUID

from app.processing import (
    EmptyDocumentError,
    InvalidTxtEncodingError,
    process_txt,
)

from .repository import DocumentRepository

logger = logging.getLogger(__name__)


class DocumentService:
    """Coordinate TXT processing and document status transitions."""

    def __init__(self, repository: DocumentRepository) -> None:
        self._repository = repository

    def _record_failure(
        self,
        document_id: UUID,
        code: str,
        message: str,
    ) -> None:
        """Persist a failure, logging storage errors without crashing the task."""
        try:
            self._repository.fail(document_id, code, message)
        except Exception:
            logger.exception(
                "Could not save failure status for document %s",
                document_id,
            )

    def process_document(self, document_id: UUID) -> None:
        """Process a stored TXT and persist its result or failure."""
        try:
            if not self._repository.mark_processing(document_id):
                return

            data = self._repository.read_original(document_id)

            if data is None:
                raise FileNotFoundError("Original document file is missing")

            result = process_txt(data, document_id)

            self._repository.complete(document_id, result)

        except InvalidTxtEncodingError as exc:
            self._record_failure(
                document_id,
                "invalid_encoding",
                str(exc),
            )

        except EmptyDocumentError as exc:
            self._record_failure(
                document_id,
                "empty_document",
                str(exc),
            )

        except Exception:
            logger.exception(
                "Document processing failed for %s",
                document_id,
            )
            self._record_failure(
                document_id,
                "processing_failed",
                "Не удалось обработать документ.",
            )
