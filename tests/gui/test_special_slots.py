"""Tests for special (supercharged) slot rendering and editing.

Tests cover:
- Special slot detection from SpecialSlots array
- Gold L-border styling on special slots
- Toggle supercharged via InventoryGrid.toggle_special()
- Supercharged checkbox in SlotEditor
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from nmstoolkit.gui.widgets.inventory_grid import (
    InventoryGrid,
    SlotWidget,
    _SPECIAL_BORDER,
    _make_slot_style,
)
from nmstoolkit.gui.widgets.slot_editor import SlotEditor

_app = QApplication.instance() or QApplication([])


def _make_slot(item_id="^FUEL1", amount=60, max_amount=500, inv_type="Substance", x=0, y=0):
    return {
        "Type": {"InventoryType": inv_type},
        "Id": item_id,
        "Amount": amount,
        "MaxAmount": max_amount,
        "DamageFactor": 0.0,
        "FullyInstalled": True,
        "Index": {"X": x, "Y": y},
    }


def _make_inventory(slots=None, valid_indices=None, width=3, height=2, special_slots=None):
    if slots is None:
        slots = [_make_slot(x=0, y=0)]
    if valid_indices is None:
        valid_indices = [{"X": s["Index"]["X"], "Y": s["Index"]["Y"]} for s in slots]
    inv = {
        "Slots": slots,
        "ValidSlotIndices": valid_indices,
        "Width": width,
        "Height": height,
        "SpecialSlots": special_slots or [],
    }
    return inv


class TestSpecialSlotRendering:
    def test_special_slot_widget_has_special_flag(self):
        """SlotWidget created for a special position should have _special=True."""
        inventory = _make_inventory(
            slots=[_make_slot(x=0, y=0, inv_type="Technology")],
            valid_indices=[{"X": 0, "Y": 0}, {"X": 1, "Y": 0}],
            width=2,
            height=1,
            special_slots=[
                {"Type": {"InventorySpecialSlotType": "TechBonus"}, "Index": {"X": 0, "Y": 0}},
            ],
        )
        grid = InventoryGrid("Test")
        grid.set_inventory(inventory)

        w0 = grid.get_slot_widget(0, 0)
        w1 = grid.get_slot_widget(1, 0)
        assert w0._special is True
        assert w1._special is False

    def test_special_slot_style_contains_gold_border(self):
        """Style for special slots should use a full gold border."""
        style = _make_slot_style("#2d3a5a", "#48a", special=True)
        assert f"border: 3px solid {_SPECIAL_BORDER}" in style
        assert "border: 1px solid #48a" not in style

    def test_non_special_slot_style_no_gold(self):
        """Style for normal slots should NOT contain gold border."""
        style = _make_slot_style("#2d3a5a", "#48a", special=False)
        assert _SPECIAL_BORDER not in style

    def test_multiple_special_slots_detected(self):
        """Multiple SpecialSlots entries should all be detected."""
        slots = [
            _make_slot(x=0, y=0, inv_type="Technology"),
            _make_slot(x=1, y=0, inv_type="Technology"),
            _make_slot(x=2, y=0, inv_type="Technology"),
        ]
        inventory = _make_inventory(
            slots=slots,
            valid_indices=[{"X": 0, "Y": 0}, {"X": 1, "Y": 0}, {"X": 2, "Y": 0}],
            width=3,
            height=1,
            special_slots=[
                {"Type": {"InventorySpecialSlotType": "TechBonus"}, "Index": {"X": 0, "Y": 0}},
                {"Type": {"InventorySpecialSlotType": "TechBonus"}, "Index": {"X": 2, "Y": 0}},
            ],
        )
        grid = InventoryGrid("Test")
        grid.set_inventory(inventory)

        assert grid.get_slot_widget(0, 0)._special is True
        assert grid.get_slot_widget(1, 0)._special is False
        assert grid.get_slot_widget(2, 0)._special is True

    def test_only_techbonus_slots_marked_special(self):
        """Only InventorySpecialSlotType=TechBonus should render as special."""
        inventory = _make_inventory(
            slots=[_make_slot(x=0, y=0, inv_type="Technology")],
            valid_indices=[{"X": 0, "Y": 0}],
            width=1,
            height=1,
            special_slots=[
                {"Type": {"InventorySpecialSlotType": "CargoBonus"}, "Index": {"X": 0, "Y": 0}},
            ],
        )
        grid = InventoryGrid("Test")
        grid.set_inventory(inventory)

        assert grid.get_slot_widget(0, 0)._special is False


class TestToggleSpecial:
    def test_toggle_adds_special(self):
        """Toggling a non-special slot should add it to SpecialSlots."""
        inventory = _make_inventory(
            slots=[_make_slot(x=0, y=0)],
            valid_indices=[{"X": 0, "Y": 0}],
            width=1,
            height=1,
        )
        grid = InventoryGrid("Test")
        grid.set_inventory(inventory)

        grid.toggle_special(0, 0)

        assert len(inventory["SpecialSlots"]) == 1
        entry = inventory["SpecialSlots"][0]
        assert entry["Index"]["X"] == 0
        assert entry["Index"]["Y"] == 0
        assert entry["Type"]["InventorySpecialSlotType"] == "TechBonus"

    def test_toggle_removes_special(self):
        """Toggling a special slot should remove it from SpecialSlots."""
        inventory = _make_inventory(
            slots=[_make_slot(x=0, y=0)],
            valid_indices=[{"X": 0, "Y": 0}],
            width=1,
            height=1,
            special_slots=[
                {"Type": {"InventorySpecialSlotType": "TechBonus"}, "Index": {"X": 0, "Y": 0}},
            ],
        )
        grid = InventoryGrid("Test")
        grid.set_inventory(inventory)

        grid.toggle_special(0, 0)

        assert len(inventory["SpecialSlots"]) == 0

    def test_toggle_updates_widget_flag(self):
        """After toggle, the widget's _special flag should update."""
        inventory = _make_inventory(
            slots=[_make_slot(x=0, y=0)],
            valid_indices=[{"X": 0, "Y": 0}],
            width=1,
            height=1,
        )
        grid = InventoryGrid("Test")
        grid.set_inventory(inventory)

        w = grid.get_slot_widget(0, 0)
        assert w._special is False

        grid.toggle_special(0, 0)
        assert w._special is True

        grid.toggle_special(0, 0)
        assert w._special is False

    def test_toggle_preserves_other_specials(self):
        """Toggling one slot should not affect other special slots."""
        inventory = _make_inventory(
            slots=[_make_slot(x=0, y=0), _make_slot(x=1, y=0)],
            valid_indices=[{"X": 0, "Y": 0}, {"X": 1, "Y": 0}],
            width=2,
            height=1,
            special_slots=[
                {"Type": {"InventorySpecialSlotType": "TechBonus"}, "Index": {"X": 0, "Y": 0}},
                {"Type": {"InventorySpecialSlotType": "TechBonus"}, "Index": {"X": 1, "Y": 0}},
            ],
        )
        grid = InventoryGrid("Test")
        grid.set_inventory(inventory)

        grid.toggle_special(0, 0)

        assert len(inventory["SpecialSlots"]) == 1
        assert inventory["SpecialSlots"][0]["Index"]["X"] == 1


class TestSlotEditorSupercharged:
    def test_checkbox_checked_for_special_slot(self):
        """Supercharged checkbox should be checked when slot is in SpecialSlots."""
        slot = _make_slot(x=0, y=0)
        inventory = _make_inventory(
            slots=[slot],
            special_slots=[
                {"Type": {"InventorySpecialSlotType": "TechBonus"}, "Index": {"X": 0, "Y": 0}},
            ],
        )
        editor = SlotEditor(slot, inventory)
        assert editor.supercharged_check.isChecked() is True

    def test_checkbox_unchecked_for_normal_slot(self):
        """Supercharged checkbox should be unchecked for normal slots."""
        slot = _make_slot(x=0, y=0)
        inventory = _make_inventory(slots=[slot])
        editor = SlotEditor(slot, inventory)
        assert editor.supercharged_check.isChecked() is False

    def test_apply_adds_special_slot(self):
        """Checking supercharged and applying should add to SpecialSlots."""
        slot = _make_slot(x=0, y=0)
        inventory = _make_inventory(slots=[slot])
        editor = SlotEditor(slot, inventory)

        editor.supercharged_check.setChecked(True)
        editor.apply_changes()

        assert len(inventory["SpecialSlots"]) == 1
        assert inventory["SpecialSlots"][0]["Index"]["X"] == 0

    def test_apply_removes_special_slot(self):
        """Unchecking supercharged and applying should remove from SpecialSlots."""
        slot = _make_slot(x=0, y=0)
        inventory = _make_inventory(
            slots=[slot],
            special_slots=[
                {"Type": {"InventorySpecialSlotType": "TechBonus"}, "Index": {"X": 0, "Y": 0}},
            ],
        )
        editor = SlotEditor(slot, inventory)

        editor.supercharged_check.setChecked(False)
        editor.apply_changes()

        assert len(inventory["SpecialSlots"]) == 0
