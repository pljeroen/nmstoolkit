"""Save directory scanner — finds NMS save profiles and slots.

Pure domain module. Uses lz4 for decompression (same as codec.py).
"""

from __future__ import annotations

import json
import re
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import List

import lz4.block

MAGIC = 0xFEEDA1E5
_SAVE_PATTERN = re.compile(r"^save(\d*)\.hg$", re.IGNORECASE)


@dataclass(frozen=True)
class SaveSlot:
    """A single save slot within a profile."""

    slot_number: int
    path: Path
    save_name: str
    last_modified: float


@dataclass(frozen=True)
class SaveProfile:
    """A Steam profile directory containing save slots."""

    steam_id: str
    path: Path
    save_slots: List[SaveSlot]


def quick_read_save_name(path: Path) -> str:
    """Extract SaveName from a .hg file by decompressing only the first block.

    Returns empty string on any failure.
    """
    try:
        data = path.read_bytes()
        if not data:
            return ""

        # Check if LZ4 compressed
        if len(data) >= 4 and struct.unpack_from("<I", data, 0)[0] == MAGIC:
            if len(data) < 16:
                return ""
            _, comp_size, uncomp_size, _ = struct.unpack_from("<IIII", data, 0)
            compressed = data[16:16 + comp_size]
            decompressed = lz4.block.decompress(
                compressed, uncompressed_size=uncomp_size
            )
            json_str = decompressed.rstrip(b"\x00").decode("utf-8", errors="replace")
        else:
            # Plain JSON (e.g. accountdata.hg)
            json_str = data.rstrip(b"\x00").decode("utf-8", errors="replace")

        parsed = json.loads(json_str)
        return parsed.get("CommonStateData", {}).get("SaveName", "")
    except Exception:
        return ""


def _slot_number_from_filename(filename: str) -> int:
    """Extract slot number from save filename.

    save.hg → 1, save2.hg → 2, save15.hg → 15.
    Returns 0 if not a valid save filename.
    """
    match = _SAVE_PATTERN.match(filename)
    if not match:
        return 0
    num = match.group(1)
    return int(num) if num else 1


def _scan_profile_dir(profile_dir: Path) -> List[SaveSlot]:
    """Scan a single directory for save slots."""
    slots = []
    for hg_file in profile_dir.glob("*.hg"):
        name = hg_file.name.lower()
        # Exclude accountdata and mf_save files
        if name.startswith("accountdata") or name.startswith("mf_"):
            continue
        slot_num = _slot_number_from_filename(hg_file.name)
        if slot_num == 0:
            continue
        save_name = quick_read_save_name(hg_file)
        slots.append(SaveSlot(
            slot_number=slot_num,
            path=hg_file,
            save_name=save_name,
            last_modified=hg_file.stat().st_mtime,
        ))
    slots.sort(key=lambda s: s.slot_number)
    return slots


def scan_for_profiles(base_dirs: List[Path]) -> List[SaveProfile]:
    """Scan base directories for NMS save profiles.

    Looks for subdirectories named st_<steamid> containing save*.hg files.
    Also checks directories themselves for save files (direct profile dir).

    Args:
        base_dirs: List of directories to scan.

    Returns:
        List of SaveProfile objects found.
    """
    profiles = []
    seen_paths = set()

    for base_dir in base_dirs:
        if not base_dir.exists() or not base_dir.is_dir():
            continue

        # Check subdirectories (st_<steamid> pattern)
        for sub in sorted(base_dir.iterdir()):
            if not sub.is_dir():
                continue
            if sub in seen_paths:
                continue

            slots = _scan_profile_dir(sub)
            if not slots:
                continue

            seen_paths.add(sub)
            steam_id = sub.name
            if steam_id.startswith("st_"):
                steam_id = steam_id[3:]

            profiles.append(SaveProfile(
                steam_id=steam_id,
                path=sub,
                save_slots=slots,
            ))

        # Check base_dir itself for save files (direct profile dir)
        if base_dir not in seen_paths:
            slots = _scan_profile_dir(base_dir)
            if slots:
                seen_paths.add(base_dir)
                profiles.append(SaveProfile(
                    steam_id=base_dir.name,
                    path=base_dir,
                    save_slots=slots,
                ))

    return profiles
