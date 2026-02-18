"""Expedition / Season data tab.

Displays current expedition progress, historical season data,
and provides offline expedition replay by downloading SEASON_DATA_CACHE.JSON
from the cwmonkey/nms-expeditions repository.
"""

import json
import re
import urllib.request
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from nmstoolkit.gui.widgets.inventory_grid import get_item_display_name, get_item_icon

# Cosmetic/expedition reward IDs that aren't in items.json
_REWARD_NAMES = {
    # Expedition cosmetics — titles & banners
    "^YOURFIRSTPLANET1": "Your First Planet (Title)",
    "^YOURFIRSTPLANET2": "Your First Planet II (Title)",
    "^YOURFIRSTPLANET3": "Your First Planet III (Title)",
    # T-shirt / poster rewards
    "^TSHIRT_POSTERS1": "Poster Pack 1",
    "^TSHIRT_POSTERS1_HARD": "Poster Pack 1 (Hard Mode)",
    "^TSHIRT_POSTERS2": "Poster Pack 2",
    "^TSHIRT_POSTERS2_HARD": "Poster Pack 2 (Hard Mode)",
    "^TSHIRT_POSTERS3": "Poster Pack 3",
    "^TSHIRT_POSTERS3_HARD": "Poster Pack 3 (Hard Mode)",
    # Ship/freighter cosmetics
    "^YOURSHIP_TRAIL": "Ship Trail",
    "^YOURFREIG_TRAIL": "Freighter Trail",
    "^YOURSHIP_BOBBLE": "Ship Bobblehead",
    "^YOURSUIT_JETTRAIL": "Jetpack Trail",
    "^YOURSUIT_CAPE": "Cape",
    "^YOURSUIT_CLOAK": "Cloak",
    "^YOURSUIT_HEADGEAR": "Headgear",
    # Expedition-specific rewards
    "^YOURSHIP_PANTHER": "Panther Ship",
    "^YOURSHIP_SQUID": "Living Ship (Squid)",
    "^YOURSHIP_LIVING": "Living Ship",
    "^YOURSUIT_TITAN": "Titan Suit",
    "^YOURSUIT_RELIC": "Relic Suit",
    "^YOURSUIT_CURSED": "Cursed Suit",
    "^YOURSUIT_POLESTAR": "Polestar Suit",
    "^YOURSUIT_SINGULARITY": "Singularity Suit",
    "^YOURSUIT_LIQUIDATOR": "Liquidator Suit",
    "^YOURSUIT_AQUARIUS": "Aquarius Suit",
    "^YOURSUIT_OMEGA": "Omega Suit",
    "^YOURSUIT_ADRIFT": "Adrift Suit",
    # Companions
    "^PET_EGG": "Companion Egg",
    "^PET_EGG_SHIP": "Living Ship Egg",
    # Base parts
    "^BLD_POSTER": "Poster (Base Decoration)",
    "^BLD_TROPHY": "Trophy (Base Decoration)",
    "^BLD_STATUE": "Statue (Base Decoration)",
    "^BLD_FLAG": "Flag (Base Decoration)",
    "^BLD_BANNER": "Banner (Base Decoration)",
    # Fireworks
    "^YOURSUIT_FIREWORK": "Firework Emote",
    # Tokens
    "^TOKEN_PIONEER": "Pioneer Token",
    "^TOKEN_BEACHHEAD": "Beachhead Token",
    "^TOKEN_CARTO": "Cartographers Token",
    "^TOKEN_EMERGENCE": "Emergence Token",
    "^TOKEN_EXOBIO": "Exobiology Token",
    "^TOKEN_BLIGHT": "Blighted Token",
    "^TOKEN_LEVIATHAN": "Leviathan Token",
    "^TOKEN_POLESTAR": "Polestar Token",
    "^TOKEN_UTOPIA": "Utopia Token",
    "^TOKEN_SINGULARITY": "Singularity Token",
    "^TOKEN_VOYAGER": "Voyagers Token",
    "^TOKEN_OMEGA": "Omega Token",
    "^TOKEN_ADRIFT": "Adrift Token",
    "^TOKEN_LIQUIDATOR": "Liquidators Token",
    "^TOKEN_AQUARIUS": "Aquarius Token",
    "^TOKEN_CURSED": "Cursed Token",
    "^TOKEN_TITAN": "Titan Token",
    "^TOKEN_RELICS": "Relics Token",
    "^TOKEN_CORVETTE": "Corvette Token",
    "^TOKEN_BREACH": "Breach Token",
    "^TOKEN_REMNANT": "Remnant Token",
}


def _reward_expedition_number(reward_id: str) -> int:
    """Extract the expedition number from a reward ID, or 0 if unclassifiable.

    E.g. ^EXPD_POSTER06A -> 6, ^EXPD_TITLE19 -> 19, ^JETS_WORM -> 0.
    """
    clean = reward_id.lstrip("^")
    m = re.search(r"(\d+)", clean)
    if m:
        num = int(m.group(1))
        if 1 <= num <= 99:
            return num
    return 0


def _resolve_locale_name(raw_name: str) -> str:
    """Resolve a locale key to a display name.

    Handles ^UI_SEASON_* keys by trying get_item_display_name first,
    then falling back to a cleaned version of the raw string.
    """
    if not raw_name:
        return "Unknown"
    # If it looks like a locale key (starts with ^ or UI_), try resolution
    if raw_name.startswith("^") or raw_name.startswith("UI_"):
        resolved = get_item_display_name(raw_name)
        if resolved != raw_name and resolved != raw_name.lstrip("^"):
            return resolved
        # Fallback: strip caret, replace underscores, title case
        return raw_name.lstrip("^").replace("_", " ").title()
    return raw_name


def _resolve_reward_name(reward_id: str) -> str:
    """Resolve a reward ID to a human-readable name."""
    # Check exact match first
    if reward_id in _REWARD_NAMES:
        return _REWARD_NAMES[reward_id]
    # Check items.json via the standard resolver
    name = get_item_display_name(reward_id)
    if name != reward_id and name != reward_id.lstrip("^"):
        return name
    # Fallback: make the raw ID more readable
    clean = reward_id.lstrip("^").replace("_", " ").title()
    return clean

# Known expeditions: (number, display_name, repo_filename_base)
# Repo filenames from github.com/cwmonkey/nms-expeditions/patched/
_EXPEDITIONS = [
    (1, "Pioneers", "PIONEERS"),
    (2, "Beachhead", "BEACHHEAD"),
    (3, "Cartographers", "CARTOGRAPHERS"),
    (4, "Emergence", "EMERGENCE"),
    (5, "Exobiology", "EXOBIOLOGY"),
    (6, "The Blighted", "THE BLIGHTED"),
    (7, "Leviathan", "LEVIATHAN"),
    (8, "Polestar", "POLESTAR"),
    (9, "Utopia", "UTOPIA"),
    (10, "Singularity", "SINGULARITY"),
    (11, "Voyagers", "VOYAGERS"),
    (12, "Omega", "OMEGA"),
    (13, "Adrift", "ADRIFT"),
    (14, "Liquidators", "LIQUIDATORS"),
    (15, "Aquarius", "AQUARIUS"),
    (16, "The Cursed", "THE CURSED"),
    (17, "Titan", "TITAN"),
    (18, "Relics", "RELICS"),
    (19, "Corvette", "CORVETTE"),
    (20, "Breach", "BREACH"),
    (21, "Remnant", "REMNANT"),
]

_REPO_BASE = "https://raw.githubusercontent.com/cwmonkey/nms-expeditions/master/patched"


class ExpeditionTab(QWidget):
    def __init__(self):
        super().__init__()
        self._data = None
        self._common_data = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        content_panel = QWidget()
        content_layout = QHBoxLayout(content_panel)
        content_layout.setContentsMargins(0, 0, 0, 0)

        self._left_panel = QWidget()
        left_layout = QVBoxLayout(self._left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        self._right_panel = QWidget()
        right_layout = QVBoxLayout(self._right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # Current season info
        season_group = QGroupBox("Current Expedition")
        season_layout = QVBoxLayout(season_group)

        self._season_info = QLabel("No expedition data loaded")
        self._season_info.setWordWrap(True)
        season_layout.addWidget(self._season_info)

        progress_row = QHBoxLayout()
        self._final_reward_label = QLabel("")
        progress_row.addWidget(self._final_reward_label)
        progress_row.addStretch()
        season_layout.addLayout(progress_row)

        left_layout.addWidget(season_group)

        # Milestone progress table
        milestone_group = QGroupBox("Milestone Progress")
        milestone_layout = QVBoxLayout(milestone_group)

        self._milestone_table = QTableWidget()
        self._milestone_table.setColumnCount(3)
        self._milestone_table.setHorizontalHeaderLabels(
            ["Milestone", "Value", "Reward Collected"]
        )
        self._milestone_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.Stretch
        )
        self._milestone_table.setAlternatingRowColors(True)
        milestone_layout.addWidget(self._milestone_table)

        left_layout.addWidget(milestone_group)

        # Redeemed season rewards
        rewards_group = QGroupBox("Redeemed Season Rewards")
        rewards_layout = QVBoxLayout(rewards_group)

        # Filter and unlock row
        reward_bar = QHBoxLayout()
        reward_bar.addWidget(QLabel("Expedition:"))
        self._reward_filter = QComboBox()
        self._reward_filter.setMinimumWidth(150)
        self._reward_filter.addItem("All")
        self._reward_filter.currentIndexChanged.connect(self._apply_reward_filter)
        reward_bar.addWidget(self._reward_filter)
        reward_bar.addStretch()

        self._unlock_all_btn = QPushButton("Unlock All Rewards")
        self._unlock_all_btn.clicked.connect(self._on_unlock_all)
        reward_bar.addWidget(self._unlock_all_btn)
        rewards_layout.addLayout(reward_bar)

        self._rewards_table = QTableWidget()
        self._rewards_table.setColumnCount(2)
        self._rewards_table.setHorizontalHeaderLabels(["Reward", "Expedition"])
        self._rewards_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.Stretch
        )
        self._rewards_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeToContents
        )
        self._rewards_table.setAlternatingRowColors(True)
        rewards_layout.addWidget(self._rewards_table)

        right_layout.addWidget(rewards_group)

        # Twitch Rewards
        twitch_group = QGroupBox("Twitch Rewards")
        twitch_layout = QVBoxLayout(twitch_group)
        self._twitch_count = QLabel("0 rewards")
        twitch_layout.addWidget(self._twitch_count)
        self._twitch_table = QTableWidget()
        self._twitch_table.setColumnCount(1)
        self._twitch_table.setHorizontalHeaderLabels(["Reward"])
        self._twitch_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.Stretch
        )
        self._twitch_table.setAlternatingRowColors(True)
        twitch_layout.addWidget(self._twitch_table)
        right_layout.addWidget(twitch_group)

        # Platform Rewards
        platform_group = QGroupBox("Platform Rewards")
        platform_layout = QVBoxLayout(platform_group)
        self._platform_count = QLabel("0 rewards")
        platform_layout.addWidget(self._platform_count)
        self._platform_table = QTableWidget()
        self._platform_table.setColumnCount(1)
        self._platform_table.setHorizontalHeaderLabels(["Reward"])
        self._platform_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.Stretch
        )
        self._platform_table.setAlternatingRowColors(True)
        platform_layout.addWidget(self._platform_table)
        right_layout.addWidget(platform_group)

        # Offline expedition replay
        replay_group = QGroupBox("Offline Expedition Replay")
        replay_layout = QVBoxLayout(replay_group)

        replay_info = QLabel(
            "Download a past expedition's SEASON_DATA_CACHE.JSON to replay it offline.\n"
            "Place the file in your NMS cache directory and start the game in offline mode.\n"
            "Source: github.com/cwmonkey/nms-expeditions"
        )
        replay_info.setWordWrap(True)
        replay_info.setStyleSheet("color: #aaa; font-size: 11px;")
        replay_layout.addWidget(replay_info)

        select_row = QHBoxLayout()
        select_row.addWidget(QLabel("Expedition:"))
        self._expedition_combo = QComboBox()
        self._expedition_combo.setMinimumWidth(300)
        for num, name, _repo in _EXPEDITIONS:
            self._expedition_combo.addItem(f"#{num} — {name}")
        select_row.addWidget(self._expedition_combo)
        select_row.addStretch()
        replay_layout.addLayout(select_row)

        btn_row = QHBoxLayout()
        self._download_btn = QPushButton("Download && Install to Cache")
        self._download_btn.clicked.connect(self._on_download_expedition)
        btn_row.addWidget(self._download_btn)

        self._save_as_btn = QPushButton("Download && Save As...")
        self._save_as_btn.clicked.connect(self._on_save_expedition_as)
        btn_row.addWidget(self._save_as_btn)

        btn_row.addStretch()
        replay_layout.addLayout(btn_row)

        self._replay_status = QLabel("")
        self._replay_status.setWordWrap(True)
        replay_layout.addWidget(self._replay_status)

        left_layout.addWidget(replay_group)

        content_layout.addWidget(self._left_panel, 1)
        content_layout.addWidget(self._right_panel, 1)
        layout.addWidget(content_panel)

    def set_data(self, psd: dict, common_state: dict = None):
        self._data = psd
        self._common_data = common_state or {}

        self._populate_season_info()
        self._populate_milestones()
        self._populate_rewards()
        self._populate_twitch_rewards()
        self._populate_platform_rewards()

    def _populate_season_info(self):
        season_data = self._common_data.get("SeasonData", {})
        season_state = self._common_data.get("SeasonState", {})

        if not season_data:
            self._season_info.setText("No active expedition")
            self._final_reward_label.setText("")
            return

        season_num = season_data.get("SeasonNumber", "?")
        raw_season_name = season_data.get("SeasonName", "Unknown")
        season_id = season_data.get("SeasonId", "?")

        # Resolve locale keys (e.g. ^UI_SEASON_19_NAME -> "Corvette")
        season_name = _resolve_locale_name(raw_season_name)

        has_final = season_state.get("HasCollectedFinalReward", False)
        final_status = "Collected" if has_final else "Not collected"

        self._season_info.setText(
            f"Season {season_id} (#{season_num}) — {season_name}"
        )

        raw_final = season_data.get("FinalReward", "—")
        final_name = _resolve_reward_name(raw_final) if raw_final != "—" else "—"
        self._final_reward_label.setText(
            f"Final Reward: {final_name} ({final_status})"
        )

    def _populate_milestones(self):
        season_state = self._common_data.get("SeasonState", {})
        milestones = season_state.get("MilestoneValues", [])

        self._milestone_table.setRowCount(len(milestones))
        for row, ms in enumerate(milestones):
            if isinstance(ms, dict):
                name = ms.get("Name", f"Milestone {row}")
                value = str(ms.get("Value", 0))
                collected = "Yes" if ms.get("RewardCollected", False) else "No"
            else:
                name = f"[{row}]"
                value = str(ms)
                collected = "?"

            self._milestone_table.setItem(row, 0, QTableWidgetItem(name))
            self._milestone_table.setItem(row, 1, QTableWidgetItem(value))

            collected_item = QTableWidgetItem(collected)
            if collected == "Yes":
                collected_item.setForeground(Qt.green)
            self._milestone_table.setItem(row, 2, collected_item)

    def _populate_rewards(self):
        self._redeemed = []
        if self._data:
            self._redeemed = self._data.get("RedeemedSeasonRewards", [])

        # Build expedition filter options from redeemed rewards
        exp_nums = set()
        for reward in self._redeemed:
            num = _reward_expedition_number(str(reward))
            if num > 0:
                exp_nums.add(num)

        self._reward_filter.blockSignals(True)
        self._reward_filter.clear()
        self._reward_filter.addItem("All")
        for num in sorted(exp_nums):
            self._reward_filter.addItem(str(num))
        if exp_nums:
            self._reward_filter.addItem("Other")
        self._reward_filter.blockSignals(False)

        self._apply_reward_filter()

    def _populate_twitch_rewards(self):
        """Populate Twitch rewards table from RedeemedTwitchRewards."""
        rewards = []
        if self._data:
            rewards = self._data.get("RedeemedTwitchRewards", [])

        self._twitch_count.setText(f"{len(rewards)} rewards")
        self._twitch_table.setRowCount(len(rewards))
        for row, reward_id in enumerate(rewards):
            reward_id = str(reward_id)
            display = _resolve_reward_name(reward_id)
            item = QTableWidgetItem(display)
            item.setToolTip(reward_id)
            pixmap = get_item_icon(reward_id)
            if pixmap is not None:
                item.setIcon(QIcon(pixmap))
            self._twitch_table.setItem(row, 0, item)

    def _populate_platform_rewards(self):
        """Populate Platform rewards table from RedeemedPlatformRewards."""
        rewards = []
        if self._data:
            rewards = self._data.get("RedeemedPlatformRewards", [])

        self._platform_count.setText(f"{len(rewards)} rewards")
        self._platform_table.setRowCount(len(rewards))
        for row, reward_id in enumerate(rewards):
            reward_id = str(reward_id)
            display = _resolve_reward_name(reward_id)
            item = QTableWidgetItem(display)
            item.setToolTip(reward_id)
            pixmap = get_item_icon(reward_id)
            if pixmap is not None:
                item.setIcon(QIcon(pixmap))
            self._platform_table.setItem(row, 0, item)

    def _apply_reward_filter(self):
        """Filter rewards table by selected expedition number."""
        filter_text = self._reward_filter.currentText()

        filtered = []
        for reward in self._redeemed:
            reward_id = str(reward)
            exp_num = _reward_expedition_number(reward_id)

            if filter_text == "All":
                pass  # include all
            elif filter_text == "Other":
                if exp_num > 0:
                    continue
            else:
                try:
                    if exp_num != int(filter_text):
                        continue
                except ValueError:
                    continue

            filtered.append((reward_id, exp_num))

        self._rewards_table.setRowCount(len(filtered))
        for row, (reward_id, exp_num) in enumerate(filtered):
            display = _resolve_reward_name(reward_id)
            item = QTableWidgetItem(display)
            item.setToolTip(reward_id)
            pixmap = get_item_icon(reward_id)
            if pixmap is not None:
                item.setIcon(QIcon(pixmap))
            self._rewards_table.setItem(row, 0, item)

            exp_label = str(exp_num) if exp_num > 0 else "—"
            self._rewards_table.setItem(row, 1, QTableWidgetItem(exp_label))

    def _on_unlock_all(self):
        """Unlock all known expedition rewards for the player."""
        if self._data is None:
            return

        redeemed = self._data.get("RedeemedSeasonRewards", [])
        existing = set(redeemed)

        # Collect all known reward IDs from all expeditions in _EXPEDITIONS
        # Build from known patterns: EXPD_*, BLD_BUGHEAD*, BLD_SHIPBREAK*, etc.
        all_known = set()
        for num, name, _repo in _EXPEDITIONS:
            # Standard reward patterns per expedition
            nn = f"{num:02d}"
            n = str(num)
            patterns = [
                f"^EXPD_BANNER{nn}", f"^EXPD_DECAL{nn}",
                f"^EXPD_POSTER{nn}A", f"^EXPD_POSTER{nn}B", f"^EXPD_POSTER{nn}C",
                f"^EXPD_TITLE{nn}",
            ]
            # Also try single-digit variants
            if num < 10:
                patterns += [
                    f"^BASE_CAVE{n}", f"^BLD_BUGHEAD{n}", f"^BLD_SHIPBREAK{n}",
                    f"^EXPD_BACKPACK{nn}", f"^EXPD_CAPE{nn}",
                    f"^EXPD_EGG_{nn}", f"^EXPD_FIREPACK{nn}",
                    f"^EXPD_SHIP{nn}", f"^EXPD_PETCUST{nn}",
                    f"^EXPD_HELMET{nn}", f"^EXPD_SPEC{nn}",
                ]
            else:
                patterns += [
                    f"^EXPD_CAPE{nn}", f"^EXPD_EGG_{nn}",
                    f"^EXPD_SHIP{nn}", f"^EXPD_PETCUST{nn}",
                    f"^EXPD_SHIPMAT{nn}", f"^EXPD_STAFF_{nn}",
                ]
            all_known.update(patterns)

        # Add any rewards the player already has (they know more than we do)
        all_known.update(existing)

        # Add missing rewards
        added = 0
        for reward_id in sorted(all_known):
            if reward_id not in existing:
                redeemed.append(reward_id)
                existing.add(reward_id)
                added += 1

        self._data["RedeemedSeasonRewards"] = redeemed
        self._redeemed = redeemed
        self._apply_reward_filter()

    def _get_expedition_url(self) -> str:
        """Build the download URL for the selected expedition."""
        idx = self._expedition_combo.currentIndex()
        if idx < 0 or idx >= len(_EXPEDITIONS):
            return ""
        num, _name, repo_name = _EXPEDITIONS[idx]
        # Repo uses spaces in filenames, URL-encode them
        filename = f"{num:02d}_{repo_name}_LATEST_SEASON_DATA_CACHE.JSON"
        # URL-encode spaces
        filename = filename.replace(" ", "%20")
        return f"{_REPO_BASE}/{filename}"

    def _find_cache_dir(self) -> Path:
        """Find the NMS cache directory."""
        home = Path.home()
        # Steam/Proton (Linux)
        proton = home / ".local/share/Steam/steamapps/compatdata/275850/pfx/drive_c/users/steamuser/AppData/Roaming/HelloGames/NMS/cache"
        if proton.parent.exists():
            proton.mkdir(parents=True, exist_ok=True)
            return proton
        # Windows
        win = Path("C:/Users") / home.name / "AppData/Roaming/HelloGames/NMS/cache"
        if win.parent.exists():
            return win
        # Fallback
        return home / ".cache" / "nmstoolkit" / "nms-cache"

    def _download_json(self, url: str) -> dict:
        """Download and parse JSON from URL."""
        req = urllib.request.Request(url, headers={"User-Agent": "NMSToolkit/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _on_download_expedition(self):
        """Download expedition cache and install to NMS cache directory."""
        url = self._get_expedition_url()
        if not url:
            return

        idx = self._expedition_combo.currentIndex()
        num, name, _repo = _EXPEDITIONS[idx]

        self._replay_status.setText(f"Downloading expedition #{num} ({name})...")
        QApplication.processEvents()

        try:
            data = self._download_json(url)
        except Exception as e:
            self._replay_status.setText(f"Download failed: {e}")
            # Try alternate filename patterns
            try:
                # Try simpler filename
                alt_url = f"{_REPO_BASE}/{num:02d}_LATEST_SEASON_DATA_CACHE.JSON"
                data = self._download_json(alt_url)
            except Exception:
                self._replay_status.setText(
                    f"Download failed for expedition #{num}.\n"
                    f"URL: {url}\n"
                    f"Error: {e}\n\n"
                    "Try 'Save As...' and manually place the file."
                )
                return

        cache_dir = self._find_cache_dir()
        cache_dir.mkdir(parents=True, exist_ok=True)
        target = cache_dir / "SEASON_DATA_CACHE.JSON"

        # Back up existing cache file
        if target.exists():
            backup = cache_dir / "SEASON_DATA_CACHE.JSON.bak"
            target.rename(backup)

        target.write_text(json.dumps(data, indent=2), encoding="utf-8")
        self._replay_status.setText(
            f"Installed expedition #{num} ({name}) to:\n{target}\n\n"
            "Start NMS in offline mode (Steam → Go Offline) to replay this expedition.\n"
            "The expedition has been patched to never expire."
        )
        self._replay_status.setStyleSheet("color: #4a7;")

    def _on_save_expedition_as(self):
        """Download expedition cache and save to user-chosen location."""
        url = self._get_expedition_url()
        if not url:
            return

        idx = self._expedition_combo.currentIndex()
        num, name, _repo = _EXPEDITIONS[idx]

        path, _ = QFileDialog.getSaveFileName(
            self, "Save Expedition Cache",
            f"SEASON_DATA_CACHE.JSON",
            "JSON Files (*.JSON *.json);;All Files (*)"
        )
        if not path:
            return

        self._replay_status.setText(f"Downloading expedition #{num} ({name})...")
        QApplication.processEvents()

        try:
            data = self._download_json(url)
        except Exception as e:
            try:
                alt_url = f"{_REPO_BASE}/{num:02d}_LATEST_SEASON_DATA_CACHE.JSON"
                data = self._download_json(alt_url)
            except Exception:
                self._replay_status.setText(f"Download failed: {e}")
                return

        Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")
        self._replay_status.setText(f"Saved expedition #{num} ({name}) to:\n{path}")
        self._replay_status.setStyleSheet("color: #4a7;")
