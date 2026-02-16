"""Tests for inventory grid context menu non-blocking behavior.

R-CTXMENU-01: Context menu uses popup() instead of exec() to avoid freezing.
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import inspect

import pytest
from PySide6.QtWidgets import QApplication

from nmstoolkit.gui.widgets.inventory_grid import InventoryGrid

_app = QApplication.instance() or QApplication([])


class TestContextMenuNonBlocking:
    """R-CTXMENU-01: Context menu should use popup() not exec()."""

    def test_show_context_menu_source_uses_popup(self):
        """_show_context_menu source code must contain popup() and not exec()."""
        source = inspect.getsource(InventoryGrid._show_context_menu)
        assert "menu.popup(" in source, "Expected menu.popup() call"
        assert "menu.exec(" not in source, "menu.exec() should not be used (causes freezes)"
