"""Tests for settlements tab.

R-SET-01: Settlement displays its actual name from save data.
R-SET-02: Settlement info displayed — population, happiness, productivity, etc.
R-SET-03: Multiple settlements listed if player has more than one.
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

_app = QApplication.instance() or QApplication([])


def _make_settlement(
    name="Test Village",
    seed="0xABCD1234",
    population=42,
    stats=None,
    owner_lid="76561198078575175",
    perks=None,
    judgement_type="None",
):
    """Create a settlement dict matching NMS V2 ring buffer format."""
    return {
        "UniqueId": "",
        "UniverseAddress": 0,
        "Position": [0.0, 0.0, 0.0],
        "SeedValue": seed,
        "BuildingStates": [0] * 48,
        "LastBuildingUpgradesTimestamps": [0] * 48,
        "Name": name,
        "Owner": {"LID": owner_lid, "UID": "", "USN": "", "PTK": "", "TS": 0},
        "PendingJudgementType": {"SettlementJudgementType": judgement_type},
        "PendingCustomJudgementID": "^",
        "Stats": stats if stats is not None else [0, 0, 0, 0, 0, 0, 0, 0],
        "Perks": perks or [],
        "LastJudgementTime": 0,
        "Population": population,
        "Race": {"AlienRace": "None"},
    }


def _make_empty_settlement():
    """Create an empty ring buffer slot (no owner, no name)."""
    return _make_settlement(name="", seed=0, population=0, owner_lid="")


def _make_local_save_data(seed):
    """Create a SettlementLocalSaveData entry."""
    return {"Seed": seed, "Cyx": [0] * 48, "Mp7": []}


class TestSettlementOwnershipDetection:
    """R-SET-01, R-SET-03: Owned settlements found via SettlementLocalSaveData seeds."""

    def test_finds_single_owned_settlement(self):
        from nmstoolkit.gui.tabs.settlements_tab import SettlementsTab

        owned = _make_settlement(name="My Town", seed="0xABCD")
        others = [_make_settlement(name=f"Town {i}", seed=f"0x{i:04X}", owner_lid="other") for i in range(5)]
        ring_buffer = others[:3] + [owned] + others[3:] + [_make_empty_settlement()] * 94

        psd = {
            "SettlementStatesV2": ring_buffer,
            "SettlementStateRingBufferIndexV2": 0,  # Points to someone else's
            "SettlementLocalSaveData": [_make_local_save_data("0xABCD")],
        }
        tab = SettlementsTab()
        tab.set_data(psd)
        assert tab._combo.count() == 1
        assert "My Town" in tab._combo.itemText(0)

    def test_finds_two_owned_settlements(self):
        from nmstoolkit.gui.tabs.settlements_tab import SettlementsTab

        town1 = _make_settlement(name="127.0.0.1", seed="0xABCD")
        town2 = _make_settlement(name="Village Two", seed="0x1234")
        ring_buffer = [_make_empty_settlement()] * 28 + [town1] + [_make_empty_settlement()] * 34 + [town2] + [_make_empty_settlement()] * 36

        psd = {
            "SettlementStatesV2": ring_buffer,
            "SettlementStateRingBufferIndexV2": 50,  # Points to empty slot
            "SettlementLocalSaveData": [
                _make_local_save_data("0xABCD"),
                _make_local_save_data("0x1234"),
            ],
        }
        tab = SettlementsTab()
        tab.set_data(psd)
        assert tab._combo.count() == 2

    def test_active_index_empty_still_finds_owned(self):
        """Ring buffer index points to empty slot — should still find owned settlement."""
        from nmstoolkit.gui.tabs.settlements_tab import SettlementsTab

        owned = _make_settlement(name="Real Town", seed="0xBEEF", population=100)
        ring_buffer = [_make_empty_settlement()] * 34 + [_make_empty_settlement()] + [_make_empty_settlement()] * 28
        ring_buffer[10] = owned  # Owned is at index 10, not at active index

        psd = {
            "SettlementStatesV2": ring_buffer,
            "SettlementStateRingBufferIndexV2": 34,  # Points to empty
            "SettlementLocalSaveData": [_make_local_save_data("0xBEEF")],
        }
        tab = SettlementsTab()
        tab.set_data(psd)
        assert tab._combo.count() == 1
        assert "Real Town" in tab._combo.itemText(0)

    def test_no_local_save_data_falls_back_to_active_index(self):
        """If SettlementLocalSaveData is missing, fall back to active index."""
        from nmstoolkit.gui.tabs.settlements_tab import SettlementsTab

        owned = _make_settlement(name="Fallback Town", seed="0xFALL")
        ring_buffer = [_make_empty_settlement()] * 5 + [owned] + [_make_empty_settlement()] * 94

        psd = {
            "SettlementStatesV2": ring_buffer,
            "SettlementStateRingBufferIndexV2": 5,
            # No SettlementLocalSaveData
        }
        tab = SettlementsTab()
        tab.set_data(psd)
        assert tab._combo.count() == 1
        assert "Fallback Town" in tab._combo.itemText(0)


class TestSettlementNameDisplay:
    """R-SET-01: Actual settlement name from save data."""

    def test_name_displayed(self):
        from nmstoolkit.gui.tabs.settlements_tab import SettlementsTab

        psd = {
            "SettlementStatesV2": [_make_settlement(name="127.0.0.1", seed="0xABCD")],
            "SettlementStateRingBufferIndexV2": 0,
            "SettlementLocalSaveData": [_make_local_save_data("0xABCD")],
        }
        tab = SettlementsTab()
        tab.set_data(psd)
        assert tab._name_label.text() == "127.0.0.1"

    def test_unnamed_settlement_shows_placeholder(self):
        from nmstoolkit.gui.tabs.settlements_tab import SettlementsTab

        psd = {
            "SettlementStatesV2": [_make_settlement(name="", seed="0xABCD")],
            "SettlementStateRingBufferIndexV2": 0,
            "SettlementLocalSaveData": [_make_local_save_data("0xABCD")],
        }
        tab = SettlementsTab()
        tab.set_data(psd)
        assert tab._name_label.text() == "(Unnamed)"


class TestSettlementStatsDisplay:
    """R-SET-02: Stats are visible and editable."""

    def test_stats_populated_from_list(self):
        from nmstoolkit.gui.tabs.settlements_tab import SettlementsTab

        stats = [0, 4, 0, -17618, 43, 0, 1000, 923]
        psd = {
            "SettlementStatesV2": [_make_settlement(stats=stats, seed="0xABCD")],
            "SettlementStateRingBufferIndexV2": 0,
            "SettlementLocalSaveData": [_make_local_save_data("0xABCD")],
        }
        tab = SettlementsTab()
        tab.set_data(psd)
        # Stats array maps to stat names in order
        assert tab._stat_editors["Happiness"].value() == 4
        assert tab._stat_editors["Upkeep"].value() == 43

    def test_population_displayed(self):
        from nmstoolkit.gui.tabs.settlements_tab import SettlementsTab

        psd = {
            "SettlementStatesV2": [_make_settlement(population=129, seed="0xABCD")],
            "SettlementStateRingBufferIndexV2": 0,
            "SettlementLocalSaveData": [_make_local_save_data("0xABCD")],
        }
        tab = SettlementsTab()
        tab.set_data(psd)
        assert tab._stat_editors["Population"].value() == 129

    def test_stat_writeback(self):
        """Changing a stat value writes back to the data dict."""
        from nmstoolkit.gui.tabs.settlements_tab import SettlementsTab

        settlement = _make_settlement(stats=[0, 50, 0, 0, 0, 0, 0, 0], population=100, seed="0xABCD")
        psd = {
            "SettlementStatesV2": [settlement],
            "SettlementStateRingBufferIndexV2": 0,
            "SettlementLocalSaveData": [_make_local_save_data("0xABCD")],
        }
        tab = SettlementsTab()
        tab.set_data(psd)
        tab._stat_editors["Happiness"].setValue(99)
        assert settlement["Stats"][1] == 99

    def test_population_writeback(self):
        """Changing population writes back to the data dict."""
        from nmstoolkit.gui.tabs.settlements_tab import SettlementsTab

        settlement = _make_settlement(population=100, seed="0xABCD")
        psd = {
            "SettlementStatesV2": [settlement],
            "SettlementStateRingBufferIndexV2": 0,
            "SettlementLocalSaveData": [_make_local_save_data("0xABCD")],
        }
        tab = SettlementsTab()
        tab.set_data(psd)
        tab._stat_editors["Population"].setValue(200)
        assert settlement["Population"] == 200


class TestSettlementProductionDisplay:
    """R-SET-04: Production state displayed and editable."""

    def test_production_items_displayed(self):
        from nmstoolkit.gui.tabs.settlements_tab import SettlementsTab

        settlement = _make_settlement(seed="0xABCD")
        settlement["ProductionState"] = [
            {"ElementId": "^FUEL1", "Amount": 100, "Cap": 500, "RateMultiplier": 1.5},
            {"ElementId": "^TECH_COMP", "Amount": 50, "Cap": 200, "RateMultiplier": 0.75},
        ]
        psd = {
            "SettlementStatesV2": [settlement],
            "SettlementStateRingBufferIndexV2": 0,
            "SettlementLocalSaveData": [_make_local_save_data("0xABCD")],
        }
        tab = SettlementsTab()
        tab.set_data(psd)
        # Should have 2 production rows
        assert len(tab._prod_rows) == 2
        assert tab._prod_rows[0]["amount"].value() == 100
        assert tab._prod_rows[1]["amount"].value() == 50

    def test_production_amount_writeback(self):
        from nmstoolkit.gui.tabs.settlements_tab import SettlementsTab

        settlement = _make_settlement(seed="0xABCD")
        settlement["ProductionState"] = [
            {"ElementId": "^FUEL1", "Amount": 100, "Cap": 500, "RateMultiplier": 1.0},
        ]
        psd = {
            "SettlementStatesV2": [settlement],
            "SettlementStateRingBufferIndexV2": 0,
            "SettlementLocalSaveData": [_make_local_save_data("0xABCD")],
        }
        tab = SettlementsTab()
        tab.set_data(psd)
        tab._prod_rows[0]["amount"].setValue(250)
        assert settlement["ProductionState"][0]["Amount"] == 250

    def test_production_cap_writeback(self):
        from nmstoolkit.gui.tabs.settlements_tab import SettlementsTab

        settlement = _make_settlement(seed="0xABCD")
        settlement["ProductionState"] = [
            {"ElementId": "^FUEL1", "Amount": 100, "Cap": 500, "RateMultiplier": 1.0},
        ]
        psd = {
            "SettlementStatesV2": [settlement],
            "SettlementStateRingBufferIndexV2": 0,
            "SettlementLocalSaveData": [_make_local_save_data("0xABCD")],
        }
        tab = SettlementsTab()
        tab.set_data(psd)
        tab._prod_rows[0]["cap"].setValue(999)
        assert settlement["ProductionState"][0]["Cap"] == 999

    def test_production_rate_writeback(self):
        from nmstoolkit.gui.tabs.settlements_tab import SettlementsTab

        settlement = _make_settlement(seed="0xABCD")
        settlement["ProductionState"] = [
            {"ElementId": "^FUEL1", "Amount": 100, "Cap": 500, "RateMultiplier": 1.0},
        ]
        psd = {
            "SettlementStatesV2": [settlement],
            "SettlementStateRingBufferIndexV2": 0,
            "SettlementLocalSaveData": [_make_local_save_data("0xABCD")],
        }
        tab = SettlementsTab()
        tab.set_data(psd)
        tab._prod_rows[0]["rate"].setValue(2.5)
        assert abs(settlement["ProductionState"][0]["RateMultiplier"] - 2.5) < 0.01

    def test_empty_production_state(self):
        from nmstoolkit.gui.tabs.settlements_tab import SettlementsTab

        settlement = _make_settlement(seed="0xABCD")
        # No ProductionState key
        psd = {
            "SettlementStatesV2": [settlement],
            "SettlementStateRingBufferIndexV2": 0,
            "SettlementLocalSaveData": [_make_local_save_data("0xABCD")],
        }
        tab = SettlementsTab()
        tab.set_data(psd)
        assert len(tab._prod_rows) == 0


class TestSettlementQOL:
    """R-SET-05: Race, address, and building count displayed."""

    def test_race_displayed(self):
        from nmstoolkit.gui.tabs.settlements_tab import SettlementsTab

        settlement = _make_settlement(seed="0xABCD")
        settlement["Race"] = {"AlienRace": "Korvax"}
        psd = {
            "SettlementStatesV2": [settlement],
            "SettlementStateRingBufferIndexV2": 0,
            "SettlementLocalSaveData": [_make_local_save_data("0xABCD")],
        }
        tab = SettlementsTab()
        tab.set_data(psd)
        assert tab._race_label.text() == "Korvax"

    def test_address_displayed(self):
        from nmstoolkit.gui.tabs.settlements_tab import SettlementsTab

        settlement = _make_settlement(seed="0xABCD")
        settlement["UniverseAddress"] = 0x0001000200030004
        psd = {
            "SettlementStatesV2": [settlement],
            "SettlementStateRingBufferIndexV2": 0,
            "SettlementLocalSaveData": [_make_local_save_data("0xABCD")],
        }
        tab = SettlementsTab()
        tab.set_data(psd)
        assert tab._address_label.text() != "—"

    def test_building_count_displayed(self):
        from nmstoolkit.gui.tabs.settlements_tab import SettlementsTab

        settlement = _make_settlement(seed="0xABCD")
        # 41 non-zero out of 48
        settlement["BuildingStates"] = [1] * 41 + [0] * 7
        psd = {
            "SettlementStatesV2": [settlement],
            "SettlementStateRingBufferIndexV2": 0,
            "SettlementLocalSaveData": [_make_local_save_data("0xABCD")],
        }
        tab = SettlementsTab()
        tab.set_data(psd)
        assert "41" in tab._buildings_label.text()
        assert "48" in tab._buildings_label.text()


class TestSettlementEmptyData:
    """Edge cases: no data, no settlements, empty PSD."""

    def test_no_settlements_shows_message(self):
        from nmstoolkit.gui.tabs.settlements_tab import SettlementsTab

        tab = SettlementsTab()
        tab.set_data({})
        assert tab._combo.count() == 1
        assert "No owned" in tab._combo.itemText(0).lower() or "no" in tab._combo.itemText(0).lower()

    def test_all_empty_ring_buffer(self):
        from nmstoolkit.gui.tabs.settlements_tab import SettlementsTab

        psd = {
            "SettlementStatesV2": [_make_empty_settlement()] * 100,
            "SettlementStateRingBufferIndexV2": 34,
            "SettlementLocalSaveData": [],
        }
        tab = SettlementsTab()
        tab.set_data(psd)
        assert tab._combo.count() == 1  # "No owned settlements found"


class TestSettlementPerks:
    """R-SET-06: Settlement perks selectable via dropdown and add/removable."""

    def test_perk_list_displayed(self):
        from nmstoolkit.gui.tabs.settlements_tab import SettlementsTab

        settlement = _make_settlement(seed="0xABCD", perks=["^STARTING_NEG1", "^GIFT_PROD1"])
        psd = {
            "SettlementStatesV2": [settlement],
            "SettlementStateRingBufferIndexV2": 0,
            "SettlementLocalSaveData": [_make_local_save_data("0xABCD")],
        }
        tab = SettlementsTab()
        tab.set_data(psd)
        assert tab._perk_list.count() == 2

    def test_perk_add(self):
        from nmstoolkit.gui.tabs.settlements_tab import SettlementsTab

        settlement = _make_settlement(seed="0xABCD", perks=["^STARTING_NEG1"])
        psd = {
            "SettlementStatesV2": [settlement],
            "SettlementStateRingBufferIndexV2": 0,
            "SettlementLocalSaveData": [_make_local_save_data("0xABCD")],
        }
        tab = SettlementsTab()
        tab.set_data(psd)
        # Select a perk from the dropdown and add it
        tab._perk_combo.setCurrentIndex(0)
        tab._on_add_perk()
        assert len(settlement["Perks"]) == 2

    def test_perk_remove_selected(self):
        from nmstoolkit.gui.tabs.settlements_tab import SettlementsTab

        settlement = _make_settlement(seed="0xABCD", perks=["^STARTING_NEG1", "^GIFT_PROD1"])
        psd = {
            "SettlementStatesV2": [settlement],
            "SettlementStateRingBufferIndexV2": 0,
            "SettlementLocalSaveData": [_make_local_save_data("0xABCD")],
        }
        tab = SettlementsTab()
        tab.set_data(psd)
        tab._perk_list.setCurrentRow(0)
        tab._on_remove_perk()
        assert len(settlement["Perks"]) == 1

    def test_perk_names_resolved(self):
        """Perks should show human-readable names from settlements.json."""
        from nmstoolkit.gui.tabs.settlements_tab import SettlementsTab

        settlement = _make_settlement(seed="0xABCD", perks=["^STARTING_NEG1"])
        psd = {
            "SettlementStatesV2": [settlement],
            "SettlementStateRingBufferIndexV2": 0,
            "SettlementLocalSaveData": [_make_local_save_data("0xABCD")],
        }
        tab = SettlementsTab()
        tab.set_data(psd)
        # The perk list item should show a name, not just the ID
        text = tab._perk_list.item(0).text()
        assert text != "^STARTING_NEG1"  # Should be resolved to friendly name
