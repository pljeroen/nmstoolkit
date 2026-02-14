"""Icon provider — resolves item IDs to QPixmap icons via IconCache."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

from nmstoolkit.core.game_catalogue import GameCatalogue
from nmstoolkit.core.icon_cache import IconCache


class IconProvider:
    """Provides icon paths for item IDs by looking up icon_map, catalogue, and cache."""

    def __init__(
        self,
        icon_cache: Optional[IconCache],
        catalogue: Optional[GameCatalogue],
        icon_map: Optional[Dict[str, str]] = None,
    ) -> None:
        self._cache = icon_cache
        self._catalogue = catalogue
        self._icon_map = icon_map or {}

    def get_icon_path(self, item_id: str) -> str:
        """Look up the DDS icon path for an item ID.

        Priority: exact icon_map match, then base-type fallback for procedural
        items (^UP_BOLTX#12345 → ^UP_BOLTX), then catalogue.
        Returns empty string if not found.
        """
        # 1. Exact match
        dds_path = self._icon_map.get(item_id, "")
        if dds_path:
            return dds_path

        # 2. Procedural item fallback: strip #nnnnn suffix
        if "#" in item_id:
            base_id = item_id.split("#")[0]
            dds_path = self._icon_map.get(base_id, "")
            if dds_path:
                return dds_path

        # 3. Catalogue lookup
        if self._catalogue is not None:
            item = self._catalogue.find_item(item_id)
            if item is not None:
                return item.get("icon", "")
            # Try base ID in catalogue too
            if "#" in item_id:
                base_id = item_id.split("#")[0]
                item = self._catalogue.find_item(base_id)
                if item is not None:
                    return item.get("icon", "")

        return ""

    def get_pixmap_path(self, item_id: str) -> Optional[Path]:
        """Return the cached PNG path for an item, or None if unavailable."""
        icon_dds = self.get_icon_path(item_id)
        if not icon_dds:
            return None
        if self._cache is None:
            return None
        return self._cache.get_icon(icon_dds)
