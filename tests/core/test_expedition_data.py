"""Tests for expedition data extraction from save files.

Tests R-EXPED-02: Extract expedition progress from PlayerStateData.
Tests R-EXPED-03: GameCatalogue includes season data.
"""

import json

import pytest

from nmstoolkit.core.game_catalogue import GameCatalogue


# Minimal save structure with expedition data
SAVE_WITH_EXPEDITION = {
    "CommonStateData": {
        "SeasonData": {
            "SeasonId": 21,
            "SeasonNumber": 45,
            "SeasonName": "UI_SEASON_21_NAME",
        },
        "SeasonState": {
            "MilestoneValues": [
                {"Name": "MS_WALK_DISTANCE", "Value": 500, "RewardCollected": True},
                {"Name": "MS_SCAN_FLORA", "Value": 3, "RewardCollected": False},
            ],
            "PinnedStage": 1,
            "PinnedMilestone": 0,
            "HasCollectedFinalReward": False,
            "RedeemedSeasonRewards": ["RS_S21_STAGE1"],
        },
    },
    "BaseContext": {
        "PlayerStateData": {
            "StartingSeasonNumber": 21,
            "RedeemedSeasonRewards": ["RS_S1_COMPLETE", "RS_S5_COMPLETE"],
        },
    },
    "ExpeditionContext": {
        "GameMode": "Seasonal",
        "PlayerStateData": {
            "SeasonData": {
                "SeasonId": 21,
                "SeasonNumber": 45,
            },
        },
    },
}


class TestExpeditionExtraction:
    """R-EXPED-02: Extract expedition progress from save data."""

    def test_season_data_from_common_state(self):
        common = SAVE_WITH_EXPEDITION["CommonStateData"]
        season_data = common.get("SeasonData", {})
        assert season_data["SeasonNumber"] == 45
        assert season_data["SeasonName"] == "UI_SEASON_21_NAME"

    def test_season_state_milestones(self):
        common = SAVE_WITH_EXPEDITION["CommonStateData"]
        season_state = common.get("SeasonState", {})
        milestones = season_state.get("MilestoneValues", [])
        assert len(milestones) == 2
        assert milestones[0]["Name"] == "MS_WALK_DISTANCE"
        assert milestones[0]["RewardCollected"] is True

    def test_has_collected_final_reward(self):
        common = SAVE_WITH_EXPEDITION["CommonStateData"]
        state = common.get("SeasonState", {})
        assert state["HasCollectedFinalReward"] is False

    def test_redeemed_rewards_from_base_context(self):
        psd = SAVE_WITH_EXPEDITION["BaseContext"]["PlayerStateData"]
        redeemed = psd.get("RedeemedSeasonRewards", [])
        assert "RS_S1_COMPLETE" in redeemed
        assert "RS_S5_COMPLETE" in redeemed

    def test_expedition_context_exists(self):
        exp_ctx = SAVE_WITH_EXPEDITION.get("ExpeditionContext")
        assert exp_ctx is not None
        assert exp_ctx["GameMode"] == "Seasonal"

    def test_no_expedition_graceful(self):
        """Save without expedition data should not crash."""
        save = {"CommonStateData": {}, "BaseContext": {"PlayerStateData": {}}}
        common = save["CommonStateData"]
        assert common.get("SeasonData") is None
        assert common.get("SeasonState") is None


class TestGameCatalogueSeasons:
    """R-EXPED-03: GameCatalogue includes season data."""

    def test_catalogue_with_seasons(self):
        seasons = [
            {"season_name": "UI_SEASON_1_NAME", "season_number": 1, "display_number": 1,
             "final_reward": "RS_S1_COMPLETE"},
            {"season_name": "UI_SEASON_2_NAME", "season_number": 2, "display_number": 2,
             "final_reward": "RS_S2_COMPLETE"},
        ]
        cat = GameCatalogue(
            products=[], substances=[], technologies=[],
            locale={}, seasons=seasons,
        )
        assert len(cat.seasons) == 2

    def test_catalogue_seasons_default_empty(self):
        cat = GameCatalogue(
            products=[], substances=[], technologies=[],
            locale={},
        )
        assert cat.seasons == []

    def test_find_season_by_number(self):
        seasons = [
            {"season_name": "UI_SEASON_1_NAME", "season_number": 1, "final_reward": "RS_S1_COMPLETE"},
            {"season_name": "UI_SEASON_5_NAME", "season_number": 9, "final_reward": "RS_S5_COMPLETE"},
        ]
        cat = GameCatalogue(
            products=[], substances=[], technologies=[],
            locale={}, seasons=seasons,
        )
        found = cat.find_season(9)
        assert found is not None
        assert found["season_name"] == "UI_SEASON_5_NAME"

    def test_find_season_not_found(self):
        cat = GameCatalogue(
            products=[], substances=[], technologies=[],
            locale={}, seasons=[],
        )
        assert cat.find_season(99) is None

    def test_catalogue_json_roundtrip_with_seasons(self):
        seasons = [
            {"season_name": "UI_SEASON_1_NAME", "season_number": 1,
             "display_number": 1, "final_reward": "RS_S1_COMPLETE"},
        ]
        cat = GameCatalogue(
            products=[], substances=[], technologies=[],
            locale={}, seasons=seasons,
        )
        json_str = cat.to_json()
        restored = GameCatalogue.from_json(json_str)
        assert len(restored.seasons) == 1
        assert restored.seasons[0]["season_number"] == 1
