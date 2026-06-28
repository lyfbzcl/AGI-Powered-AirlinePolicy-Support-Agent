# Project Tasks and Status

## Final Status

The prototype is complete for the course final submission.

Implemented:

- Sample airline policy corpus in `data/raw/`
- Text preprocessing and overlapping chunking
- Metadata enrichment for policy area, version, effective date, priority, and document hash
- FAISS vector index and aligned chunk metadata
- OpenAI-compatible embedding and chat model configuration
- Retrieval-augmented answer generation
- Multi-turn context resolution for follow-up questions
- Missing-information detection
- Answer / clarify / escalate decision layer
- Heuristic answer-source verification
- Conflict and unsupported-policy escalation
- Human handoff messages
- Passenger/support-agent Streamlit UI
- Separate human customer-service console
- SQLite conversation and source persistence
- Semantic cache for repeated verified answers
- Offline reliability evaluation
- README reproducibility instructions for international and Chinese mainland DashScope endpoints

## Validation Commands

```bash
python3 -m compileall src streamlit_app.py agent_app.py
python3 eval/run_eval.py
```

Expected reliability result:

```text
Reliability eval: 6/6 passed
```

## Final Demo Scenarios

1. Grounded baggage answer with source evidence.
2. Refund question clarification when fare type, route, timing, or reason is missing.
3. Multi-turn refund follow-up using conversation context but current retrieved evidence.
4. Unsupported onboard-service question escalated to the human console.

## Remaining Production Work

The project is a proof-of-concept. Production deployment would require:

- expert-validated real airline policy data,
- stronger quantitative accuracy evaluation,
- prompt-injection and malicious-document defenses,
- role-based authentication,
- integration with CRM/ticketing systems,
- monitoring and audit logging,
- formal policy versioning and approval workflow.
