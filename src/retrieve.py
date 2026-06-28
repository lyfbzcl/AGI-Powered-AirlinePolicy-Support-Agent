import json
from pathlib import Path

import faiss
import numpy as np
from openai import OpenAI

from embed_index import CHUNKS_PATH, INDEX_PATH
from model_config import load_embedding_config, load_top_k
from policy_metadata import enrich_chunks


def load_config() -> tuple[str, str, str, int]:
    """Load OpenAI-compatible embedding and retrieval settings from .env."""
    api_key, base_url, embedding_model = load_embedding_config()
    top_k = load_top_k()
    return api_key, base_url, embedding_model, top_k


def load_index_and_chunks() -> tuple[faiss.Index, list[dict[str, str]]]:
    """Load the saved FAISS index and chunk metadata."""
    if not INDEX_PATH.exists():
        raise FileNotFoundError(f"FAISS index not found at {INDEX_PATH}")

    if not CHUNKS_PATH.exists():
        raise FileNotFoundError(f"Chunk metadata not found at {CHUNKS_PATH}")

    index = faiss.read_index(str(INDEX_PATH))
    chunks = enrich_chunks(json.loads(CHUNKS_PATH.read_text(encoding="utf-8")))

    if index.ntotal != len(chunks):
        raise ValueError(
            "Saved index and chunk metadata are out of sync. Rebuild the index."
        )

    return index, chunks


def embed_query(query: str, client: OpenAI, model: str) -> np.ndarray:
    """Generate a single embedding vector for the user query."""
    query = query.strip()
    if not query:
        raise ValueError("Query cannot be empty")

    response = client.embeddings.create(model=model, input=[query])
    vector = response.data[0].embedding
    return np.array([vector], dtype="float32")


def retrieve_chunks(query: str) -> list[dict[str, str]]:
    """Embed the query, search FAISS, and return the top-k chunk objects."""
    api_key, base_url, embedding_model, top_k = load_config()
    client = OpenAI(api_key=api_key, base_url=base_url)
    index, chunks = load_index_and_chunks()
    query_vector = embed_query(query, client=client, model=embedding_model)

    result_count = min(top_k, len(chunks))
    distances, indices = index.search(query_vector, result_count)

    retrieved: list[dict[str, str]] = []
    for rank, chunk_index in enumerate(indices[0]):
        if chunk_index < 0 or chunk_index >= len(chunks):
            continue
        chunk = dict(chunks[chunk_index])
        chunk["retrieval_distance"] = float(distances[0][rank])
        chunk["retrieval_rank"] = rank + 1
        retrieved.append(chunk)

    return retrieved


def format_chunks(chunks: list[dict[str, str]]) -> str:
    """Format retrieved chunks for readable terminal output."""
    if not chunks:
        return "No chunks retrieved."

    sections: list[str] = []
    for rank, chunk in enumerate(chunks, start=1):
        sections.append(
            "\n".join(
                [
                    f"Result {rank}",
                    f"source: {chunk['source']}",
                    f"chunk_id: {chunk['chunk_id']}",
                    f"text: {chunk['text']}",
                ]
            )
        )

    return "\n\n".join(sections)


def test_retrieval() -> None:
    example_queries = [
        "Can I get a refund if I cancel before departure?",
        "What happens if my baggage is overweight?",
    ]

    for query in example_queries:
        print(f"\nQuery: {query}")
        print(format_chunks(retrieve_chunks(query)))


if __name__ == "__main__":
    test_retrieval()
