"""Extended icon provider tests — base tech map, corvette DDS, fossil DDS resolution.

Tests R-IPROV-04 through R-IPROV-06:
  R-IPROV-04: Base building tech static icon map
  R-IPROV-05: Corvette module DDS path construction
  R-IPROV-06: Fossil part DDS path construction
"""

from unittest.mock import MagicMock

import pytest

from nmstoolkit.gui.widgets.icon_provider import IconProvider


def _make_catalogue_with_items(items_by_id):
    """Create a mock catalogue that stores items by bare ID (no caret)."""
    catalogue = MagicMock()

    def find_item(item_id):
        return items_by_id.get(item_id)

    catalogue.find_item.side_effect = find_item
    return catalogue


# ---------------------------------------------------------------------------
# R-IPROV-04: Base building tech static icon map
# ---------------------------------------------------------------------------

class TestBaseTechIconMap:
    """R-IPROV-04: Base building techs not in catalogue resolve via static map."""

    def test_cooker_resolves_without_catalogue(self):
        """COOKER → BUILDABLE.COOKER.DDS via static map, no catalogue needed."""
        provider = IconProvider(icon_cache=None, catalogue=None)
        result = provider.get_icon_path("COOKER")
        assert result == "TEXTURES/UI/FRONTEND/ICONS/BUILDABLE/BUILDABLE.COOKER.DDS"

    def test_caret_cooker_resolves(self):
        """^COOKER also resolves via static map."""
        provider = IconProvider(icon_cache=None, catalogue=None)
        result = provider.get_icon_path("^COOKER")
        assert result == "TEXTURES/UI/FRONTEND/ICONS/BUILDABLE/BUILDABLE.COOKER.DDS"

    def test_buildsignal_resolves(self):
        """BUILDSIGNAL → BUILDABLE.SIGNAL.DDS."""
        provider = IconProvider(icon_cache=None, catalogue=None)
        result = provider.get_icon_path("BUILDSIGNAL")
        assert result == "TEXTURES/UI/FRONTEND/ICONS/BUILDABLE/BUILDABLE.SIGNAL.DDS"

    def test_refiner1_resolves(self):
        """BUILD_REFINER1 → BUILDABLE.REFINER1.DDS."""
        provider = IconProvider(icon_cache=None, catalogue=None)
        result = provider.get_icon_path("BUILD_REFINER1")
        assert result == "TEXTURES/UI/FRONTEND/ICONS/BUILDABLE/BUILDABLE.REFINER1.DDS"

    def test_refiner2_resolves(self):
        """BUILD_REFINER2 → BUILDABLE.REFINER2.DDS."""
        provider = IconProvider(icon_cache=None, catalogue=None)
        result = provider.get_icon_path("BUILD_REFINER2")
        assert result == "TEXTURES/UI/FRONTEND/ICONS/BUILDABLE/BUILDABLE.REFINER2.DDS"

    def test_refiner3_resolves(self):
        """BUILD_REFINER3 → BUILDABLE.REFINER3.DDS."""
        provider = IconProvider(icon_cache=None, catalogue=None)
        result = provider.get_icon_path("BUILD_REFINER3")
        assert result == "TEXTURES/UI/FRONTEND/ICONS/BUILDABLE/BUILDABLE.REFINER3.DDS"

    def test_savepoint_resolves(self):
        """BUILDSAVE → BUILDABLE.SAVEPOINT.DDS."""
        provider = IconProvider(icon_cache=None, catalogue=None)
        result = provider.get_icon_path("BUILDSAVE")
        assert result == "TEXTURES/UI/FRONTEND/ICONS/BUILDABLE/BUILDABLE.SAVEPOINT.DDS"

    def test_beamstone_resolves(self):
        """BASE_BEAMSTONE → BUILDABLE.BEAMSTONE.DDS."""
        provider = IconProvider(icon_cache=None, catalogue=None)
        result = provider.get_icon_path("BASE_BEAMSTONE")
        assert result == "TEXTURES/UI/FRONTEND/ICONS/BUILDABLE/BUILDABLE.BEAMSTONE.DDS"

    def test_caret_beamstone_resolves(self):
        """^BASE_BEAMSTONE also resolves via static map."""
        provider = IconProvider(icon_cache=None, catalogue=None)
        result = provider.get_icon_path("^BASE_BEAMSTONE")
        assert result == "TEXTURES/UI/FRONTEND/ICONS/BUILDABLE/BUILDABLE.BEAMSTONE.DDS"

    def test_bubblecluster_resolves(self):
        """BASE_BUBBLECLUS → BUILDABLE.BUBBLECLUSTER.DDS."""
        provider = IconProvider(icon_cache=None, catalogue=None)
        result = provider.get_icon_path("BASE_BUBBLECLUS")
        assert result == "TEXTURES/UI/FRONTEND/ICONS/BUILDABLE/BUILDABLE.BUBBLECLUSTER.DDS"

    def test_glitch_separator_resolves(self):
        """YOURGLITCHSEP → BUILDGROUP.GLITCH.DDS."""
        provider = IconProvider(icon_cache=None, catalogue=None)
        result = provider.get_icon_path("YOURGLITCHSEP")
        assert result == "TEXTURES/UI/FRONTEND/ICONS/BUILDABLE/GROUPS/BUILDGROUP.GLITCH.DDS"

    def test_weirdcube_resolves(self):
        """BASE_WEIRDCUBE (Electric Cube) → BUILDABLE.WEIRDCUBE.DDS."""
        provider = IconProvider(icon_cache=None, catalogue=None)
        result = provider.get_icon_path("BASE_WEIRDCUBE")
        assert result == "TEXTURES/UI/FRONTEND/ICONS/BUILDABLE/BUILDABLE.WEIRDCUBE.DDS"

    def test_proc_loot_resolves(self):
        """PROC_LOOT (Unearthed Treasure) → curiosity icon."""
        provider = IconProvider(icon_cache=None, catalogue=None)
        result = provider.get_icon_path("PROC_LOOT")
        assert result == "TEXTURES/UI/FRONTEND/ICONS/PRODUCTS/PRODUCT.CURIO.1.DDS"

    def test_proc_bio_resolves(self):
        """PROC_BIO (Biological Sample) → curiosity icon."""
        provider = IconProvider(icon_cache=None, catalogue=None)
        result = provider.get_icon_path("PROC_BIO")
        assert result == "TEXTURES/UI/FRONTEND/ICONS/PRODUCTS/PRODUCT.CURIO.1.DDS"

    def test_proc_plnt_resolves(self):
        """PROC_PLNT (Delicate Flora) → plantpot icon."""
        provider = IconProvider(icon_cache=None, catalogue=None)
        result = provider.get_icon_path("PROC_PLNT")
        assert result == "TEXTURES/UI/FRONTEND/ICONS/BUILDABLE/DECORATION.PLANTPOT3.DDS"

    def test_proc_tool_resolves(self):
        """PROC_TOOL (Lost Artifact) → curiosity icon."""
        provider = IconProvider(icon_cache=None, catalogue=None)
        result = provider.get_icon_path("PROC_TOOL")
        assert result == "TEXTURES/UI/FRONTEND/ICONS/PRODUCTS/PRODUCT.CURIO.1.DDS"

    def test_proc_capt_resolves(self):
        """PROC_CAPT (Official Record) → curiosity icon."""
        provider = IconProvider(icon_cache=None, catalogue=None)
        result = provider.get_icon_path("PROC_CAPT")
        assert result == "TEXTURES/UI/FRONTEND/ICONS/PRODUCTS/PRODUCT.CURIO.1.DDS"

    def test_proc_crew_resolves(self):
        """PROC_CREW (Official Record) → curiosity icon."""
        provider = IconProvider(icon_cache=None, catalogue=None)
        result = provider.get_icon_path("PROC_CREW")
        assert result == "TEXTURES/UI/FRONTEND/ICONS/PRODUCTS/PRODUCT.CURIO.1.DDS"

    def test_caret_proc_loot_resolves(self):
        """^PROC_LOOT also resolves."""
        provider = IconProvider(icon_cache=None, catalogue=None)
        result = provider.get_icon_path("^PROC_LOOT")
        assert result == "TEXTURES/UI/FRONTEND/ICONS/PRODUCTS/PRODUCT.CURIO.1.DDS"

    def test_static_map_takes_priority_over_catalogue(self):
        """Static map wins over catalogue (verified DDS paths override catalogue)."""
        cat = _make_catalogue_with_items({
            "COOKER": {"id": "COOKER", "icon": "TEXTURES/FROM_CATALOGUE.DDS"},
        })
        provider = IconProvider(icon_cache=None, catalogue=cat)
        result = provider.get_icon_path("COOKER")
        assert result == "TEXTURES/UI/FRONTEND/ICONS/BUILDABLE/BUILDABLE.COOKER.DDS"

    def test_static_map_takes_priority_over_icon_map(self):
        """Static map wins over icon_map (overrides bad items.json values)."""
        provider = IconProvider(
            icon_cache=None, catalogue=None,
            icon_map={"COOKER": "PRODUCT-COOKER.PNG"},
        )
        result = provider.get_icon_path("COOKER")
        assert result == "TEXTURES/UI/FRONTEND/ICONS/BUILDABLE/BUILDABLE.COOKER.DDS"


# ---------------------------------------------------------------------------
# R-IPROV-05: Corvette module DDS path construction
# ---------------------------------------------------------------------------

class TestCorvetteModuleDDSConstruction:
    """R-IPROV-05: Corvette modules resolve to per-variant DDS paths directly."""

    def test_cockpit_a(self):
        """B_COK_A → BIGGS_BIG_COK1X2_A.DDS."""
        provider = IconProvider(icon_cache=None, catalogue=None)
        result = provider.get_icon_path("B_COK_A")
        assert result == "TEXTURES/UI/FRONTEND/ICONS/BUILDABLE/BIGGS_BIG_COK1X2_A.DDS"

    def test_cockpit_b(self):
        """B_COK_B → BIGGS_BIG_COK1X2_B.DDS."""
        provider = IconProvider(icon_cache=None, catalogue=None)
        result = provider.get_icon_path("B_COK_B")
        assert result == "TEXTURES/UI/FRONTEND/ICONS/BUILDABLE/BIGGS_BIG_COK1X2_B.DDS"

    def test_hab_a(self):
        """B_HAB_A → BIGGS_BIG_HAB1X1_A.DDS."""
        provider = IconProvider(icon_cache=None, catalogue=None)
        result = provider.get_icon_path("B_HAB_A")
        assert result == "TEXTURES/UI/FRONTEND/ICONS/BUILDABLE/BIGGS_BIG_HAB1X1_A.DDS"

    def test_hab1_a(self):
        """B_HAB1_A → BIGGS_BIG_HAB1X2_A.DDS (longer prefix match)."""
        provider = IconProvider(icon_cache=None, catalogue=None)
        result = provider.get_icon_path("B_HAB1_A")
        assert result == "TEXTURES/UI/FRONTEND/ICONS/BUILDABLE/BIGGS_BIG_HAB1X2_A.DDS"

    def test_wing_b(self):
        """B_WNG_B → BIGGS_BIG_WNG1X2_B.DDS."""
        provider = IconProvider(icon_cache=None, catalogue=None)
        result = provider.get_icon_path("B_WNG_B")
        assert result == "TEXTURES/UI/FRONTEND/ICONS/BUILDABLE/BIGGS_BIG_WNG1X2_B.DDS"

    def test_thruster_a(self):
        """B_TRU_A → BIGGS_BIG_TRU1X1_A.DDS."""
        provider = IconProvider(icon_cache=None, catalogue=None)
        result = provider.get_icon_path("B_TRU_A")
        assert result == "TEXTURES/UI/FRONTEND/ICONS/BUILDABLE/BIGGS_BIG_TRU1X1_A.DDS"

    def test_turret_a(self):
        """B_TUR_A → BIGGS_BIG_TUR1X1_A.DDS."""
        provider = IconProvider(icon_cache=None, catalogue=None)
        result = provider.get_icon_path("B_TUR_A")
        assert result == "TEXTURES/UI/FRONTEND/ICONS/BUILDABLE/BIGGS_BIG_TUR1X1_A.DDS"

    def test_shell_a(self):
        """B_SHL_A → BIGGS_BIG_SHL1X1_A.DDS."""
        provider = IconProvider(icon_cache=None, catalogue=None)
        result = provider.get_icon_path("B_SHL_A")
        assert result == "TEXTURES/UI/FRONTEND/ICONS/BUILDABLE/BIGGS_BIG_SHL1X1_A.DDS"

    def test_generator_a(self):
        """B_GEN_A → BIGGS_BIG_GEN1X1_A.DDS."""
        provider = IconProvider(icon_cache=None, catalogue=None)
        result = provider.get_icon_path("B_GEN_A")
        assert result == "TEXTURES/UI/FRONTEND/ICONS/BUILDABLE/BIGGS_BIG_GEN1X1_A.DDS"

    def test_connector_a(self):
        """B_CON_A → BIGGS_BIG_CON1X1_A.DDS."""
        provider = IconProvider(icon_cache=None, catalogue=None)
        result = provider.get_icon_path("B_CON_A")
        assert result == "TEXTURES/UI/FRONTEND/ICONS/BUILDABLE/BIGGS_BIG_CON1X1_A.DDS"

    def test_caret_cockpit_a(self):
        """^B_COK_A also resolves to DDS path."""
        provider = IconProvider(icon_cache=None, catalogue=None)
        result = provider.get_icon_path("^B_COK_A")
        assert result == "TEXTURES/UI/FRONTEND/ICONS/BUILDABLE/BIGGS_BIG_COK1X2_A.DDS"

    def test_deco_a(self):
        """B_DECO_A → BIGGS_BIG_DECO1X1_A.DDS."""
        provider = IconProvider(icon_cache=None, catalogue=None)
        result = provider.get_icon_path("B_DECO_A")
        assert result == "TEXTURES/UI/FRONTEND/ICONS/BUILDABLE/BIGGS_BIG_DECO1X1_A.DDS"

    def test_landing_a(self):
        """B_LND_A → BIGGS_BIG_LND1X1_A.DDS."""
        provider = IconProvider(icon_cache=None, catalogue=None)
        result = provider.get_icon_path("B_LND_A")
        assert result == "TEXTURES/UI/FRONTEND/ICONS/BUILDABLE/BIGGS_BIG_LND1X1_A.DDS"

    def test_airlock_a(self):
        """B_ALK_A → BIGGS_BIG_ALK1X1_A.DDS."""
        provider = IconProvider(icon_cache=None, catalogue=None)
        result = provider.get_icon_path("B_ALK_A")
        assert result == "TEXTURES/UI/FRONTEND/ICONS/BUILDABLE/BIGGS_BIG_ALK1X1_A.DDS"

    def test_structure_a(self):
        """B_STR_A → BIGGS_BIG_STR1X1_A.DDS."""
        provider = IconProvider(icon_cache=None, catalogue=None)
        result = provider.get_icon_path("B_STR_A")
        assert result == "TEXTURES/UI/FRONTEND/ICONS/BUILDABLE/BIGGS_BIG_STR1X1_A.DDS"

    def test_btru_a(self):
        """B_BTRU_A → BIGGS_BIG_BTRU1X1_A.DDS."""
        provider = IconProvider(icon_cache=None, catalogue=None)
        result = provider.get_icon_path("B_BTRU_A")
        assert result == "TEXTURES/UI/FRONTEND/ICONS/BUILDABLE/BIGGS_BIG_BTRU1X1_A.DDS"

    def test_con2_a(self):
        """B_CON2_A → BIGGS_BIG_CON2_A.DDS."""
        provider = IconProvider(icon_cache=None, catalogue=None)
        result = provider.get_icon_path("B_CON2_A")
        assert result == "TEXTURES/UI/FRONTEND/ICONS/BUILDABLE/BIGGS_BIG_CON2_A.DDS"

    def test_con_l_a(self):
        """B_CON_L_A → uses CON_L prefix → CON1X1."""
        provider = IconProvider(icon_cache=None, catalogue=None)
        result = provider.get_icon_path("B_CON_L_A")
        assert result == "TEXTURES/UI/FRONTEND/ICONS/BUILDABLE/BIGGS_BIG_CON1X1_A.DDS"


# ---------------------------------------------------------------------------
# R-IPROV-06: Fossil part DDS path construction
# ---------------------------------------------------------------------------

class TestFossilIconResolution:
    """R-IPROV-06: Fossil item IDs resolve to DDS paths via naming pattern."""

    def test_biped_body_ac(self):
        """FOS_BI_BODY_AC → FOSSIL.BIPED.BODY.AC.DDS."""
        provider = IconProvider(icon_cache=None, catalogue=None)
        result = provider.get_icon_path("FOS_BI_BODY_AC")
        assert result == "TEXTURES/UI/FRONTEND/ICONS/FOSSILBONES/FOSSIL.BIPED.BODY.AC.DDS"

    def test_quadruped_head_ab(self):
        """FOS_QUAD_HEAD_AB → FOSSIL.QUADRUPED.HEAD.AB.DDS."""
        provider = IconProvider(icon_cache=None, catalogue=None)
        result = provider.get_icon_path("FOS_QUAD_HEAD_AB")
        assert result == "TEXTURES/UI/FRONTEND/ICONS/FOSSILBONES/FOSSIL.QUADRUPED.HEAD.AB.DDS"

    def test_worm_tail_aa(self):
        """FOS_WORM_TAIL_AA → FOSSIL.WORM.TAIL.AA.DDS."""
        provider = IconProvider(icon_cache=None, catalogue=None)
        result = provider.get_icon_path("FOS_WORM_TAIL_AA")
        assert result == "TEXTURES/UI/FRONTEND/ICONS/FOSSILBONES/FOSSIL.WORM.TAIL.AA.DDS"

    def test_bird_skull_ba(self):
        """FOS_BIRD_SKULL_BA → FOSSIL.BIRD.SKULL.BA.DDS."""
        provider = IconProvider(icon_cache=None, catalogue=None)
        result = provider.get_icon_path("FOS_BIRD_SKULL_BA")
        assert result == "TEXTURES/UI/FRONTEND/ICONS/FOSSILBONES/FOSSIL.BIRD.SKULL.BA.DDS"

    def test_grunt_spine_ac(self):
        """FOS_GRUN_SPINE_AC → FOSSIL.GRUNT.SPINE.AC.DDS."""
        provider = IconProvider(icon_cache=None, catalogue=None)
        result = provider.get_icon_path("FOS_GRUN_SPINE_AC")
        assert result == "TEXTURES/UI/FRONTEND/ICONS/FOSSILBONES/FOSSIL.GRUNT.SPINE.AC.DDS"

    def test_caret_fossil(self):
        """^FOS_BI_BODY_AC also resolves."""
        provider = IconProvider(icon_cache=None, catalogue=None)
        result = provider.get_icon_path("^FOS_BI_BODY_AC")
        assert result == "TEXTURES/UI/FRONTEND/ICONS/FOSSILBONES/FOSSIL.BIPED.BODY.AC.DDS"

    def test_proc_foss_generic(self):
        """PROC_FOSS → generic fossil display icon."""
        provider = IconProvider(icon_cache=None, catalogue=None)
        result = provider.get_icon_path("PROC_FOSS")
        assert result == "TEXTURES/UI/FRONTEND/ICONS/FOSSILBONES/FOSSIL.DISP.DDS"

    def test_proc_foss_procedural(self):
        """PROC_FOSS#11125 → same generic fossil icon (strip #suffix)."""
        provider = IconProvider(icon_cache=None, catalogue=None)
        result = provider.get_icon_path("PROC_FOSS#11125")
        assert result == "TEXTURES/UI/FRONTEND/ICONS/FOSSILBONES/FOSSIL.DISP.DDS"

    def test_fossil_no_variant(self):
        """FOS_BI_BODY (no variant) → FOSSIL.BIPED.BODY.DDS."""
        provider = IconProvider(icon_cache=None, catalogue=None)
        result = provider.get_icon_path("FOS_BI_BODY")
        assert result == "TEXTURES/UI/FRONTEND/ICONS/FOSSILBONES/FOSSIL.BIPED.BODY.DDS"


# ---------------------------------------------------------------------------
# R-IPROV-07: Fossil display names in inventory grid
# ---------------------------------------------------------------------------

class TestFossilDisplayNames:
    """R-IPROV-07: Fossil IDs show friendly names via fossils_tab functions."""

    def test_friendly_fossil_name_public(self):
        """friendly_fossil_name is importable as public API."""
        from nmstoolkit.gui.tabs.fossils_tab import friendly_fossil_name
        result = friendly_fossil_name("FOS_BI_BODY_AC")
        assert result == "Biped Body (AC)"

    def test_friendly_fossil_name_proc(self):
        """Procedural fossil gets friendly name."""
        from nmstoolkit.gui.tabs.fossils_tab import friendly_fossil_name
        result = friendly_fossil_name("PROC_FOSS#11125")
        assert result == "Fossil Sample #11125"

    def test_friendly_fossil_name_skull(self):
        from nmstoolkit.gui.tabs.fossils_tab import friendly_fossil_name
        result = friendly_fossil_name("BLD_SKULL")
        assert result == "Titanic Trophy"
