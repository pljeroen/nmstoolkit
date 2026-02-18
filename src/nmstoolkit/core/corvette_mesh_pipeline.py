"""Corvette mesh extraction and caching pipeline.

Application service that coordinates scene/geometry parsing with
disk caching for the 3D corvette builder.

Not a pure domain module — uses pathlib for file I/O (like game_data_pipeline.py).
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from nmstoolkit.core.geometry_parser import parse_geometry
from nmstoolkit.core.mesh_data import MaterialData, Mesh, SceneMeshEntry, SceneNode, Transform
from nmstoolkit.core.scene_parser import parse_scene


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
# Scene tree walking (R-RF-02)
# ---------------------------------------------------------------------------

def collect_scene_meshes(
    node: SceneNode,
    parent_matrix: Optional[List[float]] = None,
) -> List[SceneMeshEntry]:
    """Walk a SceneNode tree and collect all geometry references with world transforms.

    Returns a SceneMeshEntry for every node that has a non-empty geometry_ref.
    """
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
    ) -> MeshCacheEntry:
        """Extract meshes from parsed scene EXML and raw geometry binaries.

        Walks the full scene tree to collect geometry from all nodes,
        not just the root. Each node's world transform is composed from
        the scene hierarchy.

        Args:
            module_id: The corvette module ID (e.g. B_COK_A).
            scene_exml: EXML string of the module's SCENE.MBIN.
            geometry_data: Map of geometry path → raw binary data.

        Returns:
            MeshCacheEntry with parsed meshes and world transforms.
        """
        scene_node = parse_scene(scene_exml)
        entries = collect_scene_meshes(scene_node)

        meshes: List[Mesh] = []
        world_transforms: List[List[float]] = []
        geometry_ref = scene_node.geometry_ref or ""

        for entry in entries:
            if entry.geometry_ref in geometry_data:
                raw = geometry_data[entry.geometry_ref]
                submeshes = parse_geometry(raw)
                for submesh in submeshes:
                    meshes.append(submesh)
                    world_transforms.append(list(entry.world_matrix))

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
