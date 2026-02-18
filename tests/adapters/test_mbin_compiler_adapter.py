"""Tests for MbinCompilerAdapter — integration tests with real MBINCompiler.

Tests R-PIPE-01: Convert MBIN bytes to EXML string.
Requires MBINCompiler binary and NMS game files.
"""

import os
from pathlib import Path

import pytest

_mbin_compiler = os.environ.get("NMS_TEST_MBIN_COMPILER", "")
MBIN_COMPILER = Path(_mbin_compiler) if _mbin_compiler else Path("/nonexistent")
_game_dir = os.environ.get("NMS_TEST_GAME_DIR", "")
GAME_DIR = Path(_game_dir) if _game_dir else Path("/nonexistent")
PAK_DIR = GAME_DIR / "GAMEDATA" / "PCBANKS"

needs_mbin_compiler = pytest.mark.skipif(
    not MBIN_COMPILER.exists(),
    reason="MBINCompiler not available",
)

needs_game_files = pytest.mark.skipif(
    not PAK_DIR.exists(),
    reason="NMS game files not available",
)


@needs_mbin_compiler
@needs_game_files
class TestMbinCompilerAdapter:
    """R-PIPE-01: Convert MBIN bytes to EXML."""

    def test_convert_mbin_to_exml(self):
        from nmstoolkit.adapters.hgpak_adapter import HgpakAdapter
        from nmstoolkit.adapters.mbin_compiler_adapter import MbinCompilerAdapter

        # Extract a small MBIN
        with HgpakAdapter.from_path(PAK_DIR / "NMSARC.Precache.pak") as reader:
            results = reader.extract(
                paths=["metadata/reality/tables/historicalseasondatatable.mbin"]
            )
            mbin_data = list(results.values())[0]

        converter = MbinCompilerAdapter(MBIN_COMPILER)
        exml = converter.convert(mbin_data)
        assert isinstance(exml, str)
        assert "cGcHistoricalSeasonDataTable" in exml
        assert "<Property" in exml

    def test_convert_returns_parseable_exml(self):
        from nmstoolkit.adapters.hgpak_adapter import HgpakAdapter
        from nmstoolkit.adapters.mbin_compiler_adapter import MbinCompilerAdapter
        from nmstoolkit.core.exml_parser import parse_exml

        with HgpakAdapter.from_path(PAK_DIR / "NMSARC.Precache.pak") as reader:
            results = reader.extract(
                paths=["metadata/reality/tables/historicalseasondatatable.mbin"]
            )
            mbin_data = list(results.values())[0]

        converter = MbinCompilerAdapter(MBIN_COMPILER)
        exml = converter.convert(mbin_data)
        parsed = parse_exml(exml)
        assert parsed["template"] == "cGcHistoricalSeasonDataTable"

    def test_convert_batch(self):
        from nmstoolkit.adapters.hgpak_adapter import HgpakAdapter
        from nmstoolkit.adapters.mbin_compiler_adapter import MbinCompilerAdapter

        with HgpakAdapter.from_path(PAK_DIR / "NMSARC.Precache.pak") as reader:
            results = reader.extract(paths=[
                "metadata/reality/tables/historicalseasondatatable.mbin",
                "metadata/reality/tables/nms_reality_gcsubstancetable.mbin",
            ])

        converter = MbinCompilerAdapter(MBIN_COMPILER)
        converted = converter.convert_batch(results)
        assert len(converted) == 2
        for path, exml in converted.items():
            assert "<Data" in exml


@needs_mbin_compiler
@needs_game_files
class TestMbinConverterPort:
    """Port conformance: MbinCompilerAdapter satisfies MbinConverter Protocol."""

    def test_structural_conformance(self):
        from nmstoolkit.adapters.mbin_compiler_adapter import MbinCompilerAdapter
        from nmstoolkit.ports.mbin_converter import MbinConverter

        adapter: MbinConverter = MbinCompilerAdapter(MBIN_COMPILER)
        assert hasattr(adapter, "convert")
        assert hasattr(adapter, "convert_batch")
