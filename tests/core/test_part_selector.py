"""Tests for part_selector — random part selection from descriptor tree."""

import inspect

from nmstoolkit.core.mesh_data import DescriptorGroup, DescriptorOption
from nmstoolkit.core.part_selector import select_parts


def _group(type_id: str, *options: DescriptorOption) -> DescriptorGroup:
    return DescriptorGroup(type_id=type_id, options=tuple(options))


def _opt(id: str, chance: float = 0.0, *children: DescriptorGroup) -> DescriptorOption:
    return DescriptorOption(id=id, chance=chance, children=tuple(children))


class TestSelectPartsSingleGroup:
    """Select from a group with one option — always returns that option."""

    def test_single_option_always_selected(self):
        group = _group("BODY", _opt("BODY_A"))
        result = select_parts(group)
        assert "BODY_A" in result

    def test_returns_frozenset(self):
        group = _group("BODY", _opt("BODY_A"))
        result = select_parts(group)
        assert isinstance(result, frozenset)

    def test_two_options_returns_exactly_one(self):
        group = _group("WINGS", _opt("WINGS_A"), _opt("WINGS_B"))
        for _ in range(20):
            result = select_parts(group)
            assert len(result) == 1
            assert result <= {"WINGS_A", "WINGS_B"}


class TestSelectPartsWeighted:
    """Weighted selection respects Chance values (statistical test)."""

    def test_high_weight_dominates(self):
        # COCK_B has weight 99, COCK_A has weight 1
        # Over 200 trials, COCK_B should win the vast majority
        group = _group(
            "COCKPIT",
            _opt("COCK_A", 1.0),
            _opt("COCK_B", 99.0),
        )
        counts = {"COCK_A": 0, "COCK_B": 0}
        for _ in range(200):
            result = select_parts(group)
            for name in result:
                counts[name] += 1
        # COCK_B should appear in at least 150 of 200 trials (very conservative)
        assert counts["COCK_B"] >= 150


class TestSelectPartsNested:
    """Nested groups produce union of all selected ids."""

    def test_nested_includes_parent_and_child(self):
        child_group = _group("DETAIL", _opt("DETAIL_X"))
        group = _group("BODY", _opt("BODY_A", 0.0, child_group))
        result = select_parts(group)
        assert "BODY_A" in result
        assert "DETAIL_X" in result

    def test_nested_two_levels(self):
        inner = _group("COLOR", _opt("RED"))
        middle = _group("DETAIL", _opt("DETAIL_X", 0.0, inner))
        outer = _group("BODY", _opt("BODY_A", 0.0, middle))
        result = select_parts(outer)
        assert result == frozenset({"BODY_A", "DETAIL_X", "RED"})


class TestSelectPartsEmpty:
    """Empty descriptor returns empty set."""

    def test_empty_options(self):
        group = _group("EMPTY")
        result = select_parts(group)
        assert result == frozenset()


class TestSelectPartsApiContract:
    """API contract: select_parts does NOT accept an NMS seed parameter."""

    def test_no_seed_parameter(self):
        sig = inspect.signature(select_parts)
        param_names = list(sig.parameters.keys())
        assert param_names == ["descriptor"], (
            f"select_parts must accept only 'descriptor', got {param_names}"
        )

    def test_no_seed_keyword(self):
        sig = inspect.signature(select_parts)
        for name in sig.parameters:
            assert "seed" not in name.lower(), (
                f"Parameter name '{name}' contains 'seed' — forbidden by community decision"
            )
