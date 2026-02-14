"""Tests for codec binary-safe decoding.

Tests R-CODEC-01: decompress_hg handles non-UTF-8 bytes gracefully.
"""

import json
import struct

import lz4.block
import pytest

from nmstoolkit.core.codec import MAGIC, BLOCK_SIZE


def _make_hg_with_raw_content(raw: bytes) -> bytes:
    """Build a .hg file from raw content bytes (adds null terminator)."""
    content = raw + b"\x00"
    result = bytearray()
    offset = 0
    while offset < len(content):
        chunk = content[offset : offset + BLOCK_SIZE]
        compressed = lz4.block.compress(chunk, store_size=False)
        result.extend(struct.pack("<IIII", MAGIC, len(compressed), len(chunk), 0))
        result.extend(compressed)
        offset += BLOCK_SIZE
    return bytes(result)


class TestBinarySafeDecompression:
    """R-CODEC-01: Non-UTF-8 bytes don't crash decompress_hg."""

    def test_binary_item_id_in_json(self):
        """Save with binary bytes in a string value should not crash."""
        from nmstoolkit.core.codec import decompress_hg

        # JSON with a binary item ID containing 0x80-0xFF bytes
        # These bytes are invalid UTF-8 but can appear in NMS saves
        raw = b'{"Id":"\x80\x81\x82","Amount":50}'
        hg_bytes = _make_hg_with_raw_content(raw)
        result = decompress_hg(hg_bytes)
        # Should not raise, replacement chars are acceptable
        assert "Amount" in result
        assert "50" in result

    def test_valid_utf8_still_works(self):
        """Normal UTF-8 content is unaffected by errors='replace'."""
        from nmstoolkit.core.codec import decompress_hg

        obj = {"name": "Metal Plating", "value": 800}
        raw = json.dumps(obj).encode("utf-8")
        hg_bytes = _make_hg_with_raw_content(raw)
        result = decompress_hg(hg_bytes)
        parsed = json.loads(result)
        assert parsed == obj
