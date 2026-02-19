"""Tests for raw binary stream geometry parser (STREAM-PARSER-01 contract).

Tests cover:
- Single triangle with known vertex positions, normals, UVs
- Multi-mesh geometry with separate StreamMetaData entries
- 16-bit and 32-bit index buffer support
- Half-float position decoding (type 5131)
- INT_2_10_10_10_REV normal decoding (type 36255)
- Collision mesh filtering
- Invalid/corrupt input returns empty list
- Domain purity (stdlib only imports)
"""

import ast
import math
import struct

import pytest

from nmstoolkit.core.geometry_parser import unpack_int_2_10_10_10_rev


def _pack_int_2_10_10_10_rev(x: int, y: int, z: int, w: int = 0) -> int:
    return (x & 0x3FF) | ((y & 0x3FF) << 10) | ((z & 0x3FF) << 20) | ((w & 0x3) << 30)


def _build_raw_stream(positions, uvs, normals_packed, tangents_packed, indices, is_16bit=True):
    """Build raw binary stream sections for a single mesh.

    Returns (pos_bytes, vert_bytes, idx_bytes) — the three section chunks.

    Position stream: 16 bytes/vertex (4 half-floats pos + 4 half-floats UV)
    Vertex stream: 8 bytes/vertex (packed normal u32 + packed tangent u32)
    Index stream: 2 bytes/index (u16) or 4 bytes/index (u32)
    """
    pos_data = bytearray()
    for (x, y, z), (u, v) in zip(positions, uvs):
        pos_data.extend(struct.pack("<4e", x, y, z, 1.0))
        pos_data.extend(struct.pack("<4e", u, v, 0.0, 0.0))

    vert_data = bytearray()
    for n, t in zip(normals_packed, tangents_packed):
        vert_data.extend(struct.pack("<I", n))
        vert_data.extend(struct.pack("<I", t))

    if is_16bit:
        idx_data = struct.pack(f"<{len(indices)}H", *indices)
    else:
        idx_data = struct.pack(f"<{len(indices)}I", *indices)

    return bytes(pos_data), bytes(vert_data), bytes(idx_data)


def _pack_raw_file(*mesh_sections):
    """Pack mesh sections into NMS raw data layout: per-mesh [vert][idx][pos] blocks.

    Each element is a (pos_bytes, vert_bytes, idx_bytes) tuple from _build_raw_stream.
    Returns (raw_bytes, list_of_meta_dicts) with correct NMS offset semantics:
      - VertexDataOffset: absolute file position of vertex data
      - IndexDataOffset: relative to VertexDataOffset (= VertexDataSize)
      - VertexPositionDataOffset: absolute file position of position data
    """
    raw = bytearray()
    metas = []
    for pos_bytes, vert_bytes, idx_bytes in mesh_sections:
        vd_off = len(raw)
        raw.extend(vert_bytes)
        raw.extend(idx_bytes)
        vpd_off = len(raw)
        raw.extend(pos_bytes)
        metas.append({
            "vert_data_offset": vd_off,
            "vert_data_size": len(vert_bytes),
            "idx_data_offset": len(vert_bytes),  # relative to vd_off
            "idx_data_size": len(idx_bytes),
            "pos_data_offset": vpd_off,
            "pos_data_size": len(pos_bytes),
        })
    return bytes(raw), metas


def _build_geometry_exml(
    meshes,
    is_16bit=True,
    vert_stride=8,
    pos_stride=16,
):
    """Build geometry EXML metadata string for the raw stream parser.

    meshes: list of dicts with keys:
        id_string, pos_data_size, vert_data_size, idx_data_size,
        pos_data_offset, vert_data_offset, idx_data_offset
    """
    meta_entries = []
    for i, m in enumerate(meshes):
        meta_entries.append(f"""
    <Property value="TkMeshMetaData" _index="{i}">
      <Property name="IdString" value="{m['id_string']}" />
      <Property name="VertexDataSize" value="{m['vert_data_size']}" />
      <Property name="VertexPositionDataSize" value="{m['pos_data_size']}" />
      <Property name="IndexDataSize" value="{m['idx_data_size']}" />
      <Property name="VertexDataOffset" value="{m.get('vert_data_offset', 0)}" />
      <Property name="VertexPositionDataOffset" value="{m.get('pos_data_offset', 0)}" />
      <Property name="IndexDataOffset" value="{m.get('idx_data_offset', 0)}" />
    </Property>""")

    return f"""\
<Data template="cTkGeometryData">
  <Property name="Indices16Bit" value="{1 if is_16bit else 0}" />
  <Property name="VertexLayout" value="TkVertexLayout">
    <Property name="Stride" value="{vert_stride}" />
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
    <Property name="Stride" value="{pos_stride}" />
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
  <Property name="StreamMetaDataArray">{"".join(meta_entries)}
  </Property>
</Data>
"""


class TestSingleTriangle:
    """R-SP-01, C-FUNC-01: Parse a single triangle from raw binary stream."""

    def _make_triangle(self):
        positions = [(1.0, 2.0, 3.0), (4.0, 5.0, 6.0), (7.0, 8.0, 9.0)]
        uvs = [(0.0, 0.0), (1.0, 0.0), (0.0, 1.0)]
        normals_packed = [_pack_int_2_10_10_10_rev(0, 0, 511)] * 3
        tangents_packed = [_pack_int_2_10_10_10_rev(511, 0, 0)] * 3
        indices = (0, 1, 2)

        sections = _build_raw_stream(
            positions, uvs, normals_packed, tangents_packed, indices,
        )
        raw, metas = _pack_raw_file(sections)
        m = metas[0]
        exml = _build_geometry_exml([{
            "id_string": "MESH_A",
            "pos_data_size": m["pos_data_size"],
            "vert_data_size": m["vert_data_size"],
            "idx_data_size": m["idx_data_size"],
            "pos_data_offset": m["pos_data_offset"],
            "vert_data_offset": m["vert_data_offset"],
            "idx_data_offset": m["idx_data_offset"],
        }])
        return raw, exml, positions, uvs

    def test_returns_one_mesh(self):
        from nmstoolkit.core.geometry_raw_stream_parser import parse_geometry_raw_stream
        raw, exml, _, _ = self._make_triangle()
        meshes = parse_geometry_raw_stream(exml, raw)
        assert len(meshes) == 1

    def test_vertex_count(self):
        from nmstoolkit.core.geometry_raw_stream_parser import parse_geometry_raw_stream
        raw, exml, _, _ = self._make_triangle()
        meshes = parse_geometry_raw_stream(exml, raw)
        assert meshes[0].vertex_count == 3

    def test_index_count(self):
        from nmstoolkit.core.geometry_raw_stream_parser import parse_geometry_raw_stream
        raw, exml, _, _ = self._make_triangle()
        meshes = parse_geometry_raw_stream(exml, raw)
        assert meshes[0].index_count == 3

    def test_indices_correct(self):
        from nmstoolkit.core.geometry_raw_stream_parser import parse_geometry_raw_stream
        raw, exml, _, _ = self._make_triangle()
        meshes = parse_geometry_raw_stream(exml, raw)
        assert meshes[0].indices == (0, 1, 2)

    def test_positions_decoded(self):
        """C-FUNC-02: Half-float positions decode correctly."""
        from nmstoolkit.core.geometry_raw_stream_parser import parse_geometry_raw_stream
        raw, exml, positions, _ = self._make_triangle()
        meshes = parse_geometry_raw_stream(exml, raw)
        for i, (ex, ey, ez) in enumerate(positions):
            ax, ay, az = meshes[0].vertices[i]
            assert ax == pytest.approx(ex, abs=0.01)
            assert ay == pytest.approx(ey, abs=0.01)
            assert az == pytest.approx(ez, abs=0.01)

    def test_uvs_decoded(self):
        from nmstoolkit.core.geometry_raw_stream_parser import parse_geometry_raw_stream
        raw, exml, _, uvs = self._make_triangle()
        meshes = parse_geometry_raw_stream(exml, raw)
        for i, (eu, ev) in enumerate(uvs):
            au, av = meshes[0].uvs[i]
            assert au == pytest.approx(eu, abs=0.01)
            assert av == pytest.approx(ev, abs=0.01)

    def test_normals_unit_length(self):
        """C-FUNC-03: INT_2_10_10_10_REV normals are unit-length."""
        from nmstoolkit.core.geometry_raw_stream_parser import parse_geometry_raw_stream
        raw, exml, _, _ = self._make_triangle()
        meshes = parse_geometry_raw_stream(exml, raw)
        for nx, ny, nz in meshes[0].normals:
            length = math.sqrt(nx * nx + ny * ny + nz * nz)
            assert length == pytest.approx(1.0, abs=0.01)

    def test_normals_point_z(self):
        """Normal packed as (0,0,511) should decode to ~(0,0,1)."""
        from nmstoolkit.core.geometry_raw_stream_parser import parse_geometry_raw_stream
        raw, exml, _, _ = self._make_triangle()
        meshes = parse_geometry_raw_stream(exml, raw)
        nx, ny, nz = meshes[0].normals[0]
        assert abs(nz) > 0.9


class TestMultiMesh:
    """C-FUNC-05, C-FUNC-06: Multi-mesh support with per-mesh offsets."""

    def _make_two_triangles(self):
        positions_a = [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)]
        positions_b = [(10.0, 20.0, 30.0), (11.0, 20.0, 30.0), (10.0, 21.0, 30.0)]
        uvs = [(0.0, 0.0), (1.0, 0.0), (0.0, 1.0)]
        n_packed = [_pack_int_2_10_10_10_rev(0, 0, 511)] * 3
        t_packed = [_pack_int_2_10_10_10_rev(511, 0, 0)] * 3
        indices = (0, 1, 2)

        sec_a = _build_raw_stream(positions_a, uvs, n_packed, t_packed, indices)
        sec_b = _build_raw_stream(positions_b, uvs, n_packed, t_packed, indices)
        raw, metas = _pack_raw_file(sec_a, sec_b)

        exml = _build_geometry_exml([
            {
                "id_string": "MESH_A",
                "pos_data_size": metas[0]["pos_data_size"],
                "vert_data_size": metas[0]["vert_data_size"],
                "idx_data_size": metas[0]["idx_data_size"],
                "pos_data_offset": metas[0]["pos_data_offset"],
                "vert_data_offset": metas[0]["vert_data_offset"],
                "idx_data_offset": metas[0]["idx_data_offset"],
            },
            {
                "id_string": "MESH_B",
                "pos_data_size": metas[1]["pos_data_size"],
                "vert_data_size": metas[1]["vert_data_size"],
                "idx_data_size": metas[1]["idx_data_size"],
                "pos_data_offset": metas[1]["pos_data_offset"],
                "vert_data_offset": metas[1]["vert_data_offset"],
                "idx_data_offset": metas[1]["idx_data_offset"],
            },
        ])
        return raw, exml

    def test_two_meshes_returned(self):
        from nmstoolkit.core.geometry_raw_stream_parser import parse_geometry_raw_stream
        raw, exml = self._make_two_triangles()
        meshes = parse_geometry_raw_stream(exml, raw)
        assert len(meshes) == 2

    def test_second_mesh_positions_correct(self):
        from nmstoolkit.core.geometry_raw_stream_parser import parse_geometry_raw_stream
        raw, exml = self._make_two_triangles()
        meshes = parse_geometry_raw_stream(exml, raw)
        ax, ay, az = meshes[1].vertices[0]
        assert ax == pytest.approx(10.0, abs=0.01)
        assert ay == pytest.approx(20.0, abs=0.01)
        assert az == pytest.approx(30.0, abs=0.01)


class TestIndexFormats:
    """C-FUNC-04: Stream data always uses 16-bit indices."""

    def _make_quad_raw(self):
        positions = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)]
        uvs = [(0, 0), (1, 0), (1, 1), (0, 1)]
        n_packed = [_pack_int_2_10_10_10_rev(0, 0, 511)] * 4
        t_packed = [_pack_int_2_10_10_10_rev(511, 0, 0)] * 4
        indices = (0, 1, 2, 0, 2, 3)

        sections = _build_raw_stream(
            positions, uvs, n_packed, t_packed, indices, is_16bit=True,
        )
        raw, metas = _pack_raw_file(sections)
        m = metas[0]
        return raw, m, indices

    def test_16bit_indices(self):
        from nmstoolkit.core.geometry_raw_stream_parser import parse_geometry_raw_stream
        raw, m, _ = self._make_quad_raw()
        exml = _build_geometry_exml(
            [{
                "id_string": "QUAD",
                "pos_data_size": m["pos_data_size"],
                "vert_data_size": m["vert_data_size"],
                "idx_data_size": m["idx_data_size"],
                "pos_data_offset": m["pos_data_offset"],
                "vert_data_offset": m["vert_data_offset"],
                "idx_data_offset": m["idx_data_offset"],
            }],
            is_16bit=True,
        )
        meshes = parse_geometry_raw_stream(exml, raw)
        assert meshes[0].indices == (0, 1, 2, 0, 2, 3)

    def test_indices16bit_flag_ignored_for_stream(self):
        """Stream data is always 16-bit regardless of root Indices16Bit flag."""
        from nmstoolkit.core.geometry_raw_stream_parser import parse_geometry_raw_stream
        raw, m, _ = self._make_quad_raw()
        exml = _build_geometry_exml(
            [{
                "id_string": "QUAD",
                "pos_data_size": m["pos_data_size"],
                "vert_data_size": m["vert_data_size"],
                "idx_data_size": m["idx_data_size"],
                "pos_data_offset": m["pos_data_offset"],
                "vert_data_offset": m["vert_data_offset"],
                "idx_data_offset": m["idx_data_offset"],
            }],
            is_16bit=False,  # EXML says 32-bit, but stream data is 16-bit
        )
        meshes = parse_geometry_raw_stream(exml, raw)
        assert meshes[0].indices == (0, 1, 2, 0, 2, 3)


class TestCollisionFiltering:
    """D4: Skip COLLISION meshes."""

    def test_collision_mesh_skipped(self):
        from nmstoolkit.core.geometry_raw_stream_parser import parse_geometry_raw_stream

        positions = [(0, 0, 0), (1, 0, 0), (0, 1, 0)]
        uvs = [(0, 0), (1, 0), (0, 1)]
        n_packed = [_pack_int_2_10_10_10_rev(0, 0, 511)] * 3
        t_packed = [_pack_int_2_10_10_10_rev(511, 0, 0)] * 3
        indices = (0, 1, 2)

        sections = _build_raw_stream(
            positions, uvs, n_packed, t_packed, indices,
        )
        raw, metas = _pack_raw_file(sections)
        m = metas[0]
        exml = _build_geometry_exml([{
            "id_string": "COLLISION",
            "pos_data_size": m["pos_data_size"],
            "vert_data_size": m["vert_data_size"],
            "idx_data_size": m["idx_data_size"],
            "pos_data_offset": m["pos_data_offset"],
            "vert_data_offset": m["vert_data_offset"],
            "idx_data_offset": m["idx_data_offset"],
        }])

        meshes = parse_geometry_raw_stream(exml, raw)
        assert len(meshes) == 0


class TestInvalidInput:
    """C-FUNC-07: Invalid/corrupt input returns empty list."""

    def test_empty_bytes(self):
        from nmstoolkit.core.geometry_raw_stream_parser import parse_geometry_raw_stream
        exml = _build_geometry_exml([{
            "id_string": "MESH",
            "pos_data_size": 48,
            "vert_data_size": 24,
            "idx_data_size": 6,
            "pos_data_offset": 0,
            "vert_data_offset": 0,
            "idx_data_offset": 0,
        }])
        assert parse_geometry_raw_stream(exml, b"") == []

    def test_garbage_exml(self):
        from nmstoolkit.core.geometry_raw_stream_parser import parse_geometry_raw_stream
        assert parse_geometry_raw_stream("<garbage/>", b"\x00" * 100) == []

    def test_truncated_data(self):
        from nmstoolkit.core.geometry_raw_stream_parser import parse_geometry_raw_stream
        exml = _build_geometry_exml([{
            "id_string": "MESH",
            "pos_data_size": 48,
            "vert_data_size": 24,
            "idx_data_size": 6,
            "pos_data_offset": 0,
            "vert_data_offset": 0,
            "idx_data_offset": 0,
        }])
        # Only 10 bytes — far too short
        assert parse_geometry_raw_stream(exml, b"\x00" * 10) == []


class TestDomainPurity:
    """C-ARCH-01: Parser uses stdlib only."""

    def test_no_external_imports(self):
        import pathlib
        src = pathlib.Path(
            "src/nmstoolkit/core/geometry_raw_stream_parser.py"
        ).read_text()
        tree = ast.parse(src)
        allowed_prefixes = {"__future__", "nmstoolkit", "xml", "struct", "hashlib", "math", "typing"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert any(
                        alias.name == p or alias.name.startswith(p + ".")
                        for p in allowed_prefixes
                    ), f"Forbidden import: {alias.name}"
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    assert any(
                        node.module == p or node.module.startswith(p + ".")
                        for p in allowed_prefixes
                    ), f"Forbidden import from: {node.module}"
