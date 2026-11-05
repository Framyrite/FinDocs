"""Document scope, retrieval and grounded chat answers."""

from dataclasses import dataclass
from uuid import UUID

from app.chat.models import ChatResponse
from app.chat.sources import build_sources
from app.documents.models import Document, DocumentStatus
from app.documents.repository import DocumentRepository
from app.llm.adapter import LLMAdapter
from app.processing.models import ProcessingResult
from app.retrieval.lexical import LexicalRetriever

INSUFFICIENT_INFO_ANSWER = (
    "В выбранных материалах не удалось найти достаточную информацию для ответа."
)


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
    """Coordinate document scope, lexical search and the LLM adapter."""

    def __init__(
        self,
        repository: DocumentRepository,
        llm_adapter: LLMAdapter,
    ) -> None:
        self._repository = repository
        self._llm_adapter = llm_adapter
        self._retriever = LexicalRetriever()

    def select_documents(
        self,
        document_ids: list[UUID] | None,
    ) -> list[ReadyDocument]:
        """Read persisted results for the requested ready documents."""
        if document_ids is None:
            documents = self._repository.list(status=DocumentStatus.READY)

            selected: list[ReadyDocument] = []

            for document in documents:
                result = self._repository.get_result(document.id)

                if result is not None:
                    selected.append(
                        ReadyDocument(
                            document=document,
                            result=result,
                        )
                    )

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

            selected.append(
                ReadyDocument(
                    document=document,
                    result=result,
                )
            )

        return selected

    def ask(
        self,
        question: str,
        document_ids: list[UUID] | None = None,
    ) -> ChatResponse:
        """Return citations and a mock answer, or an honest refusal."""
        documents = self.select_documents(document_ids)

        ranked_chunks = self._retriever.retrieve(
            question,
            documents,
        )

        sources = build_sources(
            ranked_chunks,
            question,
        )

        if not sources:
            return ChatResponse(
                status="insufficient_info",
                answer=INSUFFICIENT_INFO_ANSWER,
                sources=[],
            )

        context = "\n".join(source.quote for source in sources)

        try:
            answer = self._llm_adapter.generate(
                question,
                context,
            )

            if not isinstance(answer, str):
                raise TypeError("LLM adapter must return a string")

        except Exception as exc:
            raise ChatServiceError(
                503,
                "llm_unavailable",
                "Сервис генерации ответа временно недоступен.",
            ) from exc

        return ChatResponse(
            status="answered",
            answer=answer,
            sources=sources,
        )
