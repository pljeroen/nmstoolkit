"""Tests for Squadron and Fossils preview tab wiring."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from nmstoolkit.gui.tabs.fossils_tab import FossilsTab
from nmstoolkit.gui.tabs.squadron_tab import SquadronTab


def _make_pilot(ship_filename: str, ship_seed: str = "0xABC") -> dict:
    return {
        "NPCResource": {"Filename": "NPCGEK", "Seed": "0x111"},
        "ShipResource": {"Filename": ship_filename, "Seed": ship_seed},
        "PilotRank": 1,
    }


def _make_ship(name: str, filename: str) -> dict:
    return {
        "Name": name,
        "Resource": {"Filename": filename},
        "Seed": "0x1234",
        "Inventory": {"Slots": [], "Class": {"InventoryClass": "A"}},
        "Inventory_TechOnly": {"Slots": []},
        "Inventory_Cargo": {"Slots": []},
    }


def test_squadron_preview_tab_and_identity(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(SquadronTab, "_load_preview_meshes", lambda self, r: ([], "no preview"))
    tab = SquadronTab()
    labels = [tab._tabs.tabText(i) for i in range(tab._tabs.count())]
    assert "Preview" not in labels
    assert hasattr(tab, "_general_splitter")
    assert tab._general_splitter.count() == 2
    tab.set_data(
        {
            "SquadronPilots": [_make_pilot("MODELS/COMMON/SPACECRAFT/FIGHTERS/FIGHTER_PROC.SCENE.MBIN", "0xAAAA")],
            "SquadronUnlockedPilotSlots": [0],
            "ShipOwnership": [_make_ship("A", "MODELS/COMMON/SPACECRAFT/FIGHTERS/FIGHTER_PROC.SCENE.MBIN")],
        }
    )
    assert "0xAAAA" in tab._preview_identity.text()
    assert "FIGHTER_PROC.SCENE.MBIN" in tab._preview_identity.text()


def test_fossils_preview_tab_and_selection_updates(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(FossilsTab, "_load_preview_meshes", lambda self, r: ([], "no preview"))
    monkeypatch.setattr(
        "nmstoolkit.gui.tabs.fossils_tab.resolve_fossil_scene",
        lambda fid: "models/planets/biomes/common/buildings/parts/buildableparts/decoration/fossils/biped.scene.mbin",
    )
    tab = FossilsTab()
    assert hasattr(tab, "_preview_panel")
    assert tab._preview_panel.parentWidget() is not None
    tab.set_data(
        {
            "Inventory": {
                "Slots": [
                    {"Id": "^FOS_BI_BODY_AC", "Amount": 1, "Index": {"X": 0, "Y": 0}},
                ]
            },
            "PersistentPlayerBases": [
                {"Name": "Base A", "Objects": [{"ObjectID": "^FOS_BI"}]},
            ],
        }
    )
    tab._pieces_table.selectRow(0)
    assert "FOS_BI_BODY_AC" in tab._preview_identity.text()
    assert "biped.scene.mbin" in tab._preview_identity.text().lower()
