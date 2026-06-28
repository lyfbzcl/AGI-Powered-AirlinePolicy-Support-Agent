import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from policy_metadata import document_hash, normalize_text


ROOT_DIR = Path(__file__).resolve().parents[1]
CACHE_PATH = ROOT_DIR / "data" / "semantic_cache.sqlite3"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def init_cache(db_path: Path = CACHE_PATH) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS semantic_cache (
                cache_key TEXT PRIMARY KEY,
                normalized_question TEXT NOT NULL,
                policy_hash TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )


def make_cache_key(question: str, policy_hash: str) -> str:
    return document_hash(f"{normalize_text(question)}|{policy_hash}")


def get_cached_response(question: str, policy_hash: str, db_path: Path = CACHE_PATH) -> Optional[dict[str, Any]]:
    init_cache(db_path)
    key = make_cache_key(question, policy_hash)
    with sqlite3.connect(db_path) as connection:
        row = connection.execute(
            "SELECT payload FROM semantic_cache WHERE cache_key = ? AND policy_hash = ?",
            (key, policy_hash),
        ).fetchone()
    if row is None:
        return None
    return json.loads(row[0])


def save_cached_response(
    question: str,
    policy_hash: str,
    payload: dict[str, Any],
    db_path: Path = CACHE_PATH,
) -> None:
    init_cache(db_path)
    key = make_cache_key(question, policy_hash)
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            INSERT OR REPLACE INTO semantic_cache
                (cache_key, normalized_question, policy_hash, payload, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                key,
                normalize_text(question),
                policy_hash,
                json.dumps(payload, ensure_ascii=False),
                utc_now(),
            ),
        )
