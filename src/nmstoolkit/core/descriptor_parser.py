"""Parser for NMS DESCRIPTOR.MBIN EXML into a DescriptorGroup selection tree.

Pure domain module — stdlib only (xml.etree.ElementTree).

DESCRIPTOR EXML structure (TkResourceDescriptorList):

  <Data template="TkResourceDescriptorList">
    <Property name="TypeId" value="SHIP" />
    <Property name="Descriptors">
      <Property value="TkResourceDescriptorData">
        <Property name="Id" value="WINGS_A" />
        <Property name="Name" value="" />
        <Property name="Chance" value="0" />
        <Property name="Children">
          <Property value="TkResourceDescriptorList">...</Property>
        </Property>
      </Property>
    </Property>
  </Data>

Each DescriptorGroup contains mutually exclusive options (pick one).
Each option may have nested child groups for sub-part selection.
"""

from __future__ import annotations

from xml.etree.ElementTree import Element, fromstring

from nmstoolkit.core.mesh_data import DescriptorGroup, DescriptorOption


def parse_descriptor(exml: str) -> DescriptorGroup:
    """Parse DESCRIPTOR EXML into a DescriptorGroup tree.

    Returns an empty group (no options) if the EXML has no descriptors.
    """
    root = fromstring(exml)
    return _parse_descriptor_list(root)


def _parse_descriptor_list(element: Element) -> DescriptorGroup:
    """Parse a TkResourceDescriptorList element."""
    type_id_prop = element.find("Property[@name='TypeId']")
    type_id = type_id_prop.get("value", "") if type_id_prop is not None else ""

    descriptors_el = element.find("Property[@name='Descriptors']")
    if descriptors_el is None:
        return DescriptorGroup(type_id=type_id, options=())

    options = []
    for child in descriptors_el:
        if child.tag != "Property":
            continue
        options.append(_parse_descriptor_data(child))

    return DescriptorGroup(type_id=type_id, options=tuple(options))


def _parse_descriptor_data(element: Element) -> DescriptorOption:
    """Parse a TkResourceDescriptorData element."""
    id_prop = element.find("Property[@name='Id']")
    option_id = id_prop.get("value", "") if id_prop is not None else ""

    chance_prop = element.find("Property[@name='Chance']")
    chance = float(chance_prop.get("value", "0")) if chance_prop is not None else 0.0

    children_el = element.find("Property[@name='Children']")
    children = []
    if children_el is not None:
        for child in children_el:
            if child.tag != "Property":
                continue
            children.append(_parse_descriptor_list(child))

    return DescriptorOption(id=option_id, chance=chance, children=tuple(children))
