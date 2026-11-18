"""Internal exceptions for language model generation."""


class LLMInsufficientContext(Exception):
    """The model cannot answer using the supplied context."""


class LLMUnavailable(Exception):
    """The model service or its response is unavailable."""
