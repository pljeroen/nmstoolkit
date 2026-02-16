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

# Base building techs not in the game catalogue — direct DDS path mapping.
_BASE_TECH_ICON_MAP = {
    "COOKER": "TEXTURES/UI/FRONTEND/ICONS/BUILDABLE/BUILDABLE.COOKER.DDS",
    "BUILDSIGNAL": "TEXTURES/UI/FRONTEND/ICONS/BUILDABLE/BUILDABLE.SIGNAL.DDS",
    "BUILDSAVE": "TEXTURES/UI/FRONTEND/ICONS/BUILDABLE/BUILDABLE.SAVEPOINT.DDS",
    "YOURGLITCHSEP": "TEXTURES/UI/FRONTEND/ICONS/BUILDABLE/GROUPS/BUILDGROUP.GLITCH.DDS",
    "BUILD_REFINER1": "TEXTURES/UI/FRONTEND/ICONS/BUILDABLE/BUILDABLE.REFINER1.DDS",
    "BUILD_REFINER2": "TEXTURES/UI/FRONTEND/ICONS/BUILDABLE/BUILDABLE.REFINER2.DDS",
    "BUILD_REFINER3": "TEXTURES/UI/FRONTEND/ICONS/BUILDABLE/BUILDABLE.REFINER3.DDS",
    "BASE_BEAMSTONE": "TEXTURES/UI/FRONTEND/ICONS/BUILDABLE/BUILDABLE.BEAMSTONE.DDS",
    "BASE_BUBBLECLUS": "TEXTURES/UI/FRONTEND/ICONS/BUILDABLE/BUILDABLE.BUBBLECLUSTER.DDS",
    "BASE_WEIRDCUBE": "TEXTURES/UI/FRONTEND/ICONS/BUILDABLE/BUILDABLE.WEIRDCUBE.DDS",
    "PROC_LOOT": "TEXTURES/UI/FRONTEND/ICONS/PRODUCTS/PRODUCT.CURIO.1.DDS",
    "PROC_BIO": "TEXTURES/UI/FRONTEND/ICONS/PRODUCTS/PRODUCT.CURIO.1.DDS",
    "PROC_PLNT": "TEXTURES/UI/FRONTEND/ICONS/BUILDABLE/DECORATION.PLANTPOT3.DDS",
    "PROC_FARM": "TEXTURES/UI/FRONTEND/ICONS/BUILDABLE/DECORATION.PLANTPOT3.DDS",
    "PROC_TOOL": "TEXTURES/UI/FRONTEND/ICONS/PRODUCTS/PRODUCT.CURIO.1.DDS",
    "PROC_CAPT": "TEXTURES/UI/FRONTEND/ICONS/PRODUCTS/PRODUCT.CURIO.1.DDS",
    "PROC_CREW": "TEXTURES/UI/FRONTEND/ICONS/PRODUCTS/PRODUCT.CURIO.1.DDS",
}

# Corvette module type → DDS filename component for per-variant icon construction.
_CORVETTE_ICON_PREFIX = {
    "COK": "COK1X2", "HAB": "HAB1X1", "HAB1": "HAB1X2",
    "WNG": "WNG1X2", "TRU": "TRU1X1", "TUR": "TUR1X1",
    "SHL": "SHL1X1", "ALK": "ALK1X1", "GEN": "GEN1X1",
    "CON": "CON1X1", "CON2": "CON2", "CON_L": "CON1X1",
    "STR": "STR1X1", "DECO": "DECO1X1", "LND": "LND1X1",
    "BTRU": "BTRU1X1",
}

# Fossil type code → full type name for DDS path construction.
_FOSSIL_TYPE_MAP = {
    "BI": "BIPED", "QUAD": "QUADRUPED", "WORM": "WORM",
    "BIRD": "BIRD", "GRUN": "GRUNT",
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
        # 0. Verified static map (overrides items.json which has legacy icon formats)
        uid = item_id.lstrip("^")
        dds_path = _BASE_TECH_ICON_MAP.get(uid, "")
        if dds_path:
            return dds_path

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

        # 6. Corvette module DDS path construction (B_COK_A -> per-variant icon)
        dds_path = self._resolve_corvette_module(uid)
        if dds_path:
            return dds_path

        # 7. Fossil part DDS path construction (FOS_BI_BODY_AC -> per-part icon)
        dds_path = self._resolve_fossil_icon(uid)
        if dds_path:
            return dds_path

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
        """Resolve a corvette module ID to a full DDS icon path.

        B_COK_A → TEXTURES/UI/FRONTEND/ICONS/BUILDABLE/BIGGS_BIG_COK1X2_A.DDS
        Returns the DDS path, or empty string if not a corvette module.
        """
        uid_upper = uid.upper()
        if "#" in uid_upper:
            uid_upper = uid_upper.split("#")[0]
        if not uid_upper.startswith("B_"):
            return ""
        # Strip B_ prefix, split into type parts and variant
        remainder = uid_upper[2:]  # e.g. "COK_A", "HAB1_A", "CON_L_A"
        # Match longest type prefix in _CORVETTE_ICON_PREFIX
        best_type = ""
        best_dds_part = ""
        for type_key, dds_part in _CORVETTE_ICON_PREFIX.items():
            if remainder.startswith(type_key + "_") and len(type_key) > len(best_type):
                best_type = type_key
                best_dds_part = dds_part
        if not best_type:
            return ""
        variant = remainder[len(best_type) + 1:]  # e.g. "A", "B"
        if not variant:
            return ""
        return f"TEXTURES/UI/FRONTEND/ICONS/BUILDABLE/BIGGS_BIG_{best_dds_part}_{variant}.DDS"

    @staticmethod
    def _resolve_fossil_icon(uid: str) -> str:
        """Resolve a fossil item ID to a full DDS icon path.

        FOS_BI_BODY_AC → TEXTURES/UI/FRONTEND/ICONS/FOSSILBONES/FOSSIL.BIPED.BODY.AC.DDS
        PROC_FOSS → TEXTURES/UI/FRONTEND/ICONS/FOSSILBONES/FOSSIL.DISP.DDS
        Returns the DDS path, or empty string if not a fossil item.
        """
        uid_upper = uid.upper()
        if "#" in uid_upper:
            uid_upper = uid_upper.split("#")[0]
        # Procedural fossil samples
        if uid_upper.startswith("PROC_FOSS"):
            return "TEXTURES/UI/FRONTEND/ICONS/FOSSILBONES/FOSSIL.DISP.DDS"
        # FOS_<TYPE>_<PART>[_<VARIANT>] pattern
        if not uid_upper.startswith("FOS_"):
            return ""
        parts = uid_upper.split("_")
        if len(parts) < 3:
            return ""
        type_code = parts[1]
        full_type = _FOSSIL_TYPE_MAP.get(type_code, "")
        if not full_type:
            return ""
        part_name = parts[2]
        variant = parts[3] if len(parts) > 3 else ""
        if variant:
            return f"TEXTURES/UI/FRONTEND/ICONS/FOSSILBONES/FOSSIL.{full_type}.{part_name}.{variant}.DDS"
        return f"TEXTURES/UI/FRONTEND/ICONS/FOSSILBONES/FOSSIL.{full_type}.{part_name}.DDS"

    def get_pixmap_path(self, item_id: str) -> Optional[Path]:
        """Return the cached PNG path for an item, or None if unavailable."""
        icon_dds = self.get_icon_path(item_id)
        if not icon_dds:
            return None
        if self._cache is None:
            return None
        return self._cache.get_icon(icon_dds)
