"""Public interface for the TXT processing module."""

from .errors import (
    EmptyDocumentError,
    InvalidTxtEncodingError,
    TokenizerContractError,
    TxtProcessingError,
)
from .models import Chunk, DocumentBlock, ProcessingResult
from .txt import decode_txt
from .processor import process_txt

__all__ = [
    "DocumentBlock",
    "Chunk",
    "ProcessingResult",
    "TxtProcessingError",
    "InvalidTxtEncodingError",
    "EmptyDocumentError",
    "TokenizerContractError",
    "decode_txt",
    "process_txt",
]
