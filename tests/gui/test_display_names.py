"""Tests for locale resolution fallback in inventory_grid._get_item_name().

When catalogue.find_item() returns None but the item_id is a locale key,
_get_item_name() should resolve it via catalogue.locale before falling
through to items.json or raw ID.
"""

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from PySide6.QtWidgets import QApplication

from nmstoolkit.core.game_catalogue import GameCatalogue
from nmstoolkit.gui.widgets.inventory_grid import (
    _get_item_name,
    set_catalogue,
)

_app = QApplication.instance() or QApplication([])


@pytest.fixture
def catalogue_with_locale():
    """A catalogue with locale strings but no matching products/substances/technologies."""
    cat = GameCatalogue(
        products=[{"id": "FUEL1", "name": "Carbon", "display_name": "Carbon"}],
        substances=[],
        technologies=[],
        locale={
            "UI_SEASON_19_NAME": "Corvette",
            "UI_SEASON_21_NAME": "Remnant",
            "YOURSUIT_BUBBLE_NAME": "Bubble Cluster",
            "FREI_SCRAP_NAME": "Salvaged Scrap",
        },
    )
    return cat


@pytest.fixture(autouse=True)
def _reset_catalogue():
    """Reset catalogue state after each test."""
    yield
    set_catalogue(None)


class TestLocaleResolutionFallback:
    def test_known_product_still_resolves(self, catalogue_with_locale):
        set_catalogue(catalogue_with_locale)
        assert _get_item_name("FUEL1") == "Carbon"

    def test_locale_key_with_caret_resolves(self, catalogue_with_locale):
        """Item IDs like ^UI_SEASON_19_NAME should resolve via locale."""
        set_catalogue(catalogue_with_locale)
        result = _get_item_name("^UI_SEASON_19_NAME")
        assert result == "Corvette"

    def test_locale_key_without_caret_resolves(self, catalogue_with_locale):
        """Bare locale keys should also resolve."""
        set_catalogue(catalogue_with_locale)
        result = _get_item_name("UI_SEASON_21_NAME")
        assert result == "Remnant"

    def test_unknown_id_returns_stripped(self, catalogue_with_locale):
        """IDs not in catalogue or locale fall through to stripped raw ID."""
        set_catalogue(catalogue_with_locale)
        result = _get_item_name("^COMPLETELY_UNKNOWN")
        assert result == "COMPLETELY_UNKNOWN"

    def test_no_catalogue_falls_through(self):
        """Without a catalogue, locale resolution is skipped."""
        set_catalogue(None)
        result = _get_item_name("^UI_SEASON_19_NAME")
        # Should fall through to items.json or raw ID strip
        assert result == "UI_SEASON_19_NAME"

    def test_locale_key_preferred_over_raw_strip(self, catalogue_with_locale):
        """Locale resolution should happen before raw ID stripping."""
        set_catalogue(catalogue_with_locale)
        result = _get_item_name("^YOURSUIT_BUBBLE_NAME")
        assert result == "Bubble Cluster"
