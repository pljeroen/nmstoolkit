"""Bases & Storage editor tab."""

import json
import re
import time
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from nmstoolkit.gui.widgets.inventory_grid import InventoryGrid
from nmstoolkit.paths import user_data_root


def _base_library_dir() -> Path:
    """Return persistent base library directory."""
    lib_dir = user_data_root() / "base_library"
    lib_dir.mkdir(parents=True, exist_ok=True)
    return lib_dir


def _scan_library(lib_dir: Path) -> list:
    """Scan library dir for saved bases. Returns [(path, name, part_count), ...]."""
    results = []
    for p in sorted(lib_dir.glob("*.json")):
        try:
            data = json.loads(p.read_text())
            name = data.get("Name", p.stem)
            objects = data.get("Objects", [])
            part_count = len(objects) if isinstance(objects, list) else 0
            results.append((p, name, part_count))
        except (json.JSONDecodeError, OSError):
            pass
    return results

# Object IDs that count as electrical wires
_WIRE_IDS = {"U_POWERLINE"}

# NMS hard limits
_SAVE_PART_LIMIT = 16000
_BASE_PART_LIMIT = 3000
_BASE_LIMIT = 400


class _NumericTableItem(QTableWidgetItem):
    """Table item that sorts numerically instead of lexicographically."""

    def __init__(self, value: int):
        super().__init__(str(value))
        self._value = value
        self.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

    def __lt__(self, other):
        if isinstance(other, _NumericTableItem):
            return self._value < other._value
        return super().__lt__(other)


def _decode_galactic_address(addr) -> str:
    """Decode NMS galactic address integer to readable coordinates.

    Format: planet:system:y:z:x (portal glyph order).
    Address encodes: bits 0-11=x, 12-19=y, 20-31=z, 32-35=system_index,
    36-47=system_body... but the exact layout varies. We extract what we can.
    """
    if isinstance(addr, str):
        try:
            addr = int(addr, 0)
        except (ValueError, TypeError):
            return str(addr)
    if not isinstance(addr, int) or addr == 0:
        return str(addr) if addr else "—"

    # NMS galactic address bit layout (from community research):
    # Bits 0-15:  SolarSystemIndex (system within region)
    # Bits 16-18: PlanetIndex (0-7)
    # Bits 19-30: VoxelX (12 bits, signed, +0x801 offset)
    # Bits 31-38: VoxelY (8 bits, signed, +0x81 offset)
    # Bits 39-50: VoxelZ (12 bits, signed, +0x801 offset)
    system = addr & 0xFFFF
    planet = (addr >> 16) & 0x7
    voxel_x = (addr >> 19) & 0xFFF
    voxel_y = (addr >> 31) & 0xFF
    voxel_z = (addr >> 39) & 0xFFF

    return f"Planet {planet}, System {system:04X}, Region ({voxel_x:03X}:{voxel_y:02X}:{voxel_z:03X})"


CHEST_KEYS = [
    ("Chest1Inventory", "Storage 1"),
    ("Chest2Inventory", "Storage 2"),
    ("Chest3Inventory", "Storage 3"),
    ("Chest4Inventory", "Storage 4"),
    ("Chest5Inventory", "Storage 5"),
    ("Chest6Inventory", "Storage 6"),
    ("Chest7Inventory", "Storage 7"),
    ("Chest8Inventory", "Storage 8"),
    ("Chest9Inventory", "Storage 9"),
    ("Chest10Inventory", "Storage 10"),
    ("ChestMagicInventory", "Magic Storage"),
    ("ChestMagic2Inventory", "Magic Storage 2"),
    ("CookingIngredientsInventory", "Cooking"),
    ("RocketLockerInventory", "Rocket Locker"),
]


class BasesTab(QWidget):
    def __init__(self):
        super().__init__()
        self._data = None
        self._bases = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Top: base selector + details
        top = QHBoxLayout()

        # Base selector
        selector = QWidget()
        sel_layout = QHBoxLayout(selector)
        sel_layout.setContentsMargins(0, 0, 0, 0)
        sel_layout.addWidget(QLabel("Base:"))
        self._base_combo = QComboBox()
        self._base_combo.setMinimumWidth(300)
        self._base_combo.currentIndexChanged.connect(self._on_base_selected)
        sel_layout.addWidget(self._base_combo)
        self._export_btn = QPushButton("Export Base")
        self._export_btn.clicked.connect(self._on_export)
        sel_layout.addWidget(self._export_btn)

        self._import_btn = QPushButton("Import Base")
        self._import_btn.clicked.connect(self._on_import)
        sel_layout.addWidget(self._import_btn)

        self._move_up_btn = QPushButton("▲")
        self._move_up_btn.setMaximumWidth(30)
        self._move_up_btn.setToolTip("Move base up (changes teleport menu order)")
        self._move_up_btn.clicked.connect(self._on_move_up)
        sel_layout.addWidget(self._move_up_btn)
        self._move_down_btn = QPushButton("▼")
        self._move_down_btn.setMaximumWidth(30)
        self._move_down_btn.setToolTip("Move base down (changes teleport menu order)")
        self._move_down_btn.clicked.connect(self._on_move_down)
        sel_layout.addWidget(self._move_down_btn)

        sel_layout.addStretch()
        top.addWidget(selector)

        layout.addLayout(top)

        # Base details
        details = QGroupBox("Base Details")
        det_layout = QFormLayout(details)
        self._name_label = QLabel("—")
        det_layout.addRow("Name:", self._name_label)
        self._type_label = QLabel("—")
        det_layout.addRow("Type:", self._type_label)
        self._address_label = QLabel("—")
        det_layout.addRow("Address:", self._address_label)
        self._parts_label = QLabel("—")
        det_layout.addRow("Parts:", self._parts_label)
        layout.addWidget(details)

        # Base part budget table
        budget_group = QGroupBox("Base Part Budget")
        budget_layout = QVBoxLayout(budget_group)

        self._total_parts_label = QLabel("—")
        self._total_parts_label.setStyleSheet("font-weight: bold;")
        budget_layout.addWidget(self._total_parts_label)

        self._budget_table = QTableWidget(0, 3)
        self._budget_table.setHorizontalHeaderLabels(["Base Name", "Parts", "Wires"])
        self._budget_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._budget_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self._budget_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._budget_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._budget_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._budget_table.setSortingEnabled(True)
        self._budget_table.setAlternatingRowColors(True)
        self._budget_table.currentCellChanged.connect(self._on_budget_row_clicked)
        budget_layout.addWidget(self._budget_table)

        layout.addWidget(budget_group)

        # Base library
        lib_group = QGroupBox("Base Library")
        lib_layout = QVBoxLayout(lib_group)
        self._library_list = QListWidget()
        self._library_list.setMaximumHeight(150)
        lib_layout.addWidget(self._library_list)

        lib_btn_layout = QHBoxLayout()
        self._lib_save_btn = QPushButton("Save Current")
        self._lib_save_btn.clicked.connect(self._on_save_to_library)
        lib_btn_layout.addWidget(self._lib_save_btn)
        self._lib_load_btn = QPushButton("Load/Swap")
        self._lib_load_btn.clicked.connect(self._on_load_from_library)
        lib_btn_layout.addWidget(self._lib_load_btn)
        self._lib_delete_btn = QPushButton("Delete")
        self._lib_delete_btn.clicked.connect(self._on_delete_from_library)
        lib_btn_layout.addWidget(self._lib_delete_btn)
        lib_layout.addLayout(lib_btn_layout)

        layout.addWidget(lib_group)

        # Storage chests (universal — not per-base)
        storage_label = QLabel("Global Storage (accessible from any base/freighter)")
        storage_label.setStyleSheet("color: #aaa; font-size: 11px; margin-top: 8px;")
        layout.addWidget(storage_label)

        chest_tabs = QTabWidget()
        self._chest_grids = {}
        for key, name in CHEST_KEYS:
            grid = InventoryGrid(name)
            self._chest_grids[key] = grid
            chest_tabs.addTab(grid, name)
        layout.addWidget(chest_tabs)

    def set_data(self, psd: dict):
        self._data = psd
        self._bases = psd.get("PersistentPlayerBases", [])

        self._base_combo.blockSignals(True)
        self._base_combo.clear()
        for i, base in enumerate(self._bases):
            name = base.get("Name", "")
            base_type = base.get("BaseType", {})
            type_str = ""
            if isinstance(base_type, dict):
                type_str = base_type.get("PersistentBaseTypes", "")
            if not name:
                name = type_str or f"Base {i + 1}"
            self._base_combo.addItem(f"{i + 1}. {name}")
        self._base_combo.blockSignals(False)

        # Populate budget table
        self._budget_table.setSortingEnabled(False)
        self._budget_table.setRowCount(len(self._bases))
        total_parts = 0
        total_wires = 0
        for row, base in enumerate(self._bases):
            name = base.get("Name", "")
            if not name:
                base_type = base.get("BaseType", {})
                if isinstance(base_type, dict):
                    name = base_type.get("PersistentBaseTypes", "")
                if not name:
                    name = f"Base {row + 1}"

            objects = base.get("Objects", [])
            part_count = len(objects) if isinstance(objects, list) else 0
            wire_count = sum(
                1 for o in (objects if isinstance(objects, list) else [])
                if o.get("ObjectID", "").lstrip("^") in _WIRE_IDS
            )
            total_parts += part_count
            total_wires += wire_count

            name_item = QTableWidgetItem(name)
            self._budget_table.setItem(row, 0, name_item)
            self._budget_table.setItem(row, 1, _NumericTableItem(part_count))
            self._budget_table.setItem(row, 2, _NumericTableItem(wire_count))

        self._budget_table.setSortingEnabled(True)

        limit_pct = total_parts / _SAVE_PART_LIMIT * 100
        self._total_parts_label.setText(
            f"Total: {total_parts:,} / {_SAVE_PART_LIMIT:,} parts ({limit_pct:.1f}%), "
            f"{total_wires:,} wires, "
            f"{len(self._bases)} / {_BASE_LIMIT} bases"
        )

        if self._bases:
            self._base_combo.setCurrentIndex(0)
            self._on_base_selected(0)

        self._refresh_library()

        # Populate chest inventories (these are global, not per-base)
        for key, name in CHEST_KEYS:
            inv = psd.get(key, {})
            self._chest_grids[key].set_inventory(inv)

    def _on_base_selected(self, index):
        if index < 0 or index >= len(self._bases):
            return
        base = self._bases[index]

        name = base.get("Name", "")
        self._name_label.setText(name if name else "(Unnamed)")

        base_type = base.get("BaseType", {})
        type_str = ""
        if isinstance(base_type, dict):
            type_str = base_type.get("PersistentBaseTypes", "")
        self._type_label.setText(type_str if type_str else "—")

        # Address — decode galactic coordinates
        address = base.get("GalacticAddress", base.get("Position", ""))
        self._address_label.setText(_decode_galactic_address(address))

        # Parts count
        objects = base.get("Objects", [])
        part_count = len(objects) if isinstance(objects, list) else 0
        wire_count = sum(
            1 for o in (objects if isinstance(objects, list) else [])
            if o.get("ObjectID", "").lstrip("^") in _WIRE_IDS
        )
        limit_pct = f" ({part_count / _BASE_PART_LIMIT * 100:.0f}% of {_BASE_PART_LIMIT:,} limit)" if part_count > 0 else ""
        self._parts_label.setText(f"{part_count:,} parts, {wire_count:,} wires{limit_pct}")

    def _on_budget_row_clicked(self, row, _col, _prev_row, _prev_col):
        """Sync budget table click with base selector combo."""
        if row < 0:
            return
        # The budget table rows may be sorted, so find the base name and match
        name_item = self._budget_table.item(row, 0)
        if name_item is None:
            return
        clicked_name = name_item.text()
        for i in range(self._base_combo.count()):
            combo_text = self._base_combo.itemText(i)
            # Combo text is "N. BaseName"
            if combo_text.split(". ", 1)[-1] == clicked_name:
                self._base_combo.setCurrentIndex(i)
                break

    def _on_move_up(self):
        idx = self._base_combo.currentIndex()
        if idx <= 0 or idx >= len(self._bases):
            return
        self._bases[idx], self._bases[idx - 1] = self._bases[idx - 1], self._bases[idx]
        self.set_data(self._data)
        self._base_combo.setCurrentIndex(idx - 1)

    def _on_move_down(self):
        idx = self._base_combo.currentIndex()
        if idx < 0 or idx >= len(self._bases) - 1:
            return
        self._bases[idx], self._bases[idx + 1] = self._bases[idx + 1], self._bases[idx]
        self.set_data(self._data)
        self._base_combo.setCurrentIndex(idx + 1)

    def _refresh_library(self):
        """Repopulate library list from disk."""
        self._library_list.clear()
        self._library_entries = []
        lib_dir = _base_library_dir()
        for path, name, part_count in _scan_library(lib_dir):
            self._library_entries.append(path)
            self._library_list.addItem(f"{name} ({part_count} parts)")

    def _on_save_to_library(self):
        """Save current base to library directory."""
        index = self._base_combo.currentIndex()
        data = self._get_export_data(index)
        if not data:
            return
        name = data.get("Name", "base") or "base"
        safe_name = re.sub(r"[^\w\-]", "_", name).strip("_")[:50]
        timestamp = int(time.time())
        filename = f"{safe_name}_{timestamp}.json"
        lib_dir = _base_library_dir()
        (lib_dir / filename).write_text(json.dumps(data, indent=2))
        self._refresh_library()

    def _on_load_from_library(self):
        """Replace current base Objects with library entry's Objects."""
        row = self._library_list.currentRow()
        if row < 0 or row >= len(self._library_entries):
            return
        lib_path = self._library_entries[row]
        try:
            lib_data = json.loads(lib_path.read_text())
        except (json.JSONDecodeError, OSError):
            return
        index = self._base_combo.currentIndex()
        if index < 0 or index >= len(self._bases):
            return
        self._bases[index]["Objects"] = lib_data.get("Objects", [])
        self.set_data(self._data)

    def _on_delete_from_library(self):
        """Delete selected library entry from disk."""
        row = self._library_list.currentRow()
        if row < 0 or row >= len(self._library_entries):
            return
        lib_path = self._library_entries[row]
        try:
            lib_path.unlink()
        except OSError:
            pass
        self._refresh_library()

    def _get_export_data(self, index: int) -> dict:
        """Get exportable data for base at given index."""
        if index < 0 or index >= len(self._bases):
            return {}
        base = self._bases[index]
        return {
            "Name": base.get("Name", ""),
            "BaseType": base.get("BaseType", {}),
            "GalacticAddress": base.get("GalacticAddress", 0),
            "Objects": base.get("Objects", []),
        }

    def _import_base_data(self, base_data: dict):
        """Import a base dict into the player's base list."""
        if self._data is None:
            return
        bases = self._data.get("PersistentPlayerBases", [])
        bases.append(base_data)
        self._data["PersistentPlayerBases"] = bases
        # Refresh UI
        self.set_data(self._data)

    def _on_export(self):
        """Export the currently selected base to a JSON file."""
        index = self._base_combo.currentIndex()
        data = self._get_export_data(index)
        if not data:
            return
        name = data.get("Name", "base") or "base"
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Base", f"{name}.json", "JSON files (*.json)"
        )
        if path:
            with open(path, "w") as f:
                json.dump(data, f, indent=2)

    def _on_import(self):
        """Import a base from a JSON file."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Base", "", "JSON files (*.json)"
        )
        if path:
            with open(path) as f:
                data = json.load(f)
            if isinstance(data, dict) and "Objects" in data:
                self._import_base_data(data)
