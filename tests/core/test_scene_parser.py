"""Tests for scene_parser — SCENE EXML to SceneNode tree."""

import pytest

from nmstoolkit.core.mesh_data import SceneNode, Transform
from nmstoolkit.core.scene_parser import parse_scene


# ---------------------------------------------------------------------------
# Sample EXML fragments
# ---------------------------------------------------------------------------

MINIMAL_SCENE = """\
<?xml version="1.0" encoding="utf-8"?>
<Data template="TkSceneNodeData">
  <Property name="Name" value="ROOT" />
  <Property name="Type" value="MODEL" />
  <Property name="Transform">
    <Property name="TransX" value="0" />
    <Property name="TransY" value="0" />
    <Property name="TransZ" value="0" />
    <Property name="RotX" value="0" />
    <Property name="RotY" value="0" />
    <Property name="RotZ" value="0" />
    <Property name="ScaleX" value="1" />
    <Property name="ScaleY" value="1" />
    <Property name="ScaleZ" value="1" />
  </Property>
  <Property name="Attributes" />
  <Property name="Children" />
</Data>
"""

SCENE_WITH_GEOMETRY = """\
<?xml version="1.0" encoding="utf-8"?>
<Data template="TkSceneNodeData">
  <Property name="Name" value="BIGGS" />
  <Property name="Type" value="MODEL" />
  <Property name="Transform">
    <Property name="TransX" value="0" />
    <Property name="TransY" value="0" />
    <Property name="TransZ" value="0" />
    <Property name="RotX" value="0" />
    <Property name="RotY" value="0" />
    <Property name="RotZ" value="0" />
    <Property name="ScaleX" value="1" />
    <Property name="ScaleY" value="1" />
    <Property name="ScaleZ" value="1" />
  </Property>
  <Property name="Attributes">
    <Property value="TkSceneNodeAttributeData">
      <Property name="Name" value="GEOMETRY" />
      <Property name="Value" value="MODELS/SHIPS/CORVETTE/BIGGS/GEOMETRY.MBIN" />
    </Property>
  </Property>
  <Property name="Children">
    <Property value="TkSceneNodeData">
      <Property name="Name" value="Hull" />
      <Property name="Type" value="MESH" />
      <Property name="Transform">
        <Property name="TransX" value="1.5" />
        <Property name="TransY" value="2.0" />
        <Property name="TransZ" value="-0.5" />
        <Property name="RotX" value="45" />
        <Property name="RotY" value="0" />
        <Property name="RotZ" value="90" />
        <Property name="ScaleX" value="2" />
        <Property name="ScaleY" value="2" />
        <Property name="ScaleZ" value="2" />
      </Property>
      <Property name="Attributes">
        <Property value="TkSceneNodeAttributeData">
          <Property name="Name" value="MATERIAL" />
          <Property name="Value" value="MODELS/SHIPS/CORVETTE/BIGGS/HULL_MAT.MATERIAL.MBIN" />
        </Property>
      </Property>
      <Property name="Children" />
    </Property>
  </Property>
</Data>
"""

DEEP_HIERARCHY = """\
<?xml version="1.0" encoding="utf-8"?>
<Data template="TkSceneNodeData">
  <Property name="Name" value="Level0" />
  <Property name="Type" value="MODEL" />
  <Property name="Transform">
    <Property name="TransX" value="0" /><Property name="TransY" value="0" /><Property name="TransZ" value="0" />
    <Property name="RotX" value="0" /><Property name="RotY" value="0" /><Property name="RotZ" value="0" />
    <Property name="ScaleX" value="1" /><Property name="ScaleY" value="1" /><Property name="ScaleZ" value="1" />
  </Property>
  <Property name="Attributes" />
  <Property name="Children">
    <Property value="TkSceneNodeData">
      <Property name="Name" value="Level1" />
      <Property name="Type" value="LOCATOR" />
      <Property name="Transform">
        <Property name="TransX" value="1" /><Property name="TransY" value="0" /><Property name="TransZ" value="0" />
        <Property name="RotX" value="0" /><Property name="RotY" value="0" /><Property name="RotZ" value="0" />
        <Property name="ScaleX" value="1" /><Property name="ScaleY" value="1" /><Property name="ScaleZ" value="1" />
      </Property>
      <Property name="Attributes" />
      <Property name="Children">
        <Property value="TkSceneNodeData">
          <Property name="Name" value="Level2" />
          <Property name="Type" value="MESH" />
          <Property name="Transform">
            <Property name="TransX" value="0" /><Property name="TransY" value="2" /><Property name="TransZ" value="0" />
            <Property name="RotX" value="0" /><Property name="RotY" value="0" /><Property name="RotZ" value="0" />
            <Property name="ScaleX" value="1" /><Property name="ScaleY" value="1" /><Property name="ScaleZ" value="1" />
          </Property>
          <Property name="Attributes" />
          <Property name="Children">
            <Property value="TkSceneNodeData">
              <Property name="Name" value="Level3" />
              <Property name="Type" value="MESH" />
              <Property name="Transform">
                <Property name="TransX" value="0" /><Property name="TransY" value="0" /><Property name="TransZ" value="3" />
                <Property name="RotX" value="0" /><Property name="RotY" value="0" /><Property name="RotZ" value="0" />
                <Property name="ScaleX" value="1" /><Property name="ScaleY" value="1" /><Property name="ScaleZ" value="1" />
              </Property>
              <Property name="Attributes" />
              <Property name="Children" />
            </Property>
          </Property>
        </Property>
      </Property>
    </Property>
  </Property>
</Data>
"""

MISSING_FIELDS = """\
<?xml version="1.0" encoding="utf-8"?>
<Data template="TkSceneNodeData">
  <Property name="Name" value="Sparse" />
  <Property name="Type" value="MESH" />
  <Property name="Children" />
</Data>
"""

MULTI_ATTRIBUTES = """\
<?xml version="1.0" encoding="utf-8"?>
<Data template="TkSceneNodeData">
  <Property name="Name" value="WithBoth" />
  <Property name="Type" value="MESH" />
  <Property name="Transform">
    <Property name="TransX" value="0" /><Property name="TransY" value="0" /><Property name="TransZ" value="0" />
    <Property name="RotX" value="0" /><Property name="RotY" value="0" /><Property name="RotZ" value="0" />
    <Property name="ScaleX" value="1" /><Property name="ScaleY" value="1" /><Property name="ScaleZ" value="1" />
  </Property>
  <Property name="Attributes">
    <Property value="TkSceneNodeAttributeData">
      <Property name="Name" value="GEOMETRY" />
      <Property name="Value" value="MODELS/TEST/GEOMETRY.MBIN" />
    </Property>
    <Property value="TkSceneNodeAttributeData">
      <Property name="Name" value="MATERIAL" />
      <Property name="Value" value="MODELS/TEST/MATERIAL.MBIN" />
    </Property>
    <Property value="TkSceneNodeAttributeData">
      <Property name="Name" value="MESHINDEX" />
      <Property name="Value" value="0" />
    </Property>
  </Property>
  <Property name="Children" />
</Data>
"""


class TestMinimalScene:
    def test_root_name(self):
        node = parse_scene(MINIMAL_SCENE)
        assert node.name == "ROOT"

    def test_root_type(self):
        node = parse_scene(MINIMAL_SCENE)
        assert node.node_type == "MODEL"

    def test_identity_transform(self):
        node = parse_scene(MINIMAL_SCENE)
        assert node.transform == Transform.identity()

    def test_no_children(self):
        node = parse_scene(MINIMAL_SCENE)
        assert node.children == ()

    def test_no_geometry_ref(self):
        node = parse_scene(MINIMAL_SCENE)
        assert node.geometry_ref == ""

    def test_no_material_ref(self):
        node = parse_scene(MINIMAL_SCENE)
        assert node.material_ref == ""


class TestGeometryAndMaterialAttributes:
    def test_geometry_ref_extracted(self):
        node = parse_scene(SCENE_WITH_GEOMETRY)
        assert node.geometry_ref == "MODELS/SHIPS/CORVETTE/BIGGS/GEOMETRY.MBIN"

    def test_child_material_ref(self):
        node = parse_scene(SCENE_WITH_GEOMETRY)
        hull = node.children[0]
        assert hull.material_ref == "MODELS/SHIPS/CORVETTE/BIGGS/HULL_MAT.MATERIAL.MBIN"

    def test_child_name_and_type(self):
        node = parse_scene(SCENE_WITH_GEOMETRY)
        hull = node.children[0]
        assert hull.name == "Hull"
        assert hull.node_type == "MESH"

    def test_both_attributes(self):
        node = parse_scene(MULTI_ATTRIBUTES)
        assert node.geometry_ref == "MODELS/TEST/GEOMETRY.MBIN"
        assert node.material_ref == "MODELS/TEST/MATERIAL.MBIN"


class TestTransformExtraction:
    def test_position(self):
        node = parse_scene(SCENE_WITH_GEOMETRY)
        hull = node.children[0]
        assert hull.transform.position == (1.5, 2.0, -0.5)

    def test_rotation(self):
        node = parse_scene(SCENE_WITH_GEOMETRY)
        hull = node.children[0]
        assert hull.transform.rotation == (45.0, 0.0, 90.0)

    def test_scale(self):
        node = parse_scene(SCENE_WITH_GEOMETRY)
        hull = node.children[0]
        assert hull.transform.scale == (2.0, 2.0, 2.0)


class TestDeepHierarchy:
    def test_four_levels(self):
        node = parse_scene(DEEP_HIERARCHY)
        assert node.name == "Level0"
        level1 = node.children[0]
        assert level1.name == "Level1"
        assert level1.node_type == "LOCATOR"
        level2 = level1.children[0]
        assert level2.name == "Level2"
        level3 = level2.children[0]
        assert level3.name == "Level3"
        assert level3.children == ()

    def test_accumulated_positions(self):
        node = parse_scene(DEEP_HIERARCHY)
        assert node.children[0].transform.position == (1.0, 0.0, 0.0)
        assert node.children[0].children[0].transform.position == (0.0, 2.0, 0.0)
        assert node.children[0].children[0].children[0].transform.position == (0.0, 0.0, 3.0)


class TestMissingFields:
    def test_missing_transform_defaults_to_identity(self):
        node = parse_scene(MISSING_FIELDS)
        assert node.transform == Transform.identity()

    def test_missing_attributes_defaults_empty(self):
        node = parse_scene(MISSING_FIELDS)
        assert node.geometry_ref == ""
        assert node.material_ref == ""

    def test_name_and_type_still_parsed(self):
        node = parse_scene(MISSING_FIELDS)
        assert node.name == "Sparse"
        assert node.node_type == "MESH"
