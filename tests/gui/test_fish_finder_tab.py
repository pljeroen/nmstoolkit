"""Tests for Fish Finder tab."""

import pytest
from PySide6.QtWidgets import QApplication

from nmstoolkit.gui.tabs.fish_finder_tab import FishFinderTab, _FISH_BAIT_INFO


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _make_psd():
    return {
        "Stats": [
            {
                "Stats": [
                    {"StatID": "^FISH_KILLS", "IntValue": 42},
                    {"StatID": "^DISC_CRE_WATER", "IntValue": 7},
                ]
            }
        ],
    }


class TestFishFinderTab:
    def test_tab_creates(self, qapp):
        tab = FishFinderTab()
        assert tab is not None

    def test_has_bait_section(self, qapp):
        tab = FishFinderTab()
        # Should have bait info table
        assert tab._bait_table.rowCount() > 0

    def test_has_fish_items(self, qapp):
        tab = FishFinderTab()
        assert tab._fish_table.rowCount() > 0

    def test_set_data_shows_fish_stats(self, qapp):
        tab = FishFinderTab()
        psd = _make_psd()
        tab.set_data(psd)
        assert "42" in tab._fish_kills_label.text()

    def test_bait_info_has_entries(self):
        assert len(_FISH_BAIT_INFO) > 0
        for bait in _FISH_BAIT_INFO:
            assert "id" in bait
            assert "name" in bait
            assert "condition" in bait
