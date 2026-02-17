"""Tests for external dependencies dialog.

Tests R-GUI-01 through R-GUI-05: ExternalDepsDialog, _external_tools_dir(),
_find_mbin_compiler() ExternalTools integration, download asset selection.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


# ---------------------------------------------------------------------------
# R-GUI-04: _external_tools_dir()
# ---------------------------------------------------------------------------

class TestExternalToolsDir:
    """R-GUI-04: _external_tools_dir returns correct path per environment."""

    def test_dev_mode_returns_user_data_dir(self, tmp_path):
        from nmstoolkit.gui.main_window import _external_tools_dir

        with patch.dict("os.environ", {"NMSTOOLKIT_DATA_DIR": str(tmp_path)}):
            result = _external_tools_dir()
        assert result == tmp_path / "ExternalTools"

    def test_frozen_mode_returns_exe_sibling(self, tmp_path):
        from nmstoolkit.gui.main_window import _external_tools_dir

        fake_exe = tmp_path / "app.exe"
        with patch.object(sys, "frozen", True, create=True), \
             patch.object(sys, "executable", str(fake_exe)):
            result = _external_tools_dir()
        assert result == tmp_path / "ExternalTools"

    def test_result_is_path(self):
        from nmstoolkit.gui.main_window import _external_tools_dir

        result = _external_tools_dir()
        assert isinstance(result, Path)
        assert result.name == "ExternalTools"


# ---------------------------------------------------------------------------
# R-GUI-05: _find_mbin_compiler prefers ExternalTools
# ---------------------------------------------------------------------------

class TestFindMbinCompilerExternalTools:
    """R-GUI-05: _find_mbin_compiler checks ExternalTools/MBINCompiler first."""

    def test_finds_in_external_tools_dir(self, tmp_path):
        from nmstoolkit.gui.main_window import MainWindow

        ext_dir = tmp_path / "ExternalTools" / "MBINCompiler"
        ext_dir.mkdir(parents=True)
        compiler = ext_dir / "MBINCompiler"
        compiler.touch()

        pak_dir = tmp_path / "PCBANKS"
        pak_dir.mkdir()

        with patch("nmstoolkit.gui.main_window._external_tools_dir", return_value=tmp_path / "ExternalTools"):
            result = MainWindow._find_mbin_compiler(pak_dir)
        assert result == compiler

    def test_external_tools_preferred_over_pak_dir(self, tmp_path):
        """ExternalTools location is checked before pak_dir locations."""
        from nmstoolkit.gui.main_window import MainWindow

        # Both locations have a compiler
        ext_dir = tmp_path / "ExternalTools" / "MBINCompiler"
        ext_dir.mkdir(parents=True)
        ext_compiler = ext_dir / "MBINCompiler"
        ext_compiler.touch()

        pak_dir = tmp_path / "PCBANKS"
        pak_dir.mkdir()
        pak_compiler = pak_dir / "MBINCompiler"
        pak_compiler.touch()

        with patch("nmstoolkit.gui.main_window._external_tools_dir", return_value=tmp_path / "ExternalTools"):
            result = MainWindow._find_mbin_compiler(pak_dir)
        assert result == ext_compiler

    def test_falls_back_to_other_locations_when_not_in_external_tools(self, tmp_path):
        from nmstoolkit.gui.main_window import MainWindow

        ext_dir = tmp_path / "ExternalTools"
        ext_dir.mkdir(parents=True)

        pak_dir = tmp_path / "PCBANKS"
        pak_dir.mkdir()
        pak_compiler = pak_dir / "MBINCompiler"
        pak_compiler.touch()

        with patch("nmstoolkit.gui.main_window._external_tools_dir", return_value=ext_dir):
            result = MainWindow._find_mbin_compiler(pak_dir)
        # Should find it somewhere (pak_dir or system), just not in ExternalTools
        assert result is not None
        assert "ExternalTools" not in str(result)


# ---------------------------------------------------------------------------
# R-GUI-03: Platform asset selection
# ---------------------------------------------------------------------------

class TestPlatformAssetSelection:
    """R-GUI-03: Download picks correct platform-specific assets."""

    def test_windows_assets(self):
        from nmstoolkit.gui.dialogs.external_deps_dialog import _platform_asset_names

        with patch("sys.platform", "win32"):
            names = _platform_asset_names()
        assert "MBINCompiler.exe" in names
        assert "libMBIN.dll" in names

    def test_linux_assets(self):
        from nmstoolkit.gui.dialogs.external_deps_dialog import _platform_asset_names

        with patch("sys.platform", "linux"):
            names = _platform_asset_names()
        assert "MBINCompiler-linux" in names
        assert "libMBIN-linux.so" in names


# ---------------------------------------------------------------------------
# R-GUI-02: Dialog status detection
# ---------------------------------------------------------------------------

class TestDialogStatusDetection:
    """R-GUI-02: Dialog detects MBINCompiler found/not found."""

    def test_status_found(self, tmp_path):
        from nmstoolkit.gui.dialogs.external_deps_dialog import detect_mbin_status

        compiler = tmp_path / "MBINCompiler"
        compiler.touch()

        status = detect_mbin_status(search_dirs=[tmp_path])
        assert status["found"] is True
        assert status["path"] == compiler

    def test_status_not_found(self, tmp_path):
        from nmstoolkit.gui.dialogs.external_deps_dialog import detect_mbin_status

        status = detect_mbin_status(search_dirs=[tmp_path])
        assert status["found"] is False
        assert status["path"] is None

    def test_status_found_exe_variant(self, tmp_path):
        from nmstoolkit.gui.dialogs.external_deps_dialog import detect_mbin_status

        compiler = tmp_path / "MBINCompiler.exe"
        compiler.touch()

        status = detect_mbin_status(search_dirs=[tmp_path])
        assert status["found"] is True
        assert status["path"] == compiler


# ---------------------------------------------------------------------------
# R-GUI-01: Dialog creation
# ---------------------------------------------------------------------------

class TestDialogCreation:
    """R-GUI-01: ExternalDepsDialog can be created."""

    def test_create_dialog(self, qapp):
        from nmstoolkit.gui.dialogs.external_deps_dialog import ExternalDepsDialog

        dialog = ExternalDepsDialog(external_tools_dir=Path("/tmp/fake"))
        assert dialog is not None
        assert dialog.windowTitle() == "External Dependencies"

    def test_dialog_has_close_button(self, qapp):
        from nmstoolkit.gui.dialogs.external_deps_dialog import ExternalDepsDialog

        dialog = ExternalDepsDialog(external_tools_dir=Path("/tmp/fake"))
        assert dialog._close_btn is not None


# ---------------------------------------------------------------------------
# R-GUI-03: Download URL extraction
# ---------------------------------------------------------------------------

class TestDownloadUrlExtraction:
    """R-GUI-03: Extract download URLs from GitHub API response."""

    def test_extract_asset_urls(self):
        from nmstoolkit.gui.dialogs.external_deps_dialog import _extract_asset_urls

        api_response = {
            "tag_name": "v5.0.0",
            "assets": [
                {"name": "MBINCompiler.exe", "browser_download_url": "https://example.com/MBINCompiler.exe"},
                {"name": "libMBIN.dll", "browser_download_url": "https://example.com/libMBIN.dll"},
                {"name": "MBINCompiler-linux", "browser_download_url": "https://example.com/MBINCompiler-linux"},
                {"name": "libMBIN-linux.so", "browser_download_url": "https://example.com/libMBIN-linux.so"},
                {"name": "README.md", "browser_download_url": "https://example.com/README.md"},
            ],
        }
        wanted = ["MBINCompiler.exe", "libMBIN.dll"]
        urls = _extract_asset_urls(api_response, wanted)

        assert len(urls) == 2
        assert urls["MBINCompiler.exe"] == "https://example.com/MBINCompiler.exe"
        assert urls["libMBIN.dll"] == "https://example.com/libMBIN.dll"

    def test_extract_returns_empty_for_missing(self):
        from nmstoolkit.gui.dialogs.external_deps_dialog import _extract_asset_urls

        api_response = {"tag_name": "v1.0", "assets": []}
        urls = _extract_asset_urls(api_response, ["MBINCompiler.exe"])
        assert len(urls) == 0

    def test_extract_version_from_response(self):
        from nmstoolkit.gui.dialogs.external_deps_dialog import _extract_version

        api_response = {"tag_name": "v5.0.0", "assets": []}
        assert _extract_version(api_response) == "v5.0.0"
