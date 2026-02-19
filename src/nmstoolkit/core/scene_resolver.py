"""Resolve REFERENCE nodes in scene trees and filter geometry by descriptor.

Pure domain module — stdlib only.

REFERENCE nodes in NMS procedural scene trees point to sub-scene MBINs via
their scene_ref attribute. This module provides:
- resolve_references: recursively replaces REFERENCE nodes with loaded sub-scenes
- filter_scene_geometry: collects geometry refs with transforms, filtered by descriptor
"""

from __future__ import annotations

from typing import Dict, FrozenSet, List, Optional, Set, Tuple

from nmstoolkit.core.mesh_data import SceneNode, Transform


def resolve_references(
    root: SceneNode,
    scene_lookup: Dict[str, SceneNode],
    _seen: Optional[Set[str]] = None,
) -> SceneNode:
    """Recursively replace REFERENCE nodes with loaded sub-scene content.

    Args:
        root: Scene tree root to resolve.
        scene_lookup: Map of normalized scene path → parsed SceneNode tree.
            Keys must be lowercase with forward slashes.
        _seen: Internal cycle detection set. Do not pass externally.

    Returns:
        New SceneNode tree with REFERENCE nodes populated with sub-scene children.
        Non-REFERENCE nodes pass through unchanged. Missing or cyclic references
        keep the original empty REFERENCE node.
    """
    if _seen is None:
        _seen = set()

    return _resolve_node(root, scene_lookup, _seen)


def _resolve_node(
    node: SceneNode,
    scene_lookup: Dict[str, SceneNode],
    seen: Set[str],
) -> SceneNode:
    """Resolve a single node, recursing into children."""
    if node.node_type.upper() == "REFERENCE" and node.scene_ref:
        normalized = node.scene_ref.replace("\\", "/").lower()
        if normalized in seen:
            return node
        sub_scene = scene_lookup.get(normalized)
        if sub_scene is None:
            return node
        seen.add(normalized)
        resolved_sub = _resolve_node(sub_scene, scene_lookup, seen)
        return SceneNode(
            name=node.name,
            node_type=node.node_type,
            transform=node.transform,
            geometry_ref=node.geometry_ref,
            material_ref=node.material_ref,
            scene_ref=node.scene_ref,
            children=resolved_sub.children,
        )

    resolved_children = tuple(
        _resolve_node(child, scene_lookup, seen) for child in node.children
    )
    if resolved_children == node.children:
        return node
    return SceneNode(
        name=node.name,
        node_type=node.node_type,
        transform=node.transform,
        geometry_ref=node.geometry_ref,
        material_ref=node.material_ref,
        scene_ref=node.scene_ref,
        children=resolved_children,
    )


def filter_scene_geometry(
    scene_root: SceneNode,
    active_nodes: Optional[FrozenSet[str]] = None,
) -> List[Tuple[str, Transform]]:
    """Collect geometry references from a scene tree, optionally filtered by descriptor.

    When active_nodes is None, all geometry is collected (except COLLISION nodes).
    When active_nodes is a frozenset, REFERENCE-type nodes whose name is not in
    the set are skipped entirely (pruning their sub-trees).

    Args:
        scene_root: Root of a (possibly resolved) scene tree.
        active_nodes: Descriptor-selected node names, or None for all.

    Returns:
        List of (geometry_ref, world_transform) tuples.
    """
    out: List[Tuple[str, Transform]] = []
    _walk(scene_root, Transform.identity(), active_nodes, out)
    return out


def _combine_transform(parent: Transform, local: Transform) -> Transform:
    """Compose parent and local transforms."""
    import math

    psx, psy, psz = parent.scale
    lpx, lpy, lpz = local.position
    sp = (lpx * psx, lpy * psy, lpz * psz)

    rx, ry, rz = (
        math.radians(parent.rotation[0]),
        math.radians(parent.rotation[1]),
        math.radians(parent.rotation[2]),
    )
    x, y, z = sp
    cy, sy = math.cos(rx), math.sin(rx)
    y, z = y * cy - z * sy, y * sy + z * cy
    cx, sx = math.cos(ry), math.sin(ry)
    x, z = x * cx + z * sx, -x * sx + z * cx
    cz, sz = math.cos(rz), math.sin(rz)
    x, y = x * cz - y * sz, x * sz + y * cz

    return Transform(
        position=(parent.position[0] + x, parent.position[1] + y, parent.position[2] + z),
        rotation=(
            parent.rotation[0] + local.rotation[0],
            parent.rotation[1] + local.rotation[1],
            parent.rotation[2] + local.rotation[2],
        ),
        scale=(psx * local.scale[0], psy * local.scale[1], psz * local.scale[2]),
    )


def _walk(
    node: SceneNode,
    world: Transform,
    active_nodes: Optional[FrozenSet[str]],
    out: List[Tuple[str, Transform]],
) -> None:
    """Recursive tree walk collecting geometry instances."""
    composed = _combine_transform(world, node.transform)
    node_type_upper = str(node.node_type).upper()

    if node_type_upper == "COLLISION":
        return

    if active_nodes is not None and node.name:
        if node_type_upper == "REFERENCE" and node.name not in active_nodes:
            return

    if node.geometry_ref:
        out.append((node.geometry_ref, composed))

    for child in node.children:
        _walk(child, composed, active_nodes, out)
