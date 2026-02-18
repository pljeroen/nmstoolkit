"""Tests for save scanner.

Tests R-SCAN-01 through R-SCAN-07.
Uses synthetic save directory structures.
"""

import ast
import json
import struct
from pathlib import Path
from textwrap import dedent

import lz4.block
import pytest

from nmstoolkit.core.save_scanner import (
    SaveProfile,
    SaveSlot,
    scan_for_profiles,
    quick_read_save_name,
)


# ---------------------------------------------------------------------------
# Helpers — create synthetic .hg save files
# ---------------------------------------------------------------------------

MAGIC = 0xFEEDA1E5
BLOCK_SIZE = 0x80000


def _make_hg_file(data: dict) -> bytes:
    """Create a minimal LZ4-compressed .hg file from a dict."""
    json_str = json.dumps(data, separators=(",", ":"))
    raw = json_str.encode("utf-8") + b"\x00"
    compressed = lz4.block.compress(raw, store_size=False)
    header = struct.pack("<IIII", MAGIC, len(compressed), len(raw), 0)
    return header + compressed


def _create_save_dir(tmp_path: Path, steam_id: str, slots: dict) -> Path:
    """Create a synthetic save directory structure.

    Args:
        tmp_path: Parent directory.
        steam_id: Steam ID for the profile directory name.
        slots: Mapping of filename -> save name, e.g. {"save.hg": "My Save"}.

    Returns:
        Path to the profile directory.
    """
    profile_dir = tmp_path / f"st_{steam_id}"
    profile_dir.mkdir(parents=True)

    for filename, save_name in slots.items():
        data = {"CommonStateData": {"SaveName": save_name}}
        (profile_dir / filename).write_bytes(_make_hg_file(data))

    return profile_dir


# ---------------------------------------------------------------------------
# R-SCAN-01: SaveSlot dataclass
# ---------------------------------------------------------------------------

class TestSaveSlot:
    """R-SCAN-01: SaveSlot holds slot metadata."""

    def test_slot_fields(self):
        slot = SaveSlot(
            slot_number=1,
            path=Path("/fake/save.hg"),
            save_name="My Save",
            last_modified=1234567890.0,
        )
        assert slot.slot_number == 1
        assert slot.path == Path("/fake/save.hg")
        assert slot.save_name == "My Save"
        assert slot.last_modified == 1234567890.0

    def test_slot_is_frozen(self):
        slot = SaveSlot(
            slot_number=1,
            path=Path("/fake/save.hg"),
            save_name="Test",
            last_modified=0.0,
        )
        with pytest.raises(AttributeError):
            slot.save_name = "Changed"


# ---------------------------------------------------------------------------
# R-SCAN-02: SaveProfile dataclass
# ---------------------------------------------------------------------------

class TestSaveProfile:
    """R-SCAN-02: SaveProfile groups slots under a Steam ID."""

    def test_profile_fields(self):
        slot = SaveSlot(1, Path("/fake/save.hg"), "Test", 0.0)
        profile = SaveProfile(
            steam_id="76561198078575175",
            path=Path("/fake/profile_76561198078575175"),
            save_slots=[slot],
        )
        assert profile.steam_id == "76561198078575175"
        assert len(profile.save_slots) == 1

    def test_profile_is_frozen(self):
        profile = SaveProfile(
            steam_id="123",
            path=Path("/fake"),
            save_slots=[],
        )
        with pytest.raises(AttributeError):
            profile.steam_id = "456"


# ---------------------------------------------------------------------------
# R-SCAN-03: Quick-read save name from .hg
# ---------------------------------------------------------------------------

class TestQuickReadSaveName:
    """R-SCAN-03: Extract SaveName from first LZ4 block without full parse."""

    def test_reads_save_name(self, tmp_path):
        data = {"CommonStateData": {"SaveName": "Explorer Alpha"}}
        hg_file = tmp_path / "save.hg"
        hg_file.write_bytes(_make_hg_file(data))

        assert quick_read_save_name(hg_file) == "Explorer Alpha"

    def test_missing_save_name_returns_empty(self, tmp_path):
        data = {"CommonStateData": {}}
        hg_file = tmp_path / "save.hg"
        hg_file.write_bytes(_make_hg_file(data))

        assert quick_read_save_name(hg_file) == ""

    def test_corrupt_file_returns_empty(self, tmp_path):
        hg_file = tmp_path / "save.hg"
        hg_file.write_bytes(b"not a valid hg file")

        assert quick_read_save_name(hg_file) == ""

    def test_plain_json_account_data(self, tmp_path):
        """accountdata.hg is plain JSON — quick_read should handle it."""
        data = {"CommonStateData": {"SaveName": "Account"}}
        hg_file = tmp_path / "accountdata.hg"
        hg_file.write_bytes(json.dumps(data).encode("utf-8"))

        assert quick_read_save_name(hg_file) == "Account"


# ---------------------------------------------------------------------------
# R-SCAN-04: Scan for profiles
# ---------------------------------------------------------------------------

class TestScanForProfiles:
    """R-SCAN-04: Scan directories for save profiles."""

    def test_finds_single_profile(self, tmp_path):
        _create_save_dir(tmp_path, "12345", {"save.hg": "Slot 1"})

        profiles = scan_for_profiles([tmp_path])
        assert len(profiles) == 1
        assert profiles[0].steam_id == "12345"
        assert len(profiles[0].save_slots) == 1
        assert profiles[0].save_slots[0].save_name == "Slot 1"

    def test_finds_multiple_slots(self, tmp_path):
        _create_save_dir(tmp_path, "12345", {
            "save.hg": "Slot 1",
            "save2.hg": "Slot 2",
            "save3.hg": "Slot 3",
        })

        profiles = scan_for_profiles([tmp_path])
        assert len(profiles) == 1
        assert len(profiles[0].save_slots) == 3

    def test_slots_sorted_by_number(self, tmp_path):
        _create_save_dir(tmp_path, "12345", {
            "save3.hg": "Third",
            "save.hg": "First",
            "save2.hg": "Second",
        })

        profiles = scan_for_profiles([tmp_path])
        slots = profiles[0].save_slots
        assert slots[0].slot_number == 1
        assert slots[1].slot_number == 2
        assert slots[2].slot_number == 3

    def test_excludes_accountdata(self, tmp_path):
        profile_dir = _create_save_dir(tmp_path, "12345", {"save.hg": "Slot 1"})
        # Add accountdata — should NOT appear as a slot
        account = {"CommonStateData": {"SaveName": "Account"}}
        (profile_dir / "accountdata.hg").write_bytes(_make_hg_file(account))

        profiles = scan_for_profiles([tmp_path])
        slot_names = [s.save_name for s in profiles[0].save_slots]
        assert "Account" not in slot_names
        assert len(profiles[0].save_slots) == 1

    def test_excludes_mf_save_files(self, tmp_path):
        profile_dir = _create_save_dir(tmp_path, "12345", {"save.hg": "Slot 1"})
        mf_data = {"CommonStateData": {"SaveName": "MF"}}
        (profile_dir / "mf_save.hg").write_bytes(_make_hg_file(mf_data))

        profiles = scan_for_profiles([tmp_path])
        assert len(profiles[0].save_slots) == 1

    def test_no_profiles_in_empty_dir(self, tmp_path):
        profiles = scan_for_profiles([tmp_path])
        assert profiles == []

    def test_multiple_base_dirs(self, tmp_path):
        dir1 = tmp_path / "loc1"
        dir1.mkdir()
        dir2 = tmp_path / "loc2"
        dir2.mkdir()
        _create_save_dir(dir1, "111", {"save.hg": "Save A"})
        _create_save_dir(dir2, "222", {"save.hg": "Save B"})

        profiles = scan_for_profiles([dir1, dir2])
        assert len(profiles) == 2

    def test_nonexistent_base_dir_skipped(self, tmp_path):
        fake = tmp_path / "nonexistent"
        profiles = scan_for_profiles([fake])
        assert profiles == []


# ---------------------------------------------------------------------------
# R-SCAN-05: Slot numbering from filename
# ---------------------------------------------------------------------------

class TestSlotNumbering:
    """R-SCAN-05: Slot numbers derived from save filenames."""

    def test_save_hg_is_slot_1(self, tmp_path):
        _create_save_dir(tmp_path, "12345", {"save.hg": "First"})
        profiles = scan_for_profiles([tmp_path])
        assert profiles[0].save_slots[0].slot_number == 1

    def test_save2_hg_is_slot_2(self, tmp_path):
        _create_save_dir(tmp_path, "12345", {"save2.hg": "Second"})
        profiles = scan_for_profiles([tmp_path])
        assert profiles[0].save_slots[0].slot_number == 2

    def test_save15_hg_is_slot_15(self, tmp_path):
        _create_save_dir(tmp_path, "12345", {"save15.hg": "Fifteen"})
        profiles = scan_for_profiles([tmp_path])
        assert profiles[0].save_slots[0].slot_number == 15


# ---------------------------------------------------------------------------
# R-SCAN-06: Profile without st_ prefix (direct profile dir)
# ---------------------------------------------------------------------------

class TestDirectProfileDir:
    """R-SCAN-06: Directories with save files but no st_ prefix are found."""

    def test_direct_save_dir(self, tmp_path):
        """A directory with save.hg directly in it (no st_ subdirectory)."""
        profile_dir = tmp_path / "my_saves"
        profile_dir.mkdir()
        data = {"CommonStateData": {"SaveName": "Direct"}}
        (profile_dir / "save.hg").write_bytes(_make_hg_file(data))

        profiles = scan_for_profiles([tmp_path])
        assert len(profiles) == 1
        assert profiles[0].save_slots[0].save_name == "Direct"


# ---------------------------------------------------------------------------
# R-SCAN-07: Domain purity
# ---------------------------------------------------------------------------

class TestScannerDomainPurity:
    """R-SCAN-07: save_scanner.py uses only stdlib."""

    def test_no_external_imports(self):
        scanner_path = (
            Path(__file__).parent.parent.parent
            / "src"
            / "nmstoolkit"
            / "core"
            / "save_scanner.py"
        )
        source = scanner_path.read_text()
        tree = ast.parse(source)

        stdlib_modules = {
            "xml", "pathlib", "typing", "collections", "dataclasses",
            "enum", "os", "sys", "io", "re", "functools", "itertools",
            "__future__", "json", "struct", "lz4",
        }

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top = alias.name.split(".")[0]
                    assert top in stdlib_modules, (
                        f"Non-stdlib import: {alias.name}"
                    )
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    top = node.module.split(".")[0]
                    assert top in stdlib_modules, (
                        f"Non-stdlib import: from {node.module}"
                    )
