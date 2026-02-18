"""Parser for raw binary geometry stream data (.geometry.data.mbin).

Reads vertex/index data directly from raw binary using offset/size/format
metadata from the corresponding cTkGeometryData EXML.  This bypasses
MBINCompiler conversion entirely — the .data.mbin is raw binary, not MBIN.

Pure domain module — stdlib only (struct, xml.etree).
"""

from __future__ import annotations

import hashlib
import struct
from typing import List, Tuple
from xml.etree.ElementTree import fromstring

from nmstoolkit.core.geometry_parser import unpack_int_2_10_10_10_rev
from nmstoolkit.core.mesh_data import Mesh


def parse_geometry_raw_stream(geometry_exml: str, raw_data: bytes) -> List[Mesh]:
    """Parse mesh geometry from cTkGeometryData EXML metadata + raw binary stream.

    Args:
        geometry_exml: EXML string from the converted .geometry.mbin.pc file.
            Contains vertex layout specs and per-mesh stream offset/size metadata.
        raw_data: Raw bytes from the .geometry.data.mbin file.
            Contains packed vertex positions, normals, UVs, and index buffers.

    Returns:
        List of Mesh objects, one per non-collision StreamMetaData entry.
        Empty list on any parsing error.
    """
    if not raw_data or not geometry_exml:
        return []

    try:
        g_root = fromstring(geometry_exml)
    except Exception:
        return []

    is_16bit = _int_prop(g_root, "Indices16Bit") == 1
    vertex_layout = _parse_layout(g_root, "VertexLayout")
    position_layout = _parse_layout(g_root, "PositionVertexLayout")

    meta = _stream_meta_by_id(g_root)
    if not meta:
        return []

    meshes: List[Mesh] = []
    seen_hashes: set[str] = set()

    for mesh_id, m in meta.items():
        if "COLLISION" in mesh_id.upper():
            continue

        pos_size = m["VertexPositionDataSize"]
        vert_size = m["VertexDataSize"]
        idx_size = m["IndexDataSize"]
        pos_offset = m["VertexPositionDataOffset"]
        vert_offset = m["VertexDataOffset"]
        idx_offset = m["IndexDataOffset"]

        if pos_size <= 0 or idx_size <= 0:
            continue

        # Bounds check against raw data
        if pos_offset + pos_size > len(raw_data):
            continue
        if vert_size > 0 and vert_offset + vert_size > len(raw_data):
            continue
        if idx_offset + idx_size > len(raw_data):
            continue

        p_stream = raw_data[pos_offset:pos_offset + pos_size]
        v_stream = raw_data[vert_offset:vert_offset + vert_size] if vert_size > 0 else b""
        i_stream = raw_data[idx_offset:idx_offset + idx_size]

        # Deduplicate identical streams
        stream_hash = hashlib.sha1(p_stream + v_stream + i_stream).hexdigest()
        if stream_hash in seen_hashes:
            continue
        seen_hashes.add(stream_hash)

        verts, uvs = _parse_position_stream(p_stream, position_layout)
        normals = _parse_normal_stream(v_stream, vertex_layout, len(verts))
        indices = _parse_indices(i_stream, is_16bit)

        if not verts or not indices:
            continue

        meshes.append(Mesh(
            vertices=tuple(verts),
            normals=tuple(normals),
            uvs=tuple(uvs),
            indices=tuple(indices),
        ))

    return meshes


# ---------------------------------------------------------------------------
# EXML metadata extraction
# ---------------------------------------------------------------------------

def _int_prop(root, name: str, default: int = 0) -> int:
    node = root.find(f"Property[@name='{name}']")
    if node is None:
        return default
    try:
        return int(node.get("value", str(default)))
    except ValueError:
        return default


def _parse_layout(root, layout_name: str) -> dict:
    layout = root.find(f"Property[@name='{layout_name}']")
    if layout is None:
        return {"stride": 0, "elements": []}
    stride = _int_prop(layout, "Stride")
    elems_parent = layout.find("Property[@name='VertexElements']")
    elems = []
    if elems_parent is not None:
        for e in elems_parent.findall("Property"):
            elems.append({
                "semantic": _int_prop(e, "SemanticID"),
                "type": _int_prop(e, "Type"),
                "offset": _int_prop(e, "Offset"),
            })
    return {"stride": stride, "elements": elems}


def _stream_meta_by_id(root) -> dict:
    out: dict = {}
    parent = root.find("Property[@name='StreamMetaDataArray']")
    if parent is None:
        return out
    for e in parent.findall("Property"):
        mesh_id = _str_prop(e, "IdString")
        if not mesh_id:
            continue
        out[mesh_id] = {
            "VertexDataSize": _int_prop(e, "VertexDataSize"),
            "VertexPositionDataSize": _int_prop(e, "VertexPositionDataSize"),
            "IndexDataSize": _int_prop(e, "IndexDataSize"),
            "VertexDataOffset": _int_prop(e, "VertexDataOffset"),
            "VertexPositionDataOffset": _int_prop(e, "VertexPositionDataOffset"),
            "IndexDataOffset": _int_prop(e, "IndexDataOffset"),
        }
    return out


def _str_prop(root, name: str) -> str:
    node = root.find(f"Property[@name='{name}']")
    if node is None:
        return ""
    return node.get("value", "")


# ---------------------------------------------------------------------------
# Binary stream decoding
# ---------------------------------------------------------------------------

def _parse_position_stream(
    data: bytes, layout: dict,
) -> Tuple[List[Tuple[float, float, float]], List[Tuple[float, float]]]:
    stride = layout.get("stride", 0)
    if stride <= 0:
        return [], []
    count = len(data) // stride
    pos_off = 0
    uv_off = 8
    for e in layout.get("elements", []):
        if e["semantic"] == 0:
            pos_off = e["offset"]
        elif e["semantic"] == 1:
            uv_off = e["offset"]

    verts: List[Tuple[float, float, float]] = []
    uvs: List[Tuple[float, float]] = []
    for i in range(count):
        base = i * stride
        px, py, pz, _ = struct.unpack_from("<4e", data, base + pos_off)
        u, v, _, _ = struct.unpack_from("<4e", data, base + uv_off)
        verts.append((float(px), float(py), float(pz)))
        uvs.append((float(u), float(v)))
    return verts, uvs


def _parse_normal_stream(
    data: bytes, layout: dict, count: int,
) -> List[Tuple[float, float, float]]:
    stride = layout.get("stride", 0)
    if stride <= 0 or not data:
        return [(0.0, 0.0, 1.0)] * count
    normal_off = 0
    has_normal = False
    for e in layout.get("elements", []):
        if e["semantic"] == 2:
            has_normal = True
            normal_off = e["offset"]
            break
    if not has_normal:
        return [(0.0, 0.0, 1.0)] * count

    ncount = min(count, len(data) // stride)
    out: List[Tuple[float, float, float]] = []
    for i in range(ncount):
        base = i * stride
        packed = struct.unpack_from("<I", data, base + normal_off)[0]
        out.append(unpack_int_2_10_10_10_rev(packed))
    if ncount < count:
        out.extend([(0.0, 0.0, 1.0)] * (count - ncount))
    return out


def _parse_indices(data: bytes, is_16bit: bool) -> List[int]:
    if is_16bit:
        count = len(data) // 2
        return list(struct.unpack_from(f"<{count}H", data, 0))
    count = len(data) // 4
    return list(struct.unpack_from(f"<{count}I", data, 0))
