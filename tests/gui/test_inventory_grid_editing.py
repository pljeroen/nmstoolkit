"""Tests for InventoryGrid editing enhancements.

Tests cover:
- Locked/unlocked slot visual distinction via ValidSlotIndices
- Full Width×Height grid rendering (not just Slots entries)
- Context menu actions: copy, paste, clear, enable, disable, max stack
- Copy/paste clipboard module-level state
- Type-colored placeholder icon rendering
- Item symbol lookup from items.json
- Drag-and-drop: swap (move) and copy slot operations
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import copy

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QApplication

from nmstoolkit.gui.widgets.inventory_grid import (
    InventoryGrid,
    SlotWidget,
    _CLIPBOARD_SLOT,
    set_clipboard_slot,
    get_clipboard_slot,
    _get_item_symbol,
    _get_type_colors,
    _create_placeholder_pixmap,
)

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


def _make_inventory(slots=None, valid_indices=None, width=3, height=2):
    """Create a small test inventory."""
    if slots is None:
        slots = [_make_slot(x=0, y=0)]
    if valid_indices is None:
        valid_indices = [{"X": s["Index"]["X"], "Y": s["Index"]["Y"]} for s in slots]
    return {
        "Slots": slots,
        "ValidSlotIndices": valid_indices,
        "Width": width,
        "Height": height,
    }


class TestLockedUnlockedRendering:
    def test_full_grid_rendered(self):
        """Grid should render Width×Height slots, not just Slots entries."""
        inventory = _make_inventory(
            slots=[_make_slot(x=0, y=0)],
            valid_indices=[{"X": 0, "Y": 0}],
            width=3,
            height=2,
        )
        grid = InventoryGrid("Test")
        grid.set_inventory(inventory)

        # Should have 3×2 = 6 slot widgets
        assert len(grid._slot_widgets) == 6

    def test_unlocked_slot_with_item_is_active(self):
        """Slot in ValidSlotIndices with an item should be styled as active."""
        inventory = _make_inventory(
            slots=[_make_slot(x=0, y=0, item_id="^FUEL1")],
            valid_indices=[{"X": 0, "Y": 0}],
            width=2,
            height=1,
        )
        grid = InventoryGrid("Test")
        grid.set_inventory(inventory)

        w = grid.get_slot_widget(0, 0)
        assert w is not None
        assert w.is_locked is False

    def test_locked_slot_is_dimmed(self):
        """Slot NOT in ValidSlotIndices should be marked as locked."""
        inventory = _make_inventory(
            slots=[_make_slot(x=0, y=0)],
            valid_indices=[{"X": 0, "Y": 0}],  # only (0,0) is valid
            width=2,
            height=1,
        )
        grid = InventoryGrid("Test")
        grid.set_inventory(inventory)

        # (1,0) is NOT in ValidSlotIndices
        w = grid.get_slot_widget(1, 0)
        assert w is not None
        assert w.is_locked is True

    def test_unlocked_empty_slot_is_not_locked(self):
        """Slot in ValidSlotIndices but without item data should still be unlocked."""
        inventory = _make_inventory(
            slots=[],
            valid_indices=[{"X": 0, "Y": 0}, {"X": 1, "Y": 0}],
            width=2,
            height=1,
        )
        grid = InventoryGrid("Test")
        grid.set_inventory(inventory)

        w = grid.get_slot_widget(0, 0)
        assert w.is_locked is False

    def test_all_slots_locked_when_no_valid_indices(self):
        """With empty ValidSlotIndices, all slots should be locked."""
        inventory = _make_inventory(
            slots=[],
            valid_indices=[],
            width=2,
            height=2,
        )
        grid = InventoryGrid("Test")
        grid.set_inventory(inventory)

        for x in range(2):
            for y in range(2):
                w = grid.get_slot_widget(x, y)
                assert w.is_locked is True


class TestContextMenuActions:
    def test_clear_slot_resets_item(self):
        """Clear slot should set Id to empty and Amount to 0."""
        slot = _make_slot(x=0, y=0, item_id="^FUEL1", amount=60)
        inventory = _make_inventory(
            slots=[slot],
            valid_indices=[{"X": 0, "Y": 0}],
            width=1,
            height=1,
        )
        grid = InventoryGrid("Test")
        grid.set_inventory(inventory)

        grid.clear_slot(0, 0)

        assert slot["Id"] == ""
        assert slot["Amount"] == 0

    def test_max_stack_sets_amount_to_max(self):
        """Max Stack should set Amount = MaxAmount."""
        slot = _make_slot(x=0, y=0, amount=60, max_amount=500)
        inventory = _make_inventory(slots=[slot])
        grid = InventoryGrid("Test")
        grid.set_inventory(inventory)

        grid.max_stack(0, 0)

        assert slot["Amount"] == 500

    def test_enable_slot_adds_to_valid_indices(self):
        """Enable slot should add position to ValidSlotIndices."""
        inventory = _make_inventory(
            slots=[],
            valid_indices=[],
            width=2,
            height=1,
        )
        grid = InventoryGrid("Test")
        grid.set_inventory(inventory)

        grid.enable_slot(1, 0)

        assert {"X": 1, "Y": 0} in inventory["ValidSlotIndices"]
        w = grid.get_slot_widget(1, 0)
        assert w.is_locked is False

    def test_disable_slot_removes_from_valid_indices(self):
        """Disable slot should remove position from ValidSlotIndices."""
        slot = _make_slot(x=0, y=0, item_id="^FUEL1")
        inventory = _make_inventory(
            slots=[slot],
            valid_indices=[{"X": 0, "Y": 0}],
            width=2,
            height=1,
        )
        grid = InventoryGrid("Test")
        grid.set_inventory(inventory)

        grid.disable_slot(0, 0)

        assert {"X": 0, "Y": 0} not in inventory["ValidSlotIndices"]
        w = grid.get_slot_widget(0, 0)
        assert w.is_locked is True

    def test_disable_slot_removes_slot_entry(self):
        """Disabling a slot should also remove its Slots entry."""
        slot = _make_slot(x=0, y=0, item_id="^FUEL1")
        inventory = _make_inventory(
            slots=[slot],
            valid_indices=[{"X": 0, "Y": 0}],
            width=2,
            height=1,
        )
        grid = InventoryGrid("Test")
        grid.set_inventory(inventory)

        grid.disable_slot(0, 0)

        matching = [s for s in inventory["Slots"] if s["Index"]["X"] == 0 and s["Index"]["Y"] == 0]
        assert len(matching) == 0

    def test_enable_slot_creates_empty_slot_entry(self):
        """Enabling a slot should create an empty Slots entry."""
        inventory = _make_inventory(
            slots=[],
            valid_indices=[],
            width=2,
            height=1,
        )
        grid = InventoryGrid("Test")
        grid.set_inventory(inventory)

        grid.enable_slot(0, 0)

        matching = [s for s in inventory["Slots"] if s["Index"]["X"] == 0 and s["Index"]["Y"] == 0]
        assert len(matching) == 1
        assert matching[0]["Id"] == ""
        assert matching[0]["Amount"] == 0

    def test_enable_all_slots(self):
        """Enable All Slots should make every grid position valid."""
        inventory = _make_inventory(
            slots=[],
            valid_indices=[],
            width=2,
            height=2,
        )
        grid = InventoryGrid("Test")
        grid.set_inventory(inventory)

        grid.enable_all_slots()

        assert len(inventory["ValidSlotIndices"]) == 4
        for x in range(2):
            for y in range(2):
                assert {"X": x, "Y": y} in inventory["ValidSlotIndices"]


class TestClipboard:
    def test_copy_slot_stores_in_clipboard(self):
        slot = _make_slot(x=0, y=0, item_id="^FUEL1", amount=60)
        inventory = _make_inventory(slots=[slot])
        grid = InventoryGrid("Test")
        grid.set_inventory(inventory)

        grid.copy_slot(0, 0)

        cb = get_clipboard_slot()
        assert cb is not None
        assert cb["Id"] == "^FUEL1"
        assert cb["Amount"] == 60

    def test_copy_is_deep(self):
        """Clipboard should be independent of original."""
        slot = _make_slot(x=0, y=0, item_id="^FUEL1", amount=60)
        inventory = _make_inventory(slots=[slot])
        grid = InventoryGrid("Test")
        grid.set_inventory(inventory)

        grid.copy_slot(0, 0)
        slot["Amount"] = 999

        cb = get_clipboard_slot()
        assert cb["Amount"] == 60

    def test_paste_slot_applies_clipboard(self):
        src = _make_slot(x=0, y=0, item_id="^FUEL1", amount=60, max_amount=500)
        dst = _make_slot(x=1, y=0, item_id="", amount=0, max_amount=0)
        inventory = _make_inventory(
            slots=[src, dst],
            valid_indices=[{"X": 0, "Y": 0}, {"X": 1, "Y": 0}],
            width=2,
            height=1,
        )
        grid = InventoryGrid("Test")
        grid.set_inventory(inventory)

        grid.copy_slot(0, 0)
        grid.paste_slot(1, 0)

        assert dst["Id"] == "^FUEL1"
        assert dst["Amount"] == 60
        assert dst["MaxAmount"] == 500

    def test_paste_preserves_target_index(self):
        """Paste should keep the target slot's X,Y."""
        src = _make_slot(x=0, y=0, item_id="^FUEL1", amount=60)
        dst = _make_slot(x=1, y=0, item_id="", amount=0)
        inventory = _make_inventory(
            slots=[src, dst],
            valid_indices=[{"X": 0, "Y": 0}, {"X": 1, "Y": 0}],
            width=2,
            height=1,
        )
        grid = InventoryGrid("Test")
        grid.set_inventory(inventory)

        grid.copy_slot(0, 0)
        grid.paste_slot(1, 0)

        assert dst["Index"]["X"] == 1
        assert dst["Index"]["Y"] == 0


class TestSlotWidgetLocked:
    def test_locked_property(self):
        w = SlotWidget(0, locked=True)
        assert w.is_locked is True

    def test_unlocked_property(self):
        w = SlotWidget(0, locked=False)
        assert w.is_locked is False


class TestItemSymbolLookup:
    """Test item symbol resolution from items.json."""

    def test_substance_returns_symbol(self):
        """Known substance (Carbon) should return its symbol 'C'."""
        assert _get_item_symbol("^FUEL1") == "C"

    def test_substance_oxygen_returns_symbol(self):
        """Oxygen should return 'O2'."""
        assert _get_item_symbol("^OXYGEN") == "O2"

    def test_unknown_item_returns_empty(self):
        """Unknown item ID should return empty string."""
        assert _get_item_symbol("^NONEXISTENT_ITEM_XYZ") == ""

    def test_empty_id_returns_empty(self):
        assert _get_item_symbol("") == ""


class TestTypeColors:
    """Test type-to-color mapping."""

    def test_substance_returns_green(self):
        bg, border = _get_type_colors("Substance")
        assert bg == "#2d5a3d"
        assert border == "#4a7"

    def test_product_returns_gold(self):
        bg, border = _get_type_colors("Product")
        assert bg == "#5a4a2d"
        assert border == "#a84"

    def test_technology_returns_blue(self):
        bg, border = _get_type_colors("Technology")
        assert bg == "#2d3a5a"
        assert border == "#48a"

    def test_unknown_returns_empty_colors(self):
        bg, border = _get_type_colors("")
        assert bg == "#2a2a2e"
        assert border == "#555"


class TestPlaceholderPixmap:
    """Test placeholder icon generation."""

    def test_creates_non_null_pixmap(self):
        """Should produce a valid QPixmap."""
        from PySide6.QtGui import QPixmap

        pix = _create_placeholder_pixmap("C", "#2d5a3d", "#4a7", size=32)
        assert isinstance(pix, QPixmap)
        assert not pix.isNull()
        assert pix.width() == 32
        assert pix.height() == 32

    def test_different_sizes(self):
        from PySide6.QtGui import QPixmap

        pix = _create_placeholder_pixmap("O2", "#2d5a3d", "#4a7", size=48)
        assert pix.width() == 48
        assert pix.height() == 48


class TestSwapSlots:
    """Test drag-and-drop swap (move) operation."""

    def test_swap_two_filled_slots(self):
        """Swapping two filled slots exchanges their data, preserving positions."""
        src = _make_slot(x=0, y=0, item_id="^FUEL1", amount=60, max_amount=500)
        dst = _make_slot(x=1, y=0, item_id="^OXYGEN", amount=100, max_amount=250)
        inventory = _make_inventory(
            slots=[src, dst],
            valid_indices=[{"X": 0, "Y": 0}, {"X": 1, "Y": 0}],
            width=2,
            height=1,
        )
        grid = InventoryGrid("Test")
        grid.set_inventory(inventory)

        grid.swap_slots(0, 0, 1, 0)

        src_after = grid._find_slot_data(0, 0)
        dst_after = grid._find_slot_data(1, 0)
        assert src_after["Id"] == "^OXYGEN"
        assert src_after["Amount"] == 100
        assert dst_after["Id"] == "^FUEL1"
        assert dst_after["Amount"] == 60

    def test_swap_preserves_indices(self):
        """After swap, each slot's Index should match its grid position."""
        src = _make_slot(x=0, y=0, item_id="^FUEL1", amount=60)
        dst = _make_slot(x=1, y=0, item_id="^OXYGEN", amount=100)
        inventory = _make_inventory(
            slots=[src, dst],
            valid_indices=[{"X": 0, "Y": 0}, {"X": 1, "Y": 0}],
            width=2,
            height=1,
        )
        grid = InventoryGrid("Test")
        grid.set_inventory(inventory)

        grid.swap_slots(0, 0, 1, 0)

        src_after = grid._find_slot_data(0, 0)
        dst_after = grid._find_slot_data(1, 0)
        assert src_after["Index"] == {"X": 0, "Y": 0}
        assert dst_after["Index"] == {"X": 1, "Y": 0}

    def test_swap_filled_with_empty(self):
        """Swapping a filled slot into an empty position moves the item."""
        src = _make_slot(x=0, y=0, item_id="^FUEL1", amount=60)
        dst = _make_slot(x=1, y=0, item_id="", amount=0, max_amount=0)
        inventory = _make_inventory(
            slots=[src, dst],
            valid_indices=[{"X": 0, "Y": 0}, {"X": 1, "Y": 0}],
            width=2,
            height=1,
        )
        grid = InventoryGrid("Test")
        grid.set_inventory(inventory)

        grid.swap_slots(0, 0, 1, 0)

        src_after = grid._find_slot_data(0, 0)
        dst_after = grid._find_slot_data(1, 0)
        assert src_after["Id"] == ""
        assert dst_after["Id"] == "^FUEL1"

    def test_swap_onto_self_is_noop(self):
        """Swapping a slot with itself should change nothing."""
        src = _make_slot(x=0, y=0, item_id="^FUEL1", amount=60)
        inventory = _make_inventory(
            slots=[src],
            valid_indices=[{"X": 0, "Y": 0}],
            width=1,
            height=1,
        )
        grid = InventoryGrid("Test")
        grid.set_inventory(inventory)

        grid.swap_slots(0, 0, 0, 0)

        slot = grid._find_slot_data(0, 0)
        assert slot["Id"] == "^FUEL1"
        assert slot["Amount"] == 60


class TestCopySlotTo:
    """Test drag-and-drop copy (ctrl+drag) operation."""

    def test_copy_to_empty_slot(self):
        """Copy should duplicate source data to target."""
        src = _make_slot(x=0, y=0, item_id="^FUEL1", amount=60, max_amount=500)
        dst = _make_slot(x=1, y=0, item_id="", amount=0, max_amount=0)
        inventory = _make_inventory(
            slots=[src, dst],
            valid_indices=[{"X": 0, "Y": 0}, {"X": 1, "Y": 0}],
            width=2,
            height=1,
        )
        grid = InventoryGrid("Test")
        grid.set_inventory(inventory)

        grid.copy_slot_to(0, 0, 1, 0)

        src_after = grid._find_slot_data(0, 0)
        dst_after = grid._find_slot_data(1, 0)
        # Source unchanged
        assert src_after["Id"] == "^FUEL1"
        assert src_after["Amount"] == 60
        # Target gets copy
        assert dst_after["Id"] == "^FUEL1"
        assert dst_after["Amount"] == 60
        assert dst_after["MaxAmount"] == 500

    def test_copy_preserves_target_index(self):
        """Copy should keep the target slot's position."""
        src = _make_slot(x=0, y=0, item_id="^FUEL1", amount=60)
        dst = _make_slot(x=1, y=0, item_id="", amount=0)
        inventory = _make_inventory(
            slots=[src, dst],
            valid_indices=[{"X": 0, "Y": 0}, {"X": 1, "Y": 0}],
            width=2,
            height=1,
        )
        grid = InventoryGrid("Test")
        grid.set_inventory(inventory)

        grid.copy_slot_to(0, 0, 1, 0)

        dst_after = grid._find_slot_data(1, 0)
        assert dst_after["Index"] == {"X": 1, "Y": 0}

    def test_copy_overwrites_existing_target(self):
        """Copy onto a filled slot should overwrite the target's data."""
        src = _make_slot(x=0, y=0, item_id="^FUEL1", amount=60, max_amount=500)
        dst = _make_slot(x=1, y=0, item_id="^OXYGEN", amount=100, max_amount=250)
        inventory = _make_inventory(
            slots=[src, dst],
            valid_indices=[{"X": 0, "Y": 0}, {"X": 1, "Y": 0}],
            width=2,
            height=1,
        )
        grid = InventoryGrid("Test")
        grid.set_inventory(inventory)

        grid.copy_slot_to(0, 0, 1, 0)

        dst_after = grid._find_slot_data(1, 0)
        assert dst_after["Id"] == "^FUEL1"
        assert dst_after["Amount"] == 60

    def test_copy_is_independent(self):
        """After copy, modifying source should not affect target."""
        src = _make_slot(x=0, y=0, item_id="^FUEL1", amount=60)
        dst = _make_slot(x=1, y=0, item_id="", amount=0)
        inventory = _make_inventory(
            slots=[src, dst],
            valid_indices=[{"X": 0, "Y": 0}, {"X": 1, "Y": 0}],
            width=2,
            height=1,
        )
        grid = InventoryGrid("Test")
        grid.set_inventory(inventory)

        grid.copy_slot_to(0, 0, 1, 0)

        # Modify source after copy
        src_data = grid._find_slot_data(0, 0)
        src_data["Amount"] = 999

        dst_after = grid._find_slot_data(1, 0)
        assert dst_after["Amount"] == 60


class TestSlotWidgetAcceptsDrop:
    """Test that unlocked slots accept drops and locked slots reject."""

    def test_unlocked_slot_accepts_drops(self):
        w = SlotWidget(0, locked=False, x=0, y=0)
        assert w.acceptDrops() is True

    def test_locked_slot_rejects_drops(self):
        w = SlotWidget(0, locked=True, x=0, y=0)
        assert w.acceptDrops() is False


class TestDragVsClick:
    """Click should only fire on mouseRelease if no drag occurred."""

    def test_mouse_press_does_not_emit_clicked(self):
        """mousePressEvent should NOT emit clicked — deferred to release."""
        from PySide6.QtCore import QPointF
        from PySide6.QtGui import QMouseEvent
        from PySide6.QtCore import QEvent

        w = SlotWidget(0, locked=False, x=2, y=3)
        signals = []
        w.clicked.connect(lambda x, y: signals.append((x, y)))

        event = QMouseEvent(
            QEvent.Type.MouseButtonPress,
            QPointF(10, 10),
            Qt.LeftButton,
            Qt.LeftButton,
            Qt.NoModifier,
        )
        w.mousePressEvent(event)

        assert signals == [], "clicked should not fire on press (deferred to release)"

    def test_mouse_release_without_drag_emits_clicked(self):
        """mouseReleaseEvent after press (no drag) should emit clicked."""
        from PySide6.QtCore import QPointF
        from PySide6.QtGui import QMouseEvent
        from PySide6.QtCore import QEvent

        w = SlotWidget(0, locked=False, x=2, y=3)
        signals = []
        w.clicked.connect(lambda x, y: signals.append((x, y)))

        press = QMouseEvent(
            QEvent.Type.MouseButtonPress,
            QPointF(10, 10),
            Qt.LeftButton,
            Qt.LeftButton,
            Qt.NoModifier,
        )
        w.mousePressEvent(press)

        release = QMouseEvent(
            QEvent.Type.MouseButtonRelease,
            QPointF(12, 12),
            Qt.LeftButton,
            Qt.NoButton,
            Qt.NoModifier,
        )
        w.mouseReleaseEvent(release)

        assert signals == [(2, 3)]

    def test_drag_started_suppresses_click(self):
        """If _drag_started is True, mouseReleaseEvent should NOT emit clicked."""
        from PySide6.QtCore import QPointF
        from PySide6.QtGui import QMouseEvent
        from PySide6.QtCore import QEvent

        w = SlotWidget(0, locked=False, x=2, y=3)
        signals = []
        w.clicked.connect(lambda x, y: signals.append((x, y)))

        press = QMouseEvent(
            QEvent.Type.MouseButtonPress,
            QPointF(10, 10),
            Qt.LeftButton,
            Qt.LeftButton,
            Qt.NoModifier,
        )
        w.mousePressEvent(press)

        # Simulate drag having started
        w._drag_started = True

        release = QMouseEvent(
            QEvent.Type.MouseButtonRelease,
            QPointF(10, 10),
            Qt.LeftButton,
            Qt.NoButton,
            Qt.NoModifier,
        )
        w.mouseReleaseEvent(release)

        assert signals == [], "clicked should NOT fire after drag"

    def test_right_click_still_emits_right_clicked(self):
        """Right-click behavior should be unchanged."""
        from PySide6.QtCore import QPointF
        from PySide6.QtGui import QMouseEvent
        from PySide6.QtCore import QEvent

        w = SlotWidget(0, locked=False, x=2, y=3)
        signals = []
        w.right_clicked.connect(lambda x, y: signals.append((x, y)))

        event = QMouseEvent(
            QEvent.Type.MouseButtonPress,
            QPointF(10, 10),
            Qt.RightButton,
            Qt.RightButton,
            Qt.NoModifier,
        )
        w.mousePressEvent(event)

        assert signals == [(2, 3)]
