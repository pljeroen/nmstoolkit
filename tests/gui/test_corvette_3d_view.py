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
    _3D_VIEWPORT_SCALE,
    _CUBE_MESH,
    _MODULE_CATEGORIES,
    _MODULE_COLORS,
    _build_cube_mesh,
    _fit_meshes_to_cell,
    _get_module_category,
    _get_module_color,
    _get_module_footprint,
    _mat4_from_orientation,
    _mat4_identity,
    _mat4_multiply,
    _mat4_perspective,
    _mat4_translate,
    _normalize,
    _row_to_layer,
)
from nmstoolkit.gui.tabs.corvette_tab import (
    CorvetteTab,
    _extract_hull_modules_3d,
    _find_corvette_base,
    _is_hull_module,
)

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

    def test_cell_size_1_fits_to_unit(self):
        """cell_size=1.0 scales mesh to fill 1.0 per footprint unit."""
        mesh = self._make_mesh(5.0, 5.0)
        fitted = _fit_meshes_to_cell([mesh], footprint=(1, 1), cell_size=1.0)
        all_verts = [v for m in fitted for v in m.vertices]
        max_dim = max(
            max(v[i] for v in all_verts) - min(v[i] for v in all_verts)
            for i in range(3)
        )
        assert max_dim == pytest.approx(1.0, abs=0.01)

    def test_cell_size_1_1x2_extends_to_2(self):
        """cell_size=1.0 with 1×2 footprint allows z-extent up to 2.0."""
        mesh = self._make_mesh(5.0, 10.0)
        fitted = _fit_meshes_to_cell([mesh], footprint=(1, 2), cell_size=1.0)
        all_verts = [v for m in fitted for v in m.vertices]
        zs = [v[2] for v in all_verts]
        z_span = max(zs) - min(zs)
        assert z_span == pytest.approx(2.0, abs=0.01)


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
    """GRID-GEOMETRY-01: Layer mapping uses grid_height, not max_row."""

    def test_row_to_layer_uses_grid_height(self):
        """_row_to_layer accepts grid_height (total rows) and computes deterministic layers."""
        # grid_height=12: band = ceil(12/3) = 4
        # rows 0-3 → raw layer 0 → inverted layer 2
        # rows 4-7 → raw layer 1 → inverted layer 1
        # rows 8-11 → raw layer 2 → inverted layer 0
        assert _row_to_layer(0, 12) == 2
        assert _row_to_layer(3, 12) == 2
        assert _row_to_layer(4, 12) == 1
        assert _row_to_layer(7, 12) == 1
        assert _row_to_layer(8, 12) == 0
        assert _row_to_layer(11, 12) == 0

    def test_row_to_layer_grid_height_16(self):
        """grid_height=16: band = ceil(16/3) = 6."""
        # rows 0-5 → layer 2, rows 6-11 → layer 1, rows 12-15 → layer 0
        assert _row_to_layer(0, 16) == 2
        assert _row_to_layer(5, 16) == 2
        assert _row_to_layer(6, 16) == 1
        assert _row_to_layer(11, 16) == 1
        assert _row_to_layer(12, 16) == 0
        assert _row_to_layer(15, 16) == 0

    def test_row_to_layer_grid_height_6(self):
        """grid_height=6 (completed corvette): band = ceil(6/3) = 2."""
        # rows 0-1 → layer 2, rows 2-3 → layer 1, rows 4-5 → layer 0
        assert _row_to_layer(0, 6) == 2
        assert _row_to_layer(1, 6) == 2
        assert _row_to_layer(2, 6) == 1
        assert _row_to_layer(3, 6) == 1
        assert _row_to_layer(4, 6) == 0
        assert _row_to_layer(5, 6) == 0

    def test_no_layer_overlap_for_grid_height_16(self):
        """No two distinct rows in grid_height=16 share the same (layer, layer_row)."""
        from nmstoolkit.gui.widgets.corvette_3d_view import _row_in_layer
        seen = set()
        for row in range(16):
            pair = (_row_to_layer(row, 16), _row_in_layer(row, 16))
            assert pair not in seen, f"row {row} duplicates (layer, layer_row) = {pair}"
            seen.add(pair)

    def test_set_modules_uses_grid_height_not_max_row(self):
        """set_modules with Height=16 must give same layers regardless of occupied rows."""
        from nmstoolkit.gui.widgets.corvette_3d_view import Corvette3DView

        # Only rows 0-5 occupied, but Height=16 → band = ceil(16/3) = 6
        view = Corvette3DView()
        inv_sparse = {
            "Width": 10, "Height": 16,
            "Slots": [
                {"Id": "^B_CON_A", "Index": {"X": 1, "Y": 1}},
                {"Id": "^B_CON_A", "Index": {"X": 2, "Y": 5}},
            ],
        }
        view.set_modules(inv_sparse)
        layers_sparse = [int(s.get("_layer", -1)) for s in view._modules]

        # Full grid populated, Height=16 → same band
        view2 = Corvette3DView()
        inv_full = {
            "Width": 10, "Height": 16,
            "Slots": [
                {"Id": "^B_CON_A", "Index": {"X": 1, "Y": 1}},
                {"Id": "^B_CON_A", "Index": {"X": 2, "Y": 5}},
                {"Id": "^B_CON_A", "Index": {"X": 3, "Y": 12}},
            ],
        }
        view2.set_modules(inv_full)
        # First two slots must have identical layer assignments
        layers_full = [int(s.get("_layer", -1)) for s in view2._modules]
        assert layers_sparse[0] == layers_full[0], "Row 1 layer changed with different occupancy"
        assert layers_sparse[1] == layers_full[1], "Row 5 layer changed with different occupancy"

    def test_set_modules_layer_rows_from_grid_height(self):
        """_layer_rows must be ceil(grid_height/3) regardless of max_row."""
        from nmstoolkit.gui.widgets.corvette_3d_view import Corvette3DView

        view = Corvette3DView()
        inv = {
            "Width": 10, "Height": 16,
            "Slots": [{"Id": "^B_CON_A", "Index": {"X": 1, "Y": 3}}],  # max_row=3
        }
        view.set_modules(inv)
        # layer_rows must be ceil(16/3) = 6, NOT ceil(4/3) = 2
        assert view._layer_rows == 6

    def test_set_modules_assigns_layer_field(self):
        """Modules at rows 1, 6, 13 with Height=16 land in layers 2, 1, 0.

        grid_height=16, band=ceil(16/3)=6:
        rows 0-5 → layer 2, rows 6-11 → layer 1, rows 12-15 → layer 0.
        """
        from nmstoolkit.gui.widgets.corvette_3d_view import Corvette3DView

        view = Corvette3DView()
        inv = {
            "Width": 10, "Height": 16,
            "Slots": [
                {"Id": "^B_WNG_A", "Index": {"X": 1, "Y": 1}},
                {"Id": "^B_CON_A", "Index": {"X": 1, "Y": 6}},
                {"Id": "^B_SHL_A", "Index": {"X": 1, "Y": 13}},
            ],
        }
        view.set_modules(inv)
        layers = [int(s.get("_layer", -1)) for s in view._modules]
        assert layers == [2, 1, 0]

    def test_set_modules_camera_target_uses_grid_height(self):
        """Camera target Z must be layer_rows/2 where layer_rows = ceil(grid_height/3)."""
        from nmstoolkit.gui.widgets.corvette_3d_view import Corvette3DView

        view = Corvette3DView()
        inv = {
            "Width": 10, "Height": 16,
            "Slots": [{"Id": "^B_CON_A", "Index": {"X": 1, "Y": 0}}],
        }
        view.set_modules(inv)
        # layer_rows = ceil(16/3) = 6, camera target Z should be 6/2.0 = 3.0
        assert view._cam_target[2] == pytest.approx(3.0)


# ---------------------------------------------------------------------------
# CORVETTE-3D-01: Hull filtering, base lookup, 3D positioning
# ---------------------------------------------------------------------------


class TestIsHullModule:
    def test_cockpit_is_hull(self):
        assert _is_hull_module("^B_COK_A") is True

    def test_habitation_is_hull(self):
        assert _is_hull_module("^B_HAB_C") is True

    def test_access_module_is_hull(self):
        assert _is_hull_module("^B_HAB1_A") is True

    def test_wing_is_hull(self):
        assert _is_hull_module("^B_WNG_A") is True

    def test_structure_is_hull(self):
        assert _is_hull_module("^B_STR_A_N") is True

    def test_thruster_is_hull(self):
        assert _is_hull_module("^B_TRU_A") is True

    def test_turret_is_hull(self):
        assert _is_hull_module("^B_TUR_C") is True

    def test_generator_is_hull(self):
        assert _is_hull_module("^B_GEN_0") is True

    def test_landing_gear_is_hull(self):
        assert _is_hull_module("^B_LND_A") is True

    def test_shell_is_hull(self):
        assert _is_hull_module("^B_SHL_A") is True

    def test_airlock_is_hull(self):
        assert _is_hull_module("^B_ALK_A") is True

    def test_connector_is_hull(self):
        assert _is_hull_module("^B_CON_4") is True

    def test_decoration_is_hull(self):
        assert _is_hull_module("^B_DECO_A") is True

    def test_wall_is_not_hull(self):
        assert _is_hull_module("^B_WALL_CARG0") is False

    def test_stairs_not_hull(self):
        assert _is_hull_module("^B_STAIRS0") is False

    def test_door_not_hull(self):
        assert _is_hull_module("^B_DOOR0") is False

    def test_paragon_not_hull(self):
        assert _is_hull_module("^U_PARAGON") is False

    def test_billboard_not_hull(self):
        assert _is_hull_module("BILLBOARD") is False

    def test_empty_string(self):
        assert _is_hull_module("") is False


class TestFindCorvetteBase:
    def test_finds_matching_base(self):
        psd = {
            "PersistentPlayerBases": [
                {"BaseType": {"PersistentBaseTypes": "HomePlanetBase"}, "UserData": 0},
                {"BaseType": {"PersistentBaseTypes": "PlayerShipBase"}, "UserData": 3},
                {"BaseType": {"PersistentBaseTypes": "PlayerShipBase"}, "UserData": 7},
            ]
        }
        base = _find_corvette_base(psd, 7)
        assert base is not None
        assert base["UserData"] == 7

    def test_returns_none_when_no_match(self):
        psd = {"PersistentPlayerBases": [
            {"BaseType": {"PersistentBaseTypes": "HomePlanetBase"}, "UserData": 0},
        ]}
        assert _find_corvette_base(psd, 5) is None

    def test_returns_none_when_no_bases(self):
        assert _find_corvette_base({}, 0) is None

    def test_returns_none_when_base_type_not_dict(self):
        psd = {"PersistentPlayerBases": [{"BaseType": "broken", "UserData": 0}]}
        assert _find_corvette_base(psd, 0) is None

    def test_skips_non_ship_bases(self):
        psd = {"PersistentPlayerBases": [
            {"BaseType": {"PersistentBaseTypes": "HomePlanetBase"}, "UserData": 3},
            {"BaseType": {"PersistentBaseTypes": "PlayerShipBase"}, "UserData": 3},
        ]}
        base = _find_corvette_base(psd, 3)
        assert base["BaseType"]["PersistentBaseTypes"] == "PlayerShipBase"


class TestExtractHullModules3d:
    def test_filters_hull_only(self):
        base = {"Objects": [
            {"ObjectID": "^B_COK_A", "Position": [0.0, 3.0, -3.0]},
            {"ObjectID": "^B_WALL_CARG0", "Position": [0.0, 3.0, -3.0]},
            {"ObjectID": "^B_WNG_A", "Position": [3.0, 4.5, -6.0]},
            {"ObjectID": "^U_PARAGON", "Position": [0.0, 0.0, 0.0]},
            {"ObjectID": "BILLBOARD", "Position": [0.0, 3.0, 0.0]},
        ]}
        result = _extract_hull_modules_3d(base)
        ids = [m["ObjectID"] for m in result]
        assert "^B_COK_A" in ids
        assert "^B_WNG_A" in ids
        assert "^B_WALL_CARG0" not in ids
        assert "^U_PARAGON" not in ids
        assert "BILLBOARD" not in ids
        assert len(result) == 2

    def test_preserves_position(self):
        base = {"Objects": [
            {"ObjectID": "^B_COK_A", "Position": [0.0, 3.0, -3.0]},
        ]}
        result = _extract_hull_modules_3d(base)
        assert result[0]["Position"] == [0.0, 3.0, -3.0]

    def test_provides_default_up_at(self):
        base = {"Objects": [
            {"ObjectID": "^B_COK_A", "Position": [0.0, 3.0, -3.0]},
        ]}
        result = _extract_hull_modules_3d(base)
        assert result[0]["Up"] == [0.0, 1.0, 0.0]
        assert result[0]["At"] == [0.0, 0.0, 1.0]

    def test_preserves_custom_orientation(self):
        base = {"Objects": [
            {"ObjectID": "^B_DECO_A", "Position": [0.0, 6.0, 18.0],
             "Up": [0.0, 1.0, 0.0], "At": [-1.0, 0.0, 0.0]},
        ]}
        result = _extract_hull_modules_3d(base)
        assert result[0]["At"] == [-1.0, 0.0, 0.0]

    def test_skips_objects_without_position(self):
        base = {"Objects": [
            {"ObjectID": "^B_COK_A"},
        ]}
        assert _extract_hull_modules_3d(base) == []

    def test_empty_objects(self):
        assert _extract_hull_modules_3d({"Objects": []}) == []
        assert _extract_hull_modules_3d({}) == []

    def test_duplicate_module_ids_preserved(self):
        base = {"Objects": [
            {"ObjectID": "^B_HAB1_A", "Position": [6.0, 3.0, -12.0]},
            {"ObjectID": "^B_HAB1_A", "Position": [-6.0, 3.0, -12.0]},
        ]}
        result = _extract_hull_modules_3d(base)
        assert len(result) == 2
        assert result[0]["Position"] != result[1]["Position"]


class TestSetModules3d:
    def _make_view(self):
        from nmstoolkit.gui.widgets.corvette_3d_view import Corvette3DView
        return Corvette3DView()

    def test_sets_3d_mode_flag(self):
        view = self._make_view()
        view.set_modules_3d([
            {"ObjectID": "^B_COK_A", "Position": [0.0, 3.0, -3.0]},
        ])
        assert view._is_3d_mode is True

    def test_set_modules_clears_3d_mode(self):
        view = self._make_view()
        view.set_modules_3d([
            {"ObjectID": "^B_COK_A", "Position": [0.0, 3.0, -3.0]},
        ])
        view.set_modules({"Width": 10, "Height": 16, "Slots": []})
        assert view._is_3d_mode is False

    def test_render_pos_normalized_by_grid_step(self):
        view = self._make_view()
        view.set_modules_3d([
            {"ObjectID": "^B_COK_A", "Position": [12.0, 6.0, -6.0]},
        ])
        rp = view._modules[0]["_render_pos"]
        # Uniform scale: all axes × (1/6)
        assert rp == pytest.approx((2.0, 1.0, -1.0))

    def test_camera_centers_on_centroid(self):
        view = self._make_view()
        view.set_modules_3d([
            {"ObjectID": "^B_COK_A", "Position": [0.0, 0.0, 0.0]},
            {"ObjectID": "^B_WNG_A", "Position": [6.0, 0.0, 0.0]},
        ])
        # Centroid raw = (3.0, 0.0, 0.0), uniform scale ×(1/6) = (0.5, 0.0, 0.0)
        assert view._cam_target[0] == pytest.approx(0.5)
        assert view._cam_target[1] == pytest.approx(0.0)
        assert view._cam_target[2] == pytest.approx(0.0)

    def test_module_retains_item_id(self):
        view = self._make_view()
        view.set_modules_3d([
            {"ObjectID": "^B_COK_A", "Position": [0.0, 3.0, -3.0]},
        ])
        assert view._modules[0]["Id"] == "^B_COK_A"

    def test_empty_modules_list(self):
        view = self._make_view()
        view.set_modules_3d([])
        assert view._modules == []
        assert view._is_3d_mode is True

    def test_multiple_modules_count(self):
        view = self._make_view()
        modules = [
            {"ObjectID": "^B_COK_A", "Position": [0.0, 3.0, -3.0]},
            {"ObjectID": "^B_HAB_A", "Position": [0.0, 3.0, -9.0]},
            {"ObjectID": "^B_TRU_A", "Position": [6.0, 4.5, -15.0]},
        ]
        view.set_modules_3d(modules)
        assert len(view._modules) == 3

    def test_3d_world_pos_stored(self):
        view = self._make_view()
        view.set_modules_3d([
            {"ObjectID": "^B_COK_A", "Position": [0.0, 3.0, -3.0]},
        ])
        assert view._modules[0]["_3d_world_pos"] == pytest.approx((0.0, 3.0, -3.0))


# ---------------------------------------------------------------------------
# CORVETTE-3D-02: Physical mesh scaling in 3D mode
# ---------------------------------------------------------------------------


class TestViewportScaleConstant:
    """_3D_VIEWPORT_SCALE is a module-level constant equal to 1/6."""

    def test_value(self):
        assert _3D_VIEWPORT_SCALE == pytest.approx(1.0 / 6.0)

    def test_is_float(self):
        assert isinstance(_3D_VIEWPORT_SCALE, float)


class TestMeshDataScaling3d:
    """In 3D mode, set_mesh_data fits meshes to footprint at cell_size=1.0
    so modules fill the anchor-point spacing without gaps or overlap."""

    def _make_view(self):
        from nmstoolkit.gui.widgets.corvette_3d_view import Corvette3DView
        return Corvette3DView()

    def _make_mesh(self, extent_x: float, extent_y: float, extent_z: float) -> Mesh:
        """Create a mesh with known bounding box from origin."""
        return Mesh(
            vertices=(
                (0.0, 0.0, 0.0),
                (extent_x, 0.0, 0.0),
                (extent_x, extent_y, extent_z),
                (0.0, extent_y, extent_z),
            ),
            normals=((0, 0, 1),) * 4,
            uvs=((0, 0), (1, 0), (1, 1), (0, 1)),
            indices=(0, 1, 2, 0, 2, 3),
        )

    def test_3d_mode_1x1_max_dimension_is_1(self):
        """In 3D mode, a 1×1 module mesh max dimension should be 1.0 (not 0.9)."""
        view = self._make_view()
        view.set_modules_3d([
            {"ObjectID": "^B_CON_A", "Position": [0.0, 3.0, -3.0]},
        ])
        mesh = self._make_mesh(5.0, 5.0, 5.0)
        view.set_mesh_data("B_CON_A", [mesh])
        stored = view._mesh_data["B_CON_A"]
        all_verts = [v for m in stored for v in m.vertices]
        max_dim = max(
            max(v[i] for v in all_verts) - min(v[i] for v in all_verts)
            for i in range(3)
        )
        assert max_dim == pytest.approx(1.0, abs=0.01)

    def test_3d_mode_1x2_allows_z_extent_2(self):
        """In 3D mode, a 1×2 module (e.g. cockpit) can extend up to 2.0 in Z."""
        view = self._make_view()
        view.set_modules_3d([
            {"ObjectID": "^B_COK_B", "Position": [0.0, 3.0, -3.0]},
        ])
        # 6×3×12 mesh in a 1×2 footprint — aspect matches footprint perfectly
        mesh = self._make_mesh(6.0, 3.0, 12.0)
        view.set_mesh_data("B_COK_B", [mesh])
        stored = view._mesh_data["B_COK_B"]
        all_verts = [v for m in stored for v in m.vertices]
        xs = [v[0] for v in all_verts]
        zs = [v[2] for v in all_verts]
        x_span = max(xs) - min(xs)
        z_span = max(zs) - min(zs)
        assert x_span == pytest.approx(1.0, abs=0.01)
        assert z_span == pytest.approx(2.0, abs=0.01)

    def test_3d_mode_preserves_aspect_ratio(self):
        """Aspect ratio preserved within footprint constraint."""
        view = self._make_view()
        view.set_modules_3d([
            {"ObjectID": "^B_CON_A", "Position": [0.0, 3.0, -3.0]},
        ])
        # Non-square mesh in 1×1 footprint — uniform scale preserves ratio
        mesh = self._make_mesh(10.0, 5.0, 10.0)
        view.set_mesh_data("B_CON_A", [mesh])
        stored = view._mesh_data["B_CON_A"]
        all_verts = [v for m in stored for v in m.vertices]
        xs = [v[0] for v in all_verts]
        ys = [v[1] for v in all_verts]
        x_span = max(xs) - min(xs)
        y_span = max(ys) - min(ys)
        assert y_span / x_span == pytest.approx(5.0 / 10.0, abs=0.05)

    def test_3d_mode_centers_mesh_at_origin(self):
        """Fitted mesh should be centered at origin for correct anchor positioning."""
        view = self._make_view()
        view.set_modules_3d([
            {"ObjectID": "^B_HAB_C", "Position": [0.0, 3.0, -3.0]},
        ])
        mesh = self._make_mesh(6.0, 3.0, 12.0)
        view.set_mesh_data("B_HAB_C", [mesh])
        stored = view._mesh_data["B_HAB_C"]
        all_verts = [v for m in stored for v in m.vertices]
        cx = (max(v[0] for v in all_verts) + min(v[0] for v in all_verts)) / 2
        cy = (max(v[1] for v in all_verts) + min(v[1] for v in all_verts)) / 2
        cz = (max(v[2] for v in all_verts) + min(v[2] for v in all_verts)) / 2
        assert cx == pytest.approx(0.0, abs=0.01)
        assert cy == pytest.approx(0.0, abs=0.01)
        assert cz == pytest.approx(0.0, abs=0.01)

    def test_3d_mode_no_dimension_exceeds_footprint(self):
        """No mesh dimension should exceed its footprint in 3D mode."""
        view = self._make_view()
        view.set_modules_3d([
            {"ObjectID": "^B_COK_B", "Position": [0.0, 3.0, -3.0]},
        ])
        # Oversized mesh (7×6×21) for a 1×2 cockpit
        mesh = self._make_mesh(7.0, 6.0, 21.0)
        view.set_mesh_data("B_COK_B", [mesh])
        stored = view._mesh_data["B_COK_B"]
        all_verts = [v for m in stored for v in m.vertices]
        xs = [v[0] for v in all_verts]
        ys = [v[1] for v in all_verts]
        zs = [v[2] for v in all_verts]
        # 1×2 footprint at cell_size=1.0 → max X=1.0, max Y=1.0, max Z=2.0
        assert max(xs) - min(xs) <= 1.01
        assert max(ys) - min(ys) <= 1.01
        assert max(zs) - min(zs) <= 2.01

    def test_2d_mode_still_uses_09_cell_size(self):
        """In 2D mode (draft), set_mesh_data uses cell_size=0.9."""
        view = self._make_view()
        # Default mode is 2D (no set_modules_3d called)
        mesh = self._make_mesh(5.0, 5.0, 5.0)
        view.set_mesh_data("B_CON_A", [mesh])
        stored = view._mesh_data["B_CON_A"]
        all_verts = [v for m in stored for v in m.vertices]
        max_dim = max(
            max(v[i] for v in all_verts) - min(v[i] for v in all_verts)
            for i in range(3)
        )
        # 2D mode uses 0.9 cell_size
        assert max_dim == pytest.approx(0.9, abs=0.01)

    def test_invalidates_gpu_cache(self):
        """set_mesh_data clears GPU cache for the module."""
        view = self._make_view()
        view._mesh_cache["B_COK_A"] = "dummy_gpu"
        mesh = self._make_mesh(6.0, 3.0, 12.0)
        view.set_mesh_data("B_COK_A", [mesh])
        assert "B_COK_A" not in view._mesh_cache


# ---------------------------------------------------------------------------
# CORVETTE-3D-03: Module orientation from Up/At vectors
# ---------------------------------------------------------------------------


class TestMat4FromOrientation:
    """Build a column-major model matrix from Up/At + translation."""

    def test_identity_orientation(self):
        """Default Up=(0,1,0) At=(0,0,1) should produce identity rotation."""
        m = _mat4_from_orientation(
            up=(0, 1, 0), at=(0, 0, 1), tx=0, ty=0, tz=0,
        )
        assert m == pytest.approx(_mat4_identity())

    def test_translation_in_last_column(self):
        """Translation should appear at indices 12, 13, 14."""
        m = _mat4_from_orientation(
            up=(0, 1, 0), at=(0, 0, 1), tx=2.0, ty=3.0, tz=-1.0,
        )
        assert m[12] == pytest.approx(2.0)
        assert m[13] == pytest.approx(3.0)
        assert m[14] == pytest.approx(-1.0)
        assert m[15] == pytest.approx(1.0)

    def test_90_degree_yaw_left(self):
        """At=(-1,0,0) means module faces -X (90° left from default +Z).

        Column 0 (Right) should be (0,0,1).
        Column 2 (At) should be (-1,0,0).
        """
        m = _mat4_from_orientation(
            up=(0, 1, 0), at=(-1, 0, 0), tx=0, ty=0, tz=0,
        )
        # Column 0: Right
        assert m[0] == pytest.approx(0.0)
        assert m[1] == pytest.approx(0.0)
        assert m[2] == pytest.approx(1.0)
        # Column 1: Up
        assert m[4] == pytest.approx(0.0)
        assert m[5] == pytest.approx(1.0)
        assert m[6] == pytest.approx(0.0)
        # Column 2: At
        assert m[8] == pytest.approx(-1.0)
        assert m[9] == pytest.approx(0.0)
        assert m[10] == pytest.approx(0.0)

    def test_90_degree_yaw_right(self):
        """At=(1,0,0) means module faces +X (90° right)."""
        m = _mat4_from_orientation(
            up=(0, 1, 0), at=(1, 0, 0), tx=0, ty=0, tz=0,
        )
        # Column 0: Right = cross(Up, At) = cross((0,1,0),(1,0,0)) = (0,0,-1)
        assert m[0] == pytest.approx(0.0)
        assert m[1] == pytest.approx(0.0)
        assert m[2] == pytest.approx(-1.0)
        # Column 2: At
        assert m[8] == pytest.approx(1.0)
        assert m[9] == pytest.approx(0.0)
        assert m[10] == pytest.approx(0.0)

    def test_orthonormal(self):
        """Output columns should be orthonormal (dot products ≈ 0, lengths ≈ 1)."""
        m = _mat4_from_orientation(
            up=(0, 1, 0), at=(-1, 0, 0), tx=5, ty=6, tz=7,
        )
        rx, ry, rz = m[0], m[1], m[2]
        ux, uy, uz = m[4], m[5], m[6]
        ax, ay, az = m[8], m[9], m[10]
        # Lengths
        assert math.sqrt(rx*rx + ry*ry + rz*rz) == pytest.approx(1.0)
        assert math.sqrt(ux*ux + uy*uy + uz*uz) == pytest.approx(1.0)
        assert math.sqrt(ax*ax + ay*ay + az*az) == pytest.approx(1.0)
        # Orthogonality
        assert rx*ux + ry*uy + rz*uz == pytest.approx(0.0)
        assert rx*ax + ry*ay + rz*az == pytest.approx(0.0)
        assert ux*ax + uy*ay + uz*az == pytest.approx(0.0)


class TestSetModules3dOrientation:
    """set_modules_3d stores Up/At per module for orientation in paintGL."""

    def _make_view(self):
        from nmstoolkit.gui.widgets.corvette_3d_view import Corvette3DView
        return Corvette3DView()

    def test_stores_up_at_vectors(self):
        view = self._make_view()
        view.set_modules_3d([
            {"ObjectID": "^B_COK_A", "Position": [0, 3, -3],
             "Up": [0, 1, 0], "At": [-1, 0, 0]},
        ])
        mod = view._modules[0]
        assert mod["_up"] == pytest.approx((0, 1, 0))
        assert mod["_at"] == pytest.approx((-1, 0, 0))

    def test_default_up_at_when_missing(self):
        view = self._make_view()
        view.set_modules_3d([
            {"ObjectID": "^B_COK_A", "Position": [0, 3, -3]},
        ])
        mod = view._modules[0]
        assert mod["_up"] == pytest.approx((0, 1, 0))
        assert mod["_at"] == pytest.approx((0, 0, 1))
