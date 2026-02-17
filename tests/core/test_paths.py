"""Tests for resource/cache/data path separation."""

from pathlib import Path
from unittest.mock import patch


def test_resource_dir_points_to_package_data():
    from nmstoolkit.paths import resource_dir

    path = resource_dir()
    assert path.name == "data"
    assert (path / "items.json").exists()


def test_user_cache_root_uses_env_override(tmp_path):
    from nmstoolkit.paths import user_cache_root

    override = tmp_path / "cache_home"
    with patch.dict("os.environ", {"NMSTOOLKIT_CACHE_DIR": str(override)}):
        path = user_cache_root()

    assert path == override
    assert path.exists()


def test_user_data_root_uses_env_override(tmp_path):
    from nmstoolkit.paths import user_data_root

    override = tmp_path / "data_home"
    with patch.dict("os.environ", {"NMSTOOLKIT_DATA_DIR": str(override)}):
        path = user_data_root()

    assert path == override
    assert path.exists()


def test_cache_icons_dir_under_cache_root(tmp_path):
    from nmstoolkit.paths import cache_icons_dir

    root = tmp_path / "cache_home"
    with patch.dict("os.environ", {"NMSTOOLKIT_CACHE_DIR": str(root)}):
        icons = cache_icons_dir()

    assert icons == root / "icons"
    assert icons.exists()


def test_external_tools_dir_under_data_root(tmp_path):
    from nmstoolkit.paths import external_tools_dir

    root = tmp_path / "data_home"
    with patch.dict("os.environ", {"NMSTOOLKIT_DATA_DIR": str(root)}):
        tools = external_tools_dir()

    assert tools == root / "ExternalTools"
    assert tools.exists()
