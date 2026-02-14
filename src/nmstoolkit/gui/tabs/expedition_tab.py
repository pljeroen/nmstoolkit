"""Expedition / Season data tab.

Displays current expedition progress, historical season data,
and provides offline expedition replay by downloading SEASON_DATA_CACHE.JSON
from the cwmonkey/nms-expeditions repository.
"""

import json
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

        layout.addWidget(season_group)

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

        layout.addWidget(milestone_group)

        # Redeemed season rewards
        rewards_group = QGroupBox("Redeemed Season Rewards")
        rewards_layout = QVBoxLayout(rewards_group)

        self._rewards_table = QTableWidget()
        self._rewards_table.setColumnCount(1)
        self._rewards_table.setHorizontalHeaderLabels(["Reward ID"])
        self._rewards_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )
        self._rewards_table.setAlternatingRowColors(True)
        rewards_layout.addWidget(self._rewards_table)

        layout.addWidget(rewards_group)

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

        layout.addWidget(replay_group)

    def set_data(self, psd: dict, common_state: dict = None):
        self._data = psd
        self._common_data = common_state or {}

        self._populate_season_info()
        self._populate_milestones()
        self._populate_rewards()

    def _populate_season_info(self):
        season_data = self._common_data.get("SeasonData", {})
        season_state = self._common_data.get("SeasonState", {})

        if not season_data:
            self._season_info.setText("No active expedition")
            self._final_reward_label.setText("")
            return

        season_num = season_data.get("SeasonNumber", "?")
        season_name = season_data.get("SeasonName", "Unknown")
        season_id = season_data.get("SeasonId", "?")

        has_final = season_state.get("HasCollectedFinalReward", False)
        final_status = "Collected" if has_final else "Not collected"

        self._season_info.setText(
            f"Season {season_id} (#{season_num}) — {season_name}"
        )
        self._final_reward_label.setText(
            f"Final Reward: {season_data.get('FinalReward', '—')} ({final_status})"
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
        redeemed = []
        if self._data:
            redeemed = self._data.get("RedeemedSeasonRewards", [])

        self._rewards_table.setRowCount(len(redeemed))
        for row, reward in enumerate(redeemed):
            reward_id = str(reward)
            display = _resolve_reward_name(reward_id)
            item = QTableWidgetItem(display)
            item.setToolTip(reward_id)
            pixmap = get_item_icon(reward_id)
            if pixmap is not None:
                item.setIcon(QIcon(pixmap))
            self._rewards_table.setItem(row, 0, item)

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
