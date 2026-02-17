"""Tests for MBINCompiler auto-download prompts in MainWindow.

R-GUI-01: _on_extract_icons() checks for MBINCompiler and offers download.
R-GUI-02: _auto_load_icons() prompts on first run with no cache.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtWidgets import QApplication, QMessageBox


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _make_window(qapp):
    """Create a MainWindow with all heavy I/O mocked out."""
    with patch("nmstoolkit.gui.main_window.MainWindow._auto_load_icons"), \
         patch("nmstoolkit.gui.main_window.MainWindow._build_ui"), \
         patch("nmstoolkit.gui.main_window.MainWindow._build_menu"), \
         patch("nmstoolkit.gui.main_window.MainWindow._scan_saves"):
        from nmstoolkit.gui.main_window import MainWindow
        win = MainWindow.__new__(MainWindow)
        win._save_file = None
        win._save_path = None
        win._account_file = None
        win._account_path = None
        win._profiles = []
        win._recipe_finder_tab = MagicMock()
        from PySide6.QtCore import QSettings
        win._settings = QSettings("NMSToolkit", "NMSToolkit-Test")
        return win


# ---------------------------------------------------------------
# R-GUI-01: _on_extract_icons offers MBINCompiler download
# ---------------------------------------------------------------

class TestExtractIconsMbinPrompt:
    """Verify _on_extract_icons checks compiler before extraction and offers download."""

    def test_no_compiler_shows_question(self, qapp, tmp_path):
        """When MBINCompiler is missing, user is asked to download it."""
        win = _make_window(qapp)
        cache_dir = tmp_path / "icons"
        cache_dir.mkdir()

        # Create a fake pak_dir that "exists"
        pak_dir = tmp_path / "GAMEDATA" / "PCBANKS"
        pak_dir.mkdir(parents=True)

        with patch("nmstoolkit.gui.main_window.QFileDialog.getExistingDirectory",
                    return_value=str(tmp_path)), \
             patch("nmstoolkit.gui.main_window._user_cache_dir", return_value=cache_dir), \
             patch("nmstoolkit.gui.main_window.MainWindow._find_mbin_compiler",
                    return_value=None), \
             patch("nmstoolkit.gui.main_window.QMessageBox.question",
                    return_value=QMessageBox.StandardButton.No) as mock_q, \
             patch("nmstoolkit.gui.main_window.IconExtractor") as mock_ext_cls, \
             patch("nmstoolkit.gui.main_window.QProgressDialog"), \
             patch("nmstoolkit.gui.main_window.QApplication.processEvents"), \
             patch("nmstoolkit.gui.main_window.IconCache"), \
             patch("nmstoolkit.gui.main_window.QMessageBox.information"), \
             patch("nmstoolkit.gui.main_window.QMessageBox.warning"):
            mock_ext = MagicMock()
            mock_ext.extract_all_icons.return_value = 10
            mock_ext.build_icon_map.return_value = {"ITEM1": "path.dds"}
            mock_ext.load_icon_map.return_value = {}
            mock_ext_cls.return_value = mock_ext

            win._on_extract_icons()

            # Should prompt user about downloading MBINCompiler
            mock_q.assert_called_once()

    def test_no_compiler_yes_opens_deps_dialog(self, qapp, tmp_path):
        """When user answers Yes, ExternalDepsDialog is opened."""
        win = _make_window(qapp)
        cache_dir = tmp_path / "icons"
        cache_dir.mkdir()

        pak_dir = tmp_path / "GAMEDATA" / "PCBANKS"
        pak_dir.mkdir(parents=True)

        mock_dialog = MagicMock()

        with patch("nmstoolkit.gui.main_window.QFileDialog.getExistingDirectory",
                    return_value=str(tmp_path)), \
             patch("nmstoolkit.gui.main_window._user_cache_dir", return_value=cache_dir), \
             patch("nmstoolkit.gui.main_window.MainWindow._find_mbin_compiler",
                    return_value=None), \
             patch("nmstoolkit.gui.main_window.QMessageBox.question",
                    return_value=QMessageBox.StandardButton.Yes), \
             patch("nmstoolkit.gui.dialogs.external_deps_dialog.ExternalDepsDialog",
                    return_value=mock_dialog, create=True) as mock_cls, \
             patch("nmstoolkit.gui.main_window.IconExtractor") as mock_ext_cls, \
             patch("nmstoolkit.gui.main_window.QProgressDialog"), \
             patch("nmstoolkit.gui.main_window.QApplication.processEvents"), \
             patch("nmstoolkit.gui.main_window.IconCache"), \
             patch("nmstoolkit.gui.main_window.QMessageBox.information"), \
             patch("nmstoolkit.gui.main_window.QMessageBox.warning"):
            mock_ext = MagicMock()
            mock_ext.extract_all_icons.return_value = 10
            mock_ext.build_icon_map.return_value = {"ITEM1": "path.dds"}
            mock_ext.load_icon_map.return_value = {}
            mock_ext_cls.return_value = mock_ext

            win._on_extract_icons()

            # ExternalDepsDialog should have been opened
            mock_dialog.exec.assert_called_once()

    def test_compiler_present_no_prompt(self, qapp, tmp_path):
        """When MBINCompiler is found, no download prompt is shown."""
        win = _make_window(qapp)
        cache_dir = tmp_path / "icons"
        cache_dir.mkdir()

        pak_dir = tmp_path / "GAMEDATA" / "PCBANKS"
        pak_dir.mkdir(parents=True)

        with patch("nmstoolkit.gui.main_window.QFileDialog.getExistingDirectory",
                    return_value=str(tmp_path)), \
             patch("nmstoolkit.gui.main_window._user_cache_dir", return_value=cache_dir), \
             patch("nmstoolkit.gui.main_window.MainWindow._find_mbin_compiler",
                    return_value=Path("/fake/MBINCompiler.exe")), \
             patch("nmstoolkit.gui.main_window.QMessageBox.question") as mock_q, \
             patch("nmstoolkit.gui.main_window.IconExtractor") as mock_ext_cls, \
             patch("nmstoolkit.gui.main_window.QProgressDialog"), \
             patch("nmstoolkit.gui.main_window.QApplication.processEvents"), \
             patch("nmstoolkit.gui.main_window.IconCache"), \
             patch("nmstoolkit.gui.main_window.QMessageBox.information"), \
             patch("nmstoolkit.gui.main_window.QMessageBox.warning"):
            mock_ext = MagicMock()
            mock_ext.extract_all_icons.return_value = 10
            mock_ext.build_icon_map.return_value = {}
            mock_ext.load_icon_map.return_value = {}
            mock_ext_cls.return_value = mock_ext

            win._on_extract_icons()

            # No download prompt when compiler is already present
            mock_q.assert_not_called()


# ---------------------------------------------------------------
# R-GUI-02: _auto_load_icons prompts on first run
# ---------------------------------------------------------------

class TestAutoLoadIconsFirstRun:
    """Verify _auto_load_icons prompts when no cached data exists."""

    def test_no_cache_shows_prompt(self, qapp, tmp_path):
        """When no game_catalogue.json and no icon_map.json, user is prompted."""
        win = _make_window(qapp)
        cache_dir = tmp_path / "icons"
        cache_dir.mkdir()
        # Ensure no cache files exist
        assert not (cache_dir / "game_catalogue.json").exists()
        assert not (cache_dir / "icon_map.json").exists()

        with patch("nmstoolkit.gui.main_window._user_cache_dir", return_value=cache_dir), \
             patch("nmstoolkit.gui.main_window.DATA_DIR", tmp_path / "nodata"), \
             patch("nmstoolkit.gui.main_window.QMessageBox.question",
                    return_value=QMessageBox.StandardButton.No) as mock_q:
            win._auto_load_icons()

        mock_q.assert_called_once()

    def test_no_cache_yes_triggers_extract(self, qapp, tmp_path):
        """When user answers Yes to first-run prompt, _on_extract_icons is called."""
        win = _make_window(qapp)
        cache_dir = tmp_path / "icons"
        cache_dir.mkdir()

        with patch("nmstoolkit.gui.main_window._user_cache_dir", return_value=cache_dir), \
             patch("nmstoolkit.gui.main_window.DATA_DIR", tmp_path / "nodata"), \
             patch("nmstoolkit.gui.main_window.QMessageBox.question",
                    return_value=QMessageBox.StandardButton.Yes), \
             patch.object(win, "_on_extract_icons") as mock_extract:
            win._auto_load_icons()

        mock_extract.assert_called_once()

    def test_catalogue_exists_no_prompt(self, qapp, tmp_path):
        """When game_catalogue.json exists, no first-run prompt is shown."""
        win = _make_window(qapp)
        cache_dir = tmp_path / "icons"
        cache_dir.mkdir()
        (cache_dir / "game_catalogue.json").write_text("{}")

        with patch("nmstoolkit.gui.main_window._user_cache_dir", return_value=cache_dir), \
             patch("nmstoolkit.gui.main_window.DATA_DIR", tmp_path / "nodata"), \
             patch("nmstoolkit.gui.main_window.QMessageBox.question") as mock_q, \
             patch("nmstoolkit.core.game_catalogue.GameCatalogue.from_json",
                    side_effect=Exception("skip")):
            win._auto_load_icons()

        mock_q.assert_not_called()

    def test_icon_map_exists_no_prompt(self, qapp, tmp_path):
        """When icon_map.json exists (but not catalogue), no first-run prompt."""
        win = _make_window(qapp)
        cache_dir = tmp_path / "icons"
        cache_dir.mkdir()
        (cache_dir / "icon_map.json").write_text("{}")

        with patch("nmstoolkit.gui.main_window._user_cache_dir", return_value=cache_dir), \
             patch("nmstoolkit.gui.main_window.DATA_DIR", tmp_path / "nodata"), \
             patch("nmstoolkit.gui.main_window.QMessageBox.question") as mock_q:
            win._auto_load_icons()

        mock_q.assert_not_called()
