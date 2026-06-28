from reliable_answer import generate_reliable_answer
from retrieve import format_chunks, load_index_and_chunks


def run_cli() -> None:
    """Run one end-to-end QA interaction from terminal input."""
    load_index_and_chunks()

    question = input("Enter your airline policy question: ").strip()
    if not question:
        raise ValueError("Question cannot be empty")

    result = generate_reliable_answer(question)
    retrieved_chunks = result["retrieved_chunks"]
    final_answer = result["answer"]
    decision = result["decision"]

    print("\nUser question:")
    print(question)
    print("\nReliability action:")
    print(decision["action"])
    print("\nDecision reason:")
    print(decision["confidence_reason"])
    print("\nRetrieved chunk sources:")
    for chunk in retrieved_chunks:
        print(f"- {chunk['source']} ({chunk['chunk_id']})")
    print("\nRetrieved chunks:")
    print(format_chunks(retrieved_chunks))
    print("\nFinal response:")
    print(final_answer)


if __name__ == "__main__":
    run_cli()
