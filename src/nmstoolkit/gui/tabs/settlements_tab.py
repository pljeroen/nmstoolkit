"""Settlements editor tab."""

from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

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
        for editor in self._stat_editors.values():
            editor.set_value(0)
        self._perks_label.setText("—")
        self._judgement_label.setText("—")

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
