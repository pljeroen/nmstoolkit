"""Application path helpers: packaged resources vs user-writable data/cache."""

from __future__ import annotations

import os
import sys
from pathlib import Path

_APP_NAME = "nmstoolkit"


def resource_dir() -> Path:
    """Return packaged read-only resource directory."""
    return Path(__file__).resolve().parent / "data"


def _platform_cache_base() -> Path:
    if sys.platform == "win32":
        return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local"))
    if sys.platform == "darwin":
        return Path.home() / "Library/Caches"
    return Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))


def _platform_data_base() -> Path:
    if sys.platform == "win32":
        return Path(os.environ.get("APPDATA", Path.home() / "AppData/Roaming"))
    if sys.platform == "darwin":
        return Path.home() / "Library/Application Support"
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share"))


def user_cache_root() -> Path:
    """Return writable cache root for runtime-generated artifacts."""
    override = os.environ.get("NMSTOOLKIT_CACHE_DIR")
    if override:
        root = Path(override)
    elif getattr(sys, "frozen", False):
        root = Path(sys.executable).parent
    else:
        root = _platform_cache_base() / _APP_NAME
    root.mkdir(parents=True, exist_ok=True)
    return root


def user_data_root() -> Path:
    """Return writable data root for persistent user-managed artifacts."""
    override = os.environ.get("NMSTOOLKIT_DATA_DIR")
    if override:
        root = Path(override)
    elif getattr(sys, "frozen", False):
        root = Path(sys.executable).parent
    else:
        root = _platform_data_base() / _APP_NAME
    root.mkdir(parents=True, exist_ok=True)
    return root


def cache_icons_dir() -> Path:
    path = user_cache_root() / "icons"
    path.mkdir(parents=True, exist_ok=True)
    return path


def cache_meshes_dir() -> Path:
    path = user_cache_root() / "meshes"
    path.mkdir(parents=True, exist_ok=True)
    return path


def external_tools_dir() -> Path:
    path = user_data_root() / "ExternalTools"
    path.mkdir(parents=True, exist_ok=True)
    return path
