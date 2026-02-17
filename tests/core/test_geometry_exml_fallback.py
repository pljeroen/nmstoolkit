"""Tests for layered fallback geometry EXML parser."""

from nmstoolkit.core.geometry_exml_fallback import parse_geometry_aabb_fallback


SAMPLE_GEOM_EXML = """\
<?xml version="1.0" encoding="utf-8"?>
<Data template="cTkGeometryData">
  <Property name="MeshAABBMin">
    <Property name="MeshAABBMin" _index="0">
      <Property name="X" value="-2.0" />
      <Property name="Y" value="-1.0" />
      <Property name="Z" value="-3.0" />
      <Property name="W" value="1.0" />
    </Property>
    <Property name="MeshAABBMin" _index="1">
      <Property name="X" value="-0.5" />
      <Property name="Y" value="-0.5" />
      <Property name="Z" value="-0.5" />
      <Property name="W" value="1.0" />
    </Property>
  </Property>
  <Property name="MeshAABBMax">
    <Property name="MeshAABBMax" _index="0">
      <Property name="X" value="2.0" />
      <Property name="Y" value="1.0" />
      <Property name="Z" value="3.0" />
      <Property name="W" value="1.0" />
    </Property>
    <Property name="MeshAABBMax" _index="1">
      <Property name="X" value="0.5" />
      <Property name="Y" value="0.5" />
      <Property name="Z" value="0.5" />
      <Property name="W" value="1.0" />
    </Property>
  </Property>
</Data>
"""


def test_parses_layered_meshes_from_aabbs():
    meshes = parse_geometry_aabb_fallback(SAMPLE_GEOM_EXML)
    assert len(meshes) == 2
    assert meshes[0].vertex_count == 24
    assert meshes[0].index_count == 36
    assert meshes[1].vertex_count == 24
    assert meshes[1].index_count == 36


def test_returns_empty_when_aabb_arrays_missing():
    meshes = parse_geometry_aabb_fallback("<Data template='cTkGeometryData'></Data>")
    assert meshes == []

