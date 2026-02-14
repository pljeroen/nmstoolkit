"""Bases & Storage editor tab."""

from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from nmstoolkit.gui.widgets.inventory_grid import InventoryGrid


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
        self._total_parts_label = QLabel("—")
        det_layout.addRow("Total (all bases):", self._total_parts_label)
        layout.addWidget(details)

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

        # Compute total parts across all bases
        total_parts = 0
        for base in self._bases:
            objects = base.get("Objects", [])
            if isinstance(objects, list):
                total_parts += len(objects)
        # NMS save limit is ~16,000 base parts total (across all bases)
        limit_pct = f" ({total_parts / 16000 * 100:.1f}% of ~16K limit)" if total_parts > 0 else ""
        self._total_parts_label.setText(f"{total_parts:,} parts{limit_pct}")

        if self._bases:
            self._base_combo.setCurrentIndex(0)
            self._on_base_selected(0)

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
        self._parts_label.setText(str(len(objects)) if isinstance(objects, list) else "—")
