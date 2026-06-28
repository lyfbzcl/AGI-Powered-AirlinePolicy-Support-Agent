from openai import OpenAI

from model_config import load_chat_config
from retrieve import retrieve_chunks


def load_config() -> tuple[str, str, str]:
    """Load OpenAI-compatible chat configuration from .env."""
    return load_chat_config()


def build_context(chunks: list[dict[str, str]]) -> str:
    """Format retrieved chunks into a grounded context block."""
    if not chunks:
        return "No retrieved context available."

    sections: list[str] = []
    for index, chunk in enumerate(chunks, start=1):
        source = chunk.get("source", "unknown")
        text = chunk.get("text", "").strip()
        sections.append(f"Chunk {index} | Source: {source}\n{text}")

    return "\n\n".join(sections)


def answer_question(question: str, retrieved_chunks: list[dict[str, str]]) -> str:
    """Generate a grounded answer using an OpenAI-compatible chat API."""
    api_key, base_url, chat_model = load_config()
    client = OpenAI(api_key=api_key, base_url=base_url)
    context = build_context(retrieved_chunks)

    response = client.chat.completions.create(
        model=chat_model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are answering airline policy questions. "
                    "Use only the retrieved context. "
                    "Do not add facts that are not explicitly supported by the context. "
                    "If the context is insufficient, say that clearly."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Question: {question}\n\n"
                    f"Retrieved context:\n{context}\n\n"
                    "Write a concise answer based only on the retrieved context. "
                    "If the answer is not fully supported, say the context is insufficient."
                ),
            },
        ],
    )

    return response.choices[0].message.content or ""


def format_sources(chunks: list[dict[str, str]]) -> str:
    """List the retrieved chunk sources for test output."""
    if not chunks:
        return "No sources retrieved."

    lines: list[str] = []
    for chunk in chunks:
        lines.append(f"- {chunk['source']} ({chunk['chunk_id']})")

    return "\n".join(lines)


def test_answer_generation() -> None:
    """Run example questions through retrieval plus grounded answer generation."""
    example_questions = [
        "Can I get a refund if I cancel before departure?",
        "What happens if my baggage is overweight?",
    ]

    for question in example_questions:
        retrieved_chunks = retrieve_chunks(question)
        answer = answer_question(question, retrieved_chunks)

        print(f"\nQuestion: {question}")
        print("Retrieved chunk sources:")
        print(format_sources(retrieved_chunks))
        print("Final answer:")
        print(answer)


if __name__ == "__main__":
    test_answer_generation()
