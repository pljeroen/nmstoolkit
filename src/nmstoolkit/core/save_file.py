"""SaveFile model — loads, wraps, and saves NMS save data with readable keys."""

from pathlib import Path
from typing import Any, Dict, Optional, Union

from nmstoolkit.core.codec import (
    load_key_map,
    map_keys,
    read_hg_file,
    unmap_keys,
    write_hg_file,
)


class SaveFile:
    """Wraps a NMS save file with unmapped (readable) keys.

    The internal `data` dict uses readable key names. On save, keys are
    remapped back to obfuscated form before LZ4 compression.
    """

    def __init__(self, data: dict, key_map: Dict[str, str]) -> None:
        self.data = data
        self._key_map = key_map

    @classmethod
    def load(
        cls, path: Union[str, Path], key_map_path: Union[str, Path]
    ) -> "SaveFile":
        """Load a .hg file with key unmapping."""
        key_map = load_key_map(key_map_path)
        raw = read_hg_file(path)
        data = unmap_keys(raw, key_map)
        return cls(data, key_map)

    def save(self, path: Union[str, Path]) -> None:
        """Save to .hg file with key remapping and LZ4 compression."""
        remapped = map_keys(self.data, self._key_map)
        write_hg_file(path, remapped)

    @property
    def version(self) -> int:
        return self.data.get("Version", 0)

    @property
    def platform(self) -> Optional[str]:
        return self.data.get("Platform")

    @property
    def active_context(self) -> Optional[str]:
        return self.data.get("ActiveContext")

    @property
    def base_context(self) -> Optional[dict]:
        return self.data.get("BaseContext")

    @property
    def expedition_context(self) -> Optional[dict]:
        return self.data.get("ExpeditionContext")

    def player_state_data(self, context: str = "base") -> Optional[dict]:
        """Get PlayerStateData from the specified context.

        Args:
            context: "base" or "expedition"
        """
        ctx = self.base_context if context == "base" else self.expedition_context
        if ctx is None:
            return None
        return ctx.get("PlayerStateData")
