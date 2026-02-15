"""Corvette editor tab — list completed corvettes + active draft, with inventory editing."""

from collections import Counter
from typing import Dict, List, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QStackedWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from nmstoolkit.gui.widgets.inventory_grid import InventoryGrid

# Module category mapping from ID prefix to human-readable category.
_MODULE_CATEGORIES = {
    "B_COK": "Cockpit",
    "B_HAB1": "Access Module",
    "B_HAB": "Habitation",
    "B_WNG": "Wing",
    "B_STR": "Structure",
    "B_CON_L": "Large Connector",
    "B_CON2": "Connector",
    "B_CON": "Connector",
    "B_TRU": "Thruster",
    "B_TUR": "Turret",
    "B_LND": "Landing Gear",
    "B_SHL": "Shell",
    "B_ALK": "Airlock",
    "B_GEN": "Generator",
    "B_DECO": "Decoration",
}

_INV_CLASSES = ["C", "B", "A", "S"]

_STAT_IDS = [
    ("^SHIP_DAMAGE", "Damage"),
    ("^SHIP_SHIELD", "Shield"),
    ("^SHIP_HYPERDRIVE", "Hyperdrive"),
    ("^SHIP_AGILE", "Maneuverability"),
]


def _categorize_modules(slots: List[Dict]) -> Dict[str, int]:
    """Count modules by category from slot data."""
    counts: Counter = Counter()
    for slot in slots:
        item_id = slot.get("Id", "").lstrip("^")
        category = _get_module_category(item_id)
        if category:
            counts[category] += 1
    return dict(counts)


def _get_module_category(item_id: str) -> str:
    """Get the category name for a module ID."""
    for prefix, category in _MODULE_CATEGORIES.items():
        if item_id.startswith(prefix):
            return category
    return "Unknown"


def _is_corvette_ship(ship: dict) -> bool:
    """Check if a ship is a corvette (BIGGS model)."""
    filename = ship.get("Resource", {}).get("Filename", "").upper()
    return "BIGGS" in filename


class CorvetteTab(QWidget):
    def __init__(self):
        super().__init__()
        self._data = None
        self._corvettes = []  # List of (index, ship_dict) for completed corvettes
        self._current_index = -1  # Index into self._corvettes, -1 = draft
        self._build_ui()

    def _build_ui(self):
        layout = QHBoxLayout(self)

        # Left: selector + details
        left = QWidget()
        left.setMaximumWidth(340)
        left_layout = QVBoxLayout(left)

        # Empty state label
        self._empty_label = QLabel(
            "No corvettes found — build a corvette in-game"
        )
        self._empty_label.setWordWrap(True)
        self._empty_label.setStyleSheet("color: #888; font-size: 13px; padding: 20px;")
        left_layout.addWidget(self._empty_label)

        # Corvette selector
        self._selector_group = QGroupBox("Select Corvette")
        sel_layout = QVBoxLayout(self._selector_group)
        self._corvette_combo = QComboBox()
        self._corvette_combo.currentIndexChanged.connect(self._on_corvette_selected)
        sel_layout.addWidget(self._corvette_combo)
        left_layout.addWidget(self._selector_group)

        # Details group (for completed corvettes)
        self._details_group = QGroupBox("Corvette Details")
        det_layout = QFormLayout(self._details_group)

        self._name_edit = QLineEdit()
        self._name_edit.editingFinished.connect(self._on_name_changed)
        det_layout.addRow("Name:", self._name_edit)

        self._class_combo = QComboBox()
        self._class_combo.addItems(_INV_CLASSES)
        self._class_combo.currentTextChanged.connect(self._on_class_changed)
        det_layout.addRow("Class:", self._class_combo)

        self._seed_label = QLabel("—")
        det_layout.addRow("Seed:", self._seed_label)

        left_layout.addWidget(self._details_group)

        # Base stats
        self._stats_group = QGroupBox("Base Stats")
        stats_layout = QFormLayout(self._stats_group)
        self._stat_spinners = {}
        for stat_id, label in _STAT_IDS:
            spinner = QDoubleSpinBox()
            spinner.setRange(0, 99999)
            spinner.setDecimals(1)
            spinner.valueChanged.connect(
                lambda val, sid=stat_id: self._on_stat_changed(sid, val)
            )
            stats_layout.addRow(f"{label}:", spinner)
            self._stat_spinners[stat_id] = spinner
        left_layout.addWidget(self._stats_group)

        # Draft details group (for active draft only)
        self._draft_group = QGroupBox("Draft Details")
        draft_layout = QFormLayout(self._draft_group)

        self._draft_ship_label = QLabel("—")
        draft_layout.addRow("Target Ship:", self._draft_ship_label)

        self._draft_seed_label = QLabel("—")
        draft_layout.addRow("Draft Seed:", self._draft_seed_label)

        self._draft_level_label = QLabel("—")
        draft_layout.addRow("Level:", self._draft_level_label)

        left_layout.addWidget(self._draft_group)

        # Module summary
        self._summary_group = QGroupBox("Module Summary")
        summary_layout = QVBoxLayout(self._summary_group)
        self._summary_label = QLabel("")
        self._summary_label.setWordWrap(True)
        summary_layout.addWidget(self._summary_label)
        left_layout.addWidget(self._summary_group)

        left_layout.addStretch()
        layout.addWidget(left)

        # Right: inventory sub-tabs
        self._inv_tabs = QTabWidget()
        self._inv_general = InventoryGrid("General")
        self._inv_tech = InventoryGrid("Technology")
        self._inv_cargo = InventoryGrid("Cargo")
        self._inv_draft = InventoryGrid("Build Grid")

        # Build Grid tab: stacked 2D/3D with toggle button
        self._draft_container = QWidget()
        draft_layout = QVBoxLayout(self._draft_container)
        draft_layout.setContentsMargins(0, 0, 0, 0)

        self._view_toggle_btn = QPushButton("Switch to 3D View")
        self._view_toggle_btn.setFixedHeight(28)
        self._view_toggle_btn.clicked.connect(self._toggle_draft_view)
        draft_layout.addWidget(self._view_toggle_btn)

        self._draft_stack = QStackedWidget()
        self._draft_stack.addWidget(self._inv_draft)  # index 0 = 2D

        # Lazy-create 3D view only when toggled (avoids GL init on startup)
        self._3d_view = None
        self._3d_placeholder = QLabel("Loading 3D view...")
        self._3d_placeholder.setAlignment(Qt.AlignCenter)
        self._draft_stack.addWidget(self._3d_placeholder)  # index 1 = 3D placeholder

        draft_layout.addWidget(self._draft_stack)

        self._inv_tabs.addTab(self._inv_general, "General")
        self._inv_tabs.addTab(self._inv_tech, "Technology")
        self._inv_tabs.addTab(self._inv_cargo, "Cargo")
        self._inv_tabs.addTab(self._draft_container, "Build Grid")
        layout.addWidget(self._inv_tabs)

    def set_data(self, psd: dict):
        self._data = psd
        self._corvettes = []

        # Find completed corvettes in ShipOwnership
        ships = psd.get("ShipOwnership", [])
        for i, ship in enumerate(ships):
            if _is_corvette_ship(ship):
                self._corvettes.append((i, ship))

        # Check for active draft
        draft_inv = psd.get("CorvetteStorageInventory")
        has_draft = draft_inv is not None and bool(draft_inv.get("Slots"))
        has_any = bool(self._corvettes) or has_draft

        self._empty_label.setVisible(not has_any)
        self._selector_group.setVisible(has_any)
        self._details_group.setVisible(False)
        self._stats_group.setVisible(False)
        self._draft_group.setVisible(False)
        self._summary_group.setVisible(False)

        if not has_any:
            self._inv_general.set_inventory({})
            self._inv_tech.set_inventory({})
            self._inv_cargo.set_inventory({})
            self._inv_draft.set_inventory({})
            return

        # Populate dropdown
        self._corvette_combo.blockSignals(True)
        self._corvette_combo.clear()
        for ship_idx, ship in self._corvettes:
            name = ship.get("Name", "") or f"Corvette {ship_idx + 1}"
            inv_class = ship.get("Inventory", {}).get("Class", {}).get(
                "InventoryClass", "?"
            )
            self._corvette_combo.addItem(f"{name} ({inv_class})")
        if has_draft:
            draft_name = psd.get("CorvetteEditShipName", "") or "Active Draft"
            self._corvette_combo.addItem(f"[Draft] {draft_name}")
        self._corvette_combo.blockSignals(False)

        if self._corvette_combo.count() > 0:
            self._corvette_combo.setCurrentIndex(0)
            self._on_corvette_selected(0)

    def _toggle_draft_view(self):
        """Toggle between 2D and 3D views for the build grid."""
        current = self._draft_stack.currentIndex()
        if current == 0:
            # Switch to 3D
            if self._3d_view is None:
                try:
                    from nmstoolkit.gui.widgets.corvette_3d_view import Corvette3DView
                    self._3d_view = Corvette3DView()
                    self._draft_stack.removeWidget(self._3d_placeholder)
                    self._3d_placeholder.deleteLater()
                    self._3d_placeholder = None
                    self._draft_stack.addWidget(self._3d_view)
                except Exception as exc:
                    # OpenGL not available — show error and stay on 2D
                    if self._3d_placeholder is not None:
                        self._3d_placeholder.setText(
                            f"3D view unavailable: {exc}"
                        )
                    return
            # Feed current draft data to 3D view
            if self._data is not None:
                draft_inv = self._data.get("CorvetteStorageInventory", {})
                self._3d_view.set_modules(draft_inv)
            self._draft_stack.setCurrentIndex(1)
            self._view_toggle_btn.setText("Switch to 2D Grid")
        else:
            # Switch to 2D
            self._draft_stack.setCurrentIndex(0)
            self._view_toggle_btn.setText("Switch to 3D View")

    def _on_corvette_selected(self, index):
        if index < 0:
            return

        is_draft = index >= len(self._corvettes)

        if is_draft:
            self._current_index = -1
            self._show_draft()
        else:
            self._current_index = index
            self._show_completed(index)

    def _show_completed(self, combo_index: int):
        """Show a completed corvette's inventories and details."""
        ship_idx, ship = self._corvettes[combo_index]

        # Details
        self._details_group.setVisible(True)
        self._stats_group.setVisible(True)
        self._draft_group.setVisible(False)

        self._name_edit.blockSignals(True)
        self._name_edit.setText(ship.get("Name", ""))
        self._name_edit.blockSignals(False)

        inv = ship.get("Inventory", {})
        inv_class = inv.get("Class", {}).get("InventoryClass", "C")
        self._class_combo.blockSignals(True)
        idx = self._class_combo.findText(inv_class)
        self._class_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self._class_combo.blockSignals(False)

        self._seed_label.setText(str(ship.get("Seed", "—")))

        # Stats
        base_stats = inv.get("BaseStatValues", [])
        stats_by_id = {}
        for bs in base_stats:
            if isinstance(bs, dict):
                stats_by_id[bs.get("BaseStatID", "")] = bs.get("Value", 0)
        for stat_id, spinner in self._stat_spinners.items():
            spinner.blockSignals(True)
            spinner.setValue(stats_by_id.get(stat_id, 0))
            spinner.blockSignals(False)

        # Inventories
        self._inv_general.set_inventory(inv)
        self._inv_tech.set_inventory(ship.get("Inventory_TechOnly", {}))
        self._inv_cargo.set_inventory(ship.get("Inventory_Cargo", {}))
        self._inv_draft.set_inventory({})

        # Show General/Tech/Cargo tabs, hide Build Grid
        self._inv_tabs.setTabVisible(0, True)
        self._inv_tabs.setTabVisible(1, True)
        self._inv_tabs.setTabVisible(2, True)
        self._inv_tabs.setTabVisible(3, False)
        self._inv_tabs.setCurrentIndex(0)

        # Module summary from general inventory
        slots = inv.get("Slots", [])
        self._update_summary(slots)

    def _show_draft(self):
        """Show the active corvette draft."""
        psd = self._data
        draft_inv = psd.get("CorvetteStorageInventory", {})

        self._details_group.setVisible(False)
        self._stats_group.setVisible(False)
        self._draft_group.setVisible(True)

        # Draft details
        ship_idx = psd.get("CorvetteEditAssociatedShipIndex", -1)
        ships = psd.get("ShipOwnership", [])
        if 0 <= ship_idx < len(ships):
            ship = ships[ship_idx]
            ship_name = ship.get("Name", "") or f"Ship {ship_idx + 1}"
            self._draft_ship_label.setText(f"{ship_name} (slot {ship_idx + 1})")
        else:
            self._draft_ship_label.setText("—")

        self._draft_seed_label.setText(str(psd.get("CorvetteDraftShipSeed", 0)))
        layout_data = psd.get("CorvetteStorageLayout", {})
        self._draft_level_label.setText(str(layout_data.get("Level", "—")))

        # Hide General/Tech/Cargo, show Build Grid
        self._inv_tabs.setTabVisible(0, False)
        self._inv_tabs.setTabVisible(1, False)
        self._inv_tabs.setTabVisible(2, False)
        self._inv_tabs.setTabVisible(3, True)
        self._inv_tabs.setCurrentIndex(3)

        self._inv_draft.set_inventory(draft_inv)

        # Update 3D view if it exists
        if self._3d_view is not None:
            self._3d_view.set_modules(draft_inv)

        # Module summary from draft
        slots = draft_inv.get("Slots", [])
        self._update_summary(slots)

    def _update_summary(self, slots: list):
        """Update the module summary label from slot data."""
        if not slots:
            self._summary_group.setVisible(False)
            return
        self._summary_group.setVisible(True)
        counts = _categorize_modules(slots)
        summary_lines = []
        for category in sorted(counts.keys()):
            summary_lines.append(f"{category}: {counts[category]}")
        self._summary_label.setText("\n".join(summary_lines))

    def _current_ship(self) -> Optional[dict]:
        """Get the currently selected ship dict, or None for draft."""
        if self._current_index < 0 or self._current_index >= len(self._corvettes):
            return None
        return self._corvettes[self._current_index][1]

    def _on_name_changed(self):
        ship = self._current_ship()
        if ship is not None:
            ship["Name"] = self._name_edit.text()
            # Update combo text
            ship_idx = self._corvettes[self._current_index][0]
            inv_class = ship.get("Inventory", {}).get("Class", {}).get(
                "InventoryClass", "?"
            )
            name = self._name_edit.text() or f"Corvette {ship_idx + 1}"
            self._corvette_combo.setItemText(
                self._current_index, f"{name} ({inv_class})"
            )

    def _on_class_changed(self, text):
        ship = self._current_ship()
        if ship is None:
            return
        inv = ship.get("Inventory", {})
        cls = inv.get("Class", {})
        if isinstance(cls, dict):
            cls["InventoryClass"] = text
        else:
            inv["Class"] = {"InventoryClass": text}
        # Update combo text
        ship_idx = self._corvettes[self._current_index][0]
        name = ship.get("Name", "") or f"Corvette {ship_idx + 1}"
        self._corvette_combo.setItemText(
            self._current_index, f"{name} ({text})"
        )

    def _on_stat_changed(self, stat_id, value):
        ship = self._current_ship()
        if ship is None:
            return
        inv = ship.get("Inventory", {})
        base_stats = inv.get("BaseStatValues", [])
        for bs in base_stats:
            if isinstance(bs, dict) and bs.get("BaseStatID") == stat_id:
                bs["Value"] = value
                return
        base_stats.append({"BaseStatID": stat_id, "Value": value})
        inv["BaseStatValues"] = base_stats
