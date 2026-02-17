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
    _get_module_category,
    _get_module_color,
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
        from nmstoolkit.gui.main_window import _derive_module_id
        parts = "models/common/spacecraft/corvette/parts/cok_a/entities/cok_a.scene.mbin".split("/")
        assert _derive_module_id(parts) == "B_COK_A"

    def test_wing(self):
        from nmstoolkit.gui.main_window import _derive_module_id
        parts = "models/common/spacecraft/corvette/parts/wng_b/wng_b.scene.mbin".split("/")
        assert _derive_module_id(parts) == "B_WNG_B"

    def test_no_parts_dir(self):
        from nmstoolkit.gui.main_window import _derive_module_id
        parts = "models/common/spacecraft/corvette/geometry.mbin".split("/")
        assert _derive_module_id(parts) == ""

    def test_empty(self):
        from nmstoolkit.gui.main_window import _derive_module_id
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
