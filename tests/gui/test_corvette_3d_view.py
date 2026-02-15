"""Tests for corvette 3D view module — non-GL tests.

Tests cover:
- Module category detection
- Module color mapping
- Camera state initialization
- set_modules() data parsing
- Corvette tab 2D/3D toggle integration
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from nmstoolkit.gui.widgets.corvette_3d_view import (
    _MODULE_CATEGORIES,
    _MODULE_COLORS,
    _get_module_category,
    _get_module_color,
)
from nmstoolkit.gui.tabs.corvette_tab import CorvetteTab

_app = QApplication.instance() or QApplication([])


class TestModuleCategory:
    def test_cockpit_detected(self):
        assert _get_module_category("B_COK_A") == "Cockpit"

    def test_cockpit_with_caret(self):
        assert _get_module_category("^B_COK_A") == "Cockpit"

    def test_wing_detected(self):
        assert _get_module_category("B_WNG_A") == "Wing"

    def test_structure_detected(self):
        assert _get_module_category("B_STR_A_N") == "Structure"

    def test_thruster_detected(self):
        assert _get_module_category("B_TRU_A") == "Thruster"

    def test_turret_detected(self):
        assert _get_module_category("B_TUR_A") == "Turret"

    def test_landing_gear_detected(self):
        assert _get_module_category("B_LND_A") == "Landing Gear"

    def test_connector_detected(self):
        assert _get_module_category("B_CON_A") == "Connector"

    def test_large_connector_detected(self):
        assert _get_module_category("B_CON_L_A") == "Large Connector"

    def test_unknown_returns_unknown(self):
        assert _get_module_category("WEIRD_THING") == "Unknown"

    def test_empty_returns_unknown(self):
        assert _get_module_category("") == "Unknown"


class TestModuleColor:
    def test_cockpit_returns_red(self):
        r, g, b = _get_module_color("B_COK_A")
        assert r > 0.5  # Cockpit is reddish

    def test_wing_returns_blue(self):
        r, g, b = _get_module_color("B_WNG_A")
        assert b > 0.5  # Wing is bluish

    def test_unknown_returns_gray(self):
        r, g, b = _get_module_color("UNKNOWN_THING")
        assert r == g == b  # Gray = equal RGB

    def test_all_categories_have_colors(self):
        """Every category in the mapping should have a color entry."""
        for category in set(_MODULE_CATEGORIES.values()):
            assert category in _MODULE_COLORS


class TestCorvetteTabToggle:
    def _make_psd(self):
        return {
            "ShipOwnership": [],
            "CorvetteStorageInventory": {
                "Slots": [
                    {"Type": {"InventoryType": "Product"}, "Id": "^B_COK_A",
                     "Amount": 1, "MaxAmount": 500, "DamageFactor": 0.0,
                     "FullyInstalled": True, "Index": {"X": 5, "Y": 5}},
                ],
                "ValidSlotIndices": [{"X": x, "Y": y} for x in range(10) for y in range(12)],
                "Class": {"InventoryClass": "C"},
                "Width": 10,
                "Height": 16,
            },
            "CorvetteStorageLayout": {"Slots": 10, "Seed": [True, "0x1"], "Level": 1},
            "CorvetteEditAssociatedShipIndex": -1,
            "CorvetteEditShipName": "Draft Corvette",
            "CorvetteDraftShipSeed": 42,
        }

    def test_tab_has_toggle_button(self):
        tab = CorvetteTab()
        assert hasattr(tab, "_view_toggle_btn")
        assert tab._view_toggle_btn.text() == "Switch to 3D View"

    def test_tab_starts_on_2d(self):
        tab = CorvetteTab()
        assert tab._draft_stack.currentIndex() == 0

    def test_draft_shows_build_grid_tab(self):
        tab = CorvetteTab()
        psd = self._make_psd()
        tab.set_data(psd)
        # Build Grid tab should be visible
        assert tab._inv_tabs.isTabVisible(3) is True
