#!/usr/bin/env python3
"""Diagnostic: dump corvette inventory data from NMS save files.

Outputs all corvette ship inventory slots with every field, so we can
understand the exact data model for 3D grid placement.

Run: .venv/bin/python scripts/diag_corvette_inventory.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from nmstoolkit.core.save_file import SaveFile

# Find save files — search root dir (active saves) and backup dirs
PROFILE_DIR = Path("/home/jeroen/dev/NMS_GameFiles/st_76561198078575175")
KEY_MAP = Path(__file__).resolve().parent.parent / "src" / "nmstoolkit" / "data" / "jsonmap.txt"
OUT = Path("/tmp/nms_corvette_inventory_dump.txt")


def _is_corvette(ship):
    filename = ship.get("Resource", {}).get("Filename", "").upper()
    return "BIGGS" in filename


def main():
    lines = []
    def log(msg=""):
        lines.append(msg)
        print(msg)

    # Collect all save files: root dir first (active saves), then backups
    save_files = sorted(PROFILE_DIR.glob("save*.hg"))
    for bdir in sorted(PROFILE_DIR.glob("backup*")):
        save_files.extend(sorted(bdir.glob("save*.hg")))

    for save_path in save_files:
        if save_path.name.startswith("mf_"):
            continue

        log(f"\n{'='*80}")
        log(f"SAVE: {save_path.name}")
        log(f"{'='*80}")

        try:
            save = SaveFile.load(save_path, KEY_MAP)
        except Exception as e:
            log(f"  ERROR loading: {e}")
            continue

        psd = save.player_state_data(context="base")

        # Dump draft corvette data
        log("\n--- DRAFT CORVETTE DATA ---")
        for key in ["CorvetteStorageInventory", "CorvetteStorageLayout",
                     "CorvetteEditAssociatedShipIndex", "CorvetteEditShipName",
                     "CorvetteDraftShipSeed"]:
            val = psd.get(key)
            if val is not None:
                if key == "CorvetteStorageLayout":
                    # Dump full structure — this is critical for understanding
                    log(f"\n{key} (FULL DUMP):")
                    log(f"  {json.dumps(val, indent=4, default=str)}")
                elif isinstance(val, dict) and "Slots" in val:
                    log(f"\n{key}:")
                    log(f"  Width: {val.get('Width')}")
                    log(f"  Height: {val.get('Height')}")
                    log(f"  Class: {val.get('Class')}")
                    slots = val.get("Slots", [])
                    log(f"  Slot count: {len(slots)}")
                    for i, s in enumerate(slots):
                        sid = str(s.get("Id", "")).lstrip("^")
                        if not sid:
                            continue
                        idx = s.get("Index", {})
                        log(f"  Slot[{i}]: Id={sid} X={idx.get('X')} Y={idx.get('Y')} "
                            f"Type={s.get('Type', {})} Amount={s.get('Amount')} "
                            f"FullyInstalled={s.get('FullyInstalled')}")
                    log(f"\n  ALL SLOTS RAW:")
                    for i, s in enumerate(slots):
                        log(f"    [{i}] {json.dumps(s, default=str)}")
                    # Dump ValidSlotIndices summary
                    vsi = val.get("ValidSlotIndices", [])
                    if vsi:
                        xs = sorted(set(v.get("X", 0) for v in vsi))
                        ys = sorted(set(v.get("Y", 0) for v in vsi))
                        log(f"  ValidSlotIndices: {len(vsi)} slots, X range [{min(xs)}-{max(xs)}], Y range [{min(ys)}-{max(ys)}]")
                        log(f"  ValidSlotIndices FULL:")
                        for v in vsi[:50]:
                            log(f"    X={v.get('X')} Y={v.get('Y')}")
                        if len(vsi) > 50:
                            log(f"    ... and {len(vsi) - 50} more")
                else:
                    log(f"{key}: {json.dumps(val, default=str)}")

        # Find completed corvettes
        ships = psd.get("ShipOwnership", [])
        corvettes = [(i, s) for i, s in enumerate(ships) if _is_corvette(s)]

        if not corvettes:
            log("\nNo completed corvettes found.")
            continue

        for ship_idx, ship in corvettes:
            log(f"\n--- COMPLETED CORVETTE [{ship_idx}] ---")
            log(f"  Name: {ship.get('Name', '(unnamed)')}")
            log(f"  Seed: {ship.get('Seed')}")
            log(f"  Resource: {ship.get('Resource', {}).get('Filename', '?')}")

            for inv_key in ["Inventory", "Inventory_TechOnly", "Inventory_Cargo"]:
                inv = ship.get(inv_key, {})
                if not inv:
                    continue
                slots = inv.get("Slots", [])
                log(f"\n  {inv_key}:")
                log(f"    Width: {inv.get('Width')}")
                log(f"    Height: {inv.get('Height')}")
                log(f"    Class: {inv.get('Class')}")
                log(f"    Slot count: {len(slots)}")

                # Group by B_ prefix vs other
                b_slots = []
                other_slots = []
                for s in slots:
                    sid = str(s.get("Id", "")).lstrip("^")
                    if sid.startswith("B_"):
                        b_slots.append(s)
                    elif sid:
                        other_slots.append(s)

                if b_slots:
                    log(f"\n    BUILD MODULES ({len(b_slots)}):")
                    for s in b_slots:
                        sid = str(s.get("Id", "")).lstrip("^")
                        idx = s.get("Index", {})
                        log(f"      {sid:20s} X={idx.get('X'):2d} Y={idx.get('Y'):2d}  "
                            f"Type={s.get('Type',{}).get('InventoryType','?'):10s}  "
                            f"Amount={s.get('Amount')}  "
                            f"MaxAmount={s.get('MaxAmount')}  "
                            f"DamageFactor={s.get('DamageFactor')}  "
                            f"FullyInstalled={s.get('FullyInstalled')}")
                    # Also dump raw JSON for every B_ slot for full field analysis
                    log(f"\n    BUILD MODULES RAW JSON:")
                    for s in b_slots:
                        log(f"      {json.dumps(s, default=str)}")

                if other_slots:
                    log(f"\n    OTHER ITEMS ({len(other_slots)}):")
                    for s in other_slots[:20]:  # limit to first 20
                        sid = str(s.get("Id", "")).lstrip("^")
                        idx = s.get("Index", {})
                        log(f"      {sid:30s} X={idx.get('X'):2d} Y={idx.get('Y'):2d}  "
                            f"Type={s.get('Type',{}).get('InventoryType','?'):10s}")
                    if len(other_slots) > 20:
                        log(f"      ... and {len(other_slots) - 20} more")

                # ValidSlotIndices summary
                vsi = inv.get("ValidSlotIndices", [])
                if vsi:
                    xs = sorted(set(v.get("X", 0) for v in vsi))
                    ys = sorted(set(v.get("Y", 0) for v in vsi))
                    log(f"\n    ValidSlotIndices: {len(vsi)} slots, "
                        f"X range [{min(xs)}-{max(xs)}], Y range [{min(ys)}-{max(ys)}]")

                # SpecialSlots
                ss = inv.get("SpecialSlots", [])
                if ss:
                    log(f"    SpecialSlots: {len(ss)}")
                    for s in ss[:5]:
                        log(f"      {s}")

        # Also check if there's a corvette layout per ship
        log("\n--- TOP-LEVEL CORVETTE KEYS ---")
        for key in sorted(psd.keys()):
            if "corvette" in key.lower() or "biggs" in key.lower():
                val = psd.get(key)
                if isinstance(val, (dict, list)):
                    log(f"  {key}: {type(val).__name__} len={len(val)}")
                else:
                    log(f"  {key}: {val}")

        # Continue scanning all saves to find corvettes

    OUT.write_text("\n".join(lines), encoding="utf-8")
    log(f"\nWritten to {OUT}")


if __name__ == "__main__":
    main()
