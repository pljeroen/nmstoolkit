"""Tests for GameCatalogue domain model.

Tests R-CAT-01: Immutable value object holding game data.
"""

import ast
import json
from pathlib import Path

import pytest


class TestGameCataloguePurity:
    """Domain purity: game_catalogue.py uses only stdlib."""

    def test_no_external_imports(self):
        module_path = (
            Path(__file__).parent.parent.parent
            / "src"
            / "nmstoolkit"
            / "core"
            / "game_catalogue.py"
        )
        source = module_path.read_text()
        tree = ast.parse(source)

        stdlib_modules = {
            "dataclasses", "typing", "json", "pathlib", "os",
            "__future__", "collections", "enum",
        }

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top = alias.name.split(".")[0]
                    assert top in stdlib_modules, f"Non-stdlib: {alias.name}"
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    top = node.module.split(".")[0]
                    assert top in stdlib_modules, f"Non-stdlib: from {node.module}"


class TestGameCatalogueModel:
    """GameCatalogue is a frozen dataclass."""

    def test_create_catalogue(self):
        from nmstoolkit.core.game_catalogue import GameCatalogue

        cat = GameCatalogue(
            products=[{"id": "CASING", "name": "Metal Plating"}],
            substances=[{"id": "FUEL1", "name": "Carbon"}],
            technologies=[{"id": "PROTECT", "name": "Hazard Protection"}],
            locale={"CASING_NAME": "METAL PLATING"},
        )
        assert len(cat.products) == 1
        assert len(cat.substances) == 1
        assert len(cat.technologies) == 1
        assert cat.locale["CASING_NAME"] == "METAL PLATING"

    def test_catalogue_is_frozen(self):
        from nmstoolkit.core.game_catalogue import GameCatalogue

        cat = GameCatalogue(
            products=[], substances=[], technologies=[], locale={},
        )
        with pytest.raises(AttributeError):
            cat.products = []  # type: ignore[misc]

    def test_lookup_product_by_id(self):
        from nmstoolkit.core.game_catalogue import GameCatalogue

        cat = GameCatalogue(
            products=[
                {"id": "CASING", "name": "Metal Plating"},
                {"id": "NANOTUBES", "name": "Carbon Nanotubes"},
            ],
            substances=[], technologies=[], locale={},
        )
        result = cat.find_product("CASING")
        assert result is not None
        assert result["id"] == "CASING"

    def test_lookup_missing_product(self):
        from nmstoolkit.core.game_catalogue import GameCatalogue

        cat = GameCatalogue(
            products=[], substances=[], technologies=[], locale={},
        )
        assert cat.find_product("NONEXISTENT") is None

    def test_lookup_substance_by_id(self):
        from nmstoolkit.core.game_catalogue import GameCatalogue

        cat = GameCatalogue(
            products=[],
            substances=[{"id": "FUEL1", "name": "Carbon"}],
            technologies=[], locale={},
        )
        result = cat.find_substance("FUEL1")
        assert result is not None
        assert result["id"] == "FUEL1"

    def test_lookup_technology_by_id(self):
        from nmstoolkit.core.game_catalogue import GameCatalogue

        cat = GameCatalogue(
            products=[], substances=[],
            technologies=[{"id": "PROTECT", "name": "Hazard Protection"}],
            locale={},
        )
        result = cat.find_technology("PROTECT")
        assert result is not None

    def test_serialize_to_json(self):
        from nmstoolkit.core.game_catalogue import GameCatalogue

        cat = GameCatalogue(
            products=[{"id": "CASING"}],
            substances=[{"id": "FUEL1"}],
            technologies=[],
            locale={"K": "V"},
        )
        data = cat.to_json()
        assert isinstance(data, str)
        parsed = json.loads(data)
        assert parsed["products"] == [{"id": "CASING"}]
        assert parsed["locale"] == {"K": "V"}

    def test_deserialize_from_json(self):
        from nmstoolkit.core.game_catalogue import GameCatalogue

        data = json.dumps({
            "products": [{"id": "CASING"}],
            "substances": [],
            "technologies": [],
            "locale": {"K": "V"},
        })
        cat = GameCatalogue.from_json(data)
        assert len(cat.products) == 1
        assert cat.products[0]["id"] == "CASING"
        assert cat.locale["K"] == "V"

    def test_find_item_searches_all_types(self):
        from nmstoolkit.core.game_catalogue import GameCatalogue

        cat = GameCatalogue(
            products=[{"id": "CASING", "name": "Metal Plating"}],
            substances=[{"id": "FUEL1", "name": "Carbon"}],
            technologies=[{"id": "PROTECT", "name": "Hazard Protection"}],
            locale={},
        )
        assert cat.find_item("CASING") is not None
        assert cat.find_item("FUEL1") is not None
        assert cat.find_item("PROTECT") is not None
        assert cat.find_item("MISSING") is None
