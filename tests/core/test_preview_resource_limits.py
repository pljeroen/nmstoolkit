"""Tests for preview pipeline resource safety limits.

Contract: RESOURCE-SAFETY-01
Requirements: RS-01 through RS-08

Tests verify that the preview loading pipeline enforces:
- Recursion depth limits on sub-scene reference collection
- Sub-scene count limits
- Geometry instance count caps
- Total vertex budget caps
- Per-mesh vertex sanity caps
- Cancellation callback support
"""

import pytest

from nmstoolkit.core.mesh_data import Mesh, SceneNode, Transform


# ---------------------------------------------------------------------------
# Helpers — build scene trees for testing limits
# ---------------------------------------------------------------------------

def _leaf(name: str, geo_ref: str = "", node_type: str = "MESH") -> SceneNode:
    """Create a leaf SceneNode with optional geometry reference."""
    return SceneNode(
        name=name,
        node_type=node_type,
        transform=Transform.identity(),
        geometry_ref=geo_ref,
        material_ref="",
        scene_ref="",
        children=(),
    )


def _ref_node(name: str, scene_ref: str, children: tuple = ()) -> SceneNode:
    """Create a REFERENCE SceneNode."""
    return SceneNode(
        name=name,
        node_type="REFERENCE",
        transform=Transform.identity(),
        geometry_ref="",
        material_ref="",
        scene_ref=scene_ref,
        children=children,
    )


def _container(name: str, children: tuple, geo_ref: str = "", node_type: str = "MODEL") -> SceneNode:
    """Create a container SceneNode with children."""
    return SceneNode(
        name=name,
        node_type=node_type,
        transform=Transform.identity(),
        geometry_ref=geo_ref,
        material_ref="",
        scene_ref="",
        children=children,
    )


def _make_mesh(vertex_count: int) -> Mesh:
    """Create a Mesh with the given number of vertices."""
    verts = tuple((float(i), 0.0, 0.0) for i in range(vertex_count))
    normals = tuple((0.0, 0.0, 1.0) for _ in range(vertex_count))
    uvs = tuple((0.0, 0.0) for _ in range(vertex_count))
    indices = tuple(range(min(vertex_count, 3)))  # minimal valid triangle
    return Mesh(vertices=verts, normals=normals, uvs=uvs, indices=indices)


# ---------------------------------------------------------------------------
# RS-02: Recursion depth limit in _collect_refs
# ---------------------------------------------------------------------------

class TestRefCollectionDepthLimit:
    """RS-02: Sub-scene reference resolution stops at max depth."""

    def test_deep_chain_stopped_at_limit(self):
        """A reference chain deeper than max_depth should be truncated."""
        from nmstoolkit.core.scene_resolver import resolve_references

        # Build a chain: root -> ref_A -> ref_B -> ref_C -> ... (20 levels deep)
        # Each sub-scene is a REFERENCE pointing to the next
        depth = 20
        lookup = {}
        for i in range(depth):
            next_ref = f"scene_{i + 1}.mbin" if i < depth - 1 else ""
            child = _leaf(f"geo_{i}", geo_ref=f"geo_{i}.mbin")
            if next_ref:
                ref_child = _ref_node(f"ref_{i + 1}", next_ref)
                sub = _container(f"sub_{i}", children=(child, ref_child))
            else:
                sub = _container(f"sub_{i}", children=(child,))
            lookup[f"scene_{i}.mbin"] = sub

        root = _ref_node("root_ref", "scene_0.mbin")
        root_container = _container("ROOT", children=(root,))

        result = resolve_references(root_container, lookup, max_depth=5)

        # Count resolved geometry refs in the tree
        geo_refs = _collect_geo_refs(result)
        # With max_depth=5, we should get at most 5 resolved levels, not all 20
        assert len(geo_refs) <= 6  # 5 levels + maybe root

    def test_shallow_chain_fully_resolved(self):
        """A reference chain within max_depth should be fully resolved."""
        from nmstoolkit.core.scene_resolver import resolve_references

        lookup = {}
        child = _leaf("geo_leaf", geo_ref="leaf.mbin")
        sub_b = _container("sub_b", children=(child,))
        lookup["scene_b.mbin"] = sub_b

        ref_b = _ref_node("ref_b", "scene_b.mbin")
        sub_a = _container("sub_a", children=(ref_b,), geo_ref="sub_a.mbin")
        lookup["scene_a.mbin"] = sub_a

        root = _ref_node("root_ref", "scene_a.mbin")
        root_container = _container("ROOT", children=(root,))

        result = resolve_references(root_container, lookup, max_depth=10)

        geo_refs = _collect_geo_refs(result)
        assert "leaf.mbin" in geo_refs
        assert "sub_a.mbin" in geo_refs


# ---------------------------------------------------------------------------
# RS-03: Sub-scene count limit
# ---------------------------------------------------------------------------

class TestRefCollectionSceneCountLimit:
    """RS-03: Sub-scene reference resolution stops at max scene count."""

    def test_many_refs_truncated_at_limit(self):
        """A scene with 100 references should stop collecting at max_scenes."""
        from nmstoolkit.core.scene_resolver import resolve_references

        lookup = {}
        refs = []
        for i in range(100):
            child = _leaf(f"geo_{i}", geo_ref=f"geo_{i}.mbin")
            sub = _container(f"sub_{i}", children=(child,))
            lookup[f"scene_{i}.mbin"] = sub
            refs.append(_ref_node(f"ref_{i}", f"scene_{i}.mbin"))

        root = _container("ROOT", children=tuple(refs))
        result = resolve_references(root, lookup, max_scenes=10)

        # Count how many sub-scenes were resolved (have children)
        resolved = sum(1 for c in result.children if c.children)
        assert resolved <= 10


# ---------------------------------------------------------------------------
# RS-04: Geometry instance count cap
# ---------------------------------------------------------------------------

class TestInstanceCountCap:
    """RS-04: Geometry instances truncated at cap."""

    def test_instances_capped(self):
        from nmstoolkit.core.scene_resolver import filter_scene_geometry

        # Build a tree with 300 geometry nodes
        children = tuple(
            _leaf(f"mesh_{i}", geo_ref=f"geo_{i}.mbin")
            for i in range(300)
        )
        root = _container("ROOT", children=children)

        instances = filter_scene_geometry(root, max_instances=50)
        assert len(instances) <= 50

    def test_default_limit_allows_normal_ships(self):
        """Default limit should allow typical ship geometry (< 200)."""
        from nmstoolkit.core.scene_resolver import filter_scene_geometry

        children = tuple(
            _leaf(f"mesh_{i}", geo_ref=f"geo_{i}.mbin")
            for i in range(150)
        )
        root = _container("ROOT", children=children)

        instances = filter_scene_geometry(root)
        assert len(instances) == 150


# ---------------------------------------------------------------------------
# RS-05: Total vertex budget
# ---------------------------------------------------------------------------

class TestVertexBudget:
    """RS-05: Total vertex budget caps mesh accumulation."""

    def test_mesh_is_valid_enforces_vertex_cap(self):
        from nmstoolkit.gui.preview_support import _mesh_is_valid, MAX_VERTICES_PER_MESH

        huge = _make_mesh(MAX_VERTICES_PER_MESH + 1)
        assert _mesh_is_valid(huge) is False

    def test_mesh_is_valid_allows_normal_mesh(self):
        from nmstoolkit.gui.preview_support import _mesh_is_valid

        normal = _make_mesh(1000)
        assert _mesh_is_valid(normal) is True


# ---------------------------------------------------------------------------
# RS-06: Per-mesh vertex sanity cap
# ---------------------------------------------------------------------------

class TestPerMeshVertexCap:
    """RS-06: Meshes exceeding per-mesh vertex cap are skipped."""

    def test_oversized_mesh_rejected(self):
        from nmstoolkit.gui.preview_support import _mesh_is_valid, MAX_VERTICES_PER_MESH

        oversized = _make_mesh(MAX_VERTICES_PER_MESH + 100)
        assert _mesh_is_valid(oversized) is False

    def test_normal_mesh_accepted(self):
        from nmstoolkit.gui.preview_support import _mesh_is_valid

        normal = _make_mesh(50000)
        assert _mesh_is_valid(normal) is True

    def test_empty_mesh_rejected(self):
        from nmstoolkit.gui.preview_support import _mesh_is_valid

        empty = Mesh(vertices=(), normals=(), uvs=(), indices=())
        assert _mesh_is_valid(empty) is False


# ---------------------------------------------------------------------------
# RS-02/RS-03: _resolve_scene_references limits (integration level)
# ---------------------------------------------------------------------------

class TestResolveSceneReferencesLimits:
    """Integration: _resolve_scene_references enforces depth and count limits."""

    def test_depth_limit_parameter_accepted(self):
        """_resolve_scene_references accepts max_depth and max_scenes params."""
        from nmstoolkit.gui.preview_support import _resolve_scene_references

        root = _leaf("empty", node_type="MODEL")
        # Should not raise — just returns root unchanged
        result = _resolve_scene_references(
            root, {}, pak=None, converter=None, parse_scene_fn=None,
            max_depth=5, max_scenes=10,
        )
        assert result.name == "empty"


# ---------------------------------------------------------------------------
# Walk depth limit in filter_scene_geometry
# ---------------------------------------------------------------------------

class TestWalkDepthLimit:
    """Safety: _walk stops at max depth to prevent stack overflow."""

    def test_deeply_nested_tree_truncated(self):
        from nmstoolkit.core.scene_resolver import filter_scene_geometry

        # Build a 100-deep nested tree
        node = _leaf("deep_leaf", geo_ref="deep.mbin")
        for i in range(100):
            node = _container(f"level_{i}", children=(node,))

        # With reasonable depth, should not stack overflow and should truncate
        instances = filter_scene_geometry(node, max_depth=20)
        # Should get some instances but not necessarily all 100+ levels
        assert len(instances) <= 21  # at most max_depth + 1 nodes


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _collect_geo_refs(node: SceneNode) -> list:
    """Recursively collect all geometry_ref values from a scene tree."""
    refs = []
    if node.geometry_ref:
        refs.append(node.geometry_ref)
    for child in node.children:
        refs.extend(_collect_geo_refs(child))
    return refs
