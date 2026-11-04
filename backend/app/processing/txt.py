"""UTF-8 TXT decoding and input validation."""

from .errors import EmptyDocumentError, InvalidTxtEncodingError


def decode_txt(data: bytes) -> str:
    """Decode UTF-8 TXT data, with or without BOM."""
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise InvalidTxtEncodingError("TXT file must use UTF-8 encoding") from exc

    if not text.strip():
        raise EmptyDocumentError("TXT file is empty or contains only whitespace")

    return text
