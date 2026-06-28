# Start Here

This repository contains the final functional proof-of-concept for the Airline Policy AI Support Agent.

For normal reproduction, start with the main README:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
```

Then edit `.env` with your Alibaba Cloud Model Studio / DashScope API key and the correct endpoint for your region.

## Quick Validation

```bash
python3 -m compileall src streamlit_app.py agent_app.py
python3 eval/run_eval.py
```

## Run Both Apps

Passenger/support-agent page:

```bash
python3 -m streamlit run streamlit_app.py --server.port 8501
```

Human service console:

```bash
python3 -m streamlit run agent_app.py --server.port 8502
```

Open:

- `http://localhost:8501`
- `http://localhost:8502`

## Rebuild Index

Rebuild the FAISS index after changing policies, embedding models, or endpoint providers:

```bash
python3 src/embed_index.py
```

## Expected Final Behavior

The system should:

1. retrieve policy evidence from FAISS,
2. answer grounded questions with source display,
3. ask for missing decision-critical information,
4. resolve simple follow-up context,
5. escalate unsupported or risky questions to the human console,
6. save conversation state and retrieved sources in SQLite.
