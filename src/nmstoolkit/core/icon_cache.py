"""Icon cache — extracts DDS icons from PAK, converts to PNG, caches to disk.

Application service that coordinates PAK extraction with Pillow conversion.
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import List, Optional

from PIL import Image

from nmstoolkit.adapters.hgpak_adapter import HgpakAdapter

def _default_cache_dir() -> Path:
    """Return persistent cache dir next to exe or in project data dir."""
    import sys
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).parent
    else:
        base = Path(__file__).parent.parent / "data"
    d = base / "icons"
    d.mkdir(parents=True, exist_ok=True)
    return d


class IconCache:
    """Manages extraction and caching of NMS item icons as PNG thumbnails."""

    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        thumbnail_size: int = 64,
    ) -> None:
        self._cache_dir = cache_dir if cache_dir is not None else _default_cache_dir()
        self._thumbnail_size = thumbnail_size
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    @property
    def cache_dir(self) -> Path:
        return self._cache_dir

    def _cache_key(self, dds_path: str) -> str:
        """Convert a DDS texture path to a safe flat filename."""
        return dds_path.lower().replace("/", "_").replace("\\", "_").replace(".dds", ".png")

    def _cache_path(self, dds_path: str) -> Path:
        return self._cache_dir / self._cache_key(dds_path)

    def get_icon(self, dds_path: str) -> Optional[Path]:
        """Return cached PNG path if it exists, None otherwise."""
        cached = self._cache_path(dds_path)
        if cached.exists():
            return cached
        return None

    def store_icon(self, dds_path: str, dds_data: bytes) -> Optional[Path]:
        """Convert DDS data to a PNG thumbnail and cache it.

        Returns the cached PNG path, or None if conversion fails.
        """
        out_path = self._cache_path(dds_path)
        if out_path.exists():
            return out_path

        try:
            img = Image.open(BytesIO(dds_data))
            if img.size != (self._thumbnail_size, self._thumbnail_size):
                img = img.resize(
                    (self._thumbnail_size, self._thumbnail_size),
                    Image.LANCZOS,
                )
            img.save(out_path, "PNG")
            return out_path
        except Exception:
            return None

    def build_cache(
        self,
        pak_path: Path,
        icon_paths: List[str],
    ) -> int:
        """Batch extract icons from a PAK file and cache as PNGs.

        Args:
            pak_path: Path to the .pak file containing icon textures.
            icon_paths: List of DDS paths within the PAK to extract.

        Returns:
            Number of icons successfully cached.
        """
        with HgpakAdapter.from_path(pak_path) as pak:
            extracted = pak.extract(paths=icon_paths)

        count = 0
        for dds_path, dds_data in extracted.items():
            if self.store_icon(dds_path, dds_data) is not None:
                count += 1
        return count
