"""Tests for geometry_parser — binary GEOMETRY.MBIN parser.

Tests construct known binary data, parse it, and verify results match.
"""

import struct

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from nmstoolkit.core.geometry_parser import (
    parse_geometry,
    unpack_half_floats,
    unpack_int_2_10_10_10_rev,
)
from nmstoolkit.core.mesh_data import Mesh


class TestHalfFloatDecoding:
    """Half-float (format 'e') decoding accuracy."""

    def test_zero(self):
        data = struct.pack("<e", 0.0)
        result = unpack_half_floats(data, 1)
        assert result[0] == pytest.approx(0.0)

    def test_one(self):
        data = struct.pack("<e", 1.0)
        result = unpack_half_floats(data, 1)
        assert result[0] == pytest.approx(1.0)

    def test_negative_one(self):
        data = struct.pack("<e", -1.0)
        result = unpack_half_floats(data, 1)
        assert result[0] == pytest.approx(-1.0)

    def test_half(self):
        data = struct.pack("<e", 0.5)
        result = unpack_half_floats(data, 1)
        assert result[0] == pytest.approx(0.5)

    def test_multiple_values(self):
        values = [0.0, 1.0, -1.0, 0.5]
        data = struct.pack("<4e", *values)
        result = unpack_half_floats(data, 4)
        for i, v in enumerate(values):
            assert result[i] == pytest.approx(v)

    @given(st.floats(min_value=-65000, max_value=65000, allow_nan=False, allow_infinity=False))
    @settings(max_examples=50)
    def test_roundtrip_hypothesis(self, value):
        """Half-float roundtrip within half-float precision."""
        try:
            data = struct.pack("<e", value)
        except (OverflowError, struct.error):
            return  # Value outside half-float range
        result = unpack_half_floats(data, 1)
        expected = struct.unpack("<e", data)[0]
        assert result[0] == pytest.approx(expected, abs=1e-3)


class TestInt2101010RevUnpacking:
    """INT_2_10_10_10_REV packed normal unpacking."""

    def test_unit_x(self):
        """Pack (1, 0, 0) as INT_2_10_10_10_REV and verify."""
        # 10-bit signed: 511 = max positive (maps to ~1.0)
        packed = _pack_int_2_10_10_10_rev(511, 0, 0)
        x, y, z = unpack_int_2_10_10_10_rev(packed)
        assert x == pytest.approx(1.0, abs=0.01)
        assert y == pytest.approx(0.0, abs=0.01)
        assert z == pytest.approx(0.0, abs=0.01)

    def test_unit_y(self):
        packed = _pack_int_2_10_10_10_rev(0, 511, 0)
        x, y, z = unpack_int_2_10_10_10_rev(packed)
        assert x == pytest.approx(0.0, abs=0.01)
        assert y == pytest.approx(1.0, abs=0.01)
        assert z == pytest.approx(0.0, abs=0.01)

    def test_unit_z(self):
        packed = _pack_int_2_10_10_10_rev(0, 0, 511)
        x, y, z = unpack_int_2_10_10_10_rev(packed)
        assert x == pytest.approx(0.0, abs=0.01)
        assert y == pytest.approx(0.0, abs=0.01)
        assert z == pytest.approx(1.0, abs=0.01)

    def test_negative_x(self):
        """Pack (-1, 0, 0) — 10-bit signed -512 maps to -1.0."""
        packed = _pack_int_2_10_10_10_rev(-512, 0, 0)
        x, y, z = unpack_int_2_10_10_10_rev(packed)
        assert x == pytest.approx(-1.0, abs=0.01)

    def test_diagonal_normal(self):
        """Approximate (0.577, 0.577, 0.577) — each component ~295/511."""
        val = 295  # 295/511 ≈ 0.577
        packed = _pack_int_2_10_10_10_rev(val, val, val)
        x, y, z = unpack_int_2_10_10_10_rev(packed)
        assert x == pytest.approx(0.577, abs=0.01)
        assert y == pytest.approx(0.577, abs=0.01)
        assert z == pytest.approx(0.577, abs=0.01)


class TestGeometryParsing:
    """Full geometry binary parsing."""

    def test_single_triangle_16bit_indices(self):
        """Parse a minimal geometry with one triangle, 16-bit indices."""
        vertices = [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)]
        normals = [(0.0, 0.0, 1.0)] * 3
        uvs = [(0.0, 0.0), (1.0, 0.0), (0.0, 1.0)]
        indices = [0, 1, 2]

        data = _build_geometry_binary(
            vertices=vertices,
            normals=normals,
            uvs=uvs,
            indices=indices,
            use_16bit_indices=True,
        )
        meshes = parse_geometry(data)
        assert len(meshes) == 1
        mesh = meshes[0]
        assert mesh.vertex_count == 3
        assert mesh.index_count == 3

        for i, (vx, vy, vz) in enumerate(vertices):
            assert mesh.vertices[i][0] == pytest.approx(vx, abs=0.01)
            assert mesh.vertices[i][1] == pytest.approx(vy, abs=0.01)
            assert mesh.vertices[i][2] == pytest.approx(vz, abs=0.01)

    def test_32bit_indices(self):
        """Parse with 32-bit index buffer."""
        vertices = [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)]
        normals = [(0.0, 0.0, 1.0)] * 3
        uvs = [(0.0, 0.0), (1.0, 0.0), (0.0, 1.0)]
        indices = [0, 1, 2]

        data = _build_geometry_binary(
            vertices=vertices,
            normals=normals,
            uvs=uvs,
            indices=indices,
            use_16bit_indices=False,
        )
        meshes = parse_geometry(data)
        assert len(meshes) == 1
        assert meshes[0].index_count == 3

    def test_multi_mesh(self):
        """Parse geometry with two submeshes (different vertex ranges)."""
        # Two triangles as separate submeshes
        verts = [
            (0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0),
            (2.0, 0.0, 0.0), (3.0, 0.0, 0.0), (2.0, 1.0, 0.0),
        ]
        normals = [(0.0, 0.0, 1.0)] * 6
        uvs = [(0.0, 0.0), (1.0, 0.0), (0.0, 1.0)] * 2
        indices = [0, 1, 2, 3, 4, 5]
        mesh_ranges = [(0, 3, 0, 3), (3, 3, 3, 3)]  # (vert_start, vert_count, idx_start, idx_count)

        data = _build_geometry_binary(
            vertices=verts,
            normals=normals,
            uvs=uvs,
            indices=indices,
            use_16bit_indices=True,
            mesh_ranges=mesh_ranges,
        )
        meshes = parse_geometry(data)
        assert len(meshes) == 2
        assert meshes[0].vertex_count == 3
        assert meshes[1].vertex_count == 3

    def test_empty_data_returns_empty(self):
        """Empty or too-short data returns empty list."""
        assert parse_geometry(b"") == []
        assert parse_geometry(b"\x00" * 4) == []

    def test_uv_extraction(self):
        """Verify UV coordinates are extracted correctly."""
        vertices = [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)]
        normals = [(0.0, 0.0, 1.0)] * 3
        uvs = [(0.25, 0.75), (0.5, 0.5), (0.75, 0.25)]
        indices = [0, 1, 2]

        data = _build_geometry_binary(
            vertices=vertices,
            normals=normals,
            uvs=uvs,
            indices=indices,
            use_16bit_indices=True,
        )
        meshes = parse_geometry(data)
        mesh = meshes[0]
        for i, (u, v) in enumerate(uvs):
            assert mesh.uvs[i][0] == pytest.approx(u, abs=0.01)
            assert mesh.uvs[i][1] == pytest.approx(v, abs=0.01)


# ---------------------------------------------------------------------------
# Test helpers — build binary geometry data
# ---------------------------------------------------------------------------

def _pack_int_2_10_10_10_rev(x: int, y: int, z: int, w: int = 0) -> int:
    """Pack xyz into INT_2_10_10_10_REV format (u32).

    Each of x, y, z is 10-bit signed (-512..511), w is 2-bit signed.
    Layout: [x:10][y:10][z:10][w:2] from LSB.
    """
    x_bits = x & 0x3FF
    y_bits = y & 0x3FF
    z_bits = z & 0x3FF
    w_bits = w & 0x3
    return x_bits | (y_bits << 10) | (z_bits << 20) | (w_bits << 30)


def _build_geometry_binary(
    vertices,
    normals,
    uvs,
    indices,
    use_16bit_indices=True,
    mesh_ranges=None,
):
    """Build a binary blob matching NMS GEOMETRY.MBIN format.

    This produces the raw binary format (NOT EXML) with:
    - Header: vertex_count(u32), index_count(u32), is_16bit(u32), collision_index_count(u32)
    - Joint count (u32) = 0
    - Mesh descriptor count + descriptors
    - Vertex layout: element count, stride, element descriptors
    - Index data
    - Vertex data (interleaved: position half4 + uv half4 + normal packed u32)
    """
    vertex_count = len(vertices)
    index_count = len(indices)
    is_16bit = 1 if use_16bit_indices else 0

    if mesh_ranges is None:
        mesh_ranges = [(0, vertex_count, 0, index_count)]

    parts = []

    # --- Header ---
    parts.append(struct.pack("<IIII", vertex_count, index_count, is_16bit, 0))

    # --- Joint count ---
    parts.append(struct.pack("<I", 0))

    # --- Mesh descriptor count + descriptors ---
    parts.append(struct.pack("<I", len(mesh_ranges)))
    for vert_start, vert_count, idx_start, idx_count in mesh_ranges:
        # Each descriptor: vert_start(u32), vert_count(u32), idx_start(u32), idx_count(u32)
        # Plus bounding box (6 floats: minx, miny, minz, maxx, maxy, maxz)
        parts.append(struct.pack("<IIII", vert_start, vert_count, idx_start, idx_count))
        parts.append(struct.pack("<6f", -1.0, -1.0, -1.0, 1.0, 1.0, 1.0))

    # --- Vertex layout ---
    # 3 elements: position (semantic 0), uv (semantic 1), normal (semantic 2)
    num_elements = 3
    # Stride: position=8 bytes (half4) + uv=8 bytes (half4) + normal=4 bytes (packed u32) = 20
    stride = 20
    parts.append(struct.pack("<II", num_elements, stride))

    # Element descriptors: SemanticID(u32), Type(u32), Size(u32), Offset(u32), Normalise(u32)
    # Position: semantic=0, type=5131 (half), size=8, offset=0, normalise=0
    parts.append(struct.pack("<IIIII", 0, 5131, 8, 0, 0))
    # UV: semantic=1, type=5131, size=8, offset=8, normalise=0
    parts.append(struct.pack("<IIIII", 1, 5131, 8, 8, 0))
    # Normal: semantic=2, type=36255 (INT_2_10_10_10_REV), size=4, offset=16, normalise=0
    parts.append(struct.pack("<IIIII", 2, 36255, 4, 16, 0))

    # --- Index data ---
    if use_16bit_indices:
        for idx in indices:
            parts.append(struct.pack("<H", idx))
        # Pad to 4-byte alignment
        if (index_count * 2) % 4 != 0:
            parts.append(b"\x00\x00")
    else:
        for idx in indices:
            parts.append(struct.pack("<I", idx))

    # --- Vertex data (interleaved) ---
    for i in range(vertex_count):
        vx, vy, vz = vertices[i]
        u, v = uvs[i]
        nx, ny, nz = normals[i]

        # Position: half-float x4 (xyz + w=1.0)
        parts.append(struct.pack("<4e", vx, vy, vz, 1.0))
        # UV: half-float x4 (uv + uv2 = 0,0)
        parts.append(struct.pack("<4e", u, v, 0.0, 0.0))
        # Normal: INT_2_10_10_10_REV packed
        nx_int = int(round(nx * 511))
        ny_int = int(round(ny * 511))
        nz_int = int(round(nz * 511))
        packed = _pack_int_2_10_10_10_rev(nx_int, ny_int, nz_int)
        parts.append(struct.pack("<I", packed))

    return b"".join(parts)
