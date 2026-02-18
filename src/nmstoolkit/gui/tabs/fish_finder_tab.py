"""Fish Finder tab — reference guide for fishing in NMS."""

import json

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from nmstoolkit.gui.widgets.inventory_grid import get_item_icon
from nmstoolkit.paths import resource_dir


def _load_items():
    data_path = resource_dir() / "items.json"
    if not data_path.exists():
        return []
    with open(data_path) as f:
        return json.load(f)


# Bait reference data — what each bait targets
_FISH_BAIT_INFO = [
    {"id": "^BAIT_BASIC", "name": "Creature Pellets", "condition": "Any", "notes": "General purpose bait for all creatures"},
    {"id": "^FISHBAIT_1", "name": "Mealworms", "condition": "Any", "notes": "Basic fishing bait, catches common fish"},
    {"id": "^FISHBAIT_2", "name": "Spicy Chum", "condition": "Any", "notes": "Attracts larger fish species"},
    {"id": "^FISHBAIT_3", "name": "Bionic Lure", "condition": "Any", "notes": "High-tech lure for rare species"},
    {"id": "^FISHBAIT_DAY", "name": "Dangling Orb", "condition": "Daytime", "notes": "Only attracts diurnal fish (day cycle)"},
    {"id": "^FISHBAIT_NIGHT", "name": "Shadow Lure", "condition": "Nighttime", "notes": "Only attracts nocturnal fish (night cycle)"},
    {"id": "^FISHBAIT_STORM", "name": "Magpulse Lure", "condition": "Storm", "notes": "Only attracts storm-active fish"},
]

# Fish creature types
_FISH_CREATURE_TYPES = [
    {"id": "^FISH", "name": "Fish", "biome": "All water biomes", "notes": "Standard fish, most common aquatic creature"},
    {"id": "^JELLYFISH", "name": "Jellyfish", "biome": "All water biomes", "notes": "Passive aquatic creature, often bioluminescent"},
    {"id": "^FIENDFISHBIG", "name": "Big Fiend Fish", "biome": "Hostile/Deep water", "notes": "Large aggressive aquatic predator"},
    {"id": "^FIENDFISHSMALL", "name": "Small Fiend Fish", "biome": "Hostile/Deep water", "notes": "Small aggressive aquatic predator"},
]

# Creature category IDs are not inventory item IDs, so map them to
# representative fish loot items that have real extracted icons.
_FISH_CREATURE_ICON_ID = {
    "^FISH": "^ANY_FISH",
    "^JELLYFISH": "^F_BOSS_JELLY",
    "^FIENDFISHBIG": "^FIENDCORE",
    "^FIENDFISHSMALL": "^FIENDCORE",
}

# Stat IDs related to fishing
_FISH_STAT_IDS = {
    "^FISH_KILLS": "Fish Caught",
    "^DISC_CRE_WATER": "Water Creatures Discovered",
    "^WATERSTORY_LORE": "Water Lore Collected",
}


class FishFinderTab(QWidget):
    def __init__(self):
        super().__init__()
        self._data = None
        self._all_items = _load_items()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Stats section
        stats_group = QGroupBox("Fishing Stats")
        stats_layout = QFormLayout(stats_group)
        self._fish_kills_label = QLabel("—")
        stats_layout.addRow("Fish Caught:", self._fish_kills_label)
        self._water_disc_label = QLabel("—")
        stats_layout.addRow("Water Creatures Discovered:", self._water_disc_label)
        self._water_lore_label = QLabel("—")
        stats_layout.addRow("Water Lore Collected:", self._water_lore_label)
        layout.addWidget(stats_group)

        # Two-column layout: bait guide + fish types
        mid = QHBoxLayout()

        # Bait guide
        bait_group = QGroupBox("Bait Guide")
        bait_layout = QVBoxLayout(bait_group)
        self._bait_table = QTableWidget()
        self._bait_table.setColumnCount(4)
        self._bait_table.setHorizontalHeaderLabels(["Bait", "Name", "Condition", "Notes"])
        self._bait_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self._bait_table.setAlternatingRowColors(True)
        self._bait_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._populate_bait_table()
        bait_layout.addWidget(self._bait_table)
        mid.addWidget(bait_group)

        # Fish creature types
        creatures_group = QGroupBox("Fish Creature Types")
        creatures_layout = QVBoxLayout(creatures_group)
        self._creatures_table = QTableWidget()
        self._creatures_table.setColumnCount(4)
        self._creatures_table.setHorizontalHeaderLabels(["Type", "Name", "Biome", "Notes"])
        self._creatures_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self._creatures_table.setAlternatingRowColors(True)
        self._creatures_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._populate_creatures_table()
        creatures_layout.addWidget(self._creatures_table)
        mid.addWidget(creatures_group)

        layout.addLayout(mid)

        # Fish items from game data
        items_group = QGroupBox("Fish & Fishing Items")
        items_layout = QVBoxLayout(items_group)
        self._fish_table = QTableWidget()
        self._fish_table.setColumnCount(4)
        self._fish_table.setHorizontalHeaderLabels(["ID", "Name", "Type", "Description"])
        self._fish_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self._fish_table.setAlternatingRowColors(True)
        self._fish_table.setSortingEnabled(True)
        self._fish_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._fish_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._populate_fish_table()
        items_layout.addWidget(self._fish_table)
        layout.addWidget(items_group)

    def _make_icon_item(self, item_id: str, display_text: str) -> QTableWidgetItem:
        """Create a table item with icon and ID tooltip."""
        twi = QTableWidgetItem(display_text)
        twi.setToolTip(item_id)
        icon_id = _FISH_CREATURE_ICON_ID.get(item_id, item_id)
        pixmap = get_item_icon(icon_id)
        if pixmap is not None:
            twi.setIcon(QIcon(pixmap))
        return twi

    def refresh_icons(self):
        """Rebuild fish tables so newly loaded icon providers are applied."""
        self._populate_bait_table()
        self._populate_creatures_table()
        self._populate_fish_table()

    def _populate_bait_table(self):
        self._bait_table.setRowCount(len(_FISH_BAIT_INFO))
        for row, bait in enumerate(_FISH_BAIT_INFO):
            self._bait_table.setItem(row, 0, self._make_icon_item(bait["id"], bait["name"]))
            self._bait_table.setItem(row, 1, QTableWidgetItem(bait["name"]))
            self._bait_table.setItem(row, 2, QTableWidgetItem(bait["condition"]))
            self._bait_table.setItem(row, 3, QTableWidgetItem(bait["notes"]))

    def _populate_creatures_table(self):
        self._creatures_table.setRowCount(len(_FISH_CREATURE_TYPES))
        for row, creature in enumerate(_FISH_CREATURE_TYPES):
            self._creatures_table.setItem(row, 0, self._make_icon_item(creature["id"], creature["name"]))
            self._creatures_table.setItem(row, 1, QTableWidgetItem(creature["name"]))
            self._creatures_table.setItem(row, 2, QTableWidgetItem(creature["biome"]))
            self._creatures_table.setItem(row, 3, QTableWidgetItem(creature["notes"]))

    def _populate_fish_table(self):
        fish_items = [
            i for i in self._all_items
            if any(x in i.get("id", "").upper() for x in ["FISH", "BAIT"])
            or "fish" in i.get("name", "").lower()
            or "fishing" in i.get("name", "").lower()
            or "angler" in i.get("name", "").lower()
        ]
        self._fish_table.setSortingEnabled(False)
        self._fish_table.setRowCount(len(fish_items))
        for row, item in enumerate(fish_items):
            item_id = item.get("id", "")
            self._fish_table.setItem(row, 0, self._make_icon_item(item_id, item.get("name", "") or item_id))
            self._fish_table.setItem(row, 1, QTableWidgetItem(item.get("name", "")))
            self._fish_table.setItem(row, 2, QTableWidgetItem(item.get("type", "")))
            desc = item.get("subtitle", "") or item.get("description", "")
            if len(desc) > 100:
                desc = desc[:100] + "..."
            self._fish_table.setItem(row, 3, QTableWidgetItem(desc))
        self._fish_table.setSortingEnabled(True)

    def set_data(self, psd: dict):
        self._data = psd
        # Extract fishing stats from GLOBAL_STATS
        stats_map = {}
        for stat_group in psd.get("Stats", []):
            if isinstance(stat_group, dict):
                for entry in stat_group.get("Stats", []):
                    if isinstance(entry, dict):
                        stat_id = entry.get("StatID", "")
                        if stat_id in _FISH_STAT_IDS:
                            stats_map[stat_id] = entry.get("IntValue", 0)

        self._fish_kills_label.setText(str(stats_map.get("^FISH_KILLS", 0)))
        self._water_disc_label.setText(str(stats_map.get("^DISC_CRE_WATER", 0)))
        self._water_lore_label.setText(str(stats_map.get("^WATERSTORY_LORE", 0)))
