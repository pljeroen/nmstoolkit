"""Tests for icon provider.

Tests R-IPROV-01 through R-IPROV-03, R-ICO-01 through R-ICO-05.
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
