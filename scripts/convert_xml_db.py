#!/usr/bin/env python3
"""One-time conversion: old editor XML databases → JSON for Stellar Edit."""

import json
import os
import xml.etree.ElementTree as ET
from pathlib import Path

OLD_DB = Path(os.environ.get("NMS_OLD_DB_DIR", "legacy_db"))
OUT_DIR = Path(os.environ.get("NMS_OUT_DATA_DIR", "src/nmstoolkit/data"))
TEMPLATE_SRC = Path(os.environ.get("NMS_OLD_TEMPLATE_DIR", "legacy_templates"))


def convert_items():
    """Convert items.xml → items.json."""
    tree = ET.parse(OLD_DB / "items.xml")
    root = tree.getroot()
    items = []
    for elem in root:
        item = dict(elem.attrib)
        item["type"] = elem.tag  # "substance", "product", or "technology"
        desc = elem.find("description")
        if desc is not None and desc.text:
            item["description"] = desc.text.strip()
        items.append(item)
    return items


def convert_frigates():
    """Convert frigates.xml → frigates.json."""
    tree = ET.parse(OLD_DB / "frigates.xml")
    root = tree.getroot()
    traits = []
    for elem in root:
        trait = dict(elem.attrib)
        trait["beneficial"] = trait["beneficial"] == "true"
        if "secondary" in trait:
            trait["secondary"] = trait["secondary"].split(",")
        traits.append(trait)
    return traits


def convert_settlements():
    """Convert settlements.xml → settlements.json."""
    tree = ET.parse(OLD_DB / "settlements.xml")
    root = tree.getroot()
    perks = []
    for elem in root:
        perk = dict(elem.attrib)
        perk["beneficial"] = perk["beneficial"] == "true"
        perk["procedural"] = perk["procedural"] == "true"
        perk["starter"] = perk.get("starter", "false") == "true"
        perks.append(perk)
    return perks


def convert_rewards():
    """Convert rewards.xml → rewards.json."""
    tree = ET.parse(OLD_DB / "rewards.xml")
    root = tree.getroot()
    return [dict(elem.attrib) for elem in root]


def convert_inventory():
    """Convert inventory.xml → inventory.json."""
    tree = ET.parse(OLD_DB / "inventory.xml")
    root = tree.getroot()
    difficulties = {}
    for diff_elem in root:
        diff_id = diff_elem.attrib["id"]
        stacks = []
        for stack in diff_elem:
            entry = dict(stack.attrib)
            entry["product"] = int(entry["product"])
            entry["substance"] = int(entry["substance"])
            stacks.append(entry)
        difficulties[diff_id] = stacks
    return difficulties


def convert_words():
    """Convert words.xml → words.json."""
    tree = ET.parse(OLD_DB / "words.xml")
    root = tree.getroot()
    words = []
    for elem in root:
        word = {"id": elem.attrib["id"], "text": elem.attrib["text"]}
        groups = []
        for group_elem in elem:
            groups.append(dict(group_elem.attrib))
        if groups:
            word["groups"] = groups
        words.append(word)
    return words


def copy_key_maps():
    """Copy key mapping files as-is (they're already tab-separated)."""
    for name in ("jsonmap.txt", "jsonmapac.txt"):
        src = OLD_DB / name
        dst = OUT_DIR / name
        dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"  Copied {name} ({dst.stat().st_size} bytes)")


def copy_templates():
    """Copy JSON templates from old editor."""
    tmpl_src = TEMPLATE_SRC
    tmpl_dst = OUT_DIR / "templates"
    tmpl_dst.mkdir(exist_ok=True)
    for src_file in tmpl_src.glob("*.json"):
        dst_file = tmpl_dst / src_file.name
        dst_file.write_text(src_file.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"  Copied template {src_file.name}")


def write_json(data, name):
    path = OUT_DIR / name
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"  {name}: {path.stat().st_size} bytes")


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Converting XML databases...")
    write_json(convert_items(), "items.json")
    write_json(convert_frigates(), "frigates.json")
    write_json(convert_settlements(), "settlements.json")
    write_json(convert_rewards(), "rewards.json")
    write_json(convert_inventory(), "inventory.json")
    write_json(convert_words(), "words.json")

    print("\nCopying key maps...")
    copy_key_maps()

    print("\nCopying templates...")
    copy_templates()

    print("\nDone.")


if __name__ == "__main__":
    main()
