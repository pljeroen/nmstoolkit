"""Tests for corvette detection.

R-CORV-02: Corvettes detected by BIGGS model filename (authoritative),
with conservative module-based fallback when filename is absent.
"""

import pytest
from PySide6.QtWidgets import QApplication

from nmstoolkit.gui.tabs.corvette_tab import _is_corvette_ship


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _ship_with_filename(filename):
    return {
        "Resource": {"Filename": filename},
        "Inventory": {"Slots": []},
    }


def _ship_with_corvette_modules(filename=""):
    """A ship with corvette module IDs and optional filename."""
    return {
        "Resource": {"Filename": filename},
        "Inventory": {
            "Slots": [
                {"Id": "^B_COK_A", "Type": {"InventoryType": "Technology"}},
                {"Id": "^B_WNG_A", "Type": {"InventoryType": "Technology"}},
                {"Id": "^B_STR_A", "Type": {"InventoryType": "Technology"}},
            ],
        },
    }


class TestCorvetteDetection:
    def test_biggs_filename_detected(self, qapp):
        """Classic BIGGS model path is still detected."""
        ship = _ship_with_filename("MODELS/COMMON/SPACECRAFT/BIGGS/BIGGS.SCENE.MBIN")
        assert _is_corvette_ship(ship) is True

    def test_biggs_case_insensitive(self, qapp):
        ship = _ship_with_filename("models/common/spacecraft/biggs/biggs.scene.mbin")
        assert _is_corvette_ship(ship) is True

    def test_non_corvette_ship(self, qapp):
        ship = _ship_with_filename("MODELS/COMMON/SPACECRAFT/FIGHTERS/FIGHTER_PROC.SCENE.MBIN")
        assert _is_corvette_ship(ship) is False

    def test_corvette_modules_without_filename(self, qapp):
        """Fallback: ship with empty filename but 3+ corvette modules (cockpit + structural) is detected."""
        ship = _ship_with_corvette_modules()
        assert _is_corvette_ship(ship) is True

    def test_corvette_modules_with_non_biggs_filename_rejected(self, qapp):
        """Non-BIGGS filename takes precedence — module fallback does not apply."""
        ship = _ship_with_corvette_modules(filename="MODELS/COMMON/SPACECRAFT/GENERIC/GENERIC.SCENE.MBIN")
        assert _is_corvette_ship(ship) is False

    def test_ship_without_resource_field(self, qapp):
        """Ship missing Resource field should not crash."""
        ship = {"Inventory": {"Slots": []}}
        assert _is_corvette_ship(ship) is False

    def test_non_corvette_with_regular_modules(self, qapp):
        """Regular ship modules (not B_ prefixed) should not trigger detection."""
        ship = {
            "Resource": {"Filename": "FIGHTER_PROC.SCENE.MBIN"},
            "Inventory": {
                "Slots": [
                    {"Id": "^YOURSHIP_LAUNCH", "Type": {"InventoryType": "Technology"}},
                    {"Id": "^HYPERDRIVE", "Type": {"InventoryType": "Technology"}},
                ],
            },
        }
        assert _is_corvette_ship(ship) is False
