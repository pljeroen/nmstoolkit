"""Game data catalogue — immutable domain model.

Holds parsed game data: products, substances, technologies, seasons, locale strings.
Pure domain — stdlib only.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class GameCatalogue:
    """Immutable container for parsed NMS game data."""

    products: List[Dict[str, Any]]
    substances: List[Dict[str, Any]]
    technologies: List[Dict[str, Any]]
    locale: Dict[str, str]
    seasons: List[Dict[str, Any]] = field(default_factory=list)
    recipes: List[Dict[str, Any]] = field(default_factory=list)

    def find_product(self, item_id: str) -> Optional[Dict[str, Any]]:
        for p in self.products:
            if p.get("id") == item_id:
                return p
        return None

    def find_substance(self, item_id: str) -> Optional[Dict[str, Any]]:
        for s in self.substances:
            if s.get("id") == item_id:
                return s
        return None

    def find_technology(self, item_id: str) -> Optional[Dict[str, Any]]:
        for t in self.technologies:
            if t.get("id") == item_id:
                return t
        return None

    def find_item(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Search all item types for a given ID."""
        return (
            self.find_product(item_id)
            or self.find_substance(item_id)
            or self.find_technology(item_id)
        )

    def find_season(self, season_number: int) -> Optional[Dict[str, Any]]:
        """Find a historical season by its season number."""
        for s in self.seasons:
            if s.get("season_number") == season_number:
                return s
        return None

    def to_json(self) -> str:
        return json.dumps({
            "products": self.products,
            "substances": self.substances,
            "technologies": self.technologies,
            "locale": self.locale,
            "seasons": self.seasons,
            "recipes": self.recipes,
        }, separators=(",", ":"))

    @classmethod
    def from_json(cls, data: str) -> GameCatalogue:
        parsed = json.loads(data)
        return cls(
            products=parsed["products"],
            substances=parsed["substances"],
            technologies=parsed["technologies"],
            locale=parsed["locale"],
            seasons=parsed.get("seasons", []),
            recipes=parsed.get("recipes", []),
        )
