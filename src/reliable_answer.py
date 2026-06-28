from typing import Any, Callable, Optional

from answer import answer_question
from conversation_answer import answer_conversation_question
from handoff import CUSTOMER_HANDOFF_MESSAGE, UNSUPPORTED_POLICY_HANDOFF_MESSAGE
from policy_decision import evaluate_policy_decision
from query_understanding import resolve_query_context
from retrieve import retrieve_chunks
from semantic_cache import get_cached_response, save_cached_response
from verify_answer import verify_answer_support


def _policy_hash(retrieved_chunks: list[dict[str, Any]]) -> str:
    return "|".join(sorted({str(chunk.get("doc_hash", "")) for chunk in retrieved_chunks}))


def format_handoff_message(handoff_packet: dict[str, Any]) -> str:
    if handoff_packet.get("reason_code") == "unsupported_policy_area":
        return UNSUPPORTED_POLICY_HANDOFF_MESSAGE
    return CUSTOMER_HANDOFF_MESSAGE


def generate_reliable_answer(
    question: str,
    history_turns: Optional[list[dict[str, Any]]] = None,
    retriever: Callable[[str], list[dict[str, Any]]] = retrieve_chunks,
) -> dict[str, Any]:
    """Run retrieval, reliability decisioning, answer generation, and verification."""
    query_analysis = resolve_query_context(question, history_turns)
    retrieval_query = query_analysis["effective_question"]
    retrieved_chunks = retriever(retrieval_query)

    pre_decision = evaluate_policy_decision(
        question,
        retrieved_chunks,
        history_turns=history_turns,
        query_analysis=query_analysis,
    )
    if pre_decision["action"] == "clarify":
        return {
            "action": "clarify",
            "answer": pre_decision["clarifying_question"],
            "retrieved_chunks": retrieved_chunks,
            "decision": pre_decision,
            "verification": {},
            "from_cache": False,
        }

    if pre_decision["action"] == "escalate":
        return {
            "action": "escalate",
            "answer": format_handoff_message(pre_decision["handoff_packet"]),
            "retrieved_chunks": retrieved_chunks,
            "decision": pre_decision,
            "verification": {},
            "from_cache": False,
        }

    policy_hash = _policy_hash(retrieved_chunks)
    cached = get_cached_response(retrieval_query, policy_hash) if policy_hash else None
    if cached:
        cached["from_cache"] = True
        return cached

    if history_turns is None:
        draft_answer = answer_question(question, retrieved_chunks)
    else:
        draft_answer = answer_conversation_question(question, retrieved_chunks, history_turns)

    verification = verify_answer_support(question, draft_answer, retrieved_chunks)
    final_decision = evaluate_policy_decision(
        question,
        retrieved_chunks,
        draft_answer=draft_answer,
        verification=verification,
        history_turns=history_turns,
        query_analysis=query_analysis,
    )
    final_decision["verification"] = verification

    if final_decision["action"] == "escalate":
        final_answer = format_handoff_message(final_decision["handoff_packet"])
    elif final_decision["action"] == "clarify":
        final_answer = final_decision["clarifying_question"]
    else:
        final_answer = draft_answer

    payload = {
        "action": final_decision["action"],
        "answer": final_answer,
        "retrieved_chunks": retrieved_chunks,
        "decision": final_decision,
        "verification": verification,
        "from_cache": False,
    }

    if final_decision["action"] == "answer" and policy_hash:
        save_cached_response(retrieval_query, policy_hash, payload)

    return payload
