"""Tests for icon extractor — PAK to PNG icon pipeline.

Tests cover:
- Icon path listing from PAK file index
- DDS-to-PNG extraction and caching
- Item-to-DDS path matching (icon_map building)
- Icon map persistence (JSON save/load)
"""

import json
import struct
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from nmstoolkit.core.icon_extractor import IconExtractor


def _make_dds_bytes(width: int = 64, height: int = 64) -> bytes:
    """Create a minimal uncompressed DDS file (RGBA8)."""
    magic = b"DDS "
    pf = struct.pack(
        "<8I", 32, 0x41, 0, 32,
        0x000000FF, 0x0000FF00, 0x00FF0000, 0xFF000000,
    )
    header = struct.pack("<7I", 124, 0x1007, height, width, width * 4, 0, 0)
    header += b"\x00" * 44
    header += pf
    header += struct.pack("<5I", 0x1000, 0, 0, 0, 0)
    pixel_data = bytes([255, 128, 64, 255] * width * height)
    return magic + header + pixel_data


class TestExtractAllIcons:
    """Extract DDS icons from PAK and cache as PNG."""

    def test_extracts_icons_from_pak(self, tmp_path):
        """extract_all_icons should extract DDS files and cache as PNG."""
        cache_dir = tmp_path / "icons"
        game_dir = tmp_path / "game"
        pak_dir = game_dir / "GAMEDATA" / "PCBANKS"
        pak_dir.mkdir(parents=True)
        (pak_dir / "NMSARC.TexUI.pak").touch()

        dds_data = _make_dds_bytes()
        file_list = [
            "textures/ui/frontend/icons/substances/substance.fuel.1.dds",
            "textures/ui/frontend/icons/products/product.casing.dds",
            "textures/other/not_an_icon.dds",
        ]
        extracted = {
            "textures/ui/frontend/icons/substances/substance.fuel.1.dds": dds_data,
            "textures/ui/frontend/icons/products/product.casing.dds": dds_data,
        }

        mock_pak = MagicMock()
        mock_pak.__enter__ = MagicMock(return_value=mock_pak)
        mock_pak.__exit__ = MagicMock(return_value=False)
        mock_pak.list_files.return_value = file_list
        mock_pak.extract.return_value = extracted

        extractor = IconExtractor(game_dir, cache_dir)

        with patch(
            "nmstoolkit.core.icon_extractor.HgpakAdapter.from_path",
            return_value=mock_pak,
        ):
            count = extractor.extract_all_icons()

        assert count == 2

    def test_returns_zero_when_no_pak(self, tmp_path):
        """extract_all_icons returns 0 when PAK file doesn't exist."""
        cache_dir = tmp_path / "icons"
        game_dir = tmp_path / "game"
        extractor = IconExtractor(game_dir, cache_dir)

        count = extractor.extract_all_icons()
        assert count == 0

    def test_filters_only_icon_dds_paths(self, tmp_path):
        """Only DDS files under textures/ui/frontend/icons/ are extracted."""
        cache_dir = tmp_path / "icons"
        game_dir = tmp_path / "game"
        pak_dir = game_dir / "GAMEDATA" / "PCBANKS"
        pak_dir.mkdir(parents=True)
        (pak_dir / "NMSARC.TexUI.pak").touch()

        dds_data = _make_dds_bytes()
        file_list = [
            "textures/ui/frontend/icons/substances/fuel.dds",
            "textures/other/model.dds",
            "shaders/pixel.dds",
        ]

        mock_pak = MagicMock()
        mock_pak.__enter__ = MagicMock(return_value=mock_pak)
        mock_pak.__exit__ = MagicMock(return_value=False)
        mock_pak.list_files.return_value = file_list
        mock_pak.extract.return_value = {
            "textures/ui/frontend/icons/substances/fuel.dds": dds_data,
        }

        extractor = IconExtractor(game_dir, cache_dir)

        with patch(
            "nmstoolkit.core.icon_extractor.HgpakAdapter.from_path",
            return_value=mock_pak,
        ):
            count = extractor.extract_all_icons()

        # Only the icon path should be extracted, not the non-icon ones
        extract_call = mock_pak.extract.call_args
        paths_kwarg = extract_call.kwargs.get("paths", extract_call.args[0] if extract_call.args else [])
        assert "textures/ui/frontend/icons/substances/fuel.dds" in paths_kwarg
        assert "textures/other/model.dds" not in paths_kwarg
        assert "shaders/pixel.dds" not in paths_kwarg


class TestBuildIconMap:
    """Map item IDs to DDS texture paths."""

    def test_exact_normalized_match(self, tmp_path):
        """SUBSTANCE-FUEL1.PNG should match substance.fuel.1.dds."""
        cache_dir = tmp_path / "icons"
        cache_dir.mkdir(parents=True)
        game_dir = tmp_path / "game"

        items = [
            {"id": "^FUEL1", "icon": "SUBSTANCE-FUEL1.PNG", "type": "substance"},
        ]
        items_path = tmp_path / "items.json"
        items_path.write_text(json.dumps(items))

        dds_paths = [
            "textures/ui/frontend/icons/substances/substance.fuel.1.dds",
        ]

        extractor = IconExtractor(game_dir, cache_dir)
        icon_map = extractor.build_icon_map(items_path, dds_paths)

        assert "^FUEL1" in icon_map
        assert icon_map["^FUEL1"] == "textures/ui/frontend/icons/substances/substance.fuel.1.dds"

    def test_product_match(self, tmp_path):
        """PRODUCT-CASING.PNG should match product.casing.dds."""
        cache_dir = tmp_path / "icons"
        cache_dir.mkdir(parents=True)
        game_dir = tmp_path / "game"

        items = [
            {"id": "CASING", "icon": "PRODUCT-CASING.PNG", "type": "product"},
        ]
        items_path = tmp_path / "items.json"
        items_path.write_text(json.dumps(items))

        dds_paths = [
            "textures/ui/frontend/icons/products/product.casing.dds",
        ]

        extractor = IconExtractor(game_dir, cache_dir)
        icon_map = extractor.build_icon_map(items_path, dds_paths)

        assert "CASING" in icon_map

    def test_unmatched_item_not_in_map(self, tmp_path):
        """Items without matching DDS should not appear in the map."""
        cache_dir = tmp_path / "icons"
        cache_dir.mkdir(parents=True)
        game_dir = tmp_path / "game"

        items = [
            {"id": "UNKNOWN_ITEM", "icon": "NONEXISTENT.PNG", "type": "product"},
        ]
        items_path = tmp_path / "items.json"
        items_path.write_text(json.dumps(items))

        dds_paths = [
            "textures/ui/frontend/icons/products/product.casing.dds",
        ]

        extractor = IconExtractor(game_dir, cache_dir)
        icon_map = extractor.build_icon_map(items_path, dds_paths)

        assert "UNKNOWN_ITEM" not in icon_map

    def test_technology_match(self, tmp_path):
        """TECHNOLOGY-WPNLASER.PNG should match technology.wpnlaser.dds."""
        cache_dir = tmp_path / "icons"
        cache_dir.mkdir(parents=True)
        game_dir = tmp_path / "game"

        items = [
            {"id": "LASER", "icon": "TECHNOLOGY-WPNLASER.PNG", "type": "technology"},
        ]
        items_path = tmp_path / "items.json"
        items_path.write_text(json.dumps(items))

        dds_paths = [
            "textures/ui/frontend/icons/technology/technology.wpnlaser.dds",
        ]

        extractor = IconExtractor(game_dir, cache_dir)
        icon_map = extractor.build_icon_map(items_path, dds_paths)

        assert "LASER" in icon_map


class TestIconMapPersistence:
    """Icon map JSON save/load."""

    def test_save_and_load_icon_map(self, tmp_path):
        """save_icon_map + load_icon_map round-trips correctly."""
        cache_dir = tmp_path / "icons"
        cache_dir.mkdir(parents=True)
        game_dir = tmp_path / "game"

        extractor = IconExtractor(game_dir, cache_dir)

        original = {"^FUEL1": "textures/ui/frontend/icons/substances/substance.fuel.1.dds"}
        extractor.save_icon_map(original)

        loaded = extractor.load_icon_map()
        assert loaded == original

    def test_load_returns_empty_when_missing(self, tmp_path):
        """load_icon_map returns empty dict when no file exists."""
        cache_dir = tmp_path / "icons"
        cache_dir.mkdir(parents=True)
        game_dir = tmp_path / "game"

        extractor = IconExtractor(game_dir, cache_dir)
        assert extractor.load_icon_map() == {}
