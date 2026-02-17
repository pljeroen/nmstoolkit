"""Global cross-save vault for ships, multitools, and companions."""

import json
import re
import time
from pathlib import Path

from nmstoolkit.paths import user_data_root

# Overridable base for testing
_VAULT_BASE = None


def _vault_root() -> Path:
    """Return vault root directory."""
    if _VAULT_BASE is not None:
        return _VAULT_BASE / "vault"
    return user_data_root() / "vault"


def vault_dir(entity_type: str) -> Path:
    """Return vault subdirectory for entity type, creating if needed."""
    d = _vault_root() / entity_type
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_to_vault(entity_type: str, data: dict, name: str):
    """Save an entity dict to the vault."""
    safe_name = re.sub(r"[^\w\-]", "_", name).strip("_")[:50] or "entity"
    timestamp = int(time.time())
    filename = f"{safe_name}_{timestamp}.json"
    d = vault_dir(entity_type)
    (d / filename).write_text(json.dumps(data, indent=2))


def scan_vault(entity_type: str) -> list:
    """Scan vault for saved entities. Returns [(path, name), ...]."""
    d = vault_dir(entity_type)
    results = []
    for p in sorted(d.glob("*.json")):
        try:
            data = json.loads(p.read_text())
            name = data.get("Name") or data.get("CustomName") or p.stem
            results.append((p, name))
        except (json.JSONDecodeError, OSError):
            pass
    return results


def load_from_vault(path: Path) -> dict:
    """Load an entity dict from vault."""
    return json.loads(path.read_text())


def delete_from_vault(path: Path):
    """Delete a vault entry."""
    try:
        path.unlink()
    except OSError:
        pass
