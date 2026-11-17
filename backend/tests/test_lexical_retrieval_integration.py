"""Exercise Backend 0.8 retrieval on the unchanged QA TXT fixtures."""

from pathlib import Path
from uuid import UUID

from fastapi.testclient import TestClient

from app.chat.service import ChatService
from app.core.config import Settings
from app.main import create_app
from app.retrieval.lexical import LexicalRetriever

QA_DIR = Path(__file__).resolve().parents[2] / "qa" / "test_data"

QUESTIONS = {
    "D02": ("Какой алгоритм планирования является невытесняющим и работает по принципу FIFO?"),
    "D03": (
        "В каком году и кем был принят Акт о супрематии, "
        "ознаменовавший рождение англиканской церкви?"
    ),
    "P01": (
        "Почему странные или нереалистичные сны после интенсивного "
        "обучения помогают лучше усваивать навыки?"
    ),
    "P02": ("В чём заключается главное различие между алгоритмами FCFS и Round Robin (RR)?"),
    "N01": (
        "Какое среднее время ожидания у процессов p0, p1, p2 при "
        "алгоритме FCFS и каков их приоритет по правилам системы Linux?"
    ),
    "N02": (
        "В каком городе проходило исследование МРТ о переписывании "
        "воспоминаний во сне и сколько человек в нем участвовало?"
    ),
    "N03": ("Какова стоимость подписки на сервис FinDocs для корпоративных клиентов?"),
    "I01": (
        "Какую сумму в долларах заплатил Генрих VIII за покупку "
        "акций компании Siemens & Halske в XVI веке?"
    ),
    "I02": (
        "Как связан алгоритм планирования FCFS с принятием Акта о "
        "супрематии королем Генрихом VIII в 1534 году, "
        "и сколько долларов за это было заплачено?"
    ),
}


def test_qa_retrieval_before_llm(tmp_path: Path) -> None:
    """Confirm relevant recall without promoting unsupported negative cases."""
    app = create_app(
        settings=Settings(
            _env_file=None,
            data_dir=tmp_path,
            llm_provider="mock",
        )
    )

    with TestClient(app) as client:
        document_ids = []
        for filename in (
            "only_text.txt",
            "на_русском.txt",
            "pdf_text_injection.txt",
        ):
            response = client.post(
                "/documents",
                files={
                    "file": (
                        filename,
                        (QA_DIR / filename).read_bytes(),
                        "text/plain",
                    )
                },
            )
            assert response.status_code == 202
            document_id = response.json()["id"]
            status = client.get(f"/documents/{document_id}").json()["status"]
            assert status == "ready"
            document_ids.append(UUID(document_id))

        service = ChatService(
            repository=app.state.document_repository,
            llm_adapter=app.state.llm_adapter,
        )
        selected = service.select_documents(document_ids)
        retriever = LexicalRetriever()

        results = {
            case: retriever.retrieve(question, selected) for case, question in QUESTIONS.items()
        }

        for case in ("D02", "D03", "P01", "P02"):
            assert results[case], f"{case}: missing evidence candidates"

        assert "FIFO" in results["D02"][0].chunk.content

        for case in ("N01", "N02", "N03", "I01", "I02"):
            assert not results[case], f"{case}: unsupported fallback candidate"
