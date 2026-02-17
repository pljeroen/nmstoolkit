"""Tests for InventoryGrid tech-effects panel and adjacency visualization."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from nmstoolkit.gui.widgets.inventory_grid import (
    InventoryGrid,
    _arrow_from_to,
    set_catalogue,
)


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _slot(item_id, x, y, inv_type="Technology"):
    return {
        "Type": {"InventoryType": inv_type},
        "Id": item_id,
        "Amount": 1,
        "MaxAmount": 1,
        "DamageFactor": 0.0,
        "FullyInstalled": True,
        "Index": {"X": x, "Y": y},
    }


def _inv(slots, width=6, height=5, special=None):
    return {
        "Slots": slots,
        "ValidSlotIndices": [{"X": x, "Y": y} for x in range(width) for y in range(height)],
        "Width": width,
        "Height": height,
        "SpecialSlots": special or [],
    }


class _FakeCatalogue:
    def __init__(self, by_id):
        self._by_id = by_id
        self.locale = {}

    def find_item(self, item_id):
        return self._by_id.get(item_id)


def test_effects_panel_hidden_without_tech(qapp):
    grid = InventoryGrid("Test")
    grid.set_inventory(_inv([_slot("^FUEL1", 0, 0, inv_type="Substance")]))
    assert grid._effects_group.isHidden()


def test_effects_panel_visible_with_tech_and_stats(qapp):
    cat = _FakeCatalogue({
        "UP_LASER1": {"category": "UP_LASER", "stat_bonuses": [{"stat": "Ship_Damage", "bonus": 1.0}]},
        "UP_LASER2": {"category": "UP_LASER", "stat_bonuses": [{"stat": "Ship_Damage", "bonus": 2.0}]},
    })
    set_catalogue(cat)
    grid = InventoryGrid("Tech")
    grid.set_inventory(_inv([_slot("^UP_LASER1", 0, 0), _slot("^UP_LASER2", 1, 0)]))
    assert not grid._effects_group.isHidden()
    assert grid._effects_stats.rowCount() >= 1
    assert grid._effects_modules.rowCount() == 2
    assert grid._effects_stats.columnCount() == 3
    assert grid._effects_stats.item(0, 0).text() == "Damage"


def test_adjacency_highlight_marks_same_group_neighbors(qapp):
    cat = _FakeCatalogue({
        "UP_LASER1": {"category": "UP_LASER", "stat_bonuses": []},
        "UP_LASER2": {"category": "UP_LASER", "stat_bonuses": []},
        "UP_SHIELD1": {"category": "UP_SHIELD", "stat_bonuses": []},
    })
    set_catalogue(cat)
    grid = InventoryGrid("Tech")
    grid.set_inventory(
        _inv([
            _slot("^UP_LASER1", 0, 0),
            _slot("^UP_LASER2", 1, 0),
            _slot("^UP_SHIELD1", 0, 1),
        ])
    )

    grid._highlight_adjacency(0, 0)
    same_neighbor = grid.get_slot_widget(1, 0)
    other_neighbor = grid.get_slot_widget(0, 1)
    assert same_neighbor._adjacent_hint is True
    assert other_neighbor._adjacent_hint is False
    assert len(grid._connector_labels) == 1
    assert grid._hover_popup.isHidden() is False
    assert len(grid._hover_rows) >= 1

    grid._clear_adjacency_highlight()
    assert same_neighbor._adjacent_hint is False
    assert len(grid._connector_labels) == 0
    assert grid._hover_popup.isHidden() is True


def test_optimize_mode_updates_grid_mode(qapp, monkeypatch):
    grid = InventoryGrid("Tech")
    grid.set_inventory(_inv([_slot("^UP_LASER1", 0, 0), _slot("^UP_LASER2", 1, 0)]))

    monkeypatch.setattr(
        "PySide6.QtWidgets.QMessageBox.question",
        lambda *a, **k: 16384,  # QMessageBox.Yes
    )
    calls = []

    def fake_opt(inv, cat=None, mode="balanced"):
        calls.append(mode)

    monkeypatch.setattr(
        "nmstoolkit.gui.widgets.slot_optimizer.optimize_tech_layout",
        fake_opt,
    )

    grid._optimize_layout("dps", "DPS")
    assert grid._opt_mode == "dps"
    assert "dps" in calls


def test_effects_value_toggle_switches_between_current_and_optimized(qapp):
    cat = _FakeCatalogue({
        "UP_LASER1": {"category": "UP_LASER", "stat_bonuses": [{"stat": "Ship_Damage", "bonus": 1.0}]},
        "UP_LASER2": {"category": "UP_LASER", "stat_bonuses": [{"stat": "Ship_Damage", "bonus": 2.0}]},
    })
    set_catalogue(cat)
    grid = InventoryGrid("Tech")
    grid.set_inventory(_inv([_slot("^UP_LASER1", 0, 0), _slot("^UP_LASER2", 1, 0)]))

    before_label = grid._effects_value_toggle.text()
    grid._effects_value_toggle.click()
    after_label = grid._effects_value_toggle.text()

    assert before_label != after_label
    assert grid._effects_apply_button.isEnabled()


def test_module_row_uses_tooltip_for_name(qapp):
    cat = _FakeCatalogue({
        "UP_LASER1": {"category": "UP_LASER", "stat_bonuses": [{"stat": "Ship_Damage", "bonus": 1.0}]},
    })
    set_catalogue(cat)
    grid = InventoryGrid("Tech")
    grid.set_inventory(_inv([_slot("^UP_LASER1", 0, 0)]))
    cell_widget = grid._effects_modules.cellWidget(0, 0)
    assert cell_widget is not None
    assert cell_widget.toolTip() != ""


def test_arrow_direction_points_to_boost_recipient():
    assert _arrow_from_to(0, 0, 1, 0) == "→"
    assert _arrow_from_to(1, 0, 0, 0) == "←"
    assert _arrow_from_to(0, 0, 0, 1) == "↓"
    assert _arrow_from_to(0, 1, 0, 0) == "↑"
