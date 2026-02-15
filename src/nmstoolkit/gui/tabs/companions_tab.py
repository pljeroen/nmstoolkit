"""Companions (pets) editor tab."""

from PySide6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from nmstoolkit.gui.widgets.seed_editor import SeedEditor

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


class CompanionsTab(QWidget):
    def __init__(self):
        super().__init__()
        self._data = None
        self._companions = []
        self._current_index = -1
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

        right = QWidget()
        right_layout = QVBoxLayout(right)

        # Identity
        details = QGroupBox("Companion Details")
        det_layout = QFormLayout(details)

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

        right_layout.addWidget(details)

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

        right_layout.addWidget(stats_group)

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

        right_layout.addWidget(traits_group)

        # Descriptors (editable gene traits) — dynamic list, scrollable
        desc_group = QGroupBox("Descriptors (Gene Traits)")
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

        right_layout.addWidget(desc_group)

        right_layout.addStretch()
        layout.addWidget(right)

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

    def _rebuild_descriptor_edits(self, active_descs):
        """Rebuild the dynamic descriptor edit list and selection list to match data."""
        # Remove old edits
        for edit in self._descriptor_edits:
            edit.setParent(None)
        self._descriptor_edits.clear()

        # Update the selectable list
        self._desc_list.clear()
        for i, desc in enumerate(active_descs):
            self._desc_list.addItem(f"{i + 1}. {desc}")

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

    def _on_seed_changed(self, seed):
        pet = self._current_companion()
        if pet is not None:
            pet["CreatureSeed"] = seed

    def _on_trust_changed(self, val):
        pet = self._current_companion()
        if pet is not None:
            pet["Trust"] = val

    def _on_scale_changed(self, val):
        pet = self._current_companion()
        if pet is not None:
            pet["Scale"] = val

    def _on_predator_changed(self, checked):
        pet = self._current_companion()
        if pet is not None:
            pet["Predator"] = checked

    def _on_has_fur_changed(self, checked):
        pet = self._current_companion()
        if pet is not None:
            pet["HasFur"] = checked

    def _on_egg_modified_changed(self, checked):
        pet = self._current_companion()
        if pet is not None:
            pet["EggModified"] = checked

    def _on_trait_changed(self, idx, val):
        pet = self._current_companion()
        if pet is None:
            return
        traits = pet.get("Traits", [])
        while len(traits) <= idx:
            traits.append(0.0)
        traits[idx] = val
        pet["Traits"] = traits

    def _on_mood_changed(self, idx, val):
        pet = self._current_companion()
        if pet is None:
            return
        moods = pet.get("Moods", [])
        while len(moods) <= idx:
            moods.append(0.0)
        moods[idx] = val
        pet["Moods"] = moods

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
