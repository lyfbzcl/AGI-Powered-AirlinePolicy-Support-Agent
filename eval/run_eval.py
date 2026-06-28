import json
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from missing_info import detect_missing_info  # noqa: E402
from policy_decision import evaluate_policy_decision  # noqa: E402
from policy_metadata import enrich_chunk_metadata  # noqa: E402
from query_understanding import resolve_query_context  # noqa: E402
from reliable_answer import format_handoff_message  # noqa: E402


GOLD_PATH = Path(__file__).resolve().parent / "gold_questions.json"


def make_mock_chunk(policy_area: str) -> dict:
    return enrich_chunk_metadata(
        {
            "chunk_id": f"{policy_area}_mock_chunk_1",
            "source": f"{policy_area}_policy.txt",
            "text": (
                "This mock policy evidence is used for offline reliability "
                "evaluation. Fare rules, route, timing, exceptions, and legal "
                "requirements may affect the final policy decision."
            ),
            "policy_area": policy_area,
        }
    )


def main() -> int:
    cases = json.loads(GOLD_PATH.read_text(encoding="utf-8"))
    passed = 0
    rows = []

    for case in cases:
        question = case["question"]
        missing = detect_missing_info(question)
        chunks = [make_mock_chunk(missing["policy_area"])]
        decision = evaluate_policy_decision(question, chunks)
        expected_missing = set(case["expected_missing_fields"])
        actual_missing = set(missing["missing_fields"])

        ok = (
            missing["policy_area"] == case["expected_policy_area"]
            and decision["action"] == case["expected_action"]
            and expected_missing == actual_missing
        )
        passed += int(ok)
        rows.append(
            {
                "question": question,
                "ok": ok,
                "expected_action": case["expected_action"],
                "actual_action": decision["action"],
                "expected_policy_area": case["expected_policy_area"],
                "actual_policy_area": missing["policy_area"],
                "expected_missing": sorted(expected_missing),
                "actual_missing": sorted(actual_missing),
            }
        )

    for row in rows:
        status = "PASS" if row["ok"] else "FAIL"
        print(f"{status}: {row['question']}")
        if not row["ok"]:
            print(json.dumps(row, indent=2))

    print(f"\nReliability eval: {passed}/{len(cases)} passed")

    follow_up_history = [
        {
            "question": "What happens if my checked bag weighs more than 32kg?",
            "answer": "Bags above the maximum weight must be repacked.",
        }
    ]
    follow_up = resolve_query_context(
        "But I'm a first-class passenger.",
        follow_up_history,
    )
    follow_up_missing = detect_missing_info(follow_up["effective_question"])
    follow_up_ok = (
        follow_up["dialogue_act"] == "follow_up_detail"
        and follow_up["resolved_policy_area"] == "baggage"
        and follow_up_missing["policy_area"] == "baggage"
        and follow_up_missing["missing_fields"] == []
    )
    print(
        f"{'PASS' if follow_up_ok else 'FAIL'}: "
        "contextual first-class follow-up inherits the baggage question"
    )

    standalone_analysis = resolve_query_context("But I'm a first-class passenger.")
    standalone_chunks = [make_mock_chunk("refund")]
    standalone_decision = evaluate_policy_decision(
        "But I'm a first-class passenger.",
        standalone_chunks,
        query_analysis=standalone_analysis,
    )
    standalone_ok = (
        standalone_decision["action"] == "clarify"
        and standalone_decision["missing_info"]["missing_fields"] == ["user_goal"]
    )
    print(
        f"{'PASS' if standalone_ok else 'FAIL'}: "
        "standalone passenger detail asks for the goal without inventing refund intent"
    )

    unsupported_question = "What drink can I get on the plane? May I get beer?"
    unsupported_chunks = [make_mock_chunk("baggage")]
    unsupported_decision = evaluate_policy_decision(
        unsupported_question,
        unsupported_chunks,
    )
    unsupported_message = format_handoff_message(
        unsupported_decision["handoff_packet"]
    )
    unsupported_ok = (
        unsupported_decision["action"] == "escalate"
        and unsupported_decision["reason_code"] == "unsupported_policy_area"
        and unsupported_decision["missing_info"]["policy_area"] == "general"
        and unsupported_decision["missing_info"]["missing_fields"] == []
        and "current policy information does not address" in unsupported_message
        and "customer service agent" in unsupported_message
    )
    print(
        f"{'PASS' if unsupported_ok else 'FAIL'}: "
        "uncovered onboard-service question transfers to customer service"
    )

    all_passed = (
        passed == len(cases)
        and follow_up_ok
        and standalone_ok
        and unsupported_ok
    )
    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
