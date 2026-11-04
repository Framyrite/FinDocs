
class TxtProcessingError(Exception):
    """Base exception for TXT processing errors."""


class InvalidTxtEncodingError(TxtProcessingError):
    """TXT data cannot be decoded as UTF-8."""


class EmptyDocumentError(TxtProcessingError):
    """TXT document is empty or contains only whitespace."""


class TokenizerContractError(TxtProcessingError):
    """Tokenizer returned invalid character offsets."""
