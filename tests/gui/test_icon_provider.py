"""Tests for icon provider.

Tests R-IPROV-01 through R-IPROV-03.
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
