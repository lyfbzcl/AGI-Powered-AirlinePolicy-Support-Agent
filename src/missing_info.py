import re
from typing import Any, Optional

from policy_metadata import POLICY_AREA_KEYWORDS, infer_policy_area, normalize_text


FIELD_LABELS = {
    "fare_type": "fare type or fare family",
    "route": "route or whether the journey is domestic/international",
    "cancellation_time": "whether cancellation is before or after departure",
    "cancellation_reason": "reason for cancellation",
    "voluntary_or_disruption": "whether this is voluntary or airline-caused",
    "cabin": "cabin or ticket class",
    "bag_weight": "bag weight or size",
    "operating_carrier": "operating carrier or partner airline involvement",
    "delay_length": "delay length",
    "delay_reason": "reason for delay",
    "final_arrival_delay": "final arrival delay",
    "change_time": "when the change is requested",
    "new_route_or_date": "new travel date, time, or route",
}

REQUIRED_FIELDS = {
    "refund": ["fare_type", "cancellation_time", "cancellation_reason", "route"],
    "cancellation": ["fare_type", "cancellation_time", "voluntary_or_disruption"],
    "baggage": ["fare_type", "route", "cabin", "bag_weight"],
    "delay": ["delay_length", "route", "delay_reason", "final_arrival_delay"],
    "flight_change": ["fare_type", "change_time", "new_route_or_date"],
    "check_in": ["route"],
}

SPECIFIC_DECISION_PATTERNS = [
    r"\bcan i\b",
    r"\bam i\b",
    r"\bdo i qualify\b",
    r"\beligible\b",
    r"\bhow much\b",
    r"\bwithout (a )?fee\b",
    r"\bwill i get\b",
    r"\bmust i pay\b",
]


def detect_policy_area(question: str, retrieved_chunks: Optional[list[dict[str, Any]]] = None) -> str:
    """Infer the policy area from the question, falling back to retrieved chunks."""
    lowered = normalize_text(question)
    best_area = "general"
    best_hits = 0
    for area, keywords in POLICY_AREA_KEYWORDS.items():
        hits = sum(1 for keyword in keywords if keyword in lowered)
        if hits > best_hits:
            best_area = area
            best_hits = hits

    if best_area != "general":
        return best_area

    chunks = retrieved_chunks or []
    if chunks:
        return str(chunks[0].get("policy_area") or infer_policy_area(chunks[0].get("source", ""), chunks[0].get("text", "")))
    return best_area


def requires_specific_decision(question: str, policy_area: str) -> bool:
    lowered = normalize_text(question)
    return any(re.search(pattern, lowered) for pattern in SPECIFIC_DECISION_PATTERNS)


def _has_any(text: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, text) for pattern in patterns)


def detect_present_fields(question: str) -> set[str]:
    lowered = normalize_text(question)
    present: set[str] = set()

    if _has_any(lowered, [r"\bbasic\b", r"\bpromo", r"\bdiscount", r"\bflex", r"\brefundable\b", r"\bnon[- ]?refundable\b", r"\bfare family\b", r"\bgroup\b", r"\bcharter\b"]):
        present.add("fare_type")
    if _has_any(lowered, [r"\beconomy\b", r"\bbusiness(?: class)?\b", r"\bfirst(?: class)?\b", r"\bpremium(?: economy)?\b"]):
        present.add("cabin")
    if _has_any(lowered, [r"\bdomestic\b", r"\binternational\b", r"\broute\b", r"\bfrom .+ to .+\b", r"\bpartner\b", r"\bcodeshare\b"]):
        present.add("route")
    if _has_any(lowered, [r"\bbefore departure\b", r"\bafter departure\b", r"\bdeparted\b", r"\bno[- ]?show\b", r"\bday before\b", r"\bhours? before\b", r"\bclose to departure\b", r"\bmiss(ed)? my flight\b"]):
        present.add("cancellation_time")
        present.add("change_time")
    if _has_any(lowered, [r"\billness\b", r"\bmedical\b", r"\bdeath\b", r"\bbereavement\b", r"\bmilitary\b", r"\bjury\b", r"\bvisa\b", r"\bweather\b", r"\bairline cancel", r"\bdisruption\b", r"\bvoluntary\b"]):
        present.add("cancellation_reason")
        present.add("voluntary_or_disruption")
        present.add("delay_reason")
    if _has_any(lowered, [r"\bkg\b", r"\blb\b", r"\boverweight\b", r"\boversize\b", r"\btoo heavy\b", r"\b\d+\s*(kg|kilogram|lb|pound)"]):
        present.add("bag_weight")
    if _has_any(lowered, [r"\boperated by\b", r"\boperating carrier\b", r"\bpartner\b", r"\bcodeshare\b"]):
        present.add("operating_carrier")
    if _has_any(lowered, [r"\b\d+\s*(hour|hr|minute|min|day)s?\b", r"\bovernight\b", r"\bextended delay\b", r"\blong delay\b"]):
        present.add("delay_length")
    if _has_any(lowered, [r"\barrival\b", r"\barrive\b", r"\bfinal destination\b"]):
        present.add("final_arrival_delay")
    if _has_any(lowered, [r"\bchange to\b", r"\bnew flight\b", r"\bearlier\b", r"\blater\b", r"\btomorrow\b", r"\bnext week\b", r"\bdifferent date\b", r"\bdifferent route\b"]):
        present.add("new_route_or_date")
    return present


def detect_missing_info(question: str, retrieved_chunks: Optional[list[dict[str, Any]]] = None) -> dict[str, Any]:
    policy_area = detect_policy_area(question, retrieved_chunks)
    required = REQUIRED_FIELDS.get(policy_area, [])
    present = detect_present_fields(question)
    needs_specific = requires_specific_decision(question, policy_area)
    missing = [field for field in required if field not in present] if needs_specific else []

    return {
        "policy_area": policy_area,
        "requires_specific_decision": needs_specific,
        "required_fields": required,
        "present_fields": sorted(present),
        "missing_fields": missing,
        "missing_field_labels": [FIELD_LABELS.get(field, field) for field in missing],
    }


def build_clarifying_question(missing_info: dict[str, Any]) -> str:
    labels = missing_info.get("missing_field_labels", [])
    policy_area = str(missing_info.get("policy_area", "policy")).replace("_", " ")
    if not labels:
        return "Could you provide a little more detail so I can check the policy safely?"
    if len(labels) == 1:
        fields = labels[0]
    elif len(labels) == 2:
        fields = f"{labels[0]} and {labels[1]}"
    else:
        fields = ", ".join(labels[:-1]) + f", and {labels[-1]}"
    return f"To make a safe {policy_area} decision, I need the {fields}."
