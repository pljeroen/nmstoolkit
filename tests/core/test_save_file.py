"""Tests for SaveFile model."""

import json
from pathlib import Path

import pytest

from nmstoolkit.core.save_file import SaveFile


class TestSaveFileLoad:
    def test_load_from_real_save(self, real_save_path, key_map_path):
        sf = SaveFile.load(real_save_path, key_map_path)
        assert sf.version > 0
        assert sf.platform == "Win|Final"

    def test_load_exposes_readable_keys(self, real_save_path, key_map_path):
        sf = SaveFile.load(real_save_path, key_map_path)
        assert "Version" in sf.data
        assert "BaseContext" in sf.data

    def test_active_context(self, real_save_path, key_map_path):
        sf = SaveFile.load(real_save_path, key_map_path)
        assert sf.active_context in ("Main", "Expedition", "Season")


class TestSaveFileContextAccess:
    def test_base_context(self, real_save_path, key_map_path):
        sf = SaveFile.load(real_save_path, key_map_path)
        ctx = sf.base_context
        assert "PlayerStateData" in ctx
        assert "GameMode" in ctx

    def test_player_state_data(self, real_save_path, key_map_path):
        sf = SaveFile.load(real_save_path, key_map_path)
        psd = sf.player_state_data()
        assert len(psd) > 200  # 251 keys expected


class TestSaveFilePlayerData:
    def test_units(self, real_save_path, key_map_path):
        sf = SaveFile.load(real_save_path, key_map_path)
        psd = sf.player_state_data()
        assert "Units" in psd
        assert isinstance(psd["Units"], int)

    def test_ship_ownership(self, real_save_path, key_map_path):
        sf = SaveFile.load(real_save_path, key_map_path)
        psd = sf.player_state_data()
        assert "ShipOwnership" in psd
        assert isinstance(psd["ShipOwnership"], list)

    def test_inventory(self, real_save_path, key_map_path):
        sf = SaveFile.load(real_save_path, key_map_path)
        psd = sf.player_state_data()
        assert "Inventory" in psd


class TestSaveFileModify:
    def test_modify_and_save(self, real_save_path, key_map_path, tmp_path):
        sf = SaveFile.load(real_save_path, key_map_path)
        psd = sf.player_state_data()
        original_units = psd["Units"]
        psd["Units"] = 999999999

        out_path = tmp_path / "modified.hg"
        sf.save(out_path)

        sf2 = SaveFile.load(out_path, key_map_path)
        assert sf2.player_state_data()["Units"] == 999999999

    def test_roundtrip_preserves_structure(self, real_save_path, key_map_path, tmp_path):
        sf = SaveFile.load(real_save_path, key_map_path)
        out_path = tmp_path / "roundtrip.hg"
        sf.save(out_path)

        sf2 = SaveFile.load(out_path, key_map_path)
        assert sf.data == sf2.data


class TestSaveFileAccountData:
    def test_load_account_data(self, real_account_path, account_key_map_path):
        sf = SaveFile.load(real_account_path, account_key_map_path)
        assert sf.version > 0
        assert "UserSettingsData" in sf.data

    def test_account_data_no_contexts(self, real_account_path, account_key_map_path):
        sf = SaveFile.load(real_account_path, account_key_map_path)
        assert sf.base_context is None
        assert sf.active_context is None
