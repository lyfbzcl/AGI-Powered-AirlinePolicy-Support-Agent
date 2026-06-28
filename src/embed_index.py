import json
from pathlib import Path

import faiss
import numpy as np
from openai import OpenAI

from model_config import load_embedding_config
from policy_lifecycle import rebuild_manifest
from preprocess import preprocess_documents


INDEX_DIR = Path("index")
INDEX_PATH = INDEX_DIR / "faiss.index"
CHUNKS_PATH = INDEX_DIR / "chunks.json"
EMBEDDING_BATCH_SIZE = 20


def load_config() -> tuple[str, str, str]:
    """Load OpenAI-compatible embedding configuration from .env."""
    return load_embedding_config()


def embed_chunks(
    chunks: list[dict[str, str]], client: OpenAI, model: str
) -> np.ndarray:
    """Generate embeddings for chunk text using an OpenAI-compatible embeddings API."""
    texts = [chunk["text"] for chunk in chunks]
    vectors: list[list[float]] = []
    for start in range(0, len(texts), EMBEDDING_BATCH_SIZE):
        batch = texts[start : start + EMBEDDING_BATCH_SIZE]
        response = client.embeddings.create(model=model, input=batch)
        vectors.extend(item.embedding for item in response.data)
    return np.array(vectors, dtype="float32")


def build_faiss_index(vectors: np.ndarray) -> faiss.IndexFlatL2:
    """Build a simple FAISS L2 index from the embedding matrix."""
    if vectors.size == 0:
        raise ValueError("No vectors available to index")

    dimension = vectors.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(vectors)
    return index


def save_index(index: faiss.IndexFlatL2, chunks: list[dict[str, str]]) -> None:
    """Persist the FAISS index and chunk metadata."""
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(INDEX_PATH))
    CHUNKS_PATH.write_text(json.dumps(chunks, indent=2), encoding="utf-8")


def build_and_save_index() -> tuple[faiss.IndexFlatL2, list[dict[str, str]]]:
    """Run preprocessing, embedding generation, FAISS indexing, and save artifacts."""
    chunks = preprocess_documents()
    if not chunks:
        raise ValueError("No chunks found. Add .txt files to data/raw/ before indexing.")

    api_key, base_url, embedding_model = load_config()
    client = OpenAI(api_key=api_key, base_url=base_url)
    vectors = embed_chunks(chunks, client=client, model=embedding_model)
    index = build_faiss_index(vectors)
    save_index(index, chunks)
    rebuild_manifest()
    return index, chunks


def test_index_build() -> tuple[faiss.IndexFlatL2, list[dict[str, str]]]:
    index, chunks = build_and_save_index()
    print(f"Indexed {len(chunks)} chunk(s)")
    print(f"Stored {index.ntotal} vector(s)")
    print(f"FAISS index exists: {INDEX_PATH.exists()}")
    print(f"Chunk metadata exists: {CHUNKS_PATH.exists()}")
    return index, chunks


if __name__ == "__main__":
    test_index_build()
