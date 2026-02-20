"""Tests for REFERENCE node resolution in scene trees.

Contract: DESCRIPTOR-PREVIEW-02
R-DP02-03: Recursive reference resolution with cycle detection.
R-DP02-04: Descriptor filtering on REFERENCE-type node boundaries.
"""

import pytest

from nmstoolkit.core.mesh_data import SceneNode, Transform
from nmstoolkit.core.scene_parser import parse_scene


# ---------------------------------------------------------------------------
# Helper: build SceneNode trees without XML boilerplate
# ---------------------------------------------------------------------------

def _node(name, node_type="MESH", geometry_ref="", scene_ref="", children=()):
    return SceneNode(
        name=name,
        node_type=node_type,
        transform=Transform.identity(),
        geometry_ref=geometry_ref,
        material_ref="",
        scene_ref=scene_ref,
        children=tuple(children),
    )


def _ref_node(name, scene_ref, children=()):
    return _node(name, node_type="REFERENCE", scene_ref=scene_ref, children=children)


def _geo_node(name, geometry_ref):
    return _node(name, node_type="MESH", geometry_ref=geometry_ref)


# ---------------------------------------------------------------------------
# resolve_references import — lazy to allow RED phase to detect missing impl
# ---------------------------------------------------------------------------

def _import_resolve_references():
    """Import resolve_references. Returns None if not yet implemented."""
    try:
        from nmstoolkit.core.scene_resolver import resolve_references
        return resolve_references
    except ImportError:
        return None


def _import_filter_geometry():
    """Import filter_scene_geometry. Returns None if not yet implemented."""
    try:
        from nmstoolkit.core.scene_resolver import filter_scene_geometry
        return filter_scene_geometry
    except ImportError:
        return None


# ---------------------------------------------------------------------------
# R-DP02-03: Reference resolution tests
# ---------------------------------------------------------------------------

class TestResolveReferences:
    """Recursive reference resolution replaces REFERENCE nodes with loaded sub-scenes."""

    def test_single_reference_resolved(self):
        resolve = _import_resolve_references()
        assert resolve is not None, "resolve_references not implemented"

        sub_scene = _node(
            "WingRoot", "MODEL",
            children=[_geo_node("WingMesh", "MODELS/WINGS/GEO.MBIN")],
        )
        scene_lookup = {
            "models/ships/wings/wing_a.scene.mbin": sub_scene,
        }

        root = _node("ProcRoot", "MODEL", children=[
            _ref_node("_WINGS_A", "MODELS/SHIPS/WINGS/WING_A.SCENE.MBIN"),
        ])

        resolved = resolve(root, scene_lookup)
        # The REFERENCE node should now have children from the sub-scene
        wings = resolved.children[0]
        assert wings.name == "_WINGS_A"
        assert wings.node_type == "REFERENCE"
        assert len(wings.children) > 0

    def test_resolved_reference_contains_geometry(self):
        resolve = _import_resolve_references()
        assert resolve is not None

        sub_scene = _node(
            "WingRoot", "MODEL",
            children=[_geo_node("WingMesh", "MODELS/WINGS/GEO.MBIN")],
        )
        scene_lookup = {"models/ships/wings/wing_a.scene.mbin": sub_scene}

        root = _node("ProcRoot", "MODEL", children=[
            _ref_node("_WINGS_A", "MODELS/SHIPS/WINGS/WING_A.SCENE.MBIN"),
        ])

        resolved = resolve(root, scene_lookup)
        # Walk into resolved reference to find geometry
        geo_refs = _collect_geometry_refs(resolved)
        assert "MODELS/WINGS/GEO.MBIN" in geo_refs

    def test_nested_references(self):
        """A → B → C: reference inside a sub-scene that itself has a reference."""
        resolve = _import_resolve_references()
        assert resolve is not None

        leaf_scene = _node("LeafRoot", "MODEL", children=[
            _geo_node("LeafMesh", "MODELS/LEAF/GEO.MBIN"),
        ])
        mid_scene = _node("MidRoot", "MODEL", children=[
            _ref_node("_LEAF_REF", "MODELS/LEAF/LEAF.SCENE.MBIN"),
        ])

        scene_lookup = {
            "models/mid/mid.scene.mbin": mid_scene,
            "models/leaf/leaf.scene.mbin": leaf_scene,
        }

        root = _node("Root", "MODEL", children=[
            _ref_node("_MID_REF", "MODELS/MID/MID.SCENE.MBIN"),
        ])

        resolved = resolve(root, scene_lookup)
        geo_refs = _collect_geometry_refs(resolved)
        assert "MODELS/LEAF/GEO.MBIN" in geo_refs

    def test_cycle_detection(self):
        """A → B → A: circular reference should not infinite-loop."""
        resolve = _import_resolve_references()
        assert resolve is not None

        scene_a = _node("SceneA", "MODEL", children=[
            _ref_node("_REF_B", "MODELS/B.SCENE.MBIN"),
        ])
        scene_b = _node("SceneB", "MODEL", children=[
            _ref_node("_REF_A", "MODELS/A.SCENE.MBIN"),
        ])

        scene_lookup = {
            "models/a.scene.mbin": scene_a,
            "models/b.scene.mbin": scene_b,
        }

        root = _node("Root", "MODEL", children=[
            _ref_node("_REF_A", "MODELS/A.SCENE.MBIN"),
        ])

        # Should complete without infinite recursion
        resolved = resolve(root, scene_lookup)
        assert resolved is not None

    def test_missing_reference_graceful(self):
        """Reference to non-existent scene keeps node as empty REFERENCE."""
        resolve = _import_resolve_references()
        assert resolve is not None

        root = _node("Root", "MODEL", children=[
            _ref_node("_MISSING", "MODELS/DOES_NOT_EXIST.SCENE.MBIN"),
        ])

        resolved = resolve(root, scene_lookup={})
        missing = resolved.children[0]
        assert missing.name == "_MISSING"
        assert missing.node_type == "REFERENCE"
        assert missing.children == ()

    def test_non_reference_nodes_unchanged(self):
        """Nodes without scene_ref should pass through unmodified."""
        resolve = _import_resolve_references()
        assert resolve is not None

        root = _node("Root", "MODEL", children=[
            _geo_node("Hull", "MODELS/HULL/GEO.MBIN"),
        ])

        resolved = resolve(root, scene_lookup={})
        assert resolved.children[0].name == "Hull"
        assert resolved.children[0].geometry_ref == "MODELS/HULL/GEO.MBIN"

    def test_reference_node_preserves_type(self):
        """Resolved REFERENCE nodes keep node_type='REFERENCE' for filtering."""
        resolve = _import_resolve_references()
        assert resolve is not None

        sub_scene = _node("WingRoot", "MODEL", children=[
            _geo_node("WingMesh", "MODELS/WINGS/GEO.MBIN"),
        ])
        scene_lookup = {"models/ships/wings/wing_a.scene.mbin": sub_scene}

        root = _node("Root", "MODEL", children=[
            _ref_node("_WINGS_A", "MODELS/SHIPS/WINGS/WING_A.SCENE.MBIN"),
        ])

        resolved = resolve(root, scene_lookup)
        assert resolved.children[0].node_type == "REFERENCE"


# ---------------------------------------------------------------------------
# R-DP02-04: Descriptor filtering on REFERENCE boundaries
# ---------------------------------------------------------------------------

class TestFilterSceneGeometry:
    """Filtering collects geometry refs, skipping non-selected REFERENCE branches."""

    def test_all_parts_when_no_filter(self):
        fn = _import_filter_geometry()
        assert fn is not None, "filter_scene_geometry not implemented"

        # Build a resolved tree with two reference branches
        root = _node("Root", "MODEL", children=[
            SceneNode("_WINGS_A", "REFERENCE", Transform.identity(), "", "", "",
                      (_geo_node("WingMesh", "MODELS/WINGS/GEO.MBIN"),)),
            SceneNode("_COCKPIT_1", "REFERENCE", Transform.identity(), "", "", "",
                      (_geo_node("CockpitMesh", "MODELS/COCKPIT/GEO.MBIN"),)),
        ])

        result = fn(root, active_nodes=None)
        geo_refs = [ref for ref, _ in result]
        assert "MODELS/WINGS/GEO.MBIN" in geo_refs
        assert "MODELS/COCKPIT/GEO.MBIN" in geo_refs

    def test_filter_includes_selected_reference(self):
        fn = _import_filter_geometry()
        assert fn is not None

        root = _node("Root", "MODEL", children=[
            SceneNode("_WINGS_A", "REFERENCE", Transform.identity(), "", "", "",
                      (_geo_node("WingMesh", "MODELS/WINGS/GEO.MBIN"),)),
            SceneNode("_COCKPIT_1", "REFERENCE", Transform.identity(), "", "", "",
                      (_geo_node("CockpitMesh", "MODELS/COCKPIT/GEO.MBIN"),)),
        ])

        result = fn(root, active_nodes=frozenset({"_WINGS_A"}))
        geo_refs = [ref for ref, _ in result]
        assert "MODELS/WINGS/GEO.MBIN" in geo_refs
        assert "MODELS/COCKPIT/GEO.MBIN" not in geo_refs

    def test_filter_excludes_non_selected_reference(self):
        fn = _import_filter_geometry()
        assert fn is not None

        root = _node("Root", "MODEL", children=[
            SceneNode("_WINGS_A", "REFERENCE", Transform.identity(), "", "", "",
                      (_geo_node("WingMesh", "MODELS/WINGS/GEO.MBIN"),)),
            SceneNode("_WINGS_B", "REFERENCE", Transform.identity(), "", "", "",
                      (_geo_node("WingMeshB", "MODELS/WINGS_B/GEO.MBIN"),)),
        ])

        result = fn(root, active_nodes=frozenset({"_WINGS_B"}))
        geo_refs = [ref for ref, _ in result]
        assert "MODELS/WINGS/GEO.MBIN" not in geo_refs
        assert "MODELS/WINGS_B/GEO.MBIN" in geo_refs

    def test_root_mega_geometry_skipped_when_references_resolved(self):
        """Root geometry is skipped when REFERENCE children have been resolved.

        In NMS _PROC scenes, the root carries a mega-geometry with ALL parts
        as sub-meshes. When references are resolved, per-part geometry replaces
        it. The mega-geometry must be skipped to avoid rendering all parts.
        """
        fn = _import_filter_geometry()
        assert fn is not None

        root = _node("Root", "MODEL", geometry_ref="MODELS/ROOT/MEGA_GEO.MBIN", children=[
            SceneNode("_WINGS_A", "REFERENCE", Transform.identity(), "", "", "",
                      (_geo_node("WingMesh", "MODELS/WINGS/GEO.MBIN"),)),
        ])

        result = fn(root, active_nodes=frozenset({"_WINGS_A"}))
        geo_refs = [ref for ref, _ in result]
        assert "MODELS/ROOT/MEGA_GEO.MBIN" not in geo_refs
        assert "MODELS/WINGS/GEO.MBIN" in geo_refs

    def test_root_geometry_kept_when_references_unresolved(self):
        """Root geometry is kept when REFERENCE children are empty (unresolved)."""
        fn = _import_filter_geometry()
        assert fn is not None

        root = _node("Root", "MODEL", geometry_ref="MODELS/ROOT/GEO.MBIN", children=[
            SceneNode("_WINGS_A", "REFERENCE", Transform.identity(), "", "", "", ()),
        ])

        result = fn(root, active_nodes=None)
        geo_refs = [ref for ref, _ in result]
        assert "MODELS/ROOT/GEO.MBIN" in geo_refs

    def test_parent_geometry_kept_without_descriptor_filter(self):
        """Parent geometry is kept when active_nodes=None, even with resolved refs.

        Non-procedural scenes (frigates, freighters) have no descriptor filter.
        Their root/parent geometry must NOT be skipped, even when REFERENCE
        children have been resolved (have non-empty children).
        """
        fn = _import_filter_geometry()
        assert fn is not None

        root = _node("Root", "MODEL", geometry_ref="MODELS/FRIGATE/GEO.MBIN", children=[
            SceneNode("_HULL_A", "REFERENCE", Transform.identity(), "", "", "",
                      (_geo_node("HullMesh", "MODELS/HULL/GEO.MBIN"),)),
        ])

        result = fn(root, active_nodes=None)
        geo_refs = [ref for ref, _ in result]
        assert "MODELS/FRIGATE/GEO.MBIN" in geo_refs
        assert "MODELS/HULL/GEO.MBIN" in geo_refs

    def test_non_reference_geometry_included(self):
        """Geometry on nodes without REFERENCE children is always collected."""
        fn = _import_filter_geometry()
        assert fn is not None

        root = _node("Root", "MODEL", children=[
            _geo_node("Hull", "MODELS/HULL/GEO.MBIN"),
        ])

        result = fn(root, active_nodes=None)
        geo_refs = [ref for ref, _ in result]
        assert "MODELS/HULL/GEO.MBIN" in geo_refs

    def test_collision_nodes_excluded(self):
        fn = _import_filter_geometry()
        assert fn is not None

        root = _node("Root", "MODEL", children=[
            _node("CollisionNode", "COLLISION", geometry_ref="MODELS/COL/GEO.MBIN"),
            _geo_node("Hull", "MODELS/HULL/GEO.MBIN"),
        ])

        result = fn(root, active_nodes=None)
        geo_refs = [ref for ref, _ in result]
        assert "MODELS/COL/GEO.MBIN" not in geo_refs
        assert "MODELS/HULL/GEO.MBIN" in geo_refs

    def test_returns_transform_tuples(self):
        fn = _import_filter_geometry()
        assert fn is not None

        root = _node("Root", "MODEL", children=[
            _geo_node("Hull", "MODELS/HULL/GEO.MBIN"),
        ])

        result = fn(root, active_nodes=None)
        assert len(result) == 1
        ref, transform = result[0]
        assert ref == "MODELS/HULL/GEO.MBIN"
        assert isinstance(transform, Transform)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _collect_geometry_refs(node: SceneNode) -> list:
    """Recursively collect all geometry_ref values from a scene tree."""
    refs = []
    if node.geometry_ref:
        refs.append(node.geometry_ref)
    for child in node.children:
        refs.extend(_collect_geometry_refs(child))
    return refs
