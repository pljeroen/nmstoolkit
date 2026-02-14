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

# Settlement Stats list indices (V2 format)
_STAT_NAMES = [
    "Population", "Happiness", "Productivity", "Debt", "Upkeep",
    "Crime", "Health",
]


class SettlementsTab(QWidget):
    def __init__(self):
        super().__init__()
        self._data = None
        self._settlements = []
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
            editor = StatEditor(name, 0, 999999)
            det_layout.addRow(f"{name}:", editor)
            self._stat_editors[name] = editor

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

    def _on_selected(self, index):
        if index < 0 or index >= len(self._settlements):
            self._clear_details()
            return
        s = self._settlements[index]

        name = s.get("Name", "")
        self._name_label.setText(name if name else "(Unnamed)")
        self._owner_label.setText(s.get("Owner", {}).get("LID", "—") if isinstance(s.get("Owner"), dict) else str(s.get("Owner", "—")))

        stats = s.get("Stats", [])
        if isinstance(stats, list):
            for i, stat_name in enumerate(_STAT_NAMES):
                val = stats[i] if i < len(stats) else 0
                self._stat_editors[stat_name].set_value(val if isinstance(val, int) else 0)
        elif isinstance(stats, dict):
            for stat_name in _STAT_NAMES:
                self._stat_editors[stat_name].set_value(stats.get(stat_name, 0))
        else:
            for stat_name in _STAT_NAMES:
                self._stat_editors[stat_name].set_value(s.get(stat_name, 0))

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

    def _clear_details(self):
        self._name_label.setText("No settlement found")
        self._owner_label.setText("—")
        for editor in self._stat_editors.values():
            editor.set_value(0)
        self._perks_label.setText("—")
        self._judgement_label.setText("—")

    @staticmethod
    def _find_owned_settlements(psd: dict) -> list:
        """Find player-owned settlement using the active index pointer.

        SettlementStatesV2 is a ring buffer of ALL visited settlements.
        Only the entry at the active index is the player's owned settlement.
        """
        settlements = []

        # V2 format: use active index to find the player's settlement
        states_v2 = psd.get("SettlementStatesV2")
        active_idx = psd.get("SettlementStateRingBufferIndexV2", -1)

        if states_v2 and isinstance(states_v2, list):
            if isinstance(active_idx, int) and 0 <= active_idx < len(states_v2):
                entry = states_v2[active_idx]
                if isinstance(entry, dict):
                    settlements.append(entry)

        # V1 fallback — use active index too
        if not settlements:
            ring = psd.get("SettlementStateRingBuffer", [])
            v1_idx = psd.get("SettlementStateRingBufferIndex", -1)
            if isinstance(ring, list) and isinstance(v1_idx, int) and 0 <= v1_idx < len(ring):
                entry = ring[v1_idx]
                if isinstance(entry, dict):
                    settlements.append(entry)

        return settlements
