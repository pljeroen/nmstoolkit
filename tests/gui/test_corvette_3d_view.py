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
    _module_mesh_correction,
    _normalize,
    _row_to_layer,
)
from nmstoolkit.core.corvette_mesh_pipeline import _filter_junk_meshes
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

    def test_render_pos_uses_raw_coordinates(self):
        view = self._make_view()
        view.set_modules_3d([
            {"ObjectID": "^B_COK_A", "Position": [12.0, 6.0, -6.0]},
        ])
        rp = view._modules[0]["_render_pos"]
        # Raw game coordinates — no scaling
        assert rp == pytest.approx((12.0, 6.0, -6.0))

    def test_camera_centers_on_centroid(self):
        view = self._make_view()
        view.set_modules_3d([
            {"ObjectID": "^B_COK_A", "Position": [0.0, 0.0, 0.0]},
            {"ObjectID": "^B_WNG_A", "Position": [6.0, 0.0, 0.0]},
        ])
        # Centroid = (3.0, 0.0, 0.0) — raw coordinates
        assert view._cam_target[0] == pytest.approx(3.0)
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
    """In 3D mode, set_mesh_data stores meshes as-is (no centering, no scaling)."""

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

    def test_3d_mode_preserves_dimensions(self):
        """In 3D mode, mesh dimensions are preserved (no fitting/scaling)."""
        view = self._make_view()
        view.set_modules_3d([
            {"ObjectID": "^B_COK_A", "Position": [0.0, 3.0, -3.0]},
        ])
        mesh = self._make_mesh(6.0, 3.0, 12.0)
        view.set_mesh_data("B_COK_A", [mesh])
        stored = view._mesh_data["B_COK_A"]
        all_verts = [v for m in stored for v in m.vertices]
        xs = [v[0] for v in all_verts]
        ys = [v[1] for v in all_verts]
        zs = [v[2] for v in all_verts]
        assert max(xs) - min(xs) == pytest.approx(6.0, abs=0.01)
        assert max(ys) - min(ys) == pytest.approx(3.0, abs=0.01)
        assert max(zs) - min(zs) == pytest.approx(12.0, abs=0.01)

    def test_3d_mode_preserves_raw_vertices(self):
        """In 3D mode, mesh vertices are stored as-is (no centering)."""
        view = self._make_view()
        view.set_modules_3d([
            {"ObjectID": "^B_HAB_C", "Position": [0.0, 3.0, -3.0]},
        ])
        mesh = self._make_mesh(6.0, 3.0, 12.0)
        view.set_mesh_data("B_HAB_C", [mesh])
        stored = view._mesh_data["B_HAB_C"]
        all_verts = [v for m in stored for v in m.vertices]
        # Vertices should be unchanged — not centered
        assert (0.0, 0.0, 0.0) in all_verts
        assert (6.0, 0.0, 0.0) in all_verts
        assert (6.0, 3.0, 12.0) in all_verts

    def test_2d_mode_still_uses_fit_to_cell(self):
        """In 2D mode (draft), set_mesh_data fits to 0.9 cell size."""
        view = self._make_view()
        mesh = self._make_mesh(5.0, 5.0, 5.0)
        view.set_mesh_data("B_CON_A", [mesh])
        stored = view._mesh_data["B_CON_A"]
        all_verts = [v for m in stored for v in m.vertices]
        max_dim = max(
            max(v[i] for v in all_verts) - min(v[i] for v in all_verts)
            for i in range(3)
        )
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
    """Orientation tests — Up/At vectors from PersistentPlayerBases."""

    def _make_view(self):
        from nmstoolkit.gui.widgets.corvette_3d_view import Corvette3DView
        return Corvette3DView()

    def test_3d_world_pos_matches_render_pos(self):
        """In raw-coordinate mode, render_pos equals world_pos."""
        view = self._make_view()
        view.set_modules_3d([
            {"ObjectID": "^B_COK_A", "Position": [6.0, 3.0, -9.0]},
        ])
        mod = view._modules[0]
        assert mod["_render_pos"] == pytest.approx((6.0, 3.0, -9.0))
        assert mod["_3d_world_pos"] == pytest.approx((6.0, 3.0, -9.0))

    def test_stores_up_at_from_input(self):
        """set_modules_3d stores Up/At vectors when provided."""
        view = self._make_view()
        view.set_modules_3d([
            {
                "ObjectID": "^B_ALK_A",
                "Position": [0.0, 0.0, -12.0],
                "Up": [0.0, 1.0, 0.0],
                "At": [0.0, 0.0, -1.0],
            },
        ])
        mod = view._modules[0]
        assert mod["_up"] == pytest.approx((0.0, 1.0, 0.0))
        assert mod["_at"] == pytest.approx((0.0, 0.0, -1.0))

    def test_defaults_up_at_when_absent(self):
        """set_modules_3d defaults Up=[0,1,0] At=[0,0,1] when not provided."""
        view = self._make_view()
        view.set_modules_3d([
            {"ObjectID": "^B_COK_A", "Position": [0.0, 0.0, 0.0]},
        ])
        mod = view._modules[0]
        assert mod["_up"] == pytest.approx((0.0, 1.0, 0.0))
        assert mod["_at"] == pytest.approx((0.0, 0.0, 1.0))

    def test_model_matrix_uses_orientation(self):
        """Model matrix from Up/At should include rotation, not just translation."""
        # 180° rotation around Y: At=[0,0,-1]
        up = (0.0, 1.0, 0.0)
        at = (0.0, 0.0, -1.0)
        model = _mat4_from_orientation(up, at, 6.0, 0.0, -12.0)
        # Column 2 (At/forward) should be [0, 0, -1, 0]
        assert model[8] == pytest.approx(0.0, abs=1e-6)   # at.x
        assert model[9] == pytest.approx(0.0, abs=1e-6)   # at.y
        assert model[10] == pytest.approx(-1.0, abs=1e-6)  # at.z
        # Translation column should be correct
        assert model[12] == pytest.approx(6.0)
        assert model[13] == pytest.approx(0.0)
        assert model[14] == pytest.approx(-12.0)

    def test_identity_orientation_matches_translate(self):
        """Identity Up/At produces same result as pure translation."""
        up = (0.0, 1.0, 0.0)
        at = (0.0, 0.0, 1.0)
        model_orient = _mat4_from_orientation(up, at, 3.0, 6.0, -9.0)
        model_trans = _mat4_translate(3.0, 6.0, -9.0)
        for i in range(16):
            assert model_orient[i] == pytest.approx(model_trans[i], abs=1e-6)


class TestModuleMeshCorrection:
    """Per-module mesh rotation corrections — position-aware."""

    def test_alk_aft_gets_180_rotation_with_z_offset(self):
        """ALK_A behind cockpit gets 180° Y + Z-offset for mesh asymmetry."""
        # COK at Z=-3, ALK at Z=-15 (behind)
        corr = _module_mesh_correction("^B_ALK_A", mod_z=-15.0, cok_z=-3.0)
        assert corr[0] == pytest.approx(-1.0)   # col0.x flipped
        assert corr[5] == pytest.approx(1.0)    # col1.y unchanged
        assert corr[10] == pytest.approx(-1.0)  # col2.z flipped
        # Z translation compensates for mesh center offset (2 * 1.513)
        assert corr[14] == pytest.approx(3.026, abs=0.01)

    def test_alk_front_gets_identity(self):
        """ALK in front of cockpit keeps identity."""
        # COK at Z=-3, ALK at Z=3 (in front)
        corr = _module_mesh_correction("^B_ALK_A", mod_z=3.0, cok_z=-3.0)
        ident = _mat4_identity()
        for i in range(16):
            assert corr[i] == pytest.approx(ident[i])

    def test_alk_b_aft_gets_180_with_default_offset(self):
        """ALK_B (ambassador) — no cached mesh data, Z offset defaults to 0."""
        corr = _module_mesh_correction("^B_ALK_B", mod_z=-33.0, cok_z=-3.0)
        assert corr[0] == pytest.approx(-1.0)
        assert corr[14] == pytest.approx(0.0)  # unknown variant, no offset

    def test_alk_c_aft_gets_180_with_z_offset(self):
        """ALK_C behind cockpit gets 180° + Z-offset (2 * -0.75 = -1.5)."""
        corr = _module_mesh_correction("B_ALK_C", mod_z=-6.0, cok_z=0.0)
        assert corr[0] == pytest.approx(-1.0)
        assert corr[14] == pytest.approx(-1.5, abs=0.01)

    def test_non_alk_returns_identity(self):
        """Other modules always get identity regardless of position."""
        corr = _module_mesh_correction("^B_COK_A", mod_z=-3.0, cok_z=-3.0)
        ident = _mat4_identity()
        for i in range(16):
            assert corr[i] == pytest.approx(ident[i])

    def test_alk_at_same_z_as_cockpit_gets_identity(self):
        """ALK at same Z as cockpit — not behind, so identity."""
        corr = _module_mesh_correction("^B_ALK_A", mod_z=-3.0, cok_z=-3.0)
        assert corr[0] == pytest.approx(1.0)

    def test_no_cockpit_defaults_identity(self):
        """When cockpit Z is None (no cockpit found), ALK gets identity."""
        corr = _module_mesh_correction("^B_ALK_A", mod_z=-15.0, cok_z=None)
        assert corr[0] == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Mesh filtering — reject LOD hulls, collision proxies, distant duplicates
# ---------------------------------------------------------------------------

def _make_mesh(xs, ys, zs):
    """Build a minimal Mesh from X/Y/Z coordinate ranges (2 verts per range)."""
    verts = []
    for x in xs:
        for y in ys:
            for z in zs:
                verts.append((float(x), float(y), float(z)))
    n = len(verts)
    normals = [(0.0, 1.0, 0.0)] * n
    uvs = [(0.0, 0.0)] * n
    indices = list(range(min(n, 3)))  # at least one triangle
    return Mesh(
        vertices=tuple(verts),
        normals=tuple(normals),
        uvs=tuple(uvs),
        indices=tuple(indices),
    )


def _make_mesh_n(n_verts, x_range, y_range, z_range):
    """Build a Mesh with exactly n_verts vertices spread across given ranges."""
    import random
    rng = random.Random(42)
    verts = []
    for _ in range(n_verts):
        verts.append((
            rng.uniform(x_range[0], x_range[1]),
            rng.uniform(y_range[0], y_range[1]),
            rng.uniform(z_range[0], z_range[1]),
        ))
    normals = [(0.0, 1.0, 0.0)] * n_verts
    uvs = [(0.0, 0.0)] * n_verts
    indices = list(range(min(n_verts, 3)))
    return Mesh(
        vertices=tuple(verts),
        normals=tuple(normals),
        uvs=tuple(uvs),
        indices=tuple(indices),
    )


class TestFilterJunkMeshes:
    """Tests for _filter_junk_meshes — R1-R4."""

    # --- R1: Reject distant duplicates (center > 8 from origin) ---

    def test_keeps_mesh_centered_at_origin(self):
        """Normal mesh near origin is kept."""
        m = _make_mesh([-3, 3], [0, 3], [-3, 3])  # center ~(0, 1.5, 0)
        result = _filter_junk_meshes([m])
        assert len(result) == 1

    def test_rejects_mesh_with_distant_z_center(self):
        """B_GEN_0 LOD copy at Z=13.5 rejected."""
        good = _make_mesh_n(1000, (-3, 3), (0, 3), (-3, 3))
        bad = _make_mesh_n(1000, (-3, 3), (0, 3), (10, 17))  # center Z=13.5
        result = _filter_junk_meshes([good, bad])
        assert len(result) == 1

    def test_rejects_mesh_with_distant_negative_z(self):
        """B_GEN_0 LOD copy at Z=-25.5 rejected."""
        good = _make_mesh_n(1000, (-3, 3), (0, 3), (-3, 3))
        bad = _make_mesh_n(1000, (-3, 3), (0, 3), (-28, -23))  # center Z=-25.5
        result = _filter_junk_meshes([good, bad])
        assert len(result) == 1

    def test_rejects_mesh_with_distant_x_center(self):
        """Mesh at X=15 rejected."""
        good = _make_mesh_n(1000, (-3, 3), (0, 3), (-3, 3))
        bad = _make_mesh_n(1000, (12, 18), (0, 3), (-3, 3))  # center X=15
        result = _filter_junk_meshes([good, bad])
        assert len(result) == 1

    # --- R2: Reject collision proxies (low verts, large volume) ---

    def test_rejects_low_vert_large_volume(self):
        """B_ALK_A collision proxy: 28 verts, volume 828."""
        good = _make_mesh_n(6408, (-3, 3), (0, 3), (-3, 3))
        # 8 verts in a big box — simulates collision proxy
        bad = _make_mesh([-4.7, 4.7], [-7.4, 3.0], [-3, 10])
        assert len(bad.vertices) < 50
        result = _filter_junk_meshes([good, bad])
        assert len(result) == 1

    def test_keeps_small_low_vert_mesh(self):
        """Tiny shadow plane (0.7x0.1x0.7) with few verts is kept."""
        good = _make_mesh_n(1000, (-3, 3), (0, 3), (-3, 3))
        small = _make_mesh([-0.35, 0.35], [0, 0.1], [-0.35, 0.35])
        result = _filter_junk_meshes([good, small])
        assert len(result) == 2

    # --- R3: Reject oversized LOD hulls (dim > 7 + low verts) ---

    def test_rejects_oversized_low_detail_mesh(self):
        """B_TRU_A LOD hull: 188 verts at 8.2x6.3x5.8."""
        good = _make_mesh_n(1000, (-0.7, 0.7), (-0.7, 0.7), (-1, 1))
        bad = _make_mesh_n(188, (-4.1, 4.1), (-3.1, 3.2), (-2.9, 2.9))
        result = _filter_junk_meshes([good, bad])
        assert len(result) == 1

    def test_keeps_large_mesh_with_many_verts(self):
        """HAB_A at 6x3x12 with 5000+ verts is kept (legitimate 1x2 module)."""
        big = _make_mesh_n(5000, (-3, 3), (0, 3), (-6, 6))  # 12 units Z
        result = _filter_junk_meshes([big])
        assert len(result) == 1

    def test_keeps_moderately_large_detailed_mesh(self):
        """Cockpit at 5.5x3.7x6.7 with 4486 verts — legitimate detail."""
        m = _make_mesh_n(4486, (-2.7, 2.7), (-0.6, 3.1), (-0.2, 6.5))
        result = _filter_junk_meshes([m])
        assert len(result) == 1

    # --- R4: Fallback — never return empty ---

    def test_fallback_keeps_all_if_all_filtered(self):
        """If every mesh would be rejected, keep them all."""
        # All meshes have centers far from origin
        m1 = _make_mesh([-3, 3], [0, 3], [20, 26])  # Z=23
        m2 = _make_mesh([-3, 3], [0, 3], [-30, -24])  # Z=-27
        result = _filter_junk_meshes([m1, m2])
        assert len(result) == 2  # kept because fallback

    def test_single_mesh_always_kept(self):
        """Single mesh is never filtered even if it looks bad."""
        m = _make_mesh([-3, 3], [0, 3], [20, 26])
        result = _filter_junk_meshes([m])
        assert len(result) == 1

    # --- R3b: Reject tall LOD hulls (Y span > 5) ---

    def test_rejects_tall_lod_hull(self):
        """B_TRU_A LOD hull: 1428 verts, Y span 6.03 — rejected."""
        good = _make_mesh_n(6000, (-3, 3), (0, 3), (-3, 3))
        bad = _make_mesh_n(1428, (-2.9, 2.9), (-3.0, 3.03), (-2.6, 2.6))  # Yspan=6.03
        result = _filter_junk_meshes([good, bad])
        assert len(result) == 1

    def test_keeps_normal_height_mesh(self):
        """Normal hull at Y=[0,3] (span=3) is kept."""
        m = _make_mesh_n(1500, (-3, 3), (0, 3), (-3, 3))  # Yspan=3
        result = _filter_junk_meshes([m])
        assert len(result) == 1

    def test_keeps_two_storey_mesh(self):
        """HAB module spanning 2 rows at Y=[0,4.5] (span=4.5) is kept."""
        m = _make_mesh_n(5000, (-3, 3), (0, 4.5), (-6, 6))  # Yspan=4.5
        result = _filter_junk_meshes([m])
        assert len(result) == 1

    # --- R3c: Reject sub-floor corridors (Y min < -2 AND Z max > 4) ---

    def test_rejects_ramp_corridor(self):
        """B_ALK_A ramp: 1566 verts, extends Y=-3.20 and Z=5.66 — rejected."""
        good = _make_mesh_n(6408, (-3, 3), (-1.5, 1.5), (-3, 3))
        bad = _make_mesh_n(1566, (-1.5, 1.5), (-3.20, 0.21), (0.38, 5.66))
        result = _filter_junk_meshes([good, bad])
        assert len(result) == 1

    def test_rejects_ramp_underside(self):
        """B_ALK_A ramp underside: 336 verts, Y=-3.06 and Z=5.56 — rejected."""
        good = _make_mesh_n(6408, (-3, 3), (-1.5, 1.5), (-3, 3))
        bad = _make_mesh_n(336, (-1.5, 1.5), (-3.06, -0.45), (1.21, 5.56))
        result = _filter_junk_meshes([good, bad])
        assert len(result) == 1

    def test_keeps_landing_gear(self):
        """B_LND_A mesh: Y=[-1.50, 0.83], Z=[-0.78, 2.33] — safe from R3c."""
        gear = _make_mesh_n(800, (-1.5, 1.5), (-1.50, 0.83), (-0.78, 2.33))
        result = _filter_junk_meshes([gear])
        assert len(result) == 1

    def test_keeps_deep_but_short_mesh(self):
        """Mesh with Y min < -2 but Z max < 4 — not a corridor."""
        m = _make_mesh_n(800, (-2, 2), (-2.5, 1.0), (-1, 2))  # Z max=2
        result = _filter_junk_meshes([m])
        assert len(result) == 1

    def test_keeps_forward_but_not_deep_mesh(self):
        """Mesh with Z max > 4 but Y min > -2 — not a corridor."""
        m = _make_mesh_n(800, (-2, 2), (0, 3), (-1, 5))  # Y min=0
        result = _filter_junk_meshes([m])
        assert len(result) == 1

    # --- Combined: realistic B_GEN_0 scenario ---

    def test_gen_0_realistic(self):
        """B_GEN_0 with 6 meshes: keep main body + 2 shadow planes, reject 3 distant."""
        main = _make_mesh_n(4486, (-3, 3), (0, 3.7), (-3, 3))       # center ~origin
        lod1 = _make_mesh_n(4400, (-3, 3), (0, 3.8), (10, 17))      # center Z=13.5
        lod2 = _make_mesh_n(4400, (-3, 3), (0, 3.7), (-28, -23))    # center Z=-25.5
        lod3 = _make_mesh_n(4400, (-3, 3), (0, 3.7), (-15, -9))     # center Z=-12
        shadow1 = _make_mesh([-0.35, 0.35], [0, 0.05], [-0.35, 0.35])
        shadow2 = _make_mesh([-0.35, 0.35], [0, 0.05], [-0.35, 0.35])
        result = _filter_junk_meshes([main, lod1, lod2, lod3, shadow1, shadow2])
        assert len(result) == 3  # main + 2 shadows
