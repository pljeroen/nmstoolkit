"""Tests for the game data pipeline — end-to-end integration.

Tests R-PIPE-02: Full pipeline PAK → MBIN → EXML → GameCatalogue.
Requires MBINCompiler and NMS game files.
"""

import json
import os
from pathlib import Path

import pytest

_mbin_compiler = os.environ.get("NMS_TEST_MBIN_COMPILER", "")
MBIN_COMPILER = Path(_mbin_compiler) if _mbin_compiler else Path("/nonexistent")
_game_dir = os.environ.get("NMS_TEST_GAME_DIR", "")
GAME_DIR = Path(_game_dir) if _game_dir else Path("/nonexistent")
PAK_DIR = GAME_DIR / "GAMEDATA" / "PCBANKS"

needs_full_pipeline = pytest.mark.skipif(
    not (MBIN_COMPILER.exists() and PAK_DIR.exists()),
    reason="MBINCompiler or NMS game files not available",
)


@needs_full_pipeline
class TestGameDataPipeline:
    """R-PIPE-02: Full pipeline produces a GameCatalogue."""

    def test_build_catalogue(self, tmp_path):
        from nmstoolkit.core.game_data_pipeline import build_catalogue

        catalogue = build_catalogue(
            pak_dir=PAK_DIR,
            mbin_compiler=MBIN_COMPILER,
        )
        assert len(catalogue.products) > 100
        assert len(catalogue.substances) > 10
        assert len(catalogue.technologies) > 50
        assert len(catalogue.locale) > 1000

    def test_catalogue_has_resolved_names(self, tmp_path):
        from nmstoolkit.core.game_data_pipeline import build_catalogue

        catalogue = build_catalogue(
            pak_dir=PAK_DIR,
            mbin_compiler=MBIN_COMPILER,
        )
        # Check a known product has a display_name
        casing = catalogue.find_product("CASING")
        assert casing is not None
        assert "display_name" in casing

    def test_cache_roundtrip(self, tmp_path):
        from nmstoolkit.core.game_data_pipeline import build_catalogue
        from nmstoolkit.core.game_catalogue import GameCatalogue

        catalogue = build_catalogue(
            pak_dir=PAK_DIR,
            mbin_compiler=MBIN_COMPILER,
        )
        # Save to cache
        cache_path = tmp_path / "gamedata.json"
        cache_path.write_text(catalogue.to_json())

        # Reload
        loaded = GameCatalogue.from_json(cache_path.read_text())
        assert len(loaded.products) == len(catalogue.products)
        assert len(loaded.substances) == len(catalogue.substances)
        assert len(loaded.technologies) == len(catalogue.technologies)
