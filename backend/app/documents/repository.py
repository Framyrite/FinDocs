"""Document storage contracts and local repository implementation."""

import json
import os
import shutil
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile, mkdtemp
from threading import RLock
from typing import Protocol
from uuid import UUID

from app.processing.models import Chunk, DocumentBlock, ProcessingResult

from .models import Document, DocumentStatus


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

            if len(self.list()) >= self._max_documents:
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
        """Load document metadata from disk."""
        with self._lock:
            metadata_path = self._document_dir(document_id) / "meta.json"

            try:
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            except FileNotFoundError:
                return None

            if metadata["id"] != str(document_id):
                raise ValueError("Document ID does not match its directory")

            return Document(
                id=UUID(metadata["id"]),
                filename=metadata["filename"],
                size_bytes=metadata["size_bytes"],
                created_at=datetime.fromisoformat(metadata["created_at"]),
                format=metadata["format"],
                status=DocumentStatus(metadata["status"]),
                error_code=metadata["error_code"],
                error_message=metadata["error_message"],
            )

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

    def get_result(self, document_id: UUID) -> ProcessingResult | None:
        """Restore processed blocks and chunks from disk."""
        with self._lock:
            result_path = self._document_dir(document_id) / "result.json"

            try:
                data = json.loads(result_path.read_text(encoding="utf-8"))
            except FileNotFoundError:
                return None

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

            return ProcessingResult(
                document_id=document_id,
                blocks=blocks,
                chunks=chunks,
            )

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
        """Recover interrupted documents and remove incomplete directories."""
        with self._lock:
            for document_dir in self._documents_dir.iterdir():
                if not document_dir.is_dir():
                    continue

                try:
                    document_id = UUID(document_dir.name)
                except ValueError:
                    # Remove temporary directories left by interrupted create().
                    if document_dir.name.startswith("."):
                        shutil.rmtree(document_dir)
                    continue

                metadata_path = document_dir / "meta.json"

                if not metadata_path.is_file():
                    shutil.rmtree(document_dir)
                    continue

                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

                if metadata["id"] != str(document_id):
                    raise ValueError("Document ID does not match its directory")

                if metadata["status"] not in (
                    DocumentStatus.UPLOADED.value,
                    DocumentStatus.PROCESSING.value,
                ):
                    continue

                metadata["status"] = DocumentStatus.ERROR.value
                metadata["error_code"] = "processing_failed"
                metadata["error_message"] = "Processing interrupted by server restart"

                # Remove a result that was not fully committed as ready.
                (document_dir / "result.json").unlink(missing_ok=True)

                self._atomic_write(
                    metadata_path,
                    json.dumps(
                        metadata,
                        ensure_ascii=False,
                        indent=2,
                    ).encode("utf-8"),
                )
