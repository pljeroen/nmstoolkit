"""Port for reading game archive files.

Defines the interface for extracting files from NMS .pak archives.
Implementation is provided by adapters (e.g. HgpakAdapter).
"""

from pathlib import Path
from typing import Dict, List, Optional, Protocol, Union


class GameArchiveReader(Protocol):
    """Read-only access to a game archive (.pak file)."""

    def open(self, path: Union[str, Path]) -> None:
        """Open an archive file for reading."""
        ...

    def close(self) -> None:
        """Close the archive and release resources."""
        ...

    def list_files(self) -> List[str]:
        """Return all file paths contained in the archive (excluding manifest)."""
        ...

    def extract(
        self,
        paths: Optional[List[str]] = None,
        pattern: Optional[str] = None,
    ) -> Dict[str, bytes]:
        """Extract files from the archive.

        Args:
            paths: Specific file paths to extract. None means all files.
            pattern: Glob pattern to filter files (e.g. '*.mbin').
                     Ignored if paths is provided.

        Returns:
            Dict mapping file path to raw bytes.
            Paths not found in the archive are silently omitted.
        """
        ...
