"""Cargo tab visibility rules for inventory editors."""

import os

import pytest
from PySide6.QtWidgets import QApplication

from nmstoolkit.gui.tabs.corvette_tab import CorvetteTab
from nmstoolkit.gui.tabs.exosuit_tab import ExosuitTab
from nmstoolkit.gui.tabs.freighter_tab import FreighterTab
from nmstoolkit.gui.tabs.ships_tab import ShipsTab
from nmstoolkit.gui.tabs.vehicles_tab import VehiclesTab

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _cargo(with_data: bool) -> dict:
    if with_data:
        return {
            "Slots": [{"Id": "^ITEM", "Index": {"X": 0, "Y": 0}}],
            "ValidSlotIndices": [{"X": 0, "Y": 0}],
            "Width": 8,
            "Height": 5,
        }
    return {"Slots": [], "ValidSlotIndices": [], "Width": 8, "Height": 5}


def test_exosuit_hides_cargo_tab_when_empty(qapp):
    tab = ExosuitTab()
    tab.set_data(
        {
            "Units": 0,
            "Nanites": 0,
            "Specials": 0,
            "Health": 100,
            "Shield": 50,
            "Energy": 50,
            "Inventory": {},
            "Inventory_TechOnly": {},
            "Inventory_Cargo": _cargo(False),
        }
    )
    assert not tab._inv_tabs.isTabVisible(tab._cargo_tab_index)


def test_exosuit_hides_cargo_tab_for_structure_only_inventory(qapp):
    tab = ExosuitTab()
    tab.set_data(
        {
            "Units": 0,
            "Nanites": 0,
            "Specials": 0,
            "Health": 100,
            "Shield": 50,
            "Energy": 50,
            "Inventory": {},
            "Inventory_TechOnly": {},
            "Inventory_Cargo": {
                "Slots": [{"Id": "", "Index": {"X": 0, "Y": 0}}],
                "ValidSlotIndices": [{"X": 0, "Y": 0}],
                "Width": 8,
                "Height": 5,
            },
        }
    )
    assert not tab._inv_tabs.isTabVisible(tab._cargo_tab_index)


def test_exosuit_shows_cargo_tab_when_present(qapp):
    tab = ExosuitTab()
    tab.set_data(
        {
            "Units": 0,
            "Nanites": 0,
            "Specials": 0,
            "Health": 100,
            "Shield": 50,
            "Energy": 50,
            "Inventory": {},
            "Inventory_TechOnly": {},
            "Inventory_Cargo": _cargo(True),
        }
    )
    assert tab._inv_tabs.isTabVisible(tab._cargo_tab_index)


def test_ships_hides_cargo_tab_when_empty(qapp):
    tab = ShipsTab()
    tab.set_data(
        {
            "ShipOwnership": [
                {
                    "Name": "Test",
                    "Resource": {"Filename": "FIGHTER_PROC.SCENE.MBIN"},
                    "Inventory": {"Class": {"InventoryClass": "A"}, "Slots": []},
                    "Inventory_TechOnly": {"Slots": []},
                    "Inventory_Cargo": _cargo(False),
                }
            ]
        }
    )
    assert not tab._inv_tabs.isTabVisible(tab._cargo_tab_index)


def test_ships_shows_cargo_tab_when_present(qapp):
    tab = ShipsTab()
    tab.set_data(
        {
            "ShipOwnership": [
                {
                    "Name": "Test",
                    "Resource": {"Filename": "FIGHTER_PROC.SCENE.MBIN"},
                    "Inventory": {"Class": {"InventoryClass": "A"}, "Slots": []},
                    "Inventory_TechOnly": {"Slots": []},
                    "Inventory_Cargo": _cargo(True),
                }
            ]
        }
    )
    assert tab._inv_tabs.isTabVisible(tab._cargo_tab_index)


def test_freighter_hides_cargo_tab_when_empty(qapp):
    tab = FreighterTab()
    tab.set_data({"FreighterInventory": {}, "FreighterInventory_Cargo": _cargo(False)})
    assert not tab._inv_tabs.isTabVisible(tab._cargo_tab_index)


def test_freighter_shows_cargo_tab_when_present(qapp):
    tab = FreighterTab()
    tab.set_data({"FreighterInventory": {}, "FreighterInventory_Cargo": _cargo(True)})
    assert tab._inv_tabs.isTabVisible(tab._cargo_tab_index)


def test_vehicles_hides_cargo_tab_when_empty(qapp):
    tab = VehiclesTab()
    tab.set_data(
        {
            "VehicleOwnership": [
                {
                    "Name": "Roamer",
                    "Inventory": {"Slots": []},
                    "Inventory_TechOnly": {"Slots": []},
                    "Inventory_Cargo": _cargo(False),
                }
            ]
        }
    )
    assert not tab._inv_tabs.isTabVisible(tab._cargo_tab_index)


def test_vehicles_shows_cargo_tab_when_present(qapp):
    tab = VehiclesTab()
    tab.set_data(
        {
            "VehicleOwnership": [
                {
                    "Name": "Roamer",
                    "Inventory": {"Slots": []},
                    "Inventory_TechOnly": {"Slots": []},
                    "Inventory_Cargo": _cargo(True),
                }
            ]
        }
    )
    assert tab._inv_tabs.isTabVisible(tab._cargo_tab_index)


def _corvette_ship(cargo: dict) -> dict:
    return {
        "Name": "Corvette",
        "Resource": {"Filename": "MODELS/COMMON/SPACECRAFT/BIGGS/BIGGS.SCENE.MBIN"},
        "Inventory": {"Slots": [], "Class": {"InventoryClass": "S"}},
        "Inventory_TechOnly": {"Slots": []},
        "Inventory_Cargo": cargo,
    }


def test_corvette_hides_cargo_tab_when_empty(qapp):
    tab = CorvetteTab()
    tab.set_data({"ShipOwnership": [_corvette_ship(_cargo(False))]})
    assert not tab._inv_tabs.isTabVisible(2)


def test_corvette_shows_cargo_tab_when_present(qapp):
    tab = CorvetteTab()
    tab.set_data({"ShipOwnership": [_corvette_ship(_cargo(True))]})
    assert tab._inv_tabs.isTabVisible(2)
