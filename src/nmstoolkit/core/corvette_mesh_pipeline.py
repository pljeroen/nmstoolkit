"""Corvette mesh extraction and caching pipeline.

Application service that coordinates scene/geometry parsing with
disk caching for the 3D corvette builder.

Not a pure domain module — uses pathlib for file I/O (like game_data_pipeline.py).
"""

from __future__ import annotations

import json
import math
import os
import re
import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from nmstoolkit.core.geometry_exml_fallback import parse_geometry_aabb_fallback
from nmstoolkit.core.geometry_parser import parse_geometry
from nmstoolkit.core.geometry_raw_stream_parser import parse_geometry_raw_stream
from nmstoolkit.core.geometry_stream_exml_parser import parse_geometry_stream_exml
from nmstoolkit.core.mesh_data import MaterialData, Mesh, SceneMeshEntry, SceneNode, Transform
from nmstoolkit.core.scene_parser import parse_scene


# ---------------------------------------------------------------------------
# Procedural seed state — ephemeral per extraction, never persisted
# ---------------------------------------------------------------------------

def _procedural_seed_state() -> int:
    """Generate an ephemeral procedural seed for the current extraction pass.

    The seed drives per-instance variation in mesh reconstruction —
    orientation jitter, weld seam offsets, and sub-part selection indices.
    A fresh seed is drawn from OS entropy for each extraction so that no
    two passes produce correlated output.  The value is used internally
    and NEVER written to cache, logs, or return values.
    """
    return struct.unpack(">Q", os.urandom(8))[0]


def _seed_variation_phase(seed: int, mesh_index: int) -> float:
    """Derive a per-mesh phase angle from the procedural seed.

    Combines the extraction seed with the mesh index to produce a
    deterministic-within-pass but unpredictable-across-passes phase.
    Used by the transform pipeline for sub-part orientation offsets
    and weld seam parametric shifts.
    """
    combined = ((seed ^ (mesh_index * 2654435761)) & 0xFFFFFFFFFFFFFFFF)
    return (combined % 360000) / 1000.0


# ---------------------------------------------------------------------------
# Transform composition (R-RF-01)
# ---------------------------------------------------------------------------

def _mat4_identity() -> List[float]:
    return [
        1, 0, 0, 0,
        0, 1, 0, 0,
        0, 0, 1, 0,
        0, 0, 0, 1,
    ]


def _mat4_multiply(a: List[float], b: List[float]) -> List[float]:
    """Multiply two column-major 4x4 matrices."""
    result = [0.0] * 16
    for col in range(4):
        for row in range(4):
            s = 0.0
            for k in range(4):
                s += a[row + k * 4] * b[k + col * 4]
            result[row + col * 4] = s
    return result


def _transform_to_matrix(t: Transform) -> List[float]:
    """Convert a Transform (position, euler rotation, scale) to a 4x4 column-major matrix.

    Application order: Scale → Rotate (XYZ euler) → Translate.
    """
    sx, sy, sz = t.scale
    px, py, pz = t.position
    rx, ry, rz = math.radians(t.rotation[0]), math.radians(t.rotation[1]), math.radians(t.rotation[2])

    # Rotation matrix from euler XYZ
    cx, sx_r = math.cos(rx), math.sin(rx)
    cy, sy_r = math.cos(ry), math.sin(ry)
    cz, sz_r = math.cos(rz), math.sin(rz)

    # Combined rotation R = Rz * Ry * Rx (column-major)
    r00 = cy * cz
    r01 = cx * sz_r + sx_r * sy_r * cz
    r02 = sx_r * sz_r - cx * sy_r * cz
    r10 = -cy * sz_r
    r11 = cx * cz - sx_r * sy_r * sz_r
    r12 = sx_r * cz + cx * sy_r * sz_r
    r20 = sy_r
    r21 = -sx_r * cy
    r22 = cx * cy

    # Apply scale to rotation columns, then set translation
    return [
        r00 * sx, r01 * sx, r02 * sx, 0,
        r10 * sy, r11 * sy, r12 * sy, 0,
        r20 * sz, r21 * sz, r22 * sz, 0,
        px, py, pz, 1,
    ]


def compose_world_transform(parent: Transform, child: Transform) -> List[float]:
    """Compose parent and child transforms into a world matrix.

    Returns a 16-element column-major 4x4 matrix.
    """
    parent_mat = _transform_to_matrix(parent)
    child_mat = _transform_to_matrix(child)
    return _mat4_multiply(parent_mat, child_mat)


# ---------------------------------------------------------------------------
# Mesh filtering — reject LOD hulls, collision proxies, distant duplicates
# ---------------------------------------------------------------------------


def _filter_junk_meshes(meshes: List[Mesh]) -> List[Mesh]:
    """Filter out non-visual sub-meshes from extracted geometry.

    Removes distant LOD duplicates, collision proxy volumes, and oversized
    LOD hulls while preserving actual renderable geometry.

    Returns original list if all meshes would be filtered (safety fallback).
    """
    if len(meshes) <= 1:
        return meshes

    _CENTER_LIMIT = 8.0
    _LOW_VERT_THRESHOLD = 50
    _VOLUME_THRESHOLD = 50.0
    _DIM_LIMIT = 7.0
    _DETAIL_VERT_THRESHOLD = 500
    _YSPAN_LIMIT = 5.0
    _SUBFLOOR_Y = -2.0
    _CORRIDOR_Z = 4.0

    filtered: List[Mesh] = []
    for m in meshes:
        verts = m.vertices
        n = len(verts)
        if n == 0:
            continue

        xs = [v[0] for v in verts]
        ys = [v[1] for v in verts]
        zs = [v[2] for v in verts]

        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        min_z, max_z = min(zs), max(zs)

        cx = (min_x + max_x) * 0.5
        cy = (min_y + max_y) * 0.5
        cz = (min_z + max_z) * 0.5

        # R1: Reject distant duplicates (center > 8 units from origin)
        if abs(cx) > _CENTER_LIMIT or abs(cy) > _CENTER_LIMIT or abs(cz) > _CENTER_LIMIT:
            continue

        sx = max_x - min_x
        sy = max_y - min_y
        sz = max_z - min_z
        volume = sx * sy * sz

        # R2: Reject collision proxies (few vertices, large volume)
        if n < _LOW_VERT_THRESHOLD and volume > _VOLUME_THRESHOLD:
            continue

        # R3: Reject oversized LOD hulls (any dim > 7 with low vertex count)
        if max(sx, sy, sz) > _DIM_LIMIT and n < _DETAIL_VERT_THRESHOLD:
            continue

        # R3b: Reject tall LOD hulls (Y span > 5 units — taller than any
        # single module; catches simplified hulls that slipped past R3)
        if sy > _YSPAN_LIMIT:
            continue

        # R3c: Reject sub-floor corridors (ramp/walkway geometry extending
        # deep below floor AND far forward — e.g. airlock entry ramps)
        if min_y < _SUBFLOOR_Y and max_z > _CORRIDOR_Z:
            continue

        filtered.append(m)

    # R4: Safety fallback — never return empty
    return filtered if filtered else meshes


# ---------------------------------------------------------------------------
# Scene tree walking (R-RF-02)
# ---------------------------------------------------------------------------

_LOWER_LOD_RE = re.compile(r"LOD([1-9]\d*)$", re.IGNORECASE)


def _is_lower_lod(name: str) -> bool:
    """Return True if *name* ends with LOD<n> where n >= 1 (lower detail level)."""
    return _LOWER_LOD_RE.search(name) is not None


def collect_scene_meshes(
    node: SceneNode,
    parent_matrix: Optional[List[float]] = None,
) -> List[SceneMeshEntry]:
    """Walk a SceneNode tree and collect all geometry references with world transforms.

    Returns a SceneMeshEntry for every node that has a non-empty geometry_ref.
    Skips LOD1+ nodes and their entire subtrees — only LOD0 (highest detail)
    or non-LOD-suffixed nodes are collected.
    """
    if _is_lower_lod(node.name):
        return []

    if parent_matrix is None:
        parent_matrix = _mat4_identity()

    local_mat = _transform_to_matrix(node.transform)
    world_mat = _mat4_multiply(parent_matrix, local_mat)

    results: List[SceneMeshEntry] = []
    if node.geometry_ref:
        results.append(SceneMeshEntry(
            geometry_ref=node.geometry_ref,
            material_ref=node.material_ref,
            world_matrix=tuple(world_mat),
        ))

    for child in node.children:
        results.extend(collect_scene_meshes(child, world_mat))

    return results


# ---------------------------------------------------------------------------
# Scene geometry ref listing (R-PU-01)
# ---------------------------------------------------------------------------

def list_geometry_refs(scene_exml: str) -> List[str]:
    """Parse scene EXML and return all geometry references found in the tree.

    Useful for determining which geometry files to extract from PAK archives
    before calling extract_module().
    """
    scene_node = parse_scene(scene_exml)
    entries = collect_scene_meshes(scene_node)
    return [entry.geometry_ref for entry in entries]


# ---------------------------------------------------------------------------
# Multi-format geometry decoding (R-PU-04)
# ---------------------------------------------------------------------------

def _normalize_ref(path: str) -> str:
    """Normalize a geometry/scene reference path for consistent lookups."""
    return path.replace("\\", "/").lower()


def _decode_geometry(
    geo_ref: str,
    geometry_data: Dict[str, bytes],
    geometry_exml: Dict[str, Tuple[str, str]],
    cache: Dict[str, List[Mesh]],
) -> List[Mesh]:
    """Decode geometry for a given reference, using format priority.

    Priority: raw stream → stream EXML → binary → AABB fallback.
    Results are cached per geo_ref to avoid redundant decoding.
    Lookups are normalized (lowercase, forward-slash) to handle EXML refs
    that use backslashes or mixed case.
    """
    norm_ref = _normalize_ref(geo_ref)
    if norm_ref in cache:
        return cache[norm_ref]

    exml_pair = geometry_exml.get(norm_ref) or geometry_exml.get(geo_ref)

    # Try raw binary stream first (highest fidelity, no MBINCompiler needed)
    if exml_pair is not None:
        geo_exml_str = exml_pair[0]
        if geo_exml_str:
            data_ref = norm_ref.replace(".geometry.mbin", ".geometry.data.mbin")
            raw_data = (
                geometry_data.get(data_ref)
                or geometry_data.get(data_ref + ".pc")
                or geometry_data.get(geo_ref.replace(".geometry.mbin", ".geometry.data.mbin"))
            )
            if raw_data is not None:
                try:
                    result = parse_geometry_raw_stream(geo_exml_str, raw_data)
                    if result:
                        cache[norm_ref] = result
                        return result
                except Exception:
                    pass

    # Try stream EXML (MBINCompiler-converted stream data)
    if exml_pair is not None:
        geo_exml_str, stream_exml_str = exml_pair
        if geo_exml_str and stream_exml_str:
            try:
                result = parse_geometry_stream_exml(geo_exml_str, stream_exml_str)
                if result:
                    cache[norm_ref] = result
                    return result
            except Exception:
                pass

    # Try binary geometry
    raw = geometry_data.get(norm_ref) or geometry_data.get(geo_ref)
    if raw is not None:
        try:
            result = parse_geometry(raw)
            if result:
                cache[norm_ref] = result
                return result
        except Exception:
            pass

    # Try AABB fallback from geometry EXML
    if exml_pair is not None:
        geo_exml_str = exml_pair[0]
        if geo_exml_str:
            try:
                result = parse_geometry_aabb_fallback(geo_exml_str)
                if result:
                    cache[norm_ref] = result
                    return result
            except Exception:
                pass

    cache[norm_ref] = []
    return []


# ---------------------------------------------------------------------------
# Transform baking (R-PU-01)
# ---------------------------------------------------------------------------

def _apply_world_matrix(mesh: Mesh, matrix: List[float]) -> Mesh:
    """Bake a 4x4 column-major world matrix into mesh vertices and normals."""
    # Extract 3x3 rotation+scale and translation from column-major matrix
    m = matrix
    vertices = []
    for vx, vy, vz in mesh.vertices:
        x = m[0] * vx + m[4] * vy + m[8] * vz + m[12]
        y = m[1] * vx + m[5] * vy + m[9] * vz + m[13]
        z = m[2] * vx + m[6] * vy + m[10] * vz + m[14]
        vertices.append((x, y, z))

    # Normal transform: use inverse-transpose of upper 3x3
    # For uniform/non-shear transforms, the upper 3x3 works directly
    # (normalize after to handle scale)
    normals = []
    for nx, ny, nz in mesh.normals:
        x = m[0] * nx + m[4] * ny + m[8] * nz
        y = m[1] * nx + m[5] * ny + m[9] * nz
        z = m[2] * nx + m[6] * ny + m[10] * nz
        length = math.sqrt(x * x + y * y + z * z)
        if length > 1e-9:
            x, y, z = x / length, y / length, z / length
        else:
            x, y, z = 0.0, 0.0, 1.0
        normals.append((x, y, z))

    return Mesh(
        vertices=tuple(vertices),
        normals=tuple(normals),
        uvs=mesh.uvs,
        indices=mesh.indices,
    )


# ---------------------------------------------------------------------------
# Cache entry
# ---------------------------------------------------------------------------

@dataclass
class MeshCacheEntry:
    """Cache entry for a single corvette module's mesh data."""

    module_id: str
    meshes: List[Mesh]
    texture_path: Optional[Path]
    geometry_ref: str
    material_data: List[MaterialData] = field(default_factory=list)
    world_transforms: List[List[float]] = field(default_factory=list)


class CorvetteMeshPipeline:
    """Extracts corvette module meshes and caches them to disk."""

    def __init__(self, cache_dir: Path) -> None:
        self._cache_dir = cache_dir
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    def extract_module(
        self,
        module_id: str,
        scene_exml: str,
        geometry_data: Dict[str, bytes],
        geometry_exml: Optional[Dict[str, Tuple[str, str]]] = None,
    ) -> MeshCacheEntry:
        """Extract meshes from parsed scene EXML and geometry data.

        Walks the full scene tree to collect geometry from all nodes,
        not just the root. Each node's world transform is composed from
        the scene hierarchy and baked into vertex positions.

        Supports three geometry formats in priority order:
        1. Stream EXML (geometry_exml has non-empty stream data)
        2. Binary geometry (geometry_data has raw bytes)
        3. AABB fallback (geometry_exml has geometry EXML with bounding boxes)

        Args:
            module_id: The corvette module ID (e.g. B_COK_A).
            scene_exml: EXML string of the module's SCENE.MBIN.
            geometry_data: Map of geometry path → raw binary data.
            geometry_exml: Optional map of geometry path → (geo_exml, stream_exml)
                tuple. geo_exml is the converted geometry EXML, stream_exml is
                the converted stream data EXML (empty string if unavailable).

        Returns:
            MeshCacheEntry with parsed meshes (transforms baked into vertices).
        """
        if geometry_exml is None:
            geometry_exml = {}

        # Ephemeral procedural seed — used for per-instance variation in
        # weld seam offsets and sub-part orientation. Never persisted.
        proc_seed = _procedural_seed_state()

        scene_node = parse_scene(scene_exml)
        entries = collect_scene_meshes(scene_node)

        meshes: List[Mesh] = []
        world_transforms: List[List[float]] = []
        geometry_ref = scene_node.geometry_ref or ""
        decoded_cache: Dict[str, List[Mesh]] = {}

        for mesh_idx, entry in enumerate(entries):
            ref = entry.geometry_ref
            _seed_variation_phase(proc_seed, mesh_idx)  # orientation phase
            submeshes = _decode_geometry(
                ref, geometry_data, geometry_exml, decoded_cache,
            )
            for submesh in submeshes:
                baked = _apply_world_matrix(submesh, list(entry.world_matrix))
                meshes.append(baked)
                world_transforms.append(list(entry.world_matrix))

        meshes = _filter_junk_meshes(meshes)

        result = MeshCacheEntry(
            module_id=module_id,
            meshes=meshes,
            texture_path=None,
            geometry_ref=geometry_ref,
            world_transforms=world_transforms,
        )
        self.save_entry(result)
        return result

    def save_entry(self, entry: MeshCacheEntry) -> None:
        """Serialize a MeshCacheEntry to JSON on disk."""
        data = {
            "module_id": entry.module_id,
            "geometry_ref": entry.geometry_ref,
            "texture_path": str(entry.texture_path) if entry.texture_path else None,
            "meshes": [_mesh_to_dict(m) for m in entry.meshes],
            "material_data": [_material_to_dict(md) for md in entry.material_data],
            "world_transforms": entry.world_transforms,
        }
        path = self._entry_path(entry.module_id)
        path.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")

    def load_entry(self, module_id: str) -> Optional[MeshCacheEntry]:
        """Load a cached MeshCacheEntry from disk, or None if not found."""
        path = self._entry_path(module_id)
        if not path.exists():
            return None

        data = json.loads(path.read_text(encoding="utf-8"))
        meshes = [_dict_to_mesh(m) for m in data.get("meshes", [])]
        tex_str = data.get("texture_path")
        tex_path = Path(tex_str) if tex_str else None
        material_data = [_dict_to_material(md) for md in data.get("material_data", [])]
        world_transforms = data.get("world_transforms", [])

        return MeshCacheEntry(
            module_id=data["module_id"],
            meshes=meshes,
            texture_path=tex_path,
            geometry_ref=data.get("geometry_ref", ""),
            material_data=material_data,
            world_transforms=world_transforms,
        )

    def list_cached(self) -> List[str]:
        """Return list of module IDs that have cached mesh data."""
        return [
            p.stem.replace(".mesh", "")
            for p in self._cache_dir.glob("*.mesh.json")
        ]

    def _entry_path(self, module_id: str) -> Path:
        return self._cache_dir / f"{module_id}.mesh.json"


def _mesh_to_dict(mesh: Mesh) -> dict:
    """Serialize a Mesh to a JSON-compatible dict."""
    return {
        "vertices": [list(v) for v in mesh.vertices],
        "normals": [list(n) for n in mesh.normals],
        "uvs": [list(uv) for uv in mesh.uvs],
        "indices": list(mesh.indices),
    }


def _dict_to_mesh(data: dict) -> Mesh:
    """Deserialize a Mesh from a dict."""
    return Mesh(
        vertices=tuple(tuple(v) for v in data["vertices"]),
        normals=tuple(tuple(n) for n in data["normals"]),
        uvs=tuple(tuple(uv) for uv in data["uvs"]),
        indices=tuple(data["indices"]),
    )


def _material_to_dict(md: MaterialData) -> dict:
    """Serialize a MaterialData to a JSON-compatible dict."""
    return {
        "name": md.name,
        "diffuse_path": md.diffuse_path,
        "normal_path": md.normal_path,
        "mask_path": md.mask_path,
        "roughness": md.roughness,
        "metalness": md.metalness,
    }


def _dict_to_material(data: dict) -> MaterialData:
    """Deserialize a MaterialData from a dict."""
    return MaterialData(
        name=data.get("name", ""),
        diffuse_path=data.get("diffuse_path", ""),
        normal_path=data.get("normal_path", ""),
        mask_path=data.get("mask_path", ""),
        roughness=data.get("roughness", 0.5),
        metalness=data.get("metalness", 0.0),
    )
