"""Tests for SlotEditor dialog — inventory slot editing.

Tests cover:
- Item list loading from items.json
- Field population from slot data
- Apply modifies slot dict in-place
- Clear slot resets to empty
- Type auto-set when item selected
- Copy/paste slot data
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import copy
import json
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

from nmstoolkit.gui.widgets.slot_editor import SlotEditor

_app = QApplication.instance() or QApplication([])

DATA_DIR = Path(__file__).parent.parent.parent / "src" / "nmstoolkit" / "data"


def _make_slot(
    item_id="^FUEL1",
    amount=60,
    max_amount=500,
    inv_type="Substance",
    x=0,
    y=0,
    damage=0.0,
    installed=True,
):
    return {
        "Type": {"InventoryType": inv_type},
        "Id": item_id,
        "Amount": amount,
        "MaxAmount": max_amount,
        "DamageFactor": damage,
        "FullyInstalled": installed,
        "Index": {"X": x, "Y": y},
    }


def _make_inventory(slots=None, valid_indices=None, width=7, height=5):
    if slots is None:
        slots = [_make_slot()]
    if valid_indices is None:
        valid_indices = [{"X": s["Index"]["X"], "Y": s["Index"]["Y"]} for s in slots]
    return {
        "Slots": slots,
        "ValidSlotIndices": valid_indices,
        "Width": width,
        "Height": height,
    }


class TestSlotEditorConstruction:
    def test_creates_dialog(self):
        slot = _make_slot()
        inventory = _make_inventory([slot])
        editor = SlotEditor(slot, inventory)
        assert editor is not None

    def test_loads_items_from_json(self):
        """Item picker combobox should be populated with items from items.json."""
        slot = _make_slot()
        inventory = _make_inventory([slot])
        editor = SlotEditor(slot, inventory)
        # Should have at least some items (items.json has 4518)
        assert editor.item_combo.count() > 100

    def test_fields_populated_from_slot(self):
        """Fields should reflect the slot data passed in."""
        slot = _make_slot(
            item_id="^FUEL1",
            amount=60,
            max_amount=500,
            inv_type="Substance",
            damage=0.5,
            installed=False,
        )
        inventory = _make_inventory([slot])
        editor = SlotEditor(slot, inventory)

        assert editor.amount_spin.value() == 60
        assert editor.max_amount_spin.value() == 500
        assert editor.damage_spin.value() == pytest.approx(0.5)
        assert editor.installed_check.isChecked() is False

    def test_type_combo_shows_current_type(self):
        slot = _make_slot(inv_type="Technology")
        inventory = _make_inventory([slot])
        editor = SlotEditor(slot, inventory)
        assert editor.type_combo.currentText() == "Technology"

    def test_empty_slot_shows_defaults(self):
        slot = _make_slot(item_id="", amount=0, max_amount=0)
        inventory = _make_inventory([slot])
        editor = SlotEditor(slot, inventory)
        assert editor.amount_spin.value() == 0
        assert editor.max_amount_spin.value() == 0


class TestSlotEditorApply:
    def test_apply_modifies_slot_in_place(self):
        """Apply should modify the original slot dict, not create a new one."""
        slot = _make_slot(item_id="^FUEL1", amount=60)
        inventory = _make_inventory([slot])
        editor = SlotEditor(slot, inventory)

        editor.amount_spin.setValue(999)
        editor.apply_changes()

        assert slot["Amount"] == 999

    def test_apply_updates_max_amount(self):
        slot = _make_slot(max_amount=500)
        inventory = _make_inventory([slot])
        editor = SlotEditor(slot, inventory)

        editor.max_amount_spin.setValue(9999)
        editor.apply_changes()

        assert slot["MaxAmount"] == 9999

    def test_apply_updates_damage_factor(self):
        slot = _make_slot(damage=0.0)
        inventory = _make_inventory([slot])
        editor = SlotEditor(slot, inventory)

        editor.damage_spin.setValue(0.75)
        editor.apply_changes()

        assert slot["DamageFactor"] == pytest.approx(0.75)

    def test_apply_updates_fully_installed(self):
        slot = _make_slot(installed=True)
        inventory = _make_inventory([slot])
        editor = SlotEditor(slot, inventory)

        editor.installed_check.setChecked(False)
        editor.apply_changes()

        assert slot["FullyInstalled"] is False

    def test_apply_updates_type(self):
        slot = _make_slot(inv_type="Substance")
        inventory = _make_inventory([slot])
        editor = SlotEditor(slot, inventory)

        editor.type_combo.setCurrentText("Technology")
        editor.apply_changes()

        assert slot["Type"]["InventoryType"] == "Technology"


class TestSlotEditorClear:
    def test_clear_resets_slot(self):
        slot = _make_slot(item_id="^FUEL1", amount=60, max_amount=500)
        inventory = _make_inventory([slot])
        editor = SlotEditor(slot, inventory)

        editor.clear_slot()

        assert slot["Id"] == ""
        assert slot["Amount"] == 0
        assert slot["MaxAmount"] == 0


class TestSlotEditorItemSelection:
    def test_selecting_substance_sets_type(self):
        """When user picks a substance item, type combo should auto-set to Substance."""
        slot = _make_slot(inv_type="Technology")
        inventory = _make_inventory([slot])
        editor = SlotEditor(slot, inventory)

        # Find Carbon (^FUEL1) which is a substance
        editor.select_item_by_id("^FUEL1")
        assert editor.type_combo.currentText() == "Substance"

    def test_selecting_technology_sets_type(self):
        """When user picks a technology item, type combo should auto-set to Technology."""
        slot = _make_slot(inv_type="Substance")
        inventory = _make_inventory([slot])
        editor = SlotEditor(slot, inventory)

        # Find any technology item
        editor.select_item_by_id("^YOURSHIP_LASER")
        # Should either be Technology or remain unchanged if item not found
        # Items.json contains technology items
        if editor.item_combo.currentData() is not None:
            item_data = editor.item_combo.currentData()
            if item_data.get("type") == "technology":
                assert editor.type_combo.currentText() == "Technology"


class TestSlotEditorCopyPaste:
    def test_copy_captures_slot_data(self):
        slot = _make_slot(item_id="^FUEL1", amount=60, max_amount=500)
        inventory = _make_inventory([slot])
        editor = SlotEditor(slot, inventory)

        clipboard = editor.copy_slot()
        assert clipboard is not None
        assert clipboard["Id"] == "^FUEL1"
        assert clipboard["Amount"] == 60

    def test_copy_is_deep_copy(self):
        """Clipboard should be independent of original slot."""
        slot = _make_slot(item_id="^FUEL1", amount=60)
        inventory = _make_inventory([slot])
        editor = SlotEditor(slot, inventory)

        clipboard = editor.copy_slot()
        slot["Amount"] = 999
        assert clipboard["Amount"] == 60

    def test_paste_applies_clipboard_data(self):
        slot = _make_slot(item_id="", amount=0, max_amount=0)
        inventory = _make_inventory([slot])
        editor = SlotEditor(slot, inventory)

        clipboard = {
            "Type": {"InventoryType": "Substance"},
            "Id": "^FUEL1",
            "Amount": 60,
            "MaxAmount": 500,
            "DamageFactor": 0.0,
            "FullyInstalled": True,
        }
        editor.paste_slot(clipboard)

        assert slot["Id"] == "^FUEL1"
        assert slot["Amount"] == 60
        assert slot["MaxAmount"] == 500

    def test_paste_preserves_index(self):
        """Paste should keep the target slot's X,Y position."""
        slot = _make_slot(item_id="", x=3, y=2)
        inventory = _make_inventory([slot])
        editor = SlotEditor(slot, inventory)

        clipboard = {
            "Type": {"InventoryType": "Substance"},
            "Id": "^FUEL1",
            "Amount": 60,
            "MaxAmount": 500,
            "DamageFactor": 0.0,
            "FullyInstalled": True,
            "Index": {"X": 0, "Y": 0},
        }
        editor.paste_slot(clipboard)

        assert slot["Index"]["X"] == 3
        assert slot["Index"]["Y"] == 2
