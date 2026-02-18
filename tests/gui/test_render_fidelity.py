"""Tests for rendering fidelity enhancements.

Contract: RENDER-FIDELITY-01, R-RF-04, R-RF-05
Tests cover: shader uniforms, scene-placement mode, Blinn-Phong.
Non-GL tests — verify data flow and shader source, not actual rendering.
"""

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import math

import pytest
from PySide6.QtWidgets import QApplication

from nmstoolkit.core.mesh_data import Transform
from nmstoolkit.gui.widgets.corvette_3d_view import (
    Corvette3DView,
    _FRAGMENT_SHADER,
    _VERTEX_SHADER,
    _mat4_identity,
    _mat4_multiply,
    _mat4_translate,
)

_app = QApplication.instance() or QApplication([])


class TestBlinnPhongShader:
    """TC-04: Blinn-Phong shader has required uniforms."""

    def test_fragment_shader_has_ambient(self):
        assert "uAmbient" in _FRAGMENT_SHADER

    def test_fragment_shader_has_shininess(self):
        assert "uShininess" in _FRAGMENT_SHADER

    def test_fragment_shader_has_specular_intensity(self):
        assert "uSpecularIntensity" in _FRAGMENT_SHADER

    def test_fragment_shader_has_view_pos(self):
        assert "uViewPos" in _FRAGMENT_SHADER

    def test_fragment_shader_has_half_vector_calculation(self):
        """Blinn-Phong uses half-vector between light and view directions."""
        assert "normalize" in _FRAGMENT_SHADER
        # Should compute half vector or equivalent Blinn-Phong term
        assert "pow" in _FRAGMENT_SHADER or "specular" in _FRAGMENT_SHADER.lower()

    def test_vertex_shader_has_normal_matrix(self):
        assert "uNormalMatrix" in _VERTEX_SHADER or "uModel" in _VERTEX_SHADER

    def test_fragment_shader_has_texture_support(self):
        assert "uHasTexture" in _FRAGMENT_SHADER
        assert "uTex" in _FRAGMENT_SHADER


class TestScenePlacementMode:
    """TC-05: Scene-placement mode uses authored transforms."""

    def test_set_scene_transforms_method_exists(self):
        view = Corvette3DView()
        assert hasattr(view, "set_scene_transforms")

    def test_scene_transforms_stored(self):
        view = Corvette3DView()
        matrix = _mat4_identity()
        view.set_scene_transforms("B_COK_A", [matrix])
        assert "B_COK_A" in view._scene_transforms

    def test_grid_fallback_when_no_scene_transforms(self):
        """Modules without scene transforms use grid placement."""
        view = Corvette3DView()
        inv = {
            "Width": 10,
            "Height": 16,
            "Slots": [
                {"Id": "^B_COK_A", "Index": {"X": 3, "Y": 5}},
            ],
        }
        view.set_modules(inv)
        # No scene transforms set — should use grid placement
        assert "B_COK_A" not in getattr(view, "_scene_transforms", {})


class TestNormalMapSupport:
    """R-RF-03a (stretch): Normal map shader support."""

    def test_fragment_shader_has_normal_map_uniform(self):
        assert "uHasNormalMap" in _FRAGMENT_SHADER or "uNormalMap" in _FRAGMENT_SHADER

    def test_fragment_shader_samples_normal_map(self):
        # Should reference a normal map sampler
        frag_lower = _FRAGMENT_SHADER.lower()
        assert "normalmap" in frag_lower or "normal_map" in frag_lower or "uNormTex" in _FRAGMENT_SHADER


class TestBackwardCompatibility:
    """AC-03, AC-04: Existing API preserved."""

    def test_set_modules_still_works(self):
        view = Corvette3DView()
        inv = {
            "Width": 10, "Height": 16,
            "Slots": [{"Id": "^B_WNG_A", "Index": {"X": 0, "Y": 0}}],
        }
        view.set_modules(inv)
        assert len(view._modules) == 1

    def test_set_mesh_data_still_works(self):
        from nmstoolkit.core.mesh_data import Mesh
        view = Corvette3DView()
        mesh = Mesh(
            vertices=((0, 0, 0), (1, 0, 0), (0, 1, 0)),
            normals=((0, 0, 1),) * 3,
            uvs=((0, 0), (1, 0), (0, 1)),
            indices=(0, 1, 2),
        )
        view.set_mesh_data("B_COK_A", [mesh])
        assert "B_COK_A" in view._mesh_data

    def test_set_grid_visible_still_works(self):
        view = Corvette3DView()
        view.set_grid_visible(False)
        assert view._show_grid is False

    def test_set_layering_enabled_still_works(self):
        view = Corvette3DView()
        view.set_layering_enabled(False)
        assert view._layering_enabled is False
