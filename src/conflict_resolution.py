from typing import Any


def sort_by_policy_priority(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return chunks ordered by policy specificity and recency metadata."""
    return sorted(
        chunks,
        key=lambda chunk: (
            int(chunk.get("priority", 0) or 0),
            str(chunk.get("effective_date", "")),
            str(chunk.get("version", "")),
        ),
        reverse=True,
    )


def detect_policy_conflict(question: str, chunks: list[dict[str, Any]]) -> dict[str, Any]:
    """Detect lightweight conflict signals in retrieved evidence.

    This does not try to solve all legal/policy conflicts. It flags cases where
    multiple active policy areas or equal-priority sources could support
    different decisions and therefore deserve human review.
    """
    if len(chunks) < 2:
        return {"has_conflict": False, "reason": "", "ordered_chunks": chunks}

    ordered = sort_by_policy_priority(chunks)
    policy_areas = {str(chunk.get("policy_area", "general")) for chunk in chunks}
    top_priority = int(ordered[0].get("priority", 0) or 0)
    tied_top = [
        chunk
        for chunk in ordered
        if int(chunk.get("priority", 0) or 0) == top_priority
    ]
    tied_sources = {str(chunk.get("source", "unknown")) for chunk in tied_top}

    if len(tied_sources) > 1 and len(policy_areas) > 1:
        return {
            "has_conflict": True,
            "reason": "Top-ranked evidence comes from multiple policy areas with equal priority.",
            "ordered_chunks": ordered,
        }

    return {"has_conflict": False, "reason": "", "ordered_chunks": ordered}


def describe_priority_rule() -> str:
    return (
        "Specific fare, route, legal, or exception language is prioritized over "
        "general policy language; newer effective dates are preferred when available."
    )
