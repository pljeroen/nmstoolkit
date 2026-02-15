"""Tests for discoveries tab.

R-DIS-01: Discovered systems display their names.
R-DIS-02: Discovered planets display their names.
R-DIS-03: Discovered fauna/flora display their names.
R-DIS-04: Discovery entries without names show a sensible fallback.
R-CONST-01: Constellation reset/backup/optimize.
"""

import json
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

    def test_large_int_address_decoded(self):
        from nmstoolkit.gui.tabs.discoveries_tab import DiscoveriesTab

        records = [_make_record("SolarSystem", name="Test", address=77004501068061)]
        tab = DiscoveriesTab()
        tab.set_data(_make_discovery_data(records))
        addr = tab._table.item(0, 3).text()
        # Should be decoded galactic address, not a huge decimal
        assert "Planet" in addr or "System" in addr or "Region" in addr


class TestUndiscoveredFilter:
    """R-DISC-01: Filter for undiscovered entries only."""

    def test_undiscovered_checkbox_exists(self):
        from nmstoolkit.gui.tabs.discoveries_tab import DiscoveriesTab

        tab = DiscoveriesTab()
        assert hasattr(tab, "_undiscovered_check")

    def test_undiscovered_filter_hides_named(self):
        """When undiscovered-only is checked, named entries should be hidden."""
        from nmstoolkit.gui.tabs.discoveries_tab import DiscoveriesTab

        records = [
            _make_record("SolarSystem", name="Named System"),
            _make_record("SolarSystem"),  # no name = undiscovered
            _make_record("Planet"),  # no name = undiscovered
        ]
        tab = DiscoveriesTab()
        tab.set_data(_make_discovery_data(records))
        assert tab._table.rowCount() == 3  # All shown initially
        tab._undiscovered_check.setChecked(True)
        assert tab._table.rowCount() == 2  # Only unnamed shown

    def test_address_decoded_as_galactic(self):
        """Address column should show decoded galactic coordinates."""
        from nmstoolkit.gui.tabs.discoveries_tab import DiscoveriesTab

        records = [_make_record("SolarSystem", name="Test", address=0x0001000200030004)]
        tab = DiscoveriesTab()
        tab.set_data(_make_discovery_data(records))
        addr_text = tab._table.item(0, 3).text()
        # Should contain decoded galactic address info, not just hex
        assert "Planet" in addr_text or "System" in addr_text or "Region" in addr_text


class TestDiscoveryBackupRestore:
    """R-DISC-02: Backup and restore discovery data."""

    def test_backup_restore_buttons_exist(self):
        from nmstoolkit.gui.tabs.discoveries_tab import DiscoveriesTab

        tab = DiscoveriesTab()
        assert hasattr(tab, "_disc_backup_btn")
        assert hasattr(tab, "_disc_restore_btn")

    def test_backup_writes_file(self, tmp_path, monkeypatch):
        from nmstoolkit.gui.tabs.discoveries_tab import DiscoveriesTab

        records = [_make_record("SolarSystem", name="Star A")]
        disc_data = _make_discovery_data(records)
        tab = DiscoveriesTab()
        tab.set_data(disc_data)

        backup_path = str(tmp_path / "discoveries.json")
        monkeypatch.setattr(
            "nmstoolkit.gui.tabs.discoveries_tab.QFileDialog.getSaveFileName",
            lambda *a, **kw: (backup_path, ""),
        )
        tab._on_discovery_backup()
        assert (tmp_path / "discoveries.json").exists()
        data = json.loads((tmp_path / "discoveries.json").read_text())
        assert "DiscoveryData-v1" in data

    def test_restore_loads_file(self, tmp_path, monkeypatch):
        from nmstoolkit.gui.tabs.discoveries_tab import DiscoveriesTab

        # Create backup file with known data
        records = [_make_record("Planet", name="Restored Planet")]
        disc_data = _make_discovery_data(records)
        backup_path = tmp_path / "discoveries.json"
        backup_path.write_text(json.dumps(disc_data))

        # Start with empty discoveries
        tab = DiscoveriesTab()
        tab.set_data({})
        assert tab._table.rowCount() == 0

        monkeypatch.setattr(
            "nmstoolkit.gui.tabs.discoveries_tab.QFileDialog.getOpenFileName",
            lambda *a, **kw: (str(backup_path), ""),
        )
        tab._on_discovery_restore()
        assert tab._table.rowCount() == 1
        assert tab._table.item(0, 1).text() == "Restored Planet"


def _encode_galactic_address(voxel_x, voxel_y, voxel_z, system=1, planet=0):
    """Encode voxel coordinates into a galactic address integer."""
    addr = system & 0xFFFF
    addr |= (planet & 0x7) << 16
    addr |= (voxel_x & 0xFFF) << 19
    addr |= (voxel_y & 0xFF) << 31
    addr |= (voxel_z & 0xFFF) << 39
    return addr


class TestConstellationWidgets:
    """R-CONST-01: Constellation UI elements exist."""

    def test_constellation_group_exists(self):
        from nmstoolkit.gui.tabs.discoveries_tab import DiscoveriesTab

        tab = DiscoveriesTab()
        assert hasattr(tab, "_const_reset_btn")
        assert hasattr(tab, "_const_optimize_btn")
        assert hasattr(tab, "_const_backup_btn")
        assert hasattr(tab, "_const_restore_btn")
        assert hasattr(tab, "_const_count_label")


class TestConstellationReset:
    """R-CONST-01: Reset clears VisitedSystems."""

    def test_reset_clears_visited_systems(self):
        from nmstoolkit.gui.tabs.discoveries_tab import DiscoveriesTab

        psd = {"VisitedSystems": [111, 222, 333]}
        tab = DiscoveriesTab()
        tab.set_data({})
        tab.set_player_state(psd)
        tab._on_constellation_reset()
        assert psd["VisitedSystems"] == []

    def test_reset_updates_count_label(self):
        from nmstoolkit.gui.tabs.discoveries_tab import DiscoveriesTab

        psd = {"VisitedSystems": [111, 222]}
        tab = DiscoveriesTab()
        tab.set_data({})
        tab.set_player_state(psd)
        assert "2" in tab._const_count_label.text()
        tab._on_constellation_reset()
        assert "0" in tab._const_count_label.text()


class TestConstellationBackupRestore:
    """R-CONST-01: Backup and restore VisitedSystems."""

    def test_backup_and_restore(self, tmp_path, monkeypatch):
        from nmstoolkit.gui.tabs import discoveries_tab
        from nmstoolkit.gui.tabs.discoveries_tab import DiscoveriesTab

        original = [111, 222, 333]
        psd = {"VisitedSystems": list(original)}
        tab = DiscoveriesTab()
        tab.set_data({})
        tab.set_player_state(psd)

        # Monkeypatch file dialog to return tmp_path file
        backup_path = str(tmp_path / "constellations.json")
        monkeypatch.setattr(
            "nmstoolkit.gui.tabs.discoveries_tab.QFileDialog.getSaveFileName",
            lambda *a, **kw: (backup_path, ""),
        )
        tab._on_constellation_backup()
        assert (tmp_path / "constellations.json").exists()

        # Clear and restore
        psd["VisitedSystems"] = []
        monkeypatch.setattr(
            "nmstoolkit.gui.tabs.discoveries_tab.QFileDialog.getOpenFileName",
            lambda *a, **kw: (backup_path, ""),
        )
        tab._on_constellation_restore()
        assert psd["VisitedSystems"] == original


class TestConstellationOptimize:
    """R-CONST-01: Optimize reorders VisitedSystems for minimal path length."""

    def test_optimize_reduces_total_distance(self):
        from nmstoolkit.gui.tabs.discoveries_tab import DiscoveriesTab

        # Create a deliberately bad order: zigzag across space
        # Points along a line: (0,0,0), (100,0,0), (200,0,0), (300,0,0)
        # but ordered: 0, 200, 100, 300 (zigzag)
        addrs = [
            _encode_galactic_address(0, 0, 0, system=1),
            _encode_galactic_address(200, 0, 0, system=2),
            _encode_galactic_address(100, 0, 0, system=3),
            _encode_galactic_address(300, 0, 0, system=4),
        ]
        psd = {"VisitedSystems": list(addrs)}
        tab = DiscoveriesTab()
        tab.set_data({})
        tab.set_player_state(psd)

        from nmstoolkit.gui.tabs.discoveries_tab import _total_path_distance
        dist_before = _total_path_distance(psd["VisitedSystems"])

        tab._on_constellation_optimize()

        dist_after = _total_path_distance(psd["VisitedSystems"])
        assert dist_after <= dist_before

    def test_optimize_preserves_all_systems(self):
        """Optimize must not lose or duplicate any system."""
        from nmstoolkit.gui.tabs.discoveries_tab import DiscoveriesTab

        addrs = [
            _encode_galactic_address(x, 0, 0, system=i + 1)
            for i, x in enumerate([50, 300, 150, 0, 200])
        ]
        psd = {"VisitedSystems": list(addrs)}
        tab = DiscoveriesTab()
        tab.set_data({})
        tab.set_player_state(psd)
        tab._on_constellation_optimize()

        assert sorted(psd["VisitedSystems"]) == sorted(addrs)
        assert len(psd["VisitedSystems"]) == 5

    def test_optimize_handles_empty(self):
        from nmstoolkit.gui.tabs.discoveries_tab import DiscoveriesTab

        psd = {"VisitedSystems": []}
        tab = DiscoveriesTab()
        tab.set_data({})
        tab.set_player_state(psd)
        tab._on_constellation_optimize()
        assert psd["VisitedSystems"] == []

    def test_optimize_handles_single(self):
        from nmstoolkit.gui.tabs.discoveries_tab import DiscoveriesTab

        addr = _encode_galactic_address(100, 50, 25, system=1)
        psd = {"VisitedSystems": [addr]}
        tab = DiscoveriesTab()
        tab.set_data({})
        tab.set_player_state(psd)
        tab._on_constellation_optimize()
        assert psd["VisitedSystems"] == [addr]


class TestPathDistanceFunction:
    """Unit tests for the path distance calculation."""

    def test_total_distance_collinear(self):
        """Points on a line: total distance = end-to-end distance."""
        from nmstoolkit.gui.tabs.discoveries_tab import _total_path_distance

        addrs = [
            _encode_galactic_address(0, 0, 0, system=1),
            _encode_galactic_address(100, 0, 0, system=2),
            _encode_galactic_address(200, 0, 0, system=3),
        ]
        dist = _total_path_distance(addrs)
        # Should be ~200 (100 + 100) in voxel X units
        assert 195 < dist < 205

    def test_total_distance_zigzag_longer(self):
        """Zigzag order should be longer than sorted order."""
        from nmstoolkit.gui.tabs.discoveries_tab import _total_path_distance

        sorted_addrs = [
            _encode_galactic_address(0, 0, 0, system=1),
            _encode_galactic_address(100, 0, 0, system=2),
            _encode_galactic_address(200, 0, 0, system=3),
        ]
        zigzag_addrs = [
            _encode_galactic_address(0, 0, 0, system=1),
            _encode_galactic_address(200, 0, 0, system=3),
            _encode_galactic_address(100, 0, 0, system=2),
        ]
        assert _total_path_distance(zigzag_addrs) > _total_path_distance(sorted_addrs)
