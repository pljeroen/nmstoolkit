"""Tests for companions tab — including gene modification editing."""

import pytest
from PySide6.QtWidgets import QApplication

from nmstoolkit.gui.tabs.companions_tab import CompanionsTab, _friendly_creature_name


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _make_pet(
    creature_id="^LARGEBUTTERFLY",
    custom_name="",
    descriptors=None,
    traits=None,
    moods=None,
    scale=1.0,
    trust=0.5,
    predator=False,
    has_fur=True,
    egg_modified=False,
    creature_seed="0xABCD",
):
    return {
        "CreatureID": creature_id,
        "CustomName": f"^{custom_name}" if custom_name else "^",
        "Descriptors": descriptors or ["^_FWINGS_02", "^_MOTHBODY_01", "^_BWINGS_04"],
        "Traits": traits or [0.5, -0.3, 0.7],
        "Moods": moods or [0.2, 0.8],
        "Scale": scale,
        "Trust": trust,
        "Predator": predator,
        "HasFur": has_fur,
        "EggModified": egg_modified,
        "CreatureSeed": creature_seed,
        "AllowUnmodifiedReroll": True,
    }


class TestFriendlyCreatureName:
    def test_known_creature(self):
        assert _friendly_creature_name("^LARGEBUTTERFLY") == "Large Butterfly"

    def test_unknown_creature_fallback(self):
        name = _friendly_creature_name("^WEIRDNEWCREATURE")
        assert name  # Should produce something, not empty

    def test_empty_creature(self):
        assert _friendly_creature_name("^") == "Unknown"


class TestCompanionsTabDescriptors:
    """Test that descriptors are displayed and editable."""

    def test_descriptors_displayed(self, qapp):
        tab = CompanionsTab()
        pet = _make_pet(descriptors=["^_FWINGS_02", "^_MOTHBODY_01", "^_BWINGS_04"])
        psd = {"Pets": [pet]}
        tab.set_data(psd)
        tab._list.setCurrentRow(0)
        # Label shows count, individual edits show the values
        assert "3" in tab._descriptors_label.text()
        assert tab._descriptor_edits[0].text() == "_FWINGS_02"
        assert tab._descriptor_edits[1].text() == "_MOTHBODY_01"
        assert tab._descriptor_edits[2].text() == "_BWINGS_04"

    def test_descriptors_editable(self, qapp):
        """Descriptors should be editable via line edits."""
        tab = CompanionsTab()
        pet = _make_pet(descriptors=["^_FWINGS_02", "^_MOTHBODY_01", "^_BWINGS_04"])
        psd = {"Pets": [pet]}
        tab.set_data(psd)
        tab._list.setCurrentRow(0)
        # Tab should have descriptor editors (not just a label)
        assert hasattr(tab, "_descriptor_edits")
        assert len(tab._descriptor_edits) > 0

    def test_edit_descriptor_writes_back(self, qapp):
        tab = CompanionsTab()
        pet = _make_pet(descriptors=["^_FWINGS_02", "^_MOTHBODY_01", "^_BWINGS_04"])
        psd = {"Pets": [pet]}
        tab.set_data(psd)
        tab._list.setCurrentRow(0)
        # Change first descriptor
        tab._descriptor_edits[0].setText("_NEWWING_01")
        tab._on_descriptor_changed(0)
        assert pet["Descriptors"][0] == "^_NEWWING_01"

    def test_egg_modified_set_on_descriptor_change(self, qapp):
        """Changing descriptors should set EggModified flag."""
        tab = CompanionsTab()
        pet = _make_pet(
            descriptors=["^_FWINGS_02", "^_MOTHBODY_01"],
            egg_modified=False,
        )
        psd = {"Pets": [pet]}
        tab.set_data(psd)
        tab._list.setCurrentRow(0)
        tab._descriptor_edits[0].setText("_NEWWING_01")
        tab._on_descriptor_changed(0)
        assert pet["EggModified"] is True


class TestDescriptorsOverflow:
    """R-GEN-04: All traits display correctly when count exceeds 8."""

    def test_11_descriptors_all_editable(self, qapp):
        """A pet with 11 descriptors should create 11 edit widgets."""
        tab = CompanionsTab()
        descs = [f"^_PART_{i}" for i in range(11)]
        pet = _make_pet(descriptors=descs)
        psd = {"Pets": [pet]}
        tab.set_data(psd)
        tab._list.setCurrentRow(0)
        assert len(tab._descriptor_edits) >= 11

    def test_20_descriptors_all_editable(self, qapp):
        """Even 20 descriptors should all be accessible."""
        tab = CompanionsTab()
        descs = [f"^_DESC_{i}" for i in range(20)]
        pet = _make_pet(descriptors=descs)
        psd = {"Pets": [pet]}
        tab.set_data(psd)
        tab._list.setCurrentRow(0)
        assert len(tab._descriptor_edits) >= 20

    def test_descriptor_9_value_correct(self, qapp):
        """The 9th descriptor (index 8) should be readable."""
        tab = CompanionsTab()
        descs = [f"^_PART_{i}" for i in range(11)]
        pet = _make_pet(descriptors=descs)
        psd = {"Pets": [pet]}
        tab.set_data(psd)
        tab._list.setCurrentRow(0)
        assert tab._descriptor_edits[8].text() == "_PART_8"


class TestDescriptorAddRemove:
    """R-GEN-02, R-GEN-03: Add and remove gene traits."""

    def test_add_button_exists(self, qapp):
        tab = CompanionsTab()
        assert hasattr(tab, "_add_desc_btn")

    def test_remove_button_exists(self, qapp):
        tab = CompanionsTab()
        assert hasattr(tab, "_remove_desc_btn")

    def test_add_descriptor(self, qapp):
        tab = CompanionsTab()
        pet = _make_pet(descriptors=["^_FWINGS_02", "^_MOTHBODY_01"])
        psd = {"Pets": [pet]}
        tab.set_data(psd)
        tab._list.setCurrentRow(0)
        initial_count = len(pet["Descriptors"])
        tab._on_add_descriptor()
        assert len(pet["Descriptors"]) == initial_count + 1

    def test_remove_descriptor(self, qapp):
        tab = CompanionsTab()
        pet = _make_pet(descriptors=["^_FWINGS_02", "^_MOTHBODY_01", "^_BWINGS_04"])
        psd = {"Pets": [pet]}
        tab.set_data(psd)
        tab._list.setCurrentRow(0)
        initial_count = len(pet["Descriptors"])
        tab._on_remove_descriptor()
        assert len(pet["Descriptors"]) == initial_count - 1

    def test_remove_from_empty_no_crash(self, qapp):
        tab = CompanionsTab()
        pet = _make_pet()
        pet["Descriptors"] = []  # Override after creation to avoid falsy default
        psd = {"Pets": [pet]}
        tab.set_data(psd)
        tab._list.setCurrentRow(0)
        tab._on_remove_descriptor()
        assert len(pet["Descriptors"]) == 0


class TestCompanionsTabEditWriteBack:
    """Test that edits write back to the data dict."""

    def test_scale_writeback(self, qapp):
        tab = CompanionsTab()
        pet = _make_pet(scale=1.0)
        psd = {"Pets": [pet]}
        tab.set_data(psd)
        tab._list.setCurrentRow(0)
        tab._scale_spin.setValue(2.5)
        assert pet["Scale"] == 2.5

    def test_trust_writeback(self, qapp):
        tab = CompanionsTab()
        pet = _make_pet(trust=0.5)
        psd = {"Pets": [pet]}
        tab.set_data(psd)
        tab._list.setCurrentRow(0)
        tab._trust_spin.setValue(1.0)
        assert pet["Trust"] == 1.0

    def test_predator_writeback(self, qapp):
        tab = CompanionsTab()
        pet = _make_pet(predator=False)
        psd = {"Pets": [pet]}
        tab.set_data(psd)
        tab._list.setCurrentRow(0)
        tab._predator_check.setChecked(True)
        assert pet["Predator"] is True

    def test_trait_writeback(self, qapp):
        tab = CompanionsTab()
        pet = _make_pet(traits=[0.5, -0.3, 0.7])
        psd = {"Pets": [pet]}
        tab.set_data(psd)
        tab._list.setCurrentRow(0)
        tab._trait_spins[0].setValue(0.9)
        assert pet["Traits"][0] == pytest.approx(0.9, abs=0.01)

    def test_empty_pets_no_crash(self, qapp):
        tab = CompanionsTab()
        psd = {"Pets": []}
        tab.set_data(psd)
        assert tab._list.count() == 0

    def test_empty_slot_filtered(self, qapp):
        """Pets with empty CreatureID should be filtered out."""
        tab = CompanionsTab()
        psd = {
            "Pets": [
                _make_pet(creature_id="^LARGEBUTTERFLY"),
                {"CreatureID": "^", "CustomName": "^"},  # empty slot
            ]
        }
        tab.set_data(psd)
        assert tab._list.count() == 1
