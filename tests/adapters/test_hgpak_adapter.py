"""Tests for HgpakAdapter — integration tests against real PAK files.

Tests: R-PAK-02, R-PAK-04, R-PAK-05.
Requires NMS game files via NMS_TEST_GAME_DIR env var.
"""

import os
from pathlib import Path

import pytest

_game_dir = os.environ.get("NMS_TEST_GAME_DIR", "")
GAME_DIR = Path(_game_dir) if _game_dir else Path("/nonexistent")
PAK_DIR = GAME_DIR / "GAMEDATA" / "PCBANKS"
GLOBALS_PAK = PAK_DIR / "NMSARC.globals.pak"

needs_game_files = pytest.mark.skipif(
    not GLOBALS_PAK.exists(),
    reason="NMS game files not available",
)


@needs_game_files
class TestHgpakAdapterOpen:
    """R-PAK-02, R-PAK-05: Open PAK files from Path or str."""

    def test_open_from_path(self):
        from nmstoolkit.adapters.hgpak_adapter import HgpakAdapter

        adapter = HgpakAdapter()
        adapter.open(GLOBALS_PAK)
        try:
            files = adapter.list_files()
            assert len(files) > 0
        finally:
            adapter.close()

    def test_open_from_str(self):
        from nmstoolkit.adapters.hgpak_adapter import HgpakAdapter

        adapter = HgpakAdapter()
        adapter.open(str(GLOBALS_PAK))
        try:
            files = adapter.list_files()
            assert len(files) > 0
        finally:
            adapter.close()

    def test_context_manager(self):
        from nmstoolkit.adapters.hgpak_adapter import HgpakAdapter

        with HgpakAdapter.from_path(GLOBALS_PAK) as reader:
            files = reader.list_files()
            assert len(files) > 0


@needs_game_files
class TestHgpakAdapterListFiles:
    """R-PAK-02: list_files returns non-manifest paths."""

    def test_lists_mbin_files(self):
        from nmstoolkit.adapters.hgpak_adapter import HgpakAdapter

        with HgpakAdapter.from_path(GLOBALS_PAK) as reader:
            files = reader.list_files()
            mbin_files = [f for f in files if f.endswith(".mbin")]
            assert len(mbin_files) > 0, "globals.pak should contain .mbin files"

    def test_no_manifest_in_listing(self):
        from nmstoolkit.adapters.hgpak_adapter import HgpakAdapter

        with HgpakAdapter.from_path(GLOBALS_PAK) as reader:
            files = reader.list_files()
            for f in files:
                assert not f.endswith(".manifest"), "Manifest should not appear in file listing"


@needs_game_files
class TestHgpakAdapterExtract:
    """R-PAK-02: Extract specific files."""

    def test_extract_specific_file(self):
        from nmstoolkit.adapters.hgpak_adapter import HgpakAdapter

        with HgpakAdapter.from_path(GLOBALS_PAK) as reader:
            files = reader.list_files()
            target = files[0]
            results = reader.extract(paths=[target])
            assert target in results
            assert len(results[target]) > 0

    def test_extract_returns_bytes(self):
        from nmstoolkit.adapters.hgpak_adapter import HgpakAdapter

        with HgpakAdapter.from_path(GLOBALS_PAK) as reader:
            files = reader.list_files()
            results = reader.extract(paths=[files[0]])
            for data in results.values():
                assert isinstance(data, bytes)

    def test_extract_multiple_files(self):
        from nmstoolkit.adapters.hgpak_adapter import HgpakAdapter

        with HgpakAdapter.from_path(GLOBALS_PAK) as reader:
            files = reader.list_files()
            targets = files[:3]
            results = reader.extract(paths=targets)
            assert len(results) == len(targets)
            for t in targets:
                assert t in results

    def test_extract_missing_path_omitted(self):
        from nmstoolkit.adapters.hgpak_adapter import HgpakAdapter

        with HgpakAdapter.from_path(GLOBALS_PAK) as reader:
            results = reader.extract(paths=["nonexistent/file.mbin"])
            assert len(results) == 0

    def test_extract_all(self):
        from nmstoolkit.adapters.hgpak_adapter import HgpakAdapter

        with HgpakAdapter.from_path(GLOBALS_PAK) as reader:
            files = reader.list_files()
            results = reader.extract()
            assert len(results) == len(files)


@needs_game_files
class TestHgpakAdapterGlobFilter:
    """R-PAK-04: Glob pattern filtering."""

    def test_glob_pattern(self):
        from nmstoolkit.adapters.hgpak_adapter import HgpakAdapter

        with HgpakAdapter.from_path(GLOBALS_PAK) as reader:
            results = reader.extract(pattern="*.global.mbin")
            assert len(results) > 0
            for path in results:
                assert path.endswith(".global.mbin")

    def test_glob_no_match(self):
        from nmstoolkit.adapters.hgpak_adapter import HgpakAdapter

        with HgpakAdapter.from_path(GLOBALS_PAK) as reader:
            results = reader.extract(pattern="*.xyz_nonexistent")
            assert len(results) == 0


@needs_game_files
class TestHgpakAdapterDataIntegrity:
    """Verify extracted data matches known MBIN characteristics."""

    def test_mbin_magic_bytes(self):
        """MBIN files start with 0xCCCCCCCCCCCCCCCC or 0xDDDDDDDDDDDDDDDD."""
        from nmstoolkit.adapters.hgpak_adapter import HgpakAdapter

        with HgpakAdapter.from_path(GLOBALS_PAK) as reader:
            files = reader.list_files()
            mbin_files = [f for f in files if f.endswith(".mbin")]
            results = reader.extract(paths=[mbin_files[0]])
            data = list(results.values())[0]
            magic = data[:8]
            assert magic in (
                b"\xcc" * 8,
                b"\xdd" * 8,
            ), f"Unexpected MBIN magic: {magic.hex()}"
