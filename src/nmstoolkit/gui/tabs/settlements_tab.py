"""Settlements editor tab."""

from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from nmstoolkit.gui.tabs.bases_tab import _decode_galactic_address
from nmstoolkit.gui.widgets.inventory_grid import get_item_display_name
from nmstoolkit.gui.widgets.stat_editor import StatEditor

# Stats array indices (V2 format) — Population is stored separately
_STATS_ARRAY_NAMES = [
    "Happiness", "Productivity", "Debt", "Upkeep",
    "Crime", "Health",
]

# All stat names including Population (which comes from its own field)
_STAT_NAMES = ["Population"] + _STATS_ARRAY_NAMES


class SettlementsTab(QWidget):
    def __init__(self):
        super().__init__()
        self._data = None
        self._settlements = []
        self._current_index = -1
        self._prod_rows = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Settlement selector
        sel_bar = QHBoxLayout()
        sel_bar.addWidget(QLabel("Settlement:"))
        self._combo = QComboBox()
        self._combo.setMinimumWidth(300)
        self._combo.currentIndexChanged.connect(self._on_selected)
        sel_bar.addWidget(self._combo)
        sel_bar.addStretch()
        layout.addLayout(sel_bar)

        details = QGroupBox("Settlement Details")
        det_layout = QFormLayout(details)

        self._name_label = QLabel("—")
        det_layout.addRow("Name:", self._name_label)
        self._owner_label = QLabel("—")
        det_layout.addRow("Owner:", self._owner_label)

        self._race_label = QLabel("—")
        det_layout.addRow("Race:", self._race_label)
        self._address_label = QLabel("—")
        det_layout.addRow("Address:", self._address_label)
        self._buildings_label = QLabel("—")
        det_layout.addRow("Buildings:", self._buildings_label)

        self._stat_editors = {}
        for name in _STAT_NAMES:
            editor = StatEditor(name, -999999, 999999)
            det_layout.addRow(f"{name}:", editor)
            self._stat_editors[name] = editor

        # Connect write-back signals
        self._stat_editors["Population"].value_changed.connect(
            lambda val: self._on_stat_changed("Population", val)
        )
        for i, name in enumerate(_STATS_ARRAY_NAMES):
            self._stat_editors[name].value_changed.connect(
                lambda val, idx=i, n=name: self._on_stat_changed(n, val)
            )

        self._perks_label = QLabel("—")
        self._perks_label.setWordWrap(True)
        det_layout.addRow("Perks:", self._perks_label)

        self._judgement_label = QLabel("—")
        det_layout.addRow("Pending Judgement:", self._judgement_label)

        layout.addWidget(details)

        # Production Output group
        self._prod_group = QGroupBox("Production Output")
        self._prod_layout = QVBoxLayout(self._prod_group)
        layout.addWidget(self._prod_group)

        layout.addStretch()

    def set_data(self, psd: dict):
        self._data = psd
        self._settlements = self._find_owned_settlements(psd)
        self._current_index = -1

        self._combo.blockSignals(True)
        self._combo.clear()
        if not self._settlements:
            self._combo.addItem("No owned settlements found")
        else:
            for i, s in enumerate(self._settlements):
                name = s.get("Name", "") or f"(Settlement {i + 1})"
                self._combo.addItem(f"{i + 1}. {name}")
        self._combo.blockSignals(False)

        if self._settlements:
            self._combo.setCurrentIndex(0)
            self._on_selected(0)
        else:
            self._clear_details()

    def _current_settlement(self):
        if self._current_index < 0 or self._current_index >= len(self._settlements):
            return None
        return self._settlements[self._current_index]

    def _on_selected(self, index):
        if index < 0 or index >= len(self._settlements):
            self._current_index = -1
            self._clear_details()
            return
        self._current_index = index
        s = self._settlements[index]

        name = s.get("Name", "")
        self._name_label.setText(name if name else "(Unnamed)")
        self._owner_label.setText(s.get("Owner", {}).get("LID", "—") if isinstance(s.get("Owner"), dict) else str(s.get("Owner", "—")))

        # Race
        race = s.get("Race", {})
        if isinstance(race, dict):
            self._race_label.setText(race.get("AlienRace", "—"))
        else:
            self._race_label.setText(str(race) if race else "—")

        # Galactic address
        addr = s.get("UniverseAddress", 0)
        self._address_label.setText(_decode_galactic_address(addr))

        # Building count
        building_states = s.get("BuildingStates", [])
        if isinstance(building_states, list):
            built = sum(1 for b in building_states if b)
            total = len(building_states)
            self._buildings_label.setText(f"{built} / {total} slots built")
        else:
            self._buildings_label.setText("—")

        # Population is a separate field
        pop = s.get("Population", 0)
        self._stat_editors["Population"].set_value(pop if isinstance(pop, int) else 0)

        # Stats array: indices map to _STATS_ARRAY_NAMES
        stats = s.get("Stats", [])
        if isinstance(stats, list):
            for i, stat_name in enumerate(_STATS_ARRAY_NAMES):
                # Stats[0] is unknown/unused, Stats[1] = Happiness, etc.
                # Based on real data: index 1=Happiness, 2=Productivity, 3=Debt, 4=Upkeep, 5=Crime, 6=Health
                stat_idx = i + 1
                val = stats[stat_idx] if stat_idx < len(stats) else 0
                self._stat_editors[stat_name].set_value(val if isinstance(val, int) else 0)

        perks = s.get("Perks", [])
        if isinstance(perks, list) and perks:
            perk_names = [str(p) for p in perks if p]
            self._perks_label.setText(", ".join(perk_names) if perk_names else "None")
        else:
            self._perks_label.setText("None")

        judgement = s.get("PendingJudgementType", {})
        if isinstance(judgement, dict):
            jt = judgement.get("SettlementJudgementType", "None")
        else:
            jt = str(judgement) if judgement else "None"
        self._judgement_label.setText(jt)

        # Production output
        self._populate_production(s)

    def _populate_production(self, settlement: dict):
        """Populate production output editors from settlement ProductionState."""
        # Clear existing production rows
        self._prod_rows = []
        while self._prod_layout.count():
            child = self._prod_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                while child.layout().count():
                    sub = child.layout().takeAt(0)
                    if sub.widget():
                        sub.widget().deleteLater()

        production = settlement.get("ProductionState", [])
        if not isinstance(production, list):
            return

        for i, entry in enumerate(production):
            if not isinstance(entry, dict):
                continue

            row_data = {}

            # Item name (read-only)
            element_id = entry.get("ElementId", "")
            item_name = get_item_display_name(element_id) if element_id else "Unknown"
            item_label = QLabel(f"{item_name} ({element_id})" if element_id else "Empty")
            item_label.setStyleSheet("font-weight: bold;")

            # Amount
            amount_spin = StatEditor("Amount", 0, 99999)
            amount_spin.set_value(entry.get("Amount", 0))
            amount_spin.value_changed.connect(
                lambda val, idx=i: self._on_production_changed(idx, "Amount", val)
            )
            row_data["amount"] = amount_spin

            # Cap
            cap_spin = StatEditor("Cap", 0, 99999)
            cap_spin.set_value(entry.get("Cap", 0))
            cap_spin.value_changed.connect(
                lambda val, idx=i: self._on_production_changed(idx, "Cap", val)
            )
            row_data["cap"] = cap_spin

            # Rate multiplier
            rate_spin = QDoubleSpinBox()
            rate_spin.setRange(0.00, 10.00)
            rate_spin.setSingleStep(0.01)
            rate_spin.setDecimals(2)
            rate_spin.setValue(entry.get("RateMultiplier", 0.0))
            rate_spin.valueChanged.connect(
                lambda val, idx=i: self._on_production_changed(idx, "RateMultiplier", val)
            )
            row_data["rate"] = rate_spin

            # Layout for this production line
            row_layout = QFormLayout()
            row_layout.addRow(f"Line {i + 1}:", item_label)
            row_layout.addRow("Amount:", amount_spin)
            row_layout.addRow("Cap:", cap_spin)
            row_layout.addRow("Rate:", rate_spin)

            container = QWidget()
            container.setLayout(row_layout)
            self._prod_layout.addWidget(container)
            self._prod_rows.append(row_data)

    def _on_production_changed(self, index: int, field: str, value):
        """Write production field changes back to settlement data."""
        s = self._current_settlement()
        if s is None:
            return
        production = s.get("ProductionState", [])
        if index < len(production) and isinstance(production[index], dict):
            production[index][field] = value

    def _on_stat_changed(self, stat_name, value):
        """Write stat changes back to the settlement data dict."""
        s = self._current_settlement()
        if s is None:
            return
        if stat_name == "Population":
            s["Population"] = value
        else:
            stats = s.get("Stats", [])
            idx = _STATS_ARRAY_NAMES.index(stat_name) + 1  # offset by 1 (Stats[0] is unused)
            while len(stats) <= idx:
                stats.append(0)
            stats[idx] = value
            s["Stats"] = stats

    def _clear_details(self):
        self._name_label.setText("No settlement found")
        self._owner_label.setText("—")
        self._race_label.setText("—")
        self._address_label.setText("—")
        self._buildings_label.setText("—")
        for editor in self._stat_editors.values():
            editor.set_value(0)
        self._perks_label.setText("—")
        self._judgement_label.setText("—")
        self._prod_rows = []
        while self._prod_layout.count():
            child = self._prod_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    @staticmethod
    def _find_owned_settlements(psd: dict) -> list:
        """Find player-owned settlements by matching SettlementLocalSaveData seeds.

        SettlementStatesV2 is a ring buffer of ALL visited settlements (100 slots).
        SettlementLocalSaveData contains seeds of settlements the player owns.
        Match seeds to find the player's actual settlements in the ring buffer.

        Falls back to active index if SettlementLocalSaveData is unavailable.
        """
        settlements = []
        states_v2 = psd.get("SettlementStatesV2")

        if states_v2 and isinstance(states_v2, list):
            # Primary: match via SettlementLocalSaveData seeds
            local_data = psd.get("SettlementLocalSaveData", [])
            if isinstance(local_data, list) and local_data:
                owned_seeds = set()
                for entry in local_data:
                    if isinstance(entry, dict):
                        seed = entry.get("Seed", "")
                        if seed:
                            owned_seeds.add(str(seed))

                if owned_seeds:
                    for state in states_v2:
                        if isinstance(state, dict):
                            sv = str(state.get("SeedValue", ""))
                            if sv and sv in owned_seeds:
                                settlements.append(state)

            # Fallback: use active index if no local save data
            if not settlements:
                active_idx = psd.get("SettlementStateRingBufferIndexV2", -1)
                if isinstance(active_idx, int) and 0 <= active_idx < len(states_v2):
                    entry = states_v2[active_idx]
                    if isinstance(entry, dict) and entry.get("Name"):
                        settlements.append(entry)

        # V1 fallback
        if not settlements:
            ring = psd.get("SettlementStateRingBuffer", [])
            v1_idx = psd.get("SettlementStateRingBufferIndex", -1)
            if isinstance(ring, list) and isinstance(v1_idx, int) and 0 <= v1_idx < len(ring):
                entry = ring[v1_idx]
                if isinstance(entry, dict):
                    settlements.append(entry)

        return settlements
