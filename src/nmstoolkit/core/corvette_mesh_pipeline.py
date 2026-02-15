"""Corvette mesh extraction and caching pipeline.

Application service that coordinates scene/geometry parsing with
disk caching for the 3D corvette builder.

Not a pure domain module — uses pathlib for file I/O (like game_data_pipeline.py).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from nmstoolkit.core.geometry_parser import parse_geometry
from nmstoolkit.core.mesh_data import Mesh
from nmstoolkit.core.scene_parser import parse_scene


@dataclass
class MeshCacheEntry:
    """Cache entry for a single corvette module's mesh data."""

    module_id: str
    meshes: List[Mesh]
    texture_path: Optional[Path]
    geometry_ref: str


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

        Args:
            module_id: The corvette module ID (e.g. B_COK_A).
            scene_exml: EXML string of the module's SCENE.MBIN.
            geometry_data: Map of geometry path → raw binary data.

        Returns:
            MeshCacheEntry with parsed meshes.
        """
        scene_node = parse_scene(scene_exml)
        geometry_ref = scene_node.geometry_ref

        meshes: List[Mesh] = []
        if geometry_ref and geometry_ref in geometry_data:
            raw = geometry_data[geometry_ref]
            meshes = parse_geometry(raw)

        entry = MeshCacheEntry(
            module_id=module_id,
            meshes=meshes,
            texture_path=None,
            geometry_ref=geometry_ref,
        )
        self.save_entry(entry)
        return entry

    def save_entry(self, entry: MeshCacheEntry) -> None:
        """Serialize a MeshCacheEntry to JSON on disk."""
        data = {
            "module_id": entry.module_id,
            "geometry_ref": entry.geometry_ref,
            "texture_path": str(entry.texture_path) if entry.texture_path else None,
            "meshes": [_mesh_to_dict(m) for m in entry.meshes],
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

        return MeshCacheEntry(
            module_id=data["module_id"],
            meshes=meshes,
            texture_path=tex_path,
            geometry_ref=data.get("geometry_ref", ""),
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
