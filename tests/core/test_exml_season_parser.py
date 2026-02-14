"""Tests for EXML season table parser.

Tests R-EXPED-01: parse_season_table extracts historical expedition data.
"""

import pytest

from nmstoolkit.core.exml_parser import parse_season_table


SEASON_TABLE_EXML = """\
<?xml version="1.0" encoding="utf-8"?>
<Data template="cGcHistoricalSeasonDataTable">
  <Property name="Table">
    <Property name="Table" value="GcHistoricalSeasonData" _index="0">
      <Property name="SeasonName" value="UI_SEASON_1_NAME" />
      <Property name="SeasonNameUpper" value="UI_SEASON_1_NAME_U" />
      <Property name="SeasonNumber" value="1" />
      <Property name="RemixNumber" value="0" />
      <Property name="DisplayNumber" value="1" />
      <Property name="MainIcon" value="TkTextureResource">
        <Property name="Filename" value="TEXTURES/UI/FRONTEND/ICONS/EXPEDITION/PATCH.EXPEDITION.1.DDS" />
      </Property>
      <Property name="Description" value="UI_EXPED1_MAIN_DESC" />
      <Property name="FinalReward" value="RS_S1_COMPLETE" />
      <Property name="UnlockedTitle" value="UI_PLAYER_TITLE_EXPD1" />
    </Property>
    <Property name="Table" value="GcHistoricalSeasonData" _index="1">
      <Property name="SeasonName" value="UI_SEASON_2_NAME" />
      <Property name="SeasonNameUpper" value="UI_SEASON_2_NAME_U" />
      <Property name="SeasonNumber" value="2" />
      <Property name="RemixNumber" value="0" />
      <Property name="DisplayNumber" value="2" />
      <Property name="MainIcon" value="TkTextureResource">
        <Property name="Filename" value="TEXTURES/UI/FRONTEND/ICONS/EXPEDITION/PATCH.EXPEDITION.2.DDS" />
      </Property>
      <Property name="Description" value="UI_EXPED2_MAIN_DESC" />
      <Property name="FinalReward" value="RS_S2_COMPLETE" />
      <Property name="UnlockedTitle" value="UI_PLAYER_TITLE_EXPD2B" />
    </Property>
    <Property name="Table" value="GcHistoricalSeasonData" _index="2">
      <Property name="SeasonName" value="UI_SEASON_5_NAME" />
      <Property name="SeasonNameUpper" value="UI_SEASON_5_NAME_U" />
      <Property name="SeasonNumber" value="9" />
      <Property name="RemixNumber" value="0" />
      <Property name="DisplayNumber" value="5" />
      <Property name="MainIcon" value="TkTextureResource">
        <Property name="Filename" value="TEXTURES/UI/FRONTEND/ICONS/EXPEDITION/PATCH.EXPEDITION.5.DDS" />
      </Property>
      <Property name="Description" value="UI_EXPED5_MAIN_DESC" />
      <Property name="FinalReward" value="RS_S5_COMPLETE" />
      <Property name="UnlockedTitle" value="UI_PLAYER_TITLE_EXPD5" />
    </Property>
  </Property>
</Data>"""


class TestParseSeasonTable:
    """R-EXPED-01: parse_season_table extracts historical expedition data."""

    def test_returns_list(self):
        result = parse_season_table(SEASON_TABLE_EXML)
        assert isinstance(result, list)

    def test_correct_count(self):
        result = parse_season_table(SEASON_TABLE_EXML)
        assert len(result) == 3

    def test_season_name(self):
        result = parse_season_table(SEASON_TABLE_EXML)
        assert result[0]["season_name"] == "UI_SEASON_1_NAME"
        assert result[1]["season_name"] == "UI_SEASON_2_NAME"

    def test_season_number(self):
        result = parse_season_table(SEASON_TABLE_EXML)
        assert result[0]["season_number"] == 1
        assert result[2]["season_number"] == 9  # non-sequential

    def test_display_number(self):
        result = parse_season_table(SEASON_TABLE_EXML)
        assert result[0]["display_number"] == 1
        assert result[2]["display_number"] == 5

    def test_remix_number(self):
        result = parse_season_table(SEASON_TABLE_EXML)
        assert result[0]["remix_number"] == 0

    def test_final_reward(self):
        result = parse_season_table(SEASON_TABLE_EXML)
        assert result[0]["final_reward"] == "RS_S1_COMPLETE"

    def test_unlocked_title(self):
        result = parse_season_table(SEASON_TABLE_EXML)
        assert result[0]["unlocked_title"] == "UI_PLAYER_TITLE_EXPD1"

    def test_description(self):
        result = parse_season_table(SEASON_TABLE_EXML)
        assert result[0]["description"] == "UI_EXPED1_MAIN_DESC"

    def test_icon_filename(self):
        result = parse_season_table(SEASON_TABLE_EXML)
        assert "PATCH.EXPEDITION.1.DDS" in result[0]["icon"]

    def test_empty_table(self):
        empty_exml = """\
<?xml version="1.0" encoding="utf-8"?>
<Data template="cGcHistoricalSeasonDataTable">
  <Property name="Table">
  </Property>
</Data>"""
        result = parse_season_table(empty_exml)
        assert result == []

    def test_bytes_input(self):
        result = parse_season_table(SEASON_TABLE_EXML.encode("utf-8"))
        assert len(result) == 3

    def test_resolve_locale_on_seasons(self):
        """Season names can be locale-resolved like other tables."""
        from nmstoolkit.core.exml_parser import resolve_locale

        seasons = parse_season_table(SEASON_TABLE_EXML)
        locale = {"UI_SEASON_1_NAME": "Pioneers", "UI_SEASON_2_NAME": "Beachhead"}
        resolved = resolve_locale(seasons, locale, "season_name")
        assert resolved[0]["display_name"] == "Pioneers"
        assert resolved[1]["display_name"] == "Beachhead"
        # Unresolved falls back to key
        assert resolved[2]["display_name"] == "UI_SEASON_5_NAME"
