"""Settlements editor tab."""

import json
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from nmstoolkit.core.game_catalogue import GameCatalogue
from nmstoolkit.gui.preview_support import (
    PreviewLoadThread,
    configure_preview_view,
    load_template_preview_meshes,
    resolve_settlement_scene,
)
from nmstoolkit.gui.tabs.bases_tab import _decode_galactic_address
from nmstoolkit.gui.widgets.inventory_grid import get_item_display_name
from nmstoolkit.gui.widgets.stat_editor import StatEditor
from nmstoolkit.paths import cache_icons_dir, resource_dir

_DATA_DIR = resource_dir()


def _load_perk_data():
    """Load settlement perk definitions from settlements.json."""
    path = _DATA_DIR / "settlements.json"
    if not path.exists():
        return {}
    with open(path) as f:
        data = json.load(f)
    return {entry["id"]: entry for entry in data if isinstance(entry, dict) and "id" in entry}


_PERK_DATA = _load_perk_data()


def _load_output_options() -> list[tuple[str, str]]:
    """Load settlement output options from cached game data.

    Uses Tradeable products as the canonical pool. Current settlement output IDs are
    always preserved in the combo even if they fall outside this pool.
    """
    options: dict[str, str] = {}

    cat_path = cache_icons_dir() / "game_catalogue.json"
    if cat_path.exists():
        try:
            cat = GameCatalogue.from_json(cat_path.read_text(encoding="utf-8"))
            for item in cat.products:
                if str(item.get("type", "")) != "Tradeable":
                    continue
                raw_id = str(item.get("id", "")).strip()
                if not raw_id:
                    continue
                item_id = raw_id if raw_id.startswith("^") else f"^{raw_id}"
                label = item.get("display_name") or item.get("name") or get_item_display_name(item_id)
                options[item_id] = str(label)
        except Exception:
            pass

    if not options:
        items_path = _DATA_DIR / "items.json"
        if items_path.exists():
            with open(items_path, "r", encoding="utf-8") as f:
                items = json.load(f)
            for item in items:
                if item.get("type") != "product":
                    continue
                # legacy fallback: keep known settlement/trade-like families
                item_id_raw = str(item.get("id", "")).lstrip("^").upper()
                if not (
                    item_id_raw.startswith("TRA_")
                    or item_id_raw.startswith("SALVAGE_")
                    or item_id_raw.startswith("ILLEGAL_")
                    or item_id_raw.startswith("ALLOY")
                    or item_id_raw.startswith("FARMPROD")
                    or item_id_raw.startswith("REACTION")
                    or item_id_raw.startswith("COMPOUND")
                    or item_id_raw.startswith("MEGAPROD")
                    or item_id_raw.startswith("ULTRAPROD")
                ):
                    continue
                raw_id = str(item.get("id", "")).strip()
                if not raw_id:
                    continue
                item_id = raw_id if raw_id.startswith("^") else f"^{raw_id}"
                options[item_id] = str(item.get("name") or get_item_display_name(item_id))

    sorted_items = sorted(options.items(), key=lambda kv: kv[1].casefold())
    return [(item_id, f"{label} ({item_id})") for item_id, label in sorted_items]


def _perk_display_name(perk_id: str) -> str:
    """Resolve a perk ID to a human-readable name."""
    entry = _PERK_DATA.get(perk_id)
    if entry:
        name = entry.get("name", perk_id)
        if entry.get("beneficial"):
            return f"{name} (+)"
        elif entry.get("beneficial") is False:
            return f"{name} (-)"
        return name
    raw = perk_id.lstrip("^")
    if "#" in raw:
        base, suffix = raw.split("#", 1)
        resolved = get_item_display_name(f"^{base}")
        if resolved != f"^{base}" and resolved != base:
            return f"{resolved} #{suffix}"
        return f"{base.replace('_', ' ').title()} #{suffix}"
    resolved = get_item_display_name(perk_id)
    if resolved != perk_id and resolved != raw:
        return resolved
    return raw.replace("_", " ").title()

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
        self._output_options = _load_output_options()
        self._preview_view: Optional[QWidget] = None
        self._preview_request_id = 0
        self._preview_thread: Optional[PreviewLoadThread] = None
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

        content_panel = QWidget()
        content_layout = QHBoxLayout(content_panel)
        content_layout.setContentsMargins(0, 0, 0, 0)

        self._left_panel = QWidget()
        left_layout = QVBoxLayout(self._left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        self._right_panel = QWidget()
        right_layout = QVBoxLayout(self._right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

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

        self._judgement_label = QLabel("—")
        det_layout.addRow("Pending Judgement:", self._judgement_label)

        left_layout.addWidget(details)

        # Perks group with table, dropdown, add/remove
        perks_group = QGroupBox("Settlement Perks")
        perks_layout = QVBoxLayout(perks_group)

        self._perk_table = QTableWidget(0, 2)
        self._perk_table.setHorizontalHeaderLabels(["Perk", "ID"])
        self._perk_table.horizontalHeader().setStretchLastSection(False)
        self._perk_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._perk_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self._perk_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self._perk_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._perk_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._perk_table.setMaximumHeight(180)
        perks_layout.addWidget(self._perk_table)

        perk_btn_row = QHBoxLayout()
        self._perk_combo = QComboBox()
        self._perk_combo.setMinimumWidth(200)
        # Populate with all known perks
        for perk_id, perk_info in sorted(_PERK_DATA.items(), key=lambda x: x[1].get("name", "")):
            self._perk_combo.addItem(_perk_display_name(perk_id), perk_id)
        perk_btn_row.addWidget(self._perk_combo)

        self._add_perk_btn = QPushButton("Add")
        self._add_perk_btn.clicked.connect(self._on_add_perk)
        perk_btn_row.addWidget(self._add_perk_btn)

        self._remove_perk_btn = QPushButton("Remove Selected")
        self._remove_perk_btn.clicked.connect(self._on_remove_perk)
        perk_btn_row.addWidget(self._remove_perk_btn)

        perk_btn_row.addStretch()
        perks_layout.addLayout(perk_btn_row)
        right_layout.addWidget(perks_group)

        preview_group = QGroupBox("Settlement Preview")
        preview_layout = QVBoxLayout(preview_group)
        self._preview_identity = QLabel("Settlement: —\nResource: —")
        self._preview_identity.setWordWrap(True)
        self._preview_status = QLabel("Preview: select a settlement")
        self._preview_status.setWordWrap(True)
        self._preview_progress = QProgressBar()
        self._preview_progress.setRange(0, 0)
        self._preview_progress.setVisible(False)
        self._preview_placeholder = QLabel("3D preview will appear here")
        self._preview_placeholder.setMinimumHeight(260)
        self._preview_placeholder.setStyleSheet("color: #aaa;")
        preview_layout.addWidget(self._preview_identity)
        preview_layout.addWidget(self._preview_status)
        preview_layout.addWidget(self._preview_progress)
        preview_layout.addWidget(self._preview_placeholder, 1)
        right_layout.addWidget(preview_group, 1)

        # Production Output group
        self._prod_group = QGroupBox("Production Output")
        self._prod_layout = QVBoxLayout(self._prod_group)
        left_layout.addWidget(self._prod_group)

        content_layout.addWidget(self._left_panel, 1)
        content_layout.addWidget(self._right_panel, 1)
        layout.addWidget(content_panel)

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

        # Populate perk list
        perks = s.get("Perks", [])
        self._refresh_perks_table(perks if isinstance(perks, list) else [])

        judgement = s.get("PendingJudgementType", {})
        if isinstance(judgement, dict):
            jt = judgement.get("SettlementJudgementType", "None")
        else:
            jt = str(judgement) if judgement else "None"
        self._judgement_label.setText(jt)

        # Production output
        self._populate_production(s)
        self._update_preview(s)

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
        current_output_ids = sorted({
            str(entry.get("ElementId", ""))
            for entry in production
            if isinstance(entry, dict) and entry.get("ElementId")
        })

        for i, entry in enumerate(production):
            if not isinstance(entry, dict):
                continue

            row_data = {}

            element_id = entry.get("ElementId", "")
            output_combo = QComboBox()
            output_combo.setMinimumWidth(220)
            for out_id, out_label in self._output_options:
                output_combo.addItem(out_label, out_id)
            for out_id in current_output_ids:
                if out_id and output_combo.findData(out_id) < 0:
                    out_name = get_item_display_name(out_id)
                    out_label = f"{out_name} ({out_id})" if out_name and out_name != out_id else out_id
                    output_combo.addItem(out_label, out_id)
            if element_id and output_combo.findData(element_id) < 0:
                out_name = get_item_display_name(element_id)
                out_label = f"{out_name} ({element_id})" if out_name and out_name != element_id else element_id
                output_combo.addItem(out_label, element_id)
            current_idx = output_combo.findData(element_id)
            output_combo.setCurrentIndex(current_idx if current_idx >= 0 else 0)
            output_combo.currentIndexChanged.connect(
                lambda _val, idx=i, combo=output_combo: self._on_production_changed(
                    idx, "ElementId", combo.currentData() or ""
                )
            )
            row_data["output"] = output_combo

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
            row_layout.addRow(f"Line {i + 1}:", output_combo)
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

    def _on_add_perk(self):
        """Add selected perk from dropdown to settlement."""
        s = self._current_settlement()
        if s is None:
            return
        perk_id = self._perk_combo.currentData()
        if not perk_id:
            return
        perks = s.get("Perks", [])
        perks.append(perk_id)
        s["Perks"] = perks
        self._refresh_perks_table(perks)

    def _on_remove_perk(self):
        """Remove selected perk from settlement."""
        s = self._current_settlement()
        if s is None:
            return
        selected = self._perk_table.selectedItems()
        row = selected[0].row() if selected else -1
        perks = s.get("Perks", [])
        if row < 0 or row >= len(perks):
            return
        perks.pop(row)
        s["Perks"] = perks
        self._refresh_perks_table(perks)

    def _ensure_preview_view(self) -> None:
        if self._preview_view is not None:
            return
        try:
            from nmstoolkit.gui.widgets.corvette_3d_view import Corvette3DView
        except Exception:
            self._preview_status.setText("Preview unavailable: OpenGL widget import failed.")
            return
        self._preview_view = Corvette3DView(self)
        configure_preview_view(self._preview_view)
        self._preview_placeholder.parentWidget().layout().replaceWidget(self._preview_placeholder, self._preview_view)
        self._preview_placeholder.hide()
        self._preview_view.show()

    def _load_preview_meshes(self, resource_filename: str):
        return load_template_preview_meshes(resource_filename)

    def _update_preview(self, settlement: dict) -> None:
        race_obj = settlement.get("Race", {})
        race = race_obj.get("AlienRace", "") if isinstance(race_obj, dict) else str(race_obj)
        resource = resolve_settlement_scene(race)
        name = settlement.get("Name", "") or "(Unnamed)"
        self._preview_identity.setText(f"Settlement: {name}\nResource: {resource or '—'}")
        if not resource:
            self._preview_status.setText("Preview unavailable: settlement scene not resolved.")
            self._preview_progress.setVisible(False)
            return
        if not self.isVisible():
            self._preview_status.setText("Open Settlements tab to load preview.")
            self._preview_progress.setVisible(False)
            return
        self._start_preview_load(resource)

    def _cancel_preview_thread(self) -> None:
        thread = self._preview_thread
        if thread is None:
            return
        if thread.isRunning():
            thread.requestInterruption()
            thread.quit()
            thread.wait(1000)
        self._preview_thread = None

    def _start_preview_load(self, resource: str) -> None:
        self._cancel_preview_thread()
        self._preview_request_id += 1
        request_id = self._preview_request_id
        self._preview_status.setText("Loading preview meshes...")
        self._preview_progress.setVisible(True)
        thread = PreviewLoadThread(
            request_id=request_id,
            resource_filename=resource,
            loader=self._load_preview_meshes,
            parent=self,
        )
        thread.completed.connect(self._on_preview_loaded)
        thread.finished.connect(thread.deleteLater)
        self._preview_thread = thread
        thread.start()

    def _on_preview_loaded(self, request_id: int, meshes: object, status: str) -> None:
        if request_id != self._preview_request_id:
            return
        self._preview_progress.setVisible(False)
        mesh_list = meshes if isinstance(meshes, list) else []
        if not mesh_list:
            self._preview_status.setText(status)
            return
        self._ensure_preview_view()
        if self._preview_view is None:
            return
        self._preview_view.set_modules(
            {
                "Width": 1,
                "Height": 1,
                "Slots": [{"Id": "^SETTLEMENT_PREVIEW", "Index": {"X": 0, "Y": 0}, "_no_layer_tooltip": True}],
            }
        )
        self._preview_view.set_mesh_data("SETTLEMENT_PREVIEW", mesh_list)
        self._preview_status.setText(status)
        self._preview_view.update()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        current = self._current_settlement()
        if current is not None:
            self._update_preview(current)

    def _refresh_perks_table(self, perks: list) -> None:
        self._perk_table.setRowCount(0)
        for perk_id in perks:
            if not perk_id:
                continue
            row = self._perk_table.rowCount()
            self._perk_table.insertRow(row)
            self._perk_table.setItem(row, 0, QTableWidgetItem(_perk_display_name(str(perk_id))))
            self._perk_table.setItem(row, 1, QTableWidgetItem(str(perk_id)))

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
        self._perk_table.setRowCount(0)
        self._judgement_label.setText("—")
        self._preview_identity.setText("Settlement: —\nResource: —")
        self._preview_status.setText("Preview: select a settlement")
        self._preview_progress.setVisible(False)
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
