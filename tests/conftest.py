"""Shared test fixtures."""

import json
import struct
from pathlib import Path

import lz4.block
import pytest

# Path to real save files for integration tests
SAVE_DIR = Path("/home/jeroen/dev/NMSSaveEditor/st_76561198078575175")
OLD_EDITOR_DB = Path("/home/jeroen/dev/NMSSaveEditor/NMSSaveEditor/nomanssave/db")

# Minimal valid JSON for test saves
MINIMAL_SAVE_JSON = {"F2P": 1234, "8>q": "Win|Final", "XTp": "Main"}


def make_hg_bytes(json_obj: dict, block_size: int = 524288) -> bytes:
    """Create a valid .hg file from a JSON object."""
    json_bytes = json.dumps(json_obj, separators=(",", ":")).encode("utf-8") + b"\x00"

    result = bytearray()
    offset = 0
    while offset < len(json_bytes):
        chunk = json_bytes[offset : offset + block_size]
        compressed = lz4.block.compress(chunk, store_size=False)
        result.extend(struct.pack("<IIII", 0xFEEDA1E5, len(compressed), len(chunk), 0))
        result.extend(compressed)
        offset += block_size

    return bytes(result)


@pytest.fixture
def minimal_hg_bytes():
    """Minimal valid .hg file bytes."""
    return make_hg_bytes(MINIMAL_SAVE_JSON)


@pytest.fixture
def minimal_hg_file(tmp_path, minimal_hg_bytes):
    """Minimal valid .hg file on disk."""
    path = tmp_path / "test_save.hg"
    path.write_bytes(minimal_hg_bytes)
    return path


@pytest.fixture
def real_save_path():
    """Path to a real save file (skip if not available)."""
    path = SAVE_DIR / "save.hg"
    if not path.exists():
        pytest.skip("Real save file not available")
    return path


@pytest.fixture
def real_account_path():
    """Path to real account data (skip if not available)."""
    path = SAVE_DIR / "accountdata.hg"
    if not path.exists():
        pytest.skip("Real account data not available")
    return path


@pytest.fixture
def key_map_path():
    """Path to jsonmap.txt."""
    path = OLD_EDITOR_DB / "jsonmap.txt"
    if not path.exists():
        pytest.skip("Key map file not available")
    return path


@pytest.fixture
def account_key_map_path():
    """Path to jsonmapac.txt."""
    path = OLD_EDITOR_DB / "jsonmapac.txt"
    if not path.exists():
        pytest.skip("Account key map file not available")
    return path
