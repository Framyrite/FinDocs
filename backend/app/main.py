"""Application creation and module wiring."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.documents import router as documents_router
from app.api.health import router as health_router
from app.core.config import Settings
from app.documents.repository import (
    DocumentRepository,
    LocalFileDocumentRepository,
)
from app.documents.service import DocumentService
from app.llm.adapter import LLMAdapter
from app.llm.mock import MockLLM


def create_app(
    settings: Settings | None = None,
    llm_adapter: LLMAdapter | None = None,
    document_repository: DocumentRepository | None = None,
) -> FastAPI:
    """Create an application with injectable settings and dependencies."""
    config = Settings() if settings is None else settings
    adapter = MockLLM() if llm_adapter is None else llm_adapter

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        """Initialize storage and recover interrupted processing on startup."""
        repository = (
            document_repository
            if document_repository is not None
            else LocalFileDocumentRepository(
                data_dir=config.data_dir,
                max_documents=config.max_documents,
            )
        )

        repository.recover_incomplete()

        application.state.document_repository = repository
        application.state.document_service = DocumentService(repository)

        yield

    application = FastAPI(
        title=config.app_name,
        debug=config.debug,
        lifespan=lifespan,
    )

    application.state.settings = config
    application.include_router(documents_router)
    application.state.llm_adapter = adapter
    application.include_router(health_router)

    @application.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        """Return validation errors in the shared API error format."""
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "validation_error",
                    "message": "Некорректные параметры запроса.",
                }
            },
        )

    return application


app = create_app()
