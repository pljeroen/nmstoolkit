"""Account data editor tab — expedition rewards, Twitch drops, settings."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QHeaderView,
    QLabel,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from nmstoolkit.gui.widgets.inventory_grid import get_item_display_name, get_item_icon
from nmstoolkit.gui.tabs.expedition_tab import _resolve_reward_name


class AccountTab(QWidget):
    def __init__(self):
        super().__init__()
        self._data = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content_layout = QVBoxLayout(content)

        # Account info
        self._info_group = QGroupBox("Account Information")
        self._info_layout = QFormLayout(self._info_group)
        self._version_label = QLabel("—")
        self._info_layout.addRow("Version:", self._version_label)
        content_layout.addWidget(self._info_group)

        # Expedition rewards
        exp_group = QGroupBox("Unlocked Expedition Rewards")
        exp_layout = QVBoxLayout(exp_group)
        self._exp_table = QTableWidget()
        self._exp_table.setColumnCount(1)
        self._exp_table.setHorizontalHeaderLabels(["Reward ID"])
        self._exp_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._exp_table.setAlternatingRowColors(True)
        exp_layout.addWidget(self._exp_table)
        self._exp_count_label = QLabel("0 rewards")
        exp_layout.addWidget(self._exp_count_label)
        content_layout.addWidget(exp_group)

        # Twitch rewards
        twitch_group = QGroupBox("Unlocked Twitch Rewards")
        twitch_layout = QVBoxLayout(twitch_group)
        self._twitch_table = QTableWidget()
        self._twitch_table.setColumnCount(1)
        self._twitch_table.setHorizontalHeaderLabels(["Reward ID"])
        self._twitch_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._twitch_table.setAlternatingRowColors(True)
        twitch_layout.addWidget(self._twitch_table)
        self._twitch_count_label = QLabel("0 rewards")
        twitch_layout.addWidget(self._twitch_count_label)
        content_layout.addWidget(twitch_group)

        # User settings
        self._settings_group = QGroupBox("User Settings")
        self._settings_layout = QFormLayout(self._settings_group)
        content_layout.addWidget(self._settings_group)

        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

    def set_data(self, data: dict):
        self._data = data
        self._version_label.setText(str(data.get("Version", "—")))

        # Expedition rewards (obfuscated key d4U → unmapped key varies)
        exp_rewards = self._find_reward_list(data, "expedition")
        self._exp_table.setRowCount(len(exp_rewards))
        for row, reward in enumerate(exp_rewards):
            reward_id = str(reward)
            display = _resolve_reward_name(reward_id)
            item = QTableWidgetItem(display)
            item.setToolTip(reward_id)
            pixmap = get_item_icon(reward_id)
            if pixmap is not None:
                item.setIcon(QIcon(pixmap))
            item.setFlags(item.flags() | Qt.ItemIsSelectable)
            self._exp_table.setItem(row, 0, item)
        self._exp_count_label.setText(f"{len(exp_rewards)} rewards")

        # Twitch rewards
        twitch_rewards = self._find_reward_list(data, "twitch")
        self._twitch_table.setRowCount(len(twitch_rewards))
        for row, reward in enumerate(twitch_rewards):
            reward_id = str(reward)
            display = _resolve_reward_name(reward_id)
            item = QTableWidgetItem(display)
            item.setToolTip(reward_id)
            pixmap = get_item_icon(reward_id)
            if pixmap is not None:
                item.setIcon(QIcon(pixmap))
            item.setFlags(item.flags() | Qt.ItemIsSelectable)
            self._twitch_table.setItem(row, 0, item)
        self._twitch_count_label.setText(f"{len(twitch_rewards)} rewards")

        # Clear old settings rows
        while self._settings_layout.rowCount() > 0:
            self._settings_layout.removeRow(0)

        settings = data.get("UserSettingsData", {})
        for key, value in list(settings.items())[:30]:
            label = QLabel(str(value))
            label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            self._settings_layout.addRow(f"{key}:", label)

    @staticmethod
    def _find_reward_list(data: dict, reward_type: str) -> list:
        """Find expedition or twitch reward lists in account data.

        Account data keys may be unmapped or still obfuscated.
        Search by content pattern: lists of strings starting with ^EXPD_ or ^TWITCH_.
        """
        prefix = "^EXPD_" if reward_type == "expedition" else "^TWITCH_"

        # Try known unmapped keys
        for key in ["UnlockedSeasonRewards", "UnlockedTwitchRewards",
                     "d4U", "<5B", "CrossPlatformUnlockedRewards"]:
            val = data.get(key, [])
            if isinstance(val, list) and val:
                if any(str(v).startswith(prefix) for v in val[:5]):
                    return val

        # Scan all top-level lists for matching patterns
        for key, val in data.items():
            if not isinstance(val, list):
                continue
            if len(val) < 2:
                continue
            matches = sum(1 for v in val[:10] if isinstance(v, str) and v.startswith(prefix))
            if matches >= 2:
                return val

        # Also check for expedition rewards that don't start with ^EXPD_
        if reward_type == "expedition":
            for key, val in data.items():
                if not isinstance(val, list):
                    continue
                if len(val) >= 5:
                    str_count = sum(1 for v in val if isinstance(v, str) and v.startswith("^"))
                    if str_count > len(val) * 0.8:
                        # Mostly ^-prefixed strings, likely rewards
                        if any("EXPD" in str(v) or "BLD_" in str(v) for v in val[:20]):
                            return val

        return []
