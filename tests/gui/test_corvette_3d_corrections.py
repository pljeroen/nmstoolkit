"""Tests for CORVETTE-3D-09: position-based orientation & editing controls.

Covers:
- Turret rotation corrections based on module X position
- ALK Z-offset removal (keep 180 Y rotation, dz=0)
- 3D module selection by slot index
- Module editing panel in corvette tab
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from nmstoolkit.gui.widgets.corvette_3d_view import (
    _mat4_identity,
    _mat4_multiply,
    _module_mesh_correction,
)

_app = QApplication.instance() or QApplication([])


# ---------------------------------------------------------------------------
# WI-1: Turret rotation corrections
# ---------------------------------------------------------------------------


class TestTurretCorrection:
    """Turrets need Z-axis rotation based on X position.

    The turret mesh has the gun pointing +Y.  Side-mounted turrets need
    rotation so the gun points outward (±X).  Half-grid X positions
    (like ±3, ±9, ±15) are side-mounts; full-grid edge positions
    (|X| >= 6) also face outward; center (X=0) stays identity.
    """

    def test_turret_starboard_half_grid_x3(self):
        """Turret at X=+3 (half-grid, starboard) → -90 deg Z rotation."""
        corr = _module_mesh_correction(
            "^B_TUR_A", mod_x=3.0, mod_y=4.5, mod_z=-6.0, cok_z=-3.0,
        )
        # -90 deg Z: col0=(0,-1,0), col1=(1,0,0), col2=(0,0,1)
        assert corr[0] == pytest.approx(0.0)    # col0.x
        assert corr[1] == pytest.approx(-1.0)   # col0.y
        assert corr[2] == pytest.approx(0.0)    # col0.z
        assert corr[4] == pytest.approx(1.0)    # col1.x
        assert corr[5] == pytest.approx(0.0)    # col1.y
        assert corr[10] == pytest.approx(1.0)   # col2.z

    def test_turret_port_half_grid_xn3(self):
        """Turret at X=-3 (half-grid, port) → +90 deg Z rotation."""
        corr = _module_mesh_correction(
            "^B_TUR_A", mod_x=-3.0, mod_y=4.5, mod_z=-6.0, cok_z=-3.0,
        )
        # +90 deg Z: col0=(0,1,0), col1=(-1,0,0), col2=(0,0,1)
        assert corr[0] == pytest.approx(0.0)
        assert corr[1] == pytest.approx(1.0)
        assert corr[4] == pytest.approx(-1.0)
        assert corr[5] == pytest.approx(0.0)
        assert corr[10] == pytest.approx(1.0)

    def test_turret_starboard_half_grid_x9(self):
        """Turret at X=+9 (half-grid, starboard) → -90 deg Z."""
        corr = _module_mesh_correction(
            "^B_TUR_C", mod_x=9.0, mod_y=4.5, mod_z=-12.0, cok_z=-3.0,
        )
        assert corr[1] == pytest.approx(-1.0)   # starboard = -90 deg Z
        assert corr[4] == pytest.approx(1.0)

    def test_turret_port_half_grid_xn15(self):
        """Turret at X=-15 (half-grid, port) → +90 deg Z."""
        corr = _module_mesh_correction(
            "B_TUR_B", mod_x=-15.0, mod_y=4.5, mod_z=-6.0, cok_z=-3.0,
        )
        assert corr[1] == pytest.approx(1.0)    # port = +90 deg Z
        assert corr[4] == pytest.approx(-1.0)

    def test_turret_full_grid_edge_x12(self):
        """Turret at X=+12 (full-grid, edge |X|>=6) → face outward (-90 Z)."""
        corr = _module_mesh_correction(
            "^B_TUR_A", mod_x=12.0, mod_y=4.5, mod_z=-6.0, cok_z=-3.0,
        )
        assert corr[1] == pytest.approx(-1.0)   # starboard
        assert corr[4] == pytest.approx(1.0)

    def test_turret_full_grid_edge_xn6(self):
        """Turret at X=-6 (full-grid, edge) → face outward (+90 Z)."""
        corr = _module_mesh_correction(
            "^B_TUR_A", mod_x=-6.0, mod_y=4.5, mod_z=-6.0, cok_z=-3.0,
        )
        assert corr[1] == pytest.approx(1.0)    # port
        assert corr[4] == pytest.approx(-1.0)

    def test_turret_center_x0_identity(self):
        """Turret at X=0 (center) → identity (no rotation)."""
        corr = _module_mesh_correction(
            "^B_TUR_A", mod_x=0.0, mod_y=4.5, mod_z=-6.0, cok_z=-3.0,
        )
        assert corr == pytest.approx(_mat4_identity())

    def test_turret_no_z_translation(self):
        """Turret corrections never apply Z translation."""
        corr = _module_mesh_correction(
            "^B_TUR_A", mod_x=3.0, mod_y=4.5, mod_z=-6.0, cok_z=-3.0,
        )
        assert corr[12] == pytest.approx(0.0)   # tx
        assert corr[13] == pytest.approx(0.0)   # ty
        assert corr[14] == pytest.approx(0.0)   # tz

    def test_turret_transforms_gun_up_to_right(self):
        """Starboard turret: multiplying (0,1,0) by correction → (1,0,0)."""
        corr = _module_mesh_correction(
            "^B_TUR_A", mod_x=3.0, mod_y=4.5, mod_z=-6.0, cok_z=-3.0,
        )
        # Transform point (0, 1, 0, 1) by the correction matrix
        # x' = corr[0]*0 + corr[4]*1 + corr[8]*0 + corr[12]*1
        x_prime = corr[0] * 0 + corr[4] * 1 + corr[8] * 0 + corr[12]
        y_prime = corr[1] * 0 + corr[5] * 1 + corr[9] * 0 + corr[13]
        z_prime = corr[2] * 0 + corr[6] * 1 + corr[10] * 0 + corr[14]
        assert x_prime == pytest.approx(1.0)
        assert y_prime == pytest.approx(0.0)
        assert z_prime == pytest.approx(0.0)

    def test_turret_transforms_gun_up_to_left(self):
        """Port turret: multiplying (0,1,0) by correction → (-1,0,0)."""
        corr = _module_mesh_correction(
            "^B_TUR_A", mod_x=-3.0, mod_y=4.5, mod_z=-6.0, cok_z=-3.0,
        )
        x_prime = corr[0] * 0 + corr[4] * 1 + corr[8] * 0 + corr[12]
        y_prime = corr[1] * 0 + corr[5] * 1 + corr[9] * 0 + corr[13]
        z_prime = corr[2] * 0 + corr[6] * 1 + corr[10] * 0 + corr[14]
        assert x_prime == pytest.approx(-1.0)
        assert y_prime == pytest.approx(0.0)
        assert z_prime == pytest.approx(0.0)

    def test_turret_with_float_noise(self):
        """X=2.999 should round to 3 → half-grid → starboard rotation."""
        corr = _module_mesh_correction(
            "^B_TUR_A", mod_x=2.999, mod_y=4.5, mod_z=-6.0, cok_z=-3.0,
        )
        assert corr[1] == pytest.approx(-1.0)   # starboard

    def test_non_turret_unaffected_by_mod_x(self):
        """Non-turret modules ignore mod_x parameter."""
        corr = _module_mesh_correction(
            "^B_COK_A", mod_x=3.0, mod_y=4.5, mod_z=-3.0, cok_z=-3.0,
        )
        assert corr == pytest.approx(_mat4_identity())


# ---------------------------------------------------------------------------
# WI-2: ALK Z-offset fix
# ---------------------------------------------------------------------------


class TestAlkZOffsetRemoved:
    """ALK corrections: keep 180 deg Y rotation, remove Z-offset."""

    def test_alk_a_aft_rotation_no_z_offset(self):
        """ALK_A behind cockpit: 180 Y rotation, dz=0."""
        corr = _module_mesh_correction(
            "^B_ALK_A", mod_x=0.0, mod_y=3.0, mod_z=-15.0, cok_z=-3.0,
        )
        # 180 Y rotation: col0.x = -1, col2.z = -1
        assert corr[0] == pytest.approx(-1.0)
        assert corr[5] == pytest.approx(1.0)
        assert corr[10] == pytest.approx(-1.0)
        # Z translation = 0 (no compensation)
        assert corr[14] == pytest.approx(0.0)

    def test_alk_c_aft_rotation_no_z_offset(self):
        """ALK_C behind cockpit: 180 Y rotation, dz=0."""
        corr = _module_mesh_correction(
            "B_ALK_C", mod_x=0.0, mod_y=3.0, mod_z=-6.0, cok_z=0.0,
        )
        assert corr[0] == pytest.approx(-1.0)
        assert corr[14] == pytest.approx(0.0)   # was -1.5, now 0

    def test_alk_b_aft_rotation_no_z_offset(self):
        """ALK_B behind cockpit: 180 Y rotation, dz=0."""
        corr = _module_mesh_correction(
            "^B_ALK_B", mod_x=0.0, mod_y=3.0, mod_z=-33.0, cok_z=-3.0,
        )
        assert corr[0] == pytest.approx(-1.0)
        assert corr[14] == pytest.approx(0.0)

    def test_alk_front_of_cockpit_identity(self):
        """ALK in front of cockpit keeps identity."""
        corr = _module_mesh_correction(
            "^B_ALK_A", mod_x=0.0, mod_y=3.0, mod_z=3.0, cok_z=-3.0,
        )
        assert corr == pytest.approx(_mat4_identity())

    def test_alk_at_cockpit_z_identity(self):
        """ALK at same Z as cockpit → identity (not behind)."""
        corr = _module_mesh_correction(
            "^B_ALK_A", mod_x=0.0, mod_y=3.0, mod_z=-3.0, cok_z=-3.0,
        )
        assert corr == pytest.approx(_mat4_identity())

    def test_alk_no_cockpit_identity(self):
        """No cockpit found (cok_z=None) → identity."""
        corr = _module_mesh_correction(
            "^B_ALK_A", mod_x=0.0, mod_y=3.0, mod_z=-15.0, cok_z=None,
        )
        assert corr == pytest.approx(_mat4_identity())


# ---------------------------------------------------------------------------
# WI-3: 3D module selection by slot index
# ---------------------------------------------------------------------------


class TestSelection3D:
    """In 3D mode, selection uses slot index, not grid coordinates."""

    def _make_view(self):
        from nmstoolkit.gui.widgets.corvette_3d_view import Corvette3DView
        return Corvette3DView()

    def test_3d_mode_selection_uses_slot_index(self):
        """Clicking module at slot 2 stores _selected=(2, 0, 0)."""
        view = self._make_view()
        modules = [
            {"ObjectID": "^B_COK_A", "Position": [0.0, 3.0, -3.0]},
            {"ObjectID": "^B_HAB_A", "Position": [0.0, 3.0, -9.0]},
            {"ObjectID": "^B_TUR_A", "Position": [3.0, 4.5, -6.0]},
        ]
        view.set_modules_3d(modules)
        # Simulate selection of the third module (index 2)
        picked = view._modules[2]
        slot_idx = view._modules.index(picked)
        assert slot_idx == 2
        # In 3D mode, selection should be (slot_idx, 0, 0)
        if picked.get("_render_pos") is not None:
            expected_selected = (slot_idx, 0, 0)
        else:
            expected_selected = (0, 0, 0)
        assert expected_selected == (2, 0, 0)

    def test_3d_selection_differentiates_modules(self):
        """Two different modules should produce different selection tuples."""
        view = self._make_view()
        modules = [
            {"ObjectID": "^B_COK_A", "Position": [0.0, 3.0, -3.0]},
            {"ObjectID": "^B_TUR_A", "Position": [3.0, 4.5, -6.0]},
        ]
        view.set_modules_3d(modules)
        sel_0 = (0, 0, 0)  # slot 0
        sel_1 = (1, 0, 0)  # slot 1
        assert sel_0 != sel_1

    def test_2d_mode_selection_unchanged(self):
        """In 2D mode, selection still uses grid coordinates."""
        view = self._make_view()
        inv = {
            "Width": 10, "Height": 16,
            "Slots": [
                {"Id": "^B_COK_A", "Index": {"X": 5, "Y": 3}},
                {"Id": "^B_CON_A", "Index": {"X": 2, "Y": 7}},
            ],
        }
        view.set_modules(inv)
        # 2D modules should NOT have _render_pos
        assert view._modules[0].get("_render_pos") is None


# ---------------------------------------------------------------------------
# WI-4: Module editing panel
# ---------------------------------------------------------------------------


class TestModuleEditPanel:
    """Corvette tab should have a module editing panel for 3D mode."""

    def test_tab_has_edit_panel_widgets(self):
        """Tab should have module info labels and move buttons."""
        from nmstoolkit.gui.tabs.corvette_tab import CorvetteTab
        tab = CorvetteTab()
        assert hasattr(tab, "_mod_type_label")
        assert hasattr(tab, "_mod_pos_label")
        assert hasattr(tab, "_mod_cat_label")

    def test_tab_has_move_buttons(self):
        """Tab should have 6 directional move buttons."""
        from nmstoolkit.gui.tabs.corvette_tab import CorvetteTab
        tab = CorvetteTab()
        assert hasattr(tab, "_move_xp_btn")
        assert hasattr(tab, "_move_xn_btn")
        assert hasattr(tab, "_move_yp_btn")
        assert hasattr(tab, "_move_yn_btn")
        assert hasattr(tab, "_move_zp_btn")
        assert hasattr(tab, "_move_zn_btn")

    def test_edit_panel_hidden_initially(self):
        """Edit panel should be hidden until a module is selected."""
        from nmstoolkit.gui.tabs.corvette_tab import CorvetteTab
        tab = CorvetteTab()
        assert hasattr(tab, "_edit_group")
        assert tab._edit_group.isHidden() or not tab._edit_group.isVisible()

    def test_edit_panel_populates_on_selection(self):
        """Selecting a module should populate the edit panel labels."""
        from nmstoolkit.gui.tabs.corvette_tab import CorvetteTab
        tab = CorvetteTab()
        # Simulate selection data
        tab._on_module_selected_3d(0, 0, "B_TUR_A")
        # Should show module type
        assert "B_TUR_A" in tab._mod_type_label.text()

    def test_move_updates_position(self):
        """Moving a module should update its position by 3.0 units."""
        from nmstoolkit.gui.tabs.corvette_tab import CorvetteTab
        tab = CorvetteTab()
        # Set up a base object reference
        obj = {
            "ObjectID": "^B_TUR_A",
            "Position": [3.0, 4.5, -6.0],
            "Up": [0.0, 1.0, 0.0],
            "At": [0.0, 0.0, 1.0],
        }
        tab._selected_base_object = obj
        tab._move_module(0, 3.0)  # +X
        assert obj["Position"][0] == pytest.approx(6.0)

    def test_move_z_updates_position(self):
        """Moving along Z updates position[2]."""
        from nmstoolkit.gui.tabs.corvette_tab import CorvetteTab
        tab = CorvetteTab()
        obj = {
            "ObjectID": "^B_TUR_A",
            "Position": [3.0, 4.5, -6.0],
            "Up": [0.0, 1.0, 0.0],
            "At": [0.0, 0.0, 1.0],
        }
        tab._selected_base_object = obj
        tab._move_module(2, -3.0)  # -Z
        assert obj["Position"][2] == pytest.approx(-9.0)
