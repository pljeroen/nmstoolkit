"""Tests for descriptor_parser — DESCRIPTOR.MBIN EXML → DescriptorGroup tree."""

from nmstoolkit.core.descriptor_parser import parse_descriptor, parse_descriptor_groups
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

# -- cTkModelDescriptorList fixtures (real game format) --

MODEL_DESCRIPTOR_SINGLE_GROUP = """\
<Data template="cTkModelDescriptorList">
  <Property name="List">
    <Property name="List" value="TkResourceDescriptorList" _index="0">
      <Property name="TypeId" value="_TOPMID_" />
      <Property name="Descriptors">
        <Property name="Descriptors" value="TkResourceDescriptorData" _id="_TOPMID_A">
          <Property name="Id" value="_TOPMID_A" />
          <Property name="Chance" value="0.000000" />
          <Property name="Children" />
        </Property>
        <Property name="Descriptors" value="TkResourceDescriptorData" _id="_TOPMID_B">
          <Property name="Id" value="_TOPMID_B" />
          <Property name="Chance" value="50.000000" />
          <Property name="Children" />
        </Property>
      </Property>
    </Property>
  </Property>
</Data>
"""

MODEL_DESCRIPTOR_MULTI_GROUP = """\
<Data template="cTkModelDescriptorList">
  <Property name="List">
    <Property name="List" value="TkResourceDescriptorList" _index="0">
      <Property name="TypeId" value="WINGS" />
      <Property name="Descriptors">
        <Property name="Descriptors" value="TkResourceDescriptorData" _id="W_A">
          <Property name="Id" value="W_A" />
          <Property name="Chance" value="0.000000" />
          <Property name="Children" />
        </Property>
        <Property name="Descriptors" value="TkResourceDescriptorData" _id="W_B">
          <Property name="Id" value="W_B" />
          <Property name="Chance" value="0.000000" />
          <Property name="Children" />
        </Property>
      </Property>
    </Property>
    <Property name="List" value="TkResourceDescriptorList" _index="1">
      <Property name="TypeId" value="ENGINE" />
      <Property name="Descriptors">
        <Property name="Descriptors" value="TkResourceDescriptorData" _id="E_A">
          <Property name="Id" value="E_A" />
          <Property name="Chance" value="0.000000" />
          <Property name="Children" />
        </Property>
      </Property>
    </Property>
  </Property>
</Data>
"""

MODEL_DESCRIPTOR_NESTED = """\
<Data template="cTkModelDescriptorList">
  <Property name="List">
    <Property name="List" value="TkResourceDescriptorList" _index="0">
      <Property name="TypeId" value="BODY" />
      <Property name="Descriptors">
        <Property name="Descriptors" value="TkResourceDescriptorData" _id="B_MAIN">
          <Property name="Id" value="B_MAIN" />
          <Property name="Chance" value="0.000000" />
          <Property name="Children">
            <Property value="TkResourceDescriptorList">
              <Property name="TypeId" value="DETAIL" />
              <Property name="Descriptors">
                <Property name="Descriptors" value="TkResourceDescriptorData" _id="D_X">
                  <Property name="Id" value="D_X" />
                  <Property name="Chance" value="0.000000" />
                  <Property name="Children" />
                </Property>
              </Property>
            </Property>
          </Property>
        </Property>
      </Property>
    </Property>
  </Property>
</Data>
"""

MODEL_DESCRIPTOR_EMPTY_LIST = """\
<Data template="cTkModelDescriptorList">
  <Property name="List" />
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


class TestModelDescriptorListSingle:
    """Parse cTkModelDescriptorList with a single group — unwraps to that group."""

    def test_returns_descriptor_group(self):
        result = parse_descriptor(MODEL_DESCRIPTOR_SINGLE_GROUP)
        assert isinstance(result, DescriptorGroup)

    def test_type_id(self):
        result = parse_descriptor(MODEL_DESCRIPTOR_SINGLE_GROUP)
        assert result.type_id == "_TOPMID_"

    def test_option_count(self):
        result = parse_descriptor(MODEL_DESCRIPTOR_SINGLE_GROUP)
        assert len(result.options) == 2

    def test_option_ids(self):
        result = parse_descriptor(MODEL_DESCRIPTOR_SINGLE_GROUP)
        ids = [opt.id for opt in result.options]
        assert ids == ["_TOPMID_A", "_TOPMID_B"]

    def test_chance_values(self):
        result = parse_descriptor(MODEL_DESCRIPTOR_SINGLE_GROUP)
        assert result.options[0].chance == 0.0
        assert result.options[1].chance == 50.0


class TestModelDescriptorListMulti:
    """Parse cTkModelDescriptorList with multiple groups — synthetic root."""

    def test_synthetic_root_type_id(self):
        result = parse_descriptor(MODEL_DESCRIPTOR_MULTI_GROUP)
        assert result.type_id == "ROOT"

    def test_synthetic_root_option_count(self):
        result = parse_descriptor(MODEL_DESCRIPTOR_MULTI_GROUP)
        # One synthetic option per group
        assert len(result.options) == 2

    def test_synthetic_options_carry_groups_as_children(self):
        result = parse_descriptor(MODEL_DESCRIPTOR_MULTI_GROUP)
        for opt in result.options:
            assert opt.id == ""
            assert len(opt.children) == 1
            assert isinstance(opt.children[0], DescriptorGroup)

    def test_child_group_type_ids(self):
        result = parse_descriptor(MODEL_DESCRIPTOR_MULTI_GROUP)
        group_type_ids = [opt.children[0].type_id for opt in result.options]
        assert group_type_ids == ["WINGS", "ENGINE"]

    def test_wings_group_options(self):
        result = parse_descriptor(MODEL_DESCRIPTOR_MULTI_GROUP)
        wings = result.options[0].children[0]
        ids = [opt.id for opt in wings.options]
        assert ids == ["W_A", "W_B"]

    def test_engine_group_single_option(self):
        result = parse_descriptor(MODEL_DESCRIPTOR_MULTI_GROUP)
        engine = result.options[1].children[0]
        assert len(engine.options) == 1
        assert engine.options[0].id == "E_A"


class TestModelDescriptorListNested:
    """Parse cTkModelDescriptorList with nested Children."""

    def test_nested_child_group(self):
        result = parse_descriptor(MODEL_DESCRIPTOR_NESTED)
        # Single group, unwrapped
        assert result.type_id == "BODY"
        body_main = result.options[0]
        assert body_main.id == "B_MAIN"
        assert len(body_main.children) == 1
        detail = body_main.children[0]
        assert detail.type_id == "DETAIL"
        assert detail.options[0].id == "D_X"


class TestModelDescriptorListEmpty:
    """Parse cTkModelDescriptorList with empty List."""

    def test_empty_list(self):
        result = parse_descriptor(MODEL_DESCRIPTOR_EMPTY_LIST)
        assert result.options == ()


class TestParseDescriptorGroups:
    """parse_descriptor_groups returns individual groups (not synthetic root)."""

    def test_multi_group_returns_tuple(self):
        groups = parse_descriptor_groups(MODEL_DESCRIPTOR_MULTI_GROUP)
        assert isinstance(groups, tuple)
        assert len(groups) == 2

    def test_group_type_ids(self):
        groups = parse_descriptor_groups(MODEL_DESCRIPTOR_MULTI_GROUP)
        assert groups[0].type_id == "WINGS"
        assert groups[1].type_id == "ENGINE"

    def test_single_group(self):
        groups = parse_descriptor_groups(MODEL_DESCRIPTOR_SINGLE_GROUP)
        assert len(groups) == 1
        assert groups[0].type_id == "_TOPMID_"

    def test_empty_list(self):
        groups = parse_descriptor_groups(MODEL_DESCRIPTOR_EMPTY_LIST)
        assert groups == ()

    def test_bare_format(self):
        groups = parse_descriptor_groups(SIMPLE_DESCRIPTOR)
        assert len(groups) == 1
        assert groups[0].type_id == "SHIP"
