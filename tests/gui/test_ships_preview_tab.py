"""Tests for Ships preview tab wiring and fidelity labeling."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from nmstoolkit.gui.tabs.ships_tab import ShipsTab


def _make_ship(name: str, seed: str, resource: str) -> dict:
    return {
        "Name": name,
        "Seed": seed,
        "Resource": {"Filename": resource},
        "Inventory": {"Slots": [], "Class": {"InventoryClass": "A"}},
        "Inventory_TechOnly": {"Slots": []},
        "Inventory_Cargo": {"Slots": []},
    }


def _make_psd() -> dict:
    return {
        "ShipOwnership": [
            _make_ship("Alpha", "0xAAAA", "MODELS/COMMON/SPACECRAFT/FIGHTERS/FIGHTER_PROC.SCENE.MBIN"),
            _make_ship("Beta", "0xBBBB", "MODELS/COMMON/SPACECRAFT/SHUTTLE/SHUTTLE_PROC.SCENE.MBIN"),
        ],
        "PrimaryShip": 0,
    }


def test_preview_tab_exists(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(ShipsTab, "_load_preview_meshes", lambda self, r: ([], "no preview"))
    tab = ShipsTab()
    labels = [tab._inv_tabs.tabText(i) for i in range(tab._inv_tabs.count())]
    assert "Preview" in labels
    assert "template-level" in tab._preview_fidelity.text().lower()


def test_preview_identity_updates_on_selection(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(ShipsTab, "_load_preview_meshes", lambda self, r: ([], "no preview"))
    tab = ShipsTab()
    tab.set_data(_make_psd())
    assert "0xAAAA" in tab._preview_identity.text()
    tab._ship_list.setCurrentRow(1)
    assert "0xBBBB" in tab._preview_identity.text()
    assert "SHUTTLE_PROC.SCENE.MBIN" in tab._preview_identity.text()


def test_preview_uses_resource_seed_when_ship_seed_missing(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(ShipsTab, "_load_preview_meshes", lambda self, r: ([], "no preview"))
    tab = ShipsTab()
    psd = {
        "ShipOwnership": [
            {
                "Name": "Galaxy Hopper",
                "Seed": None,
                "Resource": {
                    "Filename": "MODELS/COMMON/SPACECRAFT/SAILSHIP/SAILSHIP_PROC.SCENE.MBIN",
                    "Seed": [True, "0xC8B096BB223CE711"],
                },
                "Inventory": {"Slots": [], "Class": {"InventoryClass": "B"}},
                "Inventory_TechOnly": {"Slots": []},
                "Inventory_Cargo": {"Slots": []},
            }
        ]
    }
    tab.set_data(psd)
    assert "0xC8B096BB223CE711" in tab._preview_identity.text()
