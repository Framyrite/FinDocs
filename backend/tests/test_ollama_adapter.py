"""Offline tests for the Ollama language model adapter."""

import json

import httpx
import pytest

from app.core.config import Settings
from app.llm.errors import LLMInsufficientContext, LLMUnavailable
from app.llm.ollama import OllamaLLMAdapter


def test_ollama_generates_answer() -> None:
    def handle_request(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/api/chat"

        payload = json.loads(request.content)

        assert payload["model"] == "qwen3.5:4b-q4_K_M"
        assert payload["stream"] is False
        assert payload["think"] is False
        assert payload["options"]["temperature"] == 0

        return httpx.Response(
            200,
            json={
                "done": True,
                "done_reason": "stop",
                "message": {
                    "role": "assistant",
                    "content": json.dumps(
                        {
                            "supported": True,
                            "answer": "Облигация — долговая ценная бумага.",
                        }
                    ),
                },
            },
        )

    adapter = OllamaLLMAdapter(
        settings=Settings(_env_file=None),
        transport=httpx.MockTransport(handle_request),
    )

    answer = adapter.generate(
        question="Что такое облигация?",
        context="Облигация — долговая ценная бумага.",
    )

    assert answer == "Облигация — долговая ценная бумага."


def make_adapter(response: httpx.Response) -> OllamaLLMAdapter:
    return OllamaLLMAdapter(
        settings=Settings(_env_file=None),
        transport=httpx.MockTransport(lambda request: response),
    )


@pytest.mark.parametrize(
    ("supported", "answer", "expected_error"),
    [
        (False, "", LLMInsufficientContext),
        (False, "Ответ при отказе", LLMUnavailable),
        (True, "", LLMUnavailable),
    ],
)
def test_model_refusal_and_empty_answer(
    supported: bool,
    answer: str,
    expected_error: type[Exception],
) -> None:
    response = httpx.Response(
        200,
        json={
            "done": True,
            "message": {
                "role": "assistant",
                "content": json.dumps({"supported": supported, "answer": answer}),
            },
        },
    )

    with pytest.raises(expected_error):
        make_adapter(response).generate("Вопрос", "Контекст")


@pytest.mark.parametrize(
    "content",
    [
        "not valid json",
        "{}",
        '{"supported": "true", "answer": "Ответ"}',
        '{"supported": true}',
        '{"supported": true, "answer": 123}',
        '{"supported": true, "answer": "Ответ", "extra": 1}',
    ],
)
def test_invalid_model_format(content: str) -> None:
    response = httpx.Response(
        200,
        json={
            "done": True,
            "message": {"role": "assistant", "content": content},
        },
    )

    with pytest.raises(LLMUnavailable):
        make_adapter(response).generate("Вопрос", "Контекст")


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(404),
        httpx.Response(500),
        httpx.Response(200, json={"done": False}),
        httpx.Response(
            200,
            json={"done": True, "done_reason": "length"},
        ),
        httpx.Response(200, json={"done": True}),
        httpx.Response(
            200,
            json={
                "done": True,
                "message": {"role": "assistant", "content": None},
            },
        ),
    ],
)
def test_invalid_http_responses(response: httpx.Response) -> None:
    with pytest.raises(LLMUnavailable):
        make_adapter(response).generate("Вопрос", "Контекст")


@pytest.mark.parametrize(
    "error_type",
    [httpx.ConnectError, httpx.ReadTimeout],
)
def test_network_errors(
    error_type: type[httpx.RequestError],
) -> None:
    def fail_request(request: httpx.Request) -> httpx.Response:
        raise error_type("Connection failed")

    adapter = OllamaLLMAdapter(
        settings=Settings(_env_file=None),
        transport=httpx.MockTransport(fail_request),
    )

    with pytest.raises(LLMUnavailable):
        adapter.generate("Вопрос", "Контекст")


def test_empty_question() -> None:
    adapter = make_adapter(httpx.Response(200))

    with pytest.raises(ValueError):
        adapter.generate("   ", "Контекст")


def test_invalid_input_types() -> None:
    adapter = make_adapter(httpx.Response(200))

    with pytest.raises(TypeError):
        adapter.generate(123, "Контекст")

    with pytest.raises(TypeError):
        adapter.generate("Вопрос", None)


@pytest.mark.parametrize(
    "role",
    [None, "user", "system", "tool", ""],
)
def test_invalid_message_role(role: str | None) -> None:
    message = {
        "content": json.dumps({"supported": True, "answer": "Корректный ответ."}),
    }

    if role is not None:
        message["role"] = role

    response = httpx.Response(
        200,
        json={
            "done": True,
            "done_reason": "stop",
            "message": message,
        },
    )

    with pytest.raises(
        LLMUnavailable,
        match="Invalid Ollama message role",
    ):
        make_adapter(response).generate("Вопрос", "Контекст")
