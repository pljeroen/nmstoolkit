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
class MaterialData:
    """PBR material properties parsed from MATERIAL.MBIN EXML."""

    name: str
    diffuse_path: str
    normal_path: str
    mask_path: str
    roughness: float
    metalness: float

    @classmethod
    def empty(cls) -> MaterialData:
        return cls(
            name="",
            diffuse_path="",
            normal_path="",
            mask_path="",
            roughness=0.5,
            metalness=0.0,
        )


@dataclass(frozen=True)
class SceneNode:
    """Node in a scene graph hierarchy."""

    name: str
    node_type: str
    transform: Transform
    geometry_ref: str
    material_ref: str
    scene_ref: str
    children: Tuple[SceneNode, ...]


@dataclass(frozen=True)
class SceneMeshEntry:
    """A geometry reference collected from a scene tree walk, with world transform."""

    geometry_ref: str
    material_ref: str
    world_matrix: Tuple[float, ...]


@dataclass(frozen=True)
class DescriptorOption:
    """One selectable part in a descriptor group.

    Attributes:
        id: Node name matching SceneNode.name in the scene tree.
        chance: Selection weight. 0 means equal weight among siblings.
        children: Nested descriptor groups for sub-part selection.
    """

    id: str
    chance: float
    children: Tuple[DescriptorGroup, ...]


@dataclass(frozen=True)
class DescriptorGroup:
    """A group of mutually exclusive part options — pick exactly one.

    Attributes:
        type_id: Group identifier from the DESCRIPTOR EXML.
        options: Available parts to choose from (one is selected at random).
    """

    type_id: str
    options: Tuple[DescriptorOption, ...]
