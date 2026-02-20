"""Tests for Freighter preview tab wiring and identity updates."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from nmstoolkit.gui.tabs.freighter_tab import FreighterTab
from nmstoolkit.gui.preview_support import PreviewLoadThread


def test_preview_tab_exists(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(FreighterTab, "_load_preview_meshes", lambda self, r: ([], "no preview"))
    tab = FreighterTab()
    labels = [tab._inv_tabs.tabText(i) for i in range(tab._inv_tabs.count())]
    assert "Preview" in labels
    assert "template-level" in tab._preview_fidelity.text().lower()


def test_preview_identity_updates_from_current_freighter(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(FreighterTab, "_load_preview_meshes", lambda self, r: ([], "no preview"))
    tab = FreighterTab()
    tab.set_data(
        {
            "CurrentFreighter": {
                "Seed": [True, "0xF00D"],
                "Filename": "MODELS/COMMON/SPACECRAFT/INDUSTRIAL/FRIGATE.SCENE.MBIN",
            },
            "FreighterInventory": {},
            "FreighterInventory_TechOnly": {},
            "FreighterInventory_Cargo": {"Slots": []},
        }
    )
    assert "0xF00D" in tab._preview_identity.text()
    assert "FRIGATE.SCENE.MBIN" in tab._preview_identity.text()


def test_freighter_has_async_preview_members(monkeypatch):
    """Freighter tab must have PreviewLoadThread async infrastructure."""
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(FreighterTab, "_load_preview_meshes", lambda self, r: ([], "no preview"))
    tab = FreighterTab()
    assert hasattr(tab, "_preview_thread"), "missing _preview_thread member"
    assert hasattr(tab, "_preview_request_id"), "missing _preview_request_id member"
    assert callable(getattr(tab, "_cancel_preview_thread", None)), "missing _cancel_preview_thread()"
    assert callable(getattr(tab, "_start_preview_load", None)), "missing _start_preview_load()"
    assert callable(getattr(tab, "_on_preview_loaded", None)), "missing _on_preview_loaded()"
