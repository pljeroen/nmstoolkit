"""Tests for bases tab — base part budget table and base library.

R-BASE-01: Table shows all bases with part counts and wire counts.
R-BASE-02: Table is sortable by clicking column headers.
R-BASE-03: Total parts shown with percentage of 16K save limit.
R-BASE-04: Wire count column identifies U_POWERLINE objects.
R-BASE-06: In-tool base library for storing and swapping bases.
"""

import json
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

_app = QApplication.instance() or QApplication([])


def _make_base(name="Test Base", objects=None):
    """Create a base dict matching NMS save format."""
    return {
        "Name": name,
        "BaseType": {"PersistentBaseTypes": "HomePlanetBase"},
        "GalacticAddress": 0,
        "Objects": objects or [],
    }


def _make_object(object_id="^S_FLOOR"):
    """Create a base object."""
    return {"ObjectID": object_id, "Position": [0.0, 0.0, 0.0]}


class TestBasePartBudgetTable:
    """R-BASE-01: Table shows bases with part and wire counts."""

    def test_table_exists(self):
        from nmstoolkit.gui.tabs.bases_tab import BasesTab

        tab = BasesTab()
        assert hasattr(tab, "_budget_table")

    def test_table_has_correct_columns(self):
        from nmstoolkit.gui.tabs.bases_tab import BasesTab

        tab = BasesTab()
        headers = []
        for col in range(tab._budget_table.columnCount()):
            headers.append(tab._budget_table.horizontalHeaderItem(col).text())
        assert "Base Name" in headers
        assert "Parts" in headers
        assert "Wires" in headers

    def test_table_populated_with_bases(self):
        from nmstoolkit.gui.tabs.bases_tab import BasesTab

        psd = {
            "PersistentPlayerBases": [
                _make_base("Alpha", [_make_object() for _ in range(10)]),
                _make_base("Beta", [_make_object() for _ in range(5)]),
            ],
        }
        tab = BasesTab()
        tab.set_data(psd)
        assert tab._budget_table.rowCount() == 2

    def test_part_counts_correct(self):
        from nmstoolkit.gui.tabs.bases_tab import BasesTab

        psd = {
            "PersistentPlayerBases": [
                _make_base("Alpha", [_make_object() for _ in range(10)]),
            ],
        }
        tab = BasesTab()
        tab.set_data(psd)
        # Parts column should show "10"
        parts_col = _find_column(tab._budget_table, "Parts")
        assert tab._budget_table.item(0, parts_col).text() == "10"


class TestWireCount:
    """R-BASE-04: Wire count identifies U_POWERLINE objects."""

    def test_wire_count_correct(self):
        from nmstoolkit.gui.tabs.bases_tab import BasesTab

        objects = [
            _make_object("^S_FLOOR"),
            _make_object("^U_POWERLINE"),
            _make_object("^U_POWERLINE"),
            _make_object("^CUBEGLASS"),
            _make_object("^U_POWERLINE"),
        ]
        psd = {"PersistentPlayerBases": [_make_base("Wired", objects)]}
        tab = BasesTab()
        tab.set_data(psd)
        wires_col = _find_column(tab._budget_table, "Wires")
        assert tab._budget_table.item(0, wires_col).text() == "3"

    def test_no_wires(self):
        from nmstoolkit.gui.tabs.bases_tab import BasesTab

        objects = [_make_object("^S_FLOOR") for _ in range(5)]
        psd = {"PersistentPlayerBases": [_make_base("Clean", objects)]}
        tab = BasesTab()
        tab.set_data(psd)
        wires_col = _find_column(tab._budget_table, "Wires")
        assert tab._budget_table.item(0, wires_col).text() == "0"


class TestTotalBudget:
    """R-BASE-03: Total parts shown with save limit context."""

    def test_total_label_shows_count(self):
        from nmstoolkit.gui.tabs.bases_tab import BasesTab

        psd = {
            "PersistentPlayerBases": [
                _make_base("A", [_make_object() for _ in range(100)]),
                _make_base("B", [_make_object() for _ in range(200)]),
            ],
        }
        tab = BasesTab()
        tab.set_data(psd)
        text = tab._total_parts_label.text()
        assert "300" in text
        assert "16" in text.lower() or "%" in text  # Shows limit context

    def test_empty_bases(self):
        from nmstoolkit.gui.tabs.bases_tab import BasesTab

        tab = BasesTab()
        tab.set_data({"PersistentPlayerBases": []})
        assert tab._budget_table.rowCount() == 0


class TestTableSorting:
    """R-BASE-02: Table is sortable by column headers."""

    def test_sorting_enabled(self):
        from nmstoolkit.gui.tabs.bases_tab import BasesTab

        tab = BasesTab()
        assert tab._budget_table.isSortingEnabled()

    def test_numeric_sort_parts(self):
        """Sorting by parts column should sort numerically, not lexicographically."""
        from nmstoolkit.gui.tabs.bases_tab import BasesTab

        psd = {
            "PersistentPlayerBases": [
                _make_base("Small", [_make_object() for _ in range(5)]),
                _make_base("Big", [_make_object() for _ in range(100)]),
                _make_base("Medium", [_make_object() for _ in range(50)]),
            ],
        }
        tab = BasesTab()
        tab.set_data(psd)
        parts_col = _find_column(tab._budget_table, "Parts")
        # Sort ascending
        tab._budget_table.sortItems(parts_col)
        # First row should be smallest
        assert tab._budget_table.item(0, parts_col).text() == "5"
        assert tab._budget_table.item(2, parts_col).text() == "100"


def _find_column(table, header_text):
    """Find column index by header text."""
    for col in range(table.columnCount()):
        item = table.horizontalHeaderItem(col)
        if item and item.text() == header_text:
            return col
    raise ValueError(f"Column '{header_text}' not found")


class TestBaseExportImport:
    """R-BASE-05: Export and import individual bases as JSON."""

    def test_export_button_exists(self):
        from nmstoolkit.gui.tabs.bases_tab import BasesTab

        tab = BasesTab()
        assert hasattr(tab, "_export_btn")

    def test_import_button_exists(self):
        from nmstoolkit.gui.tabs.bases_tab import BasesTab

        tab = BasesTab()
        assert hasattr(tab, "_import_btn")

    def test_export_base_data(self):
        """Export should produce a dict with Objects, Name, BaseType."""
        from nmstoolkit.gui.tabs.bases_tab import BasesTab

        objects = [_make_object("^S_FLOOR"), _make_object("^S_WALL")]
        psd = {"PersistentPlayerBases": [_make_base("Export Test", objects)]}
        tab = BasesTab()
        tab.set_data(psd)
        exported = tab._get_export_data(0)
        assert exported["Name"] == "Export Test"
        assert len(exported["Objects"]) == 2
        assert "BaseType" in exported

    def test_import_base_adds_to_list(self):
        """Importing a base should add it to PersistentPlayerBases."""
        from nmstoolkit.gui.tabs.bases_tab import BasesTab

        psd = {"PersistentPlayerBases": [_make_base("Existing")]}
        tab = BasesTab()
        tab.set_data(psd)
        new_base = {
            "Name": "Imported Base",
            "BaseType": {"PersistentBaseTypes": "HomePlanetBase"},
            "Objects": [_make_object("^S_FLOOR")],
            "GalacticAddress": 0,
        }
        tab._import_base_data(new_base)
        assert len(psd["PersistentPlayerBases"]) == 2
        assert psd["PersistentPlayerBases"][-1]["Name"] == "Imported Base"


class TestBaseLibrary:
    """R-BASE-06: In-tool base library for storing and swapping bases."""

    def test_library_widgets_exist(self):
        """Library group box, list, and buttons exist in UI."""
        from nmstoolkit.gui.tabs.bases_tab import BasesTab

        tab = BasesTab()
        assert hasattr(tab, "_library_list")
        assert hasattr(tab, "_lib_save_btn")
        assert hasattr(tab, "_lib_load_btn")
        assert hasattr(tab, "_lib_delete_btn")

    def test_save_to_library(self, tmp_path, monkeypatch):
        """Save current base to library dir, file appears on disk."""
        from nmstoolkit.gui.tabs import bases_tab
        from nmstoolkit.gui.tabs.bases_tab import BasesTab

        monkeypatch.setattr(bases_tab, "_base_library_dir", lambda: tmp_path)

        objects = [_make_object("^S_FLOOR") for _ in range(5)]
        psd = {"PersistentPlayerBases": [_make_base("My Tower", objects)]}
        tab = BasesTab()
        tab.set_data(psd)
        tab._on_save_to_library()

        files = list(tmp_path.glob("*.json"))
        assert len(files) == 1
        data = json.loads(files[0].read_text())
        assert data["Name"] == "My Tower"
        assert len(data["Objects"]) == 5

    def test_load_from_library(self, tmp_path, monkeypatch):
        """Load replaces current base Objects from library entry."""
        from nmstoolkit.gui.tabs import bases_tab
        from nmstoolkit.gui.tabs.bases_tab import BasesTab

        monkeypatch.setattr(bases_tab, "_base_library_dir", lambda: tmp_path)

        # Save a library entry with 3 objects
        lib_data = _make_base("Library Base", [_make_object("^S_WALL") for _ in range(3)])
        lib_file = tmp_path / "library_base_20260215.json"
        lib_file.write_text(json.dumps(lib_data))

        # Current base has 1 object
        psd = {"PersistentPlayerBases": [
            _make_base("Current Base", [_make_object("^S_FLOOR")]),
        ]}
        tab = BasesTab()
        tab.set_data(psd)

        # Select the library entry and load
        tab._refresh_library()
        tab._library_list.setCurrentRow(0)
        tab._on_load_from_library()

        # Objects replaced, but Name/Address/BaseType preserved
        base = psd["PersistentPlayerBases"][0]
        assert len(base["Objects"]) == 3
        assert base["Objects"][0]["ObjectID"] == "^S_WALL"
        assert base["Name"] == "Current Base"  # Name preserved

    def test_delete_from_library(self, tmp_path, monkeypatch):
        """Delete removes selected library entry from disk."""
        from nmstoolkit.gui.tabs import bases_tab
        from nmstoolkit.gui.tabs.bases_tab import BasesTab

        monkeypatch.setattr(bases_tab, "_base_library_dir", lambda: tmp_path)

        # Create a library file
        lib_data = _make_base("Doomed Base", [_make_object()])
        lib_file = tmp_path / "doomed_base_20260215.json"
        lib_file.write_text(json.dumps(lib_data))

        tab = BasesTab()
        tab.set_data({"PersistentPlayerBases": []})
        tab._refresh_library()
        assert tab._library_list.count() == 1

        tab._library_list.setCurrentRow(0)
        tab._on_delete_from_library()

        assert not lib_file.exists()
        assert tab._library_list.count() == 0

    def test_library_list_shows_saved(self, tmp_path, monkeypatch):
        """Library list populated after save."""
        from nmstoolkit.gui.tabs import bases_tab
        from nmstoolkit.gui.tabs.bases_tab import BasesTab

        monkeypatch.setattr(bases_tab, "_base_library_dir", lambda: tmp_path)

        objects = [_make_object() for _ in range(7)]
        psd = {"PersistentPlayerBases": [_make_base("Listed Base", objects)]}
        tab = BasesTab()
        tab.set_data(psd)
        tab._on_save_to_library()

        assert tab._library_list.count() == 1
        item_text = tab._library_list.item(0).text()
        assert "Listed Base" in item_text
        assert "7" in item_text  # part count shown
