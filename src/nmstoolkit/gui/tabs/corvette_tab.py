"""Corvette editor tab — list completed corvettes + active draft, with inventory editing."""

from collections import Counter
from pathlib import Path
import shutil
from typing import Dict, List, Optional

from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QStackedWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from nmstoolkit.gui.widgets.inventory_grid import InventoryGrid
from nmstoolkit.paths import cache_meshes_dir, external_tools_dir

# Module category mapping from ID prefix to human-readable category.
_MODULE_CATEGORIES = {
    "B_COK": "Cockpit",
    "B_HAB1": "Access Module",
    "B_HAB": "Habitation",
    "B_WNG": "Wing",
    "B_STR": "Structure",
    "B_CON_L": "Large Connector",
    "B_CON2": "Connector",
    "B_CON": "Connector",
    "B_TRU": "Thruster",
    "B_TUR": "Turret",
    "B_LND": "Landing Gear",
    "B_SHL": "Shell",
    "B_ALK": "Airlock",
    "B_GEN": "Generator",
    "B_DECO": "Decoration",
}

_INV_CLASSES = ["C", "B", "A", "S"]

_STAT_IDS = [
    ("^SHIP_DAMAGE", "Damage"),
    ("^SHIP_SHIELD", "Shield"),
    ("^SHIP_HYPERDRIVE", "Hyperdrive"),
    ("^SHIP_AGILE", "Maneuverability"),
]


def _categorize_modules(slots: List[Dict]) -> Dict[str, int]:
    """Count modules by category from slot data."""
    counts: Counter = Counter()
    for slot in slots:
        item_id = slot.get("Id", "").lstrip("^")
        category = _get_module_category(item_id)
        if category:
            counts[category] += 1
    return dict(counts)


def _get_module_category(item_id: str) -> str:
    """Get the category name for a module ID."""
    for prefix, category in _MODULE_CATEGORIES.items():
        if item_id.startswith(prefix):
            return category
    return "Unknown"


_CORVETTE_MODULE_PREFIXES = ("B_COK", "B_HAB", "B_WNG", "B_STR", "B_TRU", "B_TUR", "B_LND", "B_SHL", "B_ALK", "B_GEN", "B_CON", "B_DECO")


def _is_hull_module(object_id: str) -> bool:
    """Return True if object_id is an exterior corvette hull module.

    Uses _CORVETTE_MODULE_PREFIXES to include only structural hull parts.
    Excludes interior items (B_WALL_*, B_STAIRS*, B_DOOR*), anchors (U_PARAGON),
    and any other non-hull objects found in PersistentPlayerBases.
    """
    uid = object_id.lstrip("^").upper()
    return any(uid.startswith(prefix) for prefix in _CORVETTE_MODULE_PREFIXES)


def _find_corvette_base(psd: dict, ship_ownership_index: int) -> Optional[dict]:
    """Find the PersistentPlayerBases entry for a completed corvette.

    Corvette bases have BaseType.PersistentBaseTypes == "PlayerShipBase"
    and UserData matching the ship's index in ShipOwnership.
    """
    for base in psd.get("PersistentPlayerBases", []):
        base_type = base.get("BaseType", {})
        if not isinstance(base_type, dict):
            continue
        if base_type.get("PersistentBaseTypes") != "PlayerShipBase":
            continue
        if base.get("UserData") == ship_ownership_index:
            return base
    return None


def _extract_hull_modules_3d(base: dict) -> List[dict]:
    """Extract hull module objects with 3D positions from a corvette base.

    Returns a list of dicts with keys: ObjectID, Position, Up, At.
    Only includes exterior hull modules (filtered by _is_hull_module).
    """
    result: List[dict] = []
    for obj in base.get("Objects", []):
        object_id = obj.get("ObjectID", "")
        if not _is_hull_module(object_id):
            continue
        pos = obj.get("Position")
        if not isinstance(pos, list) or len(pos) < 3:
            continue
        result.append({
            "ObjectID": object_id,
            "Position": pos,
            "Up": obj.get("Up", [0.0, 1.0, 0.0]),
            "At": obj.get("At", [0.0, 0.0, 1.0]),
        })
    return result


def _inventory_has_data(inv: dict) -> bool:
    if not isinstance(inv, dict):
        return False
    for slot in inv.get("Slots", []):
        if isinstance(slot, dict) and slot.get("Id"):
            return True
    return False


def _derive_module_id(path_parts: list[str]) -> str:
    """Derive corvette module ID (e.g. B_COK_A) from a SCENE path."""
    try:
        parts_idx = path_parts.index("parts")
        part_dir = path_parts[parts_idx + 1] if parts_idx + 1 < len(path_parts) else ""
    except ValueError:
        return ""
    if not part_dir:
        return ""
    return "B_" + part_dir.upper()


def _scene_candidates_for_module(module_id: str) -> list[str]:
    """Return likely BIGGS module scene paths for a corvette module id."""
    uid = module_id.upper().lstrip("^")
    base = "models/common/spacecraft/biggs/modules/"
    parts_base = "models/common/spacecraft/biggs/modules/parts/"
    parts = uid.split("_")
    if len(parts) < 2 or parts[0] != "B":
        return []

    if parts[1] == "COK" and len(parts) >= 3:
        v = parts[2].lower()
        return [
            f"{parts_base}cockpit_1x2_{v}.scene.mbin",
            f"{parts_base}cockpit_1x2_{v}_ext.scene.mbin",
            f"{base}cockpit_{v}_1x2_placement.scene.mbin",
        ]

    if parts[1] == "HAB1" and len(parts) >= 3:
        v = parts[2].lower()
        return [
            f"{parts_base}hab_{v}_1x1_core.scene.mbin",
            f"{base}hab_{v}_1x1_placement.scene.mbin",
        ]

    if parts[1] == "HAB" and len(parts) >= 3:
        v = parts[2].lower()
        return [
            f"{parts_base}hab_{v}_1x2_core.scene.mbin",
            f"{base}hab_{v}_1x2_placement.scene.mbin",
        ]

    if parts[1] == "WNG" and len(parts) >= 3:
        if parts[2] == "O" and len(parts) >= 4:
            n = parts[3].lower()
            return [
                f"{parts_base}wing_{n}_l.scene.mbin",
                f"{parts_base}wing_{n}_r.scene.mbin",
                f"{parts_base}wing_{n}.scene.mbin",
                f"{base}ext_wing_o_{n}_1x2_placement.scene.mbin",
                f"{base}ext_wing_o_{n}_1x2_r_placement.scene.mbin",
            ]
        v = parts[2].lower()
        return [
            f"{parts_base}wing_{v}_l.scene.mbin",
            f"{parts_base}wing_{v}_r.scene.mbin",
            f"{parts_base}wing_{v}.scene.mbin",
            f"{base}ext_wing_{v}_1x2_placement.scene.mbin",
            f"{base}ext_wing_{v}_1x2_r_placement.scene.mbin",
            f"{base}ext_wing_{v}_1x1_placement.scene.mbin",
        ]

    if parts[1] == "CON" and len(parts) >= 4 and parts[2] == "L":
        n = parts[3].lower()
        return [
            f"{parts_base}connectors/connector_1x1_l_{n}.scene.mbin",
            f"{base}ext_connector_1x1_l_{n}_placement.scene.mbin",
        ]

    if parts[1] == "CON2" and len(parts) >= 3:
        n = parts[2].lower()
        return [
            f"{parts_base}connectors/connector_1x1_r_{n}.scene.mbin",
            f"{base}ext_connector_1x1_r_{n}_placement.scene.mbin",
        ]

    if parts[1] == "CON" and len(parts) >= 3:
        n = parts[2].lower()
        return [
            f"{parts_base}connectors/connector_1x1_{n}.scene.mbin",
            f"{base}ext_connector_1x1_{n}_placement.scene.mbin",
        ]

    if parts[1] == "TRU":
        if len(parts) >= 3 and parts[2] in {"A", "B", "C"}:
            v = parts[2].lower()
            return [
                f"{parts_base}backthruster_{v}.scene.mbin",
                f"{base}ext_backthrusters_{v}_1x1_placement.scene.mbin",
                f"{base}ext_thrusters_1x1_placement.scene.mbin",
            ]
        return [
            f"{parts_base}backthruster_a.scene.mbin",
            f"{base}ext_thrusters_1x1_placement.scene.mbin",
        ]

    if parts[1] == "TUR":
        return [f"{base}ext_turret_1x1_placement.scene.mbin"]

    if parts[1] == "LND":
        v = parts[2].lower() if len(parts) >= 3 else "a"
        return [
            f"{parts_base}landinggear_leg_{v}.scene.mbin",
            f"{base}ext_landinggear_1x1_placement.scene.mbin",
        ]

    if parts[1] == "SHL" and len(parts) >= 3:
        v = parts[2].lower()
        return [
            f"{parts_base}shieldgenerator_{v}.scene.mbin",
            f"{base}ext_shieldgen_{v}_1x1_placement.scene.mbin",
            f"{base}ext_shieldgen_a_1x1_placement.scene.mbin",
        ]

    if parts[1] == "ALK" and len(parts) >= 3:
        v = parts[2].lower()
        return [
            f"{parts_base}airlock_nesw_{v}.scene.mbin",
            f"{parts_base}airlock_ew_{v}.scene.mbin",
            f"{base}exthatch_airlock_{v}_1x1_placement.scene.mbin",
            f"{base}exthatch_airlock_z_{v}_1x1_placement.scene.mbin",
        ]

    if parts[1] == "GEN" and len(parts) >= 3:
        n = parts[2].lower()
        return [
            f"{parts_base}generator_{n}.scene.mbin",
            f"{base}ext_gen_1x1_{n}_placement.scene.mbin",
        ]

    if parts[1] == "STR":
        candidates = []
        if len(parts) >= 4:
            direction = parts[3].lower()
            v = parts[2].lower() if len(parts) >= 3 else "a"
            candidates.append(f"{parts_base}structural/structural_1x1_{direction}_0.scene.mbin")
            candidates.append(f"{parts_base}structural/structural_1x1_{direction}_{v}.scene.mbin")
            candidates.append(f"{base}ext_structural_1x1_{direction}_placement.scene.mbin")
            candidates.append(f"{base}ext_structural_1x1_y_{direction}_placement.scene.mbin")
        candidates.append(f"{base}ext_structural_1x1_placement.scene.mbin")
        return candidates

    if parts[1] == "DECO":
        return [
            f"{parts_base}bay_a.scene.mbin",
            f"{base}bay_a_1x1_placement.scene.mbin",
        ]

    return []


def _normalize_ref(path: str) -> str:
    return path.replace("\\", "/").lower()


def _required_corvette_modules(inv: dict) -> set[str]:
    """Return unique corvette module IDs present in inventory slots."""
    required: set[str] = set()
    if not isinstance(inv, dict):
        return required
    for slot in inv.get("Slots", []):
        if not isinstance(slot, dict):
            continue
        item_id = str(slot.get("Id", "")).lstrip("^").upper()
        if item_id.startswith("B_"):
            required.add(item_id)
    return required


def _resolve_pak_dir(game_dir: Path) -> Optional[Path]:
    """Resolve PCBANKS path from a user-selected game directory."""
    pcbanks = game_dir / "GAMEDATA" / "PCBANKS"
    if pcbanks.exists():
        return pcbanks
    pcbanks = game_dir / "PCBANKS"
    if pcbanks.exists():
        return pcbanks
    if game_dir.name.upper() == "PCBANKS" and game_dir.exists():
        return game_dir
    return None


def _find_mbin_compiler(pak_dir: Path) -> Optional[Path]:
    """Locate MBINCompiler via ExternalTools, nearby folders, or PATH."""
    ext_dir = external_tools_dir() / "MBINCompiler"
    candidates = [
        ext_dir / "MBINCompiler.exe",
        ext_dir / "MBINCompiler",
        ext_dir / "MBINCompiler-linux",
        Path("/tmp/nms_exml/MBINCompiler"),
        pak_dir / "MBINCompiler.exe",
        pak_dir / "MBINCompiler",
        pak_dir.parent / "MBINCompiler.exe",
        pak_dir.parent / "MBINCompiler",
        pak_dir.parent.parent / "MBINCompiler.exe",
        pak_dir.parent.parent / "MBINCompiler",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    found = shutil.which("MBINCompiler") or shutil.which("MBINCompiler.exe")
    return Path(found) if found else None


def _is_corvette_ship(ship: dict) -> bool:
    """Check if a ship is a corvette.

    Detection priority:
    1) BIGGS model filename (authoritative)
    2) Conservative fallback when filename is missing: require multiple
       installed corvette modules with cockpit + structural companion.
    """
    filename = ship.get("Resource", {}).get("Filename", "").upper()
    if "BIGGS" in filename:
        return True

    # Conservative fallback only when filename is absent/unknown.
    if filename:
        return False

    module_ids: set[str] = set()
    for inv_key in ("Inventory", "Inventory_TechOnly"):
        slots = ship.get(inv_key, {}).get("Slots", [])
        for slot in slots:
            if not isinstance(slot, dict):
                continue
            slot_type = (
                slot.get("Type", {})
                .get("InventoryType", "")
                .upper()
            )
            if slot_type and slot_type != "TECHNOLOGY":
                continue
            slot_id = str(slot.get("Id", "")).lstrip("^").upper()
            if slot_id.startswith("B_"):
                module_ids.add(slot_id)

    has_cockpit = any(mid.startswith("B_COK") for mid in module_ids)
    has_structure = any(mid.startswith(("B_WNG", "B_HAB", "B_STR")) for mid in module_ids)
    return len(module_ids) >= 3 and has_cockpit and has_structure


class CorvetteTab(QWidget):
    def __init__(self):
        super().__init__()
        self._data = None
        self._corvettes = []  # List of (index, ship_dict) for completed corvettes
        self._current_index = -1  # Index into self._corvettes, -1 = draft
        self._build_ui()

    def _build_ui(self):
        layout = QHBoxLayout(self)

        # Left: selector + details
        left = QWidget()
        left.setMaximumWidth(340)
        left_layout = QVBoxLayout(left)

        # Empty state label
        self._empty_label = QLabel(
            "No corvettes found — build a corvette in-game"
        )
        self._empty_label.setWordWrap(True)
        self._empty_label.setStyleSheet("color: #888; font-size: 13px; padding: 20px;")
        left_layout.addWidget(self._empty_label)

        # Corvette selector
        self._selector_group = QGroupBox("Select Corvette")
        sel_layout = QVBoxLayout(self._selector_group)
        self._corvette_combo = QComboBox()
        self._corvette_combo.currentIndexChanged.connect(self._on_corvette_selected)
        sel_layout.addWidget(self._corvette_combo)
        left_layout.addWidget(self._selector_group)

        # Details group (for completed corvettes)
        self._details_group = QGroupBox("Corvette Details")
        det_layout = QFormLayout(self._details_group)

        self._name_edit = QLineEdit()
        self._name_edit.editingFinished.connect(self._on_name_changed)
        det_layout.addRow("Name:", self._name_edit)

        self._class_combo = QComboBox()
        self._class_combo.addItems(_INV_CLASSES)
        self._class_combo.currentTextChanged.connect(self._on_class_changed)
        det_layout.addRow("Class:", self._class_combo)

        self._seed_label = QLabel("—")
        det_layout.addRow("Seed:", self._seed_label)

        left_layout.addWidget(self._details_group)

        # Base stats
        self._stats_group = QGroupBox("Base Stats")
        stats_layout = QFormLayout(self._stats_group)
        self._stat_spinners = {}
        for stat_id, label in _STAT_IDS:
            spinner = QDoubleSpinBox()
            spinner.setRange(0, 99999)
            spinner.setDecimals(1)
            spinner.valueChanged.connect(
                lambda val, sid=stat_id: self._on_stat_changed(sid, val)
            )
            stats_layout.addRow(f"{label}:", spinner)
            self._stat_spinners[stat_id] = spinner
        left_layout.addWidget(self._stats_group)

        # Draft details group (for active draft only)
        self._draft_group = QGroupBox("Draft Details")
        draft_layout = QFormLayout(self._draft_group)

        self._draft_ship_label = QLabel("—")
        draft_layout.addRow("Target Ship:", self._draft_ship_label)

        self._draft_seed_label = QLabel("—")
        draft_layout.addRow("Draft Seed:", self._draft_seed_label)

        self._draft_level_label = QLabel("—")
        draft_layout.addRow("Level:", self._draft_level_label)

        left_layout.addWidget(self._draft_group)

        # Module summary
        self._summary_group = QGroupBox("Module Summary")
        summary_layout = QVBoxLayout(self._summary_group)
        self._summary_label = QLabel("")
        self._summary_label.setWordWrap(True)
        summary_layout.addWidget(self._summary_label)
        left_layout.addWidget(self._summary_group)

        left_layout.addStretch()
        layout.addWidget(left)

        # Right: inventory sub-tabs
        self._right_placeholder = QLabel("Load a save to view corvette inventories")
        self._right_placeholder.setAlignment(Qt.AlignCenter)
        self._right_placeholder.setWordWrap(True)
        self._right_placeholder.setStyleSheet("color: #888; font-size: 13px; padding: 24px;")

        self._inv_tabs = QTabWidget()
        self._inv_general = InventoryGrid("General")
        self._inv_tech = InventoryGrid("Technology")
        self._inv_cargo = InventoryGrid("Cargo")
        self._inv_draft = InventoryGrid("Build Grid")

        # Build Grid tab: stacked 2D/3D with toggle button
        self._draft_container = QWidget()
        draft_layout = QVBoxLayout(self._draft_container)
        draft_layout.setContentsMargins(0, 0, 0, 0)

        controls_layout = QHBoxLayout()
        controls_layout.setContentsMargins(0, 0, 0, 0)

        self._view_toggle_btn = QPushButton("Switch to 3D View")
        self._view_toggle_btn.setFixedHeight(28)
        self._view_toggle_btn.clicked.connect(self._toggle_draft_view)
        controls_layout.addWidget(self._view_toggle_btn)

        self._reload_3d_btn = QPushButton("Reload 3D")
        self._reload_3d_btn.setFixedHeight(28)
        self._reload_3d_btn.clicked.connect(self._on_reload_3d)
        controls_layout.addWidget(self._reload_3d_btn)

        controls_layout.addStretch()
        draft_layout.addLayout(controls_layout)

        self._draft_stack = QStackedWidget()
        self._draft_stack.addWidget(self._inv_draft)  # index 0 = 2D

        # Lazy-create 3D view only when toggled (avoids GL init on startup)
        self._3d_view = None
        self._3d_placeholder = QLabel("Loading 3D view...")
        self._3d_placeholder.setAlignment(Qt.AlignCenter)
        self._draft_stack.addWidget(self._3d_placeholder)  # index 1 = 3D placeholder

        draft_layout.addWidget(self._draft_stack)

        self._inv_tabs.addTab(self._inv_general, "General")
        self._inv_tabs.addTab(self._inv_tech, "Technology + Effects")
        self._inv_tabs.addTab(self._inv_cargo, "Cargo")
        self._inv_tabs.addTab(self._draft_container, "Build Grid")
        self._inv_tabs.setVisible(False)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(self._right_placeholder)
        right_layout.addWidget(self._inv_tabs)
        layout.addWidget(right)

    def set_data(self, psd: dict):
        self._data = psd
        self._corvettes = []

        # Find completed corvettes in ShipOwnership
        ships = psd.get("ShipOwnership", [])
        for i, ship in enumerate(ships):
            if _is_corvette_ship(ship):
                self._corvettes.append((i, ship))

        # Check for active draft
        draft_inv = psd.get("CorvetteStorageInventory")
        has_draft = draft_inv is not None and bool(draft_inv.get("Slots"))
        has_any = bool(self._corvettes) or has_draft

        self._empty_label.setVisible(not has_any)
        self._selector_group.setVisible(has_any)
        self._details_group.setVisible(False)
        self._stats_group.setVisible(False)
        self._draft_group.setVisible(False)
        self._summary_group.setVisible(False)

        if not has_any:
            self._inv_tabs.setVisible(False)
            self._right_placeholder.setVisible(True)
            self._right_placeholder.setText(
                "No corvettes or active draft found in this save."
            )
            self._inv_general.set_inventory({})
            self._inv_tech.set_inventory({})
            self._inv_cargo.set_inventory({})
            self._inv_draft.set_inventory({})
            return
        self._inv_tabs.setVisible(True)
        self._right_placeholder.setVisible(False)

        # Populate dropdown
        self._corvette_combo.blockSignals(True)
        self._corvette_combo.clear()
        for ship_idx, ship in self._corvettes:
            name = ship.get("Name", "") or f"Corvette {ship_idx + 1}"
            inv_class = ship.get("Inventory", {}).get("Class", {}).get(
                "InventoryClass", "?"
            )
            self._corvette_combo.addItem(f"{name} ({inv_class})")
        if has_draft:
            draft_name = psd.get("CorvetteEditShipName", "") or "Active Draft"
            self._corvette_combo.addItem(f"[Draft] {draft_name}")
        self._corvette_combo.blockSignals(False)

        if self._corvette_combo.count() > 0:
            self._corvette_combo.setCurrentIndex(0)
            self._on_corvette_selected(0)

    def _toggle_draft_view(self):
        """Toggle between 2D and 3D views for the build grid."""
        current = self._draft_stack.currentIndex()
        if current == 0:
            # Switch to 3D
            if self._3d_view is None:
                try:
                    from nmstoolkit.gui.widgets.corvette_3d_view import Corvette3DView
                    self._3d_view = Corvette3DView()
                    self._draft_stack.removeWidget(self._3d_placeholder)
                    self._3d_placeholder.deleteLater()
                    self._3d_placeholder = None
                    self._draft_stack.addWidget(self._3d_view)
                    self._load_cached_meshes()
                except Exception as exc:
                    # OpenGL not available — show error and stay on 2D
                    if self._3d_placeholder is not None:
                        self._3d_placeholder.setText(
                            f"3D view unavailable: {exc}"
                        )
                    return
            # Feed currently selected data to 3D view.
            self._feed_3d_view(force_reload=True)
            self._draft_stack.setCurrentIndex(1)
            self._view_toggle_btn.setText("Switch to 2D Grid")
        else:
            # Switch to 2D
            self._draft_stack.setCurrentIndex(0)
            self._view_toggle_btn.setText("Switch to 3D View")

    def _load_cached_meshes(self):
        """Load cached mesh data into the 3D view if available."""
        if self._3d_view is None:
            return
        try:
            from nmstoolkit.core.corvette_mesh_pipeline import CorvetteMeshPipeline
            cache_dir = self._mesh_cache_dir()
            if not cache_dir.exists():
                return
            pipeline = CorvetteMeshPipeline(cache_dir=cache_dir)
            for module_id in pipeline.list_cached():
                entry = pipeline.load_entry(module_id)
                if entry is not None and entry.meshes:
                    self._3d_view.set_mesh_data(module_id, entry.meshes)
                    if entry.texture_path and entry.texture_path.exists():
                        self._3d_view.set_texture(module_id, entry.texture_path)
        except Exception:
            pass

    def _load_missing_meshes_from_gamefiles(self, draft_inv: dict, force: bool = False) -> None:
        """Load missing module meshes directly from gamefiles (on-demand)."""
        if self._3d_view is None:
            return

        required = _required_corvette_modules(draft_inv)
        if not required:
            return

        if force:
            for module_id in required:
                self._3d_view._mesh_data.pop(module_id, None)  # type: ignore[attr-defined]
                self._3d_view._mesh_cache.pop(module_id, None)  # type: ignore[attr-defined]

        loaded = set(getattr(self._3d_view, "_mesh_data", {}).keys())
        missing = sorted(required - loaded)
        if not missing:
            return

        settings = QSettings("NMSToolkit", "NMSToolkit")
        game_dir_value = settings.value("game_dir", "")
        if not game_dir_value:
            return

        pak_dir = _resolve_pak_dir(Path(str(game_dir_value)))
        if pak_dir is None:
            return

        mbin_compiler = _find_mbin_compiler(pak_dir)
        if mbin_compiler is None:
            return

        try:
            from nmstoolkit.adapters.hgpak_adapter import HgpakAdapter
            from nmstoolkit.adapters.mbin_compiler_adapter import MbinCompilerAdapter
            from nmstoolkit.core.corvette_mesh_pipeline import CorvetteMeshPipeline

            scene_pak = pak_dir / "NMSARC.EntitySceneMBIN.pak"
            if not scene_pak.exists():
                return

            QApplication.processEvents()
            with HgpakAdapter.from_path(scene_pak) as pak:
                all_files = pak.list_files()
                scene_files = {_normalize_ref(p): p for p in all_files}
                scene_by_module: Dict[str, str] = {}
                for module_id in missing:
                    for cand in _scene_candidates_for_module(module_id):
                        found = scene_files.get(_normalize_ref(cand))
                        if found:
                            scene_by_module[module_id] = found
                            break

                if not scene_by_module:
                    return

                scene_data = pak.extract(paths=list(scene_by_module.values()))

            converter = MbinCompilerAdapter(mbin_compiler)
            scene_exml = converter.convert_batch(scene_data)
            pipeline = CorvetteMeshPipeline(cache_dir=self._mesh_cache_dir())

            # Collect all geometry refs from scene EXML to know what to extract.
            from nmstoolkit.core.corvette_mesh_pipeline import list_geometry_refs

            required_geo_refs: set[str] = set()
            scene_exml_by_module: Dict[str, str] = {}
            for module_id, scene_path in scene_by_module.items():
                exml = scene_exml.get(scene_path)
                if not exml:
                    continue
                scene_exml_by_module[module_id] = exml
                for geo_ref in list_geometry_refs(exml):
                    required_geo_refs.add(_normalize_ref(geo_ref))

            if not required_geo_refs:
                return

            # Extract geometry binaries from mesh paks (adapter I/O).
            # Include .geometry.data.mbin files alongside .geometry.mbin
            # so parse_geometry_raw_stream can decode real mesh data.
            data_refs = {g.replace(".geometry.mbin", ".geometry.data.mbin")
                         for g in required_geo_refs}
            mesh_paks = sorted(pak_dir.glob("NMSARC.Mesh*.pak"))
            geo_map: Dict[str, bytes] = {}
            wanted = set(required_geo_refs) | data_refs
            wanted_pc = {g + ".pc" for g in wanted}

            for mesh_pak in mesh_paks:
                if not (wanted or wanted_pc):
                    break
                with HgpakAdapter.from_path(mesh_pak) as pak:
                    files = pak.list_files()
                    known = {_normalize_ref(f): f for f in files}
                    to_extract: List[str] = []
                    for ref in list(wanted):
                        found = known.get(ref)
                        if found:
                            to_extract.append(found)
                            wanted.discard(ref)
                            continue
                        found_pc = known.get(ref + ".pc")
                        if found_pc:
                            to_extract.append(found_pc)
                            wanted.discard(ref)
                    for ref in list(wanted_pc):
                        found = known.get(ref)
                        if found:
                            to_extract.append(found)
                            wanted_pc.discard(ref)
                    if not to_extract:
                        continue
                    extracted = pak.extract(paths=to_extract)
                    for geo_path, geo_bytes in extracted.items():
                        norm = _normalize_ref(geo_path)
                        geo_map[norm] = geo_bytes
                        if norm.endswith(".pc"):
                            geo_map[norm[:-3]] = geo_bytes
                        geo_map[geo_path] = geo_bytes
                        geo_map[geo_path.upper()] = geo_bytes
                        if ".geometry.data.mbin" in norm and norm.endswith(".pc"):
                            geo_map[norm[:-3]] = geo_bytes

            # Convert geometry MBINs to EXML for stream/fallback parsing.
            geometry_exml: Dict[str, tuple[str, str]] = {}
            for geo_ref_norm in required_geo_refs:
                geo_bytes = geo_map.get(geo_ref_norm) or geo_map.get(geo_ref_norm + ".pc")
                if geo_bytes is None:
                    continue
                try:
                    geo_exml_str = converter.convert(geo_bytes)
                except Exception:
                    geo_exml_str = ""

                stream_exml_str = ""
                data_ref = geo_ref_norm.replace(".geometry.mbin", ".geometry.data.mbin")
                data_bytes = geo_map.get(data_ref) or geo_map.get(data_ref + ".pc")
                if data_bytes is not None and geo_exml_str:
                    try:
                        stream_exml_str = converter.convert(data_bytes)
                    except Exception:
                        pass

                if geo_exml_str or stream_exml_str:
                    geometry_exml[geo_ref_norm] = (geo_exml_str, stream_exml_str)

            # Delegate extraction to pipeline (domain layer).
            for module_id, exml in scene_exml_by_module.items():
                entry = pipeline.extract_module(
                    module_id=module_id,
                    scene_exml=exml,
                    geometry_data=geo_map,
                    geometry_exml=geometry_exml,
                )
                if entry.meshes:
                    self._3d_view.set_mesh_data(module_id, entry.meshes)

            QApplication.processEvents()
        except Exception:
            # Keep 3D experience non-blocking when gamefile read fails.
            return

    def _on_reload_3d(self) -> None:
        """Reload current draft meshes from gamefiles."""
        if self._3d_view is None:
            self._toggle_draft_view()
            return
        if self._data is None:
            return
        # Drop persisted mesh cache so loader cannot reuse stale proxy meshes.
        try:
            from nmstoolkit.core.corvette_mesh_pipeline import CorvetteMeshPipeline

            pipeline = CorvetteMeshPipeline(cache_dir=self._mesh_cache_dir())
            for module_id in pipeline.list_cached():
                path = self._mesh_cache_dir() / f"{module_id}.mesh.json"
                if path.exists():
                    path.unlink()
        except Exception:
            pass
        self._feed_3d_view(force_reload=True)

    @staticmethod
    def _mesh_cache_dir() -> Path:
        """Return mesh cache directory."""
        return cache_meshes_dir()

    def _on_corvette_selected(self, index):
        if index < 0:
            return

        is_draft = index >= len(self._corvettes)

        if is_draft:
            self._current_index = -1
            self._show_draft()
        else:
            self._current_index = index
            self._show_completed(index)

    def _show_completed(self, combo_index: int):
        """Show a completed corvette's inventories and details."""
        ship_idx, ship = self._corvettes[combo_index]

        # Details
        self._details_group.setVisible(True)
        self._stats_group.setVisible(True)
        self._draft_group.setVisible(False)

        self._name_edit.blockSignals(True)
        self._name_edit.setText(ship.get("Name", ""))
        self._name_edit.blockSignals(False)

        inv = ship.get("Inventory", {})
        inv_class = inv.get("Class", {}).get("InventoryClass", "C")
        self._class_combo.blockSignals(True)
        idx = self._class_combo.findText(inv_class)
        self._class_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self._class_combo.blockSignals(False)

        self._seed_label.setText(str(ship.get("Seed", "—")))

        # Stats
        base_stats = inv.get("BaseStatValues", [])
        stats_by_id = {}
        for bs in base_stats:
            if isinstance(bs, dict):
                stats_by_id[bs.get("BaseStatID", "")] = bs.get("Value", 0)
        for stat_id, spinner in self._stat_spinners.items():
            spinner.blockSignals(True)
            spinner.setValue(stats_by_id.get(stat_id, 0))
            spinner.blockSignals(False)

        # Inventories
        self._inv_general.set_inventory(inv)
        self._inv_tech.set_inventory(ship.get("Inventory_TechOnly", {}))
        cargo_inv = ship.get("Inventory_Cargo", {})
        self._inv_cargo.set_inventory(cargo_inv)
        self._inv_draft.set_inventory({})

        # Show General/Tech/Cargo/Build Grid tabs for completed corvettes.
        # Build Grid may still be useful to inspect active draft state.
        self._inv_tabs.setTabVisible(0, True)
        self._inv_tabs.setTabVisible(1, True)
        self._inv_tabs.setTabVisible(2, _inventory_has_data(cargo_inv))
        self._inv_tabs.setTabVisible(3, True)
        self._inv_tabs.setCurrentIndex(0)

        # Module summary from general inventory
        slots = inv.get("Slots", [])
        self._update_summary(slots)

        # Keep 3D view in sync with current selection if it is active.
        if self._3d_view is not None and self._draft_stack.currentIndex() == 1:
            self._feed_3d_view(force_reload=True)

    def _show_draft(self):
        """Show the active corvette draft."""
        psd = self._data
        draft_inv = psd.get("CorvetteStorageInventory", {})

        self._details_group.setVisible(False)
        self._stats_group.setVisible(False)
        self._draft_group.setVisible(True)

        # Draft details
        ship_idx = psd.get("CorvetteEditAssociatedShipIndex", -1)
        ships = psd.get("ShipOwnership", [])
        if 0 <= ship_idx < len(ships):
            ship = ships[ship_idx]
            ship_name = ship.get("Name", "") or f"Ship {ship_idx + 1}"
            self._draft_ship_label.setText(f"{ship_name} (slot {ship_idx + 1})")
        else:
            self._draft_ship_label.setText("—")

        self._draft_seed_label.setText(str(psd.get("CorvetteDraftShipSeed", 0)))
        layout_data = psd.get("CorvetteStorageLayout", {})
        self._draft_level_label.setText(str(layout_data.get("Level", "—")))

        # Hide General/Tech/Cargo, show Build Grid
        self._inv_tabs.setTabVisible(0, False)
        self._inv_tabs.setTabVisible(1, False)
        self._inv_tabs.setTabVisible(2, False)
        self._inv_tabs.setTabVisible(3, True)
        self._inv_tabs.setCurrentIndex(3)

        self._inv_draft.set_inventory(draft_inv)

        # Update 3D view if it exists (draft mode → always uses grid)
        if self._3d_view is not None:
            self._3d_view.set_modules(draft_inv)
            if self._draft_stack.currentIndex() == 1:
                self._feed_3d_view(force_reload=True)

        # Module summary from draft
        slots = draft_inv.get("Slots", [])
        self._update_summary(slots)

    def _update_summary(self, slots: list):
        """Update the module summary label from slot data."""
        if not slots:
            self._summary_group.setVisible(False)
            return
        self._summary_group.setVisible(True)
        counts = _categorize_modules(slots)
        summary_lines = []
        for category in sorted(counts.keys()):
            summary_lines.append(f"{category}: {counts[category]}")
        self._summary_label.setText("\n".join(summary_lines))

    def _selected_inventory_for_3d(self) -> Optional[dict]:
        """Return currently selected inventory payload for mesh loading."""
        if self._data is None:
            return None
        if self._current_index < 0:
            return self._data.get("CorvetteStorageInventory", {})
        ship = self._current_ship()
        if ship is None:
            return None
        return ship.get("Inventory", {})

    def _feed_3d_view(self, force_reload: bool = True) -> None:
        """Send the appropriate data to the 3D view widget.

        For completed corvettes: extracts hull modules from PersistentPlayerBases
        and uses set_modules_3d() for real 3D positions.
        For draft: uses set_modules() with CorvetteStorageInventory (2D grid).
        Falls back to 2D grid if no ship base found.
        """
        if self._3d_view is None or self._data is None:
            return
        if self._current_index >= 0:
            ship_idx = self._corvettes[self._current_index][0]
            base = _find_corvette_base(self._data, ship_idx)
            if base is not None:
                hull_modules = _extract_hull_modules_3d(base)
                if hull_modules:
                    self._3d_view.set_modules_3d(hull_modules)
                    # Build pseudo-inventory for mesh loading
                    mesh_inv = {
                        "Slots": [{"Id": m["ObjectID"]} for m in hull_modules],
                    }
                    self._load_missing_meshes_from_gamefiles(mesh_inv, force=force_reload)
                    self._3d_view.update()
                    return
        # Draft or fallback: use inventory grid
        selected_inv = self._selected_inventory_for_3d()
        if selected_inv is not None:
            self._3d_view.set_modules(selected_inv)
            self._load_missing_meshes_from_gamefiles(selected_inv, force=force_reload)
            self._3d_view.update()

    def _current_ship(self) -> Optional[dict]:
        """Get the currently selected ship dict, or None for draft."""
        if self._current_index < 0 or self._current_index >= len(self._corvettes):
            return None
        return self._corvettes[self._current_index][1]

    def _on_name_changed(self):
        ship = self._current_ship()
        if ship is not None:
            ship["Name"] = self._name_edit.text()
            # Update combo text
            ship_idx = self._corvettes[self._current_index][0]
            inv_class = ship.get("Inventory", {}).get("Class", {}).get(
                "InventoryClass", "?"
            )
            name = self._name_edit.text() or f"Corvette {ship_idx + 1}"
            self._corvette_combo.setItemText(
                self._current_index, f"{name} ({inv_class})"
            )

    def _on_class_changed(self, text):
        ship = self._current_ship()
        if ship is None:
            return
        inv = ship.get("Inventory", {})
        cls = inv.get("Class", {})
        if isinstance(cls, dict):
            cls["InventoryClass"] = text
        else:
            inv["Class"] = {"InventoryClass": text}
        # Update combo text
        ship_idx = self._corvettes[self._current_index][0]
        name = ship.get("Name", "") or f"Corvette {ship_idx + 1}"
        self._corvette_combo.setItemText(
            self._current_index, f"{name} ({text})"
        )

    def _on_stat_changed(self, stat_id, value):
        ship = self._current_ship()
        if ship is None:
            return
        inv = ship.get("Inventory", {})
        base_stats = inv.get("BaseStatValues", [])
        for bs in base_stats:
            if isinstance(bs, dict) and bs.get("BaseStatID") == stat_id:
                bs["Value"] = value
                return
        base_stats.append({"BaseStatID": stat_id, "Value": value})
        inv["BaseStatValues"] = base_stats
