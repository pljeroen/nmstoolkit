"""Codec for No Man's Sky .hg save files.

Handles LZ4 block compression/decompression and obfuscated key mapping.

.hg format:
  - One or more blocks, each:
    magic (4B, 0xFEEDA1E5) | compressed_size (4B) | uncompressed_size (4B) | padding (4B) | LZ4 data
  - Block uncompressed size is 512KB (0x80000) except possibly the last block.
  - Decompressed content is JSON with a trailing null byte.
  - Exception: accountdata.hg is plain JSON (no LZ4 header).
"""

import json
import struct
from pathlib import Path
from typing import Any, Dict, Union

import lz4.block

MAGIC = 0xFEEDA1E5
BLOCK_SIZE = 0x80000  # 512KB


def decompress_hg(data: bytes) -> str:
    """Decompress .hg LZ4 block data to a JSON string.

    Raises ValueError if the data has an invalid magic number or is empty.
    """
    if not data:
        raise ValueError("Empty input data")

    magic = struct.unpack_from("<I", data, 0)[0]
    if magic != MAGIC:
        raise ValueError(
            f"Invalid magic number: 0x{magic:08X} (expected 0x{MAGIC:08X})"
        )

    chunks = []
    offset = 0
    while offset < len(data):
        magic, comp_size, uncomp_size, _padding = struct.unpack_from(
            "<IIII", data, offset
        )
        if magic != MAGIC:
            raise ValueError(
                f"Invalid magic at offset {offset}: 0x{magic:08X}"
            )
        compressed = data[offset + 16 : offset + 16 + comp_size]
        decompressed = lz4.block.decompress(
            compressed, uncompressed_size=uncomp_size
        )
        chunks.append(decompressed)
        offset += 16 + comp_size

    raw = b"".join(chunks)
    return raw.rstrip(b"\x00").decode("utf-8", errors="replace")


def compress_hg(json_str: str) -> bytes:
    """Compress a JSON string into .hg LZ4 block format.

    Adds a trailing null byte before compression, matching the game's format.
    """
    raw = json_str.encode("utf-8") + b"\x00"

    result = bytearray()
    offset = 0
    while offset < len(raw):
        chunk = raw[offset : offset + BLOCK_SIZE]
        compressed = lz4.block.compress(chunk, store_size=False)
        result.extend(
            struct.pack("<IIII", MAGIC, len(compressed), len(chunk), 0)
        )
        result.extend(compressed)
        offset += BLOCK_SIZE

    return bytes(result)


def load_key_map(path: Union[str, Path]) -> Dict[str, str]:
    """Load a key mapping file (tab-separated: obfuscated<TAB>readable).

    Returns dict mapping obfuscated key → readable key.
    """
    key_map = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) == 2:
                obfuscated, readable = parts
                key_map[obfuscated] = readable
    return key_map


def unmap_keys(data: Any, key_map: Dict[str, str]) -> Any:
    """Recursively replace obfuscated keys with readable names."""
    if isinstance(data, dict):
        return {
            key_map.get(k, k): unmap_keys(v, key_map)
            for k, v in data.items()
        }
    if isinstance(data, list):
        return [unmap_keys(item, key_map) for item in data]
    return data


def map_keys(data: Any, key_map: Dict[str, str]) -> Any:
    """Recursively replace readable keys with obfuscated names."""
    reverse_map = {v: k for k, v in key_map.items()}
    return _map_keys_inner(data, reverse_map)


def _map_keys_inner(data: Any, reverse_map: Dict[str, str]) -> Any:
    if isinstance(data, dict):
        return {
            reverse_map.get(k, k): _map_keys_inner(v, reverse_map)
            for k, v in data.items()
        }
    if isinstance(data, list):
        return [_map_keys_inner(item, reverse_map) for item in data]
    return data


def _is_lz4_compressed(data: bytes) -> bool:
    """Check if data starts with the .hg LZ4 magic number."""
    if len(data) < 4:
        return False
    return struct.unpack_from("<I", data, 0)[0] == MAGIC


def read_hg_file(path: Union[str, Path]) -> dict:
    """Read a .hg file and return the parsed JSON dict.

    Handles both LZ4-compressed saves and plain JSON (accountdata.hg).
    """
    path = Path(path)
    data = path.read_bytes()

    if _is_lz4_compressed(data):
        json_str = decompress_hg(data)
    else:
        json_str = data.rstrip(b"\x00").decode("utf-8")

    return json.loads(json_str)


def write_hg_file(path: Union[str, Path], obj: dict) -> None:
    """Write a dict as a .hg file with LZ4 block compression."""
    path = Path(path)
    json_str = json.dumps(obj, separators=(",", ":"))
    compressed = compress_hg(json_str)
    path.write_bytes(compressed)
