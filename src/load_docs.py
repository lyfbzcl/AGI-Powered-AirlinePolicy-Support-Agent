from pathlib import Path


def load_documents(data_dir: str = "data/raw") -> list[dict[str, str]]:
    """Load .txt documents from the raw data directory."""
    raw_dir = Path(data_dir)
    documents: list[dict[str, str]] = []

    if not raw_dir.exists():
        return documents

    for file_path in sorted(raw_dir.glob("*.txt")):
        documents.append(
            {
                "source": file_path.name,
                "text": file_path.read_text(encoding="utf-8"),
            }
        )

    return documents


if __name__ == "__main__":
    docs = load_documents()
    print(f"Loaded {len(docs)} document(s)")
    for doc in docs:
        print(f"\nSource: {doc['source']}")
        print(doc["text"])
