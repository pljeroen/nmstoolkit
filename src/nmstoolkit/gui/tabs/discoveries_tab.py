"""Discoveries editor tab."""

import json
import math

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
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


def _extract_voxels(addr):
    """Extract (x, y, z) voxel coordinates from a galactic address integer."""
    if not isinstance(addr, int):
        return (0, 0, 0)
    voxel_x = (addr >> 19) & 0xFFF
    voxel_y = (addr >> 31) & 0xFF
    voxel_z = (addr >> 39) & 0xFFF
    return (voxel_x, voxel_y, voxel_z)


def _distance(addr_a, addr_b):
    """Euclidean distance between two galactic addresses."""
    ax, ay, az = _extract_voxels(addr_a)
    bx, by, bz = _extract_voxels(addr_b)
    return math.sqrt((bx - ax) ** 2 + (by - ay) ** 2 + (bz - az) ** 2)


def _total_path_distance(addrs):
    """Total distance of the polyline through addresses in order."""
    total = 0.0
    for i in range(len(addrs) - 1):
        total += _distance(addrs[i], addrs[i + 1])
    return total


def _optimize_path(addrs):
    """Reorder addresses to minimize total path length.

    Uses nearest-neighbor heuristic followed by 2-opt improvement.
    Handles up to ~1000 points in a few seconds with stdlib only.
    """
    n = len(addrs)
    if n <= 2:
        return list(addrs)

    # Pre-compute voxel coordinates
    coords = [_extract_voxels(a) for a in addrs]

    def dist_sq(i, j):
        cx, cy, cz = coords[i]
        dx, dy, dz = coords[j]
        return (dx - cx) ** 2 + (dy - cy) ** 2 + (dz - cz) ** 2

    def dist(i, j):
        return math.sqrt(dist_sq(i, j))

    # Phase 1: Nearest Neighbor
    visited = [False] * n
    order = [0]
    visited[0] = True
    for _ in range(n - 1):
        last = order[-1]
        best_idx = -1
        best_d = float("inf")
        for j in range(n):
            if not visited[j]:
                d = dist_sq(last, j)
                if d < best_d:
                    best_d = d
                    best_idx = j
        order.append(best_idx)
        visited[best_idx] = True

    # Phase 2: 2-opt improvement (up to 10 passes)
    improved = True
    passes = 0
    while improved and passes < 10:
        improved = False
        passes += 1
        for i in range(n - 1):
            for j in range(i + 2, n):
                # Current edges: (i, i+1) and (j, j+1 if exists)
                d_old = dist(order[i], order[i + 1])
                d_new = dist(order[i], order[j])
                if j + 1 < n:
                    d_old += dist(order[j], order[j + 1])
                    d_new += dist(order[i + 1], order[j + 1])
                else:
                    # j is the last element — only one edge to consider
                    pass
                if d_new < d_old:
                    # Reverse segment [i+1..j]
                    order[i + 1 : j + 1] = reversed(order[i + 1 : j + 1])
                    improved = True

    return [addrs[i] for i in order]


class DiscoveriesTab(QWidget):
    def __init__(self):
        super().__init__()
        self._data = None
        self._psd = None
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

        # Constellation management
        const_group = QGroupBox("Constellations (Star Map Travel Lines)")
        const_layout = QVBoxLayout(const_group)
        self._const_count_label = QLabel("Visited systems: —")
        const_layout.addWidget(self._const_count_label)

        btn_layout = QHBoxLayout()
        self._const_optimize_btn = QPushButton("Optimize Paths")
        self._const_optimize_btn.setToolTip(
            "Reorder visited systems to minimize total travel line length"
        )
        self._const_optimize_btn.clicked.connect(self._on_constellation_optimize)
        btn_layout.addWidget(self._const_optimize_btn)

        self._const_reset_btn = QPushButton("Reset")
        self._const_reset_btn.setToolTip("Clear all constellation lines from star map")
        self._const_reset_btn.clicked.connect(self._on_constellation_reset)
        btn_layout.addWidget(self._const_reset_btn)

        self._const_backup_btn = QPushButton("Backup")
        self._const_backup_btn.clicked.connect(self._on_constellation_backup)
        btn_layout.addWidget(self._const_backup_btn)

        self._const_restore_btn = QPushButton("Restore")
        self._const_restore_btn.clicked.connect(self._on_constellation_restore)
        btn_layout.addWidget(self._const_restore_btn)

        const_layout.addLayout(btn_layout)
        layout.addWidget(const_group)

        # Discovery backup/restore
        disc_group = QGroupBox("Discovery Data")
        disc_layout = QHBoxLayout(disc_group)
        self._disc_backup_btn = QPushButton("Backup Discoveries")
        self._disc_backup_btn.clicked.connect(self._on_discovery_backup)
        disc_layout.addWidget(self._disc_backup_btn)
        self._disc_restore_btn = QPushButton("Restore Discoveries")
        self._disc_restore_btn.clicked.connect(self._on_discovery_restore)
        disc_layout.addWidget(self._disc_restore_btn)
        layout.addWidget(disc_group)

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

    def set_player_state(self, psd: dict):
        """Accept PlayerStateData for constellation management."""
        self._psd = psd
        self._update_constellation_label()

    def _update_constellation_label(self):
        if self._psd is None:
            self._const_count_label.setText("Visited systems: —")
            return
        vs = self._psd.get("VisitedSystems", [])
        count = len(vs)
        if count > 1:
            dist = _total_path_distance(vs)
            self._const_count_label.setText(
                f"Visited systems: {count} ({dist:,.0f} voxel units total path length)"
            )
        else:
            self._const_count_label.setText(f"Visited systems: {count}")

    def _on_constellation_reset(self):
        if self._psd is None:
            return
        self._psd["VisitedSystems"] = []
        self._update_constellation_label()

    def _on_constellation_optimize(self):
        if self._psd is None:
            return
        vs = self._psd.get("VisitedSystems", [])
        if len(vs) <= 2:
            return
        self._psd["VisitedSystems"] = _optimize_path(vs)
        self._update_constellation_label()

    def _on_constellation_backup(self):
        if self._psd is None:
            return
        vs = self._psd.get("VisitedSystems", [])
        path, _ = QFileDialog.getSaveFileName(
            self, "Backup Constellations", "constellations.json", "JSON files (*.json)"
        )
        if path:
            with open(path, "w") as f:
                json.dump(vs, f, indent=2)

    def _on_constellation_restore(self):
        if self._psd is None:
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Restore Constellations", "", "JSON files (*.json)"
        )
        if path:
            with open(path) as f:
                data = json.load(f)
            if isinstance(data, list):
                self._psd["VisitedSystems"] = data
                self._update_constellation_label()

    def _on_discovery_backup(self):
        if self._data is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Backup Discoveries", "discoveries.json", "JSON files (*.json)"
        )
        if path:
            with open(path, "w") as f:
                json.dump(self._data, f, indent=2)

    def _on_discovery_restore(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Restore Discoveries", "", "JSON files (*.json)"
        )
        if path:
            with open(path) as f:
                data = json.load(f)
            if isinstance(data, dict):
                self.set_data(data)

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
