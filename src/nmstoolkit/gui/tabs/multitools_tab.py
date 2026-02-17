"""Multitools editor tab."""

from typing import Optional

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
from nmstoolkit.gui import vault
from nmstoolkit.gui.preview_support import (
    find_scene_resource_filename,
    load_template_preview_meshes,
    seed_to_text,
)

_INV_CLASSES = ["C", "B", "A", "S"]


class MultitoolsTab(QWidget):
    def __init__(self):
        super().__init__()
        self._data = None
        self._multitools = []
        self._active_index = 0
        self._current_index = -1
        self._preview_view: Optional[QWidget] = None
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

        # Vault
        vault_group = QGroupBox("Cross-Save Vault")
        vault_layout = QVBoxLayout(vault_group)
        self._vault_list = QListWidget()
        self._vault_list.setMaximumHeight(100)
        vault_layout.addWidget(self._vault_list)
        vault_btn_layout = QHBoxLayout()
        self._vault_save_btn = QPushButton("Store in Vault")
        self._vault_save_btn.clicked.connect(self._on_vault_save)
        vault_btn_layout.addWidget(self._vault_save_btn)
        self._vault_load_btn = QPushButton("Load from Vault")
        self._vault_load_btn.clicked.connect(self._on_vault_load)
        vault_btn_layout.addWidget(self._vault_load_btn)
        self._vault_delete_btn = QPushButton("Delete")
        self._vault_delete_btn.clicked.connect(self._on_vault_delete)
        vault_btn_layout.addWidget(self._vault_delete_btn)
        vault_layout.addLayout(vault_btn_layout)
        left_layout.addWidget(vault_group)

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
        self._tabs = QTabWidget()
        self._inv_store = InventoryGrid("Inventory")
        self._tabs.addTab(self._inv_store, "Inventory")
        self._preview_tab = QWidget()
        preview_layout = QVBoxLayout(self._preview_tab)
        self._preview_identity = QLabel("Seed: —\nResource: —")
        self._preview_identity.setWordWrap(True)
        self._preview_fidelity = QLabel(
            "Fidelity: template-level preview (seed/resource shown; exact procedural reconstruction not guaranteed)"
        )
        self._preview_fidelity.setWordWrap(True)
        self._preview_status = QLabel("Preview: select a multitool")
        self._preview_status.setWordWrap(True)
        self._preview_placeholder = QLabel("3D preview will appear here")
        self._preview_placeholder.setMinimumHeight(280)
        self._preview_placeholder.setStyleSheet("color: #aaa;")
        preview_layout.addWidget(self._preview_identity)
        preview_layout.addWidget(self._preview_fidelity)
        preview_layout.addWidget(self._preview_status)
        preview_layout.addWidget(self._preview_placeholder, 1)
        self._tabs.addTab(self._preview_tab, "Preview")
        layout.addWidget(self._tabs)

    def set_data(self, psd: dict):
        self._data = psd
        self._multitools = psd.get("Multitools", [])
        self._active_index = psd.get("ActiveMultioolIndex", 0)
        self._refresh_list()
        self._refresh_vault()
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
        self._update_preview(mt)

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

    def _refresh_vault(self):
        self._vault_list.clear()
        self._vault_entries = []
        for path, name in vault.scan_vault("multitools"):
            self._vault_entries.append(path)
            self._vault_list.addItem(name)

    def _on_vault_save(self):
        mt = self._current_multitool()
        if mt is None:
            return
        import copy
        name = mt.get("Name", "") or "Multitool"
        vault.save_to_vault("multitools", copy.deepcopy(mt), name)
        self._refresh_vault()

    def _on_vault_load(self):
        row = self._vault_list.currentRow()
        if row < 0 or row >= len(self._vault_entries):
            return
        mt = vault.load_from_vault(self._vault_entries[row])
        self._multitools.append(mt)
        self._refresh_list()
        self._refresh_vault()

    def _on_vault_delete(self):
        row = self._vault_list.currentRow()
        if row < 0 or row >= len(self._vault_entries):
            return
        vault.delete_from_vault(self._vault_entries[row])
        self._refresh_vault()

    def _ensure_preview_view(self) -> None:
        if self._preview_view is not None:
            return
        try:
            from nmstoolkit.gui.widgets.corvette_3d_view import Corvette3DView
        except Exception:
            self._preview_status.setText("Preview unavailable: OpenGL widget import failed.")
            return
        self._preview_view = Corvette3DView(self._preview_tab)
        if hasattr(self._preview_view, "set_grid_visible"):
            self._preview_view.set_grid_visible(False)
        if hasattr(self._preview_view, "set_layering_enabled"):
            self._preview_view.set_layering_enabled(False)
        self._preview_tab.layout().replaceWidget(self._preview_placeholder, self._preview_view)
        self._preview_placeholder.hide()
        self._preview_view.show()

    def _load_preview_meshes(self, resource_filename: str):
        return load_template_preview_meshes(resource_filename)

    def _update_preview(self, multitool: dict) -> None:
        resource = find_scene_resource_filename(multitool)
        seed = seed_to_text(multitool.get("Seed"))
        if seed == "—":
            resource_obj = multitool.get("Resource", {})
            if isinstance(resource_obj, dict):
                seed = seed_to_text(resource_obj.get("Seed"))
        self._preview_identity.setText(f"Seed: {seed}\nResource: {resource or '—'}")
        self._preview_fidelity.setText(
            "Fidelity: template-level preview (seed/resource shown; exact procedural reconstruction not guaranteed)"
        )
        if not resource:
            self._preview_status.setText("Preview unavailable: multitool resource filename missing.")
            return
        meshes, status = self._load_preview_meshes(resource)
        if not meshes:
            self._preview_status.setText(status)
            return
        self._ensure_preview_view()
        if self._preview_view is None:
            return
        self._preview_view.set_modules(
            {
                "Width": 1,
                "Height": 1,
                "Slots": [{"Id": "^MULTITOOL_PREVIEW", "Index": {"X": 0, "Y": 0}, "_no_layer_tooltip": True}],
            }
        )
        self._preview_view.set_mesh_data("MULTITOOL_PREVIEW", meshes)
        self._preview_status.setText(status)
        self._preview_view.update()
