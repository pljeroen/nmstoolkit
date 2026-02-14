"""Frigates editor tab — regular, biological, and corvette frigates."""

from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QVBoxLayout,
    QWidget,
)

from nmstoolkit.gui.widgets.stat_editor import StatEditor


_CLASS_NAMES = {
    "Combat": "Combat",
    "Diplomacy": "Trade",
    "Exploration": "Exploration",
    "Industrial": "Industrial",
    "Support": "Support",
    "DEEPSPACE": "Organic (Rare)",
    "DEEPSPACECOMMON": "Organic",
    "NORMANDY": "Normandy",
    "GHOSTSHIP": "Ghost",
}

_INV_CLASSES = ["C", "B", "A", "S"]

# Stats indices in the frigate Stats list
_STAT_LABELS = [
    "Combat", "Exploration", "Industrial", "Trade", "Mining",
]

# Known trait IDs (stripped of ^) for reference
_TRAIT_FRIENDLY = {
    # Regular frigate traits
    "TRADING_PRI": "Trading Primary",
    "COMBAT_PRI": "Combat Primary",
    "EXPLORE_PRI": "Exploration Primary",
    "INDUSTRY_PRI": "Industrial Primary",
    "MINING_PRI": "Mining Primary",
    "DIPLO_SEC": "Diplomacy Secondary",
    "COMBAT_SEC": "Combat Secondary",
    "EXPLORE_SEC": "Exploration Secondary",
    "INDUSTRY_SEC": "Industrial Secondary",
    "TRADING_SEC": "Trading Secondary",
    "MINING_SEC": "Mining Secondary",
    # Biological / Living frigate traits
    "LIVING_COM_BITTER": "Bitter Memories",
    "LIVING_COM_MUSCLE": "Muscular Tentacles",
    "LIVING_COM_TEETH": "Razor Teeth",
    "LIVING_COM_VENOM": "Venomous Spines",
    "LIVING_COM_AGGRO": "Aggressive Instincts",
    "LIVING_EXP_ECHO": "Echolocation",
    "LIVING_EXP_ANCIENT": "Ancient Knowledge",
    "LIVING_EXP_BIOLUM": "Bioluminescence",
    "LIVING_EXP_SENSOR": "Sensory Tendrils",
    "LIVING_EXP_DREAM": "Dream Navigation",
    "LIVING_MIN_SONG": "Seismic Song",
    "LIVING_MIN_BALEEN": "Baleen Plates",
    "LIVING_MIN_DIGEST": "Mineral Digestion",
    "LIVING_MIN_DRILL": "Bore Tentacles",
    "LIVING_TRA_MESMER": "Mesmerising Voice",
    "LIVING_TRA_PHEROM": "Pheromone Aura",
    "LIVING_TRA_EMPATH": "Empathic Bond",
    "LIVING_TRA_MIMIC": "Mimicry",
    "LIVING_FUEL_SLOW": "Slow Metabolism",
    "LIVING_FUEL_SKIM": "Reality Skimming",
    "LIVING_FUEL_PHOTO": "Photosynthetic Sails",
    "LIVING_FUEL_STORE": "Energy Reserves",
    "LIVING_SPE_WORM": "Wormhole Navigation",
    "LIVING_SPE_HOME": "Homing Instincts",
    "LIVING_SPE_PULSE": "Pulse Jet Organs",
    "LIVING_SPE_TENTA": "Tentacle Propulsion",
}

_BIOLOGICAL_CLASSES = {"DEEPSPACE", "DEEPSPACECOMMON", "GHOSTSHIP", "NORMANDY"}


def _categorize_frigate(frigate: dict) -> str:
    """Categorize a frigate as 'regular', 'biological', or 'special'."""
    fc = frigate.get("FrigateClass", {})
    fc_str = fc.get("FrigateClass", "") if isinstance(fc, dict) else str(fc)
    if fc_str in ("DEEPSPACE", "DEEPSPACECOMMON"):
        return "biological"
    if fc_str in ("GHOSTSHIP", "NORMANDY"):
        return "special"
    return "regular"


class FrigatesTab(QWidget):
    def __init__(self):
        super().__init__()
        self._data = None
        self._frigates = []
        self._current_index = -1
        self._build_ui()

    def _build_ui(self):
        layout = QHBoxLayout(self)

        # Left: frigate list
        left = QWidget()
        left.setMaximumWidth(260)
        left_layout = QVBoxLayout(left)
        self._list = QListWidget()
        self._list.currentRowChanged.connect(self._on_selected)
        left_layout.addWidget(self._list)
        layout.addWidget(left)

        # Right: details (editable)
        right = QWidget()
        right_layout = QVBoxLayout(right)

        details = QGroupBox("Frigate Details")
        det_layout = QFormLayout(details)

        self._name_edit = QLineEdit()
        self._name_edit.editingFinished.connect(self._on_name_changed)
        det_layout.addRow("Name:", self._name_edit)

        self._type_label = QLabel("—")
        det_layout.addRow("Type:", self._type_label)

        self._category_label = QLabel("—")
        det_layout.addRow("Category:", self._category_label)

        self._class_combo = QComboBox()
        self._class_combo.addItems(_INV_CLASSES)
        self._class_combo.currentTextChanged.connect(self._on_class_changed)
        det_layout.addRow("Class:", self._class_combo)

        self._race_label = QLabel("—")
        det_layout.addRow("Race:", self._race_label)

        self._expeditions_editor = StatEditor("Expeditions", 0, 999999)
        self._expeditions_editor.value_changed.connect(self._on_expeditions_changed)
        det_layout.addRow("Expeditions:", self._expeditions_editor)

        self._damaged_editor = StatEditor("Damaged", 0, 999999)
        self._damaged_editor.value_changed.connect(self._on_damaged_changed)
        det_layout.addRow("Times Damaged:", self._damaged_editor)

        right_layout.addWidget(details)

        # Stats (editable)
        stats_group = QGroupBox("Stats")
        stats_layout = QFormLayout(stats_group)
        self._stat_editors = []
        for name in _STAT_LABELS:
            editor = StatEditor(name, 0, 999999)
            editor.value_changed.connect(
                lambda val, idx=len(self._stat_editors): self._on_stat_changed(idx, val)
            )
            stats_layout.addRow(f"{name}:", editor)
            self._stat_editors.append(editor)
        right_layout.addWidget(stats_group)

        # Traits (display with friendly names)
        traits_group = QGroupBox("Traits")
        traits_layout = QVBoxLayout(traits_group)
        self._traits_label = QLabel("—")
        self._traits_label.setWordWrap(True)
        traits_layout.addWidget(self._traits_label)
        right_layout.addWidget(traits_group)

        right_layout.addStretch()
        layout.addWidget(right)

    def set_data(self, psd: dict):
        self._data = psd
        self._frigates = psd.get("FleetFrigates", [])
        self._current_index = -1
        self._list.clear()
        for i, frigate in enumerate(self._frigates):
            name = frigate.get("CustomName", "") or f"Frigate {i + 1}"
            fc = frigate.get("FrigateClass", {})
            fc_str = fc.get("FrigateClass", "?") if isinstance(fc, dict) else str(fc)
            fc_display = _CLASS_NAMES.get(fc_str, fc_str)
            inv_class = frigate.get("InventoryClass", {})
            class_str = inv_class.get("InventoryClass", "?") if isinstance(inv_class, dict) else str(inv_class)
            category = _categorize_frigate(frigate)
            prefix = ""
            if category == "biological":
                prefix = "[Bio] "
            elif category == "special":
                prefix = "[Special] "
            self._list.addItem(f"{prefix}{name} ({fc_display} {class_str})")
        if self._frigates:
            self._list.setCurrentRow(0)

    def _on_selected(self, index):
        if index < 0 or index >= len(self._frigates):
            self._current_index = -1
            return
        self._current_index = index
        frigate = self._frigates[index]

        # Name
        name = frigate.get("CustomName", "")
        self._name_edit.blockSignals(True)
        self._name_edit.setText(name)
        self._name_edit.blockSignals(False)

        # Type
        fc = frigate.get("FrigateClass", {})
        fc_str = fc.get("FrigateClass", "—") if isinstance(fc, dict) else str(fc)
        self._type_label.setText(_CLASS_NAMES.get(fc_str, fc_str))

        # Category
        category = _categorize_frigate(frigate)
        category_display = {
            "regular": "Regular Frigate",
            "biological": "Organic / Living Frigate",
            "special": "Special Frigate",
        }
        self._category_label.setText(category_display.get(category, category))

        # Class
        inv_class = frigate.get("InventoryClass", {})
        class_str = inv_class.get("InventoryClass", "C") if isinstance(inv_class, dict) else "C"
        self._class_combo.blockSignals(True)
        idx = self._class_combo.findText(class_str)
        self._class_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self._class_combo.blockSignals(False)

        # Race
        race = frigate.get("Race", {})
        race_str = race.get("AlienRace", "—") if isinstance(race, dict) else str(race)
        self._race_label.setText(race_str)

        # Expeditions / Damaged
        self._expeditions_editor.set_value(frigate.get("TotalNumberOfExpeditions", 0))
        self._damaged_editor.set_value(frigate.get("NumberOfTimesDamaged", 0))

        # Stats (list of ints)
        stats = frigate.get("Stats", [])
        if isinstance(stats, list):
            for i, editor in enumerate(self._stat_editors):
                val = stats[i] if i < len(stats) else 0
                editor.set_value(val)
        else:
            for editor in self._stat_editors:
                editor.set_value(0)

        # Traits
        traits = frigate.get("TraitIDs", [])
        active_traits = []
        for t in traits:
            if isinstance(t, str) and t.strip("^"):
                raw = t.lstrip("^")
                friendly = _TRAIT_FRIENDLY.get(raw, raw)
                active_traits.append(friendly)
        self._traits_label.setText(", ".join(active_traits) if active_traits else "None")

    def _current_frigate(self):
        if self._current_index < 0 or self._current_index >= len(self._frigates):
            return None
        return self._frigates[self._current_index]

    def _on_name_changed(self):
        frigate = self._current_frigate()
        if frigate is None:
            return
        frigate["CustomName"] = self._name_edit.text()
        # Update list item
        i = self._current_index
        name = frigate.get("CustomName", "") or f"Frigate {i + 1}"
        fc = frigate.get("FrigateClass", {})
        fc_str = fc.get("FrigateClass", "?") if isinstance(fc, dict) else str(fc)
        fc_display = _CLASS_NAMES.get(fc_str, fc_str)
        inv_class = frigate.get("InventoryClass", {})
        class_str = inv_class.get("InventoryClass", "?") if isinstance(inv_class, dict) else str(inv_class)
        category = _categorize_frigate(frigate)
        prefix = ""
        if category == "biological":
            prefix = "[Bio] "
        elif category == "special":
            prefix = "[Special] "
        self._list.item(i).setText(f"{prefix}{name} ({fc_display} {class_str})")

    def _on_class_changed(self, text):
        frigate = self._current_frigate()
        if frigate is None:
            return
        inv_class = frigate.get("InventoryClass", {})
        if isinstance(inv_class, dict):
            inv_class["InventoryClass"] = text
        else:
            frigate["InventoryClass"] = {"InventoryClass": text}

    def _on_expeditions_changed(self, val):
        frigate = self._current_frigate()
        if frigate is not None:
            frigate["TotalNumberOfExpeditions"] = val

    def _on_damaged_changed(self, val):
        frigate = self._current_frigate()
        if frigate is not None:
            frigate["NumberOfTimesDamaged"] = val

    def _on_stat_changed(self, stat_index, value):
        frigate = self._current_frigate()
        if frigate is None:
            return
        stats = frigate.get("Stats", [])
        if isinstance(stats, list):
            while len(stats) <= stat_index:
                stats.append(0)
            stats[stat_index] = value
            frigate["Stats"] = stats
