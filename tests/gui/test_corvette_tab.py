"""Tests for Corvette editor tab."""

import pytest
from PySide6.QtWidgets import QApplication

from nmstoolkit.gui.tabs.corvette_tab import (
    CorvetteTab,
    _categorize_modules,
    _derive_module_id,
    _required_corvette_modules,
    _resolve_pak_dir,
    _scene_candidates_for_module,
)


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _make_corvette_ship(name="My Corvette", inv_class="S"):
    """Build a corvette ship entry (BIGGS model)."""
    return {
        "Name": name,
        "Seed": "0xABC",
        "Resource": {"Filename": "MODELS/COMMON/SPACECRAFT/BIGGS/BIGGS.SCENE.MBIN"},
        "Inventory": {
            "Slots": [
                {
                    "Type": {"InventoryType": "Technology"},
                    "Id": "^YOURSHIP_LAUNCH",
                    "Amount": 1,
                    "MaxAmount": 1,
                    "DamageFactor": 0.0,
                    "FullyInstalled": True,
                    "Index": {"X": 0, "Y": 0},
                },
            ],
            "ValidSlotIndices": [{"X": x, "Y": y} for x in range(10) for y in range(6)],
            "Class": {"InventoryClass": inv_class},
            "StackSizeGroup": {"InventoryStackSizeGroup": "Ship"},
            "BaseStatValues": [
                {"BaseStatID": "^SHIP_DAMAGE", "Value": 150.0},
                {"BaseStatID": "^SHIP_SHIELD", "Value": 200.0},
            ],
            "SpecialSlots": [],
            "Width": 10,
            "Height": 6,
        },
        "Inventory_TechOnly": {
            "Slots": [],
            "ValidSlotIndices": [{"X": x, "Y": y} for x in range(10) for y in range(6)],
            "Class": {"InventoryClass": inv_class},
            "Width": 10,
            "Height": 6,
        },
        "Inventory_Cargo": {
            "Slots": [],
            "ValidSlotIndices": [],
            "Class": {"InventoryClass": inv_class},
            "Width": 8,
            "Height": 5,
        },
    }


def _make_psd(corvettes=None, with_draft=False):
    """Build a minimal PlayerStateData dict."""
    ships = [
        {"Name": "My Fighter", "Resource": {"Filename": "FIGHTER_PROC.SCENE.MBIN"},
         "Inventory": {"Slots": [], "ValidSlotIndices": [], "Class": {"InventoryClass": "A"},
                        "Width": 10, "Height": 5}},
    ]
    if corvettes:
        ships.extend(corvettes)

    psd = {"ShipOwnership": ships}

    if with_draft:
        psd["CorvetteStorageInventory"] = {
            "Slots": [
                {"Type": {"InventoryType": "Product"}, "Id": "^B_COK_A",
                 "Amount": 1, "MaxAmount": 500, "DamageFactor": 0.0,
                 "FullyInstalled": True, "Index": {"X": 5, "Y": 5}},
                {"Type": {"InventoryType": "Product"}, "Id": "^B_WNG_A",
                 "Amount": 1, "MaxAmount": 500, "DamageFactor": 0.0,
                 "FullyInstalled": True, "Index": {"X": 3, "Y": 5}},
                {"Type": {"InventoryType": "Product"}, "Id": "^B_WNG_B",
                 "Amount": 1, "MaxAmount": 500, "DamageFactor": 0.0,
                 "FullyInstalled": True, "Index": {"X": 7, "Y": 5}},
                {"Type": {"InventoryType": "Product"}, "Id": "^B_TRU_A",
                 "Amount": 1, "MaxAmount": 500, "DamageFactor": 0.0,
                 "FullyInstalled": True, "Index": {"X": 5, "Y": 8}},
            ],
            "ValidSlotIndices": [{"X": x, "Y": y} for x in range(10) for y in range(12)],
            "Class": {"InventoryClass": "C"},
            "Width": 10,
            "Height": 16,
        }
        psd["CorvetteStorageLayout"] = {"Slots": 10, "Seed": [True, "0x1"], "Level": 1}
        psd["CorvetteEditAssociatedShipIndex"] = 1
        psd["CorvetteEditShipName"] = "Draft Corvette"
        psd["CorvetteDraftShipSeed"] = 42
    return psd


class TestCorvetteTabCreate:
    def test_tab_creates(self, qapp):
        tab = CorvetteTab()
        assert tab is not None

    def test_build_grid_hidden_before_loading_data(self, qapp):
        tab = CorvetteTab()
        assert tab._inv_tabs.isHidden()
        assert not tab._right_placeholder.isHidden()

    def test_empty_state_when_no_corvettes(self, qapp):
        tab = CorvetteTab()
        psd = _make_psd()
        tab.set_data(psd)
        assert not tab._empty_label.isHidden()
        assert tab._selector_group.isHidden()

    def test_selector_shown_with_corvettes(self, qapp):
        tab = CorvetteTab()
        psd = _make_psd(corvettes=[_make_corvette_ship("BigBoy")])
        tab.set_data(psd)
        assert tab._empty_label.isHidden()
        assert not tab._selector_group.isHidden()


class TestCorvetteDropdown:
    def test_completed_corvettes_in_dropdown(self, qapp):
        tab = CorvetteTab()
        psd = _make_psd(corvettes=[
            _make_corvette_ship("Alpha", "S"),
            _make_corvette_ship("Beta", "A"),
        ])
        tab.set_data(psd)
        assert tab._corvette_combo.count() == 2
        assert "Alpha" in tab._corvette_combo.itemText(0)
        assert "Beta" in tab._corvette_combo.itemText(1)

    def test_draft_appears_in_dropdown(self, qapp):
        tab = CorvetteTab()
        psd = _make_psd(
            corvettes=[_make_corvette_ship("Alpha")],
            with_draft=True,
        )
        tab.set_data(psd)
        assert tab._corvette_combo.count() == 2
        assert "[Draft]" in tab._corvette_combo.itemText(1)

    def test_draft_only_in_dropdown(self, qapp):
        tab = CorvetteTab()
        psd = _make_psd(with_draft=True)
        tab.set_data(psd)
        assert tab._corvette_combo.count() == 1
        assert "[Draft]" in tab._corvette_combo.itemText(0)


class TestCorvetteDetails:
    def test_completed_shows_name(self, qapp):
        tab = CorvetteTab()
        psd = _make_psd(corvettes=[_make_corvette_ship("BigBoy", "S")])
        tab.set_data(psd)
        assert tab._name_edit.text() == "BigBoy"
        assert not tab._details_group.isHidden()
        assert tab._draft_group.isHidden()

    def test_completed_shows_class(self, qapp):
        tab = CorvetteTab()
        psd = _make_psd(corvettes=[_make_corvette_ship("BigBoy", "S")])
        tab.set_data(psd)
        assert tab._class_combo.currentText() == "S"

    def test_completed_shows_stats(self, qapp):
        tab = CorvetteTab()
        psd = _make_psd(corvettes=[_make_corvette_ship("BigBoy")])
        tab.set_data(psd)
        assert tab._stat_spinners["^SHIP_DAMAGE"].value() == 150.0
        assert tab._stat_spinners["^SHIP_SHIELD"].value() == 200.0

    def test_name_edit_updates_psd(self, qapp):
        tab = CorvetteTab()
        corvette = _make_corvette_ship("BigBoy")
        psd = _make_psd(corvettes=[corvette])
        tab.set_data(psd)
        tab._name_edit.setText("NewName")
        tab._on_name_changed()
        assert corvette["Name"] == "NewName"

    def test_draft_shows_draft_details(self, qapp):
        tab = CorvetteTab()
        psd = _make_psd(with_draft=True)
        tab.set_data(psd)
        assert tab._details_group.isHidden()
        assert not tab._draft_group.isHidden()
        assert "42" in tab._draft_seed_label.text()


class TestModuleCategorization:
    def test_categorize_modules(self):
        slots = [
            {"Id": "^B_COK_A"},
            {"Id": "^B_COK_B"},
            {"Id": "^B_WNG_A"},
            {"Id": "^B_WNG_B"},
            {"Id": "^B_WNG_C"},
            {"Id": "^B_TRU_A"},
            {"Id": "^B_DECO_A"},
            {"Id": "^B_STR_A_N"},
            {"Id": "^B_STR_A_NE"},
        ]
        counts = _categorize_modules(slots)
        assert counts["Cockpit"] == 2
        assert counts["Wing"] == 3
        assert counts["Thruster"] == 1
        assert counts["Decoration"] == 1
        assert counts["Structure"] == 2

    def test_categorize_empty(self):
        counts = _categorize_modules([])
        assert len(counts) == 0


class TestCorvetteModuleSummary:
    def test_draft_shows_module_summary(self, qapp):
        tab = CorvetteTab()
        psd = _make_psd(with_draft=True)
        tab.set_data(psd)
        text = tab._summary_label.text()
        assert "Cockpit" in text
        assert "Wing" in text
        assert "Thruster" in text


class TestCorvetteFilterExcludesNonCorvettes:
    """R-CORV-01: Non-corvette ships must not appear in corvette selector."""

    def test_fighter_excluded_from_corvettes(self, qapp):
        """A fighter with no BIGGS filename should not appear as a corvette."""
        from nmstoolkit.gui.tabs.corvette_tab import _is_corvette_ship

        fighter = {
            "Name": "My Fighter",
            "Resource": {"Filename": "MODELS/COMMON/SPACECRAFT/FIGHTERS/FIGHTER_PROC.SCENE.MBIN"},
            "Inventory": {"Slots": [{"Id": "^YOURSHIP_LAUNCH", "Amount": 1}]},
        }
        assert _is_corvette_ship(fighter) is False

    def test_shuttle_excluded_from_corvettes(self, qapp):
        from nmstoolkit.gui.tabs.corvette_tab import _is_corvette_ship

        shuttle = {
            "Name": "My Shuttle",
            "Resource": {"Filename": "MODELS/COMMON/SPACECRAFT/SHUTTLE/SHUTTLE_PROC.SCENE.MBIN"},
            "Inventory": {"Slots": []},
        }
        assert _is_corvette_ship(shuttle) is False

    def test_biggs_ship_is_corvette(self, qapp):
        from nmstoolkit.gui.tabs.corvette_tab import _is_corvette_ship

        corvette = {
            "Name": "My Corvette",
            "Resource": {"Filename": "MODELS/COMMON/SPACECRAFT/BIGGS/BIGGS.SCENE.MBIN"},
            "Inventory": {"Slots": []},
        }
        assert _is_corvette_ship(corvette) is True

    def test_non_corvette_not_in_dropdown(self, qapp):
        """Only BIGGS ships should appear in the corvette dropdown, not fighters."""
        tab = CorvetteTab()
        psd = {
            "ShipOwnership": [
                {"Name": "Fighter", "Resource": {"Filename": "FIGHTER_PROC.SCENE.MBIN"},
                 "Inventory": {"Slots": [], "ValidSlotIndices": [], "Class": {"InventoryClass": "A"},
                               "Width": 10, "Height": 5}},
                _make_corvette_ship("Real Corvette"),
            ],
        }
        tab.set_data(psd)
        # Only the corvette should appear, not the fighter
        assert tab._corvette_combo.count() == 1
        assert "Real Corvette" in tab._corvette_combo.itemText(0)

    def test_cargo_module_item_does_not_mark_corvette(self, qapp):
        """A non-BIGGS ship carrying B_* product items must not be listed."""
        tab = CorvetteTab()
        ship_with_cargo_item = {
            "Name": "Loot Hauler",
            "Resource": {"Filename": "MODELS/COMMON/SPACECRAFT/FIGHTERS/FIGHTER_PROC.SCENE.MBIN"},
            "Inventory": {
                "Slots": [
                    {
                        "Id": "B_COK_A",
                        "Type": {"InventoryType": "Product"},
                        "Index": {"X": 0, "Y": 0},
                    }
                ],
                "ValidSlotIndices": [],
                "Class": {"InventoryClass": "A"},
                "Width": 10,
                "Height": 5,
            },
            "Inventory_TechOnly": {"Slots": []},
        }
        psd = {"ShipOwnership": [ship_with_cargo_item, _make_corvette_ship("Real Corvette")]}
        tab.set_data(psd)
        assert tab._corvette_combo.count() == 1
        assert "Real Corvette" in tab._corvette_combo.itemText(0)


class TestCorvetteModelGuidance:
    """R-CORV-02: Show helpful message when models unavailable."""

    def test_3d_placeholder_shows_guidance(self, qapp):
        """When 3D view hasn't been initialized, placeholder should exist."""
        tab = CorvetteTab()
        assert tab._3d_view is None
        assert tab._3d_placeholder is not None


class TestCorvette3DBinding:
    def test_selected_completed_ship_drives_3d_modules(self, qapp, monkeypatch):
        class Dummy3D:
            def __init__(self):
                self.last_modules = None

            def set_modules(self, inv):
                self.last_modules = inv

            def update(self):
                pass

        tab = CorvetteTab()
        alpha = _make_corvette_ship("Alpha")
        beta = _make_corvette_ship("Beta")
        psd = _make_psd(corvettes=[alpha, beta])
        tab.set_data(psd)
        dummy = Dummy3D()
        tab._3d_view = dummy
        tab._draft_stack.setCurrentIndex(1)
        monkeypatch.setattr(
            tab,
            "_load_missing_meshes_from_gamefiles",
            lambda inv, force=False: None,
        )

        tab._on_corvette_selected(1)
        assert dummy.last_modules is beta["Inventory"]


class TestCorvetteGamefileHelpers:
    def test_required_corvette_modules_extracts_unique_ids(self):
        inv = {
            "Slots": [
                {"Id": "^B_COK_A"},
                {"Id": "^B_WNG_A"},
                {"Id": "^B_WNG_A"},
                {"Id": "^YOURSHIP_LAUNCH"},
            ]
        }
        assert _required_corvette_modules(inv) == {"B_COK_A", "B_WNG_A"}

    def test_derive_module_id_from_scene_path_parts(self):
        parts = "models/common/spacecraft/corvette/parts/cok_a/entities/cok_a.scene.mbin".split("/")
        assert _derive_module_id(parts) == "B_COK_A"

    def test_resolve_pak_dir_from_root_with_gamedata(self, tmp_path):
        game_dir = tmp_path / "No Man's Sky"
        pcbanks = game_dir / "GAMEDATA" / "PCBANKS"
        pcbanks.mkdir(parents=True)
        assert _resolve_pak_dir(game_dir) == pcbanks

    def test_resolve_pak_dir_from_pcbanks_dir(self, tmp_path):
        pcbanks = tmp_path / "PCBANKS"
        pcbanks.mkdir(parents=True)
        assert _resolve_pak_dir(pcbanks) == pcbanks

    def test_scene_candidates_prefer_parts_cockpit(self):
        candidates = _scene_candidates_for_module("B_COK_A")
        assert candidates
        assert candidates[0] == "models/common/spacecraft/biggs/modules/parts/cockpit_1x2_a.scene.mbin"
        assert "models/common/spacecraft/biggs/modules/cockpit_a_1x2_placement.scene.mbin" in candidates

    def test_scene_candidates_prefer_parts_wing(self):
        candidates = _scene_candidates_for_module("B_WNG_A")
        assert candidates
        assert candidates[0] == "models/common/spacecraft/biggs/modules/parts/wing_a_l.scene.mbin"
        assert "models/common/spacecraft/biggs/modules/ext_wing_a_1x2_placement.scene.mbin" in candidates
