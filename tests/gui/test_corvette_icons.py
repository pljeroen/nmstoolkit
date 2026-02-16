"""Tests for corvette module icon resolution.

R-ICON-02: Corvette modules (B_COK, B_HAB, B_WNG etc.) resolve to icon paths.
"""

import pytest

from nmstoolkit.gui.widgets.icon_provider import IconProvider, _CORVETTE_ICON_PREFIX


class TestCorvetteModuleIconMap:
    def test_corvette_icon_prefix_has_expected_types(self):
        """The corvette icon prefix map should cover key module types."""
        expected = ["COK", "HAB", "WNG", "STR", "TRU", "TUR", "LND"]
        for type_key in expected:
            assert type_key in _CORVETTE_ICON_PREFIX, f"Missing mapping for {type_key}"


class TestCorvetteModuleIconResolution:
    def test_corvette_module_resolves_directly(self):
        """B_COK_A should resolve to a DDS path directly."""
        provider = IconProvider(icon_cache=None, catalogue=None)
        result = provider.get_icon_path("^B_COK_A")
        assert result != "", "B_COK_A should resolve to an icon path"
        assert "BIGGS_BIG_COK1X2_A" in result

    def test_non_corvette_module_unaffected(self):
        """Regular items should not be affected by corvette module resolution."""
        provider = IconProvider(icon_cache=None, catalogue=None, icon_map={"FUEL1": "TEXTURES/FUEL1.DDS"})
        result = provider.get_icon_path("FUEL1")
        assert result == "TEXTURES/FUEL1.DDS"
