"""Slot editor dialog — edit individual inventory slot properties."""

import copy
import json
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

DATA_DIR = Path(__file__).parent.parent.parent / "data"

_ITEMS_CACHE = None

_TYPE_MAP = {
    "substance": "Substance",
    "product": "Product",
    "product-template": "Product",
    "procedural-product": "Product",
    "technology": "Technology",
    "procedural-technology": "Technology",
}

INVENTORY_TYPES = ["Substance", "Product", "Technology"]


def _load_items():
    """Load and cache items from items.json."""
    global _ITEMS_CACHE
    if _ITEMS_CACHE is not None:
        return _ITEMS_CACHE
    items_path = DATA_DIR / "items.json"
    if not items_path.exists():
        _ITEMS_CACHE = []
        return _ITEMS_CACHE
    with open(items_path, "r", encoding="utf-8") as f:
        _ITEMS_CACHE = json.load(f)
    return _ITEMS_CACHE


class SlotEditor(QDialog):
    """Dialog for editing a single inventory slot."""

    def __init__(self, slot: dict, inventory: dict, parent=None):
        super().__init__(parent)
        self._slot = slot
        self._inventory = inventory
        self.setWindowTitle("Edit Slot")
        self.setMinimumWidth(400)

        self._items = _load_items()
        self._items_by_id = {item["id"]: item for item in self._items}

        self._build_ui()
        self._populate_from_slot()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        form = QFormLayout()

        # Item picker
        self.item_combo = QComboBox()
        self.item_combo.setEditable(True)
        self.item_combo.setInsertPolicy(QComboBox.NoInsert)
        self.item_combo.addItem("(Empty)", None)
        for item in self._items:
            inv_type = _TYPE_MAP.get(item.get("type", ""), "")
            label = f"{item['id']} — {item['name']} ({inv_type})"
            self.item_combo.addItem(label, item)
        self.item_combo.currentIndexChanged.connect(self._on_item_changed)
        form.addRow("Item:", self.item_combo)

        # Type
        self.type_combo = QComboBox()
        self.type_combo.addItems(INVENTORY_TYPES)
        form.addRow("Type:", self.type_combo)

        # Amount / MaxAmount
        self.amount_spin = QSpinBox()
        self.amount_spin.setRange(0, 2_147_483_647)
        form.addRow("Amount:", self.amount_spin)

        self.max_amount_spin = QSpinBox()
        self.max_amount_spin.setRange(0, 2_147_483_647)
        form.addRow("Max Amount:", self.max_amount_spin)

        # DamageFactor
        self.damage_spin = QDoubleSpinBox()
        self.damage_spin.setRange(0.0, 1.0)
        self.damage_spin.setSingleStep(0.05)
        self.damage_spin.setDecimals(2)
        form.addRow("Damage Factor:", self.damage_spin)

        # FullyInstalled
        self.installed_check = QCheckBox("Fully Installed")
        form.addRow("", self.installed_check)

        layout.addLayout(form)

        # Buttons
        btn_layout = QHBoxLayout()
        apply_btn = QPushButton("Apply")
        apply_btn.clicked.connect(self._on_apply)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        clear_btn = QPushButton("Clear Slot")
        clear_btn.clicked.connect(self._on_clear)

        btn_layout.addWidget(apply_btn)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(clear_btn)
        layout.addLayout(btn_layout)

    def _populate_from_slot(self):
        item_id = self._slot.get("Id", "")
        if item_id and item_id in self._items_by_id:
            item = self._items_by_id[item_id]
            for i in range(self.item_combo.count()):
                data = self.item_combo.itemData(i)
                if data is not None and data.get("id") == item_id:
                    self.item_combo.setCurrentIndex(i)
                    break
        else:
            self.item_combo.setCurrentIndex(0)

        inv_type = self._slot.get("Type", {}).get("InventoryType", "Substance")
        idx = self.type_combo.findText(inv_type)
        if idx >= 0:
            self.type_combo.setCurrentIndex(idx)

        self.amount_spin.setValue(self._slot.get("Amount", 0))
        self.max_amount_spin.setValue(self._slot.get("MaxAmount", 0))
        self.damage_spin.setValue(self._slot.get("DamageFactor", 0.0))
        self.installed_check.setChecked(self._slot.get("FullyInstalled", True))

    def _on_item_changed(self, index):
        item_data = self.item_combo.itemData(index)
        if item_data is not None:
            item_type = item_data.get("type", "")
            inv_type = _TYPE_MAP.get(item_type, "")
            if inv_type:
                idx = self.type_combo.findText(inv_type)
                if idx >= 0:
                    self.type_combo.setCurrentIndex(idx)

    def select_item_by_id(self, item_id: str):
        """Select an item in the combo by its ID. Used programmatically."""
        for i in range(self.item_combo.count()):
            data = self.item_combo.itemData(i)
            if data is not None and data.get("id") == item_id:
                self.item_combo.setCurrentIndex(i)
                self._on_item_changed(i)
                return

    def apply_changes(self):
        """Apply current field values to the slot dict in-place."""
        item_data = self.item_combo.currentData()
        if item_data is not None:
            self._slot["Id"] = item_data["id"]
        elif self.item_combo.currentIndex() == 0:
            self._slot["Id"] = ""

        self._slot["Type"]["InventoryType"] = self.type_combo.currentText()
        self._slot["Amount"] = self.amount_spin.value()
        self._slot["MaxAmount"] = self.max_amount_spin.value()
        self._slot["DamageFactor"] = self.damage_spin.value()
        self._slot["FullyInstalled"] = self.installed_check.isChecked()

    def clear_slot(self):
        """Reset the slot to empty."""
        self._slot["Id"] = ""
        self._slot["Amount"] = 0
        self._slot["MaxAmount"] = 0
        self._slot["DamageFactor"] = 0.0
        self._slot["FullyInstalled"] = True
        self._slot["Type"]["InventoryType"] = "Substance"

    def copy_slot(self) -> dict:
        """Return a deep copy of the current slot data."""
        return copy.deepcopy(self._slot)

    def paste_slot(self, clipboard: dict):
        """Apply clipboard data to the slot, preserving the slot's Index."""
        original_index = copy.deepcopy(self._slot.get("Index", {"X": 0, "Y": 0}))
        for key in ("Type", "Id", "Amount", "MaxAmount", "DamageFactor", "FullyInstalled"):
            if key in clipboard:
                if isinstance(clipboard[key], dict):
                    self._slot[key] = copy.deepcopy(clipboard[key])
                else:
                    self._slot[key] = clipboard[key]
        self._slot["Index"] = original_index
        self._populate_from_slot()

    def _on_apply(self):
        self.apply_changes()
        self.accept()

    def _on_clear(self):
        self.clear_slot()
        self.accept()
