"""Tests for corvette_mesh_pipeline full scene tree extraction.

Contract: RENDER-FIDELITY-01, R-RF-02, R-RF-03
Tests that extract_module walks the full scene tree and collects
all geometry + material references, not just root.
"""

import json
import struct
import tempfile
from pathlib import Path

import pytest

from nmstoolkit.core.corvette_mesh_pipeline import (
    CorvetteMeshPipeline,
    MeshCacheEntry,
)
from nmstoolkit.core.mesh_data import MaterialData, Mesh


SCENE_WITH_CHILDREN = """\
<?xml version="1.0" encoding="utf-8"?>
<Data template="TkSceneNodeData">
  <Property name="Name" value="MODULE" />
  <Property name="Type" value="MODEL" />
  <Property name="Transform">
    <Property name="TransX" value="0" /><Property name="TransY" value="0" /><Property name="TransZ" value="0" />
    <Property name="RotX" value="0" /><Property name="RotY" value="0" /><Property name="RotZ" value="0" />
    <Property name="ScaleX" value="1" /><Property name="ScaleY" value="1" /><Property name="ScaleZ" value="1" />
  </Property>
  <Property name="Attributes">
    <Property value="TkSceneNodeAttributeData">
      <Property name="Name" value="GEOMETRY" />
      <Property name="Value" value="MODELS/ROOT/GEOMETRY.MBIN" />
    </Property>
  </Property>
  <Property name="Children">
    <Property value="TkSceneNodeData">
      <Property name="Name" value="SubMesh" />
      <Property name="Type" value="MESH" />
      <Property name="Transform">
        <Property name="TransX" value="0" /><Property name="TransY" value="1" /><Property name="TransZ" value="0" />
        <Property name="RotX" value="0" /><Property name="RotY" value="0" /><Property name="RotZ" value="0" />
        <Property name="ScaleX" value="1" /><Property name="ScaleY" value="1" /><Property name="ScaleZ" value="1" />
      </Property>
      <Property name="Attributes">
        <Property value="TkSceneNodeAttributeData">
          <Property name="Name" value="GEOMETRY" />
          <Property name="Value" value="MODELS/CHILD/GEOMETRY.MBIN" />
        </Property>
        <Property value="TkSceneNodeAttributeData">
          <Property name="Name" value="MATERIAL" />
          <Property name="Value" value="MODELS/CHILD/MATERIAL.MBIN" />
        </Property>
      </Property>
      <Property name="Children" />
    </Property>
  </Property>
</Data>
"""


def _build_minimal_geometry():
    """Build a minimal valid geometry binary blob."""
    parts = []
    parts.append(struct.pack("<IIII", 3, 3, 1, 0))  # header
    parts.append(struct.pack("<I", 0))  # joints
    parts.append(struct.pack("<I", 1))  # 1 mesh range
    parts.append(struct.pack("<IIII", 0, 3, 0, 3))  # range
    parts.append(struct.pack("<6f", -1, -1, -1, 1, 1, 1))  # bbox
    parts.append(struct.pack("<II", 3, 20))  # layout: 3 elements, stride 20
    parts.append(struct.pack("<IIIII", 0, 5131, 8, 0, 0))  # position
    parts.append(struct.pack("<IIIII", 1, 5131, 8, 8, 0))  # uv
    parts.append(struct.pack("<IIIII", 2, 36255, 4, 16, 0))  # normal
    for idx in [0, 1, 2]:
        parts.append(struct.pack("<H", idx))
    parts.append(b"\x00\x00")
    for i in range(3):
        parts.append(struct.pack("<4e", float(i), 0.0, 0.0, 1.0))
        parts.append(struct.pack("<4e", 0.0, 0.0, 0.0, 0.0))
        parts.append(struct.pack("<I", 0x1FF << 20))  # normal +Z
    return b"".join(parts)


class TestPipelineSceneTreeWalk:
    """R-RF-02: Pipeline walks full scene tree."""

    def test_extracts_root_and_child_geometry(self):
        geo_data = _build_minimal_geometry()
        with tempfile.TemporaryDirectory() as tmpdir:
            pipeline = CorvetteMeshPipeline(cache_dir=Path(tmpdir))
            entry = pipeline.extract_module(
                module_id="B_COK_A",
                scene_exml=SCENE_WITH_CHILDREN,
                geometry_data={
                    "MODELS/ROOT/GEOMETRY.MBIN": geo_data,
                    "MODELS/CHILD/GEOMETRY.MBIN": geo_data,
                },
            )
            # Should have meshes from both root and child
            assert len(entry.meshes) >= 2

    def test_preserves_child_transform_in_cache(self):
        geo_data = _build_minimal_geometry()
        with tempfile.TemporaryDirectory() as tmpdir:
            pipeline = CorvetteMeshPipeline(cache_dir=Path(tmpdir))
            entry = pipeline.extract_module(
                module_id="B_COK_A",
                scene_exml=SCENE_WITH_CHILDREN,
                geometry_data={
                    "MODELS/ROOT/GEOMETRY.MBIN": geo_data,
                    "MODELS/CHILD/GEOMETRY.MBIN": geo_data,
                },
            )
            # Entry should have world transforms for submeshes
            assert hasattr(entry, "world_transforms")
            assert len(entry.world_transforms) >= 2


class TestMaterialDataCacheRoundtrip:
    """TC-06: MaterialData round-trips through cache."""

    def test_material_data_survives_save_load(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pipeline = CorvetteMeshPipeline(cache_dir=Path(tmpdir))
            md = MaterialData(
                name="TEST",
                diffuse_path="a.dds",
                normal_path="b.dds",
                mask_path="c.dds",
                roughness=32.0,
                metalness=0.5,
            )
            entry = MeshCacheEntry(
                module_id="B_TEST",
                meshes=[Mesh.empty()],
                texture_path=None,
                geometry_ref="geo.mbin",
                material_data=[md],
                world_transforms=[[1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1]],
            )
            pipeline.save_entry(entry)
            loaded = pipeline.load_entry("B_TEST")
            assert loaded is not None
            assert len(loaded.material_data) == 1
            assert loaded.material_data[0].diffuse_path == "a.dds"
            assert loaded.material_data[0].roughness == pytest.approx(32.0)
            assert loaded.material_data[0].metalness == pytest.approx(0.5)
