"""Vehicles (Exocraft) editor tab."""

from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from nmstoolkit.gui.widgets.inventory_grid import InventoryGrid
from nmstoolkit.gui.widgets.seed_editor import SeedEditor

VEHICLE_NAMES = [
    "Roamer", "Nomad", "Colossus", "Pilgrim", "Nautilon",
    "Minotaur", "Motorcycle",
]


class VehiclesTab(QWidget):
    def __init__(self):
        super().__init__()
        self._data = None
        self._vehicles = []
        self._current_index = -1
        self._build_ui()

    def _build_ui(self):
        layout = QHBoxLayout(self)

        # Left: list + details
        left = QWidget()
        left.setMaximumWidth(280)
        left_layout = QVBoxLayout(left)

        self._list = QListWidget()
        self._list.currentRowChanged.connect(self._on_selected)
        left_layout.addWidget(self._list)

        details = QGroupBox("Vehicle Details")
        det_layout = QFormLayout(details)

        self._name_edit = QLineEdit()
        self._name_edit.editingFinished.connect(self._on_name_changed)
        det_layout.addRow("Name:", self._name_edit)

        self._type_label = QLabel("—")
        det_layout.addRow("Type:", self._type_label)

        self._seed_editor = SeedEditor("Seed")
        self._seed_editor.seed_changed.connect(self._on_seed_changed)
        det_layout.addRow("Seed:", self._seed_editor)

        self._location_label = QLabel("—")
        self._location_label.setWordWrap(True)
        det_layout.addRow("Location:", self._location_label)

        left_layout.addWidget(details)
        layout.addWidget(left)

        # Right: inventory tabs
        right = QTabWidget()
        self._inv = InventoryGrid("Inventory")
        self._inv_tech = InventoryGrid("Technology")
        self._inv_cargo = InventoryGrid("Cargo")
        right.addTab(self._inv, "Inventory")
        right.addTab(self._inv_tech, "Technology")
        right.addTab(self._inv_cargo, "Cargo")
        layout.addWidget(right)

    def set_data(self, psd: dict):
        self._data = psd
        self._vehicles = psd.get("VehicleOwnership", [])
        self._current_index = -1
        self._list.clear()
        for i, v in enumerate(self._vehicles):
            default_name = VEHICLE_NAMES[i] if i < len(VEHICLE_NAMES) else f"Vehicle {i + 1}"
            custom_name = v.get("Name", "")
            display = f"{custom_name} ({default_name})" if custom_name else default_name
            # Mark if it has inventory data
            has_inv = bool(v.get("Inventory", {}).get("Slots", []))
            if has_inv:
                display += " [equipped]"
            self._list.addItem(f"{i + 1}. {display}")
        if self._vehicles:
            self._list.setCurrentRow(0)

    def _current_vehicle(self):
        if self._current_index < 0 or self._current_index >= len(self._vehicles):
            return None
        return self._vehicles[self._current_index]

    def _on_selected(self, index):
        if index < 0 or index >= len(self._vehicles):
            self._current_index = -1
            return
        self._current_index = index
        v = self._vehicles[index]

        # Name
        self._name_edit.blockSignals(True)
        self._name_edit.setText(v.get("Name", ""))
        self._name_edit.blockSignals(False)

        # Type
        default_name = VEHICLE_NAMES[index] if index < len(VEHICLE_NAMES) else f"Vehicle {index + 1}"
        self._type_label.setText(default_name)

        # Seed
        self._seed_editor.set_seed(v.get("Seed", ""))

        # Location
        location = v.get("Location", "")
        position = v.get("Position", [])
        if position and isinstance(position, list):
            pos_str = ", ".join(f"{p:.0f}" for p in position if isinstance(p, (int, float)))
            self._location_label.setText(pos_str if pos_str else "—")
        else:
            self._location_label.setText(str(location) if location else "—")

        # Inventories
        self._inv.set_inventory(v.get("Inventory", {}))
        self._inv_tech.set_inventory(v.get("Inventory_TechOnly", {}))
        self._inv_cargo.set_inventory(v.get("Inventory_Cargo", {}))

    def _on_name_changed(self):
        v = self._current_vehicle()
        if v is not None:
            v["Name"] = self._name_edit.text()

    def _on_seed_changed(self, seed):
        v = self._current_vehicle()
        if v is not None:
            v["Seed"] = seed
            resource = v.get("Resource", {})
            if isinstance(resource, dict):
                resource["Seed"] = seed
