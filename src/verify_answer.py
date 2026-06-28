import re
from typing import Any


STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "can", "for", "from",
    "if", "in", "is", "it", "may", "of", "on", "or", "should", "that",
    "the", "this", "to", "was", "when", "where", "will", "with", "you",
    "your", "passenger", "passengers", "airline", "policy",
}


def tokenize(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", text.lower())
        if token not in STOPWORDS
    }


def split_sentences(text: str) -> list[str]:
    return [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+", text.strip())
        if sentence.strip()
    ]


def verify_answer_support(
    question: str,
    answer: str,
    retrieved_chunks: list[dict[str, Any]],
    min_overlap: float = 0.16,
) -> dict[str, Any]:
    """Heuristically verify that answer claims are supported by retrieved text."""
    context = " ".join(str(chunk.get("text", "")) for chunk in retrieved_chunks)
    if not retrieved_chunks:
        return {
            "verdict": "fail",
            "supported": False,
            "citation_quality": "missing",
            "unsupported_claims": ["No retrieved policy evidence was available."],
        }

    context_terms = tokenize(context)
    if not context_terms:
        return {
            "verdict": "fail",
            "supported": False,
            "citation_quality": "missing",
            "unsupported_claims": ["Retrieved policy evidence was empty."],
        }

    unsupported: list[str] = []
    checked = 0
    for sentence in split_sentences(answer):
        sentence_terms = tokenize(sentence)
        if len(sentence_terms) < 4:
            continue
        checked += 1
        overlap = len(sentence_terms & context_terms) / max(len(sentence_terms), 1)
        if overlap < min_overlap:
            unsupported.append(sentence)

    if checked == 0:
        return {
            "verdict": "needs_human",
            "supported": False,
            "citation_quality": "weak",
            "unsupported_claims": ["The answer did not contain enough policy detail to verify."],
        }

    if unsupported:
        return {
            "verdict": "fail",
            "supported": False,
            "citation_quality": "weak",
            "unsupported_claims": unsupported,
        }

    return {
        "verdict": "pass",
        "supported": True,
        "citation_quality": "strong",
        "unsupported_claims": [],
    }
