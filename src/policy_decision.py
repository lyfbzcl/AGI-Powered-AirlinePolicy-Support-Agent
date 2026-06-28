from typing import Any, Optional

from conflict_resolution import describe_priority_rule, detect_policy_conflict
from missing_info import build_clarifying_question, detect_missing_info
from query_understanding import build_goal_clarification, resolve_query_context


def make_handoff_packet(
    question: str,
    retrieved_chunks: list[dict[str, Any]],
    missing_info: dict[str, Any],
    verification: Optional[dict[str, Any]],
    escalation_reason: str,
    draft_answer: str = "",
) -> dict[str, Any]:
    return {
        "original_question": question,
        "detected_intent": missing_info.get("policy_area", "general"),
        "missing_fields": missing_info.get("missing_fields", []),
        "retrieved_sources": [
            {
                "rank": index,
                "source": chunk.get("source", "unknown"),
                "chunk_id": chunk.get("chunk_id", "unknown"),
                "policy_area": chunk.get("policy_area", "general"),
                "priority": chunk.get("priority", 0),
            }
            for index, chunk in enumerate(retrieved_chunks, start=1)
        ],
        "draft_answer": draft_answer,
        "verification_result": verification or {},
        "reason_for_escalation": escalation_reason,
        "recommended_next_step": build_next_step(missing_info, escalation_reason),
    }


def build_next_step(missing_info: dict[str, Any], escalation_reason: str) -> str:
    if missing_info.get("missing_fields"):
        return build_clarifying_question(missing_info)
    if "conflict" in escalation_reason.lower():
        return f"Review source priority manually. Priority rule: {describe_priority_rule()}"
    if "support" in escalation_reason.lower() or "verification" in escalation_reason.lower():
        return "Review the retrieved sources and confirm whether the draft answer is fully supported."
    return "Review the case manually before giving a binding policy decision."


def evaluate_policy_decision(
    question: str,
    retrieved_chunks: list[dict[str, Any]],
    draft_answer: str = "",
    verification: Optional[dict[str, Any]] = None,
    history_turns: Optional[list[dict[str, Any]]] = None,
    query_analysis: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Decide whether the system should answer, clarify, or escalate."""
    analysis = query_analysis or resolve_query_context(question, history_turns)
    effective_question = str(analysis.get("effective_question") or question)

    if analysis.get("goal_ambiguous"):
        missing = detect_missing_info(effective_question)
        question_text = build_goal_clarification(question, analysis)
        missing["missing_fields"] = ["user_goal"]
        missing["missing_field_labels"] = ["what the user wants help with"]
        return {
            "action": "clarify",
            "reason_code": "missing_user_goal",
            "missing_info": missing,
            "query_analysis": analysis,
            "clarifying_question": question_text,
            "confidence_reason": (
                "The turn contains context or a passenger detail, but no policy goal "
                "has been established."
            ),
            "escalation_reason": "",
            "handoff_packet": {},
        }

    if analysis.get("resolved_policy_area") == "general":
        missing = detect_missing_info(effective_question)
        reason = "The current policy set does not cover the user's question."
        handoff_packet = make_handoff_packet(
            question,
            retrieved_chunks,
            missing,
            verification,
            reason,
            draft_answer,
        )
        handoff_packet["reason_code"] = "unsupported_policy_area"
        return {
            "action": "escalate",
            "reason_code": "unsupported_policy_area",
            "missing_info": missing,
            "query_analysis": analysis,
            "clarifying_question": "",
            "confidence_reason": (
                "The question does not match any policy area covered by the "
                "current knowledge base."
            ),
            "escalation_reason": reason,
            "handoff_packet": handoff_packet,
        }

    missing = detect_missing_info(effective_question, retrieved_chunks)

    if not retrieved_chunks:
        reason = "No policy evidence was retrieved."
        return {
            "action": "escalate",
            "reason_code": "no_retrieval_evidence",
            "missing_info": missing,
            "query_analysis": analysis,
            "clarifying_question": "",
            "confidence_reason": "Retrieval returned no sources.",
            "escalation_reason": reason,
            "handoff_packet": make_handoff_packet(question, retrieved_chunks, missing, verification, reason, draft_answer),
        }

    if missing.get("missing_fields"):
        question_text = build_clarifying_question(missing)
        return {
            "action": "clarify",
            "reason_code": "missing_decision_fields",
            "missing_info": missing,
            "query_analysis": analysis,
            "clarifying_question": question_text,
            "confidence_reason": "The request asks for a specific policy decision but lacks required fields.",
            "escalation_reason": "",
            "handoff_packet": {},
        }

    conflict = detect_policy_conflict(question, retrieved_chunks)
    if conflict["has_conflict"]:
        reason = conflict["reason"]
        return {
            "action": "escalate",
            "reason_code": "policy_conflict",
            "missing_info": missing,
            "query_analysis": analysis,
            "clarifying_question": "",
            "confidence_reason": "Retrieved evidence may require manual priority review.",
            "escalation_reason": reason,
            "handoff_packet": make_handoff_packet(question, retrieved_chunks, missing, verification, reason, draft_answer),
        }

    if verification and verification.get("verdict") in {"fail", "needs_human"}:
        reason = "Answer verification did not confirm source support."
        return {
            "action": "escalate",
            "reason_code": "answer_not_verified",
            "missing_info": missing,
            "query_analysis": analysis,
            "clarifying_question": "",
            "confidence_reason": "Draft answer is not sufficiently grounded in retrieved evidence.",
            "escalation_reason": reason,
            "handoff_packet": make_handoff_packet(question, retrieved_chunks, missing, verification, reason, draft_answer),
        }

    return {
        "action": "answer",
        "reason_code": "verified_answer",
        "missing_info": missing,
        "query_analysis": analysis,
        "clarifying_question": "",
        "confidence_reason": "Required fields are present or not needed, and retrieved evidence is usable.",
        "escalation_reason": "",
        "handoff_packet": {},
    }
