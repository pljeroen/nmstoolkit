"""Tests for material_parser — MATERIAL.MBIN EXML to MaterialData.

Contract: RENDER-FIDELITY-01, R-RF-03
"""

import pytest

from nmstoolkit.core.material_parser import parse_material
from nmstoolkit.core.mesh_data import MaterialData


# ---------------------------------------------------------------------------
# Sample EXML fragments
# ---------------------------------------------------------------------------

MATERIAL_WITH_DIFFUSE = """\
<?xml version="1.0" encoding="utf-8"?>
<Data template="TkMaterialData">
  <Property name="Name" value="COK_A_MAT" />
  <Property name="Class" value="Opaque" />
  <Property name="Shader" value="SHADERS/UBERSHADER.SHADER.BIN" />
  <Property name="Flags">
    <Property value="_F01_DIFFUSEMAP" />
    <Property value="_F03_NORMALMAP" />
  </Property>
  <Property name="Samplers">
    <Property value="TkMaterialSampler">
      <Property name="Name" value="gDiffuseMap" />
      <Property name="Map" value="TEXTURES/COMMON/SPACECRAFT/BIGGS/COK_A.DDS" />
    </Property>
    <Property value="TkMaterialSampler">
      <Property name="Name" value="gNormalMap" />
      <Property name="Map" value="TEXTURES/COMMON/SPACECRAFT/BIGGS/COK_A.NORMAL.DDS" />
    </Property>
    <Property value="TkMaterialSampler">
      <Property name="Name" value="gMaskMap" />
      <Property name="Map" value="TEXTURES/COMMON/SPACECRAFT/BIGGS/COK_A.MASKS.DDS" />
    </Property>
  </Property>
  <Property name="Uniforms">
    <Property value="TkMaterialUniform">
      <Property name="Name" value="gMaterialColourVec4" />
      <Property name="Values">
        <Property name="t" value="1" />
        <Property name="x" value="0.8" />
        <Property name="y" value="0.8" />
        <Property name="z" value="0.8" />
      </Property>
    </Property>
    <Property value="TkMaterialUniform">
      <Property name="Name" value="gMaterialParamsVec4" />
      <Property name="Values">
        <Property name="t" value="0" />
        <Property name="x" value="0.5" />
        <Property name="y" value="0" />
        <Property name="z" value="0.3" />
      </Property>
    </Property>
  </Property>
</Data>
"""

MATERIAL_DIFFUSE_ONLY = """\
<?xml version="1.0" encoding="utf-8"?>
<Data template="TkMaterialData">
  <Property name="Name" value="SIMPLE_MAT" />
  <Property name="Class" value="Opaque" />
  <Property name="Shader" value="SHADERS/UBERSHADER.SHADER.BIN" />
  <Property name="Flags">
    <Property value="_F01_DIFFUSEMAP" />
  </Property>
  <Property name="Samplers">
    <Property value="TkMaterialSampler">
      <Property name="Name" value="gDiffuseMap" />
      <Property name="Map" value="TEXTURES/SHIPS/HULL.DDS" />
    </Property>
  </Property>
  <Property name="Uniforms" />
</Data>
"""

MATERIAL_EMPTY_SAMPLERS = """\
<?xml version="1.0" encoding="utf-8"?>
<Data template="TkMaterialData">
  <Property name="Name" value="EMPTY_MAT" />
  <Property name="Class" value="Opaque" />
  <Property name="Shader" value="SHADERS/UBERSHADER.SHADER.BIN" />
  <Property name="Flags" />
  <Property name="Samplers" />
  <Property name="Uniforms" />
</Data>
"""

MATERIAL_NO_SAMPLERS = """\
<?xml version="1.0" encoding="utf-8"?>
<Data template="TkMaterialData">
  <Property name="Name" value="BARE_MAT" />
  <Property name="Class" value="Opaque" />
  <Property name="Shader" value="SHADERS/UBERSHADER.SHADER.BIN" />
</Data>
"""


class TestParseMaterialDiffuse:
    """R-RF-03 / TC-03: Material parser extracts diffuse path."""

    def test_diffuse_path_extracted(self):
        mat = parse_material(MATERIAL_WITH_DIFFUSE)
        assert mat.diffuse_path == "TEXTURES/COMMON/SPACECRAFT/BIGGS/COK_A.DDS"

    def test_normal_path_extracted(self):
        mat = parse_material(MATERIAL_WITH_DIFFUSE)
        assert mat.normal_path == "TEXTURES/COMMON/SPACECRAFT/BIGGS/COK_A.NORMAL.DDS"

    def test_mask_path_extracted(self):
        mat = parse_material(MATERIAL_WITH_DIFFUSE)
        assert mat.mask_path == "TEXTURES/COMMON/SPACECRAFT/BIGGS/COK_A.MASKS.DDS"

    def test_material_name(self):
        mat = parse_material(MATERIAL_WITH_DIFFUSE)
        assert mat.name == "COK_A_MAT"


class TestParseMaterialUniforms:
    """R-RF-05: Material properties for Blinn-Phong lighting."""

    def test_roughness_from_params(self):
        mat = parse_material(MATERIAL_WITH_DIFFUSE)
        assert mat.roughness == pytest.approx(0.5)

    def test_metalness_from_params(self):
        mat = parse_material(MATERIAL_WITH_DIFFUSE)
        assert mat.metalness == pytest.approx(0.3)


class TestParseMaterialDiffuseOnly:
    def test_diffuse_path(self):
        mat = parse_material(MATERIAL_DIFFUSE_ONLY)
        assert mat.diffuse_path == "TEXTURES/SHIPS/HULL.DDS"

    def test_normal_path_empty(self):
        mat = parse_material(MATERIAL_DIFFUSE_ONLY)
        assert mat.normal_path == ""

    def test_mask_path_empty(self):
        mat = parse_material(MATERIAL_DIFFUSE_ONLY)
        assert mat.mask_path == ""

    def test_defaults_for_uniforms(self):
        mat = parse_material(MATERIAL_DIFFUSE_ONLY)
        assert mat.roughness == pytest.approx(0.5)
        assert mat.metalness == pytest.approx(0.0)


class TestParseMaterialEmpty:
    def test_empty_samplers(self):
        mat = parse_material(MATERIAL_EMPTY_SAMPLERS)
        assert mat.diffuse_path == ""
        assert mat.normal_path == ""

    def test_no_samplers_tag(self):
        mat = parse_material(MATERIAL_NO_SAMPLERS)
        assert mat.diffuse_path == ""
        assert mat.normal_path == ""


class TestMaterialDataImmutability:
    def test_frozen(self):
        mat = parse_material(MATERIAL_WITH_DIFFUSE)
        with pytest.raises(AttributeError):
            mat.diffuse_path = "CHANGED"

    def test_equality(self):
        mat1 = parse_material(MATERIAL_WITH_DIFFUSE)
        mat2 = parse_material(MATERIAL_WITH_DIFFUSE)
        assert mat1 == mat2
