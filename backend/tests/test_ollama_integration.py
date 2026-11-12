"""Integration tests for Ollama provider selection and chat outcomes."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.llm.adapter import LLMAdapter
from app.llm.errors import LLMInsufficientContext, LLMUnavailable
from app.llm.mock import MockLLM
from app.llm.ollama import OllamaLLMAdapter
from app.main import create_app


class RefusingLLM(LLMAdapter):
    """Simulate a model refusing unsupported questions."""

    def generate(self, question: str, context: str) -> str:
        raise LLMInsufficientContext("Insufficient context")


class UnavailableLLM(LLMAdapter):
    """Simulate a technical model failure."""

    def generate(self, question: str, context: str) -> str:
        raise LLMUnavailable("Model unavailable")


def test_create_app_selects_ollama() -> None:
    settings = Settings(_env_file=None, llm_provider="ollama")
    application = create_app(settings=settings)

    assert isinstance(application.state.llm_adapter, OllamaLLMAdapter)


def test_explicit_adapter_has_priority() -> None:
    settings = Settings(_env_file=None, llm_provider="ollama")
    adapter = MockLLM()

    application = create_app(
        settings=settings,
        llm_adapter=adapter,
    )

    assert application.state.llm_adapter is adapter


@pytest.mark.parametrize(
    ("adapter", "expected_status"),
    [
        (RefusingLLM(), "insufficient_info"),
        (UnavailableLLM(), "error"),
    ],
)
def test_chat_handles_model_outcomes(
    tmp_path: Path,
    adapter: LLMAdapter,
    expected_status: str,
) -> None:
    settings = Settings(_env_file=None, data_dir=tmp_path)
    application = create_app(settings=settings, llm_adapter=adapter)

    with TestClient(application) as client:
        uploaded = client.post(
            "/documents",
            files={
                "file": (
                    "finance.txt",
                    "Кредит приносит процентный доход.".encode(),
                    "text/plain",
                )
            },
        )

        assert uploaded.status_code == 202
        document_id = uploaded.json()["id"]

        detail = client.get(f"/documents/{document_id}")
        assert detail.json()["status"] == "ready"

        response = client.post(
            "/chat/ask",
            json={
                "question": "кредит процентный доход",
                "document_ids": [document_id],
            },
        )

    if expected_status == "insufficient_info":
        assert response.status_code == 200
        assert response.json()["status"] == "insufficient_info"
        assert response.json()["sources"] == []
    else:
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "llm_unavailable"
