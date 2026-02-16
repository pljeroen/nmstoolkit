"""Tests for slot editor item ID display.

R-SLOTEDIT-01: Slot editor shows raw item ID in a read-only label.
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QLabel

from nmstoolkit.gui.widgets.slot_editor import SlotEditor

_app = QApplication.instance() or QApplication([])


def _make_slot(item_id="FUEL1", inv_type="Substance", amount=100, max_amount=250):
    return {
        "Type": {"InventoryType": inv_type},
        "Id": item_id,
        "Amount": amount,
        "MaxAmount": max_amount,
        "DamageFactor": 0.0,
        "FullyInstalled": True,
        "Index": {"X": 0, "Y": 0},
    }


def _make_inventory():
    return {"Slots": [], "ValidSlotIndices": [], "SpecialSlots": [], "Width": 6, "Height": 5}


class TestSlotEditorItemId:
    """R-SLOTEDIT-01: Item ID label displayed in slot editor."""

    def test_item_id_label_exists(self):
        """Slot editor has a label showing the raw item ID."""
        slot = _make_slot("^FUEL1")
        inv = _make_inventory()
        editor = SlotEditor(slot, inv)
        assert hasattr(editor, "item_id_label")
        assert isinstance(editor.item_id_label, QLabel)

    def test_item_id_label_shows_current_id(self):
        """The label shows the current item's raw ID."""
        slot = _make_slot("^COOKER")
        inv = _make_inventory()
        editor = SlotEditor(slot, inv)
        assert "COOKER" in editor.item_id_label.text()

    def test_item_id_label_shows_corvette_id(self):
        """Corvette module IDs are shown."""
        slot = _make_slot("B_COK_A")
        inv = _make_inventory()
        editor = SlotEditor(slot, inv)
        assert "B_COK_A" in editor.item_id_label.text()

    def test_item_id_label_empty_slot(self):
        """Empty slots show empty or no ID."""
        slot = _make_slot("")
        inv = _make_inventory()
        editor = SlotEditor(slot, inv)
        # Label should exist but text should be empty or indicate no item
        assert editor.item_id_label.text() == ""
