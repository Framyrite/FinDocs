"""Deterministic mock adapter requiring no model or network connection."""

from app.llm.adapter import LLMAdapter


class MockLLM(LLMAdapter):
    """Echo the input to verify the adapter flow without a real LLM."""

    def generate(self, question: str, context: str) -> str:
        if not isinstance(question, str) or not isinstance(context, str):
            raise TypeError("question and context must be strings")
        if not question.strip():
            raise ValueError("question must not be empty")

        context_text = context if context else "(пустой контекст)"
        return (
            "[MOCK] Тестовый ответ. Реальная LLM не подключена.\n"
            f"Вопрос: {question}\n"
            f"Контекст: {context_text}"
        )
