"""Tests for cTkGeometryStreamData EXML parser."""

import base64
import struct

from nmstoolkit.core.geometry_stream_exml_parser import parse_geometry_stream_exml


def _pack_int_2_10_10_10_rev(x: int, y: int, z: int, w: int = 0) -> int:
    return (x & 0x3FF) | ((y & 0x3FF) << 10) | ((z & 0x3FF) << 20) | ((w & 0x3) << 30)


def test_parse_geometry_stream_exml_triangle():
    # 3 vertices, 1 triangle
    positions = [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)]
    uvs = [(0.0, 0.0), (1.0, 0.0), (0.0, 1.0)]
    normals_packed = [_pack_int_2_10_10_10_rev(0, 0, 511)] * 3
    tangents_packed = [_pack_int_2_10_10_10_rev(511, 0, 0)] * 3
    indices = (0, 1, 2)

    mesh_data = bytearray()
    for n, t in zip(normals_packed, tangents_packed):
        mesh_data.extend(struct.pack("<I", n))
        mesh_data.extend(struct.pack("<I", t))
    mesh_data.extend(struct.pack("<3H", *indices))

    pos_data = bytearray()
    for (x, y, z), (u, v) in zip(positions, uvs):
        pos_data.extend(struct.pack("<4e", x, y, z, 1.0))
        pos_data.extend(struct.pack("<4e", u, v, 0.0, 0.0))

    geometry_exml = f"""\
<Data template="cTkGeometryData">
  <Property name="Indices16Bit" value="1" />
  <Property name="VertexLayout" value="TkVertexLayout">
    <Property name="Stride" value="8" />
    <Property name="VertexElements">
      <Property value="TkVertexElement">
        <Property name="Type" value="36255" />
        <Property name="SemanticID" value="2" />
        <Property name="Offset" value="0" />
      </Property>
      <Property value="TkVertexElement">
        <Property name="Type" value="36255" />
        <Property name="SemanticID" value="3" />
        <Property name="Offset" value="4" />
      </Property>
    </Property>
  </Property>
  <Property name="PositionVertexLayout" value="TkVertexLayout">
    <Property name="Stride" value="16" />
    <Property name="VertexElements">
      <Property value="TkVertexElement">
        <Property name="Type" value="5131" />
        <Property name="SemanticID" value="0" />
        <Property name="Offset" value="0" />
      </Property>
      <Property value="TkVertexElement">
        <Property name="Type" value="5131" />
        <Property name="SemanticID" value="1" />
        <Property name="Offset" value="8" />
      </Property>
    </Property>
  </Property>
  <Property name="StreamMetaDataArray">
    <Property value="TkMeshMetaData" _index="0">
      <Property name="IdString" value="MESHBOUNDS" />
      <Property name="VertexDataSize" value="{3*8}" />
      <Property name="VertexPositionDataSize" value="{3*16}" />
      <Property name="IndexDataSize" value="{3*2}" />
    </Property>
  </Property>
</Data>
"""

    stream_exml = f"""\
<Data template="cTkGeometryStreamData">
  <Property name="StreamDataArray">
    <Property value="TkMeshData" _index="0">
      <Property name="IdString" value="MESHBOUNDS" />
      <Property name="MeshDataStream" value="{base64.b64encode(bytes(mesh_data)).decode()}" />
      <Property name="MeshPositionDataStream" value="{base64.b64encode(bytes(pos_data)).decode()}" />
    </Property>
  </Property>
</Data>
"""

    meshes = parse_geometry_stream_exml(geometry_exml, stream_exml)
    assert len(meshes) == 1
    mesh = meshes[0]
    assert mesh.vertex_count == 3
    assert mesh.index_count == 3
    assert mesh.indices == (0, 1, 2)


def test_parse_geometry_stream_exml_deduplicates_identical_streams():
    positions = [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)]
    uvs = [(0.0, 0.0), (1.0, 0.0), (0.0, 1.0)]
    normals_packed = [_pack_int_2_10_10_10_rev(0, 0, 511)] * 3
    tangents_packed = [_pack_int_2_10_10_10_rev(511, 0, 0)] * 3
    indices = (0, 1, 2)

    mesh_data = bytearray()
    for n, t in zip(normals_packed, tangents_packed):
        mesh_data.extend(struct.pack("<I", n))
        mesh_data.extend(struct.pack("<I", t))
    mesh_data.extend(struct.pack("<3H", *indices))

    pos_data = bytearray()
    for (x, y, z), (u, v) in zip(positions, uvs):
        pos_data.extend(struct.pack("<4e", x, y, z, 1.0))
        pos_data.extend(struct.pack("<4e", u, v, 0.0, 0.0))

    mesh_b64 = base64.b64encode(bytes(mesh_data)).decode()
    pos_b64 = base64.b64encode(bytes(pos_data)).decode()

    geometry_exml = f"""\
<Data template="cTkGeometryData">
  <Property name="Indices16Bit" value="1" />
  <Property name="VertexLayout" value="TkVertexLayout">
    <Property name="Stride" value="8" />
    <Property name="VertexElements">
      <Property value="TkVertexElement">
        <Property name="Type" value="36255" />
        <Property name="SemanticID" value="2" />
        <Property name="Offset" value="0" />
      </Property>
      <Property value="TkVertexElement">
        <Property name="Type" value="36255" />
        <Property name="SemanticID" value="3" />
        <Property name="Offset" value="4" />
      </Property>
    </Property>
  </Property>
  <Property name="PositionVertexLayout" value="TkVertexLayout">
    <Property name="Stride" value="16" />
    <Property name="VertexElements">
      <Property value="TkVertexElement">
        <Property name="Type" value="5131" />
        <Property name="SemanticID" value="0" />
        <Property name="Offset" value="0" />
      </Property>
      <Property value="TkVertexElement">
        <Property name="Type" value="5131" />
        <Property name="SemanticID" value="1" />
        <Property name="Offset" value="8" />
      </Property>
    </Property>
  </Property>
  <Property name="StreamMetaDataArray">
    <Property value="TkMeshMetaData" _index="0">
      <Property name="IdString" value="MESH_A" />
      <Property name="VertexDataSize" value="{3*8}" />
      <Property name="VertexPositionDataSize" value="{3*16}" />
      <Property name="IndexDataSize" value="{3*2}" />
    </Property>
    <Property value="TkMeshMetaData" _index="1">
      <Property name="IdString" value="MESH_B" />
      <Property name="VertexDataSize" value="{3*8}" />
      <Property name="VertexPositionDataSize" value="{3*16}" />
      <Property name="IndexDataSize" value="{3*2}" />
    </Property>
  </Property>
</Data>
"""

    stream_exml = f"""\
<Data template="cTkGeometryStreamData">
  <Property name="StreamDataArray">
    <Property value="TkMeshData" _index="0">
      <Property name="IdString" value="MESH_A" />
      <Property name="MeshDataStream" value="{mesh_b64}" />
      <Property name="MeshPositionDataStream" value="{pos_b64}" />
    </Property>
    <Property value="TkMeshData" _index="1">
      <Property name="IdString" value="MESH_B" />
      <Property name="MeshDataStream" value="{mesh_b64}" />
      <Property name="MeshPositionDataStream" value="{pos_b64}" />
    </Property>
  </Property>
</Data>
"""

    meshes = parse_geometry_stream_exml(geometry_exml, stream_exml)
    assert len(meshes) == 1
    assert meshes[0].vertex_count == 3
    assert meshes[0].index_count == 3
