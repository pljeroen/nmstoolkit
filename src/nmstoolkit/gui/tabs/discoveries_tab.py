"""Discoveries editor tab."""

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from nmstoolkit.gui.tabs.bases_tab import _decode_galactic_address


def _format_address(address) -> str:
    """Format a universe address as hex for readability."""
    if isinstance(address, int):
        return f"0x{address:X}"
    if isinstance(address, str) and address:
        return address
    return str(address) if address else ""


class DiscoveriesTab(QWidget):
    def __init__(self):
        super().__init__()
        self._data = None
        self._records = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Filter bar
        filter_bar = QHBoxLayout()
        self._info_label = QLabel("Discovery data")
        filter_bar.addWidget(self._info_label)
        filter_bar.addStretch()

        filter_bar.addWidget(QLabel("Type:"))
        self._type_filter = QComboBox()
        self._type_filter.setMinimumWidth(150)
        self._type_filter.addItem("All")
        self._type_filter.currentIndexChanged.connect(self._apply_filter)
        filter_bar.addWidget(self._type_filter)

        self._undiscovered_check = QCheckBox("Undiscovered only")
        self._undiscovered_check.toggled.connect(self._apply_filter)
        filter_bar.addWidget(self._undiscovered_check)

        filter_bar.addWidget(QLabel("Search:"))
        self._search = QLineEdit()
        self._search.setPlaceholderText("Filter by name...")
        self._search.setMinimumWidth(200)
        self._search.textChanged.connect(self._apply_filter)
        filter_bar.addWidget(self._search)

        layout.addLayout(filter_bar)

        self._table = QTableWidget()
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels(["Type", "Name", "Owner", "Address"])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self._table.setAlternatingRowColors(True)
        self._table.setSortingEnabled(True)
        layout.addWidget(self._table)

    def set_data(self, discovery_data: dict):
        self._data = discovery_data
        store = discovery_data.get("DiscoveryData-v1", {})
        self._records = store.get("Store", {}).get("Record", [])

        # Collect types for filter
        types = set()
        for record in self._records:
            dd = record.get("DD", {})
            dt = dd.get("DT", "")
            if dt:
                types.add(dt)

        self._type_filter.blockSignals(True)
        self._type_filter.clear()
        self._type_filter.addItem("All")
        for t in sorted(types):
            self._type_filter.addItem(t)
        self._type_filter.blockSignals(False)

        self._apply_filter()

    def _apply_filter(self):
        type_filter = self._type_filter.currentText()
        search_text = self._search.text().lower()
        undiscovered_only = self._undiscovered_check.isChecked()

        filtered = []
        for record in self._records:
            dd = record.get("DD", {})
            ows = record.get("OWS", {})
            disc_type = dd.get("DT", "")
            dm = record.get("DM", {})
            name = ""
            if isinstance(dm, dict):
                name = dm.get("CN", "")
            if not name:
                name = dd.get("CN", "") or dd.get("N", "") or ""
            owner = ows.get("USN", "")
            address = dd.get("UA", "")

            # Undiscovered filter — hide entries with names
            is_named = bool(name)

            # Fallback for unnamed discoveries
            if not name:
                addr_str = _format_address(address)
                name = f"<unknown name> ({addr_str})" if addr_str else "<unknown name>"

            if undiscovered_only and is_named:
                continue
            if type_filter != "All" and disc_type != type_filter:
                continue
            if search_text and search_text not in name.lower() and search_text not in owner.lower():
                continue

            filtered.append((disc_type, name, owner, _decode_galactic_address(address)))

        type_counts = {}
        for record in self._records:
            dt = record.get("DD", {}).get("DT", "Unknown")
            type_counts[dt] = type_counts.get(dt, 0) + 1

        count_parts = [f"{t}: {c}" for t, c in sorted(type_counts.items())]
        self._info_label.setText(
            f"Discoveries: {len(self._records)} total, {len(filtered)} shown"
            + (f" ({', '.join(count_parts)})" if len(count_parts) <= 6 else "")
        )

        self._table.setSortingEnabled(False)
        self._table.setRowCount(min(len(filtered), 2000))
        for row, (disc_type, name, owner, address) in enumerate(filtered[:2000]):
            self._table.setItem(row, 0, QTableWidgetItem(disc_type))
            self._table.setItem(row, 1, QTableWidgetItem(name))
            self._table.setItem(row, 2, QTableWidgetItem(owner if owner else "—"))
            self._table.setItem(row, 3, QTableWidgetItem(address))
        self._table.setSortingEnabled(True)
