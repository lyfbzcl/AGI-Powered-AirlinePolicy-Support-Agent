import re
from typing import Any, Optional

from policy_metadata import POLICY_AREA_KEYWORDS, normalize_text


FOLLOW_UP_PREFIXES = (
    "but ",
    "actually ",
    "also ",
    "and ",
    "what about ",
    "how about ",
    "in that case",
)

AIR_TRAVEL_TERMS = (
    "passenger",
    "ticket",
    "fare",
    "flight",
    "journey",
    "booking",
    "first class",
    "business class",
    "economy",
    "airport",
)

QUESTION_TERMS = (
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
    "how",
    "can",
    "could",
    "do",
    "does",
    "is",
    "are",
    "will",
    "would",
    "should",
)


def detect_explicit_policy_area(text: str) -> str:
    """Infer policy area only from user-authored text, never from retrieval."""
    lowered = normalize_text(text)
    best_area = "general"
    best_hits = 0
    for area, keywords in POLICY_AREA_KEYWORDS.items():
        hits = sum(1 for keyword in keywords if keyword in lowered)
        if hits > best_hits:
            best_area = area
            best_hits = hits
    return best_area


def _looks_like_follow_up(text: str) -> bool:
    lowered = normalize_text(text)
    word_count = len(re.findall(r"[a-zA-Z0-9'-]+", lowered))
    starts_as_follow_up = any(lowered.startswith(prefix) for prefix in FOLLOW_UP_PREFIXES)
    is_short_personal_detail = (
        word_count <= 14
        and any(term in lowered for term in ("i'm", "i am", "my ", "we are", "we're"))
        and any(term in lowered for term in AIR_TRAVEL_TERMS)
    )
    return starts_as_follow_up or is_short_personal_detail


def _has_question_signal(text: str) -> bool:
    lowered = normalize_text(text)
    first_word = lowered.split(" ", 1)[0] if lowered else ""
    return "?" in text or first_word in QUESTION_TERMS


def _find_history_anchor(
    history_turns: Optional[list[dict[str, Any]]],
) -> tuple[str, str]:
    for turn in reversed(history_turns or []):
        prior_question = str(turn.get("question", "")).strip()
        policy_area = detect_explicit_policy_area(prior_question)
        if prior_question and policy_area != "general":
            return prior_question, policy_area
    return "", "general"


def resolve_query_context(
    question: str,
    history_turns: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    """Resolve whether a turn is a standalone request, a follow-up, or goal-ambiguous."""
    current_area = detect_explicit_policy_area(question)
    anchor_question, anchor_area = _find_history_anchor(history_turns)
    follows_history = (
        current_area == "general"
        and anchor_area != "general"
        and _looks_like_follow_up(question)
    )

    if follows_history:
        effective_question = (
            f"{anchor_question}\nAdditional user detail: {question.strip()}"
        )
        resolved_area = anchor_area
        dialogue_act = "follow_up_detail"
    else:
        effective_question = question.strip()
        resolved_area = current_area
        dialogue_act = "standalone_request"

    has_air_travel_signal = any(
        term in normalize_text(question) for term in AIR_TRAVEL_TERMS
    )
    goal_ambiguous = (
        resolved_area == "general"
        and not follows_history
        and not _has_question_signal(question)
    )

    return {
        "dialogue_act": "ambiguous_fragment" if goal_ambiguous else dialogue_act,
        "current_policy_area": current_area,
        "resolved_policy_area": resolved_area,
        "effective_question": effective_question,
        "history_anchor_question": anchor_question if follows_history else "",
        "used_history": follows_history,
        "goal_ambiguous": goal_ambiguous,
        "has_air_travel_signal": has_air_travel_signal,
    }


def build_goal_clarification(question: str, query_analysis: dict[str, Any]) -> str:
    """Ask for the user's goal without inventing a policy category."""
    if query_analysis.get("has_air_travel_signal"):
        return (
            "What would you like to know about that travel detail—for example, "
            "baggage allowance, changing the flight, cancellation, or a refund?"
        )
    return (
        "I’m not sure what airline-policy question you want answered. "
        "Could you describe what you need help with?"
    )
