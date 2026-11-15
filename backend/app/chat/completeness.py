"""Conservative evidence check for composite actor-and-year questions."""

import re
from collections.abc import Sequence

# This guard covers a narrow answer shape, not full semantic entailment.
YEAR_PATTERN = re.compile(r"\b[12]\d{3}\b")
ACTOR_QUESTION = re.compile(r"\b(?:кто|кем)\b", re.IGNORECASE)
YEAR_QUESTION = re.compile(r"\bв\s+каком\s+году\b", re.IGNORECASE)
NAME_PATTERN = re.compile(r"\b([А-ЯЁ][а-яё]+)\s+(?:[А-ЯЁ][а-яё]+|[IVXLCDM]{1,8})\b")
WORD_PATTERN = re.compile(r"[^\W_]+", re.UNICODE)
# Only action classes with a stable five-character Russian prefix.
EVENT_STEMS = frozenset(
    {"приня", "подпи", "созда", "основ", "утвер", "постр", "изобр", "избра", "откры"}
)
ACTOR_STEMS = frozenset(
    {
        "корол",
        "парла",
        "совет",
        "собра",
        "сенат",
        "прези",
        "прави",
        "комис",
        "минис",
        "автор",
        "учены",
        "групп",
        "иссл",
        "орган",
        "еписк",
        "папа",
    }
)


def _stems(text: str) -> set[str]:
    """Compare spelling variants using the MVP five-character normalization."""
    return {
        word[:5] for word in WORD_PATTERN.findall(text.lower().replace("ё", "е")) if len(word) >= 3
    }


def _sentences(text: str) -> list[str]:
    """Split passages, preserving dates such as '1534 г.' as one sentence."""
    protected = re.sub(r"(\b[12]\d{3}\s+г)\.", r"\1§", text)
    return re.split(r"(?<=[.!?])\s+|\n+", protected)


def has_supported_actor_and_year(
    question: str,
    answer: str,
    passages: Sequence[str],
) -> bool:
    """Reject an incomplete 'year + actor' answer without direct joint evidence.

    For all other question shapes the legacy LLM decision remains authoritative.
    This intentionally prefers refusal over guessing and is not a general NLI tool.
    """
    if not (ACTOR_QUESTION.search(question) and YEAR_QUESTION.search(question)):
        return True

    events = EVENT_STEMS & _stems(question)
    if not events:
        return True

    years = set(YEAR_PATTERN.findall(answer))
    if not years:
        return False

    # The response must actually identify an actor, not just repeat the date.
    actor_candidates = set(ACTOR_STEMS & _stems(answer))
    named_actors = {
        match.group(1).lower().replace("ё", "е")[:5] for match in NAME_PATTERN.finditer(answer)
    }
    actor_candidates.update(named_actors)
    if not actor_candidates:
        return False

    # Accept only if an *actually transmitted* sentence links the year,
    # event and the stated actor. Mere mentions in nearby sentences are not proof.
    for passage in passages:
        for sentence in _sentences(passage):
            stems = _stems(sentence)
            if (
                years & set(YEAR_PATTERN.findall(sentence))
                and events & stems
                and actor_candidates & stems
                and (not named_actors or named_actors <= stems)
            ):
                return True
    return False
