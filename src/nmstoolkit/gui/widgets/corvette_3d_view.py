"""3D corvette builder viewport — renders module grid as colored cubes.

Uses PySide6's QOpenGLWidget with legacy fixed-function OpenGL.
No external dependencies (PyOpenGL not required).
"""

from __future__ import annotations

import ctypes
import math
from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QColor, QMouseEvent, QWheelEvent
from PySide6.QtOpenGLWidgets import QOpenGLWidget

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


class Corvette3DView(QOpenGLWidget):
    """3D viewport for corvette module visualization.

    Renders modules as colored cubes on a grid. Supports orbit camera.
    """

    module_selected = Signal(int, int, str)  # x, y, item_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self._modules: List[dict] = []  # Slot dicts with Index, Id
        self._grid_width = 10
        self._grid_height = 16
        self._selected: Optional[Tuple[int, int]] = None

        # Camera
        self._cam_yaw = 45.0
        self._cam_pitch = 35.0
        self._cam_distance = 20.0
        self._cam_target = [5.0, 0.0, 8.0]  # Center of grid

        # Mouse tracking
        self._last_mouse_pos = QPoint()
        self._mouse_button = Qt.NoButton

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

    def initializeGL(self):
        """Set up OpenGL state."""
        from PySide6.QtOpenGL import QOpenGLVersionFunctionsFactory
        # Get GL functions — we use the context directly via ctypes
        ctx = self.context()
        if ctx is None:
            return
        # We'll call GL functions through the context's native interface
        self._gl_ready = True

    def resizeGL(self, w, h):
        """Handle resize."""
        pass  # Projection set in paintGL

    def paintGL(self):
        """Render the 3D scene."""
        if not hasattr(self, '_gl_ready'):
            return

        # Import GL functions via ctypes for fixed-function pipeline
        try:
            import ctypes
            if not hasattr(self, '_gl'):
                self._setup_gl()
            gl = self._gl
        except Exception:
            return

        w, h = self.width(), self.height()
        if h == 0:
            h = 1

        gl.glViewport(0, 0, w, h)
        gl.glClearColor(0.12, 0.12, 0.14, 1.0)
        gl.glClear(0x4100)  # GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT
        gl.glEnable(0x0B71)  # GL_DEPTH_TEST

        # Set up projection
        gl.glMatrixMode(0x1701)  # GL_PROJECTION
        gl.glLoadIdentity()
        aspect = w / h
        fov = 45.0
        near, far = 0.1, 100.0
        f = 1.0 / math.tan(math.radians(fov) / 2.0)
        proj = [
            f / aspect, 0, 0, 0,
            0, f, 0, 0,
            0, 0, (far + near) / (near - far), -1,
            0, 0, (2 * far * near) / (near - far), 0,
        ]
        gl.glLoadMatrixf((ctypes.c_float * 16)(*proj))

        # Set up camera (orbit)
        gl.glMatrixMode(0x1700)  # GL_MODELVIEW
        gl.glLoadIdentity()

        # Compute camera position from spherical coords
        yaw_rad = math.radians(self._cam_yaw)
        pitch_rad = math.radians(self._cam_pitch)
        cx = self._cam_target[0] + self._cam_distance * math.cos(pitch_rad) * math.sin(yaw_rad)
        cy = self._cam_target[1] + self._cam_distance * math.sin(pitch_rad)
        cz = self._cam_target[2] + self._cam_distance * math.cos(pitch_rad) * math.cos(yaw_rad)

        self._look_at(gl, cx, cy, cz, *self._cam_target, 0, 1, 0)

        # Enable simple lighting
        gl.glEnable(0x2000)  # GL_LIGHTING
        gl.glEnable(0x4000)  # GL_LIGHT0
        light_pos = (ctypes.c_float * 4)(10.0, 20.0, 10.0, 0.0)
        gl.glLightfv(0x4000, 0x1203, light_pos)  # GL_LIGHT0, GL_POSITION
        light_amb = (ctypes.c_float * 4)(0.3, 0.3, 0.3, 1.0)
        gl.glLightfv(0x4000, 0x1200, light_amb)  # GL_AMBIENT
        light_diff = (ctypes.c_float * 4)(0.8, 0.8, 0.8, 1.0)
        gl.glLightfv(0x4000, 0x1201, light_diff)  # GL_DIFFUSE

        # Draw grid floor
        self._draw_grid(gl)

        # Draw modules
        for slot in self._modules:
            idx = slot.get("Index", {})
            x, z = idx.get("X", 0), idx.get("Y", 0)
            item_id = slot.get("Id", "")
            r, g, b = _get_module_color(item_id)

            is_selected = self._selected == (x, z)
            if is_selected:
                r, g, b = min(1.0, r + 0.3), min(1.0, g + 0.3), min(1.0, b + 0.3)

            self._draw_cube(gl, x, 0, z, r, g, b)

        gl.glDisable(0x2000)  # GL_LIGHTING

    def _setup_gl(self):
        """Load GL functions from the system OpenGL library."""
        import platform
        system = platform.system()
        if system == "Windows":
            self._gl = ctypes.windll.opengl32
        elif system == "Darwin":
            self._gl = ctypes.cdll.LoadLibrary(
                "/System/Library/Frameworks/OpenGL.framework/OpenGL"
            )
        else:
            self._gl = ctypes.cdll.LoadLibrary("libGL.so.1")

        gl = self._gl

        # Set up function signatures
        gl.glViewport.argtypes = [ctypes.c_int] * 4
        gl.glClearColor.argtypes = [ctypes.c_float] * 4
        gl.glClear.argtypes = [ctypes.c_uint]
        gl.glEnable.argtypes = [ctypes.c_uint]
        gl.glDisable.argtypes = [ctypes.c_uint]
        gl.glMatrixMode.argtypes = [ctypes.c_uint]
        gl.glLoadIdentity.argtypes = []
        gl.glLoadMatrixf.argtypes = [ctypes.POINTER(ctypes.c_float)]
        gl.glLightfv.argtypes = [ctypes.c_uint, ctypes.c_uint, ctypes.POINTER(ctypes.c_float)]
        gl.glMaterialfv.argtypes = [ctypes.c_uint, ctypes.c_uint, ctypes.POINTER(ctypes.c_float)]
        gl.glBegin.argtypes = [ctypes.c_uint]
        gl.glEnd.argtypes = []
        gl.glVertex3f.argtypes = [ctypes.c_float] * 3
        gl.glNormal3f.argtypes = [ctypes.c_float] * 3
        gl.glColor3f.argtypes = [ctypes.c_float] * 3
        gl.glColor4f.argtypes = [ctypes.c_float] * 4
        gl.glLineWidth.argtypes = [ctypes.c_float]

    def _look_at(self, gl, ex, ey, ez, cx, cy, cz, ux, uy, uz):
        """Implement gluLookAt manually."""
        fx, fy, fz = cx - ex, cy - ey, cz - ez
        mag = math.sqrt(fx * fx + fy * fy + fz * fz)
        if mag == 0:
            return
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

        m = [
            sx, ux2, -fx, 0,
            sy, uy2, -fy, 0,
            sz, uz2, -fz, 0,
            -(sx * ex + sy * ey + sz * ez),
            -(ux2 * ex + uy2 * ey + uz2 * ez),
            (fx * ex + fy * ey + fz * ez),
            1,
        ]
        gl.glLoadMatrixf((ctypes.c_float * 16)(*m))

    def _draw_grid(self, gl):
        """Draw a floor grid."""
        gl.glDisable(0x2000)  # Disable lighting for lines
        gl.glColor4f(0.3, 0.3, 0.35, 1.0)
        gl.glLineWidth(1.0)
        gl.glBegin(0x0001)  # GL_LINES
        for x in range(self._grid_width + 1):
            gl.glVertex3f(float(x) - 0.5, -0.5, -0.5)
            gl.glVertex3f(float(x) - 0.5, -0.5, float(self._grid_height) - 0.5)
        for z in range(self._grid_height + 1):
            gl.glVertex3f(-0.5, -0.5, float(z) - 0.5)
            gl.glVertex3f(float(self._grid_width) - 0.5, -0.5, float(z) - 0.5)
        gl.glEnd()
        gl.glEnable(0x2000)  # Re-enable lighting

    def _draw_cube(self, gl, x: int, y: int, z: int, r: float, g: float, b: float):
        """Draw a unit cube at grid position (x, y, z)."""
        mat_diff = (ctypes.c_float * 4)(r, g, b, 1.0)
        mat_amb = (ctypes.c_float * 4)(r * 0.4, g * 0.4, b * 0.4, 1.0)
        gl.glMaterialfv(0x0408, 0x1201, mat_diff)  # GL_FRONT_AND_BACK, GL_DIFFUSE
        gl.glMaterialfv(0x0408, 0x1200, mat_amb)   # GL_AMBIENT

        s = 0.45  # Half-size (slightly smaller than 0.5 for gaps)
        cx, cy, cz = float(x), float(y), float(z)

        # 6 faces
        gl.glBegin(0x0007)  # GL_QUADS

        # Top
        gl.glNormal3f(0, 1, 0)
        gl.glVertex3f(cx - s, cy + s, cz - s)
        gl.glVertex3f(cx + s, cy + s, cz - s)
        gl.glVertex3f(cx + s, cy + s, cz + s)
        gl.glVertex3f(cx - s, cy + s, cz + s)

        # Bottom
        gl.glNormal3f(0, -1, 0)
        gl.glVertex3f(cx - s, cy - s, cz + s)
        gl.glVertex3f(cx + s, cy - s, cz + s)
        gl.glVertex3f(cx + s, cy - s, cz - s)
        gl.glVertex3f(cx - s, cy - s, cz - s)

        # Front
        gl.glNormal3f(0, 0, 1)
        gl.glVertex3f(cx - s, cy - s, cz + s)
        gl.glVertex3f(cx - s, cy + s, cz + s)
        gl.glVertex3f(cx + s, cy + s, cz + s)
        gl.glVertex3f(cx + s, cy - s, cz + s)

        # Back
        gl.glNormal3f(0, 0, -1)
        gl.glVertex3f(cx + s, cy - s, cz - s)
        gl.glVertex3f(cx + s, cy + s, cz - s)
        gl.glVertex3f(cx - s, cy + s, cz - s)
        gl.glVertex3f(cx - s, cy - s, cz - s)

        # Right
        gl.glNormal3f(1, 0, 0)
        gl.glVertex3f(cx + s, cy - s, cz + s)
        gl.glVertex3f(cx + s, cy + s, cz + s)
        gl.glVertex3f(cx + s, cy + s, cz - s)
        gl.glVertex3f(cx + s, cy - s, cz - s)

        # Left
        gl.glNormal3f(-1, 0, 0)
        gl.glVertex3f(cx - s, cy - s, cz - s)
        gl.glVertex3f(cx - s, cy + s, cz - s)
        gl.glVertex3f(cx - s, cy + s, cz + s)
        gl.glVertex3f(cx - s, cy - s, cz + s)

        gl.glEnd()

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
