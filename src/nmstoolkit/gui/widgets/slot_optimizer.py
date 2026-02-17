"""Slot optimizer — rearranges technology items for maximum adjacency bonuses.

NMS adjacency bonus: same-type technologies placed next to each other
(up/down/left/right) receive a ~10% stacking bonus. Supercharged slots
give an additional multiplier.

This module provides a pure function that modifies an inventory dict in-place.
"""

from __future__ import annotations

import copy
from collections import defaultdict
from typing import Dict, List, Optional, Set, Tuple


def _get_tech_category(item_id: str, catalogue) -> str:
    """Determine the technology category/group for adjacency purposes.

    Uses ID family grouping first; only falls back to catalogue category when
    no useful ID family exists.
    """
    if not item_id:
        return ""

    # Group by ID prefix/family first (strip ^ and procedural suffix)
    uid = item_id.lstrip("^").split("#")[0]

    # Common prefix groupings for NMS upgrades
    prefixes = [
        "UP_LASER", "UP_SCAN", "UP_BOLT", "UP_GREN", "UP_RAIL", "UP_SHOT",
        "UP_SMG", "UP_CANN", "UP_SENGUN",
        "UP_SHLD", "UP_ENGY", "UP_JET", "UP_HAZ",
        "UP_HOT", "UP_COLD", "UP_TOX", "UP_RAD", "UP_UNW",
        "UA_PULSE", "UA_LAUN", "UA_HYP", "UA_SGUN",
        "UA_PHOTON", "UA_PHASE", "UA_ROCKET", "UA_SHIELD",
        "UP_PULSE", "UP_LAUN", "UP_HYP", "UP_SGUN",
        "UP_PHOTON", "UP_PHASE", "UP_ROCKET", "UP_SHIELD",
        "UP_FREIG", "UP_FRHYP", "UP_FRSCAN",
    ]
    for prefix in prefixes:
        if uid.upper().startswith(prefix):
            return prefix

    # Generic prefix: first two segments
    parts = uid.split("_")
    if len(parts) >= 2:
        return f"{parts[0]}_{parts[1]}"
    if catalogue is not None:
        item = catalogue.find_item(uid) or catalogue.find_item(item_id)
        if item is not None:
            cat = item.get("category", "")
            if cat:
                return cat
    return uid


def _group_priority(group: str, group_slots: List[dict], mode: str) -> int:
    if mode == "balanced":
        return 1
    marker = f"{group.upper()} " + " ".join(s.get("Id", "").upper() for s in group_slots)
    dps_markers = (
        "LASER", "BOLT", "SHOT", "RAIL", "CANN", "SMG", "GRENADE",
        "PHOTON", "ROCKET", "PHASE", "SGUN", "DAMAGE",
    )
    endurance_markers = (
        "SHIELD", "SHLD", "ENGY", "JET", "HAZ", "HOT", "COLD",
        "TOX", "RAD", "UNW", "LIFE", "PROTECT",
    )
    if mode == "dps":
        return 3 if any(m in marker for m in dps_markers) else 1
    if mode == "endurance":
        return 3 if any(m in marker for m in endurance_markers) else 1
    return 1


def _neighbors(x: int, y: int) -> List[Tuple[int, int]]:
    """Return 4-directional neighbors."""
    return [(x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)]


def _score_placement(
    positions: Dict[str, List[Tuple[int, int]]],
    special_set: Set[Tuple[int, int]],
) -> int:
    """Score a placement based on adjacency pairs and supercharged positions.

    Each adjacent pair of same-group techs = 1 point.
    Each tech on a supercharged slot = 3 bonus points.
    """
    score = 0
    all_positions: Dict[Tuple[int, int], str] = {}
    for group, pos_list in positions.items():
        for pos in pos_list:
            all_positions[pos] = group

    for pos, group in all_positions.items():
        for nx, ny in _neighbors(pos[0], pos[1]):
            if all_positions.get((nx, ny)) == group:
                score += 1  # counted twice (both directions) but consistent
        if pos in special_set:
            score += 3

    return score


def _normalize_item_id(item_id: str) -> str:
    return item_id.lstrip("^").split("#")[0]


def _find_catalogue_item(item_id: str, catalogue):
    if catalogue is None:
        return None
    item = catalogue.find_item(item_id)
    if item is not None:
        return item
    bare = item_id.lstrip("^")
    item = catalogue.find_item(bare)
    if item is not None:
        return item
    if "#" in bare:
        return catalogue.find_item(bare.split("#")[0])
    return None


def _tech_slots(inventory: dict) -> List[dict]:
    slots = inventory.get("Slots", [])
    return [
        s for s in slots
        if s.get("Type", {}).get("InventoryType") == "Technology" and s.get("Id")
    ]


def _special_set(inventory: dict) -> Set[Tuple[int, int]]:
    result: Set[Tuple[int, int]] = set()
    for s in inventory.get("SpecialSlots", []):
        if s.get("Type", {}).get("InventorySpecialSlotType") != "TechBonus":
            continue
        idx = s.get("Index", {})
        if "X" in idx and "Y" in idx:
            result.add((idx["X"], idx["Y"]))
    return result


def _layout_positions_by_group(inventory: dict, catalogue=None) -> Dict[str, List[Tuple[int, int]]]:
    by_group: Dict[str, List[Tuple[int, int]]] = defaultdict(list)
    for slot in _tech_slots(inventory):
        item_id = slot.get("Id", "")
        group = _get_tech_category(item_id, catalogue)
        idx = slot.get("Index", {})
        by_group[group].append((idx.get("X", 0), idx.get("Y", 0)))
    return by_group


def _module_rows(inventory: dict, catalogue=None) -> List[dict]:
    special = _special_set(inventory)
    rows = []
    for slot in _tech_slots(inventory):
        item_id = slot.get("Id", "")
        idx = slot.get("Index", {})
        x, y = idx.get("X", 0), idx.get("Y", 0)
        pos = (x, y)
        group = _get_tech_category(item_id, catalogue)

        adjacent_same = 0
        for nx, ny in _neighbors(x, y):
            nslot = next(
                (
                    s for s in _tech_slots(inventory)
                    if s.get("Index", {}).get("X") == nx and s.get("Index", {}).get("Y") == ny
                ),
                None,
            )
            if not nslot:
                continue
            n_group = _get_tech_category(nslot.get("Id", ""), catalogue)
            if n_group == group:
                adjacent_same += 1

        contribution = adjacent_same + (3 if pos in special else 0)
        rows.append({
            "id": item_id,
            "pos": pos,
            "group": group,
            "special": pos in special,
            "adjacent_same": adjacent_same,
            "contribution": contribution,
        })
    return rows


def _stat_totals(inventory: dict, catalogue=None) -> Dict[str, dict]:
    rows = _module_rows(inventory, catalogue)
    by_pos = {r["pos"]: r for r in rows}
    totals: Dict[str, dict] = {}

    for slot in _tech_slots(inventory):
        item_id = slot.get("Id", "")
        item = _find_catalogue_item(item_id, catalogue)
        if item is None:
            continue
        bonuses = item.get("stat_bonuses", []) or []
        idx = slot.get("Index", {})
        pos = (idx.get("X", 0), idx.get("Y", 0))
        row = by_pos.get(pos, {"adjacent_same": 0, "special": False})
        # Heuristic multiplier for display: adjacency + special slot impact.
        mult = 1.0 + (0.1 * row["adjacent_same"]) + (0.25 if row["special"] else 0.0)
        for b in bonuses:
            stat = b.get("stat", "")
            base = float(b.get("bonus", 0.0) or 0.0)
            if not stat:
                continue
            agg = totals.setdefault(stat, {"base": 0.0, "effective": 0.0, "confidence": "Estimated"})
            agg["base"] += base
            agg["effective"] += base * mult
    return totals


def analyze_tech_layout(inventory: dict, catalogue=None, mode: str = "balanced") -> dict:
    """Analyze current and optimized technology layout without mutating input."""
    current_inv = copy.deepcopy(inventory)
    optimized_inv = copy.deepcopy(inventory)
    optimize_tech_layout(optimized_inv, catalogue, mode=mode)

    current_groups = _layout_positions_by_group(current_inv, catalogue)
    optimized_groups = _layout_positions_by_group(optimized_inv, catalogue)
    current_special = _special_set(current_inv)
    optimized_special = _special_set(optimized_inv)

    current_score = _score_placement(current_groups, current_special)
    optimized_score = _score_placement(optimized_groups, optimized_special)

    current_stats = _stat_totals(current_inv, catalogue)
    optimized_stats = _stat_totals(optimized_inv, catalogue)
    all_stats = sorted(set(current_stats) | set(optimized_stats))
    stat_rows = []
    for stat in all_stats:
        c = current_stats.get(stat, {"effective": 0.0, "confidence": "Estimated"})
        o = optimized_stats.get(stat, {"effective": 0.0, "confidence": "Estimated"})
        stat_rows.append({
            "stat": stat,
            "current": c.get("effective", 0.0),
            "optimized": o.get("effective", 0.0),
            "delta": o.get("effective", 0.0) - c.get("effective", 0.0),
            "confidence": c.get("confidence", "Estimated"),
        })

    return {
        "current_score": current_score,
        "optimized_score": optimized_score,
        "delta_score": optimized_score - current_score,
        "module_rows": _module_rows(current_inv, catalogue),
        "stat_rows": stat_rows,
        "optimized_inventory": optimized_inv,
    }


def optimize_tech_layout(inventory: dict, catalogue=None, mode: str = "balanced") -> None:
    """Rearrange technology items in inventory for maximum adjacency bonuses.

    Modifies the inventory dict in-place. Non-tech items are not moved.
    """
    slots = inventory.get("Slots", [])
    valid_indices = inventory.get("ValidSlotIndices", [])
    valid_set = {(v["X"], v["Y"]) for v in valid_indices}
    special_slots = inventory.get("SpecialSlots", [])
    special_set = {(s["Index"]["X"], s["Index"]["Y"]) for s in special_slots}

    # Separate tech and non-tech slots
    tech_slots = []
    non_tech_positions: Set[Tuple[int, int]] = set()

    for slot in slots:
        inv_type = slot.get("Type", {}).get("InventoryType", "")
        item_id = slot.get("Id", "")
        pos = (slot["Index"]["X"], slot["Index"]["Y"])

        if inv_type == "Technology" and item_id:
            tech_slots.append(slot)
        elif item_id:
            non_tech_positions.add(pos)

    if not tech_slots:
        return

    # Group techs by category
    groups: Dict[str, List[dict]] = defaultdict(list)
    for slot in tech_slots:
        cat = _get_tech_category(slot["Id"], catalogue)
        groups[cat].append(slot)

    # Available positions: valid, not occupied by non-tech items
    available = sorted(valid_set - non_tech_positions)
    if len(available) < len(tech_slots):
        return  # Can't fit all techs, don't optimize

    # Greedy placement: place largest groups first, starting from supercharged slots
    # Sort groups by size (largest first)
    sorted_groups = sorted(
        groups.items(),
        key=lambda kv: (_group_priority(kv[0], kv[1], mode), len(kv[1])),
        reverse=True,
    )

    placed: Dict[str, List[Tuple[int, int]]] = {}
    used: Set[Tuple[int, int]] = set()

    for group_name, group_slots in sorted_groups:
        needed = len(group_slots)

        # Find best starting position: prefer supercharged slots
        best_cluster = None
        best_score = -1

        # Try each available position as start, expand via BFS for this group
        candidates = [p for p in available if p not in used]
        supercharged_candidates = [p for p in candidates if p in special_set]
        start_candidates = supercharged_candidates + candidates

        for start in start_candidates[:20]:  # Limit search for performance
            # BFS: expand from start to fill group_size positions
            cluster = _bfs_cluster(start, needed, available, used)
            if len(cluster) < needed:
                continue

            # Score this placement
            test_placement = dict(placed)
            test_placement[group_name] = cluster
            score = _score_placement(test_placement, special_set)

            if score > best_score:
                best_score = score
                best_cluster = cluster

        if best_cluster is None:
            # Fallback: take any available positions (may not be contiguous)
            fallback = [p for p in available if p not in used]
            if len(fallback) < needed:
                return  # Cannot place all techs safely — abort optimization
            best_cluster = fallback[:needed]

        # Assign positions to slots
        for i, slot in enumerate(group_slots):
            pos = best_cluster[i]
            slot["Index"]["X"] = pos[0]
            slot["Index"]["Y"] = pos[1]
            used.add(pos)
        placed[group_name] = best_cluster

    # Rebuild Slots list: non-tech slots unchanged, tech slots with new positions
    new_slots = []
    for slot in slots:
        inv_type = slot.get("Type", {}).get("InventoryType", "")
        item_id = slot.get("Id", "")
        if inv_type == "Technology" and item_id:
            continue  # Will be re-added with new positions
        new_slots.append(slot)

    new_slots.extend(tech_slots)
    inventory["Slots"] = new_slots


def _bfs_cluster(
    start: Tuple[int, int],
    size: int,
    available: list,
    used: Set[Tuple[int, int]],
) -> List[Tuple[int, int]]:
    """BFS expand from start position to find a connected cluster of given size."""
    available_set = set(available) - used
    if start not in available_set:
        return []

    cluster = [start]
    visited = {start}
    queue = [start]
    qi = 0

    while qi < len(queue) and len(cluster) < size:
        pos = queue[qi]
        qi += 1
        for nx, ny in _neighbors(pos[0], pos[1]):
            npos = (nx, ny)
            if npos in available_set and npos not in visited:
                visited.add(npos)
                cluster.append(npos)
                queue.append(npos)
                if len(cluster) >= size:
                    break

    return cluster[:size]
