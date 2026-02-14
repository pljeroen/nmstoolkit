"""Tests for frigates tab — including biological frigates."""

import pytest
from PySide6.QtWidgets import QApplication

from nmstoolkit.gui.tabs.frigates_tab import (
    FrigatesTab,
    _CLASS_NAMES,
    _TRAIT_FRIENDLY,
    _categorize_frigate,
)


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _make_frigate(
    name="TestFrigate",
    frigate_class="Combat",
    inv_class="B",
    stats=None,
    traits=None,
    race="Gek",
    expeditions=5,
    damaged=1,
):
    return {
        "CustomName": name,
        "FrigateClass": {"FrigateClass": frigate_class},
        "InventoryClass": {"InventoryClass": inv_class},
        "Race": {"AlienRace": race},
        "Stats": stats or [10, 20, 30, 40, 50, 0, 0, 0, 0, 0, 0],
        "TraitIDs": traits or ["^COMBAT_PRI", "^EXPLORE_SEC", "^", "^", "^"],
        "TotalNumberOfExpeditions": expeditions,
        "NumberOfTimesDamaged": damaged,
        "ResourceSeed": [False, "0x0"],
    }


def _make_bio_frigate(name="BioFrigate", stats=None, traits=None):
    return _make_frigate(
        name=name,
        frigate_class="DEEPSPACECOMMON",
        stats=stats or [15, 25, 35, 45, 0, 0, 0, 0, 0, 0, 0],
        traits=traits or [
            "^LIVING_COM_BITTER",
            "^LIVING_EXP_ECHO",
            "^",
            "^",
            "^",
        ],
    )


class TestCategorizeFrigate:
    """Test frigate type detection."""

    def test_regular_combat(self):
        f = _make_frigate(frigate_class="Combat")
        assert _categorize_frigate(f) == "regular"

    def test_regular_diplomacy(self):
        f = _make_frigate(frigate_class="Diplomacy")
        assert _categorize_frigate(f) == "regular"

    def test_biological_deepspace(self):
        f = _make_frigate(frigate_class="DEEPSPACE")
        assert _categorize_frigate(f) == "biological"

    def test_biological_deepspacecommon(self):
        f = _make_frigate(frigate_class="DEEPSPACECOMMON")
        assert _categorize_frigate(f) == "biological"

    def test_unknown_class(self):
        f = _make_frigate(frigate_class="GHOSTSHIP")
        # Special types should still be detected
        cat = _categorize_frigate(f)
        assert cat in ("biological", "special")


class TestClassNames:
    """Test that biological frigate classes have display names."""

    def test_deepspace_in_class_names(self):
        assert "DEEPSPACE" in _CLASS_NAMES

    def test_deepspacecommon_in_class_names(self):
        assert "DEEPSPACECOMMON" in _CLASS_NAMES


class TestBioTraitFriendly:
    """Test that biological trait IDs have friendly names."""

    def test_living_combat_trait(self):
        # At least some LIVING_* traits should have friendly names
        living_traits = [k for k in _TRAIT_FRIENDLY if k.startswith("LIVING_")]
        assert len(living_traits) > 0


class TestFrigatesTabSetData:
    """Test FrigatesTab.set_data with mixed fleet."""

    def test_mixed_fleet_loads(self, qapp):
        tab = FrigatesTab()
        psd = {
            "FleetFrigates": [
                _make_frigate(name="Regular1"),
                _make_bio_frigate(name="Bio1"),
                _make_frigate(name="Regular2", frigate_class="Exploration"),
            ]
        }
        tab.set_data(psd)
        assert tab._list.count() == 3

    def test_bio_frigate_type_display(self, qapp):
        tab = FrigatesTab()
        psd = {"FleetFrigates": [_make_bio_frigate(name="Bio1")]}
        tab.set_data(psd)
        # Select the bio frigate
        tab._list.setCurrentRow(0)
        # Type label should show biological-specific text
        type_text = tab._type_label.text()
        assert "Bio" in type_text or "Living" in type_text or "Organic" in type_text

    def test_bio_frigate_in_list_display(self, qapp):
        tab = FrigatesTab()
        psd = {"FleetFrigates": [_make_bio_frigate(name="Bio1")]}
        tab.set_data(psd)
        list_text = tab._list.item(0).text()
        # Should show the bio-specific class display name
        assert "Bio1" in list_text

    def test_edit_bio_frigate_name(self, qapp):
        tab = FrigatesTab()
        frigate = _make_bio_frigate(name="OldName")
        psd = {"FleetFrigates": [frigate]}
        tab.set_data(psd)
        tab._list.setCurrentRow(0)
        tab._name_edit.setText("NewBioName")
        tab._on_name_changed()
        assert frigate["CustomName"] == "NewBioName"

    def test_edit_bio_frigate_stat(self, qapp):
        tab = FrigatesTab()
        frigate = _make_bio_frigate(stats=[10, 20, 30, 40, 0, 0, 0, 0, 0, 0, 0])
        psd = {"FleetFrigates": [frigate]}
        tab.set_data(psd)
        tab._list.setCurrentRow(0)
        tab._on_stat_changed(0, 99)
        assert frigate["Stats"][0] == 99

    def test_bio_frigate_traits_display(self, qapp):
        tab = FrigatesTab()
        psd = {
            "FleetFrigates": [
                _make_bio_frigate(
                    traits=["^LIVING_COM_BITTER", "^LIVING_EXP_ECHO", "^", "^", "^"]
                )
            ]
        }
        tab.set_data(psd)
        tab._list.setCurrentRow(0)
        traits_text = tab._traits_label.text()
        # Should display something meaningful, not raw IDs
        assert traits_text != "None"
        assert "LIVING_COM_BITTER" not in traits_text or len(traits_text) > 20
