"""Tests for corvette_mesh_pipeline — mesh extraction and caching service.

Uses fake adapters (no real PAK/MBINCompiler needed).
"""

import json
import struct
import tempfile
from pathlib import Path
from typing import Dict, List, Optional
from unittest.mock import MagicMock

import pytest

from nmstoolkit.core.corvette_mesh_pipeline import (
    CorvetteMeshPipeline,
    MeshCacheEntry,
)
from nmstoolkit.core.mesh_data import Mesh


# ---------------------------------------------------------------------------
# Fake adapters for testing (satisfy Protocol structurally)
# ---------------------------------------------------------------------------

class FakeArchiveReader:
    """Fake GameArchiveReader that returns pre-loaded data."""

    def __init__(self, files: Dict[str, bytes] = None):
        self._files = files or {}

    def open(self, path) -> None:
        pass

    def close(self) -> None:
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def list_files(self) -> List[str]:
        return list(self._files.keys())

    def extract(
        self,
        paths: Optional[List[str]] = None,
        pattern: Optional[str] = None,
    ) -> Dict[str, bytes]:
        if paths is not None:
            return {p: self._files[p] for p in paths if p in self._files}
        return dict(self._files)


class FakeMbinConverter:
    """Fake MbinConverter that returns pre-loaded EXML."""

    def __init__(self, conversions: Dict[str, str] = None):
        self._conversions = conversions or {}

    def convert(self, mbin_data: bytes) -> str:
        # Return based on data hash for deterministic testing
        for key, val in self._conversions.items():
            return val
        return ""

    def convert_batch(self, mbin_files: Dict[str, bytes]) -> Dict[str, str]:
        return {k: self._conversions.get(k, "") for k in mbin_files}


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

SAMPLE_SCENE_EXML = """\
<?xml version="1.0" encoding="utf-8"?>
<Data template="TkSceneNodeData">
  <Property name="Name" value="B_COK_A" />
  <Property name="Type" value="MODEL" />
  <Property name="Transform">
    <Property name="TransX" value="0" /><Property name="TransY" value="0" /><Property name="TransZ" value="0" />
    <Property name="RotX" value="0" /><Property name="RotY" value="0" /><Property name="RotZ" value="0" />
    <Property name="ScaleX" value="1" /><Property name="ScaleY" value="1" /><Property name="ScaleZ" value="1" />
  </Property>
  <Property name="Attributes">
    <Property value="TkSceneNodeAttributeData">
      <Property name="Name" value="GEOMETRY" />
      <Property name="Value" value="MODELS/SHIPS/CORVETTE/PARTS/COK_A/GEOMETRY.MBIN" />
    </Property>
  </Property>
  <Property name="Children">
    <Property value="TkSceneNodeData">
      <Property name="Name" value="Hull" />
      <Property name="Type" value="MESH" />
      <Property name="Transform">
        <Property name="TransX" value="0" /><Property name="TransY" value="0" /><Property name="TransZ" value="0" />
        <Property name="RotX" value="0" /><Property name="RotY" value="0" /><Property name="RotZ" value="0" />
        <Property name="ScaleX" value="1" /><Property name="ScaleY" value="1" /><Property name="ScaleZ" value="1" />
      </Property>
      <Property name="Attributes">
        <Property value="TkSceneNodeAttributeData">
          <Property name="Name" value="MATERIAL" />
          <Property name="Value" value="MODELS/SHIPS/CORVETTE/PARTS/COK_A/MAT.MATERIAL.MBIN" />
        </Property>
      </Property>
      <Property name="Children" />
    </Property>
  </Property>
</Data>
"""


def _build_minimal_geometry():
    """Build a minimal valid geometry binary blob for testing."""
    vertices = [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)]
    normals = [(0.0, 0.0, 1.0)] * 3
    uvs = [(0.0, 0.0), (1.0, 0.0), (0.0, 1.0)]
    indices = [0, 1, 2]

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

    # Index buffer (3 u16, padded)
    for idx in indices:
        parts.append(struct.pack("<H", idx))
    parts.append(b"\x00\x00")  # pad to 4 bytes

    # Vertex data
    for i in range(3):
        vx, vy, vz = vertices[i]
        u, v = uvs[i]
        nx, ny, nz = normals[i]
        parts.append(struct.pack("<4e", vx, vy, vz, 1.0))
        parts.append(struct.pack("<4e", u, v, 0.0, 0.0))
        nx_int = int(round(nx * 511))
        ny_int = int(round(ny * 511))
        nz_int = int(round(nz * 511))
        packed = (nx_int & 0x3FF) | ((ny_int & 0x3FF) << 10) | ((nz_int & 0x3FF) << 20)
        parts.append(struct.pack("<I", packed))

    return b"".join(parts)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestMeshCacheEntry:
    def test_construction(self):
        entry = MeshCacheEntry(
            module_id="B_COK_A",
            meshes=[Mesh.empty()],
            texture_path=None,
            geometry_ref="MODELS/TEST/GEOMETRY.MBIN",
        )
        assert entry.module_id == "B_COK_A"
        assert len(entry.meshes) == 1

    def test_no_texture(self):
        entry = MeshCacheEntry(
            module_id="B_WNG_A",
            meshes=[],
            texture_path=None,
            geometry_ref="",
        )
        assert entry.texture_path is None


class TestPipelineCacheRoundtrip:
    def test_save_and_load_mesh_cache(self):
        """Mesh data saved to JSON can be loaded back."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir)
            pipeline = CorvetteMeshPipeline(cache_dir=cache_dir)

            mesh = Mesh(
                vertices=((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
                normals=((0.0, 0.0, 1.0),) * 3,
                uvs=((0.0, 0.0), (1.0, 0.0), (0.0, 1.0)),
                indices=(0, 1, 2),
            )
            entry = MeshCacheEntry(
                module_id="B_COK_A",
                meshes=[mesh],
                texture_path=None,
                geometry_ref="MODELS/TEST/GEOMETRY.MBIN",
            )
            pipeline.save_entry(entry)

            loaded = pipeline.load_entry("B_COK_A")
            assert loaded is not None
            assert loaded.module_id == "B_COK_A"
            assert len(loaded.meshes) == 1
            assert loaded.meshes[0].vertex_count == 3
            assert loaded.meshes[0].indices == (0, 1, 2)

    def test_load_missing_returns_none(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pipeline = CorvetteMeshPipeline(cache_dir=Path(tmpdir))
            assert pipeline.load_entry("NONEXISTENT") is None

    def test_list_cached_modules(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir)
            pipeline = CorvetteMeshPipeline(cache_dir=cache_dir)

            for mid in ["B_COK_A", "B_WNG_A"]:
                entry = MeshCacheEntry(mid, [Mesh.empty()], None, "")
                pipeline.save_entry(entry)

            cached = pipeline.list_cached()
            assert "B_COK_A" in cached
            assert "B_WNG_A" in cached


class TestPipelineExtraction:
    def test_extract_module_with_fake_adapters(self):
        """Full pipeline: fake PAK → fake MBIN convert → parse → cache."""
        geometry_data = _build_minimal_geometry()
        scene_path = "models/ships/corvette/parts/cok_a/entities/cok_a.scene.mbin"

        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir)

            pipeline = CorvetteMeshPipeline(cache_dir=cache_dir)
            entry = pipeline.extract_module(
                module_id="B_COK_A",
                scene_exml=SAMPLE_SCENE_EXML,
                geometry_data={
                    "MODELS/SHIPS/CORVETTE/PARTS/COK_A/GEOMETRY.MBIN": geometry_data,
                },
            )

            assert entry is not None
            assert entry.module_id == "B_COK_A"
            assert len(entry.meshes) >= 1
            assert entry.meshes[0].vertex_count == 3

    def test_extract_with_missing_geometry_returns_empty_meshes(self):
        """If geometry data is missing, meshes list is empty."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pipeline = CorvetteMeshPipeline(cache_dir=Path(tmpdir))
            entry = pipeline.extract_module(
                module_id="B_COK_A",
                scene_exml=SAMPLE_SCENE_EXML,
                geometry_data={},  # no geometry
            )
            assert entry is not None
            assert entry.meshes == []
