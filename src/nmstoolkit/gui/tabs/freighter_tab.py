"""Freighter editor tab."""

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
