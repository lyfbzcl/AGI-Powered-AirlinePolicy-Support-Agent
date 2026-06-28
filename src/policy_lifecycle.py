import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from policy_metadata import (
    DEFAULT_EFFECTIVE_DATE,
    DEFAULT_VERSION,
    document_hash,
    infer_policy_area,
)


ROOT_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT_DIR / "data" / "raw"
INDEX_DIR = ROOT_DIR / "index"
MANIFEST_PATH = INDEX_DIR / "policy_manifest.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def build_policy_manifest(data_dir: Path = RAW_DIR) -> dict[str, Any]:
    """Build a lightweight manifest for active raw policy documents."""
    manifest: dict[str, Any] = {}
    if not data_dir.exists():
        return manifest

    for file_path in sorted(data_dir.glob("*.txt")):
        text = file_path.read_text(encoding="utf-8")
        manifest[file_path.name] = {
            "doc_hash": document_hash(text),
            "policy_area": infer_policy_area(file_path.name, text),
            "version": DEFAULT_VERSION,
            "status": "active",
            "effective_date": DEFAULT_EFFECTIVE_DATE,
            "last_indexed_at": utc_now(),
        }
    return manifest


def save_policy_manifest(manifest: dict[str, Any], path: Path = MANIFEST_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def load_policy_manifest(path: Path = MANIFEST_PATH) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def manifest_status(data_dir: Path = RAW_DIR, path: Path = MANIFEST_PATH) -> dict[str, Any]:
    """Compare current raw policy hashes with the saved manifest."""
    current = build_policy_manifest(data_dir)
    saved = load_policy_manifest(path)
    changed = []
    missing = []
    new = []

    for source, metadata in current.items():
        if source not in saved:
            new.append(source)
        elif saved[source].get("doc_hash") != metadata.get("doc_hash"):
            changed.append(source)

    for source in saved:
        if source not in current:
            missing.append(source)

    return {
        "is_current": not changed and not missing and not new,
        "changed": changed,
        "missing": missing,
        "new": new,
    }


def rebuild_manifest() -> dict[str, Any]:
    manifest = build_policy_manifest()
    save_policy_manifest(manifest)
    return manifest
