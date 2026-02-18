"""Parser for NMS MATERIAL.MBIN EXML into MaterialData.

Pure domain module — stdlib only (xml.etree.ElementTree).

MATERIAL EXML structure (TkMaterialData):
  <Data template="TkMaterialData">
    <Property name="Name" value="..." />
    <Property name="Samplers">
      <Property value="TkMaterialSampler">
        <Property name="Name" value="gDiffuseMap" />
        <Property name="Map" value="TEXTURES/.../DIFFUSE.DDS" />
      </Property>
      ...
    </Property>
    <Property name="Uniforms">
      <Property value="TkMaterialUniform">
        <Property name="Name" value="gMaterialParamsVec4" />
        <Property name="Values">
          <Property name="x" value="0.5" />  (roughness)
          <Property name="z" value="0.3" />  (metalness)
        </Property>
      </Property>
    </Property>
  </Data>
"""

from __future__ import annotations

from xml.etree.ElementTree import Element, fromstring

from nmstoolkit.core.mesh_data import MaterialData


def parse_material(source: str) -> MaterialData:
    """Parse MATERIAL EXML source into a MaterialData."""
    root = fromstring(source)

    name = _get_property_value(root, "Name") or ""
    samplers = _parse_samplers(root)
    roughness, metalness = _parse_material_params(root)

    return MaterialData(
        name=name,
        diffuse_path=samplers.get("gDiffuseMap", ""),
        normal_path=samplers.get("gNormalMap", ""),
        mask_path=samplers.get("gMaskMap", ""),
        roughness=roughness,
        metalness=metalness,
    )


def _get_property_value(parent: Element, name: str) -> str:
    """Get the value attribute of a named Property child."""
    prop = parent.find(f"Property[@name='{name}']")
    if prop is None:
        return ""
    return prop.get("value", "")


def _parse_samplers(root: Element) -> dict:
    """Extract sampler name → texture map path from Samplers array."""
    result = {}
    samplers_el = root.find("Property[@name='Samplers']")
    if samplers_el is None:
        return result

    for sampler in samplers_el:
        if sampler.tag != "Property":
            continue
        sampler_name = _get_property_value(sampler, "Name")
        sampler_map = _get_property_value(sampler, "Map")
        if sampler_name and sampler_map:
            result[sampler_name] = sampler_map

    return result


def _parse_material_params(root: Element) -> tuple:
    """Extract roughness and metalness from gMaterialParamsVec4 uniform.

    Returns (roughness, metalness) with defaults (0.5, 0.0).
    """
    roughness = 0.5
    metalness = 0.0

    uniforms_el = root.find("Property[@name='Uniforms']")
    if uniforms_el is None:
        return roughness, metalness

    for uniform in uniforms_el:
        if uniform.tag != "Property":
            continue
        uniform_name = _get_property_value(uniform, "Name")
        if uniform_name == "gMaterialParamsVec4":
            values_el = uniform.find("Property[@name='Values']")
            if values_el is not None:
                x_val = _get_property_value(values_el, "x")
                z_val = _get_property_value(values_el, "z")
                if x_val:
                    roughness = float(x_val)
                if z_val:
                    metalness = float(z_val)
            break

    return roughness, metalness
