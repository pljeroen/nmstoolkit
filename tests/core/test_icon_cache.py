"""Tests for icon cache.

Tests R-ICON-01 through R-ICON-05.
"""

import struct
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from nmstoolkit.core.icon_cache import IconCache


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_dds_bytes(width: int = 64, height: int = 64) -> bytes:
    """Create a minimal uncompressed DDS file (RGBA8)."""
    magic = b"DDS "

    # DDS_PIXELFORMAT (32 bytes)
    pf = struct.pack(
        "<8I",
        32,              # dwSize
        0x41,            # dwFlags (DDPF_RGB | DDPF_ALPHAPIXELS)
        0,               # dwFourCC
        32,              # dwRGBBitCount
        0x000000FF,      # dwRBitMask
        0x0000FF00,      # dwGBitMask
        0x00FF0000,      # dwBBitMask
        0xFF000000,      # dwABitMask
    )

    # DDS_HEADER (124 bytes)
    header = struct.pack("<7I", 124, 0x1007, height, width, width * 4, 0, 0)
    header += b"\x00" * 44  # dwReserved1[11]
    header += pf
    header += struct.pack("<5I", 0x1000, 0, 0, 0, 0)  # caps

    pixel_data = bytes([255, 128, 64, 255] * width * height)
    return magic + header + pixel_data


# ---------------------------------------------------------------------------
# R-ICON-01: IconCache creation and cache directory
# ---------------------------------------------------------------------------

class TestIconCacheCreation:
    """R-ICON-01: IconCache manages a cache directory."""

    def test_cache_dir_created(self, tmp_path):
        cache_dir = tmp_path / "icons"
        cache = IconCache(cache_dir)
        assert cache.cache_dir == cache_dir
        assert cache_dir.exists()

    def test_cache_dir_already_exists(self, tmp_path):
        cache_dir = tmp_path / "icons"
        cache_dir.mkdir()
        cache = IconCache(cache_dir)
        assert cache_dir.exists()


# ---------------------------------------------------------------------------
# R-ICON-02: Convert DDS bytes to cached PNG
# ---------------------------------------------------------------------------

class TestDdsConversion:
    """R-ICON-02: Convert DDS data to PNG thumbnail."""

    def test_convert_dds_to_png(self, tmp_path):
        cache = IconCache(tmp_path / "icons")
        dds_data = _make_dds_bytes(64, 64)
        dds_path = "TEXTURES/UI/FRONTEND/ICONS/PRODUCTS/CASING.DDS"

        result = cache.store_icon(dds_path, dds_data)

        assert result is not None
        assert result.exists()
        assert result.suffix == ".png"

        img = Image.open(result)
        assert img.size == (64, 64)

    def test_convert_large_dds_resized_to_thumbnail(self, tmp_path):
        cache = IconCache(tmp_path / "icons", thumbnail_size=32)
        dds_data = _make_dds_bytes(128, 128)
        dds_path = "TEXTURES/UI/ICONS/LARGE.DDS"

        result = cache.store_icon(dds_path, dds_data)
        img = Image.open(result)
        assert img.size == (32, 32)

    def test_invalid_dds_returns_none(self, tmp_path):
        cache = IconCache(tmp_path / "icons")
        result = cache.store_icon("bad.dds", b"not a dds file")
        assert result is None


# ---------------------------------------------------------------------------
# R-ICON-03: get_icon returns cached PNG path
# ---------------------------------------------------------------------------

class TestGetIcon:
    """R-ICON-03: get_icon checks cache first, returns Path or None."""

    def test_returns_none_when_not_cached(self, tmp_path):
        cache = IconCache(tmp_path / "icons")
        result = cache.get_icon("TEXTURES/UI/MISSING.DDS")
        assert result is None

    def test_returns_path_after_store(self, tmp_path):
        cache = IconCache(tmp_path / "icons")
        dds_data = _make_dds_bytes()
        dds_path = "TEXTURES/UI/FRONTEND/ICONS/TEST.DDS"
        cache.store_icon(dds_path, dds_data)

        result = cache.get_icon(dds_path)
        assert result is not None
        assert result.exists()


# ---------------------------------------------------------------------------
# R-ICON-04: Cache key derivation from DDS path
# ---------------------------------------------------------------------------

class TestCacheKey:
    """R-ICON-04: DDS paths are normalized to safe filenames."""

    def test_path_normalized(self, tmp_path):
        cache = IconCache(tmp_path / "icons")
        dds_data = _make_dds_bytes()
        result = cache.store_icon(
            "TEXTURES/UI/FRONTEND/ICONS/U4PRODUCTS/PRODUCT.CASING.DDS",
            dds_data,
        )
        # Should be a flat filename (no directory nesting), lowercase
        assert "/" not in result.name
        assert result.name.endswith(".png")

    def test_same_path_same_cache_file(self, tmp_path):
        cache = IconCache(tmp_path / "icons")
        dds_data = _make_dds_bytes()
        path = "TEXTURES/UI/TEST.DDS"
        r1 = cache.store_icon(path, dds_data)
        r2 = cache.store_icon(path, dds_data)
        assert r1 == r2


# ---------------------------------------------------------------------------
# R-ICON-05: build_cache batch extraction
# ---------------------------------------------------------------------------

class TestBuildCache:
    """R-ICON-05: Batch extract and cache icons from PAK."""

    def test_build_cache_stores_icons(self, tmp_path):
        cache = IconCache(tmp_path / "icons")

        icon_paths = [
            "textures/ui/icons/a.dds",
            "textures/ui/icons/b.dds",
        ]
        dds_data = _make_dds_bytes()
        extracted = {p: dds_data for p in icon_paths}

        mock_pak = MagicMock()
        mock_pak.__enter__ = MagicMock(return_value=mock_pak)
        mock_pak.__exit__ = MagicMock(return_value=False)
        mock_pak.extract.return_value = extracted

        with patch(
            "nmstoolkit.core.icon_cache.HgpakAdapter.from_path",
            return_value=mock_pak,
        ):
            count = cache.build_cache(Path("/fake/pak"), icon_paths)

        assert count == 2
        assert cache.get_icon("textures/ui/icons/a.dds") is not None
        assert cache.get_icon("textures/ui/icons/b.dds") is not None
