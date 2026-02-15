"""Parser for NMS GEOMETRY.MBIN binary format.

Pure domain module — stdlib only (struct).

NMS GEOMETRY.MBIN binary structure:
1. Header: vertex_count(u32), index_count(u32), is_16bit(u32), collision_index_count(u32)
2. Joint count (u32)
3. Mesh descriptor count + descriptors (vertex/index ranges + bounding boxes)
4. Vertex layout: element count, stride, element descriptors
5. Index buffer (u16 or u32)
6. Vertex stream (interleaved per layout stride)

Vertex attribute formats:
- SemanticID 0 (Position): half-float × 4 → xyz + w(discard)
- SemanticID 1 (UV): half-float × 4 → two uv pairs (use first)
- SemanticID 2 (Normal): INT_2_10_10_10_REV packed u32 → extract xyz 10-bit signed
- SemanticID 3 (Tangent): same packed format (ignored)
"""

from __future__ import annotations

import struct
from typing import List, Tuple

from nmstoolkit.core.mesh_data import Mesh

# GL type constants
_HALF_FLOAT = 5131
_INT_2_10_10_10_REV = 36255

# Minimum header size: 4 u32s = 16 bytes
_MIN_HEADER_SIZE = 16


def unpack_half_floats(data: bytes, count: int) -> Tuple[float, ...]:
    """Unpack `count` half-float (16-bit) values from bytes."""
    fmt = f"<{count}e"
    return struct.unpack(fmt, data[:count * 2])


def unpack_int_2_10_10_10_rev(packed: int) -> Tuple[float, float, float]:
    """Unpack INT_2_10_10_10_REV u32 into normalized xyz floats.

    Layout from LSB: [x:10][y:10][z:10][w:2].
    Each 10-bit component is signed (-512..511), normalized by dividing by 511.
    """
    x_raw = packed & 0x3FF
    y_raw = (packed >> 10) & 0x3FF
    z_raw = (packed >> 20) & 0x3FF

    # Sign-extend 10-bit to signed int
    x_signed = x_raw if x_raw < 512 else x_raw - 1024
    y_signed = y_raw if y_raw < 512 else y_raw - 1024
    z_signed = z_raw if z_raw < 512 else z_raw - 1024

    return (x_signed / 511.0, y_signed / 511.0, z_signed / 511.0)


def parse_geometry(data: bytes) -> List[Mesh]:
    """Parse raw GEOMETRY.MBIN binary into a list of Mesh objects.

    Returns one Mesh per submesh descriptor. Returns empty list for
    invalid or too-short data.
    """
    if len(data) < _MIN_HEADER_SIZE:
        return []

    try:
        return _parse_geometry_impl(data)
    except (struct.error, IndexError, ValueError):
        return []


def _parse_geometry_impl(data: bytes) -> List[Mesh]:
    """Internal parser — raises on malformed data."""
    offset = 0

    # --- Header ---
    vertex_count, index_count, is_16bit, collision_index_count = struct.unpack_from(
        "<IIII", data, offset
    )
    offset += 16

    if vertex_count == 0:
        return []

    # --- Joint count ---
    (joint_count,) = struct.unpack_from("<I", data, offset)
    offset += 4

    # --- Mesh descriptors ---
    (mesh_count,) = struct.unpack_from("<I", data, offset)
    offset += 4

    mesh_ranges = []
    for _ in range(mesh_count):
        vert_start, vert_count, idx_start, idx_count = struct.unpack_from(
            "<IIII", data, offset
        )
        offset += 16
        # Skip bounding box (6 floats)
        offset += 24
        mesh_ranges.append((vert_start, vert_count, idx_start, idx_count))

    # --- Vertex layout ---
    num_elements, stride = struct.unpack_from("<II", data, offset)
    offset += 8

    # Element descriptors
    elements = []
    for _ in range(num_elements):
        semantic_id, elem_type, size, elem_offset, normalise = struct.unpack_from(
            "<IIIII", data, offset
        )
        offset += 20
        elements.append((semantic_id, elem_type, size, elem_offset))

    # --- Index data ---
    index_data_offset = offset
    if is_16bit:
        index_size = index_count * 2
        # Pad to 4-byte alignment
        padded_size = (index_size + 3) & ~3
    else:
        padded_size = index_count * 4

    # --- Vertex data ---
    vertex_data_offset = index_data_offset + padded_size

    # Build lookup for element semantics
    pos_elem = None
    uv_elem = None
    normal_elem = None
    for semantic_id, elem_type, size, elem_offset in elements:
        if semantic_id == 0:
            pos_elem = (elem_type, elem_offset)
        elif semantic_id == 1:
            uv_elem = (elem_type, elem_offset)
        elif semantic_id == 2:
            normal_elem = (elem_type, elem_offset)

    # --- Parse meshes ---
    meshes = []
    for vert_start, vert_count, idx_start, idx_count in mesh_ranges:
        vertices = []
        normals = []
        uvs = []

        for v in range(vert_count):
            v_base = vertex_data_offset + (vert_start + v) * stride

            # Position
            if pos_elem is not None:
                p_off = v_base + pos_elem[1]
                px, py, pz, _ = struct.unpack_from("<4e", data, p_off)
                vertices.append((float(px), float(py), float(pz)))
            else:
                vertices.append((0.0, 0.0, 0.0))

            # UV
            if uv_elem is not None:
                uv_off = v_base + uv_elem[1]
                u, v_coord, _, _ = struct.unpack_from("<4e", data, uv_off)
                uvs.append((float(u), float(v_coord)))
            else:
                uvs.append((0.0, 0.0))

            # Normal
            if normal_elem is not None:
                n_off = v_base + normal_elem[1]
                (packed,) = struct.unpack_from("<I", data, n_off)
                nx, ny, nz = unpack_int_2_10_10_10_rev(packed)
                normals.append((nx, ny, nz))
            else:
                normals.append((0.0, 0.0, 1.0))

        # Indices
        indices = []
        for i in range(idx_count):
            if is_16bit:
                i_off = index_data_offset + (idx_start + i) * 2
                (idx_val,) = struct.unpack_from("<H", data, i_off)
            else:
                i_off = index_data_offset + (idx_start + i) * 4
                (idx_val,) = struct.unpack_from("<I", data, i_off)
            # Rebase index relative to submesh vertex start
            indices.append(idx_val - vert_start)

        meshes.append(Mesh(
            vertices=tuple(vertices),
            normals=tuple(normals),
            uvs=tuple(uvs),
            indices=tuple(indices),
        ))

    return meshes
