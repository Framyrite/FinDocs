"""HTTP integration and contract tests for POST /chat/ask."""

import json
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.chat import get_chat_service
from app.core.config import Settings
from app.documents.models import Document
from app.llm.adapter import LLMAdapter
from app.main import create_app
from app.processing.txt import decode_txt


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    settings = Settings(
        _env_file=None,
        data_dir=tmp_path,
        max_txt_size_mb=1,
        max_documents=10,
    )

    with TestClient(create_app(settings=settings)) as test_client:
        yield test_client


def upload_ready(
    client: TestClient,
    filename: str,
    data: bytes,
) -> str:
    response = client.post(
        "/documents",
        files={"file": (filename, data, "text/plain")},
    )

    assert response.status_code == 202, response.text

    document_id = response.json()["id"]
    detail = client.get(f"/documents/{document_id}")

    assert detail.status_code == 200
    assert detail.json()["status"] == "ready"

    return document_id


def assert_error(
    response,
    http_status: int,
    code: str,
) -> None:
    assert response.status_code == http_status
    body = response.json()

    assert set(body) == {"error"}
    assert body["error"]["code"] == code
    assert isinstance(body["error"]["message"], str)


def test_chat_end_to_end_uses_real_sources(
    client: TestClient,
    tmp_path: Path,
) -> None:
    """Upload TXT, process, ask and verify exact original coordinates."""
    text = "Введение 😀\nОблигация приносит процентный доход! Доход зависит от условий."
    data = b"\xef\xbb\xbf" + text.encode("utf-8")

    document_id = upload_ready(
        client,
        "Материал😀.txt",
        data,
    )

    response = client.post(
        "/chat/ask",
        json={
            "question": "облигация процентный доход",
            "document_ids": [document_id],
        },
    )

    assert response.status_code == 200, response.text

    body = response.json()
    assert body["status"] == "answered"
    assert 1 <= len(body["sources"]) <= 3

    document_dir = tmp_path / "documents" / document_id

    original = (document_dir / "original.bin").read_bytes()
    decoded = decode_txt(original)

    stored_result = json.loads((document_dir / "result.json").read_text(encoding="utf-8"))

    blocks = {block["id"]: block for block in stored_result["blocks"]}
    chunks = {chunk["id"]: chunk for chunk in stored_result["chunks"]}

    for source in body["sources"]:
        assert set(source) == {
            "document_id",
            "filename",
            "block_id",
            "chunk_id",
            "start_char",
            "end_char",
            "quote",
        }

        assert UUID(source["document_id"]) == UUID(document_id)
        assert UUID(source["block_id"])
        assert UUID(source["chunk_id"])

        assert source["filename"] == "Материал😀.txt"
        assert source["block_id"] in blocks
        assert source["chunk_id"] in chunks

        block = blocks[source["block_id"]]
        chunk = chunks[source["chunk_id"]]

        assert chunk["block_id"] == source["block_id"]

        start = source["start_char"]
        end = source["end_char"]

        assert 0 <= start < end <= len(decoded)
        assert len(source["quote"]) <= 300

        assert source["quote"] == decoded[start:end]

        assert (
            block["start_char"] + chunk["start_char"]
            <= start
            < end
            <= block["start_char"] + chunk["end_char"]
        )

    expected_answer = "[MOCK] Найдены фрагменты по ключевым словам вопроса:\n" + "\n".join(
        f"{index}. «{source['quote']}»"
        for index, source in enumerate(
            body["sources"],
            start=1,
        )
    )

    assert body["answer"] == expected_answer


@pytest.mark.parametrize("explicit_null", [False, True])
def test_implicit_scope_uses_ready_documents(
    client: TestClient,
    explicit_null: bool,
) -> None:
    document_id = upload_ready(
        client,
        "Кредит.txt",
        "Кредит приносит процентный доход.".encode(),
    )

    payload = {"question": "кредит процентный доход"}

    if explicit_null:
        payload["document_ids"] = None

    response = client.post("/chat/ask", json=payload)

    assert response.status_code == 200
    assert response.json()["status"] == "answered"
    assert all(source["document_id"] == document_id for source in response.json()["sources"])


def test_explicit_scope_excludes_other_documents(
    client: TestClient,
) -> None:
    first = upload_ready(
        client,
        "Кредит.txt",
        "Кредит выдается банком.".encode(),
    )
    second = upload_ready(
        client,
        "Облигации.txt",
        "Облигации выплачивают купоны.".encode(),
    )

    question = "облигация купон"

    excluded = client.post(
        "/chat/ask",
        json={
            "question": question,
            "document_ids": [first],
        },
    )

    assert excluded.status_code == 200
    assert excluded.json()["status"] == "insufficient_info"
    assert excluded.json()["sources"] == []

    selected = client.post(
        "/chat/ask",
        json={
            "question": question,
            "document_ids": [second, second],
        },
    )

    assert selected.status_code == 200
    assert selected.json()["status"] == "answered"
    assert len(selected.json()["sources"]) == 1
    assert selected.json()["sources"][0]["document_id"] == second


def test_no_matches_returns_exact_refusal(
    client: TestClient,
) -> None:
    upload_ready(
        client,
        "Кредит.txt",
        "Кредит приносит процентный доход.".encode(),
    )

    response = client.post(
        "/chat/ask",
        json={"question": "облигация купон"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "insufficient_info",
        "answer": ("В выбранных материалах не удалось найти достаточную информацию для ответа."),
        "sources": [],
    }


def test_stop_words_only_returns_insufficient_info(
    client: TestClient,
) -> None:
    upload_ready(
        client,
        "Текст.txt",
        "Кредит приносит процентный доход.".encode(),
    )

    response = client.post(
        "/chat/ask",
        json={"question": "как что это"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "insufficient_info"
    assert response.json()["sources"] == []


def test_no_ready_documents_returns_409(
    client: TestClient,
) -> None:
    response = client.post(
        "/chat/ask",
        json={"question": "кредит процент"},
    )

    assert_error(response, 409, "no_ready_documents")


@pytest.mark.parametrize(
    "status",
    ["uploaded", "processing", "error"],
)
def test_explicit_non_ready_document_returns_409(
    client: TestClient,
    status: str,
) -> None:
    repository = client.app.state.document_repository

    data = b"Pending document"
    document = Document(
        id=uuid4(),
        filename="pending.txt",
        size_bytes=len(data),
        created_at=datetime.now(UTC),
    )

    repository.create(document, data)

    if status in ("processing", "error"):
        assert repository.mark_processing(document.id)

    if status == "error":
        assert repository.fail(
            document.id,
            "processing_failed",
            "Test processing failure",
        )

    response = client.post(
        "/chat/ask",
        json={
            "question": "кредит процент",
            "document_ids": [str(document.id)],
        },
    )

    assert_error(response, 409, "document_not_ready")


def test_deleted_document_returns_404(
    client: TestClient,
) -> None:
    document_id = upload_ready(
        client,
        "Кредит.txt",
        "Кредит приносит процентный доход.".encode(),
    )

    deleted = client.delete(f"/documents/{document_id}")
    assert deleted.status_code == 204

    response = client.post(
        "/chat/ask",
        json={
            "question": "кредит процент",
            "document_ids": [document_id],
        },
    )

    assert_error(response, 404, "document_not_found")


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"question": None},
        {"question": ""},
        {"question": " \t\n "},
        {"question": 123},
        {"question": "вопрос", "document_ids": []},
        {"question": "вопрос", "document_ids": ["not-a-uuid"]},
        {"question": "вопрос", "document_ids": "bad"},
    ],
)
def test_invalid_chat_request_returns_422(
    client: TestClient,
    payload: dict,
) -> None:
    response = client.post("/chat/ask", json=payload)
    assert_error(response, 422, "invalid_question")


def test_question_over_2000_characters(
    client: TestClient,
) -> None:
    response = client.post(
        "/chat/ask",
        json={"question": "  " + "ж" * 2001 + "  "},
    )

    assert_error(response, 422, "question_too_long")


def test_question_exactly_2000_characters_is_valid(
    client: TestClient,
) -> None:
    response = client.post(
        "/chat/ask",
        json={"question": " " + "ж" * 2000 + " "},
    )

    assert_error(response, 409, "no_ready_documents")


def test_malformed_json_returns_invalid_question(
    client: TestClient,
) -> None:
    response = client.post(
        "/chat/ask",
        content="{invalid json",
        headers={"content-type": "application/json"},
    )

    assert_error(response, 422, "invalid_question")


class FailingLLM(LLMAdapter):
    def generate(self, question: str, context: str) -> str:
        raise RuntimeError("Model connection failed")


def test_llm_failure_returns_503(
    client: TestClient,
) -> None:
    document_id = upload_ready(
        client,
        "Кредит.txt",
        "Кредит приносит процентный доход.".encode(),
    )

    client.app.state.llm_adapter = FailingLLM()

    response = client.post(
        "/chat/ask",
        json={
            "question": "кредит процентный доход",
            "document_ids": [document_id],
        },
    )

    assert_error(response, 503, "llm_unavailable")


def test_unexpected_dependency_failure_returns_safe_500(
    tmp_path: Path,
) -> None:
    application = create_app(
        settings=Settings(
            _env_file=None,
            data_dir=tmp_path,
        )
    )

    def broken_dependency() -> None:
        raise RuntimeError("/private/secret/internal/path")

    application.dependency_overrides[get_chat_service] = broken_dependency

    with TestClient(
        application,
        raise_server_exceptions=False,
    ) as test_client:
        response = test_client.post(
            "/chat/ask",
            json={"question": "кредит процент"},
        )

    assert_error(response, 500, "internal_error")
    assert "/private/secret" not in response.text


def test_existing_document_validation_is_unchanged(
    client: TestClient,
) -> None:
    response = client.get("/documents/not-a-uuid")

    assert_error(response, 422, "validation_error")
