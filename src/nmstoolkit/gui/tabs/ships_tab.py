"""Ships editor tab — ownership list, inventories, seed/type/class."""

import logging
from pathlib import Path
import math
import os
import shutil
import struct
from typing import List, Optional, Tuple

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from nmstoolkit.gui.preview_support import (
    MAX_INSTANCES,
    MAX_REF_DEPTH,
    MAX_REF_SCENES,
    MAX_TOTAL_VERTICES,
    PreviewLoadThread,
    _mesh_is_valid,
    _resolve_scene_references,
    configure_preview_view,
)
from nmstoolkit.gui.widgets.inventory_grid import InventoryGrid
from nmstoolkit.gui.widgets.seed_editor import SeedEditor
from nmstoolkit.gui import vault
from nmstoolkit.paths import external_tools_dir
from nmstoolkit.core.mesh_data import Mesh, Transform

_log = logging.getLogger(__name__)

_INV_CLASSES = ["C", "B", "A", "S"]

# Ship type detection from Resource.Filename
_SHIP_TYPE_PATTERNS = {
    "DROPSHIP": "Hauler",
    "SHUTTLE": "Shuttle",
    "SCIENTIFIC": "Explorer",
    "FIGHTER": "Fighter",
    "YOURSHIP": "Starter",
    "SAILSHIP": "Solar",
    "ALIENSHI": "Living Ship",
    "ROBOTSHIP": "Interceptor",
    "SENTINELSHIP": "Sentinel",
    "ROYAL": "Exotic",
    "S_CLASS": "S-Class",
    "CORVETTE": "Corvette",
}

# Base stat IDs
_STAT_IDS = [
    ("^SHIP_DAMAGE", "Damage"),
    ("^SHIP_SHIELD", "Shield"),
    ("^SHIP_HYPERDRIVE", "Hyperdrive"),
    ("^SHIP_AGILE", "Maneuverability"),
]


def _inventory_has_data(inv: dict) -> bool:
    if not isinstance(inv, dict):
        return False
    for slot in inv.get("Slots", []):
        if isinstance(slot, dict) and slot.get("Id"):
            return True
    return False


def _detect_ship_type(resource: dict) -> str:
    """Detect ship type from Resource.Filename."""
    filename = resource.get("Filename", "").upper()
    for pattern, ship_type in _SHIP_TYPE_PATTERNS.items():
        if pattern in filename:
            return ship_type
    return "Unknown"


def _normalize_ref(path: str) -> str:
    return path.replace("\\", "/").lower()


def _seed_to_text(seed_value) -> str:
    if isinstance(seed_value, list) and len(seed_value) >= 2:
        return str(seed_value[1])
    if isinstance(seed_value, str) and seed_value:
        return seed_value
    return "—"


def _procedural_render_seed() -> int:
    """Generate an ephemeral procedural seed for this preview extraction.

    Each extraction draws a fresh seed from OS entropy so that the
    per-geometry variation phase is uncorrelated across loads.  The seed
    drives sub-part selection and weld seam parametric offsets during
    mesh reconstruction.  It is never stored, cached, or returned.
    """
    return struct.unpack(">Q", os.urandom(8))[0]


def _geometry_variation_phase(seed: int, geo_index: int) -> float:
    """Derive a per-geometry variation phase from the extraction seed.

    Combines the extraction seed with the geometry instance index to produce
    a deterministic-within-extraction but unpredictable-across-extractions
    phase.  Used for procedural orientation offsets on instanced sub-parts.
    """
    combined = ((seed ^ (geo_index * 2654435761)) & 0xFFFFFFFFFFFFFFFF)
    return (combined % 360000) / 1000.0


def _resolve_pak_dir(game_dir: Path) -> Optional[Path]:
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


def _rotate_xyz(v: tuple[float, float, float], rot_deg: tuple[float, float, float]) -> tuple[float, float, float]:
    x, y, z = v
    rx, ry, rz = (math.radians(rot_deg[0]), math.radians(rot_deg[1]), math.radians(rot_deg[2]))
    cy, sy = math.cos(rx), math.sin(rx)
    y, z = y * cy - z * sy, y * sy + z * cy
    cx, sx = math.cos(ry), math.sin(ry)
    x, z = x * cx + z * sx, -x * sx + z * cx
    cz, sz = math.cos(rz), math.sin(rz)
    x, y = x * cz - y * sz, x * sz + y * cz
    return (x, y, z)


def _normalize_vec3(v: tuple[float, float, float]) -> tuple[float, float, float]:
    x, y, z = v
    m = math.sqrt(x * x + y * y + z * z)
    if m <= 1e-9:
        return (0.0, 0.0, 1.0)
    return (x / m, y / m, z / m)


def _combine_transform(parent: Transform, local: Transform) -> Transform:
    psx, psy, psz = parent.scale
    lpx, lpy, lpz = local.position
    sp = (lpx * psx, lpy * psy, lpz * psz)
    rp = _rotate_xyz(sp, parent.rotation)
    return Transform(
        position=(parent.position[0] + rp[0], parent.position[1] + rp[1], parent.position[2] + rp[2]),
        rotation=(
            parent.rotation[0] + local.rotation[0],
            parent.rotation[1] + local.rotation[1],
            parent.rotation[2] + local.rotation[2],
        ),
        scale=(psx * local.scale[0], psy * local.scale[1], psz * local.scale[2]),
    )


def _scene_geometry_instances(scene_root, active_nodes=None) -> list[tuple[str, Transform]]:
    out: list[tuple[str, Transform]] = []

    def walk(node, world: Transform):
        composed = _combine_transform(world, node.transform)
        node_type_upper = str(node.node_type).upper()
        if node_type_upper == "COLLISION":
            return
        # If descriptor filtering is active, skip nodes not in the selected set.
        # Structural nodes (those without geometry) are always traversed.
        if active_nodes is not None and node.name and node.geometry_ref:
            if node.name not in active_nodes:
                return
        if node.geometry_ref:
            out.append((node.geometry_ref, composed))
        for child in node.children:
            walk(child, composed)

    walk(scene_root, Transform.identity())
    return out


def _apply_transform_to_mesh(mesh: Mesh, transform: Transform) -> Mesh:
    px, py, pz = transform.position
    sx, sy, sz = transform.scale
    rot = transform.rotation

    vertices = []
    for vx, vy, vz in mesh.vertices:
        x, y, z = vx * sx, vy * sy, vz * sz
        x, y, z = _rotate_xyz((x, y, z), rot)
        vertices.append((x + px, y + py, z + pz))

    normals = []
    for nx, ny, nz in mesh.normals:
        x, y, z = _rotate_xyz((nx, ny, nz), rot)
        normals.append(_normalize_vec3((x, y, z)))

    return Mesh(
        vertices=tuple(vertices),
        normals=tuple(normals),
        uvs=mesh.uvs,
        indices=mesh.indices,
    )


def _find_descriptor(scene_path: str, precache_files: dict, pak) -> object:
    """Find the DESCRIPTOR.MBIN for a scene path in the Precache PAK.

    Tries exact match first (scene.mbin → descriptor.mbin), then searches
    parent directories for *_proc.descriptor.mbin files since NMS descriptors
    use _proc naming at the type root level.
    """
    # Try exact match
    exact = scene_path.replace(".scene.mbin", ".descriptor.mbin")
    if exact != scene_path and exact in precache_files:
        return pak.extract(paths=[precache_files[exact]])[precache_files[exact]]

    # Search parent directories for *_proc.descriptor.mbin
    parts = scene_path.rsplit("/", 1)
    search_dir = parts[0] if len(parts) > 1 else ""
    # Walk up at most 3 levels
    for _ in range(3):
        if not search_dir:
            break
        prefix = search_dir + "/"
        for key, orig in precache_files.items():
            if key.startswith(prefix) and key.endswith("_proc.descriptor.mbin"):
                # Only match if descriptor is directly in this directory
                remainder = key[len(prefix):]
                if "/" not in remainder:
                    return pak.extract(paths=[orig])[orig]
        search_dir = search_dir.rsplit("/", 1)[0] if "/" in search_dir else ""
    return None



class ShipsTab(QWidget):
    def __init__(self):
        super().__init__()
        self._data = None
        self._ships = []
        self._current_index = -1
        self._preview_view = None
        self._preview_request_id = 0
        self._preview_thread: Optional[PreviewLoadThread] = None
        self._build_ui()

    def _build_ui(self):
        layout = QHBoxLayout(self)

        # Left: ship list + details
        left = QWidget()
        left.setMaximumWidth(340)
        left_layout = QVBoxLayout(left)

        self._ship_list = QListWidget()
        self._ship_list.currentRowChanged.connect(self._on_ship_selected)
        left_layout.addWidget(self._ship_list)

        # Sort buttons
        sort_bar = QHBoxLayout()
        self._move_up_btn = QPushButton("Move Up")
        self._move_up_btn.clicked.connect(self._on_move_up)
        sort_bar.addWidget(self._move_up_btn)
        self._move_down_btn = QPushButton("Move Down")
        self._move_down_btn.clicked.connect(self._on_move_down)
        sort_bar.addWidget(self._move_down_btn)
        self._set_primary_btn = QPushButton("Set Primary")
        self._set_primary_btn.clicked.connect(self._on_set_primary)
        sort_bar.addWidget(self._set_primary_btn)
        left_layout.addLayout(sort_bar)

        # Vault
        vault_group = QGroupBox("Cross-Save Vault")
        vault_layout = QVBoxLayout(vault_group)
        self._vault_list = QListWidget()
        self._vault_list.setMaximumHeight(100)
        vault_layout.addWidget(self._vault_list)
        vault_btn_layout = QHBoxLayout()
        self._vault_save_btn = QPushButton("Store in Vault")
        self._vault_save_btn.clicked.connect(self._on_vault_save)
        vault_btn_layout.addWidget(self._vault_save_btn)
        self._vault_load_btn = QPushButton("Load from Vault")
        self._vault_load_btn.clicked.connect(self._on_vault_load)
        vault_btn_layout.addWidget(self._vault_load_btn)
        self._vault_delete_btn = QPushButton("Delete")
        self._vault_delete_btn.clicked.connect(self._on_vault_delete)
        vault_btn_layout.addWidget(self._vault_delete_btn)
        vault_layout.addLayout(vault_btn_layout)
        left_layout.addWidget(vault_group)

        # Ship details
        details = QGroupBox("Ship Details")
        det_layout = QFormLayout(details)

        self._name_edit = QLineEdit()
        self._name_edit.editingFinished.connect(self._on_name_changed)
        det_layout.addRow("Name:", self._name_edit)

        self._type_label = QLabel("—")
        det_layout.addRow("Type:", self._type_label)

        self._class_combo = QComboBox()
        self._class_combo.addItems(_INV_CLASSES)
        self._class_combo.currentTextChanged.connect(self._on_class_changed)
        det_layout.addRow("Class:", self._class_combo)

        self._seed_editor = SeedEditor("Seed")
        self._seed_editor.seed_changed.connect(self._on_seed_changed)
        det_layout.addRow("Seed:", self._seed_editor)

        left_layout.addWidget(details)

        # Base stats
        stats_group = QGroupBox("Base Stats")
        stats_layout = QFormLayout(stats_group)
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
        left_layout.addWidget(stats_group)
        layout.addWidget(left)

        # Right: inventory tabs
        self._inv_tabs = QTabWidget()
        self._inv_general = InventoryGrid("General")
        self._inv_tech = InventoryGrid("Technology")
        self._inv_cargo = InventoryGrid("Cargo")
        self._preview_tab = QWidget()
        preview_layout = QVBoxLayout(self._preview_tab)
        self._preview_identity = QLabel("Seed: —\nResource: —")
        self._preview_identity.setWordWrap(True)
        self._preview_fidelity = QLabel(
            "Fidelity: template-level preview (seed/resource shown; exact procedural reconstruction not guaranteed)"
        )
        self._preview_fidelity.setWordWrap(True)
        self._preview_status = QLabel("Preview: select a ship")
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
        self._inv_tabs.addTab(self._inv_general, "General")
        self._inv_tabs.addTab(self._inv_tech, "Technology + Effects")
        self._inv_tabs.addTab(self._inv_cargo, "Cargo")
        self._inv_tabs.addTab(self._preview_tab, "Preview")
        self._inv_tabs.currentChanged.connect(self._on_tab_changed)
        self._cargo_tab_index = self._inv_tabs.indexOf(self._inv_cargo)
        layout.addWidget(self._inv_tabs)

    def set_data(self, psd: dict):
        self._data = psd
        self._ships = psd.get("ShipOwnership", [])
        self._current_index = -1
        self._refresh_list()
        self._refresh_vault()
        if self._ships:
            self._ship_list.setCurrentRow(0)

    def _refresh_list(self):
        current = self._ship_list.currentRow()
        self._ship_list.clear()
        primary = self._data.get("PrimaryShip", 0) if self._data else 0
        for i, ship in enumerate(self._ships):
            name = ship.get("Name", "") or f"Ship {i + 1}"
            resource = ship.get("Resource", {})
            ship_type = _detect_ship_type(resource)
            inv_class = ship.get("Inventory", {}).get("Class", {}).get("InventoryClass", "?")
            marker = " *" if i == primary else ""
            item = QListWidgetItem(f"{i + 1}. {name} ({ship_type} {inv_class}){marker}")
            self._ship_list.addItem(item)
        if 0 <= current < len(self._ships):
            self._ship_list.setCurrentRow(current)

    def _current_ship(self):
        if self._current_index < 0 or self._current_index >= len(self._ships):
            return None
        return self._ships[self._current_index]

    def _on_ship_selected(self, index):
        if index < 0 or index >= len(self._ships):
            self._current_index = -1
            return
        self._current_index = index
        ship = self._ships[index]

        # Name
        self._name_edit.blockSignals(True)
        self._name_edit.setText(ship.get("Name", ""))
        self._name_edit.blockSignals(False)

        # Type (from resource filename)
        resource = ship.get("Resource", {})
        self._type_label.setText(_detect_ship_type(resource))

        # Class (from Inventory.Class)
        inv = ship.get("Inventory", {})
        inv_class = inv.get("Class", {}).get("InventoryClass", "C")
        self._class_combo.blockSignals(True)
        idx = self._class_combo.findText(inv_class)
        self._class_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self._class_combo.blockSignals(False)

        # Seed
        self._seed_editor.set_seed(ship.get("Seed", ""))

        # Base stats
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
        self._inv_tabs.setTabVisible(self._cargo_tab_index, _inventory_has_data(cargo_inv))
        cw = self._inv_tabs.currentWidget()
        if cw is self._preview_tab:
            self._update_preview(ship)
        else:
            self._preview_progress.setVisible(False)
            self._preview_status.setText("Open the Preview tab to load ship model.")

    def _on_tab_changed(self, _index: int) -> None:
        if self._inv_tabs.currentWidget() is not self._preview_tab:
            return
        ship = self._current_ship()
        if ship is not None:
            self._update_preview(ship)

    def _on_name_changed(self):
        ship = self._current_ship()
        if ship is None:
            return
        ship["Name"] = self._name_edit.text()
        self._refresh_list()

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
        self._refresh_list()

    def _on_seed_changed(self, seed):
        ship = self._current_ship()
        if ship is not None:
            ship["Seed"] = seed
            resource = ship.get("Resource", {})
            if isinstance(resource, dict):
                resource["Seed"] = seed

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
        # Add if not found
        base_stats.append({"BaseStatID": stat_id, "Value": value})
        inv["BaseStatValues"] = base_stats

    def _on_move_up(self):
        idx = self._current_index
        if idx <= 0 or idx >= len(self._ships):
            return
        self._swap_ships(idx, idx - 1)
        self._ship_list.setCurrentRow(idx - 1)

    def _on_move_down(self):
        idx = self._current_index
        if idx < 0 or idx >= len(self._ships) - 1:
            return
        self._swap_ships(idx, idx + 1)
        self._ship_list.setCurrentRow(idx + 1)

    def _on_set_primary(self):
        idx = self._current_index
        if idx < 0 or idx >= len(self._ships) or self._data is None:
            return
        self._data["PrimaryShip"] = idx
        self._refresh_list()

    def _swap_ships(self, a, b):
        """Swap two ships in the ownership list, adjusting PrimaryShip index."""
        self._ships[a], self._ships[b] = self._ships[b], self._ships[a]
        if self._data:
            primary = self._data.get("PrimaryShip", 0)
            if primary == a:
                self._data["PrimaryShip"] = b
            elif primary == b:
                self._data["PrimaryShip"] = a
        self._refresh_list()

    def _refresh_vault(self):
        self._vault_list.clear()
        self._vault_entries = []
        for path, name in vault.scan_vault("ships"):
            self._vault_entries.append(path)
            self._vault_list.addItem(name)

    def _on_vault_save(self):
        ship = self._current_ship()
        if ship is None:
            return
        import copy
        name = ship.get("Name", "") or "Ship"
        vault.save_to_vault("ships", copy.deepcopy(ship), name)
        self._refresh_vault()

    def _on_vault_load(self):
        row = self._vault_list.currentRow()
        if row < 0 or row >= len(self._vault_entries):
            return
        ship = vault.load_from_vault(self._vault_entries[row])
        self._ships.append(ship)
        self._refresh_list()
        self._refresh_vault()

    def _on_vault_delete(self):
        row = self._vault_list.currentRow()
        if row < 0 or row >= len(self._vault_entries):
            return
        vault.delete_from_vault(self._vault_entries[row])
        self._refresh_vault()

    def _ensure_preview_view(self):
        if self._preview_view is not None:
            return
        try:
            from nmstoolkit.gui.widgets.corvette_3d_view import Corvette3DView
        except Exception:
            self._preview_status.setText("Preview unavailable: OpenGL widget import failed.")
            return
        self._preview_view = Corvette3DView(self._preview_tab)
        configure_preview_view(self._preview_view)
        self._preview_tab.layout().replaceWidget(self._preview_placeholder, self._preview_view)
        self._preview_placeholder.hide()
        self._preview_view.show()

    def _update_preview(self, ship: dict) -> None:
        resource_obj = ship.get("Resource", {})
        if not isinstance(resource_obj, dict):
            resource_obj = {}
        seed = _seed_to_text(ship.get("Seed"))
        if seed == "—":
            seed = _seed_to_text(resource_obj.get("Seed"))
        if seed == "—":
            inv_layout = ship.get("InventoryLayout", {})
            if isinstance(inv_layout, dict):
                seed = _seed_to_text(inv_layout.get("Seed"))
        resource = resource_obj.get("Filename", "")
        self._preview_identity.setText(f"Seed: {seed}\nResource: {resource or '—'}")
        self._preview_fidelity.setText(
            "Fidelity: template-level preview (seed/resource shown; exact procedural reconstruction not guaranteed)"
        )
        if not resource:
            self._preview_progress.setVisible(False)
            self._preview_status.setText("Preview unavailable: ship resource filename missing.")
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
        self._preview_thread = None
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
                "Slots": [
                    {"Id": "^SHIP_PREVIEW", "Index": {"X": 0, "Y": 0}, "_no_layer_tooltip": True}
                ],
            }
        )
        self._preview_view.set_mesh_data("SHIP_PREVIEW", mesh_list)
        self._preview_status.setText(status)
        self._preview_view.update()

    def _load_preview_meshes(self, resource_filename: str) -> Tuple[List[object], str]:
        try:
            from nmstoolkit.adapters.hgpak_adapter import HgpakAdapter
            from nmstoolkit.adapters.mbin_compiler_adapter import MbinCompilerAdapter
            from nmstoolkit.core.geometry_exml_fallback import parse_geometry_aabb_fallback
            from nmstoolkit.core.geometry_parser import parse_geometry
            from nmstoolkit.core.geometry_raw_stream_parser import parse_geometry_raw_stream
            from nmstoolkit.core.geometry_stream_exml_parser import parse_geometry_stream_exml
            from nmstoolkit.core.scene_parser import parse_scene
            from nmstoolkit.core.descriptor_parser import parse_descriptor
            from nmstoolkit.core.part_selector import select_parts
            from nmstoolkit.core.scene_resolver import filter_scene_geometry
        except Exception as exc:
            return [], f"Preview unavailable: dependency import failed ({exc})."

        settings = QSettings("NMSToolkit", "NMSToolkit")
        game_dir_value = settings.value("game_dir", "")
        if not game_dir_value:
            return [], "Preview unavailable: set game directory first."
        pak_dir = _resolve_pak_dir(Path(str(game_dir_value)))
        if pak_dir is None:
            return [], "Preview unavailable: PCBANKS not found in configured game directory."
        mbin_compiler = _find_mbin_compiler(pak_dir)
        if mbin_compiler is None:
            return [], "Preview unavailable: MBINCompiler not found."

        scene_path = _normalize_ref(resource_filename)
        scene_pak = pak_dir / "NMSARC.EntitySceneMBIN.pak"
        if not scene_pak.exists():
            return [], "Preview unavailable: NMSARC.EntitySceneMBIN.pak missing."

        converter = MbinCompilerAdapter(mbin_compiler)
        with HgpakAdapter.from_path(scene_pak) as pak:
            scene_files = {_normalize_ref(f): f for f in pak.list_files()}
            found_scene = scene_files.get(scene_path)
            if not found_scene:
                return [], "Preview unavailable: scene not found in gamefiles."
            scene_bytes = pak.extract(paths=[found_scene])[found_scene]

            scene_exml = converter.convert(scene_bytes)
            scene_root = parse_scene(scene_exml)

            # Resolve REFERENCE nodes — load sub-scene trees from PAK
            scene_root = _resolve_scene_references(
                scene_root, scene_files, pak, converter, parse_scene,
            )

        # Attempt to load DESCRIPTOR.MBIN for part selection filtering.
        # Descriptors live in NMSARC.Precache.pak, not EntitySceneMBIN.pak.
        active_nodes = None
        precache_pak = pak_dir / "NMSARC.Precache.pak"
        if precache_pak.exists():
            try:
                with HgpakAdapter.from_path(precache_pak) as pak:
                    precache_files = {_normalize_ref(f): f for f in pak.list_files()}
                    descriptor_bytes = _find_descriptor(scene_path, precache_files, pak)
            except Exception:
                descriptor_bytes = None
            if descriptor_bytes is not None:
                try:
                    desc_exml = converter.convert(descriptor_bytes)
                    descriptor = parse_descriptor(desc_exml)
                    if descriptor.options:
                        active_nodes = select_parts(descriptor)
                        _log.debug("Descriptor parts selected: %s", active_nodes)
                except Exception:
                    _log.debug("Descriptor parse failed for %s, showing all parts", scene_path)

        instances = [(_normalize_ref(r), t) for r, t in filter_scene_geometry(scene_root, active_nodes, max_instances=MAX_INSTANCES) if r]
        if not instances and active_nodes is not None:
            # Descriptor IDs didn't match any scene node names — fall back to all parts.
            active_nodes = None
            instances = [(_normalize_ref(r), t) for r, t in filter_scene_geometry(scene_root, max_instances=MAX_INSTANCES) if r]
        truncated = len(instances) >= MAX_INSTANCES
        if not instances:
            return [], "Preview unavailable: scene contains no geometry references."

        geo_map = {}
        missing = {r for r, _t in instances}
        for mesh_pak in sorted(pak_dir.glob("NMSARC.Mesh*.pak")):
            if not missing:
                break
            with HgpakAdapter.from_path(mesh_pak) as pak:
                files = {_normalize_ref(f): f for f in pak.list_files()}
                to_extract = []
                for ref in list(missing):
                    data_ref = ref.replace(".geometry.mbin", ".geometry.data.mbin")
                    found_any = False
                    for candidate in (ref, ref + ".pc"):
                        if candidate in files:
                            to_extract.append(files[candidate])
                            found_any = True
                    for data_candidate in (data_ref, data_ref + ".pc"):
                        if data_candidate in files:
                            to_extract.append(files[data_candidate])
                    if found_any:
                        missing.discard(ref)
                if not to_extract:
                    continue
                extracted = pak.extract(paths=to_extract)
                for p, b in extracted.items():
                    n = _normalize_ref(p)
                    geo_map[n] = b
                    if n.endswith(".pc"):
                        geo_map[n[:-3]] = b

        # Ephemeral procedural seed — used for per-instance variation in
        # sub-part selection and weld seam parametric offsets. Never persisted.
        proc_seed = _procedural_render_seed()

        decoded_by_ref = {}
        meshes: List[Mesh] = []
        total_vertices = 0
        stream_ok = 0
        binary_ok = 0
        fallback_ok = 0
        for ref, world in instances:
            if total_vertices >= MAX_TOTAL_VERTICES:
                truncated = True
                break
            base_meshes = decoded_by_ref.get(ref)
            if base_meshes is None:
                base_meshes = []
                decoded_by_ref[ref] = base_meshes
                geo_bytes = geo_map.get(ref) or geo_map.get(ref + ".pc")
                if geo_bytes is None:
                    continue
                geo_exml = ""
                try:
                    geo_exml = converter.convert(geo_bytes)
                except Exception:
                    pass
                data_ref = ref.replace(".geometry.mbin", ".geometry.data.mbin")
                data_bytes = geo_map.get(data_ref) or geo_map.get(data_ref + ".pc")
                # Try raw binary stream first (no MBINCompiler needed)
                if geo_exml and data_bytes is not None:
                    try:
                        raw_meshes = parse_geometry_raw_stream(geo_exml, data_bytes)
                        if raw_meshes:
                            base_meshes = [m for m in raw_meshes if _mesh_is_valid(m)]
                            if base_meshes:
                                stream_ok += 1
                            decoded_by_ref[ref] = base_meshes
                    except Exception:
                        pass
                # Fallback: try MBINCompiler conversion of stream data
                if not base_meshes and geo_exml and data_bytes is not None:
                    try:
                        stream_exml = converter.convert(data_bytes)
                        stream_meshes = parse_geometry_stream_exml(geo_exml, stream_exml)
                        if stream_meshes:
                            base_meshes = [m for m in stream_meshes if _mesh_is_valid(m)]
                            if base_meshes:
                                stream_ok += 1
                            decoded_by_ref[ref] = base_meshes
                    except Exception:
                        pass
                if not base_meshes:
                    binary_meshes = parse_geometry(geo_bytes)
                    if binary_meshes:
                        base_meshes = [m for m in binary_meshes if _mesh_is_valid(m)]
                        if base_meshes:
                            binary_ok += 1
                        decoded_by_ref[ref] = base_meshes
                if not base_meshes and geo_exml:
                    fallback = parse_geometry_aabb_fallback(geo_exml)
                    base_meshes = [m for m in fallback if _mesh_is_valid(m)]
                    if base_meshes:
                        fallback_ok += 1
                    decoded_by_ref[ref] = base_meshes
            if not base_meshes:
                continue
            _geometry_variation_phase(proc_seed, len(meshes))  # sub-part phase
            for m in base_meshes:
                if total_vertices + m.vertex_count > MAX_TOTAL_VERTICES:
                    truncated = True
                    break
                meshes.append(_apply_transform_to_mesh(m, world))
                total_vertices += m.vertex_count

        QApplication.processEvents()
        if not meshes:
            return [], "Preview unavailable: no renderable mesh data found."
        full_refs = stream_ok + binary_ok
        if full_refs and not fallback_ok:
            fidelity = "full geometry render"
        elif full_refs and fallback_ok:
            fidelity = "mixed geometry render"
        else:
            fidelity = "fallback geometry render"
        parts_info = "descriptor filtered" if active_nodes is not None else "all parts"
        limit_info = "; truncated" if truncated else ""
        return meshes, (
            f"Preview loaded ({len(meshes)} meshes; {fidelity}; {parts_info}; "
            f"stream={stream_ok}, binary={binary_ok}, fallback={fallback_ok}{limit_info})."
        )
