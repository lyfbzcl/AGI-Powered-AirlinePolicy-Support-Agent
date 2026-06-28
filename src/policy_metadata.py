import hashlib
import re
from pathlib import Path
from typing import Any


POLICY_AREA_KEYWORDS = {
    "refund": ["refund", "reimburse", "money back", "cash back"],
    "cancellation": ["cancel", "cancellation", "no-show", "no show"],
    "baggage": ["baggage", "bag", "checked bag", "carry-on", "carry on", "luggage"],
    "check_in": ["check-in", "check in", "boarding", "document", "airport counter"],
    "delay": ["delay", "compensation", "disruption", "rebooking", "rerouting"],
    "flight_change": ["change", "reschedule", "same-day", "standby", "new flight"],
}

SOURCE_POLICY_AREAS = {
    "refund_policy.txt": "refund",
    "cancellation_policy.txt": "cancellation",
    "baggage_policy.txt": "baggage",
    "check_in_policy.txt": "check_in",
    "delay_compensation_policy.txt": "delay",
    "flight_change_policy.txt": "flight_change",
}

DEFAULT_EFFECTIVE_DATE = "2026-01-01"
DEFAULT_VERSION = "v1"


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.lower()).strip()


def infer_policy_area(source: str, text: str = "") -> str:
    """Infer a coarse policy area from file name first, then content keywords."""
    source_name = Path(source).name
    if source_name in SOURCE_POLICY_AREAS:
        return SOURCE_POLICY_AREAS[source_name]

    haystack = normalize_text(f"{source_name} {text}")
    best_area = "general"
    best_hits = 0
    for area, keywords in POLICY_AREA_KEYWORDS.items():
        hits = sum(1 for keyword in keywords if keyword in haystack)
        if hits > best_hits:
            best_area = area
            best_hits = hits
    return best_area


def infer_priority(policy_area: str, text: str = "") -> int:
    """Higher priority means the chunk is more specific for decision ordering."""
    lowered = normalize_text(text)
    priority = 20
    if "important note" in lowered:
        priority += 5
    if any(term in lowered for term in ["fare rules", "fare conditions", "booking confirmation"]):
        priority += 10
    if any(term in lowered for term in ["route", "local law", "market", "jurisdiction"]):
        priority += 8
    if any(term in lowered for term in ["exception", "case-by-case", "supporting documents"]):
        priority += 12
    if policy_area == "general":
        priority -= 5
    return priority


def document_hash(text: str) -> str:
    """Return a stable short hash for lifecycle and cache invalidation."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def enrich_chunk_metadata(chunk: dict[str, Any]) -> dict[str, Any]:
    """Return a chunk with lightweight metadata required by reliability checks."""
    source = str(chunk.get("source", "unknown"))
    text = str(chunk.get("text", ""))
    policy_area = str(chunk.get("policy_area") or infer_policy_area(source, text))
    enriched = dict(chunk)
    enriched.setdefault("policy_area", policy_area)
    enriched.setdefault("effective_date", DEFAULT_EFFECTIVE_DATE)
    enriched.setdefault("version", DEFAULT_VERSION)
    enriched.setdefault("priority", infer_priority(policy_area, text))
    enriched.setdefault("jurisdiction", "general")
    enriched.setdefault("route_scope", "general")
    enriched.setdefault("doc_hash", document_hash(f"{source}\n{text}"))
    return enriched


def enrich_chunks(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [enrich_chunk_metadata(chunk) for chunk in chunks]
