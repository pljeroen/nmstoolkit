"""Extraction cache metadata for update-aware invalidation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Dict, Iterable, Optional


def file_signature(path: Path) -> dict:
    """Return a stable signature for a file path."""
    if not path.exists():
        return {"path": str(path), "exists": False}
    st = path.stat()
    return {
        "path": str(path),
        "exists": True,
        "size": st.st_size,
        "mtime_ns": st.st_mtime_ns,
    }


def fingerprint_from_files(files: Iterable[Path], extra: Optional[dict] = None) -> str:
    """Build a content fingerprint from file metadata + optional extras."""
    payload = {
        "files": [file_signature(Path(p)) for p in files],
        "extra": extra or {},
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def load_manifest(path: Path) -> Dict[str, dict]:
    """Load extraction manifest from disk."""
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_manifest(path: Path, manifest: Dict[str, dict]) -> None:
    """Persist extraction manifest to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")


def is_scheme_fresh(path: Path, scheme: str, fingerprint: str) -> bool:
    """Check if a scheme entry matches the computed fingerprint."""
    manifest = load_manifest(path)
    entry = manifest.get(scheme, {})
    return entry.get("fingerprint") == fingerprint


def update_scheme(path: Path, scheme: str, fingerprint: str, meta: Optional[dict] = None) -> None:
    """Write/update a scheme entry in the extraction manifest."""
    manifest = load_manifest(path)
    manifest[scheme] = {
        "fingerprint": fingerprint,
        "meta": meta or {},
    }
    save_manifest(path, manifest)

