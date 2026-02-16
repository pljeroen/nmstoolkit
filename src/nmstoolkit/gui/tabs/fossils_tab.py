"""Fossils editor tab — aggregates fossil pieces and displays across inventories and bases."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

# Fossil item ID prefixes — pieces found in inventories
_FOSSIL_PIECE_PREFIXES = ("FOS_", "PROC_FOSS", "BLD_SKULL")

# Fossil base object prefixes — assembled displays placed in bases
_FOSSIL_BASE_PREFIXES = ("FOS_", "BLD_SKULL")

# Inventory keys to scan for fossil items
_INVENTORY_KEYS = [
    ("Inventory", "Exosuit"),
    ("Inventory_Cargo", "Exosuit Cargo"),
    ("FreighterInventory", "Freighter"),
    ("FreighterInventory_Cargo", "Freighter Cargo"),
] + [
    (f"Chest{i}Inventory", f"Storage {i}") for i in range(1, 11)
] + [
    ("ChestMagicInventory", "Magic Storage"),
    ("ChestMagic2Inventory", "Magic Storage 2"),
]

# Display-friendly names for fossil categories
_FOSSIL_CATEGORIES = {
    "FOS_QUAD": "Quadruped",
    "FOS_BI": "Biped",
    "FOS_WORM": "Reptilian",
    "FOS_BIRD": "Avian",
    "FOS_GRUN": "Protoform",
    "FOS_SKULL": "Skull",
    "FOS_LIMBS": "Limbs",
    "FOS_TAIL": "Tail",
    "FOS_BODY": "Body",
    "BLD_SKULL": "Titanic Trophy",
    "PROC_FOSS": "Fossil Sample",
}


def is_fossil_item(item_id: str) -> bool:
    """Check if an item ID represents a fossil piece or fossil product.

    Excludes food items derived from fossils (FOOD_R_FOSSIL etc.).
    """
    uid = item_id.lstrip("^").upper().split("#")[0]
    if uid.startswith("FOOD_"):
        return False
    return any(uid.startswith(p) for p in _FOSSIL_PIECE_PREFIXES)


def is_fossil_base_object(object_id: str) -> bool:
    """Check if a base object ID represents a fossil display."""
    uid = object_id.lstrip("^").upper()
    return any(uid.startswith(p) for p in _FOSSIL_BASE_PREFIXES)


def _categorize_fossil(item_id: str) -> str:
    """Get a display category for a fossil item ID."""
    uid = item_id.lstrip("^").upper().split("#")[0]
    for prefix, name in _FOSSIL_CATEGORIES.items():
        if uid.startswith(prefix):
            return name
    return uid


_FOSSIL_PART_NAMES = {
    "BODY": "Body",
    "HEAD": "Head",
    "TAIL": "Tail",
    "LIMBS": "Limbs",
    "SKULL": "Skull",
    "SPINE": "Spine",
    "RIBS": "Ribs",
    "PELVIS": "Pelvis",
    "FEET": "Feet",
    "CLAWS": "Claws",
    "TEETH": "Teeth",
    "HORN": "Horn",
    "JAWS": "Jaws",
}


def friendly_fossil_name(item_id: str) -> str:
    """Convert a raw fossil ID to a friendly display name.

    E.g. FOS_BI_BODY_AC → 'Biped Body (AC)'
         PROC_FOSS#11125 → 'Fossil Sample #11125'
         BLD_SKULL → 'Titanic Trophy'
    """
    uid = item_id.lstrip("^").upper()
    # Handle procedural fossils
    if uid.startswith("PROC_FOSS"):
        suffix = item_id.split("#", 1)[1] if "#" in item_id else ""
        return f"Fossil Sample #{suffix}" if suffix else "Fossil Sample"
    if uid.startswith("BLD_SKULL"):
        return "Titanic Trophy"
    # FOS_<TYPE>_<PART>_<VARIANT> pattern
    parts = uid.split("_")
    if len(parts) >= 3 and parts[0] == "FOS":
        category = _FOSSIL_CATEGORIES.get(f"FOS_{parts[1]}", parts[1].title())
        part_name = _FOSSIL_PART_NAMES.get(parts[2], parts[2].title())
        variant = parts[3] if len(parts) > 3 else ""
        if variant:
            return f"{category} {part_name} ({variant})"
        return f"{category} {part_name}"
    return _categorize_fossil(item_id)


class FossilsTab(QWidget):
    """Tab showing fossil pieces across inventories and displays in bases."""

    def __init__(self) -> None:
        super().__init__()
        self._data = None
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)

        # Left: Fossil pieces in inventories
        pieces_group = QGroupBox("Fossil Pieces (Inventories)")
        pieces_layout = QVBoxLayout(pieces_group)
        self._pieces_label = QLabel("No save loaded")
        pieces_layout.addWidget(self._pieces_label)

        self._pieces_table = QTableWidget(0, 4)
        self._pieces_table.setHorizontalHeaderLabels(["Item", "Category", "Location", "Qty"])
        self._pieces_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._pieces_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self._pieces_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._pieces_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self._pieces_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._pieces_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        pieces_layout.addWidget(self._pieces_table)

        # Right: Fossil displays in bases
        displays_group = QGroupBox("Fossil Displays (Bases)")
        displays_layout = QVBoxLayout(displays_group)
        self._displays_label = QLabel("No save loaded")
        displays_layout.addWidget(self._displays_label)

        self._displays_table = QTableWidget(0, 3)
        self._displays_table.setHorizontalHeaderLabels(["Display", "Category", "Base"])
        self._displays_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._displays_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self._displays_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._displays_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._displays_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        displays_layout.addWidget(self._displays_table)

        layout.addWidget(pieces_group)
        layout.addWidget(displays_group)

    def set_data(self, psd: dict) -> None:
        """Load fossil data from player state data."""
        self._data = psd
        self._populate_pieces(psd)
        self._populate_displays(psd)

    def _populate_pieces(self, psd: dict) -> None:
        """Scan all inventories for fossil items."""
        rows = []
        for inv_key, inv_label in _INVENTORY_KEYS:
            inv = psd.get(inv_key, {})
            if not isinstance(inv, dict):
                continue
            for slot in inv.get("Slots", []):
                item_id = slot.get("Id", "")
                if item_id and is_fossil_item(item_id):
                    amount = slot.get("Amount", 0)
                    category = _categorize_fossil(item_id)
                    friendly = friendly_fossil_name(item_id)
                    rows.append((friendly, category, inv_label, amount))

        self._pieces_table.setRowCount(len(rows))
        for i, (item_id, category, location, amount) in enumerate(rows):
            self._pieces_table.setItem(i, 0, QTableWidgetItem(item_id))
            self._pieces_table.setItem(i, 1, QTableWidgetItem(category))
            self._pieces_table.setItem(i, 2, QTableWidgetItem(location))
            qty_item = QTableWidgetItem(str(amount))
            qty_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._pieces_table.setItem(i, 3, qty_item)

        self._pieces_label.setText(f"{len(rows)} fossil piece(s) found")

    def _populate_displays(self, psd: dict) -> None:
        """Scan all bases for fossil display objects."""
        rows = []
        bases = psd.get("PersistentPlayerBases", [])
        for base in bases:
            base_name = base.get("Name", "") or "Unnamed Base"
            for obj in base.get("Objects", []):
                object_id = obj.get("ObjectID", "")
                if object_id and is_fossil_base_object(object_id):
                    category = _categorize_fossil(object_id)
                    friendly = friendly_fossil_name(object_id)
                    rows.append((friendly, category, base_name))

        self._displays_table.setRowCount(len(rows))
        for i, (object_id, category, base_name) in enumerate(rows):
            self._displays_table.setItem(i, 0, QTableWidgetItem(object_id))
            self._displays_table.setItem(i, 1, QTableWidgetItem(category))
            self._displays_table.setItem(i, 2, QTableWidgetItem(base_name))

        self._displays_label.setText(f"{len(rows)} fossil display(s) placed")
