"""Parser for MBINCompiler geometry stream EXML (cTkGeometryStreamData)."""

from __future__ import annotations

import base64
import hashlib
import struct
from typing import Dict, List, Tuple
from xml.etree.ElementTree import fromstring

from nmstoolkit.core.geometry_parser import unpack_int_2_10_10_10_rev
from nmstoolkit.core.mesh_data import Mesh


def parse_geometry_stream_exml(geometry_exml: str, stream_exml: str) -> List[Mesh]:
    """Parse mesh geometry from cTkGeometryData + cTkGeometryStreamData EXML."""
    g_root = fromstring(geometry_exml)
    s_root = fromstring(stream_exml)

    is_16bit = _int_prop(g_root, "Indices16Bit") == 1
    vertex_layout = _parse_layout(g_root, "VertexLayout")
    position_layout = _parse_layout(g_root, "PositionVertexLayout")

    meta = _stream_meta_by_id(g_root)
    stream_data = _stream_data_by_id(s_root)
    meshes: List[Mesh] = []

    seen_stream_hashes: set[str] = set()

    for mesh_id, m in meta.items():
        s = stream_data.get(mesh_id)
        if s is None:
            continue

        mesh_data = base64.b64decode(s["mesh_data_b64"])
        pos_data = base64.b64decode(s["mesh_pos_b64"])
        vdata_size = int(m.get("VertexDataSize", 0))
        idata_size = int(m.get("IndexDataSize", 0))
        pdata_size = int(m.get("VertexPositionDataSize", 0))
        vdata_offset = int(m.get("VertexDataOffset", 0))
        idata_offset = int(m.get("IndexDataOffset", 0))
        pdata_offset = int(m.get("VertexPositionDataOffset", 0))

        if not mesh_data or not pos_data:
            continue
        if vdata_size <= 0 or idata_size <= 0:
            continue
        if pdata_size <= 0:
            pdata_size = len(pos_data)

        # Stream blocks from cTkGeometryStreamData are typically already sliced
        # per mesh, but some metadata still carries absolute offsets from packed
        # files. Use offsets only when they fit stream bounds.
        if 0 <= vdata_offset < len(mesh_data) and vdata_offset + vdata_size <= len(mesh_data):
            v_start = vdata_offset
        else:
            v_start = 0
        if idata_offset > 0 and v_start + idata_offset + idata_size <= len(mesh_data):
            i_start = v_start + idata_offset
        elif v_start + vdata_size + idata_size <= len(mesh_data):
            i_start = v_start + vdata_size
        else:
            continue
        if 0 <= pdata_offset < len(pos_data) and pdata_offset + pdata_size <= len(pos_data):
            p_start = pdata_offset
        else:
            p_start = 0

        v_stream = mesh_data[v_start:v_start + vdata_size]
        i_stream = mesh_data[i_start:i_start + idata_size]
        p_stream = pos_data[p_start:p_start + pdata_size]
        stream_hash = hashlib.sha1(v_stream + i_stream + p_stream).hexdigest()
        if stream_hash in seen_stream_hashes:
            continue
        seen_stream_hashes.add(stream_hash)

        verts, uvs = _parse_position_stream(p_stream, position_layout)
        normals = _parse_normal_stream(v_stream, vertex_layout, len(verts))
        indices = _parse_indices(i_stream, is_16bit)

        if not verts or not indices:
            continue
        meshes.append(
            Mesh(
                vertices=tuple(verts),
                normals=tuple(normals),
                uvs=tuple(uvs),
                indices=tuple(indices),
            )
        )

    return meshes


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


def _stream_meta_by_id(root) -> Dict[str, dict]:
    out: Dict[str, dict] = {}
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


def _stream_data_by_id(root) -> Dict[str, dict]:
    out: Dict[str, dict] = {}
    parent = root.find("Property[@name='StreamDataArray']")
    if parent is None:
        return out
    for e in parent.findall("Property"):
        mesh_id = _str_prop(e, "IdString")
        if not mesh_id:
            continue
        out[mesh_id] = {
            "mesh_data_b64": _str_prop(e, "MeshDataStream"),
            "mesh_pos_b64": _str_prop(e, "MeshPositionDataStream"),
        }
    return out


def _str_prop(root, name: str) -> str:
    node = root.find(f"Property[@name='{name}']")
    if node is None:
        return ""
    return node.get("value", "")


def _parse_position_stream(data: bytes, layout: dict) -> Tuple[List[Tuple[float, float, float]], List[Tuple[float, float]]]:
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

    verts = []
    uvs = []
    for i in range(count):
        base = i * stride
        px, py, pz, _ = struct.unpack_from("<4e", data, base + pos_off)
        u, v, _, _ = struct.unpack_from("<4e", data, base + uv_off)
        verts.append((float(px), float(py), float(pz)))
        uvs.append((float(u), float(v)))
    return verts, uvs


def _parse_normal_stream(data: bytes, layout: dict, count: int) -> List[Tuple[float, float, float]]:
    stride = layout.get("stride", 0)
    if stride <= 0:
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
