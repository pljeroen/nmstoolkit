"""Parser for NMS DESCRIPTOR.MBIN EXML into DescriptorGroup selection trees.

Pure domain module — stdlib only (xml.etree.ElementTree).

Actual DESCRIPTOR EXML structure (cTkModelDescriptorList):

  <Data template="cTkModelDescriptorList">
    <Property name="List">
      <Property name="List" value="TkResourceDescriptorList" _index="0">
        <Property name="TypeId" value="_TOPMID_" />
        <Property name="Descriptors">
          <Property name="Descriptors" value="TkResourceDescriptorData" _id="...">
            <Property name="Id" value="_TOPMID_B3LOD0" />
            <Property name="Chance" value="0.000000" />
            <Property name="Children" />
          </Property>
        </Property>
      </Property>
    </Property>
  </Data>

The root List contains multiple TkResourceDescriptorList entries, each an
independent part slot (e.g. wings, cockpit, engine). For each slot, one
option is selected from its Descriptors list.
"""

from __future__ import annotations

from typing import Tuple
from xml.etree.ElementTree import Element, fromstring

from nmstoolkit.core.mesh_data import DescriptorGroup, DescriptorOption


def parse_descriptor(exml: str) -> DescriptorGroup:
    """Parse DESCRIPTOR EXML into a DescriptorGroup tree.

    Handles both cTkModelDescriptorList (List of groups) and bare
    TkResourceDescriptorList (single group) formats.
    Returns a synthetic root group whose options each contain one
    slot group as a child, or an empty group if no descriptors found.
    """
    root = fromstring(exml)
    template = root.get("template", "")

    if template == "cTkModelDescriptorList" or root.find("Property[@name='List']") is not None:
        groups = _parse_model_descriptor_list(root)
    else:
        groups = (_parse_descriptor_list(root),)

    # Filter out empty groups
    groups = tuple(g for g in groups if g.options)
    if not groups:
        return DescriptorGroup(type_id="", options=())

    # Wrap multiple groups as children of synthetic options so that
    # select_parts processes each group independently.
    if len(groups) == 1:
        return groups[0]

    # Create a synthetic root: one option per group, all selected.
    # Each "option" just carries its group as a child.
    synthetic_options = []
    for group in groups:
        synthetic_options.append(
            DescriptorOption(id="", chance=0.0, children=(group,))
        )
    return DescriptorGroup(type_id="ROOT", options=tuple(synthetic_options))


def parse_descriptor_groups(exml: str) -> Tuple[DescriptorGroup, ...]:
    """Parse DESCRIPTOR EXML into a tuple of independent DescriptorGroups.

    Each group represents one part slot (e.g. wings, cockpit, engine).
    Select one option from each group independently.
    """
    root = fromstring(exml)
    template = root.get("template", "")

    if template == "cTkModelDescriptorList" or root.find("Property[@name='List']") is not None:
        groups = _parse_model_descriptor_list(root)
    else:
        groups = (_parse_descriptor_list(root),)

    return tuple(g for g in groups if g.options)


def _parse_model_descriptor_list(root: Element) -> Tuple[DescriptorGroup, ...]:
    """Parse a cTkModelDescriptorList: root List → multiple TkResourceDescriptorList."""
    list_el = root.find("Property[@name='List']")
    if list_el is None:
        return ()

    groups = []
    for child in list_el:
        if child.tag != "Property":
            continue
        groups.append(_parse_descriptor_list(child))
    return tuple(groups)


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
