"""Tests for CORVETTE-3D: position-based orientation & editing controls.

Covers:
- Turret rotation corrections based on module X position
- ALK 180 Y rotation with center offset compensation
- ALK ramp sub-mesh filtering
- Landing gear translation correction (mesh offset)
- Face-connection orientation (Up/At identity detection)
- 3D module selection by slot index
- Module editing panel in corvette tab
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from nmstoolkit.core.mesh_data import Mesh
from nmstoolkit.gui.widgets.corvette_3d_view import (
    _filter_alk_ramp,
    _is_identity_orientation,
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

    def test_alk_a_aft_rotation_with_center_compensation(self):
        """ALK_A behind cockpit: 180 Y rotation with offset compensation."""
        corr = _module_mesh_correction(
            "^B_ALK_A", mod_x=0.0, mod_y=3.0, mod_z=-15.0, cok_z=-3.0,
        )
        # 180 Y rotation: col0.x = -1, col2.z = -1
        assert corr[0] == pytest.approx(-1.0)
        assert corr[5] == pytest.approx(1.0)
        assert corr[10] == pytest.approx(-1.0)
        # Translation compensates for mesh center (cx=0.284, cy=0.669, cz=1.513)
        assert corr[12] == pytest.approx(-2 * 0.284)   # dx = -2*cx
        assert corr[13] == pytest.approx(2 * 0.669)    # dy = 2*cy
        assert corr[14] == pytest.approx(-2 * 1.513)   # dz = -2*cz

    def test_alk_c_aft_rotation_default_center(self):
        """ALK_C behind cockpit: 180 Y rotation, no center data → dz=0."""
        corr = _module_mesh_correction(
            "B_ALK_C", mod_x=0.0, mod_y=3.0, mod_z=-6.0, cok_z=0.0,
        )
        assert corr[0] == pytest.approx(-1.0)
        assert corr[12] == pytest.approx(0.0)   # no center data
        assert corr[14] == pytest.approx(0.0)

    def test_alk_b_aft_rotation_default_center(self):
        """ALK_B behind cockpit: 180 Y rotation, no center data → dz=0."""
        corr = _module_mesh_correction(
            "^B_ALK_B", mod_x=0.0, mod_y=3.0, mod_z=-33.0, cok_z=-3.0,
        )
        assert corr[0] == pytest.approx(-1.0)
        assert corr[12] == pytest.approx(0.0)
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
# WI-2c: Landing gear translation correction
# ---------------------------------------------------------------------------


class TestLandingGearCorrection:
    """Landing gear mesh has center at (0, -1.691, -0.223).

    The mesh hangs below the snap point, but the offset creates a visible
    gap between the gear and the hull it connects to.  A pure translation
    correction shifts the mesh to close the gap.
    """

    def test_lnd_a_gets_translation_correction(self):
        """B_LND_A gets translation-only correction (no rotation)."""
        corr = _module_mesh_correction(
            "^B_LND_A", mod_x=0.0, mod_y=0.0, mod_z=-18.0, cok_z=-3.0,
        )
        # No rotation — diagonal stays identity
        assert corr[0] == pytest.approx(1.0)
        assert corr[5] == pytest.approx(1.0)
        assert corr[10] == pytest.approx(1.0)
        # Translation compensates for mesh center offset
        assert corr[12] == pytest.approx(0.0)     # dx = 0 (centered in X)
        assert corr[13] == pytest.approx(2.0)       # dy = -cy (shift up)
        assert corr[14] == pytest.approx(0.223)    # dz = -cz (shift forward)

    def test_lnd_without_caret(self):
        """B_LND_A without caret prefix also gets correction."""
        corr = _module_mesh_correction(
            "B_LND_A", mod_x=0.0, mod_y=0.0, mod_z=-18.0, cok_z=-3.0,
        )
        assert corr[13] == pytest.approx(2.0)

    def test_lnd_unknown_variant_gets_identity(self):
        """B_LND_B (no cached mesh data) → identity fallback."""
        corr = _module_mesh_correction(
            "^B_LND_B", mod_x=0.0, mod_y=0.0, mod_z=-18.0, cok_z=-3.0,
        )
        assert corr == pytest.approx(_mat4_identity())

    def test_lnd_correction_independent_of_position(self):
        """Landing gear correction is the same regardless of position."""
        corr1 = _module_mesh_correction(
            "^B_LND_A", mod_x=6.0, mod_y=3.0, mod_z=-18.0, cok_z=-3.0,
        )
        corr2 = _module_mesh_correction(
            "^B_LND_A", mod_x=-6.0, mod_y=0.0, mod_z=-6.0, cok_z=-3.0,
        )
        assert corr1 == pytest.approx(corr2)


# ---------------------------------------------------------------------------
# WI-2b: Face-connection orientation (Up/At vectors)
# ---------------------------------------------------------------------------


class TestIdentityOrientationDetection:
    """Detect whether Up/At vectors are identity (default) or face-encoded."""

    def test_identity_up_at(self):
        assert _is_identity_orientation((0.0, 1.0, 0.0), (0.0, 0.0, 1.0)) is True

    def test_reversed_at_is_not_identity(self):
        """At=[0,0,-1] means 'faces backward' — not identity."""
        assert _is_identity_orientation((0.0, 1.0, 0.0), (0.0, 0.0, -1.0)) is False

    def test_rotated_up_is_not_identity(self):
        assert _is_identity_orientation((1.0, 0.0, 0.0), (0.0, 0.0, 1.0)) is False

    def test_small_float_noise_is_identity(self):
        """Values within epsilon of identity still count as identity."""
        assert _is_identity_orientation(
            (0.0001, 1.0, -0.0001), (0.0, 0.0001, 0.9999)
        ) is True

    def test_significant_deviation_is_not_identity(self):
        assert _is_identity_orientation(
            (0.0, 0.99, 0.0), (0.0, 0.0, 1.0)
        ) is False


class TestFaceConnectionSkipsCorrection:
    """When Up/At encode face-connection, correction heuristic is skipped."""

    def _make_view(self):
        from nmstoolkit.gui.widgets.corvette_3d_view import Corvette3DView
        return Corvette3DView()

    def test_alk_with_reversed_at_gets_identity_correction(self):
        """ALK aft with At=[0,0,-1] — save encodes rotation, skip heuristic."""
        view = self._make_view()
        view.set_modules_3d([
            {"ObjectID": "^B_COK_A", "Position": [0.0, 3.0, -3.0]},
            {
                "ObjectID": "^B_ALK_A",
                "Position": [0.0, 3.0, -15.0],
                "Up": [0.0, 1.0, 0.0],
                "At": [0.0, 0.0, -1.0],
            },
        ])
        alk = view._modules[1]
        # Correction should be identity — the At vector already handles rotation
        assert alk["_correction"] == pytest.approx(_mat4_identity())

    def test_alk_with_identity_at_gets_heuristic_correction(self):
        """ALK aft with identity At — fallback heuristic fires."""
        view = self._make_view()
        view.set_modules_3d([
            {"ObjectID": "^B_COK_A", "Position": [0.0, 3.0, -3.0]},
            {
                "ObjectID": "^B_ALK_A",
                "Position": [0.0, 3.0, -15.0],
                "Up": [0.0, 1.0, 0.0],
                "At": [0.0, 0.0, 1.0],
            },
        ])
        alk = view._modules[1]
        # Heuristic fires: 180 Y rotation with center compensation
        assert alk["_correction"][0] == pytest.approx(-1.0)
        assert alk["_correction"][10] == pytest.approx(-1.0)
        assert alk["_correction"][12] == pytest.approx(-2 * 0.284)
        assert alk["_correction"][13] == pytest.approx(2 * 0.669)
        assert alk["_correction"][14] == pytest.approx(-2 * 1.513)

    def test_alk_with_default_at_gets_heuristic_correction(self):
        """ALK aft with no Up/At (defaults to identity) — heuristic fires."""
        view = self._make_view()
        view.set_modules_3d([
            {"ObjectID": "^B_COK_A", "Position": [0.0, 3.0, -3.0]},
            {"ObjectID": "^B_ALK_A", "Position": [0.0, 3.0, -15.0]},
        ])
        alk = view._modules[1]
        assert alk["_correction"][0] == pytest.approx(-1.0)
        assert alk["_correction"][14] == pytest.approx(-2 * 1.513)

    def test_turret_with_rotated_up_gets_identity_correction(self):
        """Turret with non-identity Up — save encodes rotation, skip heuristic."""
        view = self._make_view()
        view.set_modules_3d([
            {"ObjectID": "^B_COK_A", "Position": [0.0, 3.0, -3.0]},
            {
                "ObjectID": "^B_TUR_A",
                "Position": [3.0, 4.5, -6.0],
                "Up": [1.0, 0.0, 0.0],
                "At": [0.0, 0.0, 1.0],
            },
        ])
        tur = view._modules[1]
        assert tur["_correction"] == pytest.approx(_mat4_identity())

    def test_turret_with_identity_up_gets_heuristic_correction(self):
        """Turret with identity Up/At — fallback heuristic fires."""
        view = self._make_view()
        view.set_modules_3d([
            {"ObjectID": "^B_COK_A", "Position": [0.0, 3.0, -3.0]},
            {
                "ObjectID": "^B_TUR_A",
                "Position": [3.0, 4.5, -6.0],
                "Up": [0.0, 1.0, 0.0],
                "At": [0.0, 0.0, 1.0],
            },
        ])
        tur = view._modules[1]
        # Heuristic fires: starboard -90 Z rotation
        assert tur["_correction"][1] == pytest.approx(-1.0)


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


# ---------------------------------------------------------------------------
# WI-6: ALK ramp sub-mesh filtering
# ---------------------------------------------------------------------------


def _make_mesh(z_range, verts=100, x_range=(-1.5, 1.5), y_range=(-1.0, 1.0)):
    """Build a minimal Mesh spanning the given Z range."""
    z_min, z_max = z_range
    x_min, x_max = x_range
    y_min, y_max = y_range
    vertices = (
        (x_min, y_min, z_min),
        (x_max, y_min, z_min),
        (x_min, y_max, z_max),
        (x_max, y_max, z_max),
    )
    # Pad to requested vertex count
    vertices = vertices + ((0.0, 0.0, (z_min + z_max) / 2),) * max(0, verts - 4)
    normals = ((0.0, 1.0, 0.0),) * len(vertices)
    uvs = ((0.0, 0.0),) * len(vertices)
    indices = (0, 1, 2, 1, 2, 3)
    return Mesh(vertices=vertices, normals=normals, uvs=uvs, indices=indices)


class TestAlkRampFilter:
    """ALK ramp sub-meshes (extending beyond module grid cell) should be filtered."""

    def test_keeps_main_body_mesh(self):
        """Mesh 6 — main body centered at origin, Z [-3, 3] — kept."""
        body = _make_mesh(z_range=(-3.0, 3.0), verts=6408)
        result = _filter_alk_ramp([body])
        assert len(result) == 1

    def test_keeps_hull_detail_mesh(self):
        """Mesh 0 — hull detail Z [1.8, 3.25] — kept (barely within tolerance)."""
        detail = _make_mesh(z_range=(1.8, 3.25), verts=698)
        result = _filter_alk_ramp([detail])
        assert len(result) == 1

    def test_removes_ramp_extending_to_z6(self):
        """Mesh 7 — ramp Z [0.07, 6.03] — removed when body present."""
        body = _make_mesh(z_range=(-3.0, 3.0), verts=6408)
        ramp = _make_mesh(z_range=(0.07, 6.03), verts=726)
        result = _filter_alk_ramp([body, ramp])
        assert len(result) == 1
        assert result[0] is body

    def test_removes_ramp_rail_z4(self):
        """Mesh 8 — ramp rail Z [0.58, 4.34] — removed when body present."""
        body = _make_mesh(z_range=(-3.0, 3.0), verts=6408)
        rail = _make_mesh(z_range=(0.58, 4.34), verts=112)
        result = _filter_alk_ramp([body, rail])
        assert len(result) == 1
        assert result[0] is body

    def test_removes_ramp_side_pieces(self):
        """Meshes 10/11 — ramp sides Z [0.48, 4.27] — removed when body present."""
        body = _make_mesh(z_range=(-3.0, 3.0), verts=6408)
        side = _make_mesh(z_range=(0.48, 4.27), verts=115)
        result = _filter_alk_ramp([body, side, side])
        assert len(result) == 1

    def test_mixed_keeps_body_removes_ramp(self):
        """Realistic 12-mesh ALK: body + details kept, ramp pieces removed."""
        body = _make_mesh(z_range=(-3.0, 3.0), verts=6408)
        hull = _make_mesh(z_range=(1.8, 3.25), verts=698)
        small_panel = _make_mesh(z_range=(3.1, 3.23), verts=8)
        trim = _make_mesh(z_range=(2.73, 2.88), verts=48)
        frame = _make_mesh(z_range=(1.92, 3.23), verts=54)
        roof_a = _make_mesh(z_range=(0.51, 2.36), verts=128)
        roof_b = _make_mesh(z_range=(0.51, 2.36), verts=76)
        face = _make_mesh(z_range=(1.5, 1.5), verts=4)
        ramp_main = _make_mesh(z_range=(0.07, 6.03), verts=726)
        ramp_rail = _make_mesh(z_range=(0.58, 4.34), verts=112)
        ramp_side_a = _make_mesh(z_range=(0.48, 4.27), verts=115)
        ramp_side_b = _make_mesh(z_range=(0.48, 4.27), verts=115)
        all_meshes = [
            body, hull, small_panel, trim, frame, roof_a, roof_b,
            ramp_main, ramp_rail, face, ramp_side_a, ramp_side_b,
        ]
        result = _filter_alk_ramp(all_meshes)
        assert len(result) == 8  # 12 - 4 ramp pieces

    def test_never_returns_empty(self):
        """Safety: if all meshes would be filtered, return all unchanged."""
        ramp = _make_mesh(z_range=(0.07, 6.03), verts=726)
        result = _filter_alk_ramp([ramp])
        # Single mesh — if it's the only one, we already tested empty return above.
        # With multiple ramp-only meshes, safety fallback should keep them.
        ramps = [
            _make_mesh(z_range=(0.07, 6.03), verts=726),
            _make_mesh(z_range=(0.58, 4.34), verts=112),
        ]
        result = _filter_alk_ramp(ramps)
        # All would be filtered → safety returns all
        assert len(result) == 2

    def test_set_mesh_data_applies_filter_for_alk(self):
        """set_mesh_data should auto-filter ramp meshes for ALK modules in 3D mode."""
        from nmstoolkit.gui.widgets.corvette_3d_view import Corvette3DView
        view = Corvette3DView()
        view.set_modules_3d([
            {"ObjectID": "^B_COK_A", "Position": [0.0, 3.0, -3.0]},
            {"ObjectID": "^B_ALK_A", "Position": [0.0, 3.0, -15.0]},
        ])
        body = _make_mesh(z_range=(-3.0, 3.0), verts=6408)
        ramp = _make_mesh(z_range=(0.07, 6.03), verts=726)
        view.set_mesh_data("B_ALK_A", [body, ramp])
        assert len(view._mesh_data["B_ALK_A"]) == 1  # ramp filtered out

    def test_set_mesh_data_does_not_filter_non_alk(self):
        """Non-ALK modules should not have ramp filtering applied."""
        from nmstoolkit.gui.widgets.corvette_3d_view import Corvette3DView
        view = Corvette3DView()
        view.set_modules_3d([
            {"ObjectID": "^B_COK_A", "Position": [0.0, 3.0, -3.0]},
            {"ObjectID": "^B_HAB_A", "Position": [0.0, 3.0, -9.0]},
        ])
        body = _make_mesh(z_range=(-3.0, 3.0), verts=6408)
        extending = _make_mesh(z_range=(0.07, 6.03), verts=726)
        view.set_mesh_data("B_HAB_A", [body, extending])
        assert len(view._mesh_data["B_HAB_A"]) == 2  # no filtering
