"""Regression checks for conservative composite-answer completeness."""

from app.chat.completeness import has_supported_actor_and_year

QUESTION = (
    "В каком году и кем был принят Акт о супрематии, ознаменовавший рождение англиканской церкви?"
)


def test_d03_rejects_year_only_when_actor_is_missing() -> None:
    context = [
        "Первый период длится с 1534 г. (принятие акта о супрематии). "
        "Генрих VIII стремился отделить церковь от Рима."
    ]
    answer = (
        "Акт о супрематии был принят в 1534 году. "
        "Именно это событие ознаменовало рождение англиканской церкви."
    )
    assert not has_supported_actor_and_year(QUESTION, answer, context)


def test_name_mentioned_without_adoption_does_not_prove_actor() -> None:
    context = [
        "Первый период длится с 1534 г. (принятие акта о супрематии). "
        "Генрих VIII стремился отделить церковь от Рима."
    ]
    answer = "Акт принят в 1534 году королём Генрихом VIII."
    assert not has_supported_actor_and_year(QUESTION, answer, context)


def test_explicit_same_sentence_attribution_is_accepted() -> None:
    context = ["В 1534 году король Генрих VIII принял Акт о супрематии."]
    answer = "Акт о супрематии был принят королём Генрихом VIII в 1534 году."
    assert has_supported_actor_and_year(QUESTION, answer, context)


def test_institutional_actor_is_accepted_when_directly_supported() -> None:
    context = ["В 1534 году парламент принял акт о супрематии."]
    answer = "Акт был принят парламентом в 1534 году."
    assert has_supported_actor_and_year(QUESTION, answer, context)


def test_source_outside_actual_context_is_not_usable() -> None:
    answer = "Акт был принят парламентом в 1534 году."
    assert not has_supported_actor_and_year(
        QUESTION,
        answer,
        ["Акт был принят в 1534 году."],
    )


def test_other_questions_keep_existing_behavior() -> None:
    for question in (
        "Почему SJF сложно применять?",
        "В каком году был принят акт?",
        "Кем был принят акт?",
        "Какой алгоритм невытесняющий и использует FIFO?",
    ):
        assert has_supported_actor_and_year(question, "Любой ответ.", [])
