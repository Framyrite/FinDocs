"""HTTP regression tests for refusing partially supported composite answers."""

from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.llm.adapter import LLMAdapter
from app.main import create_app


class FixedAnswerLLM(LLMAdapter):
    """Return a chosen response without contacting a model."""

    def __init__(self, answer: str) -> None:
        self._answer = answer

    def generate(self, question: str, context: str) -> str:
        return self._answer


def _ask(tmp_path: Path, content: str, question: str, answer: str) -> dict:
    app = create_app(
        settings=Settings(_env_file=None, data_dir=tmp_path),
        llm_adapter=FixedAnswerLLM(answer),
    )
    with TestClient(app) as client:
        upload = client.post(
            "/documents",
            files={"file": ("material.txt", content.encode("utf-8"), "text/plain")},
        )
        assert upload.status_code == 202, upload.text
        response = client.post(
            "/chat/ask",
            json={
                "question": question,
                "document_ids": [upload.json()["id"]],
            },
        )
        assert response.status_code == 200, response.text
        return response.json()


def test_d03_partial_answer_is_refused_at_chat_api(tmp_path: Path) -> None:
    source = (
        Path(__file__).resolve().parents[2] / "qa" / "test_data" / "pdf_text_injection.txt"
    ).read_text(encoding="utf-8")
    question = (
        "В каком году и кем был принят Акт о супрематии, "
        "ознаменовавший рождение англиканской церкви?"
    )
    answer = (
        "Акт о супрематии был принят в 1534 году. "
        "Именно это событие ознаменовало рождение англиканской церкви."
    )
    result = _ask(tmp_path, source, question, answer)
    assert result["status"] == "insufficient_info"
    assert result["sources"] == []


def test_explicit_actor_and_year_preserves_answered(tmp_path: Path) -> None:
    result = _ask(
        tmp_path,
        "В 1534 году король Генрих VIII принял акт о супрематии.",
        "В каком году и кем был принят акт о супрематии?",
        "Акт был принят королём Генрихом VIII в 1534 году.",
    )
    assert result["status"] == "answered"
    assert result["sources"]


def test_t01_partial_answer_is_refused(tmp_path: Path) -> None:
    source = (
        Path(__file__).resolve().parents[2] / "qa" / "test_data" / "на_русском.txt"
    ).read_text(encoding="utf-8")
    question = (
        "В каком году и каким именно директором в Массачусетском "
        "технологическом институте при остановке IBM 7094 "
        "были найдены процессы 1967 года?"
    )
    answer = (
        "Процессы 1967 года были найдены при остановке IBM 7094 "
        "в Массачусетском технологическом институте в 1973 году. "
        "В предоставленных фрагментах не указано имя директора."
    )
    result = _ask(tmp_path, source, question, answer)
    assert result["status"] == "insufficient_info"
    assert result["sources"] == []
