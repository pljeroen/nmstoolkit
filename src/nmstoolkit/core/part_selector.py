"""Random part selection from a descriptor tree.

Pure domain module — stdlib only (random).

Walks a DescriptorGroup tree and selects one option per group using
weighted random selection. Returns the set of active node names.

Uses Python's random.Random() with time-based seeding — NOT seeded
with any NMS entity seed. This is a deliberate community decision:
the NMS modding community keeps the seed-to-parts mapping private
to protect the seed-hunting community. Open-source code must not
enable seed-to-parts computation.
"""

from __future__ import annotations

import random
from typing import FrozenSet

from nmstoolkit.core.mesh_data import DescriptorGroup, DescriptorOption


def select_parts(descriptor: DescriptorGroup) -> FrozenSet[str]:
    """Select a random valid part combination from a descriptor tree.

    Returns a frozenset of node names that should be active in the scene.
    """
    rng = random.Random()
    selected: set[str] = set()
    _walk(descriptor, rng, selected)
    return frozenset(selected)


def _walk(group: DescriptorGroup, rng: random.Random, selected: set[str]) -> None:
    """Recursively walk the descriptor tree, selecting one option per group.

    When all options have empty ids (synthetic root wrapping independent
    groups), walk ALL options — they represent independent part slots,
    not alternatives to pick from.
    """
    if not group.options:
        return

    all_empty = all(opt.id == "" for opt in group.options)
    if all_empty:
        # Synthetic root: each option wraps an independent group
        for opt in group.options:
            for child_group in opt.children:
                _walk(child_group, rng, selected)
        return

    weights = [opt.chance if opt.chance > 0 else 1.0 for opt in group.options]
    chosen = rng.choices(group.options, weights=weights, k=1)[0]
    selected.add(chosen.id)

    for child_group in chosen.children:
        _walk(child_group, rng, selected)
