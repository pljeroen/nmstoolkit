"""Tests for scene tree walking and transform composition.

Contract: RENDER-FIDELITY-01, R-RF-01, R-RF-02
"""

import math

import pytest

from nmstoolkit.core.mesh_data import Mesh, SceneNode, Transform
from nmstoolkit.core.scene_parser import parse_scene
from nmstoolkit.core.corvette_mesh_pipeline import (
    collect_scene_meshes,
    compose_world_transform,
)


# ---------------------------------------------------------------------------
# Transform composition tests (R-RF-01 / TC-01)
# ---------------------------------------------------------------------------

class TestComposeWorldTransform:
    """TC-01: Transform composition correctness."""

    def test_identity_parent_preserves_child(self):
        parent = Transform.identity()
        child = Transform(
            position=(1.0, 2.0, 3.0),
            rotation=(0.0, 0.0, 0.0),
            scale=(1.0, 1.0, 1.0),
        )
        result = compose_world_transform(parent, child)
        assert result[12] == pytest.approx(1.0, abs=1e-6)
        assert result[13] == pytest.approx(2.0, abs=1e-6)
        assert result[14] == pytest.approx(3.0, abs=1e-6)

    def test_translation_composition(self):
        parent = Transform(
            position=(10.0, 0.0, 0.0),
            rotation=(0.0, 0.0, 0.0),
            scale=(1.0, 1.0, 1.0),
        )
        child = Transform(
            position=(5.0, 0.0, 0.0),
            rotation=(0.0, 0.0, 0.0),
            scale=(1.0, 1.0, 1.0),
        )
        result = compose_world_transform(parent, child)
        # Parent translates 10, child translates 5 more
        assert result[12] == pytest.approx(15.0, abs=1e-6)

    def test_scale_affects_child_translation(self):
        parent = Transform(
            position=(0.0, 0.0, 0.0),
            rotation=(0.0, 0.0, 0.0),
            scale=(2.0, 2.0, 2.0),
        )
        child = Transform(
            position=(1.0, 0.0, 0.0),
            rotation=(0.0, 0.0, 0.0),
            scale=(1.0, 1.0, 1.0),
        )
        result = compose_world_transform(parent, child)
        # Parent scale 2 × child translation 1 = world position 2
        assert result[12] == pytest.approx(2.0, abs=1e-6)

    def test_non_uniform_scale(self):
        parent = Transform(
            position=(0.0, 0.0, 0.0),
            rotation=(0.0, 0.0, 0.0),
            scale=(2.0, 3.0, 4.0),
        )
        child = Transform(
            position=(1.0, 1.0, 1.0),
            rotation=(0.0, 0.0, 0.0),
            scale=(1.0, 1.0, 1.0),
        )
        result = compose_world_transform(parent, child)
        assert result[12] == pytest.approx(2.0, abs=1e-6)  # x: 2.0 * 1.0
        assert result[13] == pytest.approx(3.0, abs=1e-6)  # y: 3.0 * 1.0
        assert result[14] == pytest.approx(4.0, abs=1e-6)  # z: 4.0 * 1.0

    def test_rotation_90_y(self):
        """90-degree Y rotation should swap X and Z axes."""
        parent = Transform(
            position=(0.0, 0.0, 0.0),
            rotation=(0.0, 90.0, 0.0),
            scale=(1.0, 1.0, 1.0),
        )
        child = Transform(
            position=(1.0, 0.0, 0.0),
            rotation=(0.0, 0.0, 0.0),
            scale=(1.0, 1.0, 1.0),
        )
        result = compose_world_transform(parent, child)
        # After 90° Y rotation: (1,0,0) → (0,0,-1)
        assert result[12] == pytest.approx(0.0, abs=1e-5)
        assert result[14] == pytest.approx(-1.0, abs=1e-5)

    def test_compose_returns_16_floats(self):
        result = compose_world_transform(Transform.identity(), Transform.identity())
        assert len(result) == 16


# ---------------------------------------------------------------------------
# Scene tree geometry collection tests (R-RF-02 / TC-02)
# ---------------------------------------------------------------------------

SCENE_MULTI_GEOMETRY = """\
<?xml version="1.0" encoding="utf-8"?>
<Data template="TkSceneNodeData">
  <Property name="Name" value="ROOT" />
  <Property name="Type" value="MODEL" />
  <Property name="Transform">
    <Property name="TransX" value="0" /><Property name="TransY" value="0" /><Property name="TransZ" value="0" />
    <Property name="RotX" value="0" /><Property name="RotY" value="0" /><Property name="RotZ" value="0" />
    <Property name="ScaleX" value="1" /><Property name="ScaleY" value="1" /><Property name="ScaleZ" value="1" />
  </Property>
  <Property name="Attributes">
    <Property value="TkSceneNodeAttributeData">
      <Property name="Name" value="GEOMETRY" />
      <Property name="Value" value="MODELS/ROOT/GEOMETRY.MBIN" />
    </Property>
  </Property>
  <Property name="Children">
    <Property value="TkSceneNodeData">
      <Property name="Name" value="Hull" />
      <Property name="Type" value="MESH" />
      <Property name="Transform">
        <Property name="TransX" value="1" /><Property name="TransY" value="0" /><Property name="TransZ" value="0" />
        <Property name="RotX" value="0" /><Property name="RotY" value="0" /><Property name="RotZ" value="0" />
        <Property name="ScaleX" value="1" /><Property name="ScaleY" value="1" /><Property name="ScaleZ" value="1" />
      </Property>
      <Property name="Attributes">
        <Property value="TkSceneNodeAttributeData">
          <Property name="Name" value="GEOMETRY" />
          <Property name="Value" value="MODELS/HULL/GEOMETRY.MBIN" />
        </Property>
        <Property value="TkSceneNodeAttributeData">
          <Property name="Name" value="MATERIAL" />
          <Property name="Value" value="MODELS/HULL/MATERIAL.MBIN" />
        </Property>
      </Property>
      <Property name="Children" />
    </Property>
    <Property value="TkSceneNodeData">
      <Property name="Name" value="Glass" />
      <Property name="Type" value="MESH" />
      <Property name="Transform">
        <Property name="TransX" value="0" /><Property name="TransY" value="2" /><Property name="TransZ" value="0" />
        <Property name="RotX" value="0" /><Property name="RotY" value="0" /><Property name="RotZ" value="0" />
        <Property name="ScaleX" value="0.5" /><Property name="ScaleY" value="0.5" /><Property name="ScaleZ" value="0.5" />
      </Property>
      <Property name="Attributes">
        <Property value="TkSceneNodeAttributeData">
          <Property name="Name" value="GEOMETRY" />
          <Property name="Value" value="MODELS/GLASS/GEOMETRY.MBIN" />
        </Property>
        <Property value="TkSceneNodeAttributeData">
          <Property name="Name" value="MATERIAL" />
          <Property name="Value" value="MODELS/GLASS/MATERIAL.MBIN" />
        </Property>
      </Property>
      <Property name="Children" />
    </Property>
  </Property>
</Data>
"""

SCENE_NO_GEOMETRY = """\
<?xml version="1.0" encoding="utf-8"?>
<Data template="TkSceneNodeData">
  <Property name="Name" value="EMPTY" />
  <Property name="Type" value="MODEL" />
  <Property name="Transform">
    <Property name="TransX" value="0" /><Property name="TransY" value="0" /><Property name="TransZ" value="0" />
    <Property name="RotX" value="0" /><Property name="RotY" value="0" /><Property name="RotZ" value="0" />
    <Property name="ScaleX" value="1" /><Property name="ScaleY" value="1" /><Property name="ScaleZ" value="1" />
  </Property>
  <Property name="Attributes" />
  <Property name="Children">
    <Property value="TkSceneNodeData">
      <Property name="Name" value="Locator" />
      <Property name="Type" value="LOCATOR" />
      <Property name="Transform">
        <Property name="TransX" value="0" /><Property name="TransY" value="0" /><Property name="TransZ" value="0" />
        <Property name="RotX" value="0" /><Property name="RotY" value="0" /><Property name="RotZ" value="0" />
        <Property name="ScaleX" value="1" /><Property name="ScaleY" value="1" /><Property name="ScaleZ" value="1" />
      </Property>
      <Property name="Attributes" />
      <Property name="Children" />
    </Property>
  </Property>
</Data>
"""


class TestCollectSceneMeshes:
    """TC-02: Scene tree geometry collection completeness."""

    def test_collects_all_geometry_refs(self):
        scene = parse_scene(SCENE_MULTI_GEOMETRY)
        results = collect_scene_meshes(scene)
        geo_refs = [r.geometry_ref for r in results]
        assert "MODELS/ROOT/GEOMETRY.MBIN" in geo_refs
        assert "MODELS/HULL/GEOMETRY.MBIN" in geo_refs
        assert "MODELS/GLASS/GEOMETRY.MBIN" in geo_refs

    def test_collects_material_refs(self):
        scene = parse_scene(SCENE_MULTI_GEOMETRY)
        results = collect_scene_meshes(scene)
        mat_refs = [r.material_ref for r in results]
        assert "MODELS/HULL/MATERIAL.MBIN" in mat_refs
        assert "MODELS/GLASS/MATERIAL.MBIN" in mat_refs

    def test_count_matches_nodes_with_geometry(self):
        scene = parse_scene(SCENE_MULTI_GEOMETRY)
        results = collect_scene_meshes(scene)
        assert len(results) == 3

    def test_empty_scene_returns_empty(self):
        scene = parse_scene(SCENE_NO_GEOMETRY)
        results = collect_scene_meshes(scene)
        assert len(results) == 0

    def test_world_transforms_propagated(self):
        scene = parse_scene(SCENE_MULTI_GEOMETRY)
        results = collect_scene_meshes(scene)
        # Hull child has translation (1, 0, 0) under identity root
        hull = [r for r in results if r.geometry_ref == "MODELS/HULL/GEOMETRY.MBIN"][0]
        # World matrix translation column
        assert hull.world_matrix[12] == pytest.approx(1.0, abs=1e-6)
        assert hull.world_matrix[13] == pytest.approx(0.0, abs=1e-6)

    def test_child_scale_preserved(self):
        scene = parse_scene(SCENE_MULTI_GEOMETRY)
        results = collect_scene_meshes(scene)
        glass = [r for r in results if r.geometry_ref == "MODELS/GLASS/GEOMETRY.MBIN"][0]
        # Glass has scale (0.5, 0.5, 0.5) — should show in matrix diagonal
        assert glass.world_matrix[0] == pytest.approx(0.5, abs=1e-6)
        assert glass.world_matrix[5] == pytest.approx(0.5, abs=1e-6)
        assert glass.world_matrix[10] == pytest.approx(0.5, abs=1e-6)
