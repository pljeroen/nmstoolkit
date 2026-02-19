"""Tests for mesh_data domain model — Mesh, Transform, SceneNode."""

import pytest

from nmstoolkit.core.mesh_data import Mesh, SceneNode, Transform


class TestTransform:
    def test_construction(self):
        t = Transform(
            position=(1.0, 2.0, 3.0),
            rotation=(45.0, 0.0, 90.0),
            scale=(1.0, 1.0, 1.0),
        )
        assert t.position == (1.0, 2.0, 3.0)
        assert t.rotation == (45.0, 0.0, 90.0)
        assert t.scale == (1.0, 1.0, 1.0)

    def test_immutability(self):
        t = Transform(
            position=(0.0, 0.0, 0.0),
            rotation=(0.0, 0.0, 0.0),
            scale=(1.0, 1.0, 1.0),
        )
        with pytest.raises(AttributeError):
            t.position = (1.0, 1.0, 1.0)

    def test_equality(self):
        t1 = Transform((0.0, 0.0, 0.0), (0.0, 0.0, 0.0), (1.0, 1.0, 1.0))
        t2 = Transform((0.0, 0.0, 0.0), (0.0, 0.0, 0.0), (1.0, 1.0, 1.0))
        assert t1 == t2

    def test_identity(self):
        t = Transform.identity()
        assert t.position == (0.0, 0.0, 0.0)
        assert t.rotation == (0.0, 0.0, 0.0)
        assert t.scale == (1.0, 1.0, 1.0)


class TestMesh:
    def test_construction(self):
        m = Mesh(
            vertices=((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
            normals=((0.0, 0.0, 1.0), (0.0, 0.0, 1.0), (0.0, 0.0, 1.0)),
            uvs=((0.0, 0.0), (1.0, 0.0), (0.0, 1.0)),
            indices=(0, 1, 2),
        )
        assert len(m.vertices) == 3
        assert len(m.normals) == 3
        assert len(m.uvs) == 3
        assert len(m.indices) == 3

    def test_immutability(self):
        m = Mesh(
            vertices=((0.0, 0.0, 0.0),),
            normals=((0.0, 0.0, 1.0),),
            uvs=((0.0, 0.0),),
            indices=(0,),
        )
        with pytest.raises(AttributeError):
            m.vertices = ()

    def test_equality(self):
        args = dict(
            vertices=((1.0, 2.0, 3.0),),
            normals=((0.0, 1.0, 0.0),),
            uvs=((0.5, 0.5),),
            indices=(0,),
        )
        assert Mesh(**args) == Mesh(**args)

    def test_empty_mesh(self):
        m = Mesh.empty()
        assert m.vertices == ()
        assert m.normals == ()
        assert m.uvs == ()
        assert m.indices == ()

    def test_vertex_count(self):
        m = Mesh(
            vertices=((0.0, 0.0, 0.0), (1.0, 0.0, 0.0)),
            normals=((0.0, 0.0, 1.0), (0.0, 0.0, 1.0)),
            uvs=((0.0, 0.0), (1.0, 0.0)),
            indices=(0, 1),
        )
        assert m.vertex_count == 2
        assert m.index_count == 2


class TestSceneNode:
    def test_construction(self):
        node = SceneNode(
            name="TestNode",
            node_type="MESH",
            transform=Transform.identity(),
            geometry_ref="MODELS/TEST/GEOMETRY.MBIN",
            material_ref="MODELS/TEST/MATERIAL.MBIN",
            scene_ref="",
            children=(),
        )
        assert node.name == "TestNode"
        assert node.node_type == "MESH"
        assert node.geometry_ref == "MODELS/TEST/GEOMETRY.MBIN"

    def test_scene_ref_field(self):
        node = SceneNode(
            name="WingsRef",
            node_type="REFERENCE",
            transform=Transform.identity(),
            geometry_ref="",
            material_ref="",
            scene_ref="MODELS/SHIPS/WINGS/WING_A.SCENE.MBIN",
            children=(),
        )
        assert node.scene_ref == "MODELS/SHIPS/WINGS/WING_A.SCENE.MBIN"

    def test_scene_ref_empty_by_default(self):
        node = SceneNode(
            name="Hull",
            node_type="MESH",
            transform=Transform.identity(),
            geometry_ref="geo.mbin",
            material_ref="mat.mbin",
            scene_ref="",
            children=(),
        )
        assert node.scene_ref == ""

    def test_immutability(self):
        node = SceneNode(
            name="Root",
            node_type="MODEL",
            transform=Transform.identity(),
            geometry_ref="",
            material_ref="",
            scene_ref="",
            children=(),
        )
        with pytest.raises(AttributeError):
            node.name = "Changed"

    def test_hierarchy(self):
        child = SceneNode(
            name="Child",
            node_type="MESH",
            transform=Transform.identity(),
            geometry_ref="geo.mbin",
            material_ref="mat.mbin",
            scene_ref="",
            children=(),
        )
        parent = SceneNode(
            name="Parent",
            node_type="MODEL",
            transform=Transform.identity(),
            geometry_ref="",
            material_ref="",
            scene_ref="",
            children=(child,),
        )
        assert len(parent.children) == 1
        assert parent.children[0].name == "Child"

    def test_deep_hierarchy(self):
        leaf = SceneNode("Leaf", "MESH", Transform.identity(), "", "", "", ())
        mid = SceneNode("Mid", "LOCATOR", Transform.identity(), "", "", "", (leaf,))
        root = SceneNode("Root", "MODEL", Transform.identity(), "", "", "", (mid,))
        assert root.children[0].children[0].name == "Leaf"

    def test_equality(self):
        args = dict(
            name="N",
            node_type="MESH",
            transform=Transform.identity(),
            geometry_ref="g",
            material_ref="m",
            scene_ref="",
            children=(),
        )
        assert SceneNode(**args) == SceneNode(**args)
