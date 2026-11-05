"""Deterministic mock adapter for grounded demonstration answers."""

from app.llm.adapter import LLMAdapter

MOCK_HEADER = "[MOCK] Найдены фрагменты по ключевым словам вопроса:"


class MockLLM(LLMAdapter):
    """Format supplied citations without generating new information."""

    def generate(self, question: str, context: str) -> str:
        if not isinstance(question, str) or not isinstance(context, str):
            raise TypeError("question and context must be strings")

        if not question.strip():
            raise ValueError("question must not be empty")

        quotes = [line for line in context.split("\n") if line]

        lines = [MOCK_HEADER]

        for number, quote in enumerate(quotes, start=1):
            lines.append(f"{number}. «{quote}»")

        return "\n".join(lines)
