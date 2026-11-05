"""Document scope selection for chat requests."""

from dataclasses import dataclass
from uuid import UUID

from app.documents.models import Document, DocumentStatus
from app.documents.repository import DocumentRepository
from app.llm.adapter import LLMAdapter
from app.processing.models import ProcessingResult


@dataclass(frozen=True, slots=True)
class ReadyDocument:
    document: Document
    result: ProcessingResult


class ChatServiceError(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


class ChatService:
    """Coordinate document selection, retrieval and answer generation."""

    def __init__(
        self,
        repository: DocumentRepository,
        llm_adapter: LLMAdapter,
    ) -> None:
        self._repository = repository
        self._llm_adapter = llm_adapter

    def select_documents(
        self,
        document_ids: list[UUID] | None,
    ) -> list[ReadyDocument]:
        """Return stored results belonging to the requested ready documents."""

        if document_ids is None:
            documents = self._repository.list(status=DocumentStatus.READY)

            selected = []

            for document in documents:
                result = self._repository.get_result(document.id)

                if result is not None:
                    selected.append(ReadyDocument(document=document, result=result))

            if not selected:
                raise ChatServiceError(
                    409,
                    "no_ready_documents",
                    "Нет готовых документов для поиска.",
                )

            return selected

        if not document_ids:
            raise ChatServiceError(
                422,
                "invalid_question",
                "Необходимо выбрать хотя бы один документ.",
            )

        selected = []

        for document_id in dict.fromkeys(document_ids):
            document = self._repository.get(document_id)

            if document is None:
                raise ChatServiceError(
                    404,
                    "document_not_found",
                    "Документ не найден.",
                )

            if document.status != DocumentStatus.READY:
                raise ChatServiceError(
                    409,
                    "document_not_ready",
                    "Документ не готов к поиску.",
                )

            result = self._repository.get_result(document_id)

            if result is None:
                current = self._repository.get(document_id)

                if current is None:
                    raise ChatServiceError(
                        404,
                        "document_not_found",
                        "Документ не найден.",
                    )

                raise ChatServiceError(
                    409,
                    "document_not_ready",
                    "Результат обработки документа недоступен.",
                )

            selected.append(ReadyDocument(document=document, result=result))

        return selected
