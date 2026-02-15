"""Tests for bases tab — base part budget table.

R-BASE-01: Table shows all bases with part counts and wire counts.
R-BASE-02: Table is sortable by clicking column headers.
R-BASE-03: Total parts shown with percentage of 16K save limit.
R-BASE-04: Wire count column identifies U_POWERLINE objects.
"""

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
