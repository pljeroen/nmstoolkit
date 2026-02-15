"""Domain model for 3D mesh data — Mesh, Transform, SceneNode.

Pure domain module — stdlib only (dataclasses, typing).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class Transform:
    """3D transform: position, rotation (euler degrees), scale."""

    position: Tuple[float, float, float]
    rotation: Tuple[float, float, float]
    scale: Tuple[float, float, float]

    @classmethod
    def identity(cls) -> Transform:
        return cls(
            position=(0.0, 0.0, 0.0),
            rotation=(0.0, 0.0, 0.0),
            scale=(1.0, 1.0, 1.0),
        )


@dataclass(frozen=True)
class Mesh:
    """Triangle mesh with vertices, normals, UVs, and indices."""

    vertices: Tuple[Tuple[float, float, float], ...]
    normals: Tuple[Tuple[float, float, float], ...]
    uvs: Tuple[Tuple[float, float], ...]
    indices: Tuple[int, ...]

    @classmethod
    def empty(cls) -> Mesh:
        return cls(vertices=(), normals=(), uvs=(), indices=())

    @property
    def vertex_count(self) -> int:
        return len(self.vertices)

    @property
    def index_count(self) -> int:
        return len(self.indices)


@dataclass(frozen=True)
class SceneNode:
    """Node in a scene graph hierarchy."""

    name: str
    node_type: str
    transform: Transform
    geometry_ref: str
    material_ref: str
    children: Tuple[SceneNode, ...]
