"""3D corvette builder viewport — renders modules with PyOpenGL.

Uses modern OpenGL 3.3+ with GLSL shaders for mesh rendering.
Falls back to colored cubes when mesh cache is not available.
"""

from __future__ import annotations

import array
import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QMouseEvent, QWheelEvent
from PySide6.QtOpenGLWidgets import QOpenGLWidget

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


def _get_module_category(item_id: str) -> str:
    """Get category name for a module ID."""
    uid = item_id.lstrip("^")
    for prefix, category in _MODULE_CATEGORIES.items():
        if uid.startswith(prefix):
            return category
    return "Unknown"


def _get_module_color(item_id: str) -> Tuple[float, float, float]:
    """Get RGB color for a module ID."""
    cat = _get_module_category(item_id)
    return _MODULE_COLORS.get(cat, (0.4, 0.4, 0.4))


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

out vec3 vNormal;
out vec2 vUV;

void main() {
    gl_Position = uMVP * vec4(aPos, 1.0);
    vNormal = mat3(uModel) * aNormal;
    vUV = aUV;
}
"""

_FRAGMENT_SHADER = """\
#version 330 core
in vec3 vNormal;
in vec2 vUV;

uniform sampler2D uTex;
uniform vec3 uTint;
uniform vec3 uLightDir;
uniform int uHasTexture;

out vec4 fragColor;

void main() {
    vec3 n = normalize(vNormal);
    float diff = max(dot(n, uLightDir), 0.0) * 0.7 + 0.3;
    vec3 baseCol;
    if (uHasTexture == 1) {
        baseCol = texture(uTex, vUV).rgb;
    } else {
        baseCol = uTint;
    }
    fragColor = vec4(baseCol * diff, 1.0);
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
        self._selected: Optional[Tuple[int, int]] = None

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

        self.setMinimumSize(400, 300)
        self.setFocusPolicy(Qt.StrongFocus)

    def set_modules(self, inventory: dict):
        """Set module data from a CorvetteStorageInventory dict."""
        self._grid_width = inventory.get("Width", 10)
        self._grid_height = inventory.get("Height", 16)
        self._modules = [
            s for s in inventory.get("Slots", [])
            if s.get("Id", "")
        ]
        self._cam_target = [self._grid_width / 2.0, 0.0, self._grid_height / 2.0]
        self.update()

    def set_mesh_data(self, module_id: str, meshes: List[Mesh]) -> None:
        """Provide parsed mesh data for a module type. Will be uploaded on next paint."""
        self._mesh_data[module_id] = meshes
        # Invalidate cached GPU mesh so it gets re-uploaded
        self._mesh_cache.pop(module_id, None)

    def set_texture(self, module_id: str, png_path: Path) -> None:
        """Set texture for a module type from a PNG file path."""
        # Texture upload happens in paintGL when GL context is current
        self._pending_textures = getattr(self, "_pending_textures", {})
        self._pending_textures[module_id] = png_path

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
        self._draw_grid(vp)

        # Draw modules
        light_dir = _normalize((0.5, 0.8, 0.6))

        GL.glUseProgram(self._shader_program)
        loc_mvp = GL.glGetUniformLocation(self._shader_program, "uMVP")
        loc_model = GL.glGetUniformLocation(self._shader_program, "uModel")
        loc_tint = GL.glGetUniformLocation(self._shader_program, "uTint")
        loc_light = GL.glGetUniformLocation(self._shader_program, "uLightDir")
        loc_has_tex = GL.glGetUniformLocation(self._shader_program, "uHasTexture")

        GL.glUniform3f(loc_light, *light_dir)

        for slot in self._modules:
            idx = slot.get("Index", {})
            x, z = idx.get("X", 0), idx.get("Y", 0)
            item_id = slot.get("Id", "")
            r, g, b = _get_module_color(item_id)

            is_selected = self._selected == (x, z)
            if is_selected:
                r, g, b = min(1.0, r + 0.3), min(1.0, g + 0.3), min(1.0, b + 0.3)

            model = _mat4_translate(float(x), 0.0, float(z))
            mvp = _mat4_multiply(vp, model)

            GL.glUniformMatrix4fv(loc_mvp, 1, GL.GL_FALSE, mvp)
            GL.glUniformMatrix4fv(loc_model, 1, GL.GL_FALSE, model)
            GL.glUniform3f(loc_tint, r, g, b)

            # Use cached mesh if available, otherwise cube fallback
            stripped_id = item_id.lstrip("^")
            gpu_mesh = self._get_or_upload_mesh(stripped_id)
            has_texture = stripped_id in self._texture_cache

            if has_texture:
                GL.glUniform1i(loc_has_tex, 1)
                GL.glActiveTexture(GL.GL_TEXTURE0)
                GL.glBindTexture(GL.GL_TEXTURE_2D, self._texture_cache[stripped_id])
            else:
                GL.glUniform1i(loc_has_tex, 0)

            GL.glBindVertexArray(gpu_mesh.vao)
            GL.glDrawElements(GL.GL_TRIANGLES, gpu_mesh.index_count, GL.GL_UNSIGNED_INT, None)

        GL.glBindVertexArray(0)
        GL.glUseProgram(0)

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
            # Upload first mesh from the list
            gpu = self._upload_mesh(self._mesh_data[module_id][0])
            self._mesh_cache[module_id] = gpu
            return gpu

        # Fallback: use cube
        return self._cube_gpu

    # ---- Grid ----

    def _build_grid_vao(self) -> _GpuMesh:
        """Build grid lines VAO."""
        return self._rebuild_grid_vao(self._grid_width, self._grid_height)

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
        GL = self._GL
        GL.glUseProgram(self._grid_shader_program)

        loc_mvp = GL.glGetUniformLocation(self._grid_shader_program, "uMVP")
        loc_color = GL.glGetUniformLocation(self._grid_shader_program, "uColor")

        GL.glUniformMatrix4fv(loc_mvp, 1, GL.GL_FALSE, vp)
        GL.glUniform3f(loc_color, 0.3, 0.3, 0.35)

        GL.glBindVertexArray(self._grid_gpu.vao)
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
