"""Tests for EXML parser.

Tests R-EXML-01 through R-EXML-07.
Uses synthetic EXML matching real NMS structure.
"""

import ast
from pathlib import Path
from textwrap import dedent

import pytest

# ---------------------------------------------------------------------------
# Synthetic EXML fixtures (based on real NMS EXML structure)
# ---------------------------------------------------------------------------

PRODUCT_TABLE_EXML = dedent("""\
    <?xml version="1.0" encoding="utf-8"?>
    <Data template="cGcProductTable">
        <Property name="Table">
            <Property name="Table" value="GcProductData" _id="CASING">
                <Property name="ID" value="CASING" />
                <Property name="Name" value="CASING_NAME" />
                <Property name="NameLower" value="CASING_NAME_L" />
                <Property name="Subtitle" value="CRAFTPROD_SUB" />
                <Property name="Description" value="CASING_DESC" />
                <Property name="BaseValue" value="800" />
                <Property name="Level" value="0" />
                <Property name="Category" value="GcRealitySubstanceCategory">
                    <Property name="SubstanceCategory" value="Catalyst" />
                </Property>
                <Property name="Type" value="GcProductCategory">
                    <Property name="ProductCategory" value="Component" />
                </Property>
                <Property name="Rarity" value="GcRarity">
                    <Property name="Rarity" value="Common" />
                </Property>
                <Property name="Icon" value="TkTextureResource">
                    <Property name="Filename" value="TEXTURES/UI/FRONTEND/ICONS/U4PRODUCTS/PRODUCT.CASING.DDS" />
                </Property>
                <Property name="Consumable" value="false" />
                <Property name="StackMultiplier" value="2" />
                <Property name="Requirements">
                    <Property name="Requirements" value="GcTechnologyRequirement" _id="LAND1">
                        <Property name="ID" value="LAND1" />
                        <Property name="Type" value="GcInventoryType">
                            <Property name="InventoryType" value="Substance" />
                        </Property>
                        <Property name="Amount" value="50" />
                    </Property>
                </Property>
            </Property>
            <Property name="Table" value="GcProductData" _id="HYPERFUEL1">
                <Property name="ID" value="HYPERFUEL1" />
                <Property name="Name" value="HYPERFUEL1_NAME" />
                <Property name="NameLower" value="HYPERFUEL1_NAME_L" />
                <Property name="Subtitle" value="CRAFTPROD_SUB" />
                <Property name="Description" value="HYPERFUEL1_DESC" />
                <Property name="BaseValue" value="3000" />
                <Property name="Level" value="0" />
                <Property name="Category" value="GcRealitySubstanceCategory">
                    <Property name="SubstanceCategory" value="Fuel" />
                </Property>
                <Property name="Type" value="GcProductCategory">
                    <Property name="ProductCategory" value="Consumable" />
                </Property>
                <Property name="Rarity" value="GcRarity">
                    <Property name="Rarity" value="Common" />
                </Property>
                <Property name="Icon" value="TkTextureResource">
                    <Property name="Filename" value="TEXTURES/UI/FRONTEND/ICONS/U4PRODUCTS/PRODUCT.DVOID.DDS" />
                </Property>
                <Property name="Consumable" value="true" />
                <Property name="StackMultiplier" value="1" />
                <Property name="Requirements">
                    <Property name="Requirements" value="GcTechnologyRequirement" _id="FUEL1">
                        <Property name="ID" value="FUEL1" />
                        <Property name="Type" value="GcInventoryType">
                            <Property name="InventoryType" value="Substance" />
                        </Property>
                        <Property name="Amount" value="40" />
                    </Property>
                    <Property name="Requirements" value="GcTechnologyRequirement" _id="ASTEROID1">
                        <Property name="ID" value="ASTEROID1" />
                        <Property name="Type" value="GcInventoryType">
                            <Property name="InventoryType" value="Substance" />
                        </Property>
                        <Property name="Amount" value="40" />
                    </Property>
                </Property>
            </Property>
        </Property>
    </Data>
""")

SUBSTANCE_TABLE_EXML = dedent("""\
    <?xml version="1.0" encoding="utf-8"?>
    <Data template="cGcSubstanceTable">
        <Property name="Table">
            <Property name="Table" value="GcRealitySubstanceData" _id="FUEL1">
                <Property name="Name" value="UI_FUEL_1_NAME" />
                <Property name="NameLower" value="UI_FUEL_1_NAME_L" />
                <Property name="ID" value="FUEL1" />
                <Property name="Symbol" value="UI_FUEL1_SYM" />
                <Property name="BaseValue" value="12" />
                <Property name="Category" value="GcRealitySubstanceCategory">
                    <Property name="SubstanceCategory" value="Fuel" />
                </Property>
                <Property name="Rarity" value="GcRarity">
                    <Property name="Rarity" value="Common" />
                </Property>
                <Property name="Icon" value="TkTextureResource">
                    <Property name="Filename" value="TEXTURES/UI/FRONTEND/ICONS/SUBSTANCES/SUBSTANCE.FUEL.1.DDS" />
                </Property>
                <Property name="ChargeValue" value="1" />
            </Property>
        </Property>
    </Data>
""")

TECHNOLOGY_TABLE_EXML = dedent("""\
    <?xml version="1.0" encoding="utf-8"?>
    <Data template="cGcTechnologyTable">
        <Property name="Table">
            <Property name="Table" value="GcTechnology" _id="PROTECT">
                <Property name="ID" value="PROTECT" />
                <Property name="Name" value="PROTECT_NAME" />
                <Property name="NameLower" value="PROTECT_NAME_L" />
                <Property name="Subtitle" value="PROTECT_SUBTITLE" />
                <Property name="Description" value="PROTECT_DESCRIPTION" />
                <Property name="Chargeable" value="true" />
                <Property name="ChargeAmount" value="80" />
                <Property name="Category" value="GcTechnologyCategory">
                    <Property name="TechnologyCategory" value="Suit" />
                </Property>
                <Property name="Rarity" value="GcTechnologyRarity">
                    <Property name="TechnologyRarity" value="Always" />
                </Property>
                <Property name="Requirements">
                    <Property name="Requirements" value="GcTechnologyRequirement" _id="LAND1">
                        <Property name="ID" value="LAND1" />
                        <Property name="Type" value="GcInventoryType">
                            <Property name="InventoryType" value="Substance" />
                        </Property>
                        <Property name="Amount" value="100" />
                    </Property>
                </Property>
                <Property name="StatBonuses">
                    <Property name="StatBonuses" value="GcStatsBonus" _index="0">
                        <Property name="Stat" value="GcStatsTypes">
                            <Property name="StatsType" value="Suit_Protection" />
                        </Property>
                        <Property name="Bonus" value="1.000000" />
                        <Property name="Level" value="1" />
                    </Property>
                </Property>
            </Property>
        </Property>
    </Data>
""")

LOCALE_TABLE_EXML = dedent("""\
    <?xml version="1.0" encoding="utf-8"?>
    <Data template="cTkLocalisationTable">
        <Property name="Table">
            <Property name="Table" value="TkLocalisationEntry" _id="CASING_NAME">
                <Property name="Id" value="CASING_NAME" />
                <Property name="English" value="METAL PLATING" />
                <Property name="French" value="" />
                <Property name="Dutch" value="" />
            </Property>
            <Property name="Table" value="TkLocalisationEntry" _id="UI_FUEL_1_NAME">
                <Property name="Id" value="UI_FUEL_1_NAME" />
                <Property name="English" value="CARBON" />
                <Property name="French" value="" />
                <Property name="Dutch" value="" />
            </Property>
            <Property name="Table" value="TkLocalisationEntry" _id="PROTECT_NAME">
                <Property name="Id" value="PROTECT_NAME" />
                <Property name="English" value="HAZARD PROTECTION" />
                <Property name="French" value="" />
                <Property name="Dutch" value="" />
            </Property>
            <Property name="Table" value="TkLocalisationEntry" _id="ESCAPED_TEXT">
                <Property name="Id" value="ESCAPED_TEXT" />
                <Property name="English" value="Press &lt;IMG&gt;SLASH&lt;&gt; to continue" />
                <Property name="French" value="" />
                <Property name="Dutch" value="" />
            </Property>
        </Property>
    </Data>
""")


# ---------------------------------------------------------------------------
# R-EXML-01: Generic Property tree parsing
# ---------------------------------------------------------------------------

class TestPropertyTreeParsing:
    """R-EXML-01: Parse EXML Property tree into Python structures."""

    def test_parse_simple_values(self):
        from nmstoolkit.core.exml_parser import parse_exml

        exml = dedent("""\
            <?xml version="1.0" encoding="utf-8"?>
            <Data template="cTest">
                <Property name="Name" value="hello" />
                <Property name="Count" value="42" />
            </Data>
        """)
        result = parse_exml(exml)
        assert result["template"] == "cTest"
        assert result["Name"] == "hello"
        assert result["Count"] == "42"

    def test_parse_nested_object(self):
        from nmstoolkit.core.exml_parser import parse_exml

        exml = dedent("""\
            <?xml version="1.0" encoding="utf-8"?>
            <Data template="cTest">
                <Property name="Category" value="GcCategory">
                    <Property name="Type" value="Fuel" />
                </Property>
            </Data>
        """)
        result = parse_exml(exml)
        assert isinstance(result["Category"], dict)
        assert result["Category"]["Type"] == "Fuel"

    def test_parse_list(self):
        from nmstoolkit.core.exml_parser import parse_exml

        exml = dedent("""\
            <?xml version="1.0" encoding="utf-8"?>
            <Data template="cTest">
                <Property name="Items">
                    <Property name="Items" value="GcItem" _index="0">
                        <Property name="ID" value="A" />
                    </Property>
                    <Property name="Items" value="GcItem" _index="1">
                        <Property name="ID" value="B" />
                    </Property>
                </Property>
            </Data>
        """)
        result = parse_exml(exml)
        assert isinstance(result["Items"], list)
        assert len(result["Items"]) == 2
        assert result["Items"][0]["ID"] == "A"
        assert result["Items"][1]["ID"] == "B"

    def test_parse_from_bytes(self):
        from nmstoolkit.core.exml_parser import parse_exml

        exml = b'<?xml version="1.0" encoding="utf-8"?>\n<Data template="cTest"><Property name="X" value="1" /></Data>'
        result = parse_exml(exml)
        assert result["X"] == "1"

    def test_template_attribute_preserved(self):
        from nmstoolkit.core.exml_parser import parse_exml

        result = parse_exml(PRODUCT_TABLE_EXML)
        assert result["template"] == "cGcProductTable"


# ---------------------------------------------------------------------------
# R-EXML-02: Product table parsing
# ---------------------------------------------------------------------------

class TestProductTable:
    """R-EXML-02: Parse GcProductTable."""

    def test_parse_products(self):
        from nmstoolkit.core.exml_parser import parse_product_table

        products = parse_product_table(PRODUCT_TABLE_EXML)
        assert len(products) == 2

    def test_product_fields(self):
        from nmstoolkit.core.exml_parser import parse_product_table

        products = parse_product_table(PRODUCT_TABLE_EXML)
        casing = products[0]
        assert casing["id"] == "CASING"
        assert casing["name"] == "CASING_NAME"
        assert casing["base_value"] == 800
        assert casing["category"] == "Catalyst"
        assert casing["type"] == "Component"
        assert casing["rarity"] == "Common"

    def test_product_icon(self):
        from nmstoolkit.core.exml_parser import parse_product_table

        products = parse_product_table(PRODUCT_TABLE_EXML)
        casing = products[0]
        assert casing["icon"] == "TEXTURES/UI/FRONTEND/ICONS/U4PRODUCTS/PRODUCT.CASING.DDS"
        hyperfuel = products[1]
        assert hyperfuel["icon"] == "TEXTURES/UI/FRONTEND/ICONS/U4PRODUCTS/PRODUCT.DVOID.DDS"

    def test_product_requirements(self):
        from nmstoolkit.core.exml_parser import parse_product_table

        products = parse_product_table(PRODUCT_TABLE_EXML)
        casing = products[0]
        assert len(casing["requirements"]) == 1
        assert casing["requirements"][0]["id"] == "LAND1"
        assert casing["requirements"][0]["amount"] == 50

    def test_product_multiple_requirements(self):
        from nmstoolkit.core.exml_parser import parse_product_table

        products = parse_product_table(PRODUCT_TABLE_EXML)
        hyperfuel = products[1]
        assert len(hyperfuel["requirements"]) == 2
        assert hyperfuel["requirements"][0]["id"] == "FUEL1"
        assert hyperfuel["requirements"][1]["id"] == "ASTEROID1"


# ---------------------------------------------------------------------------
# R-EXML-03: Substance table parsing
# ---------------------------------------------------------------------------

class TestSubstanceTable:
    """R-EXML-03: Parse GcSubstanceTable."""

    def test_parse_substances(self):
        from nmstoolkit.core.exml_parser import parse_substance_table

        substances = parse_substance_table(SUBSTANCE_TABLE_EXML)
        assert len(substances) == 1

    def test_substance_fields(self):
        from nmstoolkit.core.exml_parser import parse_substance_table

        substances = parse_substance_table(SUBSTANCE_TABLE_EXML)
        fuel = substances[0]
        assert fuel["id"] == "FUEL1"
        assert fuel["name"] == "UI_FUEL_1_NAME"
        assert fuel["symbol"] == "UI_FUEL1_SYM"
        assert fuel["base_value"] == 12
        assert fuel["category"] == "Fuel"
        assert fuel["rarity"] == "Common"

    def test_substance_icon(self):
        from nmstoolkit.core.exml_parser import parse_substance_table

        substances = parse_substance_table(SUBSTANCE_TABLE_EXML)
        fuel = substances[0]
        assert fuel["icon"] == "TEXTURES/UI/FRONTEND/ICONS/SUBSTANCES/SUBSTANCE.FUEL.1.DDS"


# ---------------------------------------------------------------------------
# R-EXML-04: Technology table parsing
# ---------------------------------------------------------------------------

class TestTechnologyTable:
    """R-EXML-04: Parse GcTechnologyTable."""

    def test_parse_technologies(self):
        from nmstoolkit.core.exml_parser import parse_technology_table

        techs = parse_technology_table(TECHNOLOGY_TABLE_EXML)
        assert len(techs) == 1

    def test_technology_fields(self):
        from nmstoolkit.core.exml_parser import parse_technology_table

        techs = parse_technology_table(TECHNOLOGY_TABLE_EXML)
        protect = techs[0]
        assert protect["id"] == "PROTECT"
        assert protect["name"] == "PROTECT_NAME"
        assert protect["category"] == "Suit"
        assert protect["rarity"] == "Always"

    def test_technology_requirements(self):
        from nmstoolkit.core.exml_parser import parse_technology_table

        techs = parse_technology_table(TECHNOLOGY_TABLE_EXML)
        protect = techs[0]
        assert len(protect["requirements"]) == 1
        assert protect["requirements"][0]["id"] == "LAND1"
        assert protect["requirements"][0]["amount"] == 100

    def test_technology_stat_bonuses(self):
        from nmstoolkit.core.exml_parser import parse_technology_table

        techs = parse_technology_table(TECHNOLOGY_TABLE_EXML)
        protect = techs[0]
        assert len(protect["stat_bonuses"]) == 1
        assert protect["stat_bonuses"][0]["stat"] == "Suit_Protection"
        assert protect["stat_bonuses"][0]["bonus"] == 1.0


# ---------------------------------------------------------------------------
# R-EXML-05: Localisation table parsing
# ---------------------------------------------------------------------------

class TestLocalisationTable:
    """R-EXML-05: Parse TkLocalisationTable."""

    def test_parse_locale(self):
        from nmstoolkit.core.exml_parser import parse_locale_table

        locale = parse_locale_table(LOCALE_TABLE_EXML)
        assert isinstance(locale, dict)
        assert len(locale) == 4

    def test_locale_values(self):
        from nmstoolkit.core.exml_parser import parse_locale_table

        locale = parse_locale_table(LOCALE_TABLE_EXML)
        assert locale["CASING_NAME"] == "METAL PLATING"
        assert locale["UI_FUEL_1_NAME"] == "CARBON"
        assert locale["PROTECT_NAME"] == "HAZARD PROTECTION"

    def test_locale_xml_entity_handling(self):
        from nmstoolkit.core.exml_parser import parse_locale_table

        locale = parse_locale_table(LOCALE_TABLE_EXML)
        assert locale["ESCAPED_TEXT"] == "Press <IMG>SLASH<> to continue"


# ---------------------------------------------------------------------------
# R-EXML-06: Locale resolution
# ---------------------------------------------------------------------------

class TestLocaleResolution:
    """R-EXML-06: Resolve locale keys to display names."""

    def test_resolve_product_name(self):
        from nmstoolkit.core.exml_parser import (
            parse_locale_table,
            parse_product_table,
            resolve_locale,
        )

        products = parse_product_table(PRODUCT_TABLE_EXML)
        locale = parse_locale_table(LOCALE_TABLE_EXML)
        resolved = resolve_locale(products, locale, "name")
        assert resolved[0]["display_name"] == "METAL PLATING"

    def test_resolve_missing_key_keeps_original(self):
        from nmstoolkit.core.exml_parser import resolve_locale

        items = [{"id": "X", "name": "MISSING_KEY"}]
        locale = {}
        resolved = resolve_locale(items, locale, "name")
        assert resolved[0]["display_name"] == "MISSING_KEY"


# ---------------------------------------------------------------------------
# R-EXML-07: Domain purity
# ---------------------------------------------------------------------------

class TestExmlParserPurity:
    """R-EXML-07: exml_parser.py uses only stdlib."""

    def test_no_external_imports(self):
        parser_path = (
            Path(__file__).parent.parent.parent
            / "src"
            / "nmstoolkit"
            / "core"
            / "exml_parser.py"
        )
        source = parser_path.read_text()
        tree = ast.parse(source)

        stdlib_modules = {
            "xml", "pathlib", "typing", "collections", "dataclasses",
            "enum", "os", "sys", "io", "re", "functools", "itertools",
            "__future__",
        }

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top = alias.name.split(".")[0]
                    assert top in stdlib_modules, (
                        f"Non-stdlib import: {alias.name}"
                    )
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    top = node.module.split(".")[0]
                    assert top in stdlib_modules, (
                        f"Non-stdlib import: from {node.module}"
                    )
