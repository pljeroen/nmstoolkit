"""Tests for global cross-save vault.

R-VAULT-01: Ships, multitools, and companions can be saved to and loaded from
a persistent vault that works across different save files.
"""

import json
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

_app = QApplication.instance() or QApplication([])


def _make_ship(name="Test Ship"):
    return {
        "Name": name,
        "Resource": {"Filename": "YOURSHIP_FIGHTER", "Seed": "0x1234"},
        "Inventory": {
            "Slots": [],
            "Class": {"InventoryClass": "S"},
        },
        "Inventory_TechOnly": {"Slots": []},
        "Inventory_Cargo": {"Slots": []},
        "Seed": "0x1234",
    }


def _make_multitool(name="Test Multitool"):
    return {
        "Name": name,
        "Store": {
            "Slots": [],
            "Class": {"InventoryClass": "A"},
        },
        "Seed": "0xABCD",
        "Resource": {"Filename": "YOURWEAPON_RIFLE"},
    }


def _make_companion(name="Test Pet"):
    return {
        "CustomName": name,
        "CreatureID": "^LARGEBUTTERFLY",
        "CreatureSeed": "0x1111",
        "Trust": 0.5,
        "Traits": [],
    }


class TestVaultDir:
    """Vault directory follows frozen/dev pattern."""

    def test_vault_dir_created(self, tmp_path, monkeypatch):
        from nmstoolkit.gui import vault

        monkeypatch.setattr(vault, "_VAULT_BASE", tmp_path)
        d = vault.vault_dir("ships")
        assert d.exists()
        assert d.name == "ships"
        assert d.parent.name == "vault"


class TestVaultSaveLoad:
    """Save and load entities to/from vault."""

    def test_save_ship_to_vault(self, tmp_path, monkeypatch):
        from nmstoolkit.gui import vault

        monkeypatch.setattr(vault, "_VAULT_BASE", tmp_path)
        ship = _make_ship("My Fighter")
        vault.save_to_vault("ships", ship, "My Fighter")
        entries = vault.scan_vault("ships")
        assert len(entries) == 1
        assert entries[0][1] == "My Fighter"

    def test_load_ship_from_vault(self, tmp_path, monkeypatch):
        from nmstoolkit.gui import vault

        monkeypatch.setattr(vault, "_VAULT_BASE", tmp_path)
        ship = _make_ship("Stored Ship")
        vault.save_to_vault("ships", ship, "Stored Ship")
        entries = vault.scan_vault("ships")
        loaded = vault.load_from_vault(entries[0][0])
        assert loaded["Name"] == "Stored Ship"
        assert loaded["Inventory"]["Class"]["InventoryClass"] == "S"

    def test_delete_from_vault(self, tmp_path, monkeypatch):
        from nmstoolkit.gui import vault

        monkeypatch.setattr(vault, "_VAULT_BASE", tmp_path)
        vault.save_to_vault("ships", _make_ship(), "Doomed")
        entries = vault.scan_vault("ships")
        assert len(entries) == 1
        vault.delete_from_vault(entries[0][0])
        assert len(vault.scan_vault("ships")) == 0

    def test_multitool_vault(self, tmp_path, monkeypatch):
        from nmstoolkit.gui import vault

        monkeypatch.setattr(vault, "_VAULT_BASE", tmp_path)
        vault.save_to_vault("multitools", _make_multitool("Alien Rifle"), "Alien Rifle")
        entries = vault.scan_vault("multitools")
        assert len(entries) == 1
        loaded = vault.load_from_vault(entries[0][0])
        assert loaded["Name"] == "Alien Rifle"

    def test_companion_vault(self, tmp_path, monkeypatch):
        from nmstoolkit.gui import vault

        monkeypatch.setattr(vault, "_VAULT_BASE", tmp_path)
        vault.save_to_vault("companions", _make_companion("Fluffy"), "Fluffy")
        entries = vault.scan_vault("companions")
        assert len(entries) == 1
        loaded = vault.load_from_vault(entries[0][0])
        assert loaded["CustomName"] == "Fluffy"

    def test_vault_types_isolated(self, tmp_path, monkeypatch):
        """Ships vault doesn't see multitools."""
        from nmstoolkit.gui import vault

        monkeypatch.setattr(vault, "_VAULT_BASE", tmp_path)
        vault.save_to_vault("ships", _make_ship(), "Ship")
        vault.save_to_vault("multitools", _make_multitool(), "MT")
        assert len(vault.scan_vault("ships")) == 1
        assert len(vault.scan_vault("multitools")) == 1


class TestShipsTabVault:
    """Vault buttons on ships tab."""

    def test_vault_buttons_exist(self):
        from nmstoolkit.gui.tabs.ships_tab import ShipsTab

        tab = ShipsTab()
        assert hasattr(tab, "_vault_save_btn")
        assert hasattr(tab, "_vault_load_btn")

    def test_save_ship_to_vault(self, tmp_path, monkeypatch):
        from nmstoolkit.gui import vault
        from nmstoolkit.gui.tabs.ships_tab import ShipsTab

        monkeypatch.setattr(vault, "_VAULT_BASE", tmp_path)
        ship = _make_ship("Vaulted Ship")
        psd = {"ShipOwnership": [ship], "PrimaryShip": 0}
        tab = ShipsTab()
        tab.set_data(psd)
        tab._ship_list.setCurrentRow(0)
        tab._on_vault_save()
        entries = vault.scan_vault("ships")
        assert len(entries) == 1

    def test_load_ship_from_vault(self, tmp_path, monkeypatch):
        from nmstoolkit.gui import vault
        from nmstoolkit.gui.tabs.ships_tab import ShipsTab

        monkeypatch.setattr(vault, "_VAULT_BASE", tmp_path)
        vault.save_to_vault("ships", _make_ship("From Vault"), "From Vault")

        psd = {"ShipOwnership": [_make_ship("Existing")], "PrimaryShip": 0}
        tab = ShipsTab()
        tab.set_data(psd)
        tab._refresh_vault()
        tab._vault_list.setCurrentRow(0)
        tab._on_vault_load()
        assert len(psd["ShipOwnership"]) == 2
        assert psd["ShipOwnership"][-1]["Name"] == "From Vault"


class TestMultitoolsTabVault:
    """Vault buttons on multitools tab."""

    def test_vault_buttons_exist(self):
        from nmstoolkit.gui.tabs.multitools_tab import MultitoolsTab

        tab = MultitoolsTab()
        assert hasattr(tab, "_vault_save_btn")
        assert hasattr(tab, "_vault_load_btn")


class TestCompanionsTabVault:
    """Vault buttons on companions tab."""

    def test_vault_buttons_exist(self):
        from nmstoolkit.gui.tabs.companions_tab import CompanionsTab

        tab = CompanionsTab()
        assert hasattr(tab, "_vault_save_btn")
        assert hasattr(tab, "_vault_load_btn")
