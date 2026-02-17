"""Fallback parser: derive layered box meshes from geometry EXML AABBs.

Used when raw GEOMETRY.MBIN(.pc) binary parsing yields no meshes.
"""

from __future__ import annotations

from typing import Dict, List, Tuple
from xml.etree.ElementTree import fromstring

from nmstoolkit.core.mesh_data import Mesh


def parse_geometry_aabb_fallback(source: str) -> List[Mesh]:
    """Build one box mesh per MeshAABBMin/Max entry found in geometry EXML."""
    root = fromstring(source)
    mins = _parse_vec4_array(root, "MeshAABBMin")
    maxs = _parse_vec4_array(root, "MeshAABBMax")
    meshes: List[Mesh] = []
    for idx in sorted(set(mins.keys()) & set(maxs.keys())):
        mn = mins[idx]
        mx = maxs[idx]
        if mn == mx:
            continue
        meshes.append(_build_box_mesh(mn, mx))
    return _normalize_meshes_to_cell(meshes)


def _parse_vec4_array(root, array_name: str) -> Dict[int, Tuple[float, float, float]]:
    out: Dict[int, Tuple[float, float, float]] = {}
    parent = root.find(f"Property[@name='{array_name}']")
    if parent is None:
        return out
    for entry in parent.findall("Property"):
        idx_str = entry.get("_index", "")
        if not idx_str.isdigit():
            continue
        idx = int(idx_str)
        x = _float(entry, "X")
        y = _float(entry, "Y")
        z = _float(entry, "Z")
        out[idx] = (x, y, z)
    return out


def _float(parent, name: str) -> float:
    node = parent.find(f"Property[@name='{name}']")
    if node is None:
        return 0.0
    try:
        return float(node.get("value", "0") or "0")
    except ValueError:
        return 0.0


def _build_box_mesh(min_xyz: Tuple[float, float, float], max_xyz: Tuple[float, float, float]) -> Mesh:
    min_x, min_y, min_z = min_xyz
    max_x, max_y, max_z = max_xyz
    x0, x1 = sorted((min_x, max_x))
    y0, y1 = sorted((min_y, max_y))
    z0, z1 = sorted((min_z, max_z))

    verts = []
    norms = []
    uvs = []
    indices = []

    face_uvs = ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0))
    faces = [
        ((0.0, 1.0, 0.0), ((x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1))),   # top
        ((0.0, -1.0, 0.0), ((x0, y0, z1), (x1, y0, z1), (x1, y0, z0), (x0, y0, z0))),  # bottom
        ((0.0, 0.0, 1.0), ((x0, y0, z1), (x0, y1, z1), (x1, y1, z1), (x1, y0, z1))),   # front
        ((0.0, 0.0, -1.0), ((x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z0))),  # back
        ((1.0, 0.0, 0.0), ((x1, y0, z1), (x1, y1, z1), (x1, y1, z0), (x1, y0, z0))),   # right
        ((-1.0, 0.0, 0.0), ((x0, y0, z0), (x0, y1, z0), (x0, y1, z1), (x0, y0, z1))),  # left
    ]

    for normal, corners in faces:
        base = len(verts)
        for corner in corners:
            verts.append(corner)
            norms.append(normal)
        uvs.extend(face_uvs)
        indices.extend((base, base + 1, base + 2, base, base + 2, base + 3))

    return Mesh(
        vertices=tuple(verts),
        normals=tuple(norms),
        uvs=tuple(uvs),
        indices=tuple(indices),
    )


def _normalize_meshes_to_cell(meshes: List[Mesh]) -> List[Mesh]:
    """Normalize layered meshes to fit a single module cell around origin."""
    if not meshes:
        return meshes

    min_x = min(v[0] for m in meshes for v in m.vertices)
    min_y = min(v[1] for m in meshes for v in m.vertices)
    min_z = min(v[2] for m in meshes for v in m.vertices)
    max_x = max(v[0] for m in meshes for v in m.vertices)
    max_y = max(v[1] for m in meshes for v in m.vertices)
    max_z = max(v[2] for m in meshes for v in m.vertices)

    sx = max_x - min_x
    sy = max_y - min_y
    sz = max_z - min_z
    max_dim = max(sx, sy, sz, 1e-6)
    target = 0.9
    scale = target / max_dim
    cx = (min_x + max_x) * 0.5
    cy = (min_y + max_y) * 0.5
    cz = (min_z + max_z) * 0.5

    normalized: List[Mesh] = []
    for mesh in meshes:
        verts = tuple(
            (
                (v[0] - cx) * scale,
                (v[1] - cy) * scale,
                (v[2] - cz) * scale,
            )
            for v in mesh.vertices
        )
        normalized.append(
            Mesh(
                vertices=verts,
                normals=mesh.normals,
                uvs=mesh.uvs,
                indices=mesh.indices,
            )
        )
    return normalized
