"""Public contract for language model integrations."""

from abc import ABC, abstractmethod


class LLMAdapter(ABC):
    """Generate text from a question and an already prepared context."""

    @abstractmethod
    def generate(self, question: str, context: str) -> str:
        """Return an answer; an empty context is valid.

        Raise ValueError for an empty or whitespace-only question and
        TypeError when question or context is not a string.
        """
