"""Game data extraction pipeline.

Orchestrates: PAK extraction → MBIN conversion → EXML parsing → GameCatalogue.

This is an application service, not pure domain. It coordinates adapters
through ports to produce a domain object (GameCatalogue).
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Union

from nmstoolkit.adapters.hgpak_adapter import HgpakAdapter
from nmstoolkit.adapters.mbin_compiler_adapter import MbinCompilerAdapter
from nmstoolkit.core.exml_parser import (
    parse_locale_table,
    parse_product_table,
    parse_recipe_table,
    parse_season_table,
    parse_substance_table,
    parse_technology_table,
    resolve_locale,
)
from nmstoolkit.core.game_catalogue import GameCatalogue


# PAK files and the MBIN paths we need from each
_PRECACHE_TARGETS = [
    "metadata/reality/tables/nms_reality_gcproducttable.mbin",
    "metadata/reality/tables/nms_reality_gcsubstancetable.mbin",
    "metadata/reality/tables/nms_reality_gctechnologytable.mbin",
    "metadata/reality/tables/nms_reality_gcrecipetable.mbin",
    "metadata/reality/tables/historicalseasondatatable.mbin",
]

# Language files are split across multiple loc files
_LANGUAGE_PREFIXES = [
    "language/nms_loc1_english.mbin",
    "language/nms_loc4_english.mbin",
    "language/nms_loc5_english.mbin",
    "language/nms_loc6_english.mbin",
    "language/nms_loc7_english.mbin",
    "language/nms_loc8_english.mbin",
    "language/nms_loc9_english.mbin",
    "language/nms_update3_english.mbin",
]


def build_catalogue(
    pak_dir: Union[str, Path],
    mbin_compiler: Union[str, Path],
) -> GameCatalogue:
    """Build a GameCatalogue from NMS game files.

    Args:
        pak_dir: Path to PCBANKS directory containing .pak files.
        mbin_compiler: Path to MBINCompiler binary.

    Returns:
        GameCatalogue with products, substances, technologies, and locale.
    """
    pak_dir = Path(pak_dir)
    converter = MbinCompilerAdapter(mbin_compiler)

    # Extract table MBINs from Precache.pak
    table_mbins = _extract_from_pak(
        pak_dir / "NMSARC.Precache.pak",
        _PRECACHE_TARGETS,
    )

    # Extract language MBINs from MetadataEtc.pak
    language_mbins = _extract_from_pak(
        pak_dir / "NMSARC.MetadataEtc.pak",
        _LANGUAGE_PREFIXES,
    )

    # Convert all MBINs to EXML
    all_mbins = {**table_mbins, **language_mbins}
    all_exml = converter.convert_batch(all_mbins)

    # Parse tables
    products = _parse_table(all_exml, _PRECACHE_TARGETS[0], parse_product_table)
    substances = _parse_table(all_exml, _PRECACHE_TARGETS[1], parse_substance_table)
    technologies = _parse_table(all_exml, _PRECACHE_TARGETS[2], parse_technology_table)
    recipes = _parse_table(all_exml, _PRECACHE_TARGETS[3], parse_recipe_table)
    seasons = _parse_table(all_exml, _PRECACHE_TARGETS[4], parse_season_table)

    # Build merged locale from all language files
    locale: Dict[str, str] = {}
    for lang_path in _LANGUAGE_PREFIXES:
        if lang_path in all_exml:
            locale.update(parse_locale_table(all_exml[lang_path]))

    # Resolve display names
    products = resolve_locale(products, locale, "name")
    substances = resolve_locale(substances, locale, "name")
    technologies = resolve_locale(technologies, locale, "name")
    seasons = resolve_locale(seasons, locale, "season_name")

    return GameCatalogue(
        products=products,
        substances=substances,
        technologies=technologies,
        locale=locale,
        seasons=seasons,
        recipes=recipes,
    )


def _extract_from_pak(pak_path: Path, targets: list) -> Dict[str, bytes]:
    """Extract specific files from a PAK archive."""
    with HgpakAdapter.from_path(pak_path) as reader:
        return reader.extract(paths=targets)


def _parse_table(exml_map, path, parser_func):
    """Parse a table from the EXML map, returning empty list if missing."""
    exml = exml_map.get(path)
    if exml is None:
        return []
    return parser_func(exml)
