"""Document storage contracts and local repository implementation."""

import json
import logging
import os
import shutil
from dataclasses import asdict, replace
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile, mkdtemp
from threading import RLock
from typing import Protocol
from uuid import UUID

from app.processing.models import Chunk, DocumentBlock, ProcessingResult

from .models import Document, DocumentStatus

logger = logging.getLogger(__name__)

RESULT_UNAVAILABLE_MESSAGE = (
    "Результат обработки отсутствует или повреждён. Загрузите файл ещё раз."
)


class DocumentRepository(Protocol):
    """Storage operations required by the document service."""

    def create(self, document: Document, data: bytes) -> None: ...

    def get(self, document_id: UUID) -> Document | None: ...

    def list(
        self,
        status: DocumentStatus | None = None,
        q: str | None = None,
    ) -> list[Document]: ...

    def read_original(self, document_id: UUID) -> bytes | None: ...

    def get_result(self, document_id: UUID) -> ProcessingResult | None: ...

    def mark_processing(self, document_id: UUID) -> bool: ...

    def complete(self, document_id: UUID, result: ProcessingResult) -> bool: ...

    def fail(self, document_id: UUID, code: str, message: str) -> bool: ...

    def delete(self, document_id: UUID) -> bool: ...

    def recover_incomplete(self) -> None: ...


class DocumentLimitExceededError(Exception):
    """Raised when the document library has reached its capacity."""


class LocalFileDocumentRepository:
    """Store document files and metadata on the local filesystem."""

    def __init__(
        self,
        data_dir: Path,
        max_documents: int = 100,
    ) -> None:
        if max_documents < 1:
            raise ValueError("max_documents must be positive")

        self._documents_dir = data_dir / "documents"
        self._documents_dir.mkdir(parents=True, exist_ok=True)
        self._max_documents = max_documents
        self._lock = RLock()

    def _document_dir(self, document_id: UUID) -> Path:
        return self._documents_dir / str(document_id)

    def _count_documents(self) -> int:
        """Count document directories, including damaged metadata."""
        count = 0

        for directory in self._documents_dir.iterdir():
            if not directory.is_dir():
                continue

            try:
                document_id = UUID(directory.name)
            except ValueError:
                continue

            if str(document_id) == directory.name:
                count += 1

        return count

    @staticmethod
    def _atomic_write(path: Path, data: bytes) -> None:
        """Write bytes atomically using a temporary file in the same directory."""
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path: Path | None = None

        try:
            with NamedTemporaryFile(
                mode="wb",
                dir=path.parent,
                prefix=f".{path.name}.",
                suffix=".tmp",
                delete=False,
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)
                temporary_file.write(data)
                temporary_file.flush()
                os.fsync(temporary_file.fileno())

            os.replace(temporary_path, path)
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)

    def create(self, document: Document, data: bytes) -> None:
        """Save original bytes and metadata before publishing the document."""
        if document.size_bytes != len(data):
            raise ValueError("Document size does not match original data")

        with self._lock:
            document_dir = self._document_dir(document.id)

            if document_dir.exists():
                raise FileExistsError(f"Document already exists: {document.id}")

            if self._count_documents() >= self._max_documents:
                raise DocumentLimitExceededError("Document library limit reached")

            temporary_dir = Path(
                mkdtemp(
                    prefix=f".{document.id}.",
                    dir=self._documents_dir,
                )
            )

            try:
                metadata = {
                    "id": str(document.id),
                    "filename": document.filename,
                    "size_bytes": document.size_bytes,
                    "created_at": document.created_at.isoformat(),
                    "format": document.format,
                    "status": document.status.value,
                    "error_code": document.error_code,
                    "error_message": document.error_message,
                }

                self._atomic_write(temporary_dir / "original.bin", data)

                self._atomic_write(
                    temporary_dir / "meta.json",
                    json.dumps(
                        metadata,
                        ensure_ascii=False,
                        indent=2,
                    ).encode("utf-8"),
                )

                os.replace(temporary_dir, document_dir)
            finally:
                if temporary_dir.exists():
                    shutil.rmtree(temporary_dir)

    def get(self, document_id: UUID) -> Document | None:
        """Read metadata, ignoring damaged documents without deleting them."""
        with self._lock:
            metadata_path = self._document_dir(document_id) / "meta.json"

            try:
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

                if not isinstance(metadata, dict):
                    raise TypeError("Document metadata must be a JSON object")

                if metadata["id"] != str(document_id):
                    raise ValueError("Document ID does not match its directory")

                if metadata["format"] != "txt":
                    raise ValueError("Unsupported stored document format")

                filename = metadata["filename"]
                size_bytes = metadata["size_bytes"]

                if not isinstance(filename, str):
                    raise TypeError("Document filename must be a string")

                if type(size_bytes) is not int or size_bytes < 0:
                    raise ValueError("Invalid document size")

                created_at = datetime.fromisoformat(metadata["created_at"])

                if created_at.tzinfo is None:
                    raise ValueError("Document timestamp must include timezone")

                error_code = metadata["error_code"]
                error_message = metadata["error_message"]

                if error_code is not None and not isinstance(error_code, str):
                    raise TypeError("Invalid document error code")

                if error_message is not None and not isinstance(error_message, str):
                    raise TypeError("Invalid document error message")

                document = Document(
                    id=UUID(metadata["id"]),
                    filename=filename,
                    size_bytes=size_bytes,
                    created_at=created_at,
                    format="txt",
                    status=DocumentStatus(metadata["status"]),
                    error_code=error_code,
                    error_message=error_message,
                )

                if document.status == DocumentStatus.READY and self.get_result(document_id) is None:
                    return replace(
                        document,
                        status=DocumentStatus.ERROR,
                        error_code="processing_failed",
                        error_message=RESULT_UNAVAILABLE_MESSAGE,
                    )

                return document

            except FileNotFoundError:
                return None

            except (OSError, ValueError, TypeError, KeyError):
                logger.exception(
                    "Cannot read metadata for document %s",
                    document_id,
                )
                return None

    def read_original(self, document_id: UUID) -> bytes | None:
        """Read the original document bytes without modifying them."""
        with self._lock:
            original_path = self._document_dir(document_id) / "original.bin"

            try:
                return original_path.read_bytes()
            except FileNotFoundError:
                return None

    def list(
        self,
        status: DocumentStatus | None = None,
        q: str | None = None,
    ) -> list[Document]:
        """List stored documents with optional status and filename filters."""
        with self._lock:
            documents: list[Document] = []

            for document_dir in self._documents_dir.iterdir():
                if not document_dir.is_dir():
                    continue

                try:
                    document_id = UUID(document_dir.name)
                except ValueError:
                    continue

                document = self.get(document_id)

                if document is None:
                    continue

                if status is not None and document.status != status:
                    continue

                if q is not None and q.casefold() not in document.filename.casefold():
                    continue

                documents.append(document)

            return sorted(
                documents,
                key=lambda document: (document.created_at, str(document.id)),
                reverse=True,
            )

    def mark_processing(self, document_id: UUID) -> bool:
        """Atomically move an uploaded document into processing."""
        with self._lock:
            document = self.get(document_id)

            if document is None:
                return False

            if document.status != DocumentStatus.UPLOADED:
                return False

            metadata_path = self._document_dir(document_id) / "meta.json"
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

            metadata["status"] = DocumentStatus.PROCESSING.value
            metadata["error_code"] = None
            metadata["error_message"] = None

            self._atomic_write(
                metadata_path,
                json.dumps(
                    metadata,
                    ensure_ascii=False,
                    indent=2,
                ).encode("utf-8"),
            )

            return True

    def complete(self, document_id: UUID, result: ProcessingResult) -> bool:
        """Persist processing results before marking a document as ready."""
        if result.document_id != document_id:
            raise ValueError("Processing result belongs to another document")

        if any(block.document_id != document_id for block in result.blocks):
            raise ValueError("Processing result contains a block from another document")

        if any(chunk.document_id != document_id for chunk in result.chunks):
            raise ValueError("Processing result contains a chunk from another document")

        with self._lock:
            document = self.get(document_id)

            if document is None or document.status != DocumentStatus.PROCESSING:
                return False

            document_dir = self._document_dir(document_id)
            result_path = document_dir / "result.json"
            metadata_path = document_dir / "meta.json"

            self._atomic_write(
                result_path,
                json.dumps(
                    asdict(result),
                    ensure_ascii=False,
                    indent=2,
                    default=str,
                ).encode("utf-8"),
            )

            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            metadata["status"] = DocumentStatus.READY.value
            metadata["error_code"] = None
            metadata["error_message"] = None

            self._atomic_write(
                metadata_path,
                json.dumps(
                    metadata,
                    ensure_ascii=False,
                    indent=2,
                ).encode("utf-8"),
            )

            return True

    def _mark_result_unavailable(self, document_id: UUID) -> None:
        """Persist an error if a ready document has no usable result."""
        with self._lock:
            metadata_path = self._document_dir(document_id) / "meta.json"

            try:
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

                if (
                    not isinstance(metadata, dict)
                    or metadata.get("id") != str(document_id)
                    or metadata.get("status") != DocumentStatus.READY.value
                ):
                    return

                metadata["status"] = DocumentStatus.ERROR.value
                metadata["error_code"] = "processing_failed"
                metadata["error_message"] = RESULT_UNAVAILABLE_MESSAGE

                self._atomic_write(
                    metadata_path,
                    json.dumps(
                        metadata,
                        ensure_ascii=False,
                        indent=2,
                    ).encode(),
                )

            except (OSError, ValueError, TypeError):
                logger.exception(
                    "Could not update status for document %s",
                    document_id,
                )

    def get_result(self, document_id: UUID) -> ProcessingResult | None:
        """Restore typed processing results, handling damaged JSON."""
        with self._lock:
            result_path = self._document_dir(document_id) / "result.json"

            try:
                data = json.loads(result_path.read_text(encoding="utf-8"))

                if not isinstance(data, dict):
                    raise TypeError("Processing result must be a JSON object")

                if data["document_id"] != str(document_id):
                    raise ValueError("Processing result belongs to another document")

                blocks = [
                    DocumentBlock(
                        id=UUID(block["id"]),
                        document_id=UUID(block["document_id"]),
                        type=block["type"],
                        position=block["position"],
                        content=block["content"],
                        start_char=block["start_char"],
                        end_char=block["end_char"],
                    )
                    for block in data["blocks"]
                ]

                chunks = [
                    Chunk(
                        id=UUID(chunk["id"]),
                        document_id=UUID(chunk["document_id"]),
                        block_id=UUID(chunk["block_id"]),
                        position=chunk["position"],
                        content=chunk["content"],
                        start_char=chunk["start_char"],
                        end_char=chunk["end_char"],
                    )
                    for chunk in data["chunks"]
                ]

                if any(block.document_id != document_id for block in blocks):
                    raise ValueError("Invalid block document ID")

                block_ids = {block.id for block in blocks}

                if any(
                    chunk.document_id != document_id or chunk.block_id not in block_ids
                    for chunk in chunks
                ):
                    raise ValueError("Invalid chunk references")

                return ProcessingResult(
                    document_id=document_id,
                    blocks=blocks,
                    chunks=chunks,
                )

            except FileNotFoundError:
                self._mark_result_unavailable(document_id)
                return None

            except (OSError, ValueError, TypeError, KeyError):
                logger.exception(
                    "Cannot read processing result for document %s",
                    document_id,
                )
                self._mark_result_unavailable(document_id)
                return None

    def fail(self, document_id: UUID, code: str, message: str) -> bool:
        """Persist a processing error only for an in-progress document."""
        with self._lock:
            document = self.get(document_id)

            if document is None or document.status != DocumentStatus.PROCESSING:
                return False

            metadata_path = self._document_dir(document_id) / "meta.json"
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

            metadata["status"] = DocumentStatus.ERROR.value
            metadata["error_code"] = code
            metadata["error_message"] = message

            self._atomic_write(
                metadata_path,
                json.dumps(
                    metadata,
                    ensure_ascii=False,
                    indent=2,
                ).encode("utf-8"),
            )
            (self._document_dir(document_id) / "result.json").unlink(missing_ok=True)

            return True

    def delete(self, document_id: UUID) -> bool:
        """Delete a document and all its stored files."""
        with self._lock:
            document_dir = self._document_dir(document_id)

            if not document_dir.is_dir():
                return False

            shutil.rmtree(document_dir)
            return True

    def recover_incomplete(self) -> None:
        """Recover documents independently so one failure cannot block others."""
        with self._lock:
            for document_dir in self._documents_dir.iterdir():
                if not document_dir.is_dir():
                    continue

                try:
                    try:
                        document_id = UUID(document_dir.name)
                    except ValueError:
                        if document_dir.name.startswith("."):
                            shutil.rmtree(document_dir)
                        continue

                    if str(document_id) != document_dir.name:
                        continue

                    metadata_path = document_dir / "meta.json"

                    if not metadata_path.is_file():
                        shutil.rmtree(document_dir)
                        continue

                    document = self.get(document_id)

                    if document is None:
                        # Keep damaged metadata for later investigation.
                        continue

                    if document.status == DocumentStatus.READY:
                        if self.get_result(document_id) is None:
                            self._mark_result_unavailable(document_id)
                        continue

                    if document.status not in (
                        DocumentStatus.UPLOADED,
                        DocumentStatus.PROCESSING,
                    ):
                        continue

                    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

                    metadata["status"] = DocumentStatus.ERROR.value
                    metadata["error_code"] = "processing_failed"
                    metadata["error_message"] = (
                        "Обработка была прервана перезапуском сервера. Загрузите файл ещё раз."
                    )

                    (document_dir / "result.json").unlink(missing_ok=True)

                    self._atomic_write(
                        metadata_path,
                        json.dumps(
                            metadata,
                            ensure_ascii=False,
                            indent=2,
                        ).encode(),
                    )

                except Exception:
                    logger.exception(
                        "Failed to recover document directory %s",
                        document_dir,
                    )
                    continue
