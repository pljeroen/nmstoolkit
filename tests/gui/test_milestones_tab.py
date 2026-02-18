"""Tests for MilestonesTab layout and import/export."""

import json
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from nmstoolkit.gui.tabs.milestones_tab import MilestonesTab


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _make_psd():
    return {
        "Stats": [
            {
                "GroupId": "^GLOBAL_STATS",
                "Stats": [
                    {
                        "Id": "^TRA_STANDING",
                        "Value": {"IntValue": 12, "FloatValue": 0.0, "Denominator": 0},
                    },
                    {
                        "Id": "^EGUILD_STAND",
                        "Value": {"IntValue": 4, "FloatValue": 0.0, "Denominator": 0},
                    },
                ],
            }
        ]
    }


def test_has_top_two_pane_and_actions(qapp):
    tab = MilestonesTab()
    assert hasattr(tab, "_rep_editors")
    assert hasattr(tab, "_guild_editors")
    assert hasattr(tab, "_export_btn")
    assert hasattr(tab, "_import_btn")


def test_export_global_stats_json(qapp, tmp_path, monkeypatch):
    tab = MilestonesTab()
    psd = _make_psd()
    tab.set_data(psd)
    out = tmp_path / "milestones_stats.json"
    monkeypatch.setattr(
        "nmstoolkit.gui.tabs.milestones_tab.QFileDialog.getSaveFileName",
        lambda *args, **kwargs: (str(out), "JSON files (*.json)"),
    )
    tab._on_export()
    data = json.loads(out.read_text())
    assert data.get("GroupId") == "^GLOBAL_STATS"
    assert isinstance(data.get("Stats"), list)
    assert any(s.get("Id") == "^TRA_STANDING" for s in data["Stats"])


def test_import_global_stats_json(qapp, tmp_path, monkeypatch):
    tab = MilestonesTab()
    psd = _make_psd()
    tab.set_data(psd)
    src = tmp_path / "milestones_import.json"
    src.write_text(
        json.dumps(
            {
                "GroupId": "^GLOBAL_STATS",
                "Stats": [
                    {"Id": "^TRA_STANDING", "Value": {"IntValue": 77, "FloatValue": 0.0, "Denominator": 0}}
                ],
            }
        )
    )
    monkeypatch.setattr(
        "nmstoolkit.gui.tabs.milestones_tab.QFileDialog.getOpenFileName",
        lambda *args, **kwargs: (str(src), "JSON files (*.json)"),
    )
    tab._on_import()
    stats = psd["Stats"][0]["Stats"]
    assert len(stats) == 1
    assert stats[0]["Id"] == "^TRA_STANDING"
    assert stats[0]["Value"]["IntValue"] == 77

