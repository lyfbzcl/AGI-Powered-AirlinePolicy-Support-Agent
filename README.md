# Airline Policy AI Support Agent

Reliability-first compound AI system for airline customer support. The project turns static airline policy documents into an internal support co-pilot that can answer with retrieved evidence, ask for missing details, and hand off risky or unsupported cases to a human service console.

This repository supports the final report and 3-minute road-show demo for Group 10.

## Product Summary

Airline support teams repeatedly answer policy questions about refunds, cancellations, baggage, flight changes, delays, check-in, and service rules. Manual lookup across scattered documents is slow, costly, and inconsistent.

The Airline Policy AI Support Agent reduces this workload by combining:

- RAG retrieval over airline policy documents
- FAISS vector search
- OpenAI-compatible embedding and chat APIs
- Missing-information detection
- Answer verification against retrieved policy sources
- Policy conflict and unsupported-area escalation
- Multi-turn context handling
- Human handoff through a separate customer-service console
- SQLite-backed conversation and source persistence
- Semantic cache for repeated verified answers

The intended business model is an internal SaaS co-pilot for airline support teams and travel-service operators. The system is designed to save agent lookup time while keeping compensation-risk and unsupported decisions under human control.

## Repository Structure

```text
.
├── agent_app.py                 # Human customer-service console
├── streamlit_app.py             # Passenger/support-agent chat UI
├── src/
│   ├── answer.py                # Grounded LLM answer generation
│   ├── conversation_answer.py   # Multi-turn grounded answer generation
│   ├── embed_index.py           # Embedding + FAISS index build
│   ├── retrieve.py              # Query embedding + vector retrieval
│   ├── reliable_answer.py       # Answer / clarify / escalate orchestration
│   ├── missing_info.py          # Required-field detection
│   ├── policy_decision.py       # Reliability decision layer
│   ├── verify_answer.py         # Source-support verification
│   ├── conflict_resolution.py   # Lightweight conflict detection
│   ├── handoff.py               # Human handoff messages
│   ├── history_store.py         # SQLite conversation persistence
│   ├── policy_lifecycle.py      # Manifest, version, and hash tracking
│   ├── policy_metadata.py       # Metadata inference and enrichment
│   └── semantic_cache.py        # Verified-answer cache
├── data/raw/                    # Sample airline policy text files
├── index/                       # Built FAISS index and chunk metadata
├── eval/
│   ├── gold_questions.json      # Offline reliability test cases
│   └── run_eval.py              # Reliability test runner
├── assets/                      # UI image assets
├── requirements.txt
├── .env.example
└── TEST_REPORT.md
```

## System Workflow

### Offline Indexing

```text
Policy documents
  -> text cleaning
  -> overlapping chunks
  -> metadata enrichment
  -> embedding API
  -> FAISS index
  -> policy manifest with hashes, version, effective date, and status
```

### Online Answer Path

```text
User question
  -> context resolution for follow-up questions
  -> query embedding
  -> FAISS retrieval
  -> missing-information detection
  -> policy conflict / unsupported-area checks
  -> grounded answer generation
  -> answer verification
  -> answer, clarify, or human handoff
  -> SQLite logging and source persistence
```

The important product behavior is:

- Answer when retrieved evidence is sufficient.
- Ask when the user omits policy-critical fields.
- Escalate when evidence is missing, unsupported, conflicting, or unverified.

## Current Prototype Scope

The sample knowledge base contains six fictional airline policy documents:

- `baggage_policy.txt`
- `cancellation_policy.txt`
- `check_in_policy.txt`
- `delay_compensation_policy.txt`
- `flight_change_policy.txt`
- `refund_policy.txt`

The current FAISS index contains 24 policy chunks, generated from 300-word chunks with 50-word overlap.

## Setup

Use Python 3.9 or newer.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
```

Then edit `.env` and add your real Alibaba Cloud Model Studio / DashScope API key.

The real `.env` file is intentionally ignored by Git and must not be committed.

## API Configuration

The code uses the OpenAI Python SDK with Alibaba Cloud Model Studio's OpenAI-compatible endpoint.

### New Zealand / International Endpoint

Use this when your DashScope key is created for the international endpoint, which is usually the correct setting when developing from New Zealand or other non-mainland regions.

```env
DASHSCOPE_API_KEY=your_dashscope_api_key_here
DASHSCOPE_BASE_URL=https://dashscope-intl.aliyuncs.com/compatible-mode/v1
LLM_CHAT_MODEL=qwen-plus
EMBEDDING_MODEL=text-embedding-v4
TOP_K=3
```

### Chinese Mainland Endpoint

Use this when your DashScope key is created in the Chinese mainland region.

```env
DASHSCOPE_API_KEY=your_dashscope_api_key_here
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_CHAT_MODEL=qwen-plus
EMBEDDING_MODEL=text-embedding-v4
TOP_K=3
```

If the embedding provider, embedding model, or raw policy documents change, rebuild the FAISS index:

```bash
python3 src/embed_index.py
```

## Run the Application

Start the passenger/support-agent chat page:

```bash
python3 -m streamlit run streamlit_app.py --server.port 8501
```

Start the human customer-service console in a second terminal:

```bash
python3 -m streamlit run agent_app.py --server.port 8502
```

Open:

- Passenger/support-agent page: `http://localhost:8501`
- Human service console: `http://localhost:8502`

Both apps use the same local SQLite database at `data/conversations.sqlite3`. This runtime database is ignored by Git.

## Demo Scenarios

The final road-show video demonstrates these cases:

1. Grounded answer: `What happens if my checked bag is overweight?`
2. Clarification: `Can I get a refund if I cancel before departure?`
3. Multi-turn follow-up: `It is a basic economy ticket and I cancel very close to departure.`
4. Human handoff: `我能在飞机上喝酒吗?`

The fourth case is intentionally outside the current policy corpus. The system should not invent a rule; it should transfer the case to the human service console.

## Evaluation

Run static import/compile checks:

```bash
python3 -m compileall src streamlit_app.py agent_app.py
```

Run the offline reliability evaluation:

```bash
python3 eval/run_eval.py
```

Expected result:

```text
Reliability eval: 6/6 passed
PASS: contextual first-class follow-up inherits the baggage question
PASS: standalone passenger detail asks for the goal without inventing refund intent
PASS: uncovered onboard-service question transfers to customer service
```

The included `TEST_REPORT.md` records additional checks performed during development:

- static compilation
- module imports
- SQLite persistence
- retrieval smoke test
- conversation-aware answer smoke test
- Streamlit HTTP health check

## Reproducibility Notes

The repository includes:

- source code
- sample policy text files
- generated chunk metadata
- generated FAISS index
- policy manifest
- offline evaluation cases
- local run instructions

To reproduce from scratch:

1. Install dependencies.
2. Configure `.env` with the correct DashScope endpoint for your region.
3. Rebuild the FAISS index with `python3 src/embed_index.py`.
4. Run `python3 eval/run_eval.py`.
5. Start both Streamlit apps.

## Security Notes

Do not commit:

- `.env`
- real API keys
- local SQLite conversation databases
- local semantic cache files
- browser automation artifacts

The public repository should contain `.env.example` only.

## Report Citation

For the final report, cite this repository as the code and data availability artifact:

```text
Code and prototype: https://github.com/lyfbzcl/AGI-Powered-AirlinePolicy-Support-Agent
```

## Limitations

This is a functional proof-of-concept, not a production airline policy engine. The current corpus is fictional and small. The verification layer is heuristic, not a formal legal reasoning system. Production deployment would require expert-validated policy data, stricter access control, stronger prompt-injection defenses, more realistic evaluation, and integration with airline CRM or ticketing systems.
