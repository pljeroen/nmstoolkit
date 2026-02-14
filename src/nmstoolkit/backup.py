"""Auto-backup before save operations."""

import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, Union


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def create_backup(
    source: Union[str, Path],
    backup_dir: Optional[Union[str, Path]] = None,
) -> Path:
    """Create a timestamped backup of a save file.

    Args:
        source: Path to the original file.
        backup_dir: Directory for backups. Defaults to source.parent / "backup".

    Returns:
        Path to the created backup file.

    Raises:
        FileNotFoundError: If source does not exist.
    """
    source = Path(source)
    if not source.exists():
        raise FileNotFoundError(f"Source file not found: {source}")

    if backup_dir is None:
        backup_dir = source.parent / "backup"
    backup_dir = Path(backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)

    stem = source.stem
    suffix = source.suffix
    backup_path = backup_dir / f"{stem}_{_timestamp()}{suffix}"
    shutil.copy2(source, backup_path)

    return backup_path
