"""Tests for recipe tab refresh mechanism.

R-RECIPE-02: Recipe tab can reload recipes after extraction completes.
"""

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import json
import pytest
from pathlib import Path
from unittest.mock import patch

from PySide6.QtWidgets import QApplication

from nmstoolkit.gui.tabs.recipe_finder_tab import RecipeFinderTab

_app = QApplication.instance() or QApplication([])


class TestRecipeRefresh:
    def test_refresh_recipes_method_exists(self):
        """RecipeFinderTab must have a refresh_recipes() method."""
        tab = RecipeFinderTab()
        assert hasattr(tab, "refresh_recipes")
        assert callable(tab.refresh_recipes)

    def test_refresh_loads_new_recipes(self, tmp_path):
        """After refresh_recipes(), newly available recipes are loaded."""
        tab = RecipeFinderTab()
        initial_count = len(tab._all_recipes)

        # Create a fake catalogue with recipes
        cat_dir = tmp_path / "icons"
        cat_dir.mkdir()
        cat_data = {
            "products": [],
            "substances": [],
            "technologies": [],
            "locale": {},
            "recipes": [
                {
                    "result": {"id": "FUEL1", "amount": 1},
                    "ingredients": [{"id": "CARBON", "amount": 2}],
                    "cooking": False,
                    "time": 30,
                },
                {
                    "result": {"id": "FUEL2", "amount": 1},
                    "ingredients": [{"id": "CARBON", "amount": 5}],
                    "cooking": False,
                    "time": 60,
                },
            ],
        }
        (cat_dir / "game_catalogue.json").write_text(json.dumps(cat_data))

        with patch(
            "nmstoolkit.gui.tabs.recipe_finder_tab._catalogue_path",
            return_value=cat_dir / "game_catalogue.json",
        ):
            tab.refresh_recipes()

        assert len(tab._all_recipes) == 2
        assert tab._table.rowCount() == 2

    def test_refresh_hides_fallback_note(self, tmp_path):
        """After refresh with actual recipes, the fallback note is hidden."""
        tab = RecipeFinderTab()

        cat_dir = tmp_path / "icons"
        cat_dir.mkdir()
        cat_data = {
            "products": [], "substances": [], "technologies": [],
            "locale": {},
            "recipes": [
                {"result": {"id": "X"}, "ingredients": [{"id": "Y"}], "cooking": False, "time": 10},
            ],
        }
        (cat_dir / "game_catalogue.json").write_text(json.dumps(cat_data))

        with patch(
            "nmstoolkit.gui.tabs.recipe_finder_tab._catalogue_path",
            return_value=cat_dir / "game_catalogue.json",
        ):
            tab.refresh_recipes()

        assert not tab._note.isVisible()
