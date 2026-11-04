import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.llm.adapter import LLMAdapter
from app.llm.mock import MockLLM
from app.main import create_app


class TestLLM(LLMAdapter):
    def generate(self, question: str, context: str) -> str:
        return f"{question}: {context}"


def test_health_returns_expected_response():
    application = create_app(settings=Settings(_env_file=None))

    with TestClient(application) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_app_uses_mock_llm_by_default(monkeypatch):
    monkeypatch.setenv("FINDOCS_APP_NAME", "FinDocs Backend")
    monkeypatch.setenv("FINDOCS_DEBUG", "false")

    application = create_app()

    assert isinstance(application, FastAPI)
    assert application.title == "FinDocs Backend"
    assert isinstance(application.state.llm_adapter, MockLLM)


def test_create_app_accepts_different_settings():
    first = Settings(_env_file=None, app_name="First", debug=False)
    second = Settings(_env_file=None, app_name="Second", debug=True)

    first_app = create_app(settings=first)
    second_app = create_app(settings=second)

    assert first_app.title == "First"
    assert first_app.debug is False

    assert second_app.title == "Second"
    assert second_app.debug is True


def test_create_app_accepts_custom_llm():
    adapter = TestLLM()
    application = create_app(llm_adapter=adapter)

    assert application.state.llm_adapter is adapter
    assert application.state.llm_adapter.generate("Вопрос", "Контекст") == "Вопрос: Контекст"


def test_mock_llm_is_deterministic():
    adapter = MockLLM()
    question = "Что такое FinDocs? 👋"
    context = "Это учебный проект."

    first = adapter.generate(question, context)
    second = adapter.generate(question, context)

    assert first == second
    assert first == (
        "[MOCK] Тестовый ответ. Реальная LLM не подключена.\n"
        "Вопрос: Что такое FinDocs? 👋\n"
        "Контекст: Это учебный проект."
    )


def test_mock_llm_allows_empty_context():
    result = MockLLM().generate("Вопрос", "")

    assert "Контекст: (пустой контекст)" in result


@pytest.mark.parametrize("question", ["", " ", "\t\n"])
def test_mock_llm_rejects_empty_question(question):
    with pytest.raises(ValueError):
        MockLLM().generate(question, "Контекст")


@pytest.mark.parametrize(
    ("question", "context"),
    [
        (None, "Контекст"),
        (123, "Контекст"),
        ("Вопрос", None),
        ("Вопрос", 123),
    ],
)
def test_mock_llm_rejects_invalid_types(question, context):
    with pytest.raises(TypeError):
        MockLLM().generate(question, context)
