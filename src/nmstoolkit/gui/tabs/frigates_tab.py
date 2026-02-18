"""Frigates editor tab — regular, biological, and corvette frigates."""

from typing import Optional

from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QProgressBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from nmstoolkit.gui.widgets.stat_editor import StatEditor
from nmstoolkit.gui.preview_support import (
    PreviewLoadThread,
    find_scene_resource_filename,
    load_template_preview_meshes,
    resolve_frigate_scene,
    seed_to_text,
)


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
        self._preview_view: Optional[QWidget] = None
        self._preview_request_id = 0
        self._preview_thread: Optional[PreviewLoadThread] = None
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

        # Right: details and preview tabs
        self._tabs = QTabWidget()
        general_tab = QWidget()
        right_layout = QVBoxLayout(general_tab)

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
        self._tabs.addTab(general_tab, "General")

        self._preview_tab = QWidget()
        preview_layout = QVBoxLayout(self._preview_tab)
        self._preview_identity = QLabel("Seed: —\nResource: —")
        self._preview_identity.setWordWrap(True)
        self._preview_fidelity = QLabel(
            "Fidelity: template-level preview (seed/resource shown; exact procedural reconstruction not guaranteed)"
        )
        self._preview_fidelity.setWordWrap(True)
        self._preview_status = QLabel("Preview: select a frigate")
        self._preview_status.setWordWrap(True)
        self._preview_progress = QProgressBar()
        self._preview_progress.setRange(0, 0)
        self._preview_progress.setVisible(False)
        self._preview_placeholder = QLabel("3D preview will appear here")
        self._preview_placeholder.setMinimumHeight(280)
        self._preview_placeholder.setStyleSheet("color: #aaa;")
        preview_layout.addWidget(self._preview_identity)
        preview_layout.addWidget(self._preview_fidelity)
        preview_layout.addWidget(self._preview_status)
        preview_layout.addWidget(self._preview_progress)
        preview_layout.addWidget(self._preview_placeholder, 1)
        self._tabs.addTab(self._preview_tab, "Preview")
        self._tabs.currentChanged.connect(self._on_tab_changed)
        layout.addWidget(self._tabs)

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
        if self._tabs.currentWidget() is self._preview_tab:
            self._update_preview(frigate)
        else:
            self._preview_progress.setVisible(False)
            self._preview_status.setText("Open the Preview tab to load frigate model.")

    def _on_tab_changed(self, _index: int) -> None:
        if self._tabs.currentWidget() is not self._preview_tab:
            return
        frigate = self._current_frigate()
        if frigate is not None:
            self._update_preview(frigate)

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

    def _update_preview(self, frigate: dict) -> None:
        resource = find_scene_resource_filename(frigate)
        if not resource:
            fc = frigate.get("FrigateClass", {})
            fc_str = fc.get("FrigateClass", "") if isinstance(fc, dict) else str(fc)
            resource = resolve_frigate_scene(fc_str)
        seed = seed_to_text(frigate.get("ResourceSeed"))
        if seed == "—":
            seed = seed_to_text(frigate.get("Seed"))
        if seed == "—":
            resource_obj = frigate.get("Resource", {})
            if isinstance(resource_obj, dict):
                seed = seed_to_text(resource_obj.get("Seed"))
        self._preview_identity.setText(f"Seed: {seed}\nResource: {resource or '—'}")
        self._preview_fidelity.setText(
            "Fidelity: template-level preview (seed/resource shown; exact procedural reconstruction not guaranteed)"
        )
        if not resource:
            self._preview_progress.setVisible(False)
            self._preview_status.setText("Preview unavailable: frigate resource filename missing.")
            return
        self._start_preview_load(resource)

    def _start_preview_load(self, resource: str) -> None:
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
                "Slots": [{"Id": "^FRIGATE_PREVIEW", "Index": {"X": 0, "Y": 0}, "_no_layer_tooltip": True}],
            }
        )
        self._preview_view.set_mesh_data("FRIGATE_PREVIEW", mesh_list)
        self._preview_status.setText(status)
        self._preview_view.update()
