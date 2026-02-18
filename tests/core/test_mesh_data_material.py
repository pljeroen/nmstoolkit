"""Tests for MaterialData domain model extension.

Contract: RENDER-FIDELITY-01, R-RF-03
"""

import pytest

from nmstoolkit.core.mesh_data import MaterialData


class TestMaterialData:
    def test_construction(self):
        md = MaterialData(
            name="TEST_MAT",
            diffuse_path="TEXTURES/DIFFUSE.DDS",
            normal_path="TEXTURES/NORMAL.DDS",
            mask_path="TEXTURES/MASKS.DDS",
            roughness=0.5,
            metalness=0.3,
        )
        assert md.name == "TEST_MAT"
        assert md.diffuse_path == "TEXTURES/DIFFUSE.DDS"
        assert md.normal_path == "TEXTURES/NORMAL.DDS"
        assert md.mask_path == "TEXTURES/MASKS.DDS"
        assert md.roughness == 0.5
        assert md.metalness == 0.3

    def test_frozen(self):
        md = MaterialData(
            name="M", diffuse_path="", normal_path="",
            mask_path="", roughness=0.5, metalness=0.0,
        )
        with pytest.raises(AttributeError):
            md.name = "CHANGED"

    def test_equality(self):
        args = dict(
            name="M", diffuse_path="a", normal_path="b",
            mask_path="c", roughness=0.5, metalness=0.3,
        )
        assert MaterialData(**args) == MaterialData(**args)

    def test_empty_factory(self):
        md = MaterialData.empty()
        assert md.name == ""
        assert md.diffuse_path == ""
        assert md.normal_path == ""
        assert md.mask_path == ""
        assert md.roughness == 0.5
        assert md.metalness == 0.0
