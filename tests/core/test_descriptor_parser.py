"""Tests for descriptor_parser — DESCRIPTOR.MBIN EXML → DescriptorGroup tree."""

from nmstoolkit.core.descriptor_parser import parse_descriptor
from nmstoolkit.core.mesh_data import DescriptorGroup, DescriptorOption


# -- Minimal valid DESCRIPTOR EXML fixtures --

SIMPLE_DESCRIPTOR = """\
<Data template="TkResourceDescriptorList">
  <Property name="TypeId" value="SHIP" />
  <Property name="Descriptors">
    <Property value="TkResourceDescriptorData">
      <Property name="Id" value="WINGS_A" />
      <Property name="Name" value="" />
      <Property name="Chance" value="0" />
      <Property name="Children" />
    </Property>
    <Property value="TkResourceDescriptorData">
      <Property name="Id" value="WINGS_B" />
      <Property name="Name" value="" />
      <Property name="Chance" value="0" />
      <Property name="Children" />
    </Property>
  </Property>
</Data>
"""

WEIGHTED_DESCRIPTOR = """\
<Data template="TkResourceDescriptorList">
  <Property name="TypeId" value="COCKPIT" />
  <Property name="Descriptors">
    <Property value="TkResourceDescriptorData">
      <Property name="Id" value="COCK_A" />
      <Property name="Name" value="" />
      <Property name="Chance" value="30" />
      <Property name="Children" />
    </Property>
    <Property value="TkResourceDescriptorData">
      <Property name="Id" value="COCK_B" />
      <Property name="Name" value="" />
      <Property name="Chance" value="70" />
      <Property name="Children" />
    </Property>
  </Property>
</Data>
"""

NESTED_DESCRIPTOR = """\
<Data template="TkResourceDescriptorList">
  <Property name="TypeId" value="BODY" />
  <Property name="Descriptors">
    <Property value="TkResourceDescriptorData">
      <Property name="Id" value="BODY_A" />
      <Property name="Name" value="" />
      <Property name="Chance" value="0" />
      <Property name="Children">
        <Property value="TkResourceDescriptorList">
          <Property name="TypeId" value="DETAIL" />
          <Property name="Descriptors">
            <Property value="TkResourceDescriptorData">
              <Property name="Id" value="DETAIL_X" />
              <Property name="Name" value="" />
              <Property name="Chance" value="0" />
              <Property name="Children" />
            </Property>
            <Property value="TkResourceDescriptorData">
              <Property name="Id" value="DETAIL_Y" />
              <Property name="Name" value="" />
              <Property name="Chance" value="0" />
              <Property name="Children" />
            </Property>
          </Property>
        </Property>
      </Property>
    </Property>
    <Property value="TkResourceDescriptorData">
      <Property name="Id" value="BODY_B" />
      <Property name="Name" value="" />
      <Property name="Chance" value="0" />
      <Property name="Children" />
    </Property>
  </Property>
</Data>
"""

EMPTY_DESCRIPTORS = """\
<Data template="TkResourceDescriptorList">
  <Property name="TypeId" value="EMPTY" />
  <Property name="Descriptors" />
</Data>
"""

MISSING_DESCRIPTORS = """\
<Data template="TkResourceDescriptorList">
  <Property name="TypeId" value="NOPE" />
</Data>
"""


class TestParseDescriptorSimple:
    """Parse a flat descriptor with two equal-weight options."""

    def test_returns_descriptor_group(self):
        result = parse_descriptor(SIMPLE_DESCRIPTOR)
        assert isinstance(result, DescriptorGroup)

    def test_type_id(self):
        result = parse_descriptor(SIMPLE_DESCRIPTOR)
        assert result.type_id == "SHIP"

    def test_option_count(self):
        result = parse_descriptor(SIMPLE_DESCRIPTOR)
        assert len(result.options) == 2

    def test_option_ids(self):
        result = parse_descriptor(SIMPLE_DESCRIPTOR)
        ids = [opt.id for opt in result.options]
        assert ids == ["WINGS_A", "WINGS_B"]

    def test_zero_chance_means_equal_weight(self):
        result = parse_descriptor(SIMPLE_DESCRIPTOR)
        for opt in result.options:
            assert opt.chance == 0.0

    def test_no_children(self):
        result = parse_descriptor(SIMPLE_DESCRIPTOR)
        for opt in result.options:
            assert opt.children == ()


class TestParseDescriptorWeighted:
    """Parse a descriptor with explicit Chance weights."""

    def test_chance_values(self):
        result = parse_descriptor(WEIGHTED_DESCRIPTOR)
        chances = [opt.chance for opt in result.options]
        assert chances == [30.0, 70.0]


class TestParseDescriptorNested:
    """Parse a descriptor with nested children."""

    def test_top_level_options(self):
        result = parse_descriptor(NESTED_DESCRIPTOR)
        assert len(result.options) == 2
        assert result.options[0].id == "BODY_A"
        assert result.options[1].id == "BODY_B"

    def test_body_a_has_child_group(self):
        result = parse_descriptor(NESTED_DESCRIPTOR)
        body_a = result.options[0]
        assert len(body_a.children) == 1
        child_group = body_a.children[0]
        assert isinstance(child_group, DescriptorGroup)
        assert child_group.type_id == "DETAIL"

    def test_nested_child_options(self):
        result = parse_descriptor(NESTED_DESCRIPTOR)
        child_group = result.options[0].children[0]
        ids = [opt.id for opt in child_group.options]
        assert ids == ["DETAIL_X", "DETAIL_Y"]

    def test_body_b_no_children(self):
        result = parse_descriptor(NESTED_DESCRIPTOR)
        body_b = result.options[1]
        assert body_b.children == ()


class TestParseDescriptorEmpty:
    """Handle missing or empty descriptor data."""

    def test_empty_descriptors_tag(self):
        result = parse_descriptor(EMPTY_DESCRIPTORS)
        assert isinstance(result, DescriptorGroup)
        assert result.options == ()

    def test_missing_descriptors_tag(self):
        result = parse_descriptor(MISSING_DESCRIPTORS)
        assert isinstance(result, DescriptorGroup)
        assert result.options == ()
