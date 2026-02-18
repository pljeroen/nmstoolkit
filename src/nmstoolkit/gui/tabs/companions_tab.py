"""Companions (pets) editor tab."""

from typing import Optional

from PySide6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from nmstoolkit.gui.widgets.seed_editor import SeedEditor
from nmstoolkit.gui import vault
from nmstoolkit.gui.preview_support import (
    configure_preview_view,
    find_scene_resource_filename,
    load_template_preview_meshes,
    resolve_companion_scene,
    seed_to_text,
)

# Friendly names for common creature IDs
_CREATURE_NAMES = {
    "TREX": "T-Rex",
    "LARGEBUTTERFLY": "Large Butterfly",
    "SMALLBUTTERFLY": "Small Butterfly",
    "FISH": "Fish",
    "JELLYFISH": "Jellyfish",
    "BEETLE": "Beetle",
    "CAT": "Cat",
    "RODENT": "Rodent",
    "COW": "Cow",
    "BLOB": "Blob",
    "DIPLO": "Diplo",
    "DRILL": "Drill",
    "STRIDER": "Strider",
    "SPIDER": "Spider",
    "FIEND": "Fiend",
    "RAPTOR": "Raptor",
    "BIRD": "Bird",
    "CRAB": "Crab",
    "FLYINGLIZARD": "Flying Lizard",
    "FLYINGSNAKE": "Flying Snake",
    "GRUNT": "Grunt",
    "ANTELOPE": "Antelope",
    "PROTOROLLER": "Proto Roller",
    "PROTOFLYER": "Proto Flyer",
    "PROTODIGGER": "Proto Digger",
    "FIENDFISHBIG": "Big Fiend Fish",
    "FIENDFISHSMALL": "Small Fiend Fish",
    "LARVLING": "Larvling",
    "WEIRDROLL": "Weird Roller",
    "WEIRDBUTTERFLY": "Weird Butterfly",
    "WEIRDFLOAT": "Weird Float",
    "WEIRDFLOCK": "Weird Flock",
    "WEIRDRIG": "Weird Rig",
    "ROBOTANTELOPE": "Robot Antelope",
    "ROBOTCAT": "Robot Cat",
    "ROBOTDEER": "Robot Deer",
}


def _friendly_creature_name(creature_id: str) -> str:
    """Convert ^LARGEBUTTERFLY to 'Large Butterfly'."""
    raw = creature_id.lstrip("^")
    if not raw:
        return "Unknown"
    friendly = _CREATURE_NAMES.get(raw)
    if friendly:
        return friendly
    # Fallback: add spaces before uppercase runs
    result = []
    for i, ch in enumerate(raw):
        if i > 0 and ch.isupper() and raw[i - 1].islower():
            result.append(" ")
        result.append(ch)
    return "".join(result).title()


def _friendly_descriptor_name(descriptor: str) -> str:
    raw = descriptor.lstrip("^").strip("_")
    if not raw:
        return "Unknown Trait"
    parts = [p for p in raw.split("_") if p]
    friendly_parts = []
    for part in parts:
        upper = part.upper()
        if upper in _CREATURE_NAMES:
            friendly_parts.append(_CREATURE_NAMES[upper])
        elif part.isdigit():
            friendly_parts.append(str(int(part)))
        else:
            friendly_parts.append(part.title())
    return " ".join(friendly_parts)


class CompanionsTab(QWidget):
    def __init__(self):
        super().__init__()
        self._data = None
        self._companions = []
        self._current_index = -1
        self._preview_view: Optional[QWidget] = None
        self._build_ui()

    def _build_ui(self):
        layout = QHBoxLayout(self)

        left = QWidget()
        left.setMaximumWidth(260)
        left_layout = QVBoxLayout(left)
        self._list = QListWidget()
        self._list.currentRowChanged.connect(self._on_selected)
        left_layout.addWidget(self._list)

        # Vault
        vault_group = QGroupBox("Cross-Save Vault")
        vault_layout = QVBoxLayout(vault_group)
        self._vault_list = QListWidget()
        self._vault_list.setMaximumHeight(80)
        vault_layout.addWidget(self._vault_list)
        vault_btn_layout = QHBoxLayout()
        self._vault_save_btn = QPushButton("Store")
        self._vault_save_btn.clicked.connect(self._on_vault_save)
        vault_btn_layout.addWidget(self._vault_save_btn)
        self._vault_load_btn = QPushButton("Load")
        self._vault_load_btn.clicked.connect(self._on_vault_load)
        vault_btn_layout.addWidget(self._vault_load_btn)
        self._vault_delete_btn = QPushButton("Delete")
        self._vault_delete_btn.clicked.connect(self._on_vault_delete)
        vault_btn_layout.addWidget(self._vault_delete_btn)
        vault_layout.addLayout(vault_btn_layout)
        left_layout.addWidget(vault_group)

        layout.addWidget(left)

        content_panel = QWidget()
        content_layout = QHBoxLayout(content_panel)
        content_layout.setContentsMargins(0, 0, 0, 0)
        left_editor = QWidget()
        left_editor_layout = QVBoxLayout(left_editor)
        left_editor_layout.setContentsMargins(0, 0, 0, 0)
        left_editor.setMaximumWidth(480)

        self._details_group = QGroupBox("Companion Details")
        self._details_group.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
        self._details_group.setMaximumWidth(380)
        det_layout = QFormLayout(self._details_group)

        self._name_edit = QLineEdit()
        self._name_edit.editingFinished.connect(self._on_name_changed)
        det_layout.addRow("Custom Name:", self._name_edit)

        self._species_label = QLabel("—")
        det_layout.addRow("Species:", self._species_label)

        self._creature_id_label = QLabel("—")
        det_layout.addRow("Creature ID:", self._creature_id_label)

        self._seed_editor = SeedEditor("Creature Seed")
        self._seed_editor.seed_changed.connect(self._on_seed_changed)
        det_layout.addRow("Seed:", self._seed_editor)

        left_editor_layout.addWidget(self._details_group, 0)

        info_group = QGroupBox("Companion Info")
        info_layout = QVBoxLayout(info_group)
        self._companion_info_table = QTableWidget(0, 4)
        self._companion_info_table.setHorizontalHeaderLabels(["Name", "Type", "Class", "Value"])
        self._companion_info_table.verticalHeader().setVisible(False)
        for col in range(4):
            self._companion_info_table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
        self._companion_info_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._companion_info_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        info_layout.addWidget(self._companion_info_table)
        left_editor_layout.addWidget(info_group, 1)

        # Editable stats
        stats_group = QGroupBox("Stats")
        stats_layout = QFormLayout(stats_group)

        self._trust_spin = QDoubleSpinBox()
        self._trust_spin.setRange(0, 1)
        self._trust_spin.setDecimals(2)
        self._trust_spin.setSingleStep(0.1)
        self._trust_spin.valueChanged.connect(self._on_trust_changed)
        stats_layout.addRow("Trust:", self._trust_spin)

        self._scale_spin = QDoubleSpinBox()
        self._scale_spin.setRange(0.1, 20.0)
        self._scale_spin.setDecimals(2)
        self._scale_spin.setSingleStep(0.1)
        self._scale_spin.valueChanged.connect(self._on_scale_changed)
        stats_layout.addRow("Scale:", self._scale_spin)

        self._predator_check = QCheckBox()
        self._predator_check.toggled.connect(self._on_predator_changed)
        stats_layout.addRow("Predator:", self._predator_check)

        self._has_fur_check = QCheckBox()
        self._has_fur_check.toggled.connect(self._on_has_fur_changed)
        stats_layout.addRow("Has Fur:", self._has_fur_check)

        self._egg_modified_check = QCheckBox()
        self._egg_modified_check.toggled.connect(self._on_egg_modified_changed)
        stats_layout.addRow("Egg Modified:", self._egg_modified_check)

        left_editor_layout.addWidget(stats_group)

        # Traits / Moods
        traits_group = QGroupBox("Traits & Moods")
        traits_layout = QFormLayout(traits_group)

        _TRAIT_LABELS = ["Helpfulness:", "Aggressiveness:", "Independence:"]
        self._trait_spins = []
        for i in range(3):
            spin = QDoubleSpinBox()
            spin.setRange(-1, 1)
            spin.setDecimals(3)
            spin.setSingleStep(0.05)
            spin.valueChanged.connect(
                lambda val, idx=i: self._on_trait_changed(idx, val)
            )
            traits_layout.addRow(_TRAIT_LABELS[i], spin)
            self._trait_spins.append(spin)

        _MOOD_LABELS = ["Playfulness:", "Curiosity:"]
        self._mood_spins = []
        for i in range(2):
            spin = QDoubleSpinBox()
            spin.setRange(-1, 1)
            spin.setDecimals(3)
            spin.setSingleStep(0.05)
            spin.valueChanged.connect(
                lambda val, idx=i: self._on_mood_changed(idx, val)
            )
            traits_layout.addRow(_MOOD_LABELS[i], spin)
            self._mood_spins.append(spin)

        left_editor_layout.addWidget(traits_group)
        content_layout.addWidget(left_editor, 3)

        # Descriptors (editable gene traits) — dynamic list, scrollable
        desc_group = QGroupBox("Gene Traits")
        desc_outer = QVBoxLayout(desc_group)
        self._descriptors_label = QLabel("—")
        self._descriptors_label.setWordWrap(True)
        self._descriptors_label.setStyleSheet("font-size: 11px; color: #aaa;")
        desc_outer.addWidget(self._descriptors_label)

        # Selectable descriptor list
        self._desc_list = QListWidget()
        self._desc_list.setMinimumHeight(120)
        desc_outer.addWidget(self._desc_list)
        self._descriptor_edits = []

        # Scrollable container for descriptor edits
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumHeight(80)
        self._desc_container = QWidget()
        self._desc_layout = QVBoxLayout(self._desc_container)
        self._desc_layout.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(self._desc_container)
        desc_outer.addWidget(scroll)

        # Add/Remove buttons
        btn_row = QHBoxLayout()
        self._add_desc_btn = QPushButton("Add Trait")
        self._add_desc_btn.clicked.connect(self._on_add_descriptor)
        self._remove_desc_btn = QPushButton("Remove Selected")
        self._remove_desc_btn.clicked.connect(self._on_remove_descriptor)
        btn_row.addWidget(self._add_desc_btn)
        btn_row.addWidget(self._remove_desc_btn)
        btn_row.addStretch()
        desc_outer.addLayout(btn_row)

        right_editor = QWidget()
        right_editor_layout = QVBoxLayout(right_editor)
        right_editor_layout.setContentsMargins(0, 0, 0, 0)
        right_editor_layout.addWidget(desc_group)
        right_editor.setMaximumWidth(520)

        self._preview_panel = QWidget()
        preview_layout = QVBoxLayout(self._preview_panel)
        self._preview_identity = QLabel("Seed: —\nResource: —")
        self._preview_identity.setWordWrap(True)
        self._preview_fidelity = QLabel(
            "Fidelity: template-level preview (seed/resource shown; exact procedural reconstruction not guaranteed)"
        )
        self._preview_fidelity.setWordWrap(True)
        self._preview_status = QLabel("Preview: select a companion")
        self._preview_status.setWordWrap(True)
        self._preview_placeholder = QLabel("3D preview will appear here")
        self._preview_placeholder.setMinimumHeight(280)
        self._preview_placeholder.setStyleSheet("color: #aaa;")
        preview_layout.addWidget(self._preview_identity)
        preview_layout.addWidget(self._preview_fidelity)
        preview_layout.addWidget(self._preview_status)
        preview_layout.addWidget(self._preview_placeholder, 1)
        content_layout.addWidget(self._preview_panel, 4)
        content_layout.addWidget(right_editor, 3)
        layout.addWidget(content_panel)

    def set_data(self, psd: dict):
        self._data = psd
        all_pets = psd.get("Pets", [])
        self._companions = [
            p for p in all_pets
            if p.get("CreatureID", "").strip("^")
        ]
        self._current_index = -1
        self._list.clear()
        for i, pet in enumerate(self._companions):
            custom_name = pet.get("CustomName", "") or ""
            if custom_name and custom_name.strip("^"):
                custom_name = custom_name.strip("^")
            else:
                custom_name = ""
            creature_id = pet.get("CreatureID", "")
            display = custom_name if custom_name else _friendly_creature_name(creature_id)
            self._list.addItem(f"{i + 1}. {display}")
        self._refresh_vault()
        if self._companions:
            self._list.setCurrentRow(0)

    def _current_companion(self):
        if self._current_index < 0 or self._current_index >= len(self._companions):
            return None
        return self._companions[self._current_index]

    def _on_selected(self, index):
        if index < 0 or index >= len(self._companions):
            self._current_index = -1
            return
        self._current_index = index
        pet = self._companions[index]

        # Name
        custom_name = pet.get("CustomName", "") or ""
        if custom_name and custom_name.strip("^"):
            custom_name = custom_name.strip("^")
        else:
            custom_name = ""
        self._name_edit.blockSignals(True)
        self._name_edit.setText(custom_name)
        self._name_edit.blockSignals(False)

        # Species / ID
        creature_id = pet.get("CreatureID", "—")
        self._creature_id_label.setText(creature_id)
        self._species_label.setText(_friendly_creature_name(creature_id))

        # Seed
        self._seed_editor.set_seed(pet.get("CreatureSeed") or pet.get("Seed", ""))

        # Stats
        self._trust_spin.blockSignals(True)
        self._trust_spin.setValue(pet.get("Trust", 0) if isinstance(pet.get("Trust"), (int, float)) else 0)
        self._trust_spin.blockSignals(False)

        self._scale_spin.blockSignals(True)
        self._scale_spin.setValue(pet.get("Scale", 1.0) if isinstance(pet.get("Scale"), (int, float)) else 1.0)
        self._scale_spin.blockSignals(False)

        self._predator_check.blockSignals(True)
        self._predator_check.setChecked(bool(pet.get("Predator", False)))
        self._predator_check.blockSignals(False)

        self._has_fur_check.blockSignals(True)
        self._has_fur_check.setChecked(bool(pet.get("HasFur", False)))
        self._has_fur_check.blockSignals(False)

        self._egg_modified_check.blockSignals(True)
        self._egg_modified_check.setChecked(bool(pet.get("EggModified", False)))
        self._egg_modified_check.blockSignals(False)

        # Traits
        traits = pet.get("Traits", [])
        for i, spin in enumerate(self._trait_spins):
            spin.blockSignals(True)
            spin.setValue(traits[i] if i < len(traits) and isinstance(traits[i], (int, float)) else 0)
            spin.blockSignals(False)

        # Moods
        moods = pet.get("Moods", [])
        for i, spin in enumerate(self._mood_spins):
            spin.blockSignals(True)
            spin.setValue(moods[i] if i < len(moods) and isinstance(moods[i], (int, float)) else 0)
            spin.blockSignals(False)

        # Descriptors — rebuild dynamic list
        descriptors = pet.get("Descriptors", [])
        active_descs = [str(d).lstrip("^") for d in descriptors if d and str(d).strip("^")]
        if active_descs:
            self._descriptors_label.setText(f"{len(active_descs)} gene traits")
        else:
            self._descriptors_label.setText("None")

        self._rebuild_descriptor_edits(active_descs)
        self._update_companion_info(pet)
        self._update_preview(pet)

    def _rebuild_descriptor_edits(self, active_descs):
        """Rebuild the dynamic descriptor edit list and selection list to match data."""
        # Remove old edits
        for edit in self._descriptor_edits:
            edit.setParent(None)
        self._descriptor_edits.clear()

        # Update the selectable list
        self._desc_list.clear()
        for i, desc in enumerate(active_descs):
            friendly = _friendly_descriptor_name(desc)
            item_text = f"{i + 1}. {friendly}"
            if desc:
                item_text = f"{item_text} ({desc})"
            self._desc_list.addItem(item_text)

        # Create one edit per active descriptor
        for i, desc in enumerate(active_descs):
            edit = QLineEdit()
            edit.setPlaceholderText(f"Descriptor {i + 1}")
            edit.setText(desc)
            edit.editingFinished.connect(
                lambda idx=i: self._on_descriptor_changed(idx)
            )
            self._desc_layout.addWidget(edit)
            self._descriptor_edits.append(edit)

    def _on_add_descriptor(self):
        """Add a new empty descriptor to the current companion."""
        pet = self._current_companion()
        if pet is None:
            return
        descriptors = pet.get("Descriptors", [])
        descriptors.append("^")
        pet["Descriptors"] = descriptors
        pet["EggModified"] = True
        self._egg_modified_check.blockSignals(True)
        self._egg_modified_check.setChecked(True)
        self._egg_modified_check.blockSignals(False)
        # Rebuild UI
        active_descs = [str(d).lstrip("^") for d in descriptors if d and str(d).strip("^")]
        self._descriptors_label.setText(f"{len(active_descs)} gene traits")
        # Also show the empty slot for editing
        all_descs = [str(d).lstrip("^") for d in descriptors]
        self._rebuild_descriptor_edits(all_descs)

    def _on_remove_descriptor(self):
        """Remove the selected descriptor from the current companion."""
        pet = self._current_companion()
        if pet is None:
            return
        descriptors = pet.get("Descriptors", [])
        if not descriptors:
            return
        # Remove selected index, or do nothing if nothing selected
        selected_row = self._desc_list.currentRow()
        if selected_row < 0 or selected_row >= len(descriptors):
            return
        descriptors.pop(selected_row)
        pet["Descriptors"] = descriptors
        pet["EggModified"] = True
        self._egg_modified_check.blockSignals(True)
        self._egg_modified_check.setChecked(True)
        self._egg_modified_check.blockSignals(False)
        # Rebuild UI
        active_descs = [str(d).lstrip("^") for d in descriptors if d and str(d).strip("^")]
        self._descriptors_label.setText(f"{len(active_descs)} gene traits")
        self._rebuild_descriptor_edits(active_descs)

    def _on_name_changed(self):
        pet = self._current_companion()
        if pet is not None:
            text = self._name_edit.text()
            pet["CustomName"] = f"^{text}" if text else "^"
            self._update_companion_info(pet)

    def _on_seed_changed(self, seed):
        pet = self._current_companion()
        if pet is not None:
            pet["CreatureSeed"] = seed
            self._update_companion_info(pet)

    def _on_trust_changed(self, val):
        pet = self._current_companion()
        if pet is not None:
            pet["Trust"] = val
            self._update_companion_info(pet)

    def _on_scale_changed(self, val):
        pet = self._current_companion()
        if pet is not None:
            pet["Scale"] = val
            self._update_companion_info(pet)

    def _on_predator_changed(self, checked):
        pet = self._current_companion()
        if pet is not None:
            pet["Predator"] = checked
            self._update_companion_info(pet)

    def _on_has_fur_changed(self, checked):
        pet = self._current_companion()
        if pet is not None:
            pet["HasFur"] = checked
            self._update_companion_info(pet)

    def _on_egg_modified_changed(self, checked):
        pet = self._current_companion()
        if pet is not None:
            pet["EggModified"] = checked
            self._update_companion_info(pet)

    def _on_trait_changed(self, idx, val):
        pet = self._current_companion()
        if pet is None:
            return
        traits = pet.get("Traits", [])
        while len(traits) <= idx:
            traits.append(0.0)
        traits[idx] = val
        pet["Traits"] = traits
        self._update_companion_info(pet)

    def _on_mood_changed(self, idx, val):
        pet = self._current_companion()
        if pet is None:
            return
        moods = pet.get("Moods", [])
        while len(moods) <= idx:
            moods.append(0.0)
        moods[idx] = val
        pet["Moods"] = moods
        self._update_companion_info(pet)

    def _update_companion_info(self, pet: dict) -> None:
        self._companion_info_table.setRowCount(0)
        custom_name = (pet.get("CustomName", "") or "").strip("^")
        display_name = custom_name or _friendly_creature_name(pet.get("CreatureID", ""))
        species = _friendly_creature_name(pet.get("CreatureID", ""))
        self._companion_info_table.insertRow(0)
        self._companion_info_table.setItem(0, 0, QTableWidgetItem(display_name))
        self._companion_info_table.setItem(0, 1, QTableWidgetItem(species))
        self._companion_info_table.setItem(0, 2, QTableWidgetItem(str(pet.get("CreatureID", "—")).lstrip("^")))
        self._companion_info_table.setItem(0, 3, QTableWidgetItem(f"Trust {pet.get('Trust', 0):.2f}"))
        self._companion_info_table.insertRow(1)
        self._companion_info_table.setItem(1, 0, QTableWidgetItem("Scale"))
        self._companion_info_table.setItem(1, 1, QTableWidgetItem("Trait"))
        self._companion_info_table.setItem(1, 2, QTableWidgetItem("—"))
        self._companion_info_table.setItem(1, 3, QTableWidgetItem(f"{pet.get('Scale', 1.0):.2f}"))

    def _on_descriptor_changed(self, idx):
        pet = self._current_companion()
        if pet is None:
            return
        descriptors = pet.get("Descriptors", [])
        text = self._descriptor_edits[idx].text().strip()
        # Ensure ^ prefix for NMS format
        if text and not text.startswith("^"):
            text = "^" + text
        elif not text:
            text = "^"
        while len(descriptors) <= idx:
            descriptors.append("^")
        descriptors[idx] = text
        pet["Descriptors"] = descriptors
        # Modifying descriptors means gene modification occurred
        pet["EggModified"] = True
        self._egg_modified_check.blockSignals(True)
        self._egg_modified_check.setChecked(True)
        self._egg_modified_check.blockSignals(False)

    def _refresh_vault(self):
        self._vault_list.clear()
        self._vault_entries = []
        for path, name in vault.scan_vault("companions"):
            self._vault_entries.append(path)
            self._vault_list.addItem(name)

    def _on_vault_save(self):
        pet = self._current_companion()
        if pet is None:
            return
        import copy
        name = pet.get("CustomName", "") or _friendly_creature_name(pet.get("CreatureID", ""))
        vault.save_to_vault("companions", copy.deepcopy(pet), name)
        self._refresh_vault()

    def _on_vault_load(self):
        row = self._vault_list.currentRow()
        if row < 0 or row >= len(self._vault_entries):
            return
        pet = vault.load_from_vault(self._vault_entries[row])
        all_pets = self._data.get("Pets", [])
        all_pets.append(pet)
        self.set_data(self._data)

    def _on_vault_delete(self):
        row = self._vault_list.currentRow()
        if row < 0 or row >= len(self._vault_entries):
            return
        vault.delete_from_vault(self._vault_entries[row])
        self._refresh_vault()

    def _ensure_preview_view(self) -> None:
        if self._preview_view is not None:
            return
        try:
            from nmstoolkit.gui.widgets.corvette_3d_view import Corvette3DView
        except Exception:
            self._preview_status.setText("Preview unavailable: OpenGL widget import failed.")
            return
        self._preview_view = Corvette3DView(self._preview_panel)
        configure_preview_view(self._preview_view)
        self._preview_panel.layout().replaceWidget(self._preview_placeholder, self._preview_view)
        self._preview_placeholder.hide()
        self._preview_view.show()

    def _load_preview_meshes(self, resource_filename: str):
        return load_template_preview_meshes(resource_filename)

    def _update_preview(self, companion: dict) -> None:
        resource = find_scene_resource_filename(companion)
        if not resource:
            resource = resolve_companion_scene(str(companion.get("CreatureID", "")))
        seed = seed_to_text(companion.get("CreatureSeed"))
        if seed == "—":
            seed = seed_to_text(companion.get("Seed"))
        if seed == "—":
            resource_obj = companion.get("Resource", {})
            if isinstance(resource_obj, dict):
                seed = seed_to_text(resource_obj.get("Seed"))
        self._preview_identity.setText(f"Seed: {seed}\nResource: {resource or '—'}")
        self._preview_fidelity.setText(
            "Fidelity: template-level preview (seed/resource shown; exact procedural reconstruction not guaranteed)"
        )
        if not resource:
            self._preview_status.setText("Preview unavailable: companion resource filename missing.")
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
                "Slots": [{"Id": "^COMPANION_PREVIEW", "Index": {"X": 0, "Y": 0}, "_no_layer_tooltip": True}],
            }
        )
        self._preview_view.set_mesh_data("COMPANION_PREVIEW", meshes)
        self._preview_status.setText(status)
        self._preview_view.update()
