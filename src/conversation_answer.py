from typing import Any

from openai import OpenAI

from answer import build_context, load_config


DEFAULT_HISTORY_LIMIT = 6


def format_history(history_turns: list[dict[str, Any]], limit: int = DEFAULT_HISTORY_LIMIT) -> str:
    """Format recent QA turns for conversation-aware prompting."""
    recent_turns = history_turns[-limit:] if limit > 0 else []
    if not recent_turns:
        return "No previous conversation history."

    sections: list[str] = []
    for index, turn in enumerate(recent_turns, start=1):
        question = turn.get("question", "").strip()
        answer = turn.get("answer", "").strip()
        sections.append(
            "\n".join(
                [
                    f"Turn {index}",
                    f"User: {question}",
                    f"Assistant: {answer}",
                ]
            )
        )

    return "\n\n".join(sections)


def answer_conversation_question(
    question: str,
    retrieved_chunks: list[dict[str, str]],
    history_turns: list[dict[str, Any]],
) -> str:
    """Generate a grounded answer while using history to interpret follow-up questions."""
    api_key, base_url, chat_model = load_config()
    client = OpenAI(api_key=api_key, base_url=base_url)
    context = build_context(retrieved_chunks)
    history = format_history(history_turns)

    response = client.chat.completions.create(
        model=chat_model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are answering airline policy questions in a multi-turn conversation. "
                    "Use recent conversation history only to understand references, ellipsis, and follow-up wording. "
                    "Use only the current retrieved policy context as factual evidence for the answer. "
                    "Do not add policy facts that are not explicitly supported by the current retrieved context. "
                    "If the current retrieved context is insufficient, say that clearly."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Recent conversation history:\n{history}\n\n"
                    f"Current question: {question}\n\n"
                    f"Current retrieved policy context:\n{context}\n\n"
                    "Write a concise answer to the current question. "
                    "Resolve follow-up references using the history, but ground policy details only in the current context."
                ),
            },
        ],
    )

    return response.choices[0].message.content or ""
