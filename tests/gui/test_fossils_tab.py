"""Tests for fossils tab.

R-FTAB-01: Dedicated Fossils tab exists and loads data.
R-FTAB-02: Display fossil parts with names and icons.
R-FTAB-03: Display fossil models (assembled displays placed in bases).
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

_app = QApplication.instance() or QApplication([])


class TestFossilsTabCreation:
    """R-FTAB-01: Tab exists, instantiates, and accepts data."""

    def test_tab_instantiates(self):
        from nmstoolkit.gui.tabs.fossils_tab import FossilsTab

        tab = FossilsTab()
        assert tab is not None

    def test_tab_has_set_data(self):
        from nmstoolkit.gui.tabs.fossils_tab import FossilsTab

        tab = FossilsTab()
        assert callable(getattr(tab, "set_data", None))

    def test_set_data_with_empty_psd(self):
        from nmstoolkit.gui.tabs.fossils_tab import FossilsTab

        tab = FossilsTab()
        tab.set_data({})
        assert tab._pieces_table.rowCount() == 0

    def test_set_data_with_fossil_in_inventory(self):
        from nmstoolkit.gui.tabs.fossils_tab import FossilsTab

        psd = {
            "Inventory": {
                "Slots": [
                    {"Id": "^FOS_BI_BODY_AC", "Amount": 1, "Type": {"InventoryType": "Product"},
                     "MaxAmount": 1, "DamageFactor": 0.0, "FullyInstalled": True,
                     "Index": {"X": 0, "Y": 0}},
                ],
                "ValidSlotIndices": [{"X": 0, "Y": 0}],
                "Class": {"InventoryClass": "C"},
                "Width": 8, "Height": 6,
            },
        }
        tab = FossilsTab()
        tab.set_data(psd)
        assert tab._pieces_table.rowCount() >= 1

    def test_set_data_with_freighter_fossil(self):
        from nmstoolkit.gui.tabs.fossils_tab import FossilsTab

        psd = {
            "FreighterInventory": {
                "Slots": [
                    {"Id": "^PROC_FOSS#11125", "Amount": 1, "Type": {"InventoryType": "Product"},
                     "MaxAmount": 1, "DamageFactor": 0.0, "FullyInstalled": True,
                     "Index": {"X": 0, "Y": 0}},
                    {"Id": "^FOS_BI_TAIL_AA", "Amount": 2, "Type": {"InventoryType": "Product"},
                     "MaxAmount": 5, "DamageFactor": 0.0, "FullyInstalled": True,
                     "Index": {"X": 1, "Y": 0}},
                ],
                "ValidSlotIndices": [{"X": 0, "Y": 0}, {"X": 1, "Y": 0}],
                "Class": {"InventoryClass": "C"},
                "Width": 8, "Height": 6,
            },
        }
        tab = FossilsTab()
        tab.set_data(psd)
        assert tab._pieces_table.rowCount() >= 2


class TestFossilDisplaysInBases:
    """R-FTAB-03: Shows fossil displays placed in bases."""

    def test_base_fossils_listed(self):
        from nmstoolkit.gui.tabs.fossils_tab import FossilsTab

        psd = {
            "PersistentPlayerBases": [
                {
                    "Name": "Fossil Museum",
                    "Objects": [
                        {"ObjectID": "^FOS_QUAD", "Position": [1.0, 2.0, 3.0]},
                        {"ObjectID": "^FOS_BI", "Position": [4.0, 5.0, 6.0]},
                        {"ObjectID": "^WALL_A", "Position": [0.0, 0.0, 0.0]},
                    ],
                },
            ],
        }
        tab = FossilsTab()
        tab.set_data(psd)
        assert tab._displays_table.rowCount() == 2

    def test_non_fossil_base_objects_excluded(self):
        from nmstoolkit.gui.tabs.fossils_tab import FossilsTab

        psd = {
            "PersistentPlayerBases": [
                {
                    "Name": "Normal Base",
                    "Objects": [
                        {"ObjectID": "^WALL_A", "Position": [0.0, 0.0, 0.0]},
                        {"ObjectID": "^DOOR_A", "Position": [1.0, 0.0, 0.0]},
                    ],
                },
            ],
        }
        tab = FossilsTab()
        tab.set_data(psd)
        assert tab._displays_table.rowCount() == 0


class TestFossilItemDetection:
    """Test the fossil item ID detection logic."""

    def test_fossil_piece_detected(self):
        from nmstoolkit.gui.tabs.fossils_tab import is_fossil_item

        assert is_fossil_item("^FOS_BI_BODY_AC") is True

    def test_fossil_display_detected(self):
        from nmstoolkit.gui.tabs.fossils_tab import is_fossil_item

        assert is_fossil_item("^FOS_QUAD") is True

    def test_procedural_fossil_detected(self):
        from nmstoolkit.gui.tabs.fossils_tab import is_fossil_item

        assert is_fossil_item("^PROC_FOSS#11125") is True

    def test_skull_trophy_detected(self):
        from nmstoolkit.gui.tabs.fossils_tab import is_fossil_item

        assert is_fossil_item("^BLD_SKULL") is True

    def test_non_fossil_rejected(self):
        from nmstoolkit.gui.tabs.fossils_tab import is_fossil_item

        assert is_fossil_item("^FUEL1") is False
        assert is_fossil_item("^LASER") is False

    def test_fossil_food_excluded(self):
        """Fossil-derived food items are not fossils themselves."""
        from nmstoolkit.gui.tabs.fossils_tab import is_fossil_item

        assert is_fossil_item("^FOOD_R_FOSSIL") is False

    def test_fossil_base_object_detected(self):
        from nmstoolkit.gui.tabs.fossils_tab import is_fossil_base_object

        assert is_fossil_base_object("^FOS_QUAD") is True
        assert is_fossil_base_object("^FOS_LIMBS") is True
        assert is_fossil_base_object("^BLD_SKULL") is True

    def test_non_fossil_base_object_rejected(self):
        from nmstoolkit.gui.tabs.fossils_tab import is_fossil_base_object

        assert is_fossil_base_object("^WALL_A") is False
