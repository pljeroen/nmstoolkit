"""Squadron editor tab."""

from typing import Optional

from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from nmstoolkit.gui.widgets.seed_editor import SeedEditor
from nmstoolkit.gui.preview_support import load_template_preview_meshes

_RANK_NAMES = {0: "Cadet", 1: "Ensign", 2: "Lieutenant", 3: "Commander", 4: "Captain"}

_RACE_NAMES = {
    "NPCGEK": "Gek",
    "NPCVYKEEN": "Vy'keen",
    "NPCKORVAX": "Korvax",
}


def _extract_race(npc_resource: dict) -> str:
    """Derive pilot race from NPC model filename."""
    filename = npc_resource.get("Filename", "")
    for key, name in _RACE_NAMES.items():
        if key.upper() in filename.upper():
            return name
    return "Unknown"


def _extract_ship_type(ship_resource: dict) -> str:
    """Extract ship type from Resource.Filename."""
    filename = ship_resource.get("Filename", "")
    if not filename:
        return "—"
    # Get last path segment, strip suffixes
    name = filename.split("/")[-1]
    for suffix in ["_PROC.SCENE.MBIN", ".SCENE.MBIN", ".MBIN"]:
        name = name.replace(suffix, "")
    return name


class SquadronTab(QWidget):
    def __init__(self):
        super().__init__()
        self._data = None
        self._pilots = []
        self._current_index = -1
        self._preview_view: Optional[QWidget] = None
        self._build_ui()

    def _build_ui(self):
        layout = QHBoxLayout(self)

        left = QWidget()
        left.setMaximumWidth(220)
        left_layout = QVBoxLayout(left)
        self._list = QListWidget()
        self._list.currentRowChanged.connect(self._on_selected)
        left_layout.addWidget(self._list)
        layout.addWidget(left)

        self._tabs = QTabWidget()
        general_tab = QWidget()
        right_layout = QVBoxLayout(general_tab)
        details = QGroupBox("Pilot Details")
        det_layout = QFormLayout(details)

        self._race_label = QLabel("—")
        det_layout.addRow("Race:", self._race_label)

        self._rank_combo = QComboBox()
        for rank_id in sorted(_RANK_NAMES.keys()):
            self._rank_combo.addItem(_RANK_NAMES[rank_id])
        self._rank_combo.currentIndexChanged.connect(self._on_rank_changed)
        det_layout.addRow("Rank:", self._rank_combo)

        self._ship_combo = QComboBox()
        self._ship_combo.setMinimumWidth(200)
        self._ship_combo.currentIndexChanged.connect(self._on_ship_selected)
        det_layout.addRow("Ship:", self._ship_combo)

        self._npc_seed = SeedEditor("NPC Seed")
        self._npc_seed.seed_changed.connect(self._on_npc_seed_changed)
        det_layout.addRow("NPC Seed:", self._npc_seed)

        self._ship_seed = SeedEditor("Ship Seed")
        self._ship_seed.seed_changed.connect(self._on_ship_seed_changed)
        det_layout.addRow("Ship Seed:", self._ship_seed)

        right_layout.addWidget(details)

        # Unlocked slots info
        self._slots_label = QLabel("—")
        right_layout.addWidget(self._slots_label)

        right_layout.addStretch()
        self._tabs.addTab(general_tab, "General")

        self._preview_tab = QWidget()
        preview_layout = QVBoxLayout(self._preview_tab)
        self._preview_identity = QLabel("Seed: —\nResource: —")
        self._preview_identity.setWordWrap(True)
        self._preview_fidelity = QLabel(
            "Fidelity: template-level preview (seed/resource shown; exact procedural reconstruction not guaranteed)"
        )
        self._preview_fidelity.setWordWrap(True)
        self._preview_status = QLabel("Preview: select a pilot")
        self._preview_status.setWordWrap(True)
        self._preview_placeholder = QLabel("3D preview will appear here")
        self._preview_placeholder.setMinimumHeight(280)
        self._preview_placeholder.setStyleSheet("color: #aaa;")
        preview_layout.addWidget(self._preview_identity)
        preview_layout.addWidget(self._preview_fidelity)
        preview_layout.addWidget(self._preview_status)
        preview_layout.addWidget(self._preview_placeholder, 1)
        self._tabs.addTab(self._preview_tab, "Preview")
        layout.addWidget(self._tabs)

    def set_data(self, psd: dict):
        self._data = psd
        self._pilots = psd.get("SquadronPilots", [])
        self._ships = psd.get("ShipOwnership", [])
        self._current_index = -1
        self._list.clear()

        # Populate ship combo with player ships
        self._ship_combo.blockSignals(True)
        self._ship_combo.clear()
        for i, ship in enumerate(self._ships):
            name = ship.get("Name", "") or f"Ship {i + 1}"
            ship_type = _extract_ship_type(ship.get("Resource", {}))
            self._ship_combo.addItem(f"{name} ({ship_type})", i)
        self._ship_combo.blockSignals(False)

        unlocked = psd.get("SquadronUnlockedPilotSlots", [])
        self._slots_label.setText(f"Unlocked pilot slots: {len(unlocked)}")

        for i, pilot in enumerate(self._pilots):
            npc = pilot.get("NPCResource", {})
            race = _extract_race(npc)
            rank = _RANK_NAMES.get(pilot.get("PilotRank", 0), "Unknown")
            has_seed = bool(npc.get("Seed"))
            if has_seed:
                self._list.addItem(f"{i + 1}. {race} ({rank})")
            else:
                self._list.addItem(f"{i + 1}. (Empty slot)")
        if self._pilots:
            self._list.setCurrentRow(0)

    def _current_pilot(self):
        if self._current_index < 0 or self._current_index >= len(self._pilots):
            return None
        return self._pilots[self._current_index]

    def _on_selected(self, index):
        if index < 0 or index >= len(self._pilots):
            self._current_index = -1
            return
        self._current_index = index
        pilot = self._pilots[index]
        npc = pilot.get("NPCResource", {})
        ship = pilot.get("ShipResource", {})

        self._race_label.setText(_extract_race(npc))

        self._rank_combo.blockSignals(True)
        rank = pilot.get("PilotRank", 0)
        self._rank_combo.setCurrentIndex(rank if 0 <= rank < self._rank_combo.count() else 0)
        self._rank_combo.blockSignals(False)

        # Select matching ship in combo by filename
        ship_filename = ship.get("Filename", "")
        self._ship_combo.blockSignals(True)
        for i in range(self._ship_combo.count()):
            ship_idx = self._ship_combo.itemData(i)
            if ship_idx is not None and ship_idx < len(self._ships):
                player_ship = self._ships[ship_idx]
                if player_ship.get("Resource", {}).get("Filename", "") == ship_filename:
                    self._ship_combo.setCurrentIndex(i)
                    break
        self._ship_combo.blockSignals(False)
        self._npc_seed.set_seed(npc.get("Seed", ""))
        self._ship_seed.set_seed(ship.get("Seed", ""))
        self._update_preview(ship)

    def _on_ship_selected(self, combo_index):
        """Update pilot's ShipResource when a ship is selected from dropdown."""
        pilot = self._current_pilot()
        if pilot is None or combo_index < 0:
            return
        ship_idx = self._ship_combo.itemData(combo_index)
        if ship_idx is None or ship_idx >= len(self._ships):
            return
        player_ship = self._ships[ship_idx]
        resource = player_ship.get("Resource", {})
        pilot["ShipResource"] = {
            "Filename": resource.get("Filename", ""),
            "Seed": player_ship.get("Seed", ""),
        }
        self._update_preview(pilot["ShipResource"])

    def _on_rank_changed(self, index):
        pilot = self._current_pilot()
        if pilot is not None:
            pilot["PilotRank"] = index
            # Update list display
            i = self._current_index
            npc = pilot.get("NPCResource", {})
            race = _extract_race(npc)
            rank = _RANK_NAMES.get(index, "Unknown")
            self._list.item(i).setText(f"{i + 1}. {race} ({rank})")

    def _on_npc_seed_changed(self, seed):
        pilot = self._current_pilot()
        if pilot is not None:
            npc = pilot.get("NPCResource", {})
            if isinstance(npc, dict):
                npc["Seed"] = seed

    def _on_ship_seed_changed(self, seed):
        pilot = self._current_pilot()
        if pilot is not None:
            ship = pilot.get("ShipResource", {})
            if isinstance(ship, dict):
                ship["Seed"] = seed
                self._update_preview(ship)

    def _ensure_preview_view(self) -> None:
        if self._preview_view is not None:
            return
        try:
            from nmstoolkit.gui.widgets.corvette_3d_view import Corvette3DView
        except Exception:
            self._preview_status.setText("Preview unavailable: OpenGL widget import failed.")
            return
        self._preview_view = Corvette3DView(self._preview_tab)
        if hasattr(self._preview_view, "set_grid_visible"):
            self._preview_view.set_grid_visible(False)
        if hasattr(self._preview_view, "set_layering_enabled"):
            self._preview_view.set_layering_enabled(False)
        self._preview_tab.layout().replaceWidget(self._preview_placeholder, self._preview_view)
        self._preview_placeholder.hide()
        self._preview_view.show()

    def _load_preview_meshes(self, resource_filename: str):
        return load_template_preview_meshes(resource_filename)

    def _update_preview(self, ship_resource: dict) -> None:
        resource = ship_resource.get("Filename", "") if isinstance(ship_resource, dict) else ""
        seed = ship_resource.get("Seed", "—") if isinstance(ship_resource, dict) else "—"
        self._preview_identity.setText(f"Seed: {seed or '—'}\nResource: {resource or '—'}")
        self._preview_fidelity.setText(
            "Fidelity: template-level preview (seed/resource shown; exact procedural reconstruction not guaranteed)"
        )
        if not resource:
            self._preview_status.setText("Preview unavailable: squadron ship resource filename missing.")
            return
        meshes, status = self._load_preview_meshes(resource)
        if not meshes:
            self._preview_status.setText(status)
            return
        self._ensure_preview_view()
        if self._preview_view is None:
            return
        self._preview_view.set_modules(
            {
                "Width": 1,
                "Height": 1,
                "Slots": [{"Id": "^SQUADRON_PREVIEW", "Index": {"X": 0, "Y": 0}, "_no_layer_tooltip": True}],
            }
        )
        self._preview_view.set_mesh_data("SQUADRON_PREVIEW", meshes)
        self._preview_status.setText(status)
        self._preview_view.update()
