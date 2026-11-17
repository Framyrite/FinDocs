"""Regression tests for PR #13 review blockers."""

from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.llm.adapter import LLMAdapter
from app.llm.ollama import OllamaLLMAdapter
from app.main import create_app


class FixedLLM(LLMAdapter):
    def __init__(self, answer: str, budget: int | None = None) -> None:
        self.answer = answer
        self.budget = budget
        self.calls = 0

    def context_char_budget(self, question: str) -> int:
        return self.budget if self.budget is not None else 6000

    def generate(self, question: str, context: str) -> str:
        self.calls += 1
        return self.answer


def _ask(
    tmp_path: Path,
    text: str,
    question: str,
    llm: FixedLLM | None = None,
) -> dict:
    app = create_app(
        settings=Settings(_env_file=None, data_dir=tmp_path),
        llm_adapter=llm,
    )
    with TestClient(app) as client:
        upload = client.post(
            "/documents",
            files={"file": ("sample.txt", text.encode("utf-8"), "text/plain")},
        )
        assert upload.status_code == 202, upload.text
        response = client.post(
            "/chat/ask",
            json={"question": question, "document_ids": [upload.json()["id"]]},
        )
        assert response.status_code == 200, response.text
        return response.json()


def test_short_rr_question_reaches_real_adapter(tmp_path: Path) -> None:
    llm = FixedLLM("RR использует квант времени.")
    result = _ask(tmp_path, "Алгоритм RR использует квант времени.", "RR", llm)
    assert llm.calls == 1
    assert result["status"] == "answered"
    assert "RR" in result["sources"][0]["quote"]


def test_short_rr_question_still_works_with_mock(tmp_path: Path) -> None:
    result = _ask(tmp_path, "Алгоритм RR использует квант времени.", "RR")
    assert result["status"] == "answered"
    assert result["answer"].startswith("[MOCK]")
    assert "RR" in result["sources"][0]["quote"]


def test_invented_amount_returns_insufficient_info(tmp_path: Path) -> None:
    llm = FixedLLM("По договору перечислили 900000 рублей.")
    result = _ask(
        tmp_path,
        "Условия кредита описаны в договоре.",
        "Какие условия кредита?",
        llm,
    )
    assert llm.calls == 1
    assert result["status"] == "insufficient_info"
    assert result["sources"] == []


def test_empty_context_budget_skips_llm(tmp_path: Path) -> None:
    llm = FixedLLM("RR использует квант времени.", budget=0)
    result = _ask(tmp_path, "Алгоритм RR использует квант времени.", "RR", llm)
    assert llm.calls == 0
    assert result["status"] == "insufficient_info"
    assert result["sources"] == []


def test_ollama_budget_reacts_to_num_ctx() -> None:
    tiny = OllamaLLMAdapter(
        Settings(_env_file=None, llm_context_tokens=512, llm_max_output_tokens=64)
    )
    default = OllamaLLMAdapter(Settings(_env_file=None))
    assert tiny.context_char_budget("Что такое FCFS?") == 0
    assert 0 < default.context_char_budget("Что такое FCFS?") <= 6000
