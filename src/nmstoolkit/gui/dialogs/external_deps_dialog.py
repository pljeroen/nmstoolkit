"""External dependencies management dialog.

Allows users to view status of and download external tools
(currently MBINCompiler) needed by the application.
"""

import json
import os
import sys
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QVBoxLayout,
)


GITHUB_RELEASES_URL = (
    "https://api.github.com/repos/monkeyman192/MBINCompiler/releases/latest"
)

_MBIN_NAMES = ["MBINCompiler", "MBINCompiler.exe"]


def _platform_asset_names() -> List[str]:
    """Return the asset filenames needed for the current platform."""
    if sys.platform == "win32":
        return ["MBINCompiler.exe", "libMBIN.dll"]
    return ["MBINCompiler-linux", "libMBIN-linux.so"]


def _extract_asset_urls(
    api_response: dict, wanted_names: List[str]
) -> Dict[str, str]:
    """Extract download URLs for wanted asset names from a GitHub release response."""
    urls: Dict[str, str] = {}
    for asset in api_response.get("assets", []):
        name = asset.get("name", "")
        if name in wanted_names:
            urls[name] = asset["browser_download_url"]
    return urls


def _extract_version(api_response: dict) -> str:
    """Extract version tag from a GitHub release response."""
    return api_response.get("tag_name", "unknown")


def detect_mbin_status(
    search_dirs: Optional[List[Path]] = None,
) -> dict:
    """Detect whether MBINCompiler is present in the given directories.

    Returns dict with keys: found (bool), path (Path|None).
    """
    if search_dirs is None:
        search_dirs = []

    for directory in search_dirs:
        if not directory.exists():
            continue
        for name in _MBIN_NAMES:
            candidate = directory / name
            if candidate.exists():
                return {"found": True, "path": candidate}

    return {"found": False, "path": None}


class _DownloadThread(QThread):
    """Background thread for downloading MBINCompiler assets."""

    progress = Signal(str)
    finished_ok = Signal()
    finished_err = Signal(str)

    def __init__(self, urls: Dict[str, str], dest_dir: Path, parent=None):
        super().__init__(parent)
        self._urls = urls
        self._dest_dir = dest_dir

    def run(self):
        try:
            self._dest_dir.mkdir(parents=True, exist_ok=True)

            for name, url in self._urls.items():
                self.progress.emit(f"Downloading {name}...")
                dest = self._dest_dir / name
                req = urllib.request.Request(
                    url, headers={"User-Agent": "NMSToolkit"}
                )
                with urllib.request.urlopen(req) as resp:
                    dest.write_bytes(resp.read())

                # Set executable permission on Linux
                if sys.platform != "win32" and "." not in name:
                    os.chmod(dest, 0o755)

            self.finished_ok.emit()
        except Exception as exc:
            self.finished_err.emit(str(exc))


class ExternalDepsDialog(QDialog):
    """Dialog showing external dependency status with download capability."""

    def __init__(self, external_tools_dir: Path, parent=None):
        super().__init__(parent)
        self._external_tools_dir = external_tools_dir
        self._download_thread: Optional[_DownloadThread] = None

        self.setWindowTitle("External Dependencies")
        self.setMinimumWidth(500)

        layout = QVBoxLayout(self)

        # Header
        header = QLabel("External tools required by NMS Toolkit:")
        header.setStyleSheet("font-weight: bold; margin-bottom: 8px;")
        layout.addWidget(header)

        # MBINCompiler row
        mbin_group = QVBoxLayout()
        mbin_header = QHBoxLayout()

        self._status_icon = QLabel()
        mbin_header.addWidget(self._status_icon)

        mbin_header.addWidget(QLabel("<b>MBINCompiler</b>"))
        mbin_header.addStretch()

        self._action_btn = QPushButton()
        self._action_btn.clicked.connect(self._on_action)
        mbin_header.addWidget(self._action_btn)

        mbin_group.addLayout(mbin_header)

        self._path_label = QLabel()
        self._path_label.setStyleSheet("color: #888; font-size: 11px; margin-left: 24px;")
        mbin_group.addWidget(self._path_label)

        self._desc_label = QLabel(
            "Converts .mbin game files to readable .exml. "
            "Required for the Extract Game Icons pipeline."
        )
        self._desc_label.setWordWrap(True)
        self._desc_label.setStyleSheet("color: #aaa; font-size: 11px; margin-left: 24px;")
        mbin_group.addWidget(self._desc_label)

        layout.addLayout(mbin_group)
        layout.addStretch()

        # Close button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self._close_btn = QPushButton("Close")
        self._close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self._close_btn)
        layout.addLayout(btn_layout)

        self._refresh_status()

    def _mbin_search_dirs(self) -> List[Path]:
        """Return directories to search for MBINCompiler."""
        return [self._external_tools_dir / "MBINCompiler"]

    def _refresh_status(self):
        """Update the display based on current MBINCompiler detection."""
        status = detect_mbin_status(self._mbin_search_dirs())

        if status["found"]:
            self._status_icon.setText("\u2705")
            self._path_label.setText(str(status["path"]))
            self._action_btn.setText("Update")
        else:
            self._status_icon.setText("\u274c")
            self._path_label.setText("Not found")
            self._action_btn.setText("Download Latest")

    def _on_action(self):
        """Start downloading MBINCompiler from GitHub."""
        self._action_btn.setEnabled(False)
        self._action_btn.setText("Checking...")

        try:
            req = urllib.request.Request(
                GITHUB_RELEASES_URL,
                headers={"User-Agent": "NMSToolkit"},
            )
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode())
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Download Failed",
                f"Could not fetch release info:\n{exc}",
            )
            self._action_btn.setEnabled(True)
            self._refresh_status()
            return

        wanted = _platform_asset_names()
        urls = _extract_asset_urls(data, wanted)

        if not urls:
            QMessageBox.warning(
                self,
                "No Assets Found",
                f"No matching assets found for this platform in release {_extract_version(data)}.",
            )
            self._action_btn.setEnabled(True)
            self._refresh_status()
            return

        version = _extract_version(data)
        dest_dir = self._external_tools_dir / "MBINCompiler"

        progress = QProgressDialog(
            f"Downloading MBINCompiler {version}...", None, 0, 0, self
        )
        progress.setWindowTitle("Downloading")
        progress.setMinimumDuration(0)
        progress.show()

        self._download_thread = _DownloadThread(urls, dest_dir, self)
        self._download_thread.progress.connect(progress.setLabelText)

        def on_ok():
            progress.close()
            self._action_btn.setEnabled(True)
            self._refresh_status()
            QMessageBox.information(
                self,
                "Download Complete",
                f"MBINCompiler {version} installed to:\n{dest_dir}",
            )

        def on_err(msg):
            progress.close()
            self._action_btn.setEnabled(True)
            self._refresh_status()
            QMessageBox.warning(
                self, "Download Failed", f"Error downloading:\n{msg}"
            )

        self._download_thread.finished_ok.connect(on_ok)
        self._download_thread.finished_err.connect(on_err)
        self._download_thread.start()
