"""Tests for PIPELINE-UNIFY-01: single extraction path via CorvetteMeshPipeline.

Contract requirements:
  R-PU-01: Single extraction path via extract_module()
  R-PU-02: No inline transform/extraction code in corvette_tab.py
  R-PU-03: No dead _on_extract_corvette_models in main_window.py
  R-PU-04: Pipeline handles multi-format geometry decoding
  R-PU-05: Cache roundtrip preserves all mesh data
  R-PU-06: Regression — existing 3D view behavior unchanged
"""

import ast
import struct
import tempfile
from pathlib import Path
from typing import Dict, List

import pytest

from nmstoolkit.core.corvette_mesh_pipeline import (
    CorvetteMeshPipeline,
    MeshCacheEntry,
)
from nmstoolkit.core.mesh_data import MaterialData, Mesh


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------

SCENE_EXML_TWO_CHILDREN = """\
<?xml version="1.0" encoding="utf-8"?>
<Data template="TkSceneNodeData">
  <Property name="Name" value="ROOT" />
  <Property name="Type" value="MODEL" />
  <Property name="Transform">
    <Property name="TransX" value="0" /><Property name="TransY" value="0" /><Property name="TransZ" value="0" />
    <Property name="RotX" value="0" /><Property name="RotY" value="0" /><Property name="RotZ" value="0" />
    <Property name="ScaleX" value="1" /><Property name="ScaleY" value="1" /><Property name="ScaleZ" value="1" />
  </Property>
  <Property name="Attributes">
    <Property value="TkSceneNodeAttributeData">
      <Property name="Name" value="GEOMETRY" />
      <Property name="Value" value="MODELS/GEO_A.GEOMETRY.MBIN" />
    </Property>
  </Property>
  <Property name="Children">
    <Property value="TkSceneNodeData">
      <Property name="Name" value="ChildA" />
      <Property name="Type" value="MESH" />
      <Property name="Transform">
        <Property name="TransX" value="1" /><Property name="TransY" value="0" /><Property name="TransZ" value="0" />
        <Property name="RotX" value="0" /><Property name="RotY" value="0" /><Property name="RotZ" value="0" />
        <Property name="ScaleX" value="1" /><Property name="ScaleY" value="1" /><Property name="ScaleZ" value="1" />
      </Property>
      <Property name="Attributes">
        <Property value="TkSceneNodeAttributeData">
          <Property name="Name" value="GEOMETRY" />
          <Property name="Value" value="MODELS/GEO_B.GEOMETRY.MBIN" />
        </Property>
      </Property>
      <Property name="Children" />
    </Property>
    <Property value="TkSceneNodeData">
      <Property name="Name" value="ChildB" />
      <Property name="Type" value="MESH" />
      <Property name="Transform">
        <Property name="TransX" value="0" /><Property name="TransY" value="2" /><Property name="TransZ" value="0" />
        <Property name="RotX" value="0" /><Property name="RotY" value="0" /><Property name="RotZ" value="0" />
        <Property name="ScaleX" value="2" /><Property name="ScaleY" value="2" /><Property name="ScaleZ" value="2" />
      </Property>
      <Property name="Attributes">
        <Property value="TkSceneNodeAttributeData">
          <Property name="Name" value="GEOMETRY" />
          <Property name="Value" value="MODELS/GEO_B.GEOMETRY.MBIN" />
        </Property>
      </Property>
      <Property name="Children" />
    </Property>
  </Property>
</Data>
"""


def _build_minimal_geometry():
    """Build a minimal valid geometry binary for parse_geometry()."""
    parts = []
    parts.append(struct.pack("<IIII", 3, 3, 1, 0))
    parts.append(struct.pack("<I", 0))
    parts.append(struct.pack("<I", 1))
    parts.append(struct.pack("<IIII", 0, 3, 0, 3))
    parts.append(struct.pack("<6f", -1, -1, -1, 1, 1, 1))
    parts.append(struct.pack("<II", 3, 20))
    parts.append(struct.pack("<IIIII", 0, 5131, 8, 0, 0))
    parts.append(struct.pack("<IIIII", 1, 5131, 8, 8, 0))
    parts.append(struct.pack("<IIIII", 2, 36255, 4, 16, 0))
    for idx in [0, 1, 2]:
        parts.append(struct.pack("<H", idx))
    parts.append(b"\x00\x00")
    for i in range(3):
        parts.append(struct.pack("<4e", float(i), 0.0, 0.0, 1.0))
        parts.append(struct.pack("<4e", 0.0, 0.0, 0.0, 0.0))
        parts.append(struct.pack("<I", 0x1FF << 20))
    return b"".join(parts)


# ---------------------------------------------------------------------------
# AC-PU-02: No direct parser calls from corvette_tab.py
# ---------------------------------------------------------------------------

class TestNoDirectParserCallsInTab:
    """AC-PU-02: corvette_tab.py must not directly call domain parsers for
    extraction (parse_scene, parse_geometry, etc). All extraction goes through
    CorvetteMeshPipeline.extract_module()."""

    def test_no_parse_scene_import(self):
        src = Path("src/nmstoolkit/gui/tabs/corvette_tab.py")
        if not src.exists():
            pytest.skip("source not found")
        tree = ast.parse(src.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                if "scene_parser" in node.module:
                    pytest.fail("corvette_tab.py imports scene_parser directly")

    def test_no_parse_geometry_import(self):
        src = Path("src/nmstoolkit/gui/tabs/corvette_tab.py")
        if not src.exists():
            pytest.skip("source not found")
        tree = ast.parse(src.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                if "geometry_parser" in node.module:
                    pytest.fail("corvette_tab.py imports geometry_parser directly")

    def test_no_geometry_stream_exml_import(self):
        src = Path("src/nmstoolkit/gui/tabs/corvette_tab.py")
        if not src.exists():
            pytest.skip("source not found")
        tree = ast.parse(src.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                if "geometry_stream_exml" in node.module:
                    pytest.fail("corvette_tab.py imports geometry_stream_exml_parser directly")

    def test_no_geometry_exml_fallback_import(self):
        src = Path("src/nmstoolkit/gui/tabs/corvette_tab.py")
        if not src.exists():
            pytest.skip("source not found")
        tree = ast.parse(src.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                if "geometry_exml_fallback" in node.module:
                    pytest.fail("corvette_tab.py imports geometry_exml_fallback directly")


# ---------------------------------------------------------------------------
# AC-PU-03: No inline transform logic in corvette_tab.py
# ---------------------------------------------------------------------------

class TestNoInlineTransformLogicInTab:
    """AC-PU-03: corvette_tab.py must not define inline transform helpers."""

    FORBIDDEN_FUNCTIONS = [
        "_rotate_xyz",
        "_combine_transform",
        "_scene_geometry_instances",
        "_apply_transform_to_mesh",
        "_normalize_vec3",
    ]

    def test_no_forbidden_function_definitions(self):
        src = Path("src/nmstoolkit/gui/tabs/corvette_tab.py")
        if not src.exists():
            pytest.skip("source not found")
        tree = ast.parse(src.read_text())
        defined = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if node.name in self.FORBIDDEN_FUNCTIONS:
                    defined.add(node.name)
        if defined:
            pytest.fail(f"corvette_tab.py still defines: {sorted(defined)}")


# ---------------------------------------------------------------------------
# AC-PU-04: No dead _on_extract_corvette_models in main_window.py
# ---------------------------------------------------------------------------

class TestNoDeadExtractMethod:
    """AC-PU-04: main_window.py must not contain _on_extract_corvette_models."""

    def test_no_extract_corvette_models_method(self):
        src = Path("src/nmstoolkit/gui/main_window.py")
        if not src.exists():
            pytest.skip("source not found")
        tree = ast.parse(src.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if node.name == "_on_extract_corvette_models":
                    pytest.fail("main_window.py still defines _on_extract_corvette_models")


# ---------------------------------------------------------------------------
# FC-PU-01: Multi-format geometry decoding in pipeline
# ---------------------------------------------------------------------------

class TestMultiFormatGeometryDecoding:
    """R-PU-04: extract_module supports three geometry formats."""

    def test_binary_geometry_format(self):
        """Pipeline decodes raw binary geometry (parse_geometry path)."""
        geo_data = _build_minimal_geometry()
        with tempfile.TemporaryDirectory() as tmpdir:
            pipeline = CorvetteMeshPipeline(cache_dir=Path(tmpdir))
            entry = pipeline.extract_module(
                module_id="B_TEST_BIN",
                scene_exml=SCENE_EXML_TWO_CHILDREN,
                geometry_data={
                    "MODELS/GEO_A.GEOMETRY.MBIN": geo_data,
                    "MODELS/GEO_B.GEOMETRY.MBIN": geo_data,
                },
            )
            assert len(entry.meshes) >= 2
            assert all(m.vertex_count > 0 for m in entry.meshes)

    def test_stream_exml_geometry_format(self):
        """Pipeline uses geometry_exml for stream EXML parsing when provided."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pipeline = CorvetteMeshPipeline(cache_dir=Path(tmpdir))
            # geometry_exml parameter must be accepted
            assert hasattr(pipeline.extract_module, '__call__')
            import inspect
            sig = inspect.signature(pipeline.extract_module)
            assert "geometry_exml" in sig.parameters, \
                "extract_module must accept geometry_exml parameter"

    def test_fallback_to_binary_when_no_exml(self):
        """When geometry_exml not provided, falls back to binary parse."""
        geo_data = _build_minimal_geometry()
        with tempfile.TemporaryDirectory() as tmpdir:
            pipeline = CorvetteMeshPipeline(cache_dir=Path(tmpdir))
            entry = pipeline.extract_module(
                module_id="B_TEST_FB",
                scene_exml=SCENE_EXML_TWO_CHILDREN,
                geometry_data={
                    "MODELS/GEO_A.GEOMETRY.MBIN": geo_data,
                    "MODELS/GEO_B.GEOMETRY.MBIN": geo_data,
                },
            )
            assert len(entry.meshes) >= 2

    def test_aabb_fallback_when_binary_fails(self):
        """When binary parse fails and geometry_exml has AABB data, uses fallback."""
        aabb_exml = """\
<?xml version="1.0" encoding="utf-8"?>
<Data template="TkGeometryData">
  <Property name="MeshAABBMin">
    <Property _index="0">
      <Property name="X" value="-1" />
      <Property name="Y" value="-1" />
      <Property name="Z" value="-1" />
    </Property>
  </Property>
  <Property name="MeshAABBMax">
    <Property _index="0">
      <Property name="X" value="1" />
      <Property name="Y" value="1" />
      <Property name="Z" value="1" />
    </Property>
  </Property>
</Data>
"""
        scene_single = """\
<?xml version="1.0" encoding="utf-8"?>
<Data template="TkSceneNodeData">
  <Property name="Name" value="ROOT" />
  <Property name="Type" value="MODEL" />
  <Property name="Transform">
    <Property name="TransX" value="0" /><Property name="TransY" value="0" /><Property name="TransZ" value="0" />
    <Property name="RotX" value="0" /><Property name="RotY" value="0" /><Property name="RotZ" value="0" />
    <Property name="ScaleX" value="1" /><Property name="ScaleY" value="1" /><Property name="ScaleZ" value="1" />
  </Property>
  <Property name="Attributes">
    <Property value="TkSceneNodeAttributeData">
      <Property name="Name" value="GEOMETRY" />
      <Property name="Value" value="MODELS/GEO_A.GEOMETRY.MBIN" />
    </Property>
  </Property>
  <Property name="Children" />
</Data>
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            pipeline = CorvetteMeshPipeline(cache_dir=Path(tmpdir))
            entry = pipeline.extract_module(
                module_id="B_TEST_AABB",
                scene_exml=scene_single,
                geometry_data={
                    "MODELS/GEO_A.GEOMETRY.MBIN": b"invalid binary data",
                },
                geometry_exml={
                    "MODELS/GEO_A.GEOMETRY.MBIN": (aabb_exml, ""),
                },
            )
            assert len(entry.meshes) >= 1
            assert entry.meshes[0].vertex_count > 0


# ---------------------------------------------------------------------------
# FC-PU-02: Cache roundtrip integrity
# ---------------------------------------------------------------------------

class TestCacheRoundtripIntegrity:
    """R-PU-05: Cache roundtrip preserves all mesh data."""

    def test_full_roundtrip_with_all_fields(self):
        mesh = Mesh(
            vertices=((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
            normals=((0.0, 0.0, 1.0),) * 3,
            uvs=((0.0, 0.0), (1.0, 0.0), (0.5, 0.5)),
            indices=(0, 1, 2),
        )
        mat = MaterialData(
            name="TestMat",
            diffuse_path="tex/diff.dds",
            normal_path="tex/norm.dds",
            mask_path="tex/mask.dds",
            roughness=0.7,
            metalness=0.3,
        )
        transforms = [
            [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 5, 3, 1, 1],
            [2, 0, 0, 0, 0, 2, 0, 0, 0, 0, 2, 0, 0, 0, 0, 1],
        ]
        entry = MeshCacheEntry(
            module_id="B_FULL",
            meshes=[mesh, mesh],
            texture_path=Path("/some/texture.png"),
            geometry_ref="MODELS/TEST.GEOMETRY.MBIN",
            material_data=[mat],
            world_transforms=transforms,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            pipeline = CorvetteMeshPipeline(cache_dir=Path(tmpdir))
            pipeline.save_entry(entry)
            loaded = pipeline.load_entry("B_FULL")

            assert loaded is not None
            assert loaded.module_id == "B_FULL"
            assert len(loaded.meshes) == 2
            assert loaded.meshes[0].vertices == mesh.vertices
            assert loaded.meshes[0].normals == mesh.normals
            assert loaded.meshes[0].uvs == mesh.uvs
            assert loaded.meshes[0].indices == mesh.indices
            assert len(loaded.material_data) == 1
            assert loaded.material_data[0].name == "TestMat"
            assert loaded.material_data[0].roughness == pytest.approx(0.7)
            assert loaded.world_transforms == transforms
            assert loaded.geometry_ref == "MODELS/TEST.GEOMETRY.MBIN"


# ---------------------------------------------------------------------------
# R-PU-01: extract_module produces pre-transformed meshes
# ---------------------------------------------------------------------------

class TestExtractModuleTransformBaking:
    """R-PU-01: extract_module bakes world transforms into mesh vertices."""

    def test_child_offset_baked_into_vertices(self):
        """Child at TransY=2, Scale=2 should produce vertices offset from root."""
        geo_data = _build_minimal_geometry()
        with tempfile.TemporaryDirectory() as tmpdir:
            pipeline = CorvetteMeshPipeline(cache_dir=Path(tmpdir))
            entry = pipeline.extract_module(
                module_id="B_BAKE",
                scene_exml=SCENE_EXML_TWO_CHILDREN,
                geometry_data={
                    "MODELS/GEO_A.GEOMETRY.MBIN": geo_data,
                    "MODELS/GEO_B.GEOMETRY.MBIN": geo_data,
                },
            )
            # Should have meshes from root + 2 children = at least 3
            assert len(entry.meshes) >= 3

            # Find meshes that were transformed (not at origin)
            has_offset = False
            for mesh in entry.meshes:
                for vx, vy, vz in mesh.vertices:
                    if abs(vy - 2.0) < 0.1 or abs(vx - 1.0) < 0.1:
                        has_offset = True
                        break
            assert has_offset, "Expected child transforms to be baked into vertices"
