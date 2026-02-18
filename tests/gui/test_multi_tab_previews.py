"""Tests for preview tabs on multitools, frigates, vehicles, and companions."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from nmstoolkit.gui.tabs.companions_tab import CompanionsTab
from nmstoolkit.gui.tabs.frigates_tab import FrigatesTab
from nmstoolkit.gui.tabs.multitools_tab import MultitoolsTab
from nmstoolkit.gui.tabs.vehicles_tab import VehiclesTab


def test_multitool_preview_tab_and_identity_refresh(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(
        MultitoolsTab, "_load_preview_meshes", lambda self, r: ([], "no preview"), raising=False
    )
    tab = MultitoolsTab()
    labels = [tab._tabs.tabText(i) for i in range(tab._tabs.count())]
    assert "Preview" in labels

    psd = {
        "Multitools": [
            {"Name": "MT-A", "Seed": "0xAAAA", "Resource": {"Filename": "MODELS/A.SCENE.MBIN"}, "Store": {}},
            {"Name": "MT-B", "Seed": "0xBBBB", "Resource": {"Filename": "MODELS/B.SCENE.MBIN"}, "Store": {}},
        ]
    }
    tab.set_data(psd)
    assert "0xAAAA" in tab._preview_identity.text()
    tab._list.setCurrentRow(1)
    assert "0xBBBB" in tab._preview_identity.text()
    assert "MODELS/B.SCENE.MBIN" in tab._preview_identity.text()


def test_frigates_preview_tab_and_identity_refresh(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(
        FrigatesTab, "_load_preview_meshes", lambda self, r: ([], "no preview"), raising=False
    )
    tab = FrigatesTab()
    assert hasattr(tab, "_preview_panel")
    assert tab._preview_panel.parentWidget() is not None

    psd = {
        "FleetFrigates": [
            {
                "CustomName": "F-A",
                "FrigateClass": {"FrigateClass": "Combat"},
                "InventoryClass": {"InventoryClass": "A"},
                "ResourceSeed": [True, "0xAAAA"],
                "Resource": {"Filename": "MODELS/FRIGATE/A.SCENE.MBIN"},
            },
            {
                "CustomName": "F-B",
                "FrigateClass": {"FrigateClass": "Combat"},
                "InventoryClass": {"InventoryClass": "A"},
                "ResourceSeed": [True, "0xBBBB"],
                "Resource": {"Filename": "MODELS/FRIGATE/B.SCENE.MBIN"},
            },
        ]
    }
    tab.set_data(psd)
    assert "0xAAAA" in tab._preview_identity.text()
    tab._list.setCurrentRow(1)
    assert "0xBBBB" in tab._preview_identity.text()
    assert "MODELS/FRIGATE/B.SCENE.MBIN" in tab._preview_identity.text()


def test_frigates_preview_fallback_resource_from_class(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(
        FrigatesTab, "_load_preview_meshes", lambda self, r: ([], "no preview"), raising=False
    )
    monkeypatch.setattr(
        "nmstoolkit.gui.tabs.frigates_tab.resolve_frigate_scene",
        lambda cls: "models/common/spacecraft/frigates/supportfrigate.scene.mbin",
    )
    tab = FrigatesTab()
    tab.set_data(
        {
            "FleetFrigates": [
                {
                    "CustomName": "F-A",
                    "FrigateClass": {"FrigateClass": "Support"},
                    "InventoryClass": {"InventoryClass": "A"},
                    "ResourceSeed": [True, "0xAAAA"],
                }
            ]
        }
    )
    assert "supportfrigate.scene.mbin" in tab._preview_identity.text().lower()


def test_vehicles_preview_tab_and_identity_refresh(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(
        VehiclesTab, "_load_preview_meshes", lambda self, r: ([], "no preview"), raising=False
    )
    tab = VehiclesTab()
    labels = [tab._inv_tabs.tabText(i) for i in range(tab._inv_tabs.count())]
    assert "Preview" not in labels
    tech_idx = labels.index("Technology + Effects")
    assert tab._inv_tabs.widget(tech_idx) is tab._inv_tech
    assert not hasattr(tab, "_tech_splitter")
    assert tab._preview_placeholder.minimumHeight() == 0
    parent = tab._preview_panel.parentWidget()
    found_inv_tech_parent = False
    while parent is not None:
        if parent is tab._inv_tech:
            found_inv_tech_parent = True
            break
        parent = parent.parentWidget()
    assert found_inv_tech_parent

    psd = {
        "VehicleOwnership": [
            {"Name": "V-A", "Seed": "0xAAAA", "Resource": {"Filename": "MODELS/VEH/A.SCENE.MBIN"}},
            {"Name": "V-B", "Seed": "0xBBBB", "Resource": {"Filename": "MODELS/VEH/B.SCENE.MBIN"}},
        ]
    }
    tab.set_data(psd)
    assert "0xAAAA" in tab._preview_identity.text()
    tab._list.setCurrentRow(1)
    assert "0xBBBB" in tab._preview_identity.text()
    assert "MODELS/VEH/B.SCENE.MBIN" in tab._preview_identity.text()


def test_vehicles_preview_fallback_resource_from_type(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(
        VehiclesTab, "_load_preview_meshes", lambda self, r: ([], "no preview"), raising=False
    )
    monkeypatch.setattr(
        "nmstoolkit.gui.tabs.vehicles_tab.resolve_vehicle_scene",
        lambda name: "models/common/vehicles/buggy/buggy.scene.mbin",
    )
    tab = VehiclesTab()
    tab.set_data({"VehicleOwnership": [{"Name": "Roamer", "Seed": "0xAAAA"}]})
    assert "buggy.scene.mbin" in tab._preview_identity.text().lower()


def test_companions_preview_tab_and_identity_refresh(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(
        CompanionsTab, "_load_preview_meshes", lambda self, r: ([], "no preview"), raising=False
    )
    tab = CompanionsTab()
    assert hasattr(tab, "_preview_panel")
    assert tab._preview_panel.parentWidget() is not None

    psd = {
        "Pets": [
            {
                "CreatureID": "^CAT",
                "CustomName": "^A",
                "CreatureSeed": "0xAAAA",
                "Resource": {"Filename": "MODELS/PETS/A.SCENE.MBIN"},
            },
            {
                "CreatureID": "^DOG",
                "CustomName": "^B",
                "CreatureSeed": "0xBBBB",
                "Resource": {"Filename": "MODELS/PETS/B.SCENE.MBIN"},
            },
        ]
    }
    tab.set_data(psd)
    assert "0xAAAA" in tab._preview_identity.text()
    tab._list.setCurrentRow(1)
    assert "0xBBBB" in tab._preview_identity.text()
    assert "MODELS/PETS/B.SCENE.MBIN" in tab._preview_identity.text()


def test_companions_preview_fallback_resource_from_creature_id(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(
        CompanionsTab, "_load_preview_meshes", lambda self, r: ([], "no preview"), raising=False
    )
    monkeypatch.setattr(
        "nmstoolkit.gui.tabs.companions_tab.resolve_companion_scene",
        lambda cid: "models/planets/creatures/trexrig/trex.scene.mbin",
    )
    tab = CompanionsTab()
    tab.set_data({"Pets": [{"CreatureID": "^TREX", "CustomName": "^", "CreatureSeed": "0xAAAA"}]})
    assert "trex.scene.mbin" in tab._preview_identity.text().lower()


def test_companions_preview_fallback_accepts_underscored_id(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(
        CompanionsTab, "_load_preview_meshes", lambda self, r: ([], "no preview"), raising=False
    )
    tab = CompanionsTab()
    tab.set_data({"Pets": [{"CreatureID": "^HOVER_PET", "CustomName": "^", "CreatureSeed": "0xAAAA"}]})
    assert "hoverpet.scene.mbin" in tab._preview_identity.text().lower()
