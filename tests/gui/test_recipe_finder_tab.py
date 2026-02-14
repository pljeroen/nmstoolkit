"""Tests for Recipe Finder tab."""

import pytest
from PySide6.QtWidgets import QApplication

from nmstoolkit.gui.tabs.recipe_finder_tab import RecipeFinderTab


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _make_psd(known_recipes=None):
    if known_recipes is None:
        known_recipes = ["^REFINERECIPE_26", "^REFINERECIPE_41"]
    return {
        "KnownRefinerRecipes": list(known_recipes),
    }


class TestRecipeFinderTabLoad:
    def test_tab_creates(self, qapp):
        tab = RecipeFinderTab()
        assert tab is not None

    def test_loads_recipes_or_fallback(self, qapp):
        tab = RecipeFinderTab()
        # Should have either catalogue recipes or fallback food items loaded
        assert tab._table.rowCount() > 0

    def test_set_data_shows_known_recipes(self, qapp):
        tab = RecipeFinderTab()
        psd = _make_psd(["^REFINERECIPE_26", "^REFINERECIPE_41"])
        tab.set_data(psd)
        assert tab._known_count_label.text() == "2 recipes unlocked"

    def test_set_data_empty_recipes(self, qapp):
        tab = RecipeFinderTab()
        psd = _make_psd([])
        tab.set_data(psd)
        assert tab._known_count_label.text() == "0 recipes unlocked"


class TestRecipeFinderSearch:
    def test_filter_narrows_results(self, qapp):
        tab = RecipeFinderTab()
        total = tab._table.rowCount()
        tab._search_edit.setText("carbon")
        tab._apply_filter()
        # Should show fewer items than total (unless no recipes loaded)
        visible = tab._table.rowCount()
        if tab._all_recipes:
            assert visible < total or total == 0

    def test_empty_filter_shows_all(self, qapp):
        tab = RecipeFinderTab()
        total_before = tab._table.rowCount()
        tab._search_edit.setText("something_unlikely_xyz")
        tab._apply_filter()
        tab._search_edit.setText("")
        tab._apply_filter()
        assert tab._table.rowCount() == total_before


class TestRecipeFinderUnlock:
    def test_unlock_all_recipes(self, qapp):
        tab = RecipeFinderTab()
        psd = _make_psd([])
        tab.set_data(psd)
        tab._on_unlock_all()
        # Should have added recipe IDs to the list
        assert len(psd["KnownRefinerRecipes"]) == 400
        assert "400 recipes unlocked" in tab._known_count_label.text()
