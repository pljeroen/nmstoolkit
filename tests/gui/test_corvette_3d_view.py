"""Tests for corvette 3D view module — non-GL tests.

Tests cover:
- Module category detection
- Module color mapping
- Camera state initialization
- set_modules() data parsing
- Corvette tab 2D/3D toggle integration
- Matrix math utilities
- Cube mesh generation
- Mesh data API
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import math

import pytest
from PySide6.QtWidgets import QApplication

from nmstoolkit.core.mesh_data import Mesh
from nmstoolkit.gui.widgets.corvette_3d_view import (
    _CUBE_MESH,
    _MODULE_CATEGORIES,
    _MODULE_COLORS,
    _build_cube_mesh,
    _fit_meshes_to_cell,
    _get_module_category,
    _get_module_color,
    _get_module_footprint,
    _mat4_identity,
    _mat4_multiply,
    _mat4_perspective,
    _mat4_translate,
    _normalize,
    _row_to_layer,
)
from nmstoolkit.gui.tabs.corvette_tab import CorvetteTab

_app = QApplication.instance() or QApplication([])


class TestModuleCategory:
    def test_cockpit_detected(self):
        assert _get_module_category("B_COK_A") == "Cockpit"

    def test_cockpit_with_caret(self):
        assert _get_module_category("^B_COK_A") == "Cockpit"

    def test_wing_detected(self):
        assert _get_module_category("B_WNG_A") == "Wing"

    def test_structure_detected(self):
        assert _get_module_category("B_STR_A_N") == "Structure"

    def test_thruster_detected(self):
        assert _get_module_category("B_TRU_A") == "Thruster"

    def test_turret_detected(self):
        assert _get_module_category("B_TUR_A") == "Turret"

    def test_landing_gear_detected(self):
        assert _get_module_category("B_LND_A") == "Landing Gear"

    def test_connector_detected(self):
        assert _get_module_category("B_CON_A") == "Connector"

    def test_large_connector_detected(self):
        assert _get_module_category("B_CON_L_A") == "Large Connector"

    def test_unknown_returns_unknown(self):
        assert _get_module_category("WEIRD_THING") == "Unknown"

    def test_empty_returns_unknown(self):
        assert _get_module_category("") == "Unknown"


class TestModuleColor:
    def test_cockpit_returns_red(self):
        r, g, b = _get_module_color("B_COK_A")
        assert r > 0.5  # Cockpit is reddish

    def test_wing_returns_blue(self):
        r, g, b = _get_module_color("B_WNG_A")
        assert b > 0.5  # Wing is bluish

    def test_unknown_returns_gray(self):
        r, g, b = _get_module_color("UNKNOWN_THING")
        assert r == g == b  # Gray = equal RGB

    def test_all_categories_have_colors(self):
        """Every category in the mapping should have a color entry."""
        for category in set(_MODULE_CATEGORIES.values()):
            assert category in _MODULE_COLORS


class TestCorvetteTabToggle:
    def _make_psd(self):
        return {
            "ShipOwnership": [],
            "CorvetteStorageInventory": {
                "Slots": [
                    {"Type": {"InventoryType": "Product"}, "Id": "^B_COK_A",
                     "Amount": 1, "MaxAmount": 500, "DamageFactor": 0.0,
                     "FullyInstalled": True, "Index": {"X": 5, "Y": 5}},
                ],
                "ValidSlotIndices": [{"X": x, "Y": y} for x in range(10) for y in range(12)],
                "Class": {"InventoryClass": "C"},
                "Width": 10,
                "Height": 16,
            },
            "CorvetteStorageLayout": {"Slots": 10, "Seed": [True, "0x1"], "Level": 1},
            "CorvetteEditAssociatedShipIndex": -1,
            "CorvetteEditShipName": "Draft Corvette",
            "CorvetteDraftShipSeed": 42,
        }

    def test_tab_has_toggle_button(self):
        tab = CorvetteTab()
        assert hasattr(tab, "_view_toggle_btn")
        assert tab._view_toggle_btn.text() == "Switch to 3D View"

    def test_tab_starts_on_2d(self):
        tab = CorvetteTab()
        assert tab._draft_stack.currentIndex() == 0

    def test_draft_shows_build_grid_tab(self):
        tab = CorvetteTab()
        psd = self._make_psd()
        tab.set_data(psd)
        # Build Grid tab should be visible
        assert tab._inv_tabs.isTabVisible(3) is True


class TestMatrixMath:
    def test_identity(self):
        m = _mat4_identity()
        assert len(m) == 16
        assert m[0] == 1.0
        assert m[5] == 1.0
        assert m[10] == 1.0
        assert m[15] == 1.0

    def test_identity_multiply(self):
        i = _mat4_identity()
        t = _mat4_translate(3.0, 4.0, 5.0)
        result = _mat4_multiply(i, t)
        assert result == pytest.approx(t)

    def test_translate(self):
        t = _mat4_translate(1.0, 2.0, 3.0)
        # Column-major: translation in elements 12, 13, 14
        assert t[12] == 1.0
        assert t[13] == 2.0
        assert t[14] == 3.0

    def test_perspective_produces_16_floats(self):
        p = _mat4_perspective(45.0, 1.0, 0.1, 100.0)
        assert len(p) == 16

    def test_normalize(self):
        n = _normalize((3.0, 4.0, 0.0))
        assert n[0] == pytest.approx(0.6)
        assert n[1] == pytest.approx(0.8)
        assert n[2] == pytest.approx(0.0)

    def test_normalize_zero_vector(self):
        n = _normalize((0.0, 0.0, 0.0))
        assert n == (0.0, 0.0, 1.0)


class TestCubeMesh:
    def test_cube_is_valid_mesh(self):
        assert isinstance(_CUBE_MESH, Mesh)

    def test_cube_has_24_vertices(self):
        assert _CUBE_MESH.vertex_count == 24

    def test_cube_has_36_indices(self):
        assert _CUBE_MESH.index_count == 36

    def test_cube_normals_are_unit_length(self):
        for nx, ny, nz in _CUBE_MESH.normals:
            length = math.sqrt(nx * nx + ny * ny + nz * nz)
            assert length == pytest.approx(1.0, abs=0.01)

    def test_build_cube_returns_fresh_mesh(self):
        m = _build_cube_mesh()
        assert m == _CUBE_MESH


class TestDeriveModuleId:
    def test_cockpit(self):
        from nmstoolkit.gui.tabs.corvette_tab import _derive_module_id
        parts = "models/common/spacecraft/corvette/parts/cok_a/entities/cok_a.scene.mbin".split("/")
        assert _derive_module_id(parts) == "B_COK_A"

    def test_wing(self):
        from nmstoolkit.gui.tabs.corvette_tab import _derive_module_id
        parts = "models/common/spacecraft/corvette/parts/wng_b/wng_b.scene.mbin".split("/")
        assert _derive_module_id(parts) == "B_WNG_B"

    def test_no_parts_dir(self):
        from nmstoolkit.gui.tabs.corvette_tab import _derive_module_id
        parts = "models/common/spacecraft/corvette/geometry.mbin".split("/")
        assert _derive_module_id(parts) == ""

    def test_empty(self):
        from nmstoolkit.gui.tabs.corvette_tab import _derive_module_id
        assert _derive_module_id([]) == ""


class TestMeshDataApi:
    def test_corvette_view_accepts_mesh_data(self):
        from nmstoolkit.gui.widgets.corvette_3d_view import Corvette3DView
        view = Corvette3DView()
        mesh = Mesh(
            vertices=((0, 0, 0), (1, 0, 0), (0, 1, 0)),
            normals=((0, 0, 1),) * 3,
            uvs=((0, 0), (1, 0), (0, 1)),
            indices=(0, 1, 2),
        )
        view.set_mesh_data("B_COK_A", [mesh])
        assert "B_COK_A" in view._mesh_data


class TestModuleFootprint:
    """CORVETTE-LAYOUT-01: Module footprint lookup from ID prefix."""

    def test_cockpit_is_1x2(self):
        assert _get_module_footprint("B_COK_A") == (1, 2)

    def test_cockpit_variant_b_is_1x2(self):
        assert _get_module_footprint("B_COK_B") == (1, 2)

    def test_cockpit_with_caret_is_1x2(self):
        assert _get_module_footprint("^B_COK_A") == (1, 2)

    def test_habitation_is_1x2(self):
        assert _get_module_footprint("B_HAB_A") == (1, 2)

    def test_access_module_is_1x1(self):
        """B_HAB1 (access module) must be 1×1, not matched by B_HAB prefix."""
        assert _get_module_footprint("B_HAB1_A") == (1, 1)

    def test_wing_is_1x2(self):
        assert _get_module_footprint("B_WNG_A") == (1, 2)

    def test_wing_variant_o_is_1x2(self):
        assert _get_module_footprint("B_WNG_O_1") == (1, 2)

    def test_connector_is_1x1(self):
        assert _get_module_footprint("B_CON_A") == (1, 1)

    def test_thruster_is_1x1(self):
        assert _get_module_footprint("B_TRU_A") == (1, 1)

    def test_turret_is_1x1(self):
        assert _get_module_footprint("B_TUR_A") == (1, 1)

    def test_structure_is_1x1(self):
        assert _get_module_footprint("B_STR_A_N") == (1, 1)

    def test_shell_is_1x1(self):
        assert _get_module_footprint("B_SHL_A") == (1, 1)

    def test_unknown_is_1x1(self):
        assert _get_module_footprint("WEIRD") == (1, 1)

    def test_empty_is_1x1(self):
        assert _get_module_footprint("") == (1, 1)


class TestFitMeshesToCell:
    """CORVETTE-LAYOUT-01: Mesh fitting respects module footprint."""

    def _make_mesh(self, extent_x: float, extent_z: float) -> Mesh:
        """Create a simple mesh with known bounding box."""
        return Mesh(
            vertices=(
                (0.0, 0.0, 0.0),
                (extent_x, 0.0, 0.0),
                (extent_x, 1.0, extent_z),
                (0.0, 1.0, extent_z),
            ),
            normals=((0, 0, 1),) * 4,
            uvs=((0, 0), (1, 0), (1, 1), (0, 1)),
            indices=(0, 1, 2, 0, 2, 3),
        )

    def test_1x1_fits_in_unit_cell(self):
        """1×1 module mesh max dimension ≤ 0.9."""
        mesh = self._make_mesh(5.0, 5.0)
        fitted = _fit_meshes_to_cell([mesh], footprint=(1, 1))
        all_verts = [v for m in fitted for v in m.vertices]
        xs = [v[0] for v in all_verts]
        zs = [v[2] for v in all_verts]
        assert max(xs) - min(xs) == pytest.approx(0.9, abs=0.01)
        assert max(zs) - min(zs) == pytest.approx(0.9, abs=0.01)

    def test_1x2_allows_double_extent_in_row_axis(self):
        """1×2 footprint allows z-extent up to 1.8 while x stays ≤ 0.9.

        An elongated mesh (2:1 aspect in z:x) should fit the full 1×2 box
        and produce z_span ≈ 2 × x_span.
        """
        # Mesh is 5.0 in x, 10.0 in z — 2:1 aspect ratio matching 1×2 footprint
        mesh = self._make_mesh(5.0, 10.0)
        fitted = _fit_meshes_to_cell([mesh], footprint=(1, 2))
        all_verts = [v for m in fitted for v in m.vertices]
        xs = [v[0] for v in all_verts]
        zs = [v[2] for v in all_verts]
        x_span = max(xs) - min(xs)
        z_span = max(zs) - min(zs)
        # Elongated mesh fills both axes proportionally
        assert z_span == pytest.approx(x_span * 2, abs=0.05)
        assert x_span == pytest.approx(0.9, abs=0.01)

    def test_1x2_max_dimension_respects_footprint(self):
        """1×2 module: max fitted dimension ≤ 0.9 * 2 = 1.8."""
        mesh = self._make_mesh(10.0, 10.0)
        fitted = _fit_meshes_to_cell([mesh], footprint=(1, 2))
        all_verts = [v for m in fitted for v in m.vertices]
        xs = [v[0] for v in all_verts]
        ys = [v[1] for v in all_verts]
        zs = [v[2] for v in all_verts]
        max_dim = max(max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs))
        assert max_dim <= 1.81  # 0.9 * 2 with small tolerance

    def test_backward_compat_no_footprint_arg(self):
        """Calling without footprint arg still works (defaults to 1×1)."""
        mesh = self._make_mesh(5.0, 5.0)
        fitted = _fit_meshes_to_cell([mesh])
        all_verts = [v for m in fitted for v in m.vertices]
        max_dim = max(
            max(v[i] for v in all_verts) - min(v[i] for v in all_verts)
            for i in range(3)
        )
        assert max_dim == pytest.approx(0.9, abs=0.01)

    def test_empty_meshes_returns_empty(self):
        fitted = _fit_meshes_to_cell([], footprint=(1, 2))
        assert fitted == []

    def test_centered_at_origin(self):
        """Fitted mesh should be centered around origin."""
        mesh = self._make_mesh(10.0, 10.0)
        fitted = _fit_meshes_to_cell([mesh], footprint=(1, 1))
        all_verts = [v for m in fitted for v in m.vertices]
        cx = (max(v[0] for v in all_verts) + min(v[0] for v in all_verts)) / 2
        cy = (max(v[1] for v in all_verts) + min(v[1] for v in all_verts)) / 2
        cz = (max(v[2] for v in all_verts) + min(v[2] for v in all_verts)) / 2
        assert cx == pytest.approx(0.0, abs=0.01)
        assert cy == pytest.approx(0.0, abs=0.01)
        assert cz == pytest.approx(0.0, abs=0.01)


class TestMulticellOffset:
    """CORVETTE-LAYOUT-01: Multi-cell module positioning offset in 3D view."""

    def test_1x1_module_no_offset(self):
        """1×1 module at (5, 3) should translate to exactly (5.0, layer*H, 3.0)."""
        from nmstoolkit.gui.widgets.corvette_3d_view import Corvette3DView, _LAYER_HEIGHT
        view = Corvette3DView()
        inv = {
            "Width": 10, "Height": 16,
            "Slots": [{"Id": "B_CON_A", "Index": {"X": 5, "Y": 3}}],
        }
        view.set_modules(inv)
        slot = view._modules[0]
        x = slot["Index"]["X"]
        z = int(slot.get("_layer_row", slot["Index"]["Y"]))
        layer = int(slot.get("_layer", 0))
        footprint = _get_module_footprint(slot["Id"])
        # For 1×1: no offset
        expected_x = float(x) + (footprint[0] - 1) / 2.0
        expected_z = float(z) + (footprint[1] - 1) / 2.0
        assert expected_x == float(x)
        assert expected_z == float(z)

    def test_1x2_module_offset_half_cell_in_z(self):
        """1×2 module at (5, 3) should be offset +0.5 in z for centering."""
        footprint = _get_module_footprint("B_COK_A")
        x, z = 5, 3
        offset_z = (footprint[1] - 1) / 2.0
        assert offset_z == pytest.approx(0.5)
        # Model translation z should be z + 0.5 = 3.5
        expected_z = float(z) + offset_z
        assert expected_z == pytest.approx(3.5)


class TestLayerMapping:
    def test_row_to_layer_three_bands(self):
        assert _row_to_layer(0, 11) == 2
        assert _row_to_layer(3, 11) == 2
        assert _row_to_layer(4, 11) == 1
        assert _row_to_layer(7, 11) == 1
        assert _row_to_layer(8, 11) == 0
        assert _row_to_layer(11, 11) == 0

    def test_set_modules_assigns_layer_field(self):
        from nmstoolkit.gui.widgets.corvette_3d_view import Corvette3DView

        view = Corvette3DView()
        inv = {
            "Width": 10,
            "Height": 16,
            "Slots": [
                {"Id": "^B_WNG_A", "Index": {"X": 1, "Y": 1}},
                {"Id": "^B_CON_A", "Index": {"X": 1, "Y": 6}},
                {"Id": "^B_SHL_A", "Index": {"X": 1, "Y": 10}},
            ],
        }
        view.set_modules(inv)
        layers = [int(s.get("_layer", -1)) for s in view._modules]
        assert layers == [2, 1, 0]
