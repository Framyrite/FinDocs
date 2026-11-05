"""Document processing service and lifecycle management."""

from uuid import UUID

from app.processing import (
    EmptyDocumentError,
    InvalidTxtEncodingError,
    process_txt,
)

from .repository import DocumentRepository


class DocumentService:
    """Coordinate TXT processing and document status transitions."""

    def __init__(self, repository: DocumentRepository) -> None:
        self._repository = repository

    def process_document(self, document_id: UUID) -> None:
        """Process a stored document and persist its result or failure."""
        if not self._repository.mark_processing(document_id):
            return

        try:
            data = self._repository.read_original(document_id)

            if data is None:
                raise FileNotFoundError("Original document file is missing")

            result = process_txt(data, document_id)

        except InvalidTxtEncodingError as exc:
            self._repository.fail(
                document_id,
                "invalid_encoding",
                str(exc),
            )

        except EmptyDocumentError as exc:
            self._repository.fail(
                document_id,
                "empty_document",
                str(exc),
            )

        except Exception:
            self._repository.fail(
                document_id,
                "processing_failed",
                "Document processing failed",
            )

        else:
            self._repository.complete(document_id, result)
