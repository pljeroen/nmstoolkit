"""Freighter editor tab."""

from typing import Optional

from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from nmstoolkit.gui.widgets.inventory_grid import InventoryGrid
from nmstoolkit.gui.widgets.seed_editor import SeedEditor
from nmstoolkit.gui.widgets.stat_editor import StatEditor
from nmstoolkit.gui.preview_support import (
    configure_preview_view,
    find_scene_resource_filename,
    load_template_preview_meshes,
    seed_to_text,
)

_STAT_IDS = [
    ("^YOURFREIG_DAM", "Damage"),
    ("^YOURFREIG_HYP", "Hyperdrive"),
    ("^YOURFREIG_SHI", "Shield"),
    ("^YOURFREIG_FLE", "Fleet Coordination"),
]


def _inventory_has_data(inv: dict) -> bool:
    if not isinstance(inv, dict):
        return False
    for slot in inv.get("Slots", []):
        if isinstance(slot, dict) and slot.get("Id"):
            return True
    return False


class FreighterTab(QWidget):
    def __init__(self):
        super().__init__()
        self._data = None
        self._preview_view: Optional[QWidget] = None
        self._build_ui()

    def _build_ui(self):
        layout = QHBoxLayout(self)

        left = QWidget()
        left.setMaximumWidth(320)
        left_layout = QVBoxLayout(left)

        details = QGroupBox("Freighter Details")
        det_layout = QFormLayout(details)
        self._name_edit = QLineEdit()
        self._name_edit.editingFinished.connect(self._on_name_changed)
        det_layout.addRow("Name:", self._name_edit)
        self._seed_editor = SeedEditor()
        self._seed_editor.seed_changed.connect(self._on_seed_changed)
        det_layout.addRow("Seed:", self._seed_editor)
        self._type_label = QLabel("—")
        det_layout.addRow("Type:", self._type_label)
        left_layout.addWidget(details)

        # Base stats
        stats_group = QGroupBox("Base Stats")
        stats_layout = QFormLayout(stats_group)
        self._stat_editors = {}
        for stat_id, label in _STAT_IDS:
            editor = StatEditor(label, 0, 999999)
            editor.value_changed.connect(
                lambda val, sid=stat_id: self._on_stat_changed(sid, val)
            )
            stats_layout.addRow(f"{label}:", editor)
            self._stat_editors[stat_id] = editor
        left_layout.addWidget(stats_group)

        left_layout.addStretch()
        layout.addWidget(left)

        self._inv_tabs = QTabWidget()
        self._inv_general = InventoryGrid("General")
        self._inv_tech = InventoryGrid("Technology")
        self._inv_cargo = InventoryGrid("Cargo")
        self._inv_tabs.addTab(self._inv_general, "General")
        self._inv_tabs.addTab(self._inv_tech, "Technology + Effects")
        self._inv_tabs.addTab(self._inv_cargo, "Cargo")
        self._preview_tab = QWidget()
        preview_layout = QVBoxLayout(self._preview_tab)
        self._preview_identity = QLabel("Seed: —\nResource: —")
        self._preview_identity.setWordWrap(True)
        self._preview_fidelity = QLabel(
            "Fidelity: template-level preview (seed/resource shown; exact procedural reconstruction not guaranteed)"
        )
        self._preview_fidelity.setWordWrap(True)
        self._preview_status = QLabel("Preview: load a save to view freighter preview")
        self._preview_status.setWordWrap(True)
        self._preview_placeholder = QLabel("3D preview will appear here")
        self._preview_placeholder.setMinimumHeight(280)
        self._preview_placeholder.setStyleSheet("color: #aaa;")
        preview_layout.addWidget(self._preview_identity)
        preview_layout.addWidget(self._preview_fidelity)
        preview_layout.addWidget(self._preview_status)
        preview_layout.addWidget(self._preview_placeholder, 1)
        self._inv_tabs.addTab(self._preview_tab, "Preview")
        self._cargo_tab_index = self._inv_tabs.indexOf(self._inv_cargo)
        layout.addWidget(self._inv_tabs)

    def set_data(self, psd: dict):
        self._data = psd

        # Freighter resource is in CurrentFreighter (model/seed), not FreighterOwnership
        freighter_res = psd.get("CurrentFreighter", {})
        name = psd.get("PlayerFreighterName", "")

        self._name_edit.blockSignals(True)
        self._name_edit.setText(name if name else "")
        self._name_edit.blockSignals(False)

        self._seed_editor.set_seed(
            freighter_res.get("Seed", "") if isinstance(freighter_res, dict) else ""
        )

        # Detect type from filename
        filename = freighter_res.get("Filename", "") if isinstance(freighter_res, dict) else ""
        type_str = "—"
        if filename:
            fname_upper = filename.upper()
            if "YOURFREIG" in fname_upper or "YOURFREI" in fname_upper:
                if "CAPITAL" in fname_upper:
                    type_str = "Capital"
                elif "YOURFREIG" in fname_upper:
                    type_str = "Freighter"
            elif "YOURFREI_CORVETTE" in fname_upper or "CORVETTE" in fname_upper:
                type_str = "Corvette"
        self._type_label.setText(type_str)

        # Base stats from FreighterInventory
        inv = psd.get("FreighterInventory", {})
        base_stats = inv.get("BaseStatValues", [])
        stats_by_id = {}
        for bs in base_stats:
            if isinstance(bs, dict):
                stats_by_id[bs.get("BaseStatID", "")] = bs.get("Value", 0)
        for stat_id, editor in self._stat_editors.items():
            editor.set_value(int(stats_by_id.get(stat_id, 0)))

        # Freighter inventories are at PSD top level
        self._inv_general.set_inventory(inv)
        self._inv_tech.set_inventory(psd.get("FreighterInventory_TechOnly", {}))
        cargo_inv = psd.get("FreighterInventory_Cargo", {})
        self._inv_cargo.set_inventory(cargo_inv)
        self._inv_tabs.setTabVisible(self._cargo_tab_index, _inventory_has_data(cargo_inv))
        self._update_preview(freighter_res if isinstance(freighter_res, dict) else {})

    def _on_name_changed(self):
        if self._data is not None:
            self._data["PlayerFreighterName"] = self._name_edit.text()

    def _on_seed_changed(self, seed):
        if self._data is not None:
            freighter_res = self._data.get("CurrentFreighter", {})
            if isinstance(freighter_res, dict):
                freighter_res["Seed"] = seed

    def _on_stat_changed(self, stat_id, value):
        if self._data is None:
            return
        inv = self._data.get("FreighterInventory", {})
        base_stats = inv.get("BaseStatValues", [])
        for bs in base_stats:
            if isinstance(bs, dict) and bs.get("BaseStatID") == stat_id:
                bs["Value"] = float(value)
                return
        base_stats.append({"BaseStatID": stat_id, "Value": float(value)})
        inv["BaseStatValues"] = base_stats

    def _ensure_preview_view(self) -> None:
        if self._preview_view is not None:
            return
        try:
            from nmstoolkit.gui.widgets.corvette_3d_view import Corvette3DView
        except Exception:
            self._preview_status.setText("Preview unavailable: OpenGL widget import failed.")
            return
        self._preview_view = Corvette3DView(self._preview_tab)
        configure_preview_view(self._preview_view)
        self._preview_tab.layout().replaceWidget(self._preview_placeholder, self._preview_view)
        self._preview_placeholder.hide()
        self._preview_view.show()

    def _load_preview_meshes(self, resource_filename: str):
        return load_template_preview_meshes(resource_filename)

    def _update_preview(self, freighter_resource: dict) -> None:
        resource = find_scene_resource_filename(freighter_resource)
        seed = seed_to_text(freighter_resource.get("Seed"))
        self._preview_identity.setText(f"Seed: {seed}\nResource: {resource or '—'}")
        self._preview_fidelity.setText(
            "Fidelity: template-level preview (seed/resource shown; exact procedural reconstruction not guaranteed)"
        )
        if not resource:
            self._preview_status.setText("Preview unavailable: freighter resource filename missing.")
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
                "Slots": [{"Id": "^FREIGHTER_PREVIEW", "Index": {"X": 0, "Y": 0}, "_no_layer_tooltip": True}],
            }
        )
        self._preview_view.set_mesh_data("FREIGHTER_PREVIEW", meshes)
        self._preview_status.setText(status)
        self._preview_view.update()
