"""Tests for ExpeditionTab GUI widget.

Tests R-EXPED-04: Expedition tab displays season/milestone data correctly.
"""

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from PySide6.QtWidgets import QApplication

from nmstoolkit.gui.tabs.expedition_tab import ExpeditionTab


# Ensure QApplication exists for widget tests
_app = QApplication.instance() or QApplication([])


COMMON_STATE = {
    "SeasonData": {
        "SeasonId": 21,
        "SeasonNumber": 45,
        "SeasonName": "UI_SEASON_21_NAME",
        "FinalReward": "RS_S21_COMPLETE",
    },
    "SeasonState": {
        "MilestoneValues": [
            {"Name": "MS_WALK", "Value": 500, "RewardCollected": True},
            {"Name": "MS_SCAN", "Value": 3, "RewardCollected": False},
        ],
        "HasCollectedFinalReward": False,
    },
}

PSD = {
    "RedeemedSeasonRewards": ["RS_S1_COMPLETE", "RS_S5_COMPLETE"],
}


@pytest.fixture
def tab():
    return ExpeditionTab()


class TestExpeditionTab:
    def test_set_data_populates_season_info(self, tab):
        tab.set_data(PSD, common_state=COMMON_STATE)
        text = tab._season_info.text()
        assert "21" in text
        assert "45" in text

    def test_set_data_populates_milestones(self, tab):
        tab.set_data(PSD, common_state=COMMON_STATE)
        assert tab._milestone_table.rowCount() == 2
        assert tab._milestone_table.item(0, 0).text() == "MS_WALK"
        assert tab._milestone_table.item(0, 1).text() == "500"
        assert tab._milestone_table.item(0, 2).text() == "Yes"
        assert tab._milestone_table.item(1, 2).text() == "No"

    def test_set_data_populates_rewards(self, tab):
        tab.set_data(PSD, common_state=COMMON_STATE)
        assert tab._rewards_table.rowCount() == 2
        # Reward name is resolved to human-readable form
        assert tab._rewards_table.item(0, 0).text() == "Rs S1 Complete"

    def test_no_expedition_data(self, tab):
        tab.set_data({}, common_state={})
        assert "No active expedition" in tab._season_info.text()
        assert tab._milestone_table.rowCount() == 0
        assert tab._rewards_table.rowCount() == 0

    def test_final_reward_status(self, tab):
        tab.set_data(PSD, common_state=COMMON_STATE)
        assert "Not collected" in tab._final_reward_label.text()

    def test_final_reward_collected(self, tab):
        common = {
            "SeasonData": {"SeasonId": 1, "SeasonNumber": 1, "SeasonName": "S1", "FinalReward": "RS_S1"},
            "SeasonState": {"HasCollectedFinalReward": True, "MilestoneValues": []},
        }
        tab.set_data({}, common_state=common)
        assert "Collected" in tab._final_reward_label.text()


class TestExpeditionRewardFilter:
    """R-EXP-01: Dropdown selector to filter rewards by expedition."""

    def test_reward_filter_combo_exists(self, tab):
        assert hasattr(tab, "_reward_filter")

    def test_reward_filter_has_all_option(self, tab):
        assert tab._reward_filter.itemText(0) == "All"

    def test_reward_filter_filters_rewards(self, tab):
        psd = {
            "RedeemedSeasonRewards": [
                "^EXPD_POSTER06A",  # Expedition 6
                "^EXPD_BANNER03",   # Expedition 3
                "^EXPD_TITLE19",    # Expedition 19
            ],
        }
        tab.set_data(psd, common_state=COMMON_STATE)
        # All shown initially
        assert tab._rewards_table.rowCount() == 3

        # Filter to expedition 6
        idx = tab._reward_filter.findText("6")
        if idx >= 0:
            tab._reward_filter.setCurrentIndex(idx)
            assert tab._rewards_table.rowCount() == 1

    def test_all_filter_shows_everything(self, tab):
        psd = {
            "RedeemedSeasonRewards": [
                "^EXPD_POSTER06A",
                "^EXPD_BANNER03",
            ],
        }
        tab.set_data(psd, common_state=COMMON_STATE)
        tab._reward_filter.setCurrentIndex(0)  # "All"
        assert tab._rewards_table.rowCount() == 2


class TestUnlockAllRewards:
    """R-EXP-03, R-EXP-04: Unlock all rewards button."""

    def test_unlock_button_exists(self, tab):
        assert hasattr(tab, "_unlock_all_btn")

    def test_unlock_adds_missing_rewards(self, tab):
        psd = {
            "RedeemedSeasonRewards": ["^EXPD_POSTER06A"],
        }
        tab.set_data(psd, common_state=COMMON_STATE)
        initial_count = len(psd["RedeemedSeasonRewards"])
        tab._on_unlock_all()
        # Should have added more rewards
        assert len(psd["RedeemedSeasonRewards"]) > initial_count

    def test_unlock_no_duplicates(self, tab):
        psd = {
            "RedeemedSeasonRewards": ["^EXPD_POSTER06A"],
        }
        tab.set_data(psd, common_state=COMMON_STATE)
        tab._on_unlock_all()
        # No duplicates
        assert len(psd["RedeemedSeasonRewards"]) == len(set(psd["RedeemedSeasonRewards"]))
