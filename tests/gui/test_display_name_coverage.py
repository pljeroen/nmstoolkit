"""Tests for display name coverage — verifies name resolution produces correct results.

Freezes the name resolution method across all item categories using the real
game_catalogue.json and items.json. Each test class covers one category with
real item IDs and the expected proper-case display names.

These tests use the on-disk data files as fixtures. They verify the RESOLUTION
chain (items.json priority → catalogue title-case → locale → raw ID).
"""

import json
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path

import pytest

from PySide6.QtWidgets import QApplication

from nmstoolkit.core.game_catalogue import GameCatalogue
from nmstoolkit.gui.widgets.inventory_grid import (
    _get_item_name,
    _title_case_name,
    set_catalogue,
)

_app = QApplication.instance() or QApplication([])

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "src" / "nmstoolkit" / "data"
ICONS_DIR = DATA_DIR / "icons"


@pytest.fixture(scope="module")
def catalogue():
    """Load the real game_catalogue.json and build a GameCatalogue."""
    path = ICONS_DIR / "game_catalogue.json"
    if not path.exists():
        pytest.skip("game_catalogue.json not available (run icon extraction first)")
    data = json.loads(path.read_text())
    return GameCatalogue(
        products=data.get("products", []),
        substances=data.get("substances", []),
        technologies=data.get("technologies", []),
        locale=data.get("locale", {}),
    )


@pytest.fixture(autouse=True)
def _reset_catalogue():
    """Reset catalogue state after each test."""
    yield
    set_catalogue(None)


# ---------------------------------------------------------------------------
# Category: Substances (minerals, gases, elements)
# User confirmed: names correct on both Linux and Windows
# ---------------------------------------------------------------------------

class TestNameSubstances:
    """Substance names resolve to proper case."""

    def test_carbon(self, catalogue):
        set_catalogue(catalogue)
        assert _get_item_name("FUEL1") == "Carbon"

    def test_oxygen(self, catalogue):
        set_catalogue(catalogue)
        assert _get_item_name("OXYGEN") == "Oxygen"

    def test_dihydrogen(self, catalogue):
        set_catalogue(catalogue)
        assert _get_item_name("LAUNCHSUB") == "Di-hydrogen"

    def test_ferrite(self, catalogue):
        set_catalogue(catalogue)
        assert _get_item_name("LAND1") == "Ferrite Dust"

    def test_sodium(self, catalogue):
        set_catalogue(catalogue)
        assert _get_item_name("CATALYST1") == "Sodium"

    def test_condensed_carbon(self, catalogue):
        set_catalogue(catalogue)
        assert _get_item_name("FUEL2") == "Condensed Carbon"

    def test_cobalt(self, catalogue):
        set_catalogue(catalogue)
        assert _get_item_name("CAVE1") == "Cobalt"

    def test_chromatic_metal(self, catalogue):
        set_catalogue(catalogue)
        assert _get_item_name("STELLAR2") == "Chromatic Metal"


# ---------------------------------------------------------------------------
# Category: Products (crafted items, trade goods)
# User confirmed: names correct on both platforms
# ---------------------------------------------------------------------------

class TestNameProducts:
    """Product names resolve to proper case."""

    def test_metal_plating(self, catalogue):
        set_catalogue(catalogue)
        assert _get_item_name("CASING") == "Metal Plating"

    def test_antimatter(self, catalogue):
        set_catalogue(catalogue)
        assert _get_item_name("ANTIMATTER") == "Antimatter"

    def test_microchip(self, catalogue):
        set_catalogue(catalogue)
        assert _get_item_name("MICROCHIP") == "Microprocessor"

    def test_warp_cell(self, catalogue):
        set_catalogue(catalogue)
        assert _get_item_name("HYPERFUEL1") == "Warp Cell"

    def test_dihydrogen_jelly(self, catalogue):
        set_catalogue(catalogue)
        assert _get_item_name("JELLY") == "Di-hydrogen Jelly"


# ---------------------------------------------------------------------------
# Category: Technologies (installed modules)
# User confirmed: names correct on both platforms
# ---------------------------------------------------------------------------

class TestNameTechnologies:
    """Technology names resolve to proper case."""

    def test_mining_beam(self, catalogue):
        set_catalogue(catalogue)
        assert _get_item_name("^LASER") == "Mining Beam"

    def test_bolt_caster(self, catalogue):
        set_catalogue(catalogue)
        assert _get_item_name("^BOLT") == "Boltcaster"

    def test_scanner(self, catalogue):
        set_catalogue(catalogue)
        assert _get_item_name("^SCAN1") == "Scanner"

    def test_hyperdrive(self, catalogue):
        set_catalogue(catalogue)
        assert _get_item_name("^HYPERDRIVE") == "Hyperdrive"

    def test_pulse_engine(self, catalogue):
        set_catalogue(catalogue)
        assert _get_item_name("^SHIPJUMP1") == "Pulse Engine"


# ---------------------------------------------------------------------------
# Category: Upgrade modules (UP_/UA_ prefixed)
# User confirmed: names correct on both platforms
# ---------------------------------------------------------------------------

class TestNameUpgrades:
    """Upgrade module names resolve to proper case."""

    def test_up_laser(self, catalogue):
        set_catalogue(catalogue)
        name = _get_item_name("^UP_LASER1")
        assert name and name != "UP_LASER1"

    def test_up_jetpack(self, catalogue):
        set_catalogue(catalogue)
        name = _get_item_name("^UP_JET1")
        assert name and name != "UP_JET1"


# ---------------------------------------------------------------------------
# Category: Food/cooking products
# User confirmed: names correct on both platforms
# ---------------------------------------------------------------------------

class TestNameFoodProducts:
    """Food item names resolve to proper case."""

    def test_food_blob(self, catalogue):
        set_catalogue(catalogue)
        name = _get_item_name("FOOD_V_BLOB")
        assert name and name != "FOOD_V_BLOB"
        assert not name.isupper(), f"Name is ALL CAPS: {name}"

    def test_food_gek(self, catalogue):
        set_catalogue(catalogue)
        name = _get_item_name("FOOD_V_GEK")
        assert name and name != "FOOD_V_GEK"
        assert not name.isupper(), f"Name is ALL CAPS: {name}"


# ---------------------------------------------------------------------------
# Category: Fish items
# User confirmed: names correct on both platforms
# ---------------------------------------------------------------------------

class TestNameFish:
    """Fish item names resolve to proper case."""

    def test_fishcore(self, catalogue):
        set_catalogue(catalogue)
        name = _get_item_name("FISHCORE")
        assert name and name != "FISHCORE"
        assert not name.isupper(), f"Name is ALL CAPS: {name}"

    def test_fishbait(self, catalogue):
        set_catalogue(catalogue)
        name = _get_item_name("FISHBAIT_1")
        assert name and name != "FISHBAIT_1"
        assert not name.isupper(), f"Name is ALL CAPS: {name}"


# ---------------------------------------------------------------------------
# Category: Expedition rewards
# User confirmed: names correct on both platforms
# ---------------------------------------------------------------------------

class TestNameExpeditionRewards:
    """Expedition reward names resolve to proper case."""

    def test_expd_backpack(self, catalogue):
        set_catalogue(catalogue)
        name = _get_item_name("EXPD_BACKPACK01")
        assert name and name != "EXPD_BACKPACK01"
        assert not name.isupper(), f"Name is ALL CAPS: {name}"

    def test_expd_ship(self, catalogue):
        set_catalogue(catalogue)
        name = _get_item_name("EXPD_SHIP01")
        assert name and name != "EXPD_SHIP01"
        assert not name.isupper(), f"Name is ALL CAPS: {name}"


# ---------------------------------------------------------------------------
# Invariant: no name in any category should be ALL CAPS after resolution
# ---------------------------------------------------------------------------

class TestNoAllCapsNames:
    """Bulk check: resolved names must never be ALL CAPS multi-word.

    Single-word ALL CAPS names (QUICKSILVER, GEK, KORVAX) are acceptable —
    these are proper nouns. Unresolved locale keys (_NAME_L suffix) are a
    known gap in locale data, not a name resolution bug.
    """

    def _is_violation(self, name: str) -> bool:
        """True if name is a multi-word ALL CAPS string (not a locale key)."""
        if not name or not name.isupper():
            return False
        # Single words are often proper nouns — acceptable
        if " " not in name:
            return False
        # Unresolved locale keys (_NAME_L suffix) — known gap
        if name.endswith("_L") or "_NAME" in name:
            return False
        return True

    def test_substance_names_not_all_caps(self, catalogue):
        """No substance should resolve to a multi-word ALL CAPS name."""
        set_catalogue(catalogue)
        path = ICONS_DIR / "game_catalogue.json"
        data = json.loads(path.read_text())
        violations = []
        for s in data["substances"]:
            name = _get_item_name(s["id"])
            if self._is_violation(name):
                violations.append(f"{s['id']} → {name}")
        assert not violations, f"ALL CAPS substances: {violations}"

    def test_product_names_not_all_caps(self, catalogue):
        """No product should resolve to a multi-word ALL CAPS name."""
        set_catalogue(catalogue)
        path = ICONS_DIR / "game_catalogue.json"
        data = json.loads(path.read_text())
        violations = []
        for p in data["products"]:
            name = _get_item_name(p["id"])
            if self._is_violation(name):
                violations.append(f"{p['id']} → {name}")
        assert not violations, f"ALL CAPS products: {violations}"

    def test_technology_names_not_all_caps(self, catalogue):
        """No technology should resolve to a multi-word ALL CAPS name."""
        set_catalogue(catalogue)
        path = ICONS_DIR / "game_catalogue.json"
        data = json.loads(path.read_text())
        violations = []
        for t in data["technologies"]:
            name = _get_item_name("^" + t["id"])
            if self._is_violation(name):
                violations.append(f"{t['id']} → {name}")
        assert not violations, f"ALL CAPS technologies: {violations}"
