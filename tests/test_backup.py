"""Tests for backup module."""

from pathlib import Path
from unittest.mock import patch

import pytest

from nmstoolkit.backup import create_backup


class TestCreateBackup:
    def test_creates_backup_directory(self, tmp_path):
        original = tmp_path / "save.hg"
        original.write_bytes(b"test data")
        backup_dir = tmp_path / "backup"

        create_backup(original, backup_dir)

        assert backup_dir.exists()

    def test_copies_file_with_timestamp(self, tmp_path):
        original = tmp_path / "save.hg"
        original.write_bytes(b"test data")
        backup_dir = tmp_path / "backup"

        result = create_backup(original, backup_dir)

        assert result.exists()
        assert result.read_bytes() == b"test data"
        assert result.name.startswith("save_")
        assert result.suffix == ".hg"

    def test_preserves_content(self, tmp_path):
        original = tmp_path / "save.hg"
        content = b"x" * 100_000
        original.write_bytes(content)
        backup_dir = tmp_path / "backup"

        result = create_backup(original, backup_dir)
        assert result.read_bytes() == content

    def test_multiple_backups_coexist(self, tmp_path):
        original = tmp_path / "save.hg"
        original.write_bytes(b"v1")
        backup_dir = tmp_path / "backup"

        with patch("nmstoolkit.backup._timestamp", return_value="20260214_100000"):
            b1 = create_backup(original, backup_dir)

        original.write_bytes(b"v2")
        with patch("nmstoolkit.backup._timestamp", return_value="20260214_100001"):
            b2 = create_backup(original, backup_dir)

        assert b1 != b2
        assert b1.read_bytes() == b"v1"
        assert b2.read_bytes() == b"v2"

    def test_returns_backup_path(self, tmp_path):
        original = tmp_path / "save.hg"
        original.write_bytes(b"data")
        backup_dir = tmp_path / "backup"

        result = create_backup(original, backup_dir)
        assert isinstance(result, Path)
        assert result.parent == backup_dir

    def test_nonexistent_source_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            create_backup(tmp_path / "missing.hg", tmp_path / "backup")

    def test_default_backup_dir_is_sibling(self, tmp_path):
        original = tmp_path / "saves" / "save.hg"
        original.parent.mkdir()
        original.write_bytes(b"data")

        result = create_backup(original)

        assert result.parent == tmp_path / "saves" / "backup"
