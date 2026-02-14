"""Icon extractor — extracts DDS icons from PAK and builds item-to-icon mapping.

Application service: coordinates HgpakAdapter (PAK reading) with IconCache (DDS→PNG).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Optional

from nmstoolkit.adapters.hgpak_adapter import HgpakAdapter
from nmstoolkit.core.icon_cache import IconCache

_ICON_PREFIX = "textures/ui/frontend/icons/"
_PAK_NAME = "NMSARC.TexUI.pak"


def _normalize_for_match(name: str) -> str:
    """Strip punctuation and lowercase for fuzzy matching."""
    return re.sub(r"[^a-z0-9]", "", name.lower())


class IconExtractor:
    """Extracts game icons from PAK files and builds item-to-DDS mapping."""

    def __init__(self, game_dir: Path, cache_dir: Path) -> None:
        self._game_dir = game_dir
        self._cache_dir = cache_dir
        self._icon_cache = IconCache(cache_dir)

    @property
    def icon_map_path(self) -> Path:
        return self._cache_dir / "icon_map.json"

    def extract_all_icons(self) -> int:
        """Extract all icon DDS files from PAK and cache as PNG.

        Returns the number of icons successfully cached.
        """
        pak_path = self._find_pak()
        if pak_path is None:
            return 0

        with HgpakAdapter.from_path(pak_path) as pak:
            all_files = pak.list_files()
            icon_paths = [
                f for f in all_files
                if f.lower().startswith(_ICON_PREFIX) and f.lower().endswith(".dds")
            ]
            if not icon_paths:
                return 0

            extracted = pak.extract(paths=icon_paths)

        count = 0
        for dds_path, dds_data in extracted.items():
            if self._icon_cache.store_icon(dds_path, dds_data) is not None:
                count += 1
        return count

    def build_icon_map(
        self, items_json_path: Path, dds_paths: List[str]
    ) -> Dict[str, str]:
        """Build a mapping of item_id → DDS path using fuzzy name matching.

        Matching strategy (priority order):
        1. Exact normalized match: SUBSTANCE-FUEL1.PNG → substancefuel1 in DDS basenames
        2. ID-based match: item ID in DDS filename
        """
        with open(items_json_path, "r", encoding="utf-8") as f:
            items = json.load(f)

        # Build DDS lookup: normalized basename → full path
        dds_by_normalized = {}
        for dds_path in dds_paths:
            basename = Path(dds_path).stem  # e.g. "substance.fuel.1"
            normalized = _normalize_for_match(basename)
            dds_by_normalized[normalized] = dds_path

        icon_map: Dict[str, str] = {}
        for item in items:
            item_id = item.get("id", "")
            icon_name = item.get("icon", "")
            if not item_id or not icon_name:
                continue

            # Strategy 1: normalize the icon field and match
            icon_normalized = _normalize_for_match(Path(icon_name).stem)
            if icon_normalized in dds_by_normalized:
                icon_map[item_id] = dds_by_normalized[icon_normalized]
                continue

            # Strategy 2: try item ID in DDS filenames
            id_normalized = _normalize_for_match(item_id.lstrip("^"))
            for norm_key, dds_path in dds_by_normalized.items():
                if id_normalized in norm_key:
                    icon_map[item_id] = dds_path
                    break

        return icon_map

    def save_icon_map(self, icon_map: Dict[str, str]) -> None:
        """Persist icon map to JSON."""
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        with open(self.icon_map_path, "w", encoding="utf-8") as f:
            json.dump(icon_map, f, separators=(",", ":"))

    def load_icon_map(self) -> Dict[str, str]:
        """Load icon map from JSON, or return empty dict."""
        if not self.icon_map_path.exists():
            return {}
        with open(self.icon_map_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _find_pak(self) -> Optional[Path]:
        """Locate the TexUI PAK file in the game directory."""
        pak_path = self._game_dir / "GAMEDATA" / "PCBANKS" / _PAK_NAME
        if pak_path.exists():
            return pak_path
        # Also check directly under game_dir
        pak_path = self._game_dir / _PAK_NAME
        if pak_path.exists():
            return pak_path
        return None
