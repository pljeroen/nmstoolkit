"""Vehicles (Exocraft) editor tab."""

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QProgressBar,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from nmstoolkit.gui.widgets.inventory_grid import InventoryGrid
from nmstoolkit.gui.widgets.seed_editor import SeedEditor
from nmstoolkit.gui.preview_support import (
    PreviewLoadThread,
    find_scene_resource_filename,
    load_template_preview_meshes,
    resolve_vehicle_scene,
    seed_to_text,
)

VEHICLE_NAMES = [
    "Roamer", "Nomad", "Colossus", "Pilgrim", "Nautilon",
    "Minotaur", "Motorcycle",
]


def _inventory_has_data(inv: dict) -> bool:
    if not isinstance(inv, dict):
        return False
    for slot in inv.get("Slots", []):
        if isinstance(slot, dict) and slot.get("Id"):
            return True
    return False


class VehiclesTab(QWidget):
    def __init__(self):
        super().__init__()
        self._data = None
        self._vehicles = []
        self._current_index = -1
        self._preview_view: Optional[QWidget] = None
        self._preview_request_id = 0
        self._preview_thread: Optional[PreviewLoadThread] = None
        self._build_ui()

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self._cancel_preview_thread()
        super().closeEvent(event)

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
        self._inv_tabs = QTabWidget()
        self._inv = InventoryGrid("Inventory")
        self._inv_tech = InventoryGrid("Technology")
        self._inv_cargo = InventoryGrid("Cargo")
        self._inv_tabs.addTab(self._inv, "Inventory")
        self._tech_splitter = QSplitter(Qt.Orientation.Vertical)
        self._tech_splitter.setChildrenCollapsible(False)
        self._tech_splitter.addWidget(self._inv_tech)
        self._preview_panel = QWidget()
        preview_layout = QVBoxLayout(self._preview_panel)
        self._preview_identity = QLabel("Seed: —\nResource: —")
        self._preview_identity.setWordWrap(True)
        self._preview_fidelity = QLabel(
            "Fidelity: template-level preview (seed/resource shown; exact procedural reconstruction not guaranteed)"
        )
        self._preview_fidelity.setWordWrap(True)
        self._preview_status = QLabel("Preview: select a vehicle")
        self._preview_status.setWordWrap(True)
        self._preview_progress = QProgressBar()
        self._preview_progress.setRange(0, 0)
        self._preview_progress.setVisible(False)
        self._preview_placeholder = QLabel("3D preview will appear here")
        self._preview_placeholder.setMinimumHeight(280)
        self._preview_placeholder.setStyleSheet("color: #aaa;")
        preview_layout.addWidget(self._preview_identity)
        preview_layout.addWidget(self._preview_fidelity)
        preview_layout.addWidget(self._preview_status)
        preview_layout.addWidget(self._preview_progress)
        preview_layout.addWidget(self._preview_placeholder, 1)
        self._tech_splitter.addWidget(self._preview_panel)
        self._tech_splitter.setStretchFactor(0, 3)
        self._tech_splitter.setStretchFactor(1, 2)
        self._inv_tabs.addTab(self._tech_splitter, "Technology + Effects")
        self._inv_tabs.addTab(self._inv_cargo, "Cargo")
        self._tech_tab_index = self._inv_tabs.indexOf(self._tech_splitter)
        self._inv_tabs.currentChanged.connect(self._on_tab_changed)
        self._cargo_tab_index = self._inv_tabs.indexOf(self._inv_cargo)
        layout.addWidget(self._inv_tabs)

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
        cargo_inv = v.get("Inventory_Cargo", {})
        self._inv_cargo.set_inventory(cargo_inv)
        self._inv_tabs.setTabVisible(self._cargo_tab_index, _inventory_has_data(cargo_inv))
        self._update_preview(v, load_meshes=self._inv_tabs.currentIndex() == self._tech_tab_index)

    def _on_tab_changed(self, _index: int) -> None:
        if self._inv_tabs.currentIndex() != self._tech_tab_index:
            return
        vehicle = self._current_vehicle()
        if vehicle is not None:
            self._update_preview(vehicle, load_meshes=True)

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

    def _ensure_preview_view(self) -> None:
        if self._preview_view is not None:
            return
        try:
            from nmstoolkit.gui.widgets.corvette_3d_view import Corvette3DView
        except Exception:
            self._preview_status.setText("Preview unavailable: OpenGL widget import failed.")
            return
        self._preview_view = Corvette3DView(self._preview_panel)
        if hasattr(self._preview_view, "set_grid_visible"):
            self._preview_view.set_grid_visible(False)
        if hasattr(self._preview_view, "set_layering_enabled"):
            self._preview_view.set_layering_enabled(False)
        self._preview_panel.layout().replaceWidget(self._preview_placeholder, self._preview_view)
        self._preview_placeholder.hide()
        self._preview_view.show()

    def _load_preview_meshes(self, resource_filename: str):
        return load_template_preview_meshes(resource_filename)

    def _update_preview(self, vehicle: dict, *, load_meshes: bool = True) -> None:
        resource = find_scene_resource_filename(vehicle)
        if not resource:
            default_name = VEHICLE_NAMES[self._current_index] if 0 <= self._current_index < len(VEHICLE_NAMES) else ""
            resource = resolve_vehicle_scene(default_name)
        seed = seed_to_text(vehicle.get("Seed"))
        if seed == "—":
            resource_obj = vehicle.get("Resource", {})
            if isinstance(resource_obj, dict):
                seed = seed_to_text(resource_obj.get("Seed"))
        self._preview_identity.setText(f"Seed: {seed}\nResource: {resource or '—'}")
        self._preview_fidelity.setText(
            "Fidelity: template-level preview (seed/resource shown; exact procedural reconstruction not guaranteed)"
        )
        if not load_meshes:
            self._preview_progress.setVisible(False)
            self._preview_status.setText("Open Technology + Effects to load vehicle model.")
            return
        if not resource:
            self._preview_progress.setVisible(False)
            self._preview_status.setText("Preview unavailable: vehicle resource filename missing.")
            return
        self._start_preview_load(resource)

    def _start_preview_load(self, resource: str) -> None:
        self._cancel_preview_thread()
        self._preview_request_id += 1
        request_id = self._preview_request_id
        self._preview_status.setText("Loading preview meshes...")
        self._preview_progress.setVisible(True)
        thread = PreviewLoadThread(
            request_id=request_id,
            resource_filename=resource,
            loader=self._load_preview_meshes,
            parent=self,
        )
        thread.completed.connect(self._on_preview_loaded)
        thread.finished.connect(thread.deleteLater)
        self._preview_thread = thread
        thread.start()

    def _cancel_preview_thread(self) -> None:
        thread = self._preview_thread
        if thread is None:
            return
        if thread.isRunning():
            thread.requestInterruption()
            thread.quit()
            thread.wait(1000)
        self._preview_thread = None

    def _on_preview_loaded(self, request_id: int, meshes: object, status: str) -> None:
        if request_id != self._preview_request_id:
            return
        self._preview_thread = None
        self._preview_progress.setVisible(False)
        mesh_list = meshes if isinstance(meshes, list) else []
        if not mesh_list:
            self._preview_status.setText(status)
            return
        self._ensure_preview_view()
        if self._preview_view is None:
            return
        self._preview_view.set_modules(
            {
                "Width": 1,
                "Height": 1,
                "Slots": [{"Id": "^VEHICLE_PREVIEW", "Index": {"X": 0, "Y": 0}, "_no_layer_tooltip": True}],
            }
        )
        self._preview_view.set_mesh_data("VEHICLE_PREVIEW", mesh_list)
        self._preview_status.setText(status)
        self._preview_view.update()
