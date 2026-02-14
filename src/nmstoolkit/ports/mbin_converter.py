"""Port for MBIN to EXML conversion.

Defines the interface for converting NMS .mbin binary data to EXML text.
Implementation is provided by adapters (e.g. MbinCompilerAdapter).
"""

from typing import Dict, Protocol


class MbinConverter(Protocol):
    """Convert MBIN binary data to EXML text."""

    def convert(self, mbin_data: bytes) -> str:
        """Convert a single MBIN file's bytes to EXML string."""
        ...

    def convert_batch(self, mbin_files: Dict[str, bytes]) -> Dict[str, str]:
        """Convert multiple MBIN files.

        Args:
            mbin_files: Dict mapping filename to MBIN bytes.

        Returns:
            Dict mapping filename to EXML string.
        """
        ...
