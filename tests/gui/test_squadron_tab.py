"""Tests for squadron tab.

R-SQUAD-01: Squadron pilot ship selectable from player's owned ships.
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

_app = QApplication.instance() or QApplication([])


def _make_pilot(race_filename="NPCGEK", rank=2, ship_filename="FIGHTER_PROC.SCENE.MBIN",
                npc_seed="0xABC", ship_seed="0xDEF"):
    return {
        "NPCResource": {"Filename": race_filename, "Seed": npc_seed},
        "ShipResource": {"Filename": ship_filename, "Seed": ship_seed},
        "PilotRank": rank,
    }


def _make_player_ship(name="My Ship", filename="MODELS/COMMON/SPACECRAFT/FIGHTERS/FIGHTER_PROC.SCENE.MBIN"):
    return {
        "Name": name,
        "Resource": {"Filename": filename},
        "Seed": "0x1234",
        "Inventory": {"Slots": [], "ValidSlotIndices": [], "Class": {"InventoryClass": "A"},
                      "Width": 10, "Height": 5},
        "Inventory_TechOnly": {"Slots": [], "ValidSlotIndices": [], "Width": 10, "Height": 6},
        "Inventory_Cargo": {"Slots": [], "ValidSlotIndices": [], "Width": 8, "Height": 5},
    }


class TestSquadronShipSelector:
    """R-SQUAD-01: Ship selectable from player's owned ships."""

    def test_ship_combo_exists(self):
        from nmstoolkit.gui.tabs.squadron_tab import SquadronTab

        tab = SquadronTab()
        assert hasattr(tab, "_ship_combo")

    def test_ship_combo_populated_with_player_ships(self):
        from nmstoolkit.gui.tabs.squadron_tab import SquadronTab

        psd = {
            "SquadronPilots": [_make_pilot()],
            "SquadronUnlockedPilotSlots": [0],
            "ShipOwnership": [
                _make_player_ship("Alpha Fighter"),
                _make_player_ship("Beta Explorer", "MODELS/COMMON/SPACECRAFT/SCIENTIFIC/SCIENTIFIC_PROC.SCENE.MBIN"),
            ],
        }
        tab = SquadronTab()
        tab.set_data(psd)
        tab._list.setCurrentRow(0)
        # Ship combo should list player ships
        assert tab._ship_combo.count() >= 2
        texts = [tab._ship_combo.itemText(i) for i in range(tab._ship_combo.count())]
        assert any("Alpha" in t for t in texts)
        assert any("Beta" in t for t in texts)

    def test_selecting_ship_updates_pilot(self):
        """Selecting a ship from the dropdown should update the pilot's ShipResource."""
        from nmstoolkit.gui.tabs.squadron_tab import SquadronTab

        pilot = _make_pilot()
        psd = {
            "SquadronPilots": [pilot],
            "SquadronUnlockedPilotSlots": [0],
            "ShipOwnership": [
                _make_player_ship("Alpha Fighter", "FIGHTER.SCENE.MBIN"),
                _make_player_ship("Beta Explorer", "SCIENTIFIC.SCENE.MBIN"),
            ],
        }
        tab = SquadronTab()
        tab.set_data(psd)
        tab._list.setCurrentRow(0)
        # Select second ship
        tab._ship_combo.setCurrentIndex(1)
        # Pilot's ship resource should be updated
        assert "SCIENTIFIC" in pilot["ShipResource"]["Filename"]


class TestSquadronTabBasics:
    """Basic squadron tab functionality."""

    def test_tab_creates(self):
        from nmstoolkit.gui.tabs.squadron_tab import SquadronTab

        tab = SquadronTab()
        assert tab is not None

    def test_empty_data(self):
        from nmstoolkit.gui.tabs.squadron_tab import SquadronTab

        tab = SquadronTab()
        tab.set_data({"SquadronPilots": [], "SquadronUnlockedPilotSlots": []})
        assert tab._list.count() == 0
