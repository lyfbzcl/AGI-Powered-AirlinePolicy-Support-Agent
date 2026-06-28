# Test Report: Airline Policy QA Assistant

Generated: 2026-05-13

## Summary

Overall result: PASS

The current application passed static checks, module import checks, SQLite persistence tests, real retrieval and conversation-answer tests, and Streamlit service health checks. The CLI entry point remains importable, and the original `retrieve_chunks()` and `answer_question()` function signatures remain compatible.

## Environment

- Project path: `/Users/liyunfeng/semester/2026s1/703/airline_rag_handoff`
- Python: `3.9.6`
- Streamlit: `1.50.0`
- Local app URL: `http://localhost:8501`
- Streamlit PID during test: `8094`
- Conversation database: `data/conversations.sqlite3`

## Test Results

| Area | Test | Result | Notes |
| --- | --- | --- | --- |
| Static check | `python3 -m compileall src streamlit_app.py` | PASS | All Python files compiled successfully. |
| Imports | Import CLI, Streamlit app, retrieval, answer, conversation answer, history store | PASS | No import errors. |
| Backward compatibility | Check `answer_question()` and `retrieve_chunks()` signatures | PASS | Existing callable interfaces are still present. |
| SQLite schema | Verify `conversations`, `turns`, `turn_sources` tables | PASS | All expected tables exist. |
| SQLite persistence | Create temp conversation, add two turns, save sources, read recent history | PASS | Turn ordering, title generation, source persistence, and recent-history retrieval worked. |
| Retrieval | Query: `Can I get a refund if I cancel before departure?` | PASS | Returned 2 chunks. |
| Conversation answer | Follow-up: `What if I cancel very close to departure?` with prior history | PASS | Returned a non-empty grounded answer. |
| Streamlit health | `curl -I http://localhost:8501` | PASS | Returned HTTP 200. |
| Runtime log | Inspect `/tmp/airline_rag_streamlit.log` | PASS | No app exception found. |

## Retrieval Test Details

Test question:

```text
Can I get a refund if I cancel before departure?
```

Retrieved chunks:

- `refund_policy.txt`, `refund_policy.txt_chunk_2`
- `cancellation_policy.txt`, `cancellation_policy.txt_chunk_1`

## Conversation Test Details

History used:

```text
User: Can I get a refund if I cancel before departure?
Assistant: The previous answer discussed refund eligibility before departure.
```

Follow-up question:

```text
What if I cancel very close to departure?
```

Result: the conversation-aware answer function returned a non-empty answer and used the history-aware wrapper successfully.

## Current Persistent Data State

At the time of testing:

- `conversations`: 1
- `turns`: 0
- `turn_sources`: 0
- Latest conversation title: `New conversation`

The persistence smoke test used a temporary SQLite file under `/tmp`, so it did not pollute the real application history.

## Warnings And Notes

- Streamlit startup logs include a `NotOpenSSLWarning` from `urllib3` because the system Python SSL module is compiled with LibreSSL. This did not block local app startup or HTTP health checks.
- The real app database currently contains one empty conversation because the Streamlit app creates an initial conversation on startup.
- No browser UI automation was run; frontend verification was done through service health checks and module-level behavior tests.

## Recommended Manual Acceptance Test

Open:

```text
http://localhost:8501
```

Then test:

1. Ask `Can I get a refund if I cancel before departure?`
2. Ask `What if I cancel very close to departure?`
3. Confirm both turns appear in the chat.
4. Confirm each assistant answer has expandable `Sources`.
5. Click `New Conversation`.
6. Reopen the previous conversation from the sidebar and confirm the saved turns are still visible.
