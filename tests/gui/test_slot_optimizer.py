"""Tests for slot optimizer — technology adjacency layout optimization.

Tests cover:
- Tech grouping by category / ID prefix
- Adjacency scoring
- BFS cluster expansion
- optimize_tech_layout() rearranges tech items
- Non-tech items are never moved
- Supercharged slot preference
"""

import copy

import pytest

from nmstoolkit.gui.widgets.slot_optimizer import (
    _bfs_cluster,
    _get_tech_category,
    _neighbors,
    _score_placement,
    optimize_tech_layout,
)


def _make_slot(item_id, x, y, inv_type="Technology"):
    return {
        "Type": {"InventoryType": inv_type},
        "Id": item_id,
        "Amount": 1,
        "MaxAmount": 1,
        "DamageFactor": 0.0,
        "FullyInstalled": True,
        "Index": {"X": x, "Y": y},
    }


def _make_inventory(slots, width=6, height=5, special_slots=None):
    valid = [{"X": x, "Y": y} for x in range(width) for y in range(height)]
    return {
        "Slots": slots,
        "ValidSlotIndices": valid,
        "Width": width,
        "Height": height,
        "SpecialSlots": special_slots or [],
    }


class TestTechCategory:
    def test_laser_upgrade_grouped(self):
        assert _get_tech_category("UP_LASER1", None) == "UP_LASER"

    def test_hyperdrive_upgrade_grouped(self):
        assert _get_tech_category("UP_HYP1", None) == "UP_HYP"

    def test_ship_shield_upgrade_grouped(self):
        assert _get_tech_category("UA_SHIELD3", None) == "UA_SHIELD"

    def test_procedural_suffix_stripped(self):
        cat = _get_tech_category("UP_LASER1#12345", None)
        assert cat == "UP_LASER"

    def test_caret_prefix_stripped(self):
        cat = _get_tech_category("^UP_LASER1", None)
        assert cat == "UP_LASER"

    def test_empty_returns_empty(self):
        assert _get_tech_category("", None) == ""

    def test_generic_prefix_fallback(self):
        """Unknown prefix should fall back to first two segments."""
        cat = _get_tech_category("WEIRD_THING_1", None)
        assert cat == "WEIRD_THING"


class TestNeighbors:
    def test_returns_four_neighbors(self):
        result = _neighbors(2, 3)
        assert len(result) == 4
        assert (1, 3) in result
        assert (3, 3) in result
        assert (2, 2) in result
        assert (2, 4) in result


class TestScorePlacement:
    def test_adjacent_pair_scores(self):
        """Two same-group items adjacent should score > 0."""
        positions = {"laser": [(0, 0), (1, 0)]}
        score = _score_placement(positions, set())
        assert score > 0

    def test_non_adjacent_scores_zero(self):
        """Two same-group items not adjacent should score 0."""
        positions = {"laser": [(0, 0), (3, 3)]}
        score = _score_placement(positions, set())
        assert score == 0

    def test_supercharged_bonus(self):
        """Item on supercharged slot should get bonus points."""
        positions = {"laser": [(0, 0)]}
        score_normal = _score_placement(positions, set())
        score_special = _score_placement(positions, {(0, 0)})
        assert score_special > score_normal

    def test_different_groups_no_adjacency_bonus(self):
        """Adjacent items from different groups should not get adjacency bonus."""
        positions = {"laser": [(0, 0)], "shield": [(1, 0)]}
        score = _score_placement(positions, set())
        assert score == 0


class TestBfsCluster:
    def test_expands_from_start(self):
        available = [(0, 0), (1, 0), (2, 0), (0, 1)]
        cluster = _bfs_cluster((0, 0), 3, available, set())
        assert len(cluster) == 3
        assert (0, 0) in cluster

    def test_respects_used_positions(self):
        available = [(0, 0), (1, 0), (2, 0)]
        used = {(1, 0)}
        cluster = _bfs_cluster((0, 0), 3, available, used)
        assert (1, 0) not in cluster

    def test_start_not_available_returns_empty(self):
        cluster = _bfs_cluster((5, 5), 3, [(0, 0), (1, 0)], set())
        assert len(cluster) == 0

    def test_cluster_is_connected(self):
        """All positions in cluster should be reachable from start."""
        available = [(x, y) for x in range(5) for y in range(5)]
        cluster = _bfs_cluster((0, 0), 4, available, set())
        assert len(cluster) == 4
        # Each position should be adjacent to at least one other
        for pos in cluster[1:]:
            has_neighbor = any(
                (pos[0] + dx, pos[1] + dy) in cluster
                for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]
            )
            assert has_neighbor


class TestOptimizeTechLayout:
    def test_non_tech_items_not_moved(self):
        """Substance/Product items should stay at their original positions."""
        substance = _make_slot("^FUEL1", 0, 0, inv_type="Substance")
        tech = _make_slot("^UP_LASER1", 3, 3)
        inventory = _make_inventory([substance, tech], width=6, height=5)

        optimize_tech_layout(inventory)

        # Find the substance slot
        for s in inventory["Slots"]:
            if s["Id"] == "^FUEL1":
                assert s["Index"]["X"] == 0
                assert s["Index"]["Y"] == 0
                break

    def test_same_group_techs_placed_adjacent(self):
        """Same-type techs should end up adjacent after optimization."""
        slots = [
            _make_slot("^UP_LASER1", 0, 0),
            _make_slot("^UP_LASER2", 5, 4),
            _make_slot("^UP_LASER3", 3, 2),
        ]
        inventory = _make_inventory(slots, width=6, height=5)

        optimize_tech_layout(inventory)

        # Find laser positions after optimization
        laser_positions = set()
        for s in inventory["Slots"]:
            if s["Id"].startswith("^UP_LASER"):
                laser_positions.add((s["Index"]["X"], s["Index"]["Y"]))

        # At least one pair should be adjacent
        adjacent_count = 0
        for pos in laser_positions:
            for nx, ny in _neighbors(pos[0], pos[1]):
                if (nx, ny) in laser_positions:
                    adjacent_count += 1
        assert adjacent_count > 0, "Laser upgrades should be adjacent after optimization"

    def test_empty_inventory_is_noop(self):
        """Optimizing an inventory with no tech items should be a no-op."""
        inventory = _make_inventory([], width=6, height=5)
        optimize_tech_layout(inventory)
        assert inventory["Slots"] == []

    def test_single_tech_item_unchanged(self):
        """A single tech item should not crash the optimizer."""
        slot = _make_slot("^UP_LASER1", 2, 2)
        inventory = _make_inventory([slot], width=6, height=5)
        optimize_tech_layout(inventory)
        # Should still have one tech slot
        tech_slots = [s for s in inventory["Slots"] if s.get("Id")]
        assert len(tech_slots) == 1

    def test_supercharged_slots_preferred(self):
        """Tech items should prefer supercharged slot positions."""
        slots = [
            _make_slot("^UP_LASER1", 0, 0),
            _make_slot("^UP_LASER2", 1, 0),
        ]
        special = [
            {"Type": {"InventorySpecialSlotType": "TechBonus"}, "Index": {"X": 3, "Y": 3}},
            {"Type": {"InventorySpecialSlotType": "TechBonus"}, "Index": {"X": 4, "Y": 3}},
        ]
        inventory = _make_inventory(slots, width=6, height=5, special_slots=special)

        optimize_tech_layout(inventory)

        # At least one laser should land on a supercharged position
        laser_positions = set()
        for s in inventory["Slots"]:
            if s["Id"].startswith("^UP_LASER"):
                laser_positions.add((s["Index"]["X"], s["Index"]["Y"]))

        special_positions = {(3, 3), (4, 3)}
        overlap = laser_positions & special_positions
        assert len(overlap) > 0, "At least one tech should be on a supercharged slot"

    def test_preserves_slot_count(self):
        """Optimizer should not create or destroy slots."""
        slots = [
            _make_slot("^FUEL1", 0, 0, inv_type="Substance"),
            _make_slot("^UP_LASER1", 1, 0),
            _make_slot("^UP_LASER2", 2, 0),
            _make_slot("^UP_SHIELD1", 3, 0),
        ]
        inventory = _make_inventory(slots, width=6, height=5)
        original_count = len(inventory["Slots"])

        optimize_tech_layout(inventory)

        assert len(inventory["Slots"]) == original_count
