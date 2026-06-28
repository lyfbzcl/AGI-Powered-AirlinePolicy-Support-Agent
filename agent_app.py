import sys
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any

import streamlit as st


ROOT_DIR = Path(__file__).resolve().parent
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from history_store import (  # noqa: E402
    add_handoff_reply,
    get_handoff_request,
    init_db,
    list_handoff_requests,
    set_handoff_status,
)


def apply_theme() -> None:
    st.markdown(
        """
        <style>
        :root {
            --navy: #071629;
            --blue: #2e78a8;
            --gold: #d4a762;
            --green: #0f6b5e;
            --line: rgba(16, 41, 70, 0.14);
            --muted: #66758a;
        }
        .stApp {
            background: #f4f7fa;
            color: var(--navy);
        }
        .block-container {
            max-width: 1440px;
            padding-top: 1.4rem;
        }
        section[data-testid="stSidebar"] {
            background: var(--navy);
        }
        section[data-testid="stSidebar"] * {
            color: #fff;
        }
        section[data-testid="stSidebar"] input {
            background: #fff;
            color: var(--navy) !important;
            caret-color: var(--navy);
        }
        section[data-testid="stSidebar"] input::placeholder {
            color: var(--muted) !important;
        }
        section[data-testid="stSidebar"] .stButton button {
            background: #fff;
            color: var(--navy) !important;
        }
        section[data-testid="stSidebar"] .stButton button * {
            color: inherit !important;
        }
        .agent-header {
            padding: 1rem 1.2rem;
            margin-bottom: 1rem;
            border-radius: 10px;
            background: linear-gradient(135deg, #071629, #153a5f);
            color: #fff;
        }
        .agent-header h1 {
            margin: 0;
            color: #fff;
            font-size: 1.55rem;
        }
        .agent-header p {
            margin: .28rem 0 0;
            color: rgba(255,255,255,.74);
        }
        .case-meta {
            display: flex;
            flex-wrap: wrap;
            gap: .5rem;
            margin-bottom: .9rem;
        }
        .case-pill {
            padding: .25rem .58rem;
            border: 1px solid var(--line);
            border-radius: 999px;
            background: #fff;
            color: var(--navy);
            font-size: .78rem;
        }
        .transcript {
            padding: 1rem;
            border: 1px solid var(--line);
            border-radius: 10px;
            background: #fff;
        }
        .message {
            max-width: 88%;
            margin-bottom: .7rem;
            padding: .68rem .8rem;
            border-radius: 9px;
        }
        .message-user {
            margin-left: auto;
            background: #eaf4fa;
            border: 1px solid rgba(46,120,168,.2);
        }
        .message-ai {
            background: #f8f3e9;
            border: 1px solid rgba(212,167,98,.25);
        }
        .message-agent {
            background: #e9f4f1;
            border: 1px solid rgba(15,107,94,.2);
        }
        .message-label {
            margin-bottom: .22rem;
            color: var(--muted);
            font-size: .72rem;
            font-weight: 750;
            text-transform: uppercase;
        }
        .empty-queue {
            padding: 2rem;
            border: 1px dashed var(--line);
            border-radius: 10px;
            background: #fff;
            text-align: center;
            color: var(--muted);
        }
        div[data-testid="stColumn"]:has(.response-panel-marker) {
            position: sticky;
            top: 1rem;
            align-self: flex-start;
        }
        .response-panel-marker {
            height: 0;
            overflow: hidden;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def format_time(value: str) -> str:
    if not value:
        return ""
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.astimezone().strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return value


def render_message(label: str, text: str, kind: str) -> None:
    safe_text = escape(text).replace("\n", "<br>")
    st.markdown(
        f"""
        <div class="message message-{kind}">
            <div class="message-label">{escape(label)}</div>
            <div>{safe_text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _turn_occurred_during_handoff(
    turn: dict[str, Any],
    handoff_turns: list[dict[str, Any]],
) -> bool:
    turn_index = int(turn.get("turn_index") or 0)
    turn_created_at = str(turn.get("created_at") or "")
    for handoff_turn in handoff_turns:
        if turn_index <= int(handoff_turn.get("turn_index") or 0):
            continue
        support = handoff_turn.get("human_support") or {}
        if support.get("status") in {"pending", "in_progress"}:
            return True
        resolved_at = str(support.get("updated_at") or "")
        if (
            support.get("status") == "resolved"
            and turn_created_at
            and resolved_at
            and turn_created_at <= resolved_at
        ):
            return True
    return False


def render_transcript(case: dict[str, Any]) -> None:
    st.markdown('<div class="transcript">', unsafe_allow_html=True)
    turns = case["conversation"].get("turns", [])
    handoff_turns = [turn for turn in turns if turn.get("human_support")]
    timeline: list[dict[str, Any]] = []

    for turn in turns:
        created_at = str(turn.get("created_at") or "")
        turn_index = int(turn.get("turn_index") or 0)
        timeline.append(
            {
                "created_at": created_at,
                "order": (turn_index, 0),
                "label": "Customer",
                "text": str(turn.get("question") or ""),
                "kind": "user",
            }
        )
        if not _turn_occurred_during_handoff(turn, handoff_turns):
            timeline.append(
                {
                    "created_at": created_at,
                    "order": (turn_index, 1),
                    "label": "AI assistant",
                    "text": str(turn.get("answer") or ""),
                    "kind": "ai",
                }
            )
        support = turn.get("human_support") or {}
        for message_index, message in enumerate(support.get("messages", [])):
            is_customer = message.get("sender_type") == "customer"
            timeline.append(
                {
                    "created_at": str(message.get("created_at") or ""),
                    "order": (turn_index, 2 + message_index),
                    "label": (
                        "Customer"
                        if is_customer
                        else str(message.get("sender_name") or "Customer service")
                    ),
                    "text": str(message.get("message") or ""),
                    "kind": "user" if is_customer else "agent",
                }
            )

    timeline.sort(key=lambda event: (event["created_at"], event["order"]))
    for event in timeline:
        render_message(event["label"], event["text"], event["kind"])
    st.markdown("</div>", unsafe_allow_html=True)


def render_queue(status_filter: str) -> list[dict[str, Any]]:
    requests = list_handoff_requests(status_filter)
    st.markdown("### Handoff queue")
    st.caption(f"{len(requests)} case(s)")
    for request in requests:
        label = (
            f"{request['title'][:28]}\n"
            f"{request['status'].replace('_', ' ').title()}"
        )
        if st.button(
            label,
            key=f"case_{request['id']}",
            use_container_width=True,
        ):
            st.session_state.selected_handoff_id = request["id"]
    return requests


def render_case(case: dict[str, Any], agent_name: str) -> None:
    st.subheader(case["title"])
    st.markdown(
        f"""
        <div class="case-meta">
            <span class="case-pill">Status: {escape(case['status'].replace('_', ' ').title())}</span>
            <span class="case-pill">Reason: {escape(case['reason_code'] or 'Not specified')}</span>
            <span class="case-pill">Created: {escape(format_time(case['created_at']))}</span>
            <span class="case-pill">Conversation: {escape(case['conversation_id'][:10])}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    transcript_col, response_col = st.columns([0.64, 0.36], gap="large")
    with transcript_col:
        st.markdown("#### Customer and AI conversation")
        render_transcript(case)

    with response_col:
        st.markdown(
            '<div class="response-panel-marker" aria-hidden="true"></div>',
            unsafe_allow_html=True,
        )
        st.markdown("#### Respond to customer")
        if case["status"] == "pending":
            if st.button("Accept case", type="secondary", use_container_width=True):
                set_handoff_status(case["id"], "in_progress")
                st.rerun()

        with st.form(f"reply_form_{case['id']}", clear_on_submit=True):
            reply = st.text_area(
                "Reply",
                height=190,
                placeholder="Write the customer-service response...",
            )
            submitted = st.form_submit_button(
                "Send reply",
                type="primary",
                use_container_width=True,
            )
        if submitted:
            try:
                add_handoff_reply(
                    case["id"],
                    reply,
                    agent_name,
                    resolve=False,
                )
            except ValueError as exc:
                st.error(str(exc))
            else:
                st.success("Reply sent and saved to the customer conversation.")
                st.rerun()

        if case["status"] != "resolved":
            if st.button(
                "Mark case as resolved",
                type="secondary",
                use_container_width=True,
            ):
                set_handoff_status(case["id"], "resolved")
                st.rerun()
        else:
            if st.button("Reopen case", use_container_width=True):
                set_handoff_status(case["id"], "in_progress")
                st.rerun()


@st.fragment(run_every="2s")
def render_live_queue(status_filter: str) -> None:
    """Refresh the handoff queue as passenger questions arrive."""
    render_queue(status_filter)


@st.fragment(run_every="2s")
def render_live_case(status_filter: str, agent_name: str) -> None:
    """Refresh the selected conversation and replies from the shared store."""
    requests = list_handoff_requests(status_filter)
    selected_id = st.session_state.get("selected_handoff_id")
    if not selected_id:
        selected_id = requests[0]["id"] if requests else None
        st.session_state.selected_handoff_id = selected_id

    if not selected_id:
        st.markdown(
            '<div class="empty-queue">No handoff requests in this queue.</div>',
            unsafe_allow_html=True,
        )
        return

    try:
        case = get_handoff_request(selected_id)
    except ValueError:
        selected_id = requests[0]["id"] if requests else None
        st.session_state.selected_handoff_id = selected_id
        if not selected_id:
            st.markdown(
                '<div class="empty-queue">No handoff requests in this queue.</div>',
                unsafe_allow_html=True,
            )
            return
        case = get_handoff_request(selected_id)

    render_case(case, agent_name)


def main() -> None:
    st.set_page_config(
        page_title="Aurelia Customer Service",
        page_icon="🎧",
        layout="wide",
    )
    apply_theme()
    init_db()

    st.markdown(
        """
        <div class="agent-header">
            <h1>Customer Service Console</h1>
            <p>Review AI handoffs, inspect the full conversation, and reply to the customer.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    agent_name = st.sidebar.text_input("Agent name", value="Aurelia Support")
    status_label = st.sidebar.radio(
        "Queue status",
        ["Pending", "In progress", "Resolved", "All"],
    )
    status_filter = {
        "Pending": "pending",
        "In progress": "in_progress",
        "Resolved": "resolved",
        "All": "all",
    }[status_label]
    with st.sidebar:
        render_live_queue(status_filter)

    render_live_case(status_filter, agent_name)


if __name__ == "__main__":
    main()
