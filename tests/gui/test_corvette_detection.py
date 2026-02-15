"""Tests for broadened corvette detection.

R-CORV-02: Corvettes detected by model filename OR by corvette module IDs in inventory.
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


def _ship_with_corvette_modules():
    """A ship with no BIGGS filename but with corvette module IDs."""
    return {
        "Resource": {"Filename": "MODELS/COMMON/SPACECRAFT/GENERIC/GENERIC.SCENE.MBIN"},
        "Inventory": {
            "Slots": [
                {"Id": "^B_COK_A", "Type": {"InventoryType": "Product"}},
                {"Id": "^B_WNG_A", "Type": {"InventoryType": "Product"}},
                {"Id": "^B_TRU_A", "Type": {"InventoryType": "Product"}},
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

    def test_corvette_modules_without_biggs(self, qapp):
        """Ship with corvette modules (B_COK, B_WNG, B_TRU) should be detected."""
        ship = _ship_with_corvette_modules()
        assert _is_corvette_ship(ship) is True

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
