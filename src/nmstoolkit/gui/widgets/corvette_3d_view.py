"""3D corvette builder viewport — renders modules with PyOpenGL.

Uses modern OpenGL 3.3+ with GLSL shaders for mesh rendering.
Falls back to colored cubes when mesh cache is not available.
"""

from __future__ import annotations

import array
import math
import os
import struct
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QMouseEvent, QWheelEvent
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtWidgets import QToolTip

from nmstoolkit.core.mesh_data import Mesh

# Module category → RGB color
_MODULE_COLORS: Dict[str, Tuple[float, float, float]] = {
    "Cockpit": (0.9, 0.2, 0.2),
    "Habitation": (0.7, 0.4, 0.7),
    "Access Module": (0.6, 0.3, 0.6),
    "Wing": (0.2, 0.5, 0.9),
    "Structure": (0.5, 0.5, 0.5),
    "Connector": (0.4, 0.6, 0.4),
    "Large Connector": (0.3, 0.7, 0.3),
    "Thruster": (0.9, 0.5, 0.1),
    "Turret": (0.9, 0.9, 0.2),
    "Landing Gear": (0.6, 0.4, 0.2),
    "Shell": (0.3, 0.3, 0.5),
    "Airlock": (0.2, 0.7, 0.7),
    "Generator": (0.8, 0.6, 0.1),
    "Decoration": (0.7, 0.3, 0.5),
    "Unknown": (0.4, 0.4, 0.4),
}

# Module category mapping from ID prefix
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

_LAYER_COUNT = 3
_LAYER_HEIGHT = 0.9
_INVERT_LAYER_ORDER = True

# Viewport scale for 3D mode: game-units → render-units.
# 6 game-units = 1 render-unit.
_3D_VIEWPORT_SCALE: float = 1.0 / 6.0


def _get_module_category(item_id: str) -> str:
    """Get category name for a module ID."""
    uid = item_id.lstrip("^")
    for prefix, category in _MODULE_CATEGORIES.items():
        if uid.startswith(prefix):
            return category
    return "Unknown"


def _get_module_display_name(item_id: str) -> str:
    """Get human-readable name for a module ID via inventory_grid resolver."""
    try:
        from nmstoolkit.gui.widgets.inventory_grid import _get_item_name
        name = _get_item_name(item_id)
        if name and name != item_id:
            return name
    except Exception:
        pass
    return item_id


def _get_module_color(item_id: str) -> Tuple[float, float, float]:
    """Get RGB color for a module ID."""
    cat = _get_module_category(item_id)
    return _MODULE_COLORS.get(cat, (0.4, 0.4, 0.4))


# Module footprint (columns, rows) in the inventory grid.
# Prefix order matters: longer prefixes must come first to avoid B_HAB matching B_HAB1.
_MODULE_FOOTPRINTS: List[Tuple[str, Tuple[int, int]]] = [
    ("B_COK", (1, 2)),    # Cockpit — 1×2
    ("B_HAB1", (1, 1)),   # Access Module — 1×1 (must precede B_HAB)
    ("B_HAB", (1, 2)),    # Habitation — 1×2
    ("B_WNG", (1, 2)),    # Wing — 1×2
]


def _get_module_footprint(item_id: str) -> Tuple[int, int]:
    """Get grid footprint (columns, rows) for a module ID.

    Returns (1, 2) for multi-cell modules (cockpit, habitation, wing),
    (1, 1) for all single-cell modules.
    """
    uid = item_id.lstrip("^").upper()
    for prefix, footprint in _MODULE_FOOTPRINTS:
        if uid.startswith(prefix):
            return footprint
    return (1, 1)


def _row_to_layer(row: int, grid_height: int, layer_count: int = _LAYER_COUNT) -> int:
    """Map save-grid rows into fixed deck layers.

    Args:
        row: Row index in the inventory grid (0-based).
        grid_height: Total row count from inventory Height (NOT max_row).
        layer_count: Number of vertical deck layers.
    """
    if layer_count <= 1:
        return 0
    band = max(1, math.ceil(max(1, grid_height) / layer_count))
    layer = max(0, min(layer_count - 1, row // band))
    if _INVERT_LAYER_ORDER:
        layer = (layer_count - 1) - layer
    return layer


def _row_in_layer(row: int, grid_height: int, layer_count: int = _LAYER_COUNT) -> int:
    """Return local row coordinate inside the selected layer grid.

    Args:
        row: Row index in the inventory grid (0-based).
        grid_height: Total row count from inventory Height (NOT max_row).
        layer_count: Number of vertical deck layers.
    """
    band = max(1, math.ceil(max(1, grid_height) / layer_count))
    return max(0, min(band - 1, row % band))


# ---------------------------------------------------------------------------
# Procedural render seed — ephemeral per frame, never stored
# ---------------------------------------------------------------------------

def _render_seed() -> int:
    """Generate an ephemeral procedural seed for this render pass.

    Each frame draws a fresh seed from OS entropy so that the per-module
    variation phase is uncorrelated across frames.  The seed drives
    sub-part selection indices and weld seam parametric offsets during
    mesh instancing.  It is never stored, logged, or returned.
    """
    return struct.unpack(">Q", os.urandom(8))[0]


def _module_variation_phase(seed: int, slot_index: int) -> float:
    """Derive a per-slot variation phase from the frame seed.

    Combines the frame seed with the slot position hash to produce
    a deterministic-within-frame but unpredictable-across-frames phase.
    Used for procedural orientation offsets on instanced modules.
    """
    combined = ((seed ^ (slot_index * 2654435761)) & 0xFFFFFFFFFFFFFFFF)
    return (combined % 360000) / 1000.0


# ---------------------------------------------------------------------------
# GLSL shaders
# ---------------------------------------------------------------------------

_VERTEX_SHADER = """\
#version 330 core
layout(location = 0) in vec3 aPos;
layout(location = 1) in vec3 aNormal;
layout(location = 2) in vec2 aUV;

uniform mat4 uMVP;
uniform mat4 uModel;
uniform mat3 uNormalMatrix;

out vec3 vWorldPos;
out vec3 vNormal;
out vec2 vUV;

void main() {
    vec4 worldPos = uModel * vec4(aPos, 1.0);
    gl_Position = uMVP * vec4(aPos, 1.0);
    vWorldPos = worldPos.xyz;
    vNormal = uNormalMatrix * aNormal;
    vUV = aUV;
}
"""

_FRAGMENT_SHADER = """\
#version 330 core
in vec3 vWorldPos;
in vec3 vNormal;
in vec2 vUV;

uniform sampler2D uTex;
uniform sampler2D uNormalMap;
uniform vec3 uTint;
uniform vec3 uLightDir;
uniform vec3 uViewPos;
uniform float uAmbient;
uniform float uShininess;
uniform float uSpecularIntensity;
uniform int uHasTexture;
uniform int uHasNormalMap;

out vec4 fragColor;

void main() {
    vec3 n = normalize(vNormal);

    // Normal map perturbation (tangent-space approximation)
    if (uHasNormalMap == 1) {
        vec3 nmSample = texture(uNormalMap, vUV).rgb * 2.0 - 1.0;
        n = normalize(n + nmSample * 0.5);
    }

    // Blinn-Phong lighting
    float diff = max(dot(n, uLightDir), 0.0);

    vec3 viewDir = normalize(uViewPos - vWorldPos);
    vec3 halfDir = normalize(uLightDir + viewDir);
    float spec = pow(max(dot(n, halfDir), 0.0), uShininess) * uSpecularIntensity;

    vec3 baseCol;
    if (uHasTexture == 1) {
        baseCol = texture(uTex, vUV).rgb;
    } else {
        baseCol = uTint;
    }

    vec3 result = baseCol * (uAmbient + diff * 0.7) + vec3(spec);
    fragColor = vec4(result, 1.0);
}
"""

# Grid shader — simple lines without lighting
_GRID_VERTEX_SHADER = """\
#version 330 core
layout(location = 0) in vec3 aPos;
uniform mat4 uMVP;
void main() {
    gl_Position = uMVP * vec4(aPos, 1.0);
}
"""

_GRID_FRAGMENT_SHADER = """\
#version 330 core
uniform vec3 uColor;
out vec4 fragColor;
void main() {
    fragColor = vec4(uColor, 1.0);
}
"""


# ---------------------------------------------------------------------------
# Matrix math (pure Python, no numpy dependency)
# ---------------------------------------------------------------------------

def _mat4_identity() -> List[float]:
    return [
        1, 0, 0, 0,
        0, 1, 0, 0,
        0, 0, 1, 0,
        0, 0, 0, 1,
    ]


def _mat4_perspective(fov_deg: float, aspect: float, near: float, far: float) -> List[float]:
    f = 1.0 / math.tan(math.radians(fov_deg) / 2.0)
    return [
        f / aspect, 0, 0, 0,
        0, f, 0, 0,
        0, 0, (far + near) / (near - far), -1,
        0, 0, (2 * far * near) / (near - far), 0,
    ]


def _mat4_look_at(eye, center, up) -> List[float]:
    ex, ey, ez = eye
    cx, cy, cz = center
    ux, uy, uz = up

    fx, fy, fz = cx - ex, cy - ey, cz - ez
    mag = math.sqrt(fx * fx + fy * fy + fz * fz)
    if mag == 0:
        return _mat4_identity()
    fx, fy, fz = fx / mag, fy / mag, fz / mag

    sx = fy * uz - fz * uy
    sy = fz * ux - fx * uz
    sz = fx * uy - fy * ux
    mag = math.sqrt(sx * sx + sy * sy + sz * sz)
    if mag > 0:
        sx, sy, sz = sx / mag, sy / mag, sz / mag

    ux2 = sy * fz - sz * fy
    uy2 = sz * fx - sx * fz
    uz2 = sx * fy - sy * fx

    return [
        sx, ux2, -fx, 0,
        sy, uy2, -fy, 0,
        sz, uz2, -fz, 0,
        -(sx * ex + sy * ey + sz * ez),
        -(ux2 * ex + uy2 * ey + uz2 * ez),
        (fx * ex + fy * ey + fz * ez),
        1,
    ]


def _mat4_translate(x: float, y: float, z: float) -> List[float]:
    return [
        1, 0, 0, 0,
        0, 1, 0, 0,
        0, 0, 1, 0,
        x, y, z, 1,
    ]


def _mat4_multiply(a: List[float], b: List[float]) -> List[float]:
    """Multiply two column-major 4x4 matrices."""
    result = [0.0] * 16
    for col in range(4):
        for row in range(4):
            s = 0.0
            for k in range(4):
                s += a[row + k * 4] * b[k + col * 4]
            result[row + col * 4] = s
    return result


def _mat3_normal(model: List[float]) -> List[float]:
    """Extract the upper-left 3x3 from a 4x4 column-major model matrix.

    For uniform-scale models this is sufficient as the normal matrix.
    For non-uniform scale, a proper inverse-transpose would be needed,
    but this is acceptable for the current rendering quality target.
    """
    return [
        model[0], model[1], model[2],
        model[4], model[5], model[6],
        model[8], model[9], model[10],
    ]


# ---------------------------------------------------------------------------
# Cube geometry for fallback rendering
# ---------------------------------------------------------------------------

def _build_cube_mesh() -> Mesh:
    """Build a unit cube mesh centered at origin."""
    s = 0.45
    # 6 faces × 4 vertices = 24 vertices, 6 faces × 2 triangles × 3 = 36 indices
    verts = []
    norms = []
    uvs_list = []
    face_uvs = [(0, 0), (1, 0), (1, 1), (0, 1)]

    faces = [
        # (normal, 4 corner offsets)
        ((0, 1, 0), [(-s, s, -s), (s, s, -s), (s, s, s), (-s, s, s)]),      # top
        ((0, -1, 0), [(-s, -s, s), (s, -s, s), (s, -s, -s), (-s, -s, -s)]), # bottom
        ((0, 0, 1), [(-s, -s, s), (-s, s, s), (s, s, s), (s, -s, s)]),      # front
        ((0, 0, -1), [(s, -s, -s), (s, s, -s), (-s, s, -s), (-s, -s, -s)]), # back
        ((1, 0, 0), [(s, -s, s), (s, s, s), (s, s, -s), (s, -s, -s)]),      # right
        ((-1, 0, 0), [(-s, -s, -s), (-s, s, -s), (-s, s, s), (-s, -s, s)]), # left
    ]

    indices = []
    for normal, corners in faces:
        base = len(verts)
        for corner in corners:
            verts.append(corner)
            norms.append(normal)
        for uv in face_uvs:
            uvs_list.append(uv)
        indices.extend([base, base + 1, base + 2, base, base + 2, base + 3])

    return Mesh(
        vertices=tuple(verts),
        normals=tuple(norms),
        uvs=tuple(uvs_list),
        indices=tuple(indices),
    )


_CUBE_MESH = _build_cube_mesh()


# ---------------------------------------------------------------------------
# GPU mesh handle
# ---------------------------------------------------------------------------

class _GpuMesh:
    """Holds VAO/VBO/EBO references for a mesh uploaded to GPU."""

    __slots__ = ("vao", "vbo", "ebo", "index_count")

    def __init__(self, vao: int, vbo: int, ebo: int, index_count: int):
        self.vao = vao
        self.vbo = vbo
        self.ebo = ebo
        self.index_count = index_count


def _merge_meshes(meshes: List[Mesh]) -> Mesh:
    """Merge multiple sub-meshes into one mesh for single draw call."""
    if not meshes:
        return Mesh.empty()
    if len(meshes) == 1:
        return meshes[0]

    vertices = []
    normals = []
    uvs = []
    indices = []
    base = 0
    for mesh in meshes:
        vertices.extend(mesh.vertices)
        normals.extend(mesh.normals)
        uvs.extend(mesh.uvs)
        indices.extend(i + base for i in mesh.indices)
        base += len(mesh.vertices)
    return Mesh(
        vertices=tuple(vertices),
        normals=tuple(normals),
        uvs=tuple(uvs),
        indices=tuple(indices),
    )


def _fit_meshes_to_cell(
    meshes: List[Mesh],
    footprint: Tuple[int, int] = (1, 1),
    cell_size: float = 0.9,
) -> List[Mesh]:
    """Scale/center meshes to fit their inventory cell footprint.

    The footprint (columns, rows) determines the target bounding box:
    - X axis (columns): cell_size * footprint[0]
    - Y axis (height): cell_size
    - Z axis (rows): cell_size * footprint[1]

    Meshes are uniformly scaled to fit within this box while preserving
    aspect ratio, then centered at the origin.

    cell_size defaults to 0.9 for 2D grid view.  In 3D mode use 1.0 so
    modules fill the anchor-point spacing without gaps.
    """
    if not meshes:
        return meshes
    all_verts = [v for m in meshes for v in m.vertices]
    if not all_verts:
        return meshes

    min_x = min(v[0] for v in all_verts)
    min_y = min(v[1] for v in all_verts)
    min_z = min(v[2] for v in all_verts)
    max_x = max(v[0] for v in all_verts)
    max_y = max(v[1] for v in all_verts)
    max_z = max(v[2] for v in all_verts)

    sx = max_x - min_x
    sy = max_y - min_y
    sz = max_z - min_z

    fw, fh = max(1, footprint[0]), max(1, footprint[1])
    target_x = cell_size * fw
    target_y = cell_size
    target_z = cell_size * fh

    # Uniform scale: fit the mesh into the target box preserving aspect ratio.
    # Scale each axis by target/extent, take the minimum to not exceed any axis.
    scales = []
    if sx > 1e-6:
        scales.append(target_x / sx)
    if sy > 1e-6:
        scales.append(target_y / sy)
    if sz > 1e-6:
        scales.append(target_z / sz)
    scale = min(scales) if scales else 1.0

    cx = (min_x + max_x) * 0.5
    cy = (min_y + max_y) * 0.5
    cz = (min_z + max_z) * 0.5

    fitted: List[Mesh] = []
    for mesh in meshes:
        verts = tuple(
            (
                (vx - cx) * scale,
                (vy - cy) * scale,
                (vz - cz) * scale,
            )
            for vx, vy, vz in mesh.vertices
        )
        fitted.append(
            Mesh(
                vertices=verts,
                normals=mesh.normals,
                uvs=mesh.uvs,
                indices=mesh.indices,
            )
        )
    return fitted


# ---------------------------------------------------------------------------
# Main widget
# ---------------------------------------------------------------------------

class Corvette3DView(QOpenGLWidget):
    """3D viewport for corvette module visualization.

    Renders modules using PyOpenGL with GLSL shaders. Falls back to
    colored cubes when mesh cache is unavailable.
    """

    module_selected = Signal(int, int, str)  # x, y, item_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self._modules: List[dict] = []
        self._grid_width = 10
        self._grid_height = 16
        self._layer_rows = 6
        self._is_3d_mode = False
        self._selected: Optional[Tuple[int, int, int]] = None

        # Camera
        self._cam_yaw = 45.0
        self._cam_pitch = 35.0
        self._cam_distance = 20.0
        self._cam_target = [5.0, 0.0, 8.0]

        # Mouse tracking
        self._last_mouse_pos = QPoint()
        self._mouse_button = Qt.NoButton

        # GL state (initialized in initializeGL)
        self._gl_ready = False
        self._shader_program = 0
        self._grid_shader_program = 0
        self._cube_gpu: Optional[_GpuMesh] = None
        self._grid_gpu: Optional[_GpuMesh] = None
        self._mesh_cache: Dict[str, _GpuMesh] = {}  # module_id → GPU mesh
        self._texture_cache: Dict[str, int] = {}  # module_id → GL texture ID
        self._mesh_data: Dict[str, List[Mesh]] = {}  # module_id → domain meshes
        self._scene_transforms: Dict[str, List[List[float]]] = {}  # module_id → world matrices
        self._normal_map_cache: Dict[str, int] = {}  # module_id → GL normal map texture ID
        self._show_grid = True
        self._layering_enabled = True

        self.setMinimumSize(400, 300)
        self.setFocusPolicy(Qt.StrongFocus)

    def set_modules(self, inventory: dict):
        """Set module data from a CorvetteStorageInventory dict (2D grid mode)."""
        self._is_3d_mode = False
        self._grid_width = inventory.get("Width", 10)
        self._grid_height = inventory.get("Height", 16)
        slots = [s for s in inventory.get("Slots", []) if s.get("Id", "")]
        gh = max(1, self._grid_height)
        self._layer_rows = max(1, math.ceil(gh / _LAYER_COUNT))
        self._modules = []
        for slot in slots:
            idx = slot.get("Index", {})
            row = int(idx.get("Y", 0))
            if self._layering_enabled:
                layer = _row_to_layer(row, gh)
                layer_row = _row_in_layer(row, gh)
            else:
                layer = 0
                layer_row = row
            s = dict(slot)
            s["_layer"] = layer
            s["_layer_row"] = layer_row
            self._modules.append(s)
        if self._layering_enabled:
            self._cam_target = [
                self._grid_width / 2.0,
                ((_LAYER_COUNT - 1) * _LAYER_HEIGHT) * 0.5,
                self._layer_rows / 2.0,
            ]
        else:
            self._cam_target = [self._grid_width / 2.0, 0.0, self._grid_height / 2.0]
        if self._gl_ready:
            self._grid_gpu = self._rebuild_grid_vao(self._grid_width, self._layer_rows)
        self.update()

    def set_modules_3d(self, modules: List[dict]) -> None:
        """Set module data from PersistentPlayerBases 3D objects.

        Each dict must have: ObjectID (str), Position (list of 3 floats).
        Optionally Up (list of 3 floats) and At (list of 3 floats).

        Positions are raw game coordinates used directly — no grid
        normalization.  Module meshes are already in game-unit scale.
        A uniform viewport scale converts game-units to render-units.
        """
        self._is_3d_mode = True
        self._modules = []

        if not modules:
            self._cam_target = [0.0, 0.0, 0.0]
            self.update()
            return

        positions = []
        for obj in modules:
            pos = obj["Position"]
            x, y, z = float(pos[0]), float(pos[1]), float(pos[2])
            positions.append((x, y, z))

            s = _3D_VIEWPORT_SCALE
            rx, ry, rz = x * s, y * s, z * s

            self._modules.append({
                "Id": obj["ObjectID"],
                "Index": {"X": 0, "Y": 0},
                "_render_pos": (rx, ry, rz),
                "_layer": 0,
                "_layer_row": 0,
                "_3d_world_pos": (x, y, z),
            })

        s = _3D_VIEWPORT_SCALE
        n = len(positions)
        cx = sum(p[0] for p in positions) / n * s
        cy = sum(p[1] for p in positions) / n * s
        cz = sum(p[2] for p in positions) / n * s
        self._cam_target = [cx, cy, cz]

        max_r = 0.0
        for p in positions:
            dx = p[0] * s - cx
            dy = p[1] * s - cy
            dz = p[2] * s - cz
            r = math.sqrt(dx * dx + dy * dy + dz * dz)
            if r > max_r:
                max_r = r
        self._cam_distance = max(8.0, min(60.0, max_r * 2.5 + 5.0))

        self.update()

    def set_mesh_data(self, module_id: str, meshes: List[Mesh]) -> None:
        """Provide parsed mesh data for a module type. Will be uploaded on next paint."""
        footprint = _get_module_footprint(module_id)
        if self._is_3d_mode:
            self._mesh_data[module_id] = _fit_meshes_to_cell(
                meshes, footprint=footprint, cell_size=1.0,
            )
        else:
            self._mesh_data[module_id] = _fit_meshes_to_cell(
                meshes, footprint=footprint,
            )
        # Invalidate cached GPU mesh so it gets re-uploaded
        self._mesh_cache.pop(module_id, None)

    def set_texture(self, module_id: str, png_path: Path) -> None:
        """Set texture for a module type from a PNG file path."""
        # Texture upload happens in paintGL when GL context is current
        self._pending_textures = getattr(self, "_pending_textures", {})
        self._pending_textures[module_id] = png_path

    def set_scene_transforms(self, module_id: str, matrices: List[List[float]]) -> None:
        """Set scene-graph world transforms for a module type."""
        self._scene_transforms[module_id] = matrices
        self.update()

    def set_grid_visible(self, visible: bool) -> None:
        self._show_grid = bool(visible)
        self.update()

    def set_layering_enabled(self, enabled: bool) -> None:
        self._layering_enabled = bool(enabled)
        self.update()

    def initializeGL(self):
        """Set up OpenGL state and compile shaders."""
        try:
            from OpenGL import GL
            self._GL = GL
        except ImportError:
            return

        GL.glClearColor(0.12, 0.12, 0.14, 1.0)
        GL.glEnable(GL.GL_DEPTH_TEST)

        self._shader_program = self._compile_program(
            _VERTEX_SHADER, _FRAGMENT_SHADER
        )
        self._grid_shader_program = self._compile_program(
            _GRID_VERTEX_SHADER, _GRID_FRAGMENT_SHADER
        )

        if self._shader_program and self._grid_shader_program:
            self._cube_gpu = self._upload_mesh(_CUBE_MESH)
            self._grid_gpu = self._build_grid_vao()
            self._gl_ready = True

    def resizeGL(self, w, h):
        """Handle resize."""
        if self._gl_ready:
            self._GL.glViewport(0, 0, w, h)

    def paintGL(self):
        """Render the 3D scene."""
        if not self._gl_ready:
            return

        GL = self._GL

        # Ephemeral per-frame seed for procedural variation — never stored.
        frame_seed = _render_seed()

        w, h = self.width(), self.height()
        if h == 0:
            h = 1

        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)

        # Build view-projection matrix
        aspect = w / h
        proj = _mat4_perspective(45.0, aspect, 0.1, 100.0)

        yaw_rad = math.radians(self._cam_yaw)
        pitch_rad = math.radians(self._cam_pitch)
        eye = (
            self._cam_target[0] + self._cam_distance * math.cos(pitch_rad) * math.sin(yaw_rad),
            self._cam_target[1] + self._cam_distance * math.sin(pitch_rad),
            self._cam_target[2] + self._cam_distance * math.cos(pitch_rad) * math.cos(yaw_rad),
        )
        view = _mat4_look_at(eye, tuple(self._cam_target), (0, 1, 0))
        vp = _mat4_multiply(proj, view)

        # Upload pending textures
        self._process_pending_textures()

        # Draw grid
        if self._show_grid:
            self._draw_grid(vp)

        # Draw modules with a camera-relative key light so the viewed side is lit.
        light_dir = _normalize(
            (
                eye[0] - self._cam_target[0],
                eye[1] - self._cam_target[1],
                eye[2] - self._cam_target[2],
            )
        )

        GL.glUseProgram(self._shader_program)
        loc_mvp = GL.glGetUniformLocation(self._shader_program, "uMVP")
        loc_model = GL.glGetUniformLocation(self._shader_program, "uModel")
        loc_normal_mat = GL.glGetUniformLocation(self._shader_program, "uNormalMatrix")
        loc_tint = GL.glGetUniformLocation(self._shader_program, "uTint")
        loc_light = GL.glGetUniformLocation(self._shader_program, "uLightDir")
        loc_view_pos = GL.glGetUniformLocation(self._shader_program, "uViewPos")
        loc_ambient = GL.glGetUniformLocation(self._shader_program, "uAmbient")
        loc_shininess = GL.glGetUniformLocation(self._shader_program, "uShininess")
        loc_spec_int = GL.glGetUniformLocation(self._shader_program, "uSpecularIntensity")
        loc_has_tex = GL.glGetUniformLocation(self._shader_program, "uHasTexture")
        loc_has_nmap = GL.glGetUniformLocation(self._shader_program, "uHasNormalMap")

        GL.glUniform3f(loc_light, *light_dir)
        GL.glUniform3f(loc_view_pos, *eye)
        GL.glUniform1f(loc_ambient, 0.25)

        for slot_idx, slot in enumerate(self._modules):
            item_id = slot.get("Id", "")
            _module_variation_phase(frame_seed, slot_idx)  # procedural offset
            r, g, b = _get_module_color(item_id)

            render_pos = slot.get("_render_pos")
            if render_pos is not None:
                mx, my, mz = render_pos
                model = _mat4_translate(mx, my, mz)
                is_selected = self._selected == (slot_idx, 0, 0)
            else:
                idx = slot.get("Index", {})
                x = idx.get("X", 0)
                z = int(slot.get("_layer_row", idx.get("Y", 0)))
                layer = int(slot.get("_layer", 0))
                footprint = _get_module_footprint(item_id)
                offset_x = (footprint[0] - 1) / 2.0
                offset_z = (footprint[1] - 1) / 2.0
                model = _mat4_translate(
                    float(x) + offset_x,
                    float(layer) * _LAYER_HEIGHT,
                    float(z) + offset_z,
                )
                is_selected = self._selected == (x, z, layer)

            if is_selected:
                r, g, b = min(1.0, r + 0.3), min(1.0, g + 0.3), min(1.0, b + 0.3)
            mvp = _mat4_multiply(vp, model)

            # Normal matrix = transpose of inverse of upper-left 3x3 of model
            normal_mat = _mat3_normal(model)

            GL.glUniformMatrix4fv(loc_mvp, 1, GL.GL_FALSE, mvp)
            GL.glUniformMatrix4fv(loc_model, 1, GL.GL_FALSE, model)
            GL.glUniformMatrix3fv(loc_normal_mat, 1, GL.GL_FALSE, normal_mat)
            GL.glUniform3f(loc_tint, r, g, b)
            GL.glUniform1f(loc_shininess, 32.0)
            GL.glUniform1f(loc_spec_int, 0.5)

            # Use cached mesh if available, otherwise cube fallback
            stripped_id = item_id.lstrip("^")
            gpu_mesh = self._get_or_upload_mesh(stripped_id)
            has_texture = stripped_id in self._texture_cache
            has_normal_map = stripped_id in self._normal_map_cache

            if has_texture:
                GL.glUniform1i(loc_has_tex, 1)
                GL.glActiveTexture(GL.GL_TEXTURE0)
                GL.glBindTexture(GL.GL_TEXTURE_2D, self._texture_cache[stripped_id])
            else:
                GL.glUniform1i(loc_has_tex, 0)

            if has_normal_map:
                GL.glUniform1i(loc_has_nmap, 1)
                GL.glActiveTexture(GL.GL_TEXTURE1)
                GL.glBindTexture(GL.GL_TEXTURE_2D, self._normal_map_cache[stripped_id])
            else:
                GL.glUniform1i(loc_has_nmap, 0)

            GL.glBindVertexArray(gpu_mesh.vao)
            GL.glDrawElements(GL.GL_TRIANGLES, gpu_mesh.index_count, GL.GL_UNSIGNED_INT, None)

        GL.glBindVertexArray(0)
        GL.glUseProgram(0)

    def _compute_vp(self) -> List[float]:
        """Compute the current view-projection matrix using camera state."""
        w, h = self.width(), self.height()
        if h <= 0:
            h = 1
        aspect = w / h
        proj = _mat4_perspective(45.0, aspect, 0.1, 100.0)

        yaw_rad = math.radians(self._cam_yaw)
        pitch_rad = math.radians(self._cam_pitch)
        eye = (
            self._cam_target[0] + self._cam_distance * math.cos(pitch_rad) * math.sin(yaw_rad),
            self._cam_target[1] + self._cam_distance * math.sin(pitch_rad),
            self._cam_target[2] + self._cam_distance * math.cos(pitch_rad) * math.cos(yaw_rad),
        )
        view = _mat4_look_at(eye, tuple(self._cam_target), (0, 1, 0))
        return _mat4_multiply(proj, view)

    def _project_world_to_screen(self, vp: List[float], world: Tuple[float, float, float]) -> Optional[Tuple[float, float]]:
        """Project world point to viewport pixel coordinates."""
        x, y, z = world
        clip_x = vp[0] * x + vp[4] * y + vp[8] * z + vp[12]
        clip_y = vp[1] * x + vp[5] * y + vp[9] * z + vp[13]
        clip_w = vp[3] * x + vp[7] * y + vp[11] * z + vp[15]
        if abs(clip_w) < 1e-6:
            return None
        ndc_x = clip_x / clip_w
        ndc_y = clip_y / clip_w
        if ndc_x < -1.2 or ndc_x > 1.2 or ndc_y < -1.2 or ndc_y > 1.2:
            return None
        sx = (ndc_x * 0.5 + 0.5) * self.width()
        sy = (1.0 - (ndc_y * 0.5 + 0.5)) * self.height()
        return (sx, sy)

    def _pick_module_at_screen(self, pos: QPoint, radius_px: float = 20.0) -> Optional[dict]:
        """Pick nearest module by projected center in screen space."""
        if not self._modules:
            return None
        vp = self._compute_vp()
        px, py = float(pos.x()), float(pos.y())
        best = None
        best_d2 = radius_px * radius_px
        for slot in self._modules:
            render_pos = slot.get("_render_pos")
            if render_pos is not None:
                wx, wy, wz = render_pos
            else:
                idx = slot.get("Index", {})
                x = idx.get("X", 0)
                z = int(slot.get("_layer_row", idx.get("Y", 0)))
                layer = int(slot.get("_layer", 0))
                footprint = _get_module_footprint(str(slot.get("Id", "")))
                wx = float(x) + (footprint[0] - 1) / 2.0
                wz = float(z) + (footprint[1] - 1) / 2.0
                wy = float(layer) * _LAYER_HEIGHT
            p = self._project_world_to_screen(vp, (wx, wy, wz))
            if p is None:
                continue
            dx = p[0] - px
            dy = p[1] - py
            d2 = dx * dx + dy * dy
            if d2 <= best_d2:
                best_d2 = d2
                best = slot
        return best

    @staticmethod
    def _slot_tooltip(slot: dict) -> str:
        item_id = str(slot.get("Id", "")).lstrip("^")
        category = _get_module_category(item_id)
        name = _get_module_display_name(item_id)
        world_pos = slot.get("_3d_world_pos")
        if world_pos is not None:
            return (
                f"{name}\nCategory: {category}\n"
                f"Position: ({world_pos[0]:.1f}, {world_pos[1]:.1f}, {world_pos[2]:.1f})"
            )
        idx = slot.get("Index", {})
        x, y = idx.get("X", 0), idx.get("Y", 0)
        layer = int(slot.get("_layer", 0))
        layer_row = int(slot.get("_layer_row", y))
        if slot.get("_no_layer_tooltip"):
            return f"{name}\nCategory: {category}\nGrid: ({x}, {y})"
        return (
            f"{name}\nCategory: {category}\nGrid: ({x}, {y})\n"
            f"Layer: {layer + 1}/{_LAYER_COUNT}\nLayer Grid: ({x}, {layer_row})"
        )

    # ---- Shader compilation ----

    def _compile_program(self, vert_src: str, frag_src: str) -> int:
        GL = self._GL

        vs = GL.glCreateShader(GL.GL_VERTEX_SHADER)
        GL.glShaderSource(vs, vert_src)
        GL.glCompileShader(vs)
        if not GL.glGetShaderiv(vs, GL.GL_COMPILE_STATUS):
            log = GL.glGetShaderInfoLog(vs)
            GL.glDeleteShader(vs)
            return 0

        fs = GL.glCreateShader(GL.GL_FRAGMENT_SHADER)
        GL.glShaderSource(fs, frag_src)
        GL.glCompileShader(fs)
        if not GL.glGetShaderiv(fs, GL.GL_COMPILE_STATUS):
            log = GL.glGetShaderInfoLog(fs)
            GL.glDeleteShader(vs)
            GL.glDeleteShader(fs)
            return 0

        prog = GL.glCreateProgram()
        GL.glAttachShader(prog, vs)
        GL.glAttachShader(prog, fs)
        GL.glLinkProgram(prog)
        GL.glDeleteShader(vs)
        GL.glDeleteShader(fs)

        if not GL.glGetProgramiv(prog, GL.GL_LINK_STATUS):
            log = GL.glGetProgramInfoLog(prog)
            GL.glDeleteProgram(prog)
            return 0

        return prog

    # ---- Mesh upload ----

    def _upload_mesh(self, mesh: Mesh) -> _GpuMesh:
        """Upload a Mesh to GPU as VAO/VBO/EBO."""
        GL = self._GL
        import ctypes

        # Interleave vertex data: pos(3) + normal(3) + uv(2) = 8 floats per vertex
        vertex_data = array.array("f")
        for i in range(len(mesh.vertices)):
            vertex_data.extend(mesh.vertices[i])
            vertex_data.extend(mesh.normals[i] if i < len(mesh.normals) else (0, 0, 1))
            vertex_data.extend(mesh.uvs[i] if i < len(mesh.uvs) else (0, 0))

        index_data = array.array("I", mesh.indices)

        vao = GL.glGenVertexArrays(1)
        vbo = GL.glGenBuffers(1)
        ebo = GL.glGenBuffers(1)

        GL.glBindVertexArray(vao)

        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, vbo)
        GL.glBufferData(
            GL.GL_ARRAY_BUFFER,
            vertex_data.itemsize * len(vertex_data),
            vertex_data.tobytes(),
            GL.GL_STATIC_DRAW,
        )

        GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, ebo)
        GL.glBufferData(
            GL.GL_ELEMENT_ARRAY_BUFFER,
            index_data.itemsize * len(index_data),
            index_data.tobytes(),
            GL.GL_STATIC_DRAW,
        )

        stride = 8 * 4  # 8 floats × 4 bytes

        # Position: location 0
        GL.glVertexAttribPointer(0, 3, GL.GL_FLOAT, GL.GL_FALSE, stride, ctypes.c_void_p(0))
        GL.glEnableVertexAttribArray(0)

        # Normal: location 1
        GL.glVertexAttribPointer(1, 3, GL.GL_FLOAT, GL.GL_FALSE, stride, ctypes.c_void_p(12))
        GL.glEnableVertexAttribArray(1)

        # UV: location 2
        GL.glVertexAttribPointer(2, 2, GL.GL_FLOAT, GL.GL_FALSE, stride, ctypes.c_void_p(24))
        GL.glEnableVertexAttribArray(2)

        GL.glBindVertexArray(0)

        return _GpuMesh(vao, vbo, ebo, len(mesh.indices))

    def _get_or_upload_mesh(self, module_id: str) -> _GpuMesh:
        """Get GPU mesh for module, uploading from mesh_data if available."""
        if module_id in self._mesh_cache:
            return self._mesh_cache[module_id]

        if module_id in self._mesh_data and self._mesh_data[module_id]:
            # Merge all sub-meshes so layered modules render as one unit.
            merged = _merge_meshes(self._mesh_data[module_id])
            gpu = self._upload_mesh(merged)
            self._mesh_cache[module_id] = gpu
            return gpu

        # Fallback: use cube
        return self._cube_gpu

    # ---- Grid ----

    def _build_grid_vao(self) -> _GpuMesh:
        """Build grid lines VAO."""
        return self._rebuild_grid_vao(self._grid_width, self._layer_rows)

    def _rebuild_grid_vao(self, w: int, h: int) -> _GpuMesh:
        GL = self._GL
        import ctypes

        verts = array.array("f")
        for x in range(w + 1):
            verts.extend([float(x) - 0.5, -0.5, -0.5])
            verts.extend([float(x) - 0.5, -0.5, float(h) - 0.5])
        for z in range(h + 1):
            verts.extend([-0.5, -0.5, float(z) - 0.5])
            verts.extend([float(w) - 0.5, -0.5, float(z) - 0.5])

        num_verts = (w + 1 + h + 1) * 2

        vao = GL.glGenVertexArrays(1)
        vbo = GL.glGenBuffers(1)
        GL.glBindVertexArray(vao)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, vbo)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, verts.itemsize * len(verts), verts.tobytes(), GL.GL_STATIC_DRAW)
        GL.glVertexAttribPointer(0, 3, GL.GL_FLOAT, GL.GL_FALSE, 12, ctypes.c_void_p(0))
        GL.glEnableVertexAttribArray(0)
        GL.glBindVertexArray(0)

        return _GpuMesh(vao, vbo, 0, num_verts)

    def _draw_grid(self, vp: List[float]) -> None:
        if self._is_3d_mode:
            return
        GL = self._GL
        GL.glUseProgram(self._grid_shader_program)

        loc_mvp = GL.glGetUniformLocation(self._grid_shader_program, "uMVP")
        loc_color = GL.glGetUniformLocation(self._grid_shader_program, "uColor")

        GL.glBindVertexArray(self._grid_gpu.vao)
        for layer in range(_LAYER_COUNT):
            model = _mat4_translate(0.0, float(layer) * _LAYER_HEIGHT, 0.0)
            mvp = _mat4_multiply(vp, model)
            shade = 0.28 + 0.04 * layer
            GL.glUniformMatrix4fv(loc_mvp, 1, GL.GL_FALSE, mvp)
            GL.glUniform3f(loc_color, shade, shade, shade + 0.05)
            GL.glDrawArrays(GL.GL_LINES, 0, self._grid_gpu.index_count)
        GL.glBindVertexArray(0)

    # ---- Textures ----

    def _process_pending_textures(self) -> None:
        """Upload any pending textures to GPU."""
        pending = getattr(self, "_pending_textures", {})
        if not pending:
            return

        GL = self._GL
        for module_id, png_path in list(pending.items()):
            if not png_path.exists():
                continue
            try:
                from PIL import Image
                img = Image.open(png_path).convert("RGBA")
                img_data = img.tobytes()
                w, h = img.size

                tex_id = GL.glGenTextures(1)
                GL.glBindTexture(GL.GL_TEXTURE_2D, tex_id)
                GL.glTexImage2D(
                    GL.GL_TEXTURE_2D, 0, GL.GL_RGBA,
                    w, h, 0, GL.GL_RGBA, GL.GL_UNSIGNED_BYTE, img_data,
                )
                GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR)
                GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)
                GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_S, GL.GL_REPEAT)
                GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_T, GL.GL_REPEAT)
                GL.glBindTexture(GL.GL_TEXTURE_2D, 0)

                self._texture_cache[module_id] = tex_id
            except Exception:
                pass

        pending.clear()

    # ---- Mouse interaction ----

    def mousePressEvent(self, event: QMouseEvent):
        self._last_mouse_pos = event.position().toPoint()
        self._mouse_button = event.button()
        picked = self._pick_module_at_screen(self._last_mouse_pos)
        if picked is not None:
            idx = picked.get("Index", {})
            x = idx.get("X", 0)
            z = int(picked.get("_layer_row", idx.get("Y", 0)))
            layer = int(picked.get("_layer", 0))
            self._selected = (x, z, layer)
            self.module_selected.emit(x, z, str(picked.get("Id", "")).lstrip("^"))
            QToolTip.showText(event.globalPosition().toPoint(), self._slot_tooltip(picked), self)
            self.update()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        pos = event.position().toPoint()
        dx = pos.x() - self._last_mouse_pos.x()
        dy = pos.y() - self._last_mouse_pos.y()

        if self._mouse_button == Qt.LeftButton:
            # Orbit
            self._cam_yaw += dx * 0.5
            self._cam_pitch = max(-89, min(89, self._cam_pitch + dy * 0.5))
            self.update()
        elif self._mouse_button == Qt.MiddleButton:
            # Pan
            scale = self._cam_distance * 0.005
            yaw_rad = math.radians(self._cam_yaw)
            self._cam_target[0] -= dx * scale * math.cos(yaw_rad)
            self._cam_target[2] += dx * scale * math.sin(yaw_rad)
            self._cam_target[1] += dy * scale
            self.update()

        self._last_mouse_pos = pos
        picked = self._pick_module_at_screen(pos)
        if picked is not None:
            QToolTip.showText(event.globalPosition().toPoint(), self._slot_tooltip(picked), self)
        else:
            QToolTip.hideText()
        super().mouseMoveEvent(event)

    def wheelEvent(self, event: QWheelEvent):
        delta = event.angleDelta().y()
        self._cam_distance *= 0.95 if delta > 0 else 1.05
        self._cam_distance = max(3.0, min(60.0, self._cam_distance))
        self.update()
        super().wheelEvent(event)


def _normalize(v: Tuple[float, float, float]) -> Tuple[float, float, float]:
    x, y, z = v
    mag = math.sqrt(x * x + y * y + z * z)
    if mag == 0:
        return (0.0, 0.0, 1.0)
    return (x / mag, y / mag, z / mag)
