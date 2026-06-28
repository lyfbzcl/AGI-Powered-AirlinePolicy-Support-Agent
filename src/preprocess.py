import re

from load_docs import load_documents
from policy_metadata import enrich_chunk_metadata


def clean_text(text: str) -> str:
    """Collapse repeated whitespace into single spaces."""
    return re.sub(r"\s+", " ", text).strip()


def chunk_text(text: str, chunk_size: int = 300, overlap: int = 50) -> list[str]:
    """Split text into overlapping word chunks."""
    words = text.split()
    if not words:
        return []

    step = max(1, chunk_size - overlap)
    chunks: list[str] = []

    for start in range(0, len(words), step):
        chunk_words = words[start : start + chunk_size]
        if not chunk_words:
            continue
        chunks.append(" ".join(chunk_words))
        if start + chunk_size >= len(words):
            break

    return chunks


def preprocess_documents(
    chunk_size: int = 300, overlap: int = 50
) -> list[dict[str, str]]:
    """Load documents, clean text, and split them into chunk objects."""
    documents = load_documents()
    processed_chunks: list[dict[str, str]] = []

    for document in documents:
        cleaned_text = clean_text(document["text"])
        text_chunks = chunk_text(cleaned_text, chunk_size=chunk_size, overlap=overlap)

        for index, chunk in enumerate(text_chunks, start=1):
            processed_chunks.append(
                enrich_chunk_metadata(
                    {
                        "chunk_id": f"{document['source']}_chunk_{index}",
                        "source": document["source"],
                        "text": chunk,
                    }
                )
            )

    return processed_chunks


def test_preprocessing() -> list[dict[str, str]]:
    chunks = preprocess_documents()
    print(f"Created {len(chunks)} chunk(s)")

    if chunks:
        print("\nSample chunk:")
        print(f"chunk_id: {chunks[0]['chunk_id']}")
        print(f"source: {chunks[0]['source']}")
        print(chunks[0]["text"])
    else:
        print("\nSample chunk: none available because data/raw/ has no .txt files")

    return chunks


if __name__ == "__main__":
    test_preprocessing()
