"""Parser for NMS EXML (MBINCompiler XML output).

Pure domain module — stdlib only (xml.etree.ElementTree).

EXML structure:
  <Data template="cTypeName">
    <Property name="Field" value="simple_value" />
    <Property name="Nested" value="GcType">
      <Property name="SubField" value="x" />
    </Property>
    <Property name="ListField">
      <Property name="ListField" value="GcType" _index="0">
        <Property name="ID" value="A" />
      </Property>
    </Property>
  </Data>
"""

from typing import Any, Dict, List, Optional, Union
from xml.etree.ElementTree import Element, fromstring


def parse_exml(source: Union[str, bytes]) -> Dict[str, Any]:
    """Parse EXML source into a nested dict.

    The root Data element's template attribute is stored under key 'template'.
    """
    if isinstance(source, bytes):
        source = source.decode("utf-8")
    root = fromstring(source)
    result: Dict[str, Any] = {}
    result["template"] = root.get("template", "")
    _parse_children(root, result)
    return result


def _parse_children(parent: Element, target: Dict[str, Any]) -> None:
    """Parse Property children of an element into a dict."""
    for child in parent:
        if child.tag != "Property":
            continue
        name = child.get("name")
        value = child.get("value")
        sub_children = [c for c in child if c.tag == "Property"]

        if name is None:
            continue

        if not sub_children:
            # Leaf: simple value
            target[name] = value if value is not None else ""
        elif _is_list_container(child):
            # List container: children share the same name as parent
            target[name] = _parse_list(child)
        elif value is not None:
            # Nested typed object (has value="GcTypeName" and children)
            nested: Dict[str, Any] = {}
            _parse_children(child, nested)
            target[name] = nested
        else:
            # Named container without value — could be list or struct
            if _is_list_container(child):
                target[name] = _parse_list(child)
            else:
                nested = {}
                _parse_children(child, nested)
                target[name] = nested


def _is_list_container(element: Element) -> bool:
    """Check if element is a list container.

    List containers have children whose name attribute matches the parent's name,
    or children with _index attributes.
    """
    parent_name = element.get("name")
    children = [c for c in element if c.tag == "Property"]
    if not children:
        return False
    # Check for _index attribute (explicit list)
    if any(c.get("_index") is not None for c in children):
        return True
    # Check for _id attribute with matching names (table-style list)
    if any(c.get("_id") is not None for c in children):
        child_names = {c.get("name") for c in children}
        if child_names == {parent_name}:
            return True
    return False


def _parse_list(container: Element) -> List[Dict[str, Any]]:
    """Parse a list container into a list of dicts."""
    items = []
    for child in container:
        if child.tag != "Property":
            continue
        item: Dict[str, Any] = {}
        _parse_children(child, item)
        items.append(item)
    return items


# ---------------------------------------------------------------------------
# Table-specific parsers
# ---------------------------------------------------------------------------

def _get_table_entries(source: Union[str, bytes]) -> List[Element]:
    """Get the entry elements from a table EXML."""
    if isinstance(source, bytes):
        source = source.decode("utf-8")
    root = fromstring(source)
    table = root.find("Property[@name='Table']")
    if table is None:
        return []
    return [e for e in table if e.tag == "Property"]


def _get_field(entry: Element, name: str) -> Optional[str]:
    """Get a simple field value from a Property entry."""
    prop = entry.find(f"Property[@name='{name}']")
    if prop is None:
        return None
    return prop.get("value")


def _get_nested_field(entry: Element, container_name: str, field_name: str) -> Optional[str]:
    """Get a field value from a nested typed object."""
    container = entry.find(f"Property[@name='{container_name}']")
    if container is None:
        return None
    inner = container.find(f"Property[@name='{field_name}']")
    if inner is None:
        return None
    return inner.get("value")


def _get_requirements(entry: Element) -> List[Dict[str, Any]]:
    """Parse Requirements list from an entry."""
    reqs_container = entry.find("Property[@name='Requirements']")
    if reqs_container is None:
        return []
    reqs = []
    for req in reqs_container:
        if req.tag != "Property":
            continue
        req_id = _get_field(req, "ID")
        amount_str = _get_field(req, "Amount")
        if req_id is not None:
            reqs.append({
                "id": req_id,
                "type": _get_nested_field(req, "Type", "InventoryType") or "",
                "amount": int(amount_str) if amount_str else 0,
            })
    return reqs


def parse_product_table(source: Union[str, bytes]) -> List[Dict[str, Any]]:
    """Parse a cGcProductTable EXML into a list of product dicts."""
    products = []
    for entry in _get_table_entries(source):
        base_value_str = _get_field(entry, "BaseValue")
        products.append({
            "id": _get_field(entry, "ID") or "",
            "name": _get_field(entry, "Name") or "",
            "name_lower": _get_field(entry, "NameLower") or "",
            "subtitle": _get_field(entry, "Subtitle") or "",
            "description": _get_field(entry, "Description") or "",
            "base_value": int(base_value_str) if base_value_str else 0,
            "icon": _get_nested_field(entry, "Icon", "Filename") or "",
            "category": _get_nested_field(entry, "Category", "SubstanceCategory") or "",
            "type": _get_nested_field(entry, "Type", "ProductCategory") or "",
            "rarity": _get_nested_field(entry, "Rarity", "Rarity") or "",
            "requirements": _get_requirements(entry),
        })
    return products


def parse_substance_table(source: Union[str, bytes]) -> List[Dict[str, Any]]:
    """Parse a cGcSubstanceTable EXML into a list of substance dicts."""
    substances = []
    for entry in _get_table_entries(source):
        base_value_str = _get_field(entry, "BaseValue")
        substances.append({
            "id": _get_field(entry, "ID") or "",
            "name": _get_field(entry, "Name") or "",
            "symbol": _get_field(entry, "Symbol") or "",
            "base_value": int(base_value_str) if base_value_str else 0,
            "icon": _get_nested_field(entry, "Icon", "Filename") or "",
            "category": _get_nested_field(entry, "Category", "SubstanceCategory") or "",
            "rarity": _get_nested_field(entry, "Rarity", "Rarity") or "",
        })
    return substances


def parse_technology_table(source: Union[str, bytes]) -> List[Dict[str, Any]]:
    """Parse a cGcTechnologyTable EXML into a list of technology dicts."""
    techs = []
    for entry in _get_table_entries(source):
        stat_bonuses = []
        bonuses_container = entry.find("Property[@name='StatBonuses']")
        if bonuses_container is not None:
            for bonus in bonuses_container:
                if bonus.tag != "Property":
                    continue
                stat_type = _get_nested_field(bonus, "Stat", "StatsType") or ""
                bonus_val_str = _get_field(bonus, "Bonus")
                level_str = _get_field(bonus, "Level")
                stat_bonuses.append({
                    "stat": stat_type,
                    "bonus": float(bonus_val_str) if bonus_val_str else 0.0,
                    "level": int(level_str) if level_str else 0,
                })

        techs.append({
            "id": _get_field(entry, "ID") or "",
            "name": _get_field(entry, "Name") or "",
            "icon": _get_nested_field(entry, "Icon", "Filename") or "",
            "category": _get_nested_field(entry, "Category", "TechnologyCategory") or "",
            "rarity": _get_nested_field(entry, "Rarity", "TechnologyRarity") or "",
            "requirements": _get_requirements(entry),
            "stat_bonuses": stat_bonuses,
        })
    return techs


def parse_procedural_technology_table(source: Union[str, bytes]) -> List[Dict[str, Any]]:
    """Parse a cGcProceduralTechnologyTable EXML into a list of proc-tech dicts.

    Each entry has: id, template, name, category.
    The template field references a base technology whose icon should be used.
    """
    proc_techs = []
    for entry in _get_table_entries(source):
        proc_techs.append({
            "id": _get_field(entry, "ID") or "",
            "template": _get_field(entry, "Template") or "",
            "name": _get_field(entry, "Name") or "",
            "category": _get_nested_field(entry, "Category", "ProceduralTechnologyCategory") or "",
        })
    return proc_techs


def parse_season_table(source: Union[str, bytes]) -> List[Dict[str, Any]]:
    """Parse a cGcHistoricalSeasonDataTable EXML into a list of season dicts."""
    seasons = []
    for entry in _get_table_entries(source):
        season_num_str = _get_field(entry, "SeasonNumber")
        display_num_str = _get_field(entry, "DisplayNumber")
        remix_num_str = _get_field(entry, "RemixNumber")
        seasons.append({
            "season_name": _get_field(entry, "SeasonName") or "",
            "season_number": int(season_num_str) if season_num_str else 0,
            "display_number": int(display_num_str) if display_num_str else 0,
            "remix_number": int(remix_num_str) if remix_num_str else 0,
            "description": _get_field(entry, "Description") or "",
            "final_reward": _get_field(entry, "FinalReward") or "",
            "unlocked_title": _get_field(entry, "UnlockedTitle") or "",
            "icon": _get_nested_field(entry, "MainIcon", "Filename") or "",
        })
    return seasons


def parse_locale_table(source: Union[str, bytes]) -> Dict[str, str]:
    """Parse a cTkLocalisationTable EXML into an id→localized string mapping."""
    locale = {}
    for entry in _get_table_entries(source):
        locale_id = _get_field(entry, "Id") or _get_field(entry, "ID")
        if not locale_id:
            continue

        # Language tables vary by game version/platform; pick the first
        # non-empty localized value field instead of hardcoding "English".
        text_value = ""
        for prop in entry.findall("Property"):
            name = (prop.get("name") or "").upper()
            if name in {"ID", "IDLOWER", "USEPLAYERNAME"}:
                continue
            value = prop.get("value")
            if value is not None and value != "":
                text_value = value
                break

        if text_value != "":
            locale[locale_id] = text_value
    return locale


def parse_recipe_table(source: Union[str, bytes]) -> List[Dict[str, Any]]:
    """Parse a cGcRecipeTable EXML into a list of recipe dicts.

    Each recipe has: id, recipe_type, recipe_name, time, cooking (bool),
    result (dict with id, type, amount), ingredients (list of same).
    """
    if isinstance(source, bytes):
        source = source.decode("utf-8")
    root = fromstring(source)

    recipes = []
    # Structure: <Property name="Table"><Property value="GcRefinerRecipe" ...>
    table = root.find(".//Property[@name='Table']")
    if table is None:
        return recipes

    for entry in table.findall("./Property[@value='GcRefinerRecipe']"):
        recipe_id = _get_field(entry, "Id") or ""
        recipe_type = _get_field(entry, "RecipeType") or ""
        recipe_name = _get_field(entry, "RecipeName") or ""
        time_str = _get_field(entry, "TimeToMake") or "0"
        cooking_str = _get_field(entry, "Cooking") or "false"

        # Parse result
        result_el = entry.find("./Property[@name='Result']")
        result = _parse_recipe_element(result_el) if result_el is not None else {}

        # Parse ingredients
        ingredients = []
        ing_container = entry.find("./Property[@name='Ingredients']")
        if ing_container is not None:
            for ing in ing_container.findall(
                "./Property[@value='GcRefinerRecipeElement']"
            ):
                ingredients.append(_parse_recipe_element(ing))

        recipes.append({
            "id": recipe_id,
            "recipe_type": recipe_type,
            "recipe_name": recipe_name,
            "time": float(time_str) if time_str else 0.0,
            "cooking": cooking_str.lower() == "true",
            "result": result,
            "ingredients": ingredients,
        })
    return recipes


def _parse_recipe_element(el: Element) -> Dict[str, Any]:
    """Parse a GcRefinerRecipeElement into {id, type, amount}."""
    return {
        "id": _get_field(el, "Id") or "",
        "type": _get_nested_field(el, "Type", "InventoryType") or "",
        "amount": int(_get_field(el, "Amount") or "0"),
    }


def resolve_locale(
    items: List[Dict[str, Any]],
    locale: Dict[str, str],
    name_field: str = "name",
) -> List[Dict[str, Any]]:
    """Add display_name to items by resolving locale keys.

    Each item gets a 'display_name' field resolved from locale[item[name_field]].
    If the key is not found, the original value is used as fallback.
    """
    resolved = []
    for item in items:
        enriched = dict(item)
        key = item.get(name_field, "")
        enriched["display_name"] = locale.get(key, key)
        resolved.append(enriched)
    return resolved
