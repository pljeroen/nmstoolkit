"""Exosuit editor tab — inventory grids, currencies, health/shield/energy."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QScrollArea,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from nmstoolkit.gui.widgets.inventory_grid import InventoryGrid
from nmstoolkit.gui.widgets.stat_editor import StatEditor


class ExosuitTab(QWidget):
    def __init__(self):
        super().__init__()
        self._data = None
        self._build_ui()

    def _build_ui(self):
        layout = QHBoxLayout(self)

        # Left panel: stats
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left.setMaximumWidth(300)

        # Currencies
        curr_group = QGroupBox("Currencies")
        curr_layout = QFormLayout(curr_group)
        self._units = QSpinBox()
        self._units.setRange(0, 2_147_483_647)
        self._units.valueChanged.connect(lambda v: self._set_value("Units", v))
        curr_layout.addRow("Units:", self._units)

        self._nanites = QSpinBox()
        self._nanites.setRange(0, 2_147_483_647)
        self._nanites.valueChanged.connect(lambda v: self._set_value("Nanites", v))
        curr_layout.addRow("Nanites:", self._nanites)

        self._quicksilver = QSpinBox()
        self._quicksilver.setRange(0, 2_147_483_647)
        self._quicksilver.valueChanged.connect(lambda v: self._set_value("Specials", v))
        curr_layout.addRow("Quicksilver:", self._quicksilver)

        left_layout.addWidget(curr_group)

        # Stats
        stats_group = QGroupBox("Main Stats")
        stats_layout = QFormLayout(stats_group)
        self._health = StatEditor("Health", 1, 99999)
        self._health.value_changed.connect(lambda v: self._set_value("Health", v))
        stats_layout.addRow("Health:", self._health)

        self._shield = StatEditor("Shield", 0, 99999)
        self._shield.value_changed.connect(lambda v: self._set_value("Shield", v))
        stats_layout.addRow("Shield:", self._shield)

        self._energy = StatEditor("Energy", 0, 99999)
        self._energy.value_changed.connect(lambda v: self._set_value("Energy", v))
        stats_layout.addRow("Energy:", self._energy)

        left_layout.addWidget(stats_group)
        left_layout.addStretch()
        layout.addWidget(left)

        # Right panel: inventory tabs
        right = QTabWidget()
        self._inv_general = InventoryGrid("General")
        self._inv_tech = InventoryGrid("Technology")
        self._inv_cargo = InventoryGrid("Cargo")
        right.addTab(self._inv_general, "General")
        right.addTab(self._inv_tech, "Technology")
        right.addTab(self._inv_cargo, "Cargo")
        layout.addWidget(right)

    def set_data(self, psd: dict):
        self._data = psd

        # Block signals during population
        for w in (self._units, self._nanites, self._quicksilver):
            w.blockSignals(True)

        # Units may overflow to negative in save; clamp to 0
        units = psd.get("Units", 0)
        self._units.setValue(max(0, units) if isinstance(units, int) else 0)
        self._nanites.setValue(psd.get("Nanites", 0))
        # Quicksilver is stored as "Specials" in NMS save format
        self._quicksilver.setValue(psd.get("Specials", 0))

        for w in (self._units, self._nanites, self._quicksilver):
            w.blockSignals(False)

        self._health.set_value(psd.get("Health", 0))
        self._shield.set_value(psd.get("Shield", 0))
        self._energy.set_value(psd.get("Energy", 0))

        self._inv_general.set_inventory(psd.get("Inventory", {}))
        self._inv_tech.set_inventory(psd.get("Inventory_TechOnly", {}))
        self._inv_cargo.set_inventory(psd.get("Inventory_Cargo", {}))

    def _set_value(self, key: str, value):
        if self._data is not None:
            self._data[key] = value
