"""Tests for ExosuitTab GUI widget.

R-CURR-01: Units currency supports unsigned 32-bit range (0 to 4,294,967,295).
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from nmstoolkit.gui.tabs.exosuit_tab import ExosuitTab

_app = QApplication.instance() or QApplication([])


def _make_psd(units=0, nanites=0, specials=0):
    return {
        "Units": units,
        "Nanites": nanites,
        "Specials": specials,
        "Health": 100,
        "Shield": 50,
        "Energy": 50,
        "Inventory": {},
        "Inventory_TechOnly": {},
        "Inventory_Cargo": {},
    }


class TestUnitsCurrencyOverflow:
    """R-CURR-01: Units supports unsigned 32-bit range."""

    def test_negative_value_treated_as_unsigned(self):
        """Negative units in save file displayed as unsigned equivalent."""
        tab = ExosuitTab()
        # -1 in signed int32 = 4,294,967,295 in unsigned
        psd = _make_psd(units=-1)
        tab.set_data(psd)
        assert tab._units.text() == "4294967295"

    def test_large_negative_treated_as_unsigned(self):
        """Large negative value converted correctly."""
        tab = ExosuitTab()
        # -2,000,000,000 + 2^32 = 2,294,967,296
        psd = _make_psd(units=-2_000_000_000)
        tab.set_data(psd)
        assert tab._units.text() == "2294967296"

    def test_positive_value_displayed_normally(self):
        """Positive units displayed as-is."""
        tab = ExosuitTab()
        psd = _make_psd(units=1_000_000)
        tab.set_data(psd)
        assert tab._units.text() == "1000000"

    def test_zero_displayed(self):
        tab = ExosuitTab()
        psd = _make_psd(units=0)
        tab.set_data(psd)
        assert tab._units.text() == "0"

    def test_max_unsigned_value_accepted(self):
        """4,294,967,295 is the maximum valid value."""
        tab = ExosuitTab()
        psd = _make_psd(units=4_294_967_295)
        tab.set_data(psd)
        assert tab._units.text() == "4294967295"


class TestUnitsCurrencyWriteback:
    """R-CURR-01: Units write-back stores correct value."""

    def test_writeback_stores_value(self):
        tab = ExosuitTab()
        psd = _make_psd(units=100)
        tab.set_data(psd)
        tab._units.setText("999999")
        # Trigger editingFinished or textChanged to write back
        tab._units.editingFinished.emit()
        assert psd["Units"] == 999999

    def test_writeback_large_value(self):
        tab = ExosuitTab()
        psd = _make_psd(units=0)
        tab.set_data(psd)
        tab._units.setText("4294967295")
        tab._units.editingFinished.emit()
        assert psd["Units"] == 4294967295

    def test_nanites_still_work(self):
        """Nanites and Quicksilver unchanged — still QSpinBox."""
        tab = ExosuitTab()
        psd = _make_psd(nanites=500, specials=200)
        tab.set_data(psd)
        assert tab._nanites.value() == 500
        assert tab._quicksilver.value() == 200
