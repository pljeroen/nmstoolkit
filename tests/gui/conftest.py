"""Shared fixtures for GUI tests."""

import gc

import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture(autouse=True, scope="session")
def _disable_gc_for_shiboken():
    """Disable Python's cyclic GC for the GUI test session.

    PySide6/shiboken and hgpaktool C extensions crash when Python's cyclic
    GC fires during their operations (widget construction, PAK parsing in
    background threads). Disabling cyclic GC prevents all such crashes.
    Objects are still freed via reference counting; only cyclic garbage
    leaks, which is irrelevant for a test process.
    """
    gc.disable()
    yield
    gc.enable()


@pytest.fixture(autouse=True)
def _cleanup_qt_widgets():
    """Explicitly destroy test-created widgets via Qt's safe mechanism.

    Without cyclic GC, abandoned widgets would accumulate as cyclic garbage.
    Using deleteLater() + processEvents() cleans them up through Qt's own
    destruction path, which is safe with GC disabled.
    """
    app = QApplication.instance()
    before = set(app.topLevelWidgets()) if app else set()
    yield
    if app is not None:
        for widget in set(app.topLevelWidgets()) - before:
            widget.deleteLater()
        app.processEvents()
