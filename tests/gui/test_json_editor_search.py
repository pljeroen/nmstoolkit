"""Tests for JSON editor search functionality.

R-JSEARCH-01: Ctrl+F opens find bar with search, navigation, and dismiss.
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QApplication, QLineEdit

from nmstoolkit.gui.tabs.json_editor_tab import JsonEditorTab

_app = QApplication.instance() or QApplication([])


class TestJsonEditorSearch:
    """R-JSEARCH-01: JSON editor has a search bar."""

    def test_search_bar_exists(self):
        """JsonEditorTab has a search bar widget."""
        tab = JsonEditorTab()
        assert hasattr(tab, "_search_bar")

    def test_search_bar_initially_hidden(self):
        """Search bar is hidden by default."""
        tab = JsonEditorTab()
        assert not tab._search_bar.isVisible()

    def test_search_bar_has_line_edit(self):
        """Search bar contains a QLineEdit."""
        tab = JsonEditorTab()
        assert hasattr(tab, "_search_input")
        assert isinstance(tab._search_input, QLineEdit)

    def test_show_search_bar(self):
        """Calling _show_search_bar makes it visible (not hidden)."""
        tab = JsonEditorTab()
        tab._show_search_bar()
        # In offscreen mode, isVisible() may return False because parent isn't shown.
        # Check that the widget is not explicitly hidden instead.
        assert not tab._search_bar.isHidden()

    def test_hide_search_bar(self):
        """Calling _hide_search_bar hides it."""
        tab = JsonEditorTab()
        tab._show_search_bar()
        tab._hide_search_bar()
        assert tab._search_bar.isHidden()

    def test_find_next_finds_text(self):
        """_find_next highlights matching text in the text pane."""
        tab = JsonEditorTab()
        tab.set_data({"hello": "world", "foo": "bar"})
        tab._search_input.setText("world")
        result = tab._find_next()
        assert result is True

    def test_find_next_no_match(self):
        """_find_next returns False when text is not found."""
        tab = JsonEditorTab()
        tab.set_data({"hello": "world"})
        tab._search_input.setText("zzzznotfound")
        result = tab._find_next()
        assert result is False

    def test_find_previous_method_exists(self):
        """_find_previous method exists and is callable."""
        tab = JsonEditorTab()
        assert callable(tab._find_previous)
