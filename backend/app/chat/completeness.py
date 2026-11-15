"""Conservative evidence check for composite actor-and-year questions."""

import re
from collections.abc import Sequence

# This guard covers a narrow answer shape, not full semantic entailment.
YEAR_PATTERN = re.compile(r"\b[12]\d{3}\b")
ACTOR_QUESTION = re.compile(r"\b(?:кто|кем)\b", re.IGNORECASE)
YEAR_QUESTION = re.compile(r"\bв\s+каком\s+году\b", re.IGNORECASE)
NAME_PATTERN = re.compile(r"\b([А-ЯЁ][а-яё]+)\s+([А-ЯЁ][а-яё]+|[IVXLCDM]{1,8})\b")
WORD_PATTERN = re.compile(r"[^\W_]+", re.UNICODE)
EVENT_OBJECT_PATTERN = re.compile(
    r"\b(?:принят\w*|подписан\w*|создан\w*|основан\w*|"
    r"утвержд\w*|построен\w*|изобретен\w*|избран\w*|открыт\w*)"
    r"\s+([^,?.;]+)",
    re.IGNORECASE,
)
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


def _people(text: str) -> set[tuple[str, str]]:
    """Extract names with surnames or Roman numerals (including inflections)."""
    result: set[tuple[str, str]] = set()
    for match in NAME_PATTERN.finditer(text):
        first = match.group(1).casefold().replace("ё", "е")
        second = match.group(2)
        if re.fullmatch(r"[IVXLCDM]+", second) is None:
            second = second.casefold().replace("ё", "е")
        result.add((first, second))
    return result


def _matching_person(expected: tuple[str, str], actual: tuple[str, str]) -> bool:
    """Do not conflate VII and VIII; allow common Russian case endings."""
    for wanted, found in zip(expected, actual, strict=True):
        if re.fullmatch(r"[IVXLCDM]+", wanted) or re.fullmatch(
            r"[IVXLCDM]+", found
        ):
            if wanted != found:
                return False
            continue
        common = min(5, len(wanted), len(found))
        if common < 3 or wanted[:common] != found[:common]:
            return False
    return True


def _event_object_terms(question: str) -> set[str]:
    """Use the event's noun phrase, excluding descriptive clauses after commas."""
    match = EVENT_OBJECT_PATTERN.search(question)
    return _stems(match.group(1)) if match is not None else set()


def has_supported_actor_and_year(
    question: str,
    answer: str,
    passages: Sequence[str],
) -> bool:
    """Require the same year, action, event and named actor in one passage sentence.

    This guard covers only selected Russian question shapes; it is not NLI.
    """
    if not (ACTOR_QUESTION.search(question) and YEAR_QUESTION.search(question)):
        return True

    actions = EVENT_STEMS & _stems(question)
    if not actions:
        return True

    target = _event_object_terms(question)
    years = set(YEAR_PATTERN.findall(answer))
    people = _people(answer)
    institutions = ACTOR_STEMS & _stems(answer)
    if not target or not years or not (people or institutions):
        return False

    for passage in passages:
        for sentence in _sentences(passage):
            stems = _stems(sentence)
            if not (
                years & set(YEAR_PATTERN.findall(sentence))
                and actions & stems
                and target <= stems
            ):
                continue
            if people:
                mentioned = _people(sentence)
                if all(
                    any(_matching_person(person, item) for item in mentioned)
                    for person in people
                ):
                    return True
            elif institutions & stems:
                return True
    return False
