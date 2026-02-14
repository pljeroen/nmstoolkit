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
