"""Multitools editor tab."""

from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from nmstoolkit.gui.widgets.inventory_grid import InventoryGrid
from nmstoolkit.gui.widgets.seed_editor import SeedEditor

_INV_CLASSES = ["C", "B", "A", "S"]


class MultitoolsTab(QWidget):
    def __init__(self):
        super().__init__()
        self._data = None
        self._multitools = []
        self._active_index = 0
        self._current_index = -1
        self._build_ui()

    def _build_ui(self):
        layout = QHBoxLayout(self)

        left = QWidget()
        left.setMaximumWidth(320)
        left_layout = QVBoxLayout(left)

        self._list = QListWidget()
        self._list.currentRowChanged.connect(self._on_selected)
        left_layout.addWidget(self._list)

        # Sort buttons
        sort_bar = QHBoxLayout()
        self._move_up_btn = QPushButton("Move Up")
        self._move_up_btn.clicked.connect(self._on_move_up)
        sort_bar.addWidget(self._move_up_btn)
        self._move_down_btn = QPushButton("Move Down")
        self._move_down_btn.clicked.connect(self._on_move_down)
        sort_bar.addWidget(self._move_down_btn)
        self._set_active_btn = QPushButton("Set Active")
        self._set_active_btn.clicked.connect(self._on_set_active)
        sort_bar.addWidget(self._set_active_btn)
        left_layout.addLayout(sort_bar)

        details = QGroupBox("Multitool Details")
        det_layout = QFormLayout(details)
        self._name_edit = QLineEdit()
        self._name_edit.editingFinished.connect(self._on_name_changed)
        det_layout.addRow("Name:", self._name_edit)
        self._seed_editor = SeedEditor()
        self._seed_editor.seed_changed.connect(self._on_seed_changed)
        det_layout.addRow("Seed:", self._seed_editor)
        self._class_combo = QComboBox()
        self._class_combo.addItems(_INV_CLASSES)
        self._class_combo.currentTextChanged.connect(self._on_class_changed)
        det_layout.addRow("Class:", self._class_combo)
        self._active_label = QLabel("—")
        det_layout.addRow("Active:", self._active_label)
        left_layout.addWidget(details)

        layout.addWidget(left)

        # Right: single inventory grid (multitools use "Store" = combined inventory)
        right = QTabWidget()
        self._inv_store = InventoryGrid("Inventory")
        right.addTab(self._inv_store, "Inventory")
        layout.addWidget(right)

    def set_data(self, psd: dict):
        self._data = psd
        self._multitools = psd.get("Multitools", [])
        self._active_index = psd.get("ActiveMultioolIndex", 0)
        self._refresh_list()
        if self._multitools:
            self._list.setCurrentRow(0)

    def _refresh_list(self):
        current = self._list.currentRow()
        self._list.clear()
        for i, mt in enumerate(self._multitools):
            name = mt.get("Name", f"Multitool {i + 1}")
            if not name:
                name = f"Multitool {i + 1}"
            active = " *" if i == self._active_index else ""
            self._list.addItem(f"{i + 1}. {name}{active}")
        if 0 <= current < len(self._multitools):
            self._list.setCurrentRow(current)

    def _current_multitool(self):
        if self._current_index < 0 or self._current_index >= len(self._multitools):
            return None
        return self._multitools[self._current_index]

    def _on_selected(self, index):
        if index < 0 or index >= len(self._multitools):
            self._current_index = -1
            return
        self._current_index = index
        mt = self._multitools[index]

        self._name_edit.blockSignals(True)
        self._name_edit.setText(mt.get("Name", ""))
        self._name_edit.blockSignals(False)

        self._seed_editor.set_seed(mt.get("Seed", ""))

        store = mt.get("Store", {})
        if isinstance(store, dict):
            inv_class = store.get("Class", {})
            class_str = inv_class.get("InventoryClass", "C") if isinstance(inv_class, dict) else "C"
        else:
            class_str = "C"
        self._class_combo.blockSignals(True)
        idx = self._class_combo.findText(class_str)
        self._class_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self._class_combo.blockSignals(False)

        self._active_label.setText("Yes" if index == self._active_index else "No")
        self._inv_store.set_inventory(store if isinstance(store, dict) else {})

    def _on_move_up(self):
        idx = self._current_index
        if idx <= 0 or idx >= len(self._multitools):
            return
        self._swap_multitools(idx, idx - 1)
        self._list.setCurrentRow(idx - 1)

    def _on_move_down(self):
        idx = self._current_index
        if idx < 0 or idx >= len(self._multitools) - 1:
            return
        self._swap_multitools(idx, idx + 1)
        self._list.setCurrentRow(idx + 1)

    def _on_set_active(self):
        idx = self._current_index
        if idx < 0 or idx >= len(self._multitools) or self._data is None:
            return
        self._active_index = idx
        self._data["ActiveMultioolIndex"] = idx
        self._refresh_list()

    def _swap_multitools(self, a, b):
        """Swap two multitools, adjusting the active index."""
        self._multitools[a], self._multitools[b] = self._multitools[b], self._multitools[a]
        if self._active_index == a:
            self._active_index = b
        elif self._active_index == b:
            self._active_index = a
        if self._data:
            self._data["ActiveMultioolIndex"] = self._active_index
        self._refresh_list()

    def _on_name_changed(self):
        mt = self._current_multitool()
        if mt is not None:
            mt["Name"] = self._name_edit.text()
            self._refresh_list()

    def _on_seed_changed(self, seed):
        mt = self._current_multitool()
        if mt is not None:
            mt["Seed"] = seed
            resource = mt.get("Resource", {})
            if isinstance(resource, dict):
                resource["Seed"] = seed

    def _on_class_changed(self, text):
        mt = self._current_multitool()
        if mt is None:
            return
        store = mt.get("Store", {})
        if isinstance(store, dict):
            cls = store.get("Class", {})
            if isinstance(cls, dict):
                cls["InventoryClass"] = text
            else:
                store["Class"] = {"InventoryClass": text}
        self._refresh_list()
