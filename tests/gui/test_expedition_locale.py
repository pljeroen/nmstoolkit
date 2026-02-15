"""Tests for expedition tab locale resolution and season name display.

R-EXPED-05: Season names resolve through locale, not shown as raw keys.
R-EXPED-06: Final reward names resolve through get_item_display_name.
"""

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from PySide6.QtWidgets import QApplication

from nmstoolkit.core.game_catalogue import GameCatalogue
from nmstoolkit.gui.widgets.inventory_grid import set_catalogue
from nmstoolkit.gui.tabs.expedition_tab import ExpeditionTab

_app = QApplication.instance() or QApplication([])


@pytest.fixture
def catalogue_with_seasons():
    return GameCatalogue(
        products=[],
        substances=[],
        technologies=[],
        locale={
            "UI_SEASON_19_NAME": "Corvette",
            "UI_SEASON_21_NAME": "Remnant",
        },
    )


@pytest.fixture(autouse=True)
def _reset_catalogue():
    yield
    set_catalogue(None)


COMMON_WITH_LOCALE_KEY = {
    "SeasonData": {
        "SeasonId": 19,
        "SeasonNumber": 37,
        "SeasonName": "^UI_SEASON_19_NAME",
        "FinalReward": "^TOKEN_CORVETTE",
    },
    "SeasonState": {
        "HasCollectedFinalReward": False,
        "MilestoneValues": [],
    },
}


class TestSeasonNameLocaleResolution:
    def test_season_name_resolves_locale_key(self, catalogue_with_seasons):
        """Season name ^UI_SEASON_19_NAME should display as 'Corvette'."""
        set_catalogue(catalogue_with_seasons)
        tab = ExpeditionTab()
        tab.set_data({}, common_state=COMMON_WITH_LOCALE_KEY)
        text = tab._season_info.text()
        assert "Corvette" in text
        assert "UI_SEASON_19_NAME" not in text

    def test_season_name_without_locale_shows_readable(self):
        """Without catalogue, raw locale key should still be cleaned up."""
        tab = ExpeditionTab()
        tab.set_data({}, common_state=COMMON_WITH_LOCALE_KEY)
        # Should at least not show the raw ^UI_SEASON_19_NAME with caret
        text = tab._season_info.text()
        assert "^" not in text

    def test_final_reward_resolves_through_display_name(self, catalogue_with_seasons):
        """Final reward should resolve through get_item_display_name."""
        set_catalogue(catalogue_with_seasons)
        tab = ExpeditionTab()
        tab.set_data({}, common_state=COMMON_WITH_LOCALE_KEY)
        text = tab._final_reward_label.text()
        # TOKEN_CORVETTE is in _REWARD_NAMES dict, should show "Corvette Token"
        assert "Corvette Token" in text

    def test_plain_season_name_unchanged(self, catalogue_with_seasons):
        """Non-locale-key season names pass through unchanged."""
        set_catalogue(catalogue_with_seasons)
        tab = ExpeditionTab()
        common = {
            "SeasonData": {
                "SeasonId": 1,
                "SeasonNumber": 1,
                "SeasonName": "Pioneers",
                "FinalReward": "RS_S1",
            },
            "SeasonState": {"HasCollectedFinalReward": True, "MilestoneValues": []},
        }
        tab.set_data({}, common_state=common)
        assert "Pioneers" in tab._season_info.text()
