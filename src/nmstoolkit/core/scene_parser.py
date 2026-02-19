"""Parser for NMS SCENE.MBIN EXML into SceneNode tree.

Pure domain module — stdlib only (xml.etree.ElementTree).

SCENE EXML structure (after MBINCompiler converts .mbin to .exml):
  <Data template="TkSceneNodeData">
    <Property name="Name" value="ROOT" />
    <Property name="Type" value="MODEL" />
    <Property name="Transform">
      <Property name="TransX" value="0" /> ...
    </Property>
    <Property name="Attributes">
      <Property value="TkSceneNodeAttributeData">
        <Property name="Name" value="GEOMETRY" />
        <Property name="Value" value="MODELS/.../GEOMETRY.MBIN" />
      </Property>
    </Property>
    <Property name="Children">
      <Property value="TkSceneNodeData">...</Property>
    </Property>
  </Data>
"""

from __future__ import annotations

from typing import Tuple
from xml.etree.ElementTree import Element, fromstring

from nmstoolkit.core.mesh_data import SceneNode, Transform


def parse_scene(source: str) -> SceneNode:
    """Parse SCENE EXML source into a SceneNode tree."""
    root = fromstring(source)
    return _parse_node(root)


def _parse_node(element: Element) -> SceneNode:
    """Parse a TkSceneNodeData element into a SceneNode."""
    name = _get_property_value(element, "Name") or ""
    node_type = _get_property_value(element, "Type") or ""
    transform = _parse_transform(element)
    geometry_ref, material_ref, scene_ref = _parse_attributes(element)
    children = _parse_children(element)

    return SceneNode(
        name=name,
        node_type=node_type,
        transform=transform,
        geometry_ref=geometry_ref,
        material_ref=material_ref,
        scene_ref=scene_ref,
        children=children,
    )


def _get_property_value(parent: Element, name: str) -> str:
    """Get the value attribute of a named Property child."""
    prop = parent.find(f"Property[@name='{name}']")
    if prop is None:
        return ""
    return prop.get("value", "")


def _parse_transform(parent: Element) -> Transform:
    """Parse Transform property into a Transform dataclass."""
    transform_el = parent.find("Property[@name='Transform']")
    if transform_el is None:
        return Transform.identity()

    def _float(name: str) -> float:
        val = _get_property_value(transform_el, name)
        if not val:
            return 0.0
        return float(val)

    return Transform(
        position=(_float("TransX"), _float("TransY"), _float("TransZ")),
        rotation=(_float("RotX"), _float("RotY"), _float("RotZ")),
        scale=(
            _float("ScaleX") or 1.0,
            _float("ScaleY") or 1.0,
            _float("ScaleZ") or 1.0,
        ),
    )


def _parse_attributes(parent: Element) -> Tuple[str, str, str]:
    """Extract GEOMETRY, MATERIAL, and SCENEGRAPH refs from Attributes list.

    Returns (geometry_ref, material_ref, scene_ref).
    """
    geometry_ref = ""
    material_ref = ""
    scene_ref = ""

    attrs_el = parent.find("Property[@name='Attributes']")
    if attrs_el is None:
        return geometry_ref, material_ref, scene_ref

    for attr in attrs_el:
        if attr.tag != "Property":
            continue
        attr_name = _get_property_value(attr, "Name")
        attr_value = _get_property_value(attr, "Value")
        if attr_name == "GEOMETRY":
            geometry_ref = attr_value
        elif attr_name == "MATERIAL":
            material_ref = attr_value
        elif attr_name == "SCENEGRAPH":
            scene_ref = attr_value

    return geometry_ref, material_ref, scene_ref


def _parse_children(parent: Element) -> Tuple[SceneNode, ...]:
    """Parse Children property into tuple of SceneNode."""
    children_el = parent.find("Property[@name='Children']")
    if children_el is None:
        return ()

    nodes = []
    for child in children_el:
        if child.tag != "Property":
            continue
        nodes.append(_parse_node(child))

    return tuple(nodes)
