"""HTTP API for the local TXT document library."""

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, File, Request, UploadFile
from fastapi.responses import JSONResponse, Response

from app.core.config import Settings
from app.documents.models import Document, DocumentStatus
from app.documents.repository import DocumentLimitExceededError, DocumentRepository
from app.documents.service import DocumentService

router = APIRouter(tags=["documents"])


def get_repository(request: Request) -> DocumentRepository:
    """Retrieve the repository initialized by application lifespan."""
    return request.app.state.document_repository


def get_service(request: Request) -> DocumentService:
    """Retrieve the document processing service."""
    return request.app.state.document_service


def document_payload(document: Document) -> dict[str, object]:
    """Serialize document metadata according to the MVP API contract."""
    return {
        "id": str(document.id),
        "filename": document.filename,
        "format": document.format,
        "status": document.status.value,
        "error_code": document.error_code,
        "error_message": document.error_message,
        "size_bytes": document.size_bytes,
        "created_at": (document.created_at.astimezone(UTC).isoformat().replace("+00:00", "Z")),
    }


def error_response(
    status_code: int,
    code: str,
    message: str,
    details: dict[str, object] | None = None,
) -> JSONResponse:
    """Return an error using the agreed JSON envelope."""
    error: dict[str, object] = {
        "code": code,
        "message": message,
    }

    if details is not None:
        error["details"] = details

    return JSONResponse(
        status_code=status_code,
        content={"error": error},
    )


@router.post("/documents", status_code=202)
async def upload_document(
    file: Annotated[UploadFile, File()],
    background_tasks: BackgroundTasks,
    request: Request,
    repository: Annotated[DocumentRepository, Depends(get_repository)],
    service: Annotated[DocumentService, Depends(get_service)],
) -> JSONResponse:
    """Accept a TXT upload and schedule its processing."""
    settings: Settings = request.app.state.settings
    max_bytes = settings.max_txt_size_mb * 1024 * 1024

    try:
        content_type = (file.content_type or "").split(";", 1)[0].strip().lower()

        if (
            not file.filename
            or not file.filename.casefold().endswith(".txt")
            or content_type not in ("", "text/plain", "application/octet-stream")
        ):
            return error_response(
                415,
                "unsupported_format",
                "Поддерживаются только TXT-файлы.",
            )

        data = await file.read(max_bytes + 1)
    finally:
        await file.close()

    if len(data) > max_bytes:
        return error_response(
            413,
            "file_too_large",
            f"Файл больше допустимого размера ({settings.max_txt_size_mb} МБ).",
            {"max_size_mb": settings.max_txt_size_mb},
        )

    if not data:
        return error_response(
            422,
            "empty_file",
            "Файл пуст.",
        )

    document = Document(
        id=uuid4(),
        filename=file.filename,
        size_bytes=len(data),
        created_at=datetime.now(UTC),
    )

    try:
        repository.create(document, data)
    except DocumentLimitExceededError:
        return error_response(
            409,
            "document_limit_reached",
            "Достигнут лимит количества документов.",
        )

    background_tasks.add_task(service.process_document, document.id)

    return JSONResponse(
        status_code=202,
        content=document_payload(document),
    )


@router.get("/documents")
def list_documents(
    repository: Annotated[DocumentRepository, Depends(get_repository)],
    status: DocumentStatus | None = None,
    q: str | None = None,
) -> JSONResponse:
    """List documents using optional status and filename filters."""
    documents = repository.list(status=status, q=q)

    return JSONResponse(
        content={
            "items": [document_payload(document) for document in documents],
            "total": len(documents),
        }
    )


@router.get("/documents/{document_id}")
def get_document(
    document_id: UUID,
    repository: Annotated[DocumentRepository, Depends(get_repository)],
) -> JSONResponse:
    """Return the current metadata and processing status."""
    document = repository.get(document_id)

    if document is None:
        return error_response(
            404,
            "document_not_found",
            "Документ не найден.",
        )

    return JSONResponse(content=document_payload(document))


@router.delete("/documents/{document_id}", status_code=204)
def delete_document(
    document_id: UUID,
    repository: Annotated[DocumentRepository, Depends(get_repository)],
) -> Response:
    """Physically delete a document and all its stored files."""
    if not repository.delete(document_id):
        return error_response(
            404,
            "document_not_found",
            "Документ не найден.",
        )

    return Response(status_code=204)
