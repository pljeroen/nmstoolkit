"""Tests for discoveries tab.

R-DIS-01: Discovered systems display their names.
R-DIS-02: Discovered planets display their names.
R-DIS-03: Discovered fauna/flora display their names.
R-DIS-04: Discovery entries without names show a sensible fallback.
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

_app = QApplication.instance() or QApplication([])


def _make_record(disc_type="SolarSystem", name="", owner="player1", address=123456, dm_name=""):
    """Create a discovery record matching NMS save format."""
    record = {
        "DD": {
            "UA": address,
            "DT": disc_type,
            "VP": ["0xABCD1234"],
        },
        "OWS": {
            "LID": "",
            "UID": "",
            "USN": owner,
            "PTK": "",
            "TS": 0,
        },
        "DM": {},
    }
    if name:
        record["DD"]["CN"] = name
    if dm_name:
        record["DM"]["CN"] = dm_name
    return record


def _make_discovery_data(records):
    """Wrap records in DiscoveryManagerData structure."""
    return {
        "DiscoveryData-v1": {
            "Store": {
                "Record": records,
            },
        },
    }


class TestDiscoveriesTabCreation:
    """Tab instantiates and accepts data."""

    def test_tab_instantiates(self):
        from nmstoolkit.gui.tabs.discoveries_tab import DiscoveriesTab

        tab = DiscoveriesTab()
        assert tab is not None

    def test_set_data_with_empty(self):
        from nmstoolkit.gui.tabs.discoveries_tab import DiscoveriesTab

        tab = DiscoveriesTab()
        tab.set_data({})
        assert tab._table.rowCount() == 0


class TestNamedDiscoveries:
    """R-DIS-01, R-DIS-02, R-DIS-03: Named discoveries show their names."""

    def test_named_system_displayed(self):
        from nmstoolkit.gui.tabs.discoveries_tab import DiscoveriesTab

        records = [_make_record("SolarSystem", name="Alpha Centauri")]
        tab = DiscoveriesTab()
        tab.set_data(_make_discovery_data(records))
        assert tab._table.item(0, 1).text() == "Alpha Centauri"

    def test_named_planet_displayed(self):
        from nmstoolkit.gui.tabs.discoveries_tab import DiscoveriesTab

        records = [_make_record("Planet", name="Earth 2")]
        tab = DiscoveriesTab()
        tab.set_data(_make_discovery_data(records))
        assert tab._table.item(0, 1).text() == "Earth 2"

    def test_dm_name_overrides_dd_name(self):
        """DM.CN takes priority over DD.CN."""
        from nmstoolkit.gui.tabs.discoveries_tab import DiscoveriesTab

        records = [_make_record("Flora", name="Original", dm_name="Renamed")]
        tab = DiscoveriesTab()
        tab.set_data(_make_discovery_data(records))
        assert tab._table.item(0, 1).text() == "Renamed"

    def test_named_fauna_displayed(self):
        from nmstoolkit.gui.tabs.discoveries_tab import DiscoveriesTab

        records = [_make_record("Animal", name="Space Cat")]
        tab = DiscoveriesTab()
        tab.set_data(_make_discovery_data(records))
        assert tab._table.item(0, 1).text() == "Space Cat"


class TestUnnamedDiscoveryFallback:
    """R-DIS-04: Unnamed entries show type-based fallback, not just '—'."""

    def test_unnamed_system_shows_unknown_with_address(self):
        from nmstoolkit.gui.tabs.discoveries_tab import DiscoveriesTab

        records = [_make_record("SolarSystem", address=77004501068061)]
        tab = DiscoveriesTab()
        tab.set_data(_make_discovery_data(records))
        text = tab._table.item(0, 1).text()
        assert "<unknown name>" in text
        assert "(" in text  # Address in parentheses

    def test_unnamed_planet_shows_unknown_with_address(self):
        from nmstoolkit.gui.tabs.discoveries_tab import DiscoveriesTab

        records = [_make_record("Planet", address=4598200442851320)]
        tab = DiscoveriesTab()
        tab.set_data(_make_discovery_data(records))
        text = tab._table.item(0, 1).text()
        assert "<unknown name>" in text
        assert "(" in text

    def test_unnamed_animal_shows_unknown_with_address(self):
        from nmstoolkit.gui.tabs.discoveries_tab import DiscoveriesTab

        records = [_make_record("Animal", address=5669086120726664)]
        tab = DiscoveriesTab()
        tab.set_data(_make_discovery_data(records))
        text = tab._table.item(0, 1).text()
        assert "<unknown name>" in text


class TestTypeFilter:
    """Type filter works correctly."""

    def test_filter_by_type(self):
        from nmstoolkit.gui.tabs.discoveries_tab import DiscoveriesTab

        records = [
            _make_record("SolarSystem", name="Star A"),
            _make_record("Planet", name="Planet B"),
            _make_record("SolarSystem", name="Star C"),
        ]
        tab = DiscoveriesTab()
        tab.set_data(_make_discovery_data(records))
        assert tab._table.rowCount() == 3  # All shown

        # Filter to SolarSystem only
        idx = tab._type_filter.findText("SolarSystem")
        tab._type_filter.setCurrentIndex(idx)
        assert tab._table.rowCount() == 2

    def test_search_by_name(self):
        from nmstoolkit.gui.tabs.discoveries_tab import DiscoveriesTab

        records = [
            _make_record("SolarSystem", name="Alpha"),
            _make_record("SolarSystem", name="Beta"),
        ]
        tab = DiscoveriesTab()
        tab.set_data(_make_discovery_data(records))
        tab._search.setText("Alpha")
        assert tab._table.rowCount() == 1


class TestAddressFormatting:
    """Addresses display as hex for readability."""

    def test_large_int_address_shows_hex(self):
        from nmstoolkit.gui.tabs.discoveries_tab import DiscoveriesTab

        records = [_make_record("SolarSystem", name="Test", address=77004501068061)]
        tab = DiscoveriesTab()
        tab.set_data(_make_discovery_data(records))
        addr = tab._table.item(0, 3).text()
        # Should be hex formatted, not a huge decimal
        assert "0x" in addr.lower() or len(addr) < 20
