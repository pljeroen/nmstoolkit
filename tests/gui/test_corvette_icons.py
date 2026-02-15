"""Tests for corvette module icon resolution.

R-ICON-02: Corvette modules (B_COK, B_HAB, B_WNG etc.) resolve to icon paths.
"""

import pytest

from nmstoolkit.gui.widgets.icon_provider import IconProvider, _CORVETTE_MODULE_MAP


class TestCorvetteModuleIconMap:
    def test_corvette_module_map_has_expected_prefixes(self):
        """The corvette module map should cover key module types."""
        expected = ["B_COK", "B_HAB", "B_WNG", "B_STR", "B_TRU", "B_TUR", "B_LND"]
        for prefix in expected:
            assert any(
                key.startswith(prefix) for key in _CORVETTE_MODULE_MAP
            ), f"Missing mapping for {prefix}"


class TestCorvetteModuleIconResolution:
    def test_corvette_module_resolves_via_icon_map(self):
        """B_COK_A should resolve to an icon path through the corvette module map."""
        icon_map = {}
        # Add the mapped target to icon_map so it resolves
        for module_id, target_id in _CORVETTE_MODULE_MAP.items():
            icon_map[target_id] = f"TEXTURES/{target_id}.DDS"

        provider = IconProvider(icon_cache=None, catalogue=None, icon_map=icon_map)
        result = provider.get_icon_path("^B_COK_A")
        assert result != "", "B_COK_A should resolve to an icon path"

    def test_non_corvette_module_unaffected(self):
        """Regular items should not be affected by corvette module resolution."""
        provider = IconProvider(icon_cache=None, catalogue=None, icon_map={"FUEL1": "TEXTURES/FUEL1.DDS"})
        result = provider.get_icon_path("FUEL1")
        assert result == "TEXTURES/FUEL1.DDS"
