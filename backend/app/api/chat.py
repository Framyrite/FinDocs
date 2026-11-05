"""HTTP API for lexical questions over stored documents."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.documents import error_response, get_repository
from app.chat.models import ChatRequest, ChatResponse
from app.chat.service import ChatService, ChatServiceError
from app.documents.repository import DocumentRepository

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])


def get_chat_service(
    request: Request,
    repository: Annotated[
        DocumentRepository,
        Depends(get_repository),
    ],
) -> ChatService:
    """Build a service with the injected repository and LLM adapter."""
    return ChatService(
        repository=repository,
        llm_adapter=request.app.state.llm_adapter,
    )


def chat_validation_error(
    exc: RequestValidationError,
) -> JSONResponse:
    """Map chat request validation failures to contract error codes."""
    too_long = any(
        error.get("type") == "string_too_long"
        and tuple(error.get("loc", ())) == ("body", "question")
        for error in exc.errors()
    )

    if too_long:
        return error_response(
            422,
            "question_too_long",
            "Вопрос не должен превышать 2000 символов.",
        )

    return error_response(
        422,
        "invalid_question",
        "Некорректный вопрос или список документов.",
    )


@router.post("/chat/ask", response_model=ChatResponse)
def ask_chat(
    payload: ChatRequest,
    service: Annotated[
        ChatService,
        Depends(get_chat_service),
    ],
) -> ChatResponse | JSONResponse:
    """Search stored chunks and return a grounded mock answer."""
    try:
        return service.ask(
            question=payload.question,
            document_ids=payload.document_ids,
        )

    except ChatServiceError as exc:
        return error_response(
            exc.status_code,
            exc.code,
            exc.message,
        )

    except Exception:
        logger.exception("Unexpected error in POST /chat/ask")

        return error_response(
            500,
            "internal_error",
            "Внутренняя ошибка сервера.",
        )
