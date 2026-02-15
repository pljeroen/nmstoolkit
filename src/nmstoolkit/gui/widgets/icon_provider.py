"""Icon provider — resolves item IDs to QPixmap icons via IconCache."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

from nmstoolkit.core.game_catalogue import GameCatalogue
from nmstoolkit.core.icon_cache import IconCache

# Save files use YOURSHIP_/YOURSUIT_/YOURMULTI_/YOURFREIG_/YOURVEHIC_ prefixes
# for installed base technologies. These don't appear in the technology table.
# Map known special cases to their catalogue IDs.
# Upgrade module prefixes (UP_/UA_/U_) map to base tech categories.
# Strip the prefix + tier digit to find the base tech's icon.
_UPGRADE_PREFIX_MAP = {
    "UP_LASER": "LASER",
    "UA_LASER": "LASER",
    "UP_SCAN": "SCAN1",
    "UA_SCAN": "SCAN1",
    "UP_BOLT": "BOLT",
    "UP_GREN": "GRENADE",
    "UP_RAIL": "RAILGUN",
    "UP_SHOT": "SHOTGUN",
    "UP_SMG": "SMG",
    "UP_CANN": "CANNON",
    "UP_SENGUN": "SENGUN",
    "UP_SHLD": "PROTECT",
    "UP_ENGY": "ENERGY",
    "UP_JET": "JET1",
    "UP_HAZ": "PROTECT",
    "UP_HOT": "UT_HOT",
    "UP_COLD": "UT_COLD",
    "UP_TOX": "UT_TOX",
    "UP_RAD": "UT_RAD",
    "UP_UNW": "PRESSURE_SUIT",
    "UA_PULSE": "SHIPJUMP1",
    "UP_PULSE": "SHIPJUMP1",
    "UA_LAUN": "LAUNCHER",
    "UP_LAUN": "LAUNCHER",
    "UA_HYP": "HYPERDRIVE",
    "UP_HYP": "HYPERDRIVE",
    "UA_SGUN": "SHIPSHOTGUN",
    "UP_SGUN": "SHIPSHOTGUN",
    "UA_PHOTON": "SHIPGUN1",
    "UP_PHOTON": "SHIPGUN1",
    "UA_PHASE": "SHIPLAS1",
    "UP_PHASE": "SHIPLAS1",
    "UA_ROCKET": "SHIPROCKETS",
    "UP_ROCKET": "SHIPROCKETS",
    "UA_SHIELD": "SHIPSHIELD",
    "UP_SHIELD": "SHIPSHIELD",
    "UA_MINI": "SHIPMINIGUN",
    "UP_MINI": "SHIPMINIGUN",
    "UA_PLASMA": "SHIPPLASMA",
    "UP_PLASMA": "SHIPPLASMA",
    "UP_FREIG": "YOURFREIG_LAUNCHER",
    "UP_FRHYP": "HYPERDRIVE",
    "UP_FRSCAN": "YOURFREIG_SCAN",
    "U_LASER": "LASER",
    "U_SCANNER": "SCAN1",
    "U_BOLT": "BOLT",
    "U_GREN": "GRENADE",
    "U_RAIL": "RAILGUN",
    "U_SHOT": "SHOTGUN",
}

_YOUR_PREFIX_STRIP = ("YOURSHIP_", "YOURSUIT_", "YOURMULTI_", "YOURFREIG_", "YOURVEHIC_")

# Corvette module prefixes → mapped to base building part IDs for icon resolution.
# These are building parts that appear in corvette inventories.
_CORVETTE_MODULE_MAP = {
    "B_COK": "BUILD_YOURSHIP_COCKPIT",
    "B_HAB": "BUILD_YOURSHIP_HAB",
    "B_HAB1": "BUILD_YOURSHIP_HAB",
    "B_WNG": "BUILD_YOURSHIP_WING",
    "B_STR": "BUILD_YOURSHIP_STRUCTURE",
    "B_CON": "BUILD_YOURSHIP_CONNECTOR",
    "B_CON2": "BUILD_YOURSHIP_CONNECTOR",
    "B_CON_L": "BUILD_YOURSHIP_CONNECTOR",
    "B_TRU": "BUILD_YOURSHIP_THRUSTER",
    "B_TUR": "BUILD_YOURSHIP_TURRET",
    "B_LND": "BUILD_YOURSHIP_LANDING",
    "B_SHL": "BUILD_YOURSHIP_SHELL",
    "B_ALK": "BUILD_YOURSHIP_AIRLOCK",
    "B_GEN": "BUILD_YOURSHIP_GENERATOR",
    "B_DECO": "BUILD_YOURSHIP_DECO",
}

_YOUR_SPECIAL_MAP = {
    "YOURSHIP_LAUNCH": "LAUNCHER",
    "YOURSHIP_PULSEDRIVE": "SHIPJUMP1",
    "YOURSHIP_PHOTON": "SHIPGUN1",
    "YOURSHIP_PHASE": "SHIPLAS1",
    "YOURSHIP_ROCKET": "SHIPROCKETS",
    "YOURSHIP_SHIELD": "SHIPSHIELD",
    "YOURSHIP_SHOTGUN": "SHIPSHOTGUN",
    "YOURSHIP_MINIGUN": "SHIPMINIGUN",
    "YOURSHIP_PLASMA": "SHIPPLASMA",
    "YOURSHIP_TELEPORT": "SHIP_TELEPORT",
    "YOURSUIT_SHIELD": "PROTECT",
    "YOURFREIG_LAUNCH": "LAUNCHER",
    "YOURVEHIC_LASER": "VEHICLEGUN",
    "YOURVEHIC_GUN": "VEHICLELAS",
    "YOURVEHIC_BOOST": "VEHICLEBOOST",
}


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

        Priority: exact icon_map match, procedural suffix strip,
        catalogue lookup, YOUR* prefix resolution.
        Returns empty string if not found.
        """
        # 1. Exact match in icon_map
        dds_path = self._icon_map.get(item_id, "")
        if dds_path:
            return dds_path

        # 1b. Try without ^ prefix in icon_map (catalogue stores bare IDs)
        bare_id = item_id.lstrip("^") if item_id.startswith("^") else ""
        if bare_id:
            dds_path = self._icon_map.get(bare_id, "")
            if dds_path:
                return dds_path

        # 2. Procedural item fallback: strip #nnnnn suffix
        if "#" in item_id:
            base_id = item_id.split("#")[0]
            dds_path = self._icon_map.get(base_id, "")
            if dds_path:
                return dds_path

        # 3. Catalogue lookup (exact, then without ^ prefix)
        if self._catalogue is not None:
            item = self._catalogue.find_item(item_id)
            if item is None and bare_id:
                item = self._catalogue.find_item(bare_id)
            if item is not None:
                return item.get("icon", "")
            # Try base ID in catalogue too (procedural)
            if "#" in item_id:
                base_id = item_id.split("#")[0]
                item = self._catalogue.find_item(base_id)
                if item is None and base_id.startswith("^"):
                    item = self._catalogue.find_item(base_id.lstrip("^"))
                if item is not None:
                    return item.get("icon", "")

        uid = item_id.lstrip("^")

        # 4. YOUR* prefix resolution for installed base technologies
        resolved = self._resolve_your_prefix(uid)
        if resolved:
            result = self._lookup_resolved(resolved)
            if result:
                return result

        # 5. Upgrade module prefix resolution (UP_LASER1 -> LASER)
        resolved = self._resolve_upgrade_prefix(uid)
        if resolved:
            result = self._lookup_resolved(resolved)
            if result:
                return result

        # 6. Corvette module prefix resolution (B_COK_A -> BUILD_YOURSHIP_COCKPIT)
        resolved = self._resolve_corvette_module(uid)
        if resolved:
            result = self._lookup_resolved(resolved)
            if result:
                return result

        return ""

    def _lookup_resolved(self, resolved_id: str) -> str:
        """Try icon_map and catalogue for a resolved ID (with and without ^)."""
        dds_path = self._icon_map.get(resolved_id, "") or self._icon_map.get("^" + resolved_id, "")
        if dds_path:
            return dds_path
        if self._catalogue is not None:
            item = self._catalogue.find_item(resolved_id) or self._catalogue.find_item("^" + resolved_id)
            if item is not None:
                return item.get("icon", "")
        return ""

    def _resolve_your_prefix(self, uid: str) -> str:
        """Resolve a YOURSHIP_*/YOURSUIT_*/etc. ID to a catalogue tech ID.

        Returns the resolved ID, or empty string if not a YOUR* ID.
        """
        uid_upper = uid.upper()

        # Check special mapping first (handles irregular names)
        mapped = _YOUR_SPECIAL_MAP.get(uid_upper, "")
        if mapped:
            return mapped

        # Generic: strip prefix, try base name, then base + "1"
        for prefix in _YOUR_PREFIX_STRIP:
            if uid_upper.startswith(prefix):
                base = uid[len(prefix):]
                if self._catalogue is not None:
                    if self._catalogue.find_item(base) is not None:
                        return base
                    if self._catalogue.find_item(base + "1") is not None:
                        return base + "1"
                # Also try in icon_map
                if base in self._icon_map or "^" + base in self._icon_map:
                    return base
                if base + "1" in self._icon_map or "^" + base + "1" in self._icon_map:
                    return base + "1"
                return base  # Return stripped form even if not found

        return ""

    @staticmethod
    def _resolve_upgrade_prefix(uid: str) -> str:
        """Resolve an upgrade module ID (UP_LASER1, UA_HYP4) to a base tech ID.

        Returns the base tech ID, or empty string if not an upgrade module.
        """
        uid_upper = uid.upper()
        # Strip procedural suffix
        if "#" in uid_upper:
            uid_upper = uid_upper.split("#")[0]

        # Match longest prefix first
        best_match = ""
        best_base = ""
        for prefix, base_tech in _UPGRADE_PREFIX_MAP.items():
            if uid_upper.startswith(prefix) and len(prefix) > len(best_match):
                best_match = prefix
                best_base = base_tech
        return best_base

    @staticmethod
    def _resolve_corvette_module(uid: str) -> str:
        """Resolve a corvette module ID (B_COK_A, B_WNG_B) to a base building part ID.

        Returns the mapped building part ID, or empty string if not a corvette module.
        """
        uid_upper = uid.upper()
        # Strip procedural suffix
        if "#" in uid_upper:
            uid_upper = uid_upper.split("#")[0]
        # Match longest prefix first
        best_match = ""
        best_base = ""
        for prefix, base_id in _CORVETTE_MODULE_MAP.items():
            if uid_upper.startswith(prefix) and len(prefix) > len(best_match):
                best_match = prefix
                best_base = base_id
        return best_base

    def get_pixmap_path(self, item_id: str) -> Optional[Path]:
        """Return the cached PNG path for an item, or None if unavailable."""
        icon_dds = self.get_icon_path(item_id)
        if not icon_dds:
            return None
        if self._cache is None:
            return None
        return self._cache.get_icon(icon_dds)
