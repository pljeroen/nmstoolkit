"""Tests for icon provider.

Tests R-IPROV-01 through R-IPROV-03, R-ICO-01 through R-ICO-05.
Per-category icon resolution tests: R-ICON-01 through R-ICON-10.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from nmstoolkit.gui.widgets.icon_provider import IconProvider


# ---------------------------------------------------------------------------
# R-IPROV-01: IconProvider initialization
# ---------------------------------------------------------------------------

class TestIconProviderInit:
    """R-IPROV-01: IconProvider wraps IconCache and GameCatalogue."""

    def test_create_without_catalogue(self):
        provider = IconProvider(icon_cache=None, catalogue=None)
        assert provider is not None

    def test_create_with_mocks(self):
        cache = MagicMock()
        catalogue = MagicMock()
        provider = IconProvider(icon_cache=cache, catalogue=catalogue)
        assert provider is not None


# ---------------------------------------------------------------------------
# R-IPROV-02: Icon path lookup from catalogue
# ---------------------------------------------------------------------------

class TestIconPathLookup:
    """R-IPROV-02: Look up icon DDS path for an item ID via catalogue."""

    def test_lookup_product_icon(self):
        catalogue = MagicMock()
        catalogue.find_item.return_value = {
            "id": "CASING",
            "icon": "TEXTURES/UI/FRONTEND/ICONS/U4PRODUCTS/PRODUCT.CASING.DDS",
        }
        provider = IconProvider(icon_cache=None, catalogue=catalogue)
        assert provider.get_icon_path("CASING") == "TEXTURES/UI/FRONTEND/ICONS/U4PRODUCTS/PRODUCT.CASING.DDS"

    def test_lookup_unknown_item_returns_empty(self):
        catalogue = MagicMock()
        catalogue.find_item.return_value = None
        provider = IconProvider(icon_cache=None, catalogue=catalogue)
        assert provider.get_icon_path("UNKNOWN") == ""

    def test_no_catalogue_returns_empty(self):
        provider = IconProvider(icon_cache=None, catalogue=None)
        assert provider.get_icon_path("CASING") == ""


# ---------------------------------------------------------------------------
# R-IPROV-03: get_pixmap_path returns cached PNG path
# ---------------------------------------------------------------------------

class TestGetPixmapPath:
    """R-IPROV-03: get_pixmap_path returns Path to cached PNG for an item."""

    def test_returns_cached_path(self, tmp_path):
        fake_png = tmp_path / "test.png"
        fake_png.write_bytes(b"fake png")

        cache = MagicMock()
        cache.get_icon.return_value = fake_png

        catalogue = MagicMock()
        catalogue.find_item.return_value = {
            "id": "FUEL1",
            "icon": "TEXTURES/UI/ICONS/FUEL.DDS",
        }

        provider = IconProvider(icon_cache=cache, catalogue=catalogue)
        result = provider.get_pixmap_path("FUEL1")
        assert result == fake_png

    def test_returns_none_when_not_cached(self):
        cache = MagicMock()
        cache.get_icon.return_value = None

        catalogue = MagicMock()
        catalogue.find_item.return_value = {
            "id": "FUEL1",
            "icon": "TEXTURES/UI/ICONS/FUEL.DDS",
        }

        provider = IconProvider(icon_cache=cache, catalogue=catalogue)
        result = provider.get_pixmap_path("FUEL1")
        assert result is None

    def test_returns_none_when_no_icon_path(self):
        cache = MagicMock()
        catalogue = MagicMock()
        catalogue.find_item.return_value = None

        provider = IconProvider(icon_cache=cache, catalogue=catalogue)
        result = provider.get_pixmap_path("UNKNOWN")
        assert result is None


# ---------------------------------------------------------------------------
# R-ICO-01 through R-ICO-04: Caret-prefixed items resolve via catalogue
# ---------------------------------------------------------------------------

def _make_catalogue_with_items(items_by_id):
    """Create a mock catalogue that stores items by bare ID (no caret)."""
    catalogue = MagicMock()

    def find_item(item_id):
        return items_by_id.get(item_id)

    catalogue.find_item.side_effect = find_item
    return catalogue


class TestCaretPrefixCatalogueLookup:
    """R-ICO-01..04: Items with ^ prefix must resolve via catalogue using bare ID."""

    def test_light_fissure_caret_resolves(self):
        """R-ICO-01: ^BASE_BEAMSTONE resolves to icon via catalogue's BASE_BEAMSTONE."""
        cat = _make_catalogue_with_items({
            "BASE_BEAMSTONE": {"id": "BASE_BEAMSTONE", "icon": "TEXTURES/UI/FRONTEND/ICONS/BASEBUILDING/BASE.BEAMSTONE.DDS"},
        })
        provider = IconProvider(icon_cache=None, catalogue=cat)
        assert provider.get_icon_path("^BASE_BEAMSTONE") != ""

    def test_bubble_cluster_caret_resolves(self):
        """R-ICO-02: ^BASE_BUBBLECLUS resolves to icon via catalogue's BASE_BUBBLECLUS."""
        cat = _make_catalogue_with_items({
            "BASE_BUBBLECLUS": {"id": "BASE_BUBBLECLUS", "icon": "TEXTURES/UI/FRONTEND/ICONS/BASEBUILDING/BASE.BUBBLECLUS.DDS"},
        })
        provider = IconProvider(icon_cache=None, catalogue=cat)
        assert provider.get_icon_path("^BASE_BUBBLECLUS") != ""

    def test_signal_booster_caret_resolves(self):
        """R-ICO-03: ^BUILDSIGNAL resolves to icon via catalogue's BUILDSIGNAL."""
        cat = _make_catalogue_with_items({
            "BUILDSIGNAL": {"id": "BUILDSIGNAL", "icon": "TEXTURES/UI/FRONTEND/ICONS/BASEBUILDING/BUILD.SIGNAL.DDS"},
        })
        provider = IconProvider(icon_cache=None, catalogue=cat)
        assert provider.get_icon_path("^BUILDSIGNAL") != ""

    def test_nutrient_processor_caret_resolves(self):
        """R-ICO-04: ^COOKER resolves to icon via catalogue's COOKER."""
        cat = _make_catalogue_with_items({
            "COOKER": {"id": "COOKER", "icon": "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/COOKER.DDS"},
        })
        provider = IconProvider(icon_cache=None, catalogue=cat)
        assert provider.get_icon_path("^COOKER") != ""

    def test_caret_item_not_in_catalogue_returns_empty(self):
        """Items with ^ that aren't in catalogue still return empty."""
        cat = _make_catalogue_with_items({})
        provider = IconProvider(icon_cache=None, catalogue=cat)
        assert provider.get_icon_path("^NONEXISTENT") == ""

    def test_bare_id_still_works(self):
        """Items without ^ should still resolve normally."""
        cat = _make_catalogue_with_items({
            "FUEL1": {"id": "FUEL1", "icon": "TEXTURES/FUEL1.DDS"},
        })
        provider = IconProvider(icon_cache=None, catalogue=cat)
        assert provider.get_icon_path("FUEL1") == "TEXTURES/FUEL1.DDS"


# ---------------------------------------------------------------------------
# R-ICO-05: Corvette module icons resolve through module map + catalogue
# ---------------------------------------------------------------------------

class TestCorvetteModuleCatalogueResolution:
    """R-ICO-05: Corvette modules (B_COK_A etc.) resolve icons via module map → catalogue."""

    def test_cockpit_resolves_via_catalogue(self):
        """B_COK_A → BUILD_YOURSHIP_COCKPIT → catalogue icon."""
        cat = _make_catalogue_with_items({
            "BUILD_YOURSHIP_COCKPIT": {
                "id": "BUILD_YOURSHIP_COCKPIT",
                "icon": "TEXTURES/UI/FRONTEND/ICONS/BUILDABLE/YOURSHIP.COCKPIT.DDS",
            },
        })
        provider = IconProvider(icon_cache=None, catalogue=cat)
        assert provider.get_icon_path("^B_COK_A") != ""

    def test_wing_resolves_via_catalogue(self):
        """B_WNG_B → BUILD_YOURSHIP_WING → catalogue icon."""
        cat = _make_catalogue_with_items({
            "BUILD_YOURSHIP_WING": {
                "id": "BUILD_YOURSHIP_WING",
                "icon": "TEXTURES/UI/FRONTEND/ICONS/BUILDABLE/YOURSHIP.WING.DDS",
            },
        })
        provider = IconProvider(icon_cache=None, catalogue=cat)
        assert provider.get_icon_path("^B_WNG_B") != ""

    def test_thruster_resolves_via_catalogue(self):
        """B_TRU_A → BUILD_YOURSHIP_THRUSTER → catalogue icon."""
        cat = _make_catalogue_with_items({
            "BUILD_YOURSHIP_THRUSTER": {
                "id": "BUILD_YOURSHIP_THRUSTER",
                "icon": "TEXTURES/UI/FRONTEND/ICONS/BUILDABLE/YOURSHIP.THRUSTER.DDS",
            },
        })
        provider = IconProvider(icon_cache=None, catalogue=cat)
        assert provider.get_icon_path("^B_TRU_A") != ""

    def test_all_corvette_prefixes_resolve_with_catalogue(self):
        """Every prefix in _CORVETTE_MODULE_MAP should resolve when target is in catalogue."""
        from nmstoolkit.gui.widgets.icon_provider import _CORVETTE_MODULE_MAP

        # Build catalogue with all corvette build targets
        items = {}
        for target_id in set(_CORVETTE_MODULE_MAP.values()):
            items[target_id] = {"id": target_id, "icon": f"TEXTURES/{target_id}.DDS"}

        cat = _make_catalogue_with_items(items)
        provider = IconProvider(icon_cache=None, catalogue=cat)

        for prefix, target_id in _CORVETTE_MODULE_MAP.items():
            test_id = f"^{prefix}_A"
            result = provider.get_icon_path(test_id)
            assert result != "", f"{test_id} → {target_id} should resolve but got empty"


# ===========================================================================
# ICON-RESOLUTION CONTRACT — Per-Category Resolution Tests (R-ICON-01..10)
#
# Each category has its own test class with independent fixtures.
# Tests assert EXACT DDS paths, not just non-empty.
# ===========================================================================


# ---------------------------------------------------------------------------
# R-ICON-02: Category 1 — Direct icon_map match (step 1)
# ---------------------------------------------------------------------------

class TestCategory1DirectIconMap:
    """R-ICON-02: Items whose ID appears verbatim in icon_map.json.

    Resolution step 1: self._icon_map.get(item_id).
    Covers substances, products, and technologies with exact IDs.
    """

    @pytest.fixture()
    def provider(self):
        """Provider with realistic icon_map entries, no catalogue."""
        icon_map = {
            "FUEL1": "TEXTURES/UI/FRONTEND/ICONS/SUBSTANCES/SUBSTANCE.FUEL.1.DDS",
            "CARBON": "TEXTURES/UI/FRONTEND/ICONS/SUBSTANCES/SUBSTANCE.PLANT.DDS",
            "OXYGEN": "TEXTURES/UI/FRONTEND/ICONS/SUBSTANCES/SUBSTANCE.OXYGEN.DDS",
            "ANTIMATTER": "TEXTURES/UI/FRONTEND/ICONS/U4PRODUCTS/PRODUCT.ANTIMATTER.DDS",
            "CASING": "TEXTURES/UI/FRONTEND/ICONS/U4PRODUCTS/PRODUCT.CASING.DDS",
            "ATLAS_SEED": "TEXTURES/UI/FRONTEND/ICONS/U4PRODUCTS/PRODUCT.ATLASSEED.DDS",
            "HYPERDRIVE": "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.YOURSHIP_HYPERDRIVE.DDS",
            "LASER": "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.LASER.DDS",
            "BOLT": "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.BOLT.DDS",
        }
        return IconProvider(icon_cache=None, catalogue=None, icon_map=icon_map)

    def test_substance_fuel(self, provider):
        assert provider.get_icon_path("FUEL1") == "TEXTURES/UI/FRONTEND/ICONS/SUBSTANCES/SUBSTANCE.FUEL.1.DDS"

    def test_substance_carbon(self, provider):
        assert provider.get_icon_path("CARBON") == "TEXTURES/UI/FRONTEND/ICONS/SUBSTANCES/SUBSTANCE.PLANT.DDS"

    def test_substance_oxygen(self, provider):
        assert provider.get_icon_path("OXYGEN") == "TEXTURES/UI/FRONTEND/ICONS/SUBSTANCES/SUBSTANCE.OXYGEN.DDS"

    def test_product_antimatter(self, provider):
        assert provider.get_icon_path("ANTIMATTER") == "TEXTURES/UI/FRONTEND/ICONS/U4PRODUCTS/PRODUCT.ANTIMATTER.DDS"

    def test_product_casing(self, provider):
        assert provider.get_icon_path("CASING") == "TEXTURES/UI/FRONTEND/ICONS/U4PRODUCTS/PRODUCT.CASING.DDS"

    def test_product_atlas_seed(self, provider):
        assert provider.get_icon_path("ATLAS_SEED") == "TEXTURES/UI/FRONTEND/ICONS/U4PRODUCTS/PRODUCT.ATLASSEED.DDS"

    def test_tech_hyperdrive(self, provider):
        assert provider.get_icon_path("HYPERDRIVE") == "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.YOURSHIP_HYPERDRIVE.DDS"

    def test_tech_laser(self, provider):
        assert provider.get_icon_path("LASER") == "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.LASER.DDS"

    def test_tech_bolt(self, provider):
        assert provider.get_icon_path("BOLT") == "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.BOLT.DDS"

    def test_icon_map_takes_priority_over_catalogue(self):
        """When item is in both icon_map and catalogue, icon_map wins (step 1 before step 3)."""
        icon_map = {"FUEL1": "TEXTURES/FROM_MAP.DDS"}
        cat = _make_catalogue_with_items({"FUEL1": {"id": "FUEL1", "icon": "TEXTURES/FROM_CAT.DDS"}})
        provider = IconProvider(icon_cache=None, catalogue=cat, icon_map=icon_map)
        assert provider.get_icon_path("FUEL1") == "TEXTURES/FROM_MAP.DDS"


# ---------------------------------------------------------------------------
# R-ICON-03: Category 2 — Caret-prefixed items (step 1b)
# ---------------------------------------------------------------------------

class TestCategory2CaretPrefix:
    """R-ICON-03: Items stored as ^ID in save data (installed techs, base parts).

    Resolution step 1b: strip ^, try bare ID in icon_map.
    Also falls through to step 3 (catalogue) for ^items not in icon_map.
    """

    @pytest.fixture()
    def icon_map(self):
        return {
            "LASER": "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.LASER.DDS",
            "BOLT": "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.BOLT.DDS",
            "HYPERDRIVE": "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.YOURSHIP_HYPERDRIVE.DDS",
            "SHIPJUMP1": "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.YOURSHIP_PULSEDRIVE.DDS",
            "PROTECT": "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.YOURSUIT_ARMOUR.DDS",
        }

    def test_caret_laser_resolves_via_icon_map(self, icon_map):
        provider = IconProvider(icon_cache=None, catalogue=None, icon_map=icon_map)
        assert provider.get_icon_path("^LASER") == "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.LASER.DDS"

    def test_caret_bolt_resolves_via_icon_map(self, icon_map):
        provider = IconProvider(icon_cache=None, catalogue=None, icon_map=icon_map)
        assert provider.get_icon_path("^BOLT") == "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.BOLT.DDS"

    def test_caret_hyperdrive_resolves_via_icon_map(self, icon_map):
        provider = IconProvider(icon_cache=None, catalogue=None, icon_map=icon_map)
        assert provider.get_icon_path("^HYPERDRIVE") == "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.YOURSHIP_HYPERDRIVE.DDS"

    def test_caret_shipjump_resolves_via_icon_map(self, icon_map):
        provider = IconProvider(icon_cache=None, catalogue=None, icon_map=icon_map)
        assert provider.get_icon_path("^SHIPJUMP1") == "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.YOURSHIP_PULSEDRIVE.DDS"

    def test_caret_protect_resolves_via_icon_map(self, icon_map):
        provider = IconProvider(icon_cache=None, catalogue=None, icon_map=icon_map)
        assert provider.get_icon_path("^PROTECT") == "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.YOURSUIT_ARMOUR.DDS"

    def test_caret_base_part_resolves_via_catalogue(self):
        """^BASE_BEAMSTONE not in icon_map, but in catalogue → step 3."""
        cat = _make_catalogue_with_items({
            "BASE_BEAMSTONE": {"id": "BASE_BEAMSTONE", "icon": "TEXTURES/UI/FRONTEND/ICONS/BASEBUILDING/BASE.BEAMSTONE.DDS"},
        })
        provider = IconProvider(icon_cache=None, catalogue=cat)
        assert provider.get_icon_path("^BASE_BEAMSTONE") == "TEXTURES/UI/FRONTEND/ICONS/BASEBUILDING/BASE.BEAMSTONE.DDS"

    def test_caret_cooker_resolves_via_catalogue(self):
        """^COOKER not in icon_map, but in catalogue → step 3."""
        cat = _make_catalogue_with_items({
            "COOKER": {"id": "COOKER", "icon": "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/COOKER.DDS"},
        })
        provider = IconProvider(icon_cache=None, catalogue=cat)
        assert provider.get_icon_path("^COOKER") == "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/COOKER.DDS"

    def test_caret_not_in_map_or_catalogue_returns_empty(self):
        cat = _make_catalogue_with_items({})
        provider = IconProvider(icon_cache=None, catalogue=cat)
        assert provider.get_icon_path("^NONEXISTENT_TECH") == ""


# ---------------------------------------------------------------------------
# R-ICON-04: Category 3 — Procedural suffix items (step 2)
# ---------------------------------------------------------------------------

class TestCategory3ProceduralSuffix:
    """R-ICON-04: Upgrade modules with #nnnnn seed suffix.

    Resolution step 2: split on #, try base_id in icon_map.
    Also covers ^ID#nnnnn combo (caret + procedural).
    """

    @pytest.fixture()
    def icon_map(self):
        return {
            "UP_BOLT4": "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.BOLT.DDS",
            "UP_LASER3": "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.LASER.DDS",
            "UP_HYP4": "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.YOURSHIP_HYPERDRIVE.DDS",
        }

    def test_procedural_bolt_upgrade(self, icon_map):
        provider = IconProvider(icon_cache=None, catalogue=None, icon_map=icon_map)
        assert provider.get_icon_path("UP_BOLT4#52847") == "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.BOLT.DDS"

    def test_procedural_laser_upgrade(self, icon_map):
        provider = IconProvider(icon_cache=None, catalogue=None, icon_map=icon_map)
        assert provider.get_icon_path("UP_LASER3#12345") == "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.LASER.DDS"

    def test_procedural_hyperdrive_upgrade(self, icon_map):
        provider = IconProvider(icon_cache=None, catalogue=None, icon_map=icon_map)
        assert provider.get_icon_path("UP_HYP4#99999") == "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.YOURSHIP_HYPERDRIVE.DDS"

    def test_caret_plus_procedural_resolves(self):
        """^UP_BOLT4#52847 → step 5 (upgrade prefix) → BOLT → icon_map.

        The ^+# combo doesn't resolve via step 2 (step 2 splits on # but keeps ^).
        It falls through to step 5 (upgrade prefix) which strips both ^ and #,
        resolves UP_BOLT→BOLT, then looks up BOLT in icon_map.
        """
        icon_map = {
            "UP_BOLT4": "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.BOLT.DDS",
            "BOLT": "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.BOLT.DDS",
        }
        provider = IconProvider(icon_cache=None, catalogue=None, icon_map=icon_map)
        assert provider.get_icon_path("^UP_BOLT4#52847") == "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.BOLT.DDS"

    def test_procedural_not_in_map_falls_to_catalogue(self):
        """UP_SCAN3#11111 not in icon_map, but catalogue has UP_SCAN3 → step 3."""
        cat = _make_catalogue_with_items({
            "UP_SCAN3": {"id": "UP_SCAN3", "icon": "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.SCAN.DDS"},
        })
        provider = IconProvider(icon_cache=None, catalogue=cat)
        assert provider.get_icon_path("UP_SCAN3#11111") == "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.SCAN.DDS"


# ---------------------------------------------------------------------------
# R-ICON-05: Category 4 — Catalogue-only items (step 3)
# ---------------------------------------------------------------------------

class TestCategory4CatalogueOnly:
    """R-ICON-05: Items not in icon_map but present in GameCatalogue.

    Resolution step 3: catalogue.find_item() returns item with "icon" key.
    """

    def test_catalogue_product_not_in_map(self):
        cat = _make_catalogue_with_items({
            "SENTINEL_LOOT": {"id": "SENTINEL_LOOT", "icon": "TEXTURES/UI/FRONTEND/ICONS/U4PRODUCTS/PRODUCT.SENTINELLOOT.DDS"},
        })
        provider = IconProvider(icon_cache=None, catalogue=cat)
        assert provider.get_icon_path("SENTINEL_LOOT") == "TEXTURES/UI/FRONTEND/ICONS/U4PRODUCTS/PRODUCT.SENTINELLOOT.DDS"

    def test_catalogue_substance_not_in_map(self):
        cat = _make_catalogue_with_items({
            "ASTEROID1": {"id": "ASTEROID1", "icon": "TEXTURES/UI/FRONTEND/ICONS/SUBSTANCES/SUBSTANCE.ASTEROID.1.DDS"},
        })
        provider = IconProvider(icon_cache=None, catalogue=cat)
        assert provider.get_icon_path("ASTEROID1") == "TEXTURES/UI/FRONTEND/ICONS/SUBSTANCES/SUBSTANCE.ASTEROID.1.DDS"

    def test_catalogue_tech_not_in_map(self):
        cat = _make_catalogue_with_items({
            "YOURFREIG_SCAN": {"id": "YOURFREIG_SCAN", "icon": "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.FREIGHTERSCAN.DDS"},
        })
        provider = IconProvider(icon_cache=None, catalogue=cat)
        assert provider.get_icon_path("YOURFREIG_SCAN") == "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.FREIGHTERSCAN.DDS"

    def test_catalogue_with_caret_prefix(self):
        """^BUILDSIGNAL: not in icon_map → catalogue has BUILDSIGNAL."""
        cat = _make_catalogue_with_items({
            "BUILDSIGNAL": {"id": "BUILDSIGNAL", "icon": "TEXTURES/UI/FRONTEND/ICONS/BASEBUILDING/BUILD.SIGNAL.DDS"},
        })
        provider = IconProvider(icon_cache=None, catalogue=cat)
        assert provider.get_icon_path("^BUILDSIGNAL") == "TEXTURES/UI/FRONTEND/ICONS/BASEBUILDING/BUILD.SIGNAL.DDS"

    def test_not_in_map_not_in_catalogue_returns_empty(self):
        cat = _make_catalogue_with_items({})
        provider = IconProvider(icon_cache=None, catalogue=cat)
        assert provider.get_icon_path("TOTALLY_UNKNOWN") == ""


# ---------------------------------------------------------------------------
# R-ICON-06: Category 5 — YOUR* special map (step 4)
# ---------------------------------------------------------------------------

class TestCategory5YourSpecialMap:
    """R-ICON-06: YOUR* IDs with special (irregular) mappings.

    Resolution step 4: _YOUR_SPECIAL_MAP lookup after icon_map/catalogue miss.
    The special map resolves YOUR* to a catalogue tech ID, then _lookup_resolved
    looks it up in icon_map or catalogue.
    """

    @pytest.fixture()
    def icon_map(self):
        """Icon map with the TARGET IDs (what special map resolves TO)."""
        return {
            "LAUNCHER": "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.YOURSHIP_LAUNCH.DDS",
            "SHIPJUMP1": "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.YOURSHIP_PULSEDRIVE.DDS",
            "SHIPGUN1": "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.YOURSHIP_PHOTON.DDS",
            "SHIPLAS1": "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.YOURSHIP_PHASE.DDS",
            "SHIPROCKETS": "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.YOURSHIP_ROCKET.DDS",
            "SHIPSHIELD": "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.YOURSHIP_SHIELD.DDS",
            "SHIPSHOTGUN": "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.YOURSHIP_SHOTGUN.DDS",
            "SHIPMINIGUN": "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.YOURSHIP_MINIGUN.DDS",
            "SHIPPLASMA": "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.YOURSHIP_PLASMA.DDS",
            "SHIP_TELEPORT": "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.YOURSHIP_TELEPORT.DDS",
            "PROTECT": "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.YOURSUIT_ARMOUR.DDS",
            "VEHICLEGUN": "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.YOURVEHIC_LASER.DDS",
            "VEHICLELAS": "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.YOURVEHIC_GUN.DDS",
            "VEHICLEBOOST": "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.YOURVEHIC_BOOST.DDS",
        }

    def test_yourship_launch(self, icon_map):
        provider = IconProvider(icon_cache=None, catalogue=None, icon_map=icon_map)
        assert provider.get_icon_path("YOURSHIP_LAUNCH") == "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.YOURSHIP_LAUNCH.DDS"

    def test_yourship_pulsedrive(self, icon_map):
        provider = IconProvider(icon_cache=None, catalogue=None, icon_map=icon_map)
        assert provider.get_icon_path("YOURSHIP_PULSEDRIVE") == "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.YOURSHIP_PULSEDRIVE.DDS"

    def test_yourship_photon(self, icon_map):
        provider = IconProvider(icon_cache=None, catalogue=None, icon_map=icon_map)
        assert provider.get_icon_path("YOURSHIP_PHOTON") == "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.YOURSHIP_PHOTON.DDS"

    def test_yourship_shield(self, icon_map):
        provider = IconProvider(icon_cache=None, catalogue=None, icon_map=icon_map)
        assert provider.get_icon_path("YOURSHIP_SHIELD") == "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.YOURSHIP_SHIELD.DDS"

    def test_yoursuit_shield(self, icon_map):
        provider = IconProvider(icon_cache=None, catalogue=None, icon_map=icon_map)
        assert provider.get_icon_path("YOURSUIT_SHIELD") == "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.YOURSUIT_ARMOUR.DDS"

    def test_yourfreig_launch(self, icon_map):
        provider = IconProvider(icon_cache=None, catalogue=None, icon_map=icon_map)
        assert provider.get_icon_path("YOURFREIG_LAUNCH") == "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.YOURSHIP_LAUNCH.DDS"

    def test_yourvehic_laser(self, icon_map):
        provider = IconProvider(icon_cache=None, catalogue=None, icon_map=icon_map)
        assert provider.get_icon_path("YOURVEHIC_LASER") == "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.YOURVEHIC_LASER.DDS"

    def test_yourvehic_gun(self, icon_map):
        provider = IconProvider(icon_cache=None, catalogue=None, icon_map=icon_map)
        assert provider.get_icon_path("YOURVEHIC_GUN") == "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.YOURVEHIC_GUN.DDS"

    def test_yourvehic_boost(self, icon_map):
        provider = IconProvider(icon_cache=None, catalogue=None, icon_map=icon_map)
        assert provider.get_icon_path("YOURVEHIC_BOOST") == "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.YOURVEHIC_BOOST.DDS"

    def test_caret_yourship_launch(self, icon_map):
        """^YOURSHIP_LAUNCH — stripped to YOURSHIP_LAUNCH, then special map."""
        provider = IconProvider(icon_cache=None, catalogue=None, icon_map=icon_map)
        assert provider.get_icon_path("^YOURSHIP_LAUNCH") == "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.YOURSHIP_LAUNCH.DDS"

    def test_all_special_map_entries_resolve(self, icon_map):
        """Every entry in _YOUR_SPECIAL_MAP should resolve when target is in icon_map."""
        from nmstoolkit.gui.widgets.icon_provider import _YOUR_SPECIAL_MAP
        provider = IconProvider(icon_cache=None, catalogue=None, icon_map=icon_map)
        for your_id, target_id in _YOUR_SPECIAL_MAP.items():
            result = provider.get_icon_path(your_id)
            assert result != "", f"{your_id} → {target_id} should resolve but got empty"


# ---------------------------------------------------------------------------
# R-ICON-07: Category 6 — YOUR* generic strip (step 4 generic path)
# ---------------------------------------------------------------------------

class TestCategory6YourGenericStrip:
    """R-ICON-07: YOUR* IDs NOT in special map — generic prefix strip.

    Step 4 generic path: strip YOURSHIP_/YOURSUIT_/etc., try base name,
    then base+"1" in catalogue and icon_map.
    """

    def test_yourship_hyperdrive_strips_to_hyperdrive(self):
        """YOURSHIP_HYPERDRIVE not in special map → strip YOURSHIP_ → HYPERDRIVE."""
        icon_map = {"HYPERDRIVE": "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.YOURSHIP_HYPERDRIVE.DDS"}
        provider = IconProvider(icon_cache=None, catalogue=None, icon_map=icon_map)
        assert provider.get_icon_path("YOURSHIP_HYPERDRIVE") == "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.YOURSHIP_HYPERDRIVE.DDS"

    def test_yoursuit_energy_strips_to_energy(self):
        """YOURSUIT_ENERGY → strip YOURSUIT_ → ENERGY."""
        icon_map = {"ENERGY": "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.ENERGY.DDS"}
        provider = IconProvider(icon_cache=None, catalogue=None, icon_map=icon_map)
        assert provider.get_icon_path("YOURSUIT_ENERGY") == "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.ENERGY.DDS"

    def test_yourmulti_scan_strips_and_tries_base_plus_1(self):
        """YOURMULTI_SCAN → strip YOURMULTI_ → SCAN not found → try SCAN1."""
        cat = _make_catalogue_with_items({
            "SCAN1": {"id": "SCAN1", "icon": "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.SCAN.DDS"},
        })
        provider = IconProvider(icon_cache=None, catalogue=cat)
        assert provider.get_icon_path("YOURMULTI_SCAN") == "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.SCAN.DDS"

    def test_yourfreig_engine_strips_to_engine(self):
        """YOURFREIG_ENGINE → strip YOURFREIG_ → ENGINE."""
        icon_map = {"ENGINE": "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.ENGINE.DDS"}
        provider = IconProvider(icon_cache=None, catalogue=None, icon_map=icon_map)
        assert provider.get_icon_path("YOURFREIG_ENGINE") == "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.ENGINE.DDS"

    def test_caret_yourship_hyperdrive(self):
        """^YOURSHIP_HYPERDRIVE → strip ^, then generic strip."""
        icon_map = {"HYPERDRIVE": "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.YOURSHIP_HYPERDRIVE.DDS"}
        provider = IconProvider(icon_cache=None, catalogue=None, icon_map=icon_map)
        assert provider.get_icon_path("^YOURSHIP_HYPERDRIVE") == "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.YOURSHIP_HYPERDRIVE.DDS"

    def test_generic_strip_returns_base_even_if_no_match(self):
        """When stripped base is not in icon_map or catalogue, still returns base (line 226)."""
        provider = IconProvider(icon_cache=None, catalogue=None)
        # YOURSHIP_UNKNOWNTECH → strip → UNKNOWNTECH → not found anywhere
        # _resolve_your_prefix returns "UNKNOWNTECH", then _lookup_resolved returns ""
        assert provider.get_icon_path("YOURSHIP_UNKNOWNTECH") == ""


# ---------------------------------------------------------------------------
# R-ICON-08: Category 7 — UP_/UA_/U_ upgrade prefix (step 5)
# ---------------------------------------------------------------------------

class TestCategory7UpgradePrefix:
    """R-ICON-08: Upgrade modules (UP_LASER4, UA_HYP3, U_BOLT2).

    Resolution step 5: longest-prefix match in _UPGRADE_PREFIX_MAP,
    then _lookup_resolved on the base tech ID.
    """

    @pytest.fixture()
    def icon_map(self):
        """Icon map with base tech IDs that upgrades resolve TO."""
        return {
            "LASER": "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.LASER.DDS",
            "SCAN1": "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.SCAN.DDS",
            "BOLT": "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.BOLT.DDS",
            "GRENADE": "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.GRENADE.DDS",
            "RAILGUN": "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.RAILGUN.DDS",
            "SHOTGUN": "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.SHOTGUN.DDS",
            "SMG": "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.SMG.DDS",
            "CANNON": "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.CANNON.DDS",
            "PROTECT": "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.YOURSUIT_ARMOUR.DDS",
            "ENERGY": "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.ENERGY.DDS",
            "JET1": "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.JET.DDS",
            "UT_HOT": "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.YOURSUIT_HEATARMOUR.DDS",
            "UT_COLD": "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.YOURSUIT_COLDARMOUR.DDS",
            "UT_TOX": "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.YOURSUIT_TOXARMOUR.DDS",
            "UT_RAD": "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.YOURSUIT_RADARMOUR.DDS",
            "PRESSURE_SUIT": "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.PRESSURESUIT.DDS",
            "SHIPJUMP1": "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.YOURSHIP_PULSEDRIVE.DDS",
            "LAUNCHER": "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.YOURSHIP_LAUNCH.DDS",
            "HYPERDRIVE": "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.YOURSHIP_HYPERDRIVE.DDS",
            "SHIPSHOTGUN": "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.YOURSHIP_SHOTGUN.DDS",
            "SHIPGUN1": "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.YOURSHIP_PHOTON.DDS",
            "SHIPLAS1": "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.YOURSHIP_PHASE.DDS",
            "SHIPROCKETS": "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.YOURSHIP_ROCKET.DDS",
            "SHIPSHIELD": "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.YOURSHIP_SHIELD.DDS",
            "SHIPMINIGUN": "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.YOURSHIP_MINIGUN.DDS",
            "SHIPPLASMA": "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.YOURSHIP_PLASMA.DDS",
            "SENGUN": "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.SENGUN.DDS",
            "YOURFREIG_LAUNCHER": "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.FREIGHTER_LAUNCH.DDS",
            "YOURFREIG_SCAN": "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.FREIGHTERSCAN.DDS",
        }

    def test_up_laser4(self, icon_map):
        provider = IconProvider(icon_cache=None, catalogue=None, icon_map=icon_map)
        assert provider.get_icon_path("UP_LASER4") == "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.LASER.DDS"

    def test_ua_laser2(self, icon_map):
        provider = IconProvider(icon_cache=None, catalogue=None, icon_map=icon_map)
        assert provider.get_icon_path("UA_LASER2") == "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.LASER.DDS"

    def test_up_scan1(self, icon_map):
        provider = IconProvider(icon_cache=None, catalogue=None, icon_map=icon_map)
        assert provider.get_icon_path("UP_SCAN1") == "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.SCAN.DDS"

    def test_up_bolt3(self, icon_map):
        provider = IconProvider(icon_cache=None, catalogue=None, icon_map=icon_map)
        assert provider.get_icon_path("UP_BOLT3") == "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.BOLT.DDS"

    def test_up_hyp4(self, icon_map):
        provider = IconProvider(icon_cache=None, catalogue=None, icon_map=icon_map)
        assert provider.get_icon_path("UP_HYP4") == "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.YOURSHIP_HYPERDRIVE.DDS"

    def test_ua_hyp3(self, icon_map):
        provider = IconProvider(icon_cache=None, catalogue=None, icon_map=icon_map)
        assert provider.get_icon_path("UA_HYP3") == "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.YOURSHIP_HYPERDRIVE.DDS"

    def test_up_hot2(self, icon_map):
        provider = IconProvider(icon_cache=None, catalogue=None, icon_map=icon_map)
        assert provider.get_icon_path("UP_HOT2") == "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.YOURSUIT_HEATARMOUR.DDS"

    def test_ua_pulse4(self, icon_map):
        provider = IconProvider(icon_cache=None, catalogue=None, icon_map=icon_map)
        assert provider.get_icon_path("UA_PULSE4") == "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.YOURSHIP_PULSEDRIVE.DDS"

    def test_ua_shield2(self, icon_map):
        provider = IconProvider(icon_cache=None, catalogue=None, icon_map=icon_map)
        assert provider.get_icon_path("UA_SHIELD2") == "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.YOURSHIP_SHIELD.DDS"

    def test_u_laser1(self, icon_map):
        """U_ prefix (legacy) also works."""
        provider = IconProvider(icon_cache=None, catalogue=None, icon_map=icon_map)
        assert provider.get_icon_path("U_LASER1") == "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.LASER.DDS"

    def test_caret_up_laser4(self, icon_map):
        """^UP_LASER4 — strip ^, then upgrade prefix resolution."""
        provider = IconProvider(icon_cache=None, catalogue=None, icon_map=icon_map)
        assert provider.get_icon_path("^UP_LASER4") == "TEXTURES/UI/FRONTEND/ICONS/TECHNOLOGY/RENDER.LASER.DDS"

    def test_all_upgrade_prefixes_resolve(self, icon_map):
        """Every entry in _UPGRADE_PREFIX_MAP should resolve when target is in icon_map."""
        from nmstoolkit.gui.widgets.icon_provider import _UPGRADE_PREFIX_MAP
        provider = IconProvider(icon_cache=None, catalogue=None, icon_map=icon_map)
        for prefix, target_id in _UPGRADE_PREFIX_MAP.items():
            test_id = f"{prefix}1"  # Add tier digit
            result = provider.get_icon_path(test_id)
            assert result != "", f"{test_id} → {target_id} should resolve but got empty (target in icon_map: {target_id in icon_map})"


# ---------------------------------------------------------------------------
# R-ICON-09: Category 8 — Corvette module prefix (step 6)
# ---------------------------------------------------------------------------

class TestCategory8CorvetteModule:
    """R-ICON-09: Corvette modules (B_COK_A, B_WNG_B).

    Resolution step 6: longest-prefix match in _CORVETTE_MODULE_MAP,
    then _lookup_resolved on the build part ID.
    """

    @pytest.fixture()
    def catalogue(self):
        """Catalogue with all corvette build target entries."""
        from nmstoolkit.gui.widgets.icon_provider import _CORVETTE_MODULE_MAP
        items = {}
        for target_id in set(_CORVETTE_MODULE_MAP.values()):
            items[target_id] = {"id": target_id, "icon": f"TEXTURES/UI/FRONTEND/ICONS/BUILDABLE/{target_id}.DDS"}
        return _make_catalogue_with_items(items)

    def test_cockpit_a(self, catalogue):
        provider = IconProvider(icon_cache=None, catalogue=catalogue)
        assert provider.get_icon_path("B_COK_A") == "TEXTURES/UI/FRONTEND/ICONS/BUILDABLE/BUILD_YOURSHIP_COCKPIT.DDS"

    def test_cockpit_b(self, catalogue):
        provider = IconProvider(icon_cache=None, catalogue=catalogue)
        assert provider.get_icon_path("B_COK_B") == "TEXTURES/UI/FRONTEND/ICONS/BUILDABLE/BUILD_YOURSHIP_COCKPIT.DDS"

    def test_wing_a(self, catalogue):
        provider = IconProvider(icon_cache=None, catalogue=catalogue)
        assert provider.get_icon_path("B_WNG_A") == "TEXTURES/UI/FRONTEND/ICONS/BUILDABLE/BUILD_YOURSHIP_WING.DDS"

    def test_thruster_c(self, catalogue):
        provider = IconProvider(icon_cache=None, catalogue=catalogue)
        assert provider.get_icon_path("B_TRU_C") == "TEXTURES/UI/FRONTEND/ICONS/BUILDABLE/BUILD_YOURSHIP_THRUSTER.DDS"

    def test_turret_a(self, catalogue):
        provider = IconProvider(icon_cache=None, catalogue=catalogue)
        assert provider.get_icon_path("B_TUR_A") == "TEXTURES/UI/FRONTEND/ICONS/BUILDABLE/BUILD_YOURSHIP_TURRET.DDS"

    def test_hab1_variant_longer_prefix(self, catalogue):
        """B_HAB1 has a longer prefix than B_HAB — longest-prefix match should pick B_HAB1."""
        provider = IconProvider(icon_cache=None, catalogue=catalogue)
        assert provider.get_icon_path("B_HAB1_A") == "TEXTURES/UI/FRONTEND/ICONS/BUILDABLE/BUILD_YOURSHIP_HAB.DDS"

    def test_caret_cockpit(self, catalogue):
        """^B_COK_A — strip ^, then corvette module resolution."""
        provider = IconProvider(icon_cache=None, catalogue=catalogue)
        assert provider.get_icon_path("^B_COK_A") == "TEXTURES/UI/FRONTEND/ICONS/BUILDABLE/BUILD_YOURSHIP_COCKPIT.DDS"

    def test_all_corvette_module_prefixes(self, catalogue):
        """Every entry in _CORVETTE_MODULE_MAP resolves with a _A suffix."""
        from nmstoolkit.gui.widgets.icon_provider import _CORVETTE_MODULE_MAP
        provider = IconProvider(icon_cache=None, catalogue=catalogue)
        for prefix, target_id in _CORVETTE_MODULE_MAP.items():
            test_id = f"{prefix}_A"
            result = provider.get_icon_path(test_id)
            assert result != "", f"{test_id} → {target_id} should resolve"
            assert target_id in result, f"{test_id} should resolve via {target_id}"


# ---------------------------------------------------------------------------
# R-ICON-10: Category 9 — Unknown/unmapped items
# ---------------------------------------------------------------------------

class TestCategory9UnknownUnmapped:
    """R-ICON-10: Items that don't match any resolution category.

    Must return empty string, not crash or return partial matches.
    """

    @pytest.fixture()
    def provider(self):
        """Provider with empty icon_map and empty catalogue."""
        cat = _make_catalogue_with_items({})
        return IconProvider(icon_cache=None, catalogue=cat)

    def test_nonsense_id_returns_empty(self, provider):
        assert provider.get_icon_path("XYZZY_NOTHING_12345") == ""

    def test_empty_string_returns_empty(self, provider):
        assert provider.get_icon_path("") == ""

    def test_just_caret_returns_empty(self, provider):
        assert provider.get_icon_path("^") == ""

    def test_just_hash_returns_empty(self, provider):
        assert provider.get_icon_path("#12345") == ""

    def test_unknown_your_prefix_returns_empty(self, provider):
        """YOURSHIP_ prefix but unrecognized suffix — returns empty."""
        assert provider.get_icon_path("YOURSHIP_NONEXISTENT") == ""

    def test_unknown_upgrade_prefix_returns_empty(self, provider):
        """UP_NONEXISTENT — doesn't match any upgrade prefix → empty."""
        assert provider.get_icon_path("UP_NONEXISTENT") == ""

    def test_unknown_corvette_returns_empty(self, provider):
        """B_NONEXISTENT — doesn't start with any corvette prefix → empty."""
        assert provider.get_icon_path("B_NONEXISTENT") == ""

    def test_partial_prefix_no_match(self, provider):
        """UP_ alone (no suffix) should not crash."""
        assert provider.get_icon_path("UP_") == ""
