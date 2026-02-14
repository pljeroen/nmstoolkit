"""Recipe Finder tab — lists all cooking/refiner recipes with inputs → outputs."""

import json
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from nmstoolkit.gui.widgets.inventory_grid import (
    get_item_display_name,
    get_item_icon,
)

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

# Known refiner recipe IDs (0-indexed)
_MAX_REFINER_RECIPES = 400

_RECIPE_CATEGORIES = {
    "All Recipes": lambda r: True,
    "Cooking": lambda r: r.get("cooking", False),
    "Refining": lambda r: not r.get("cooking", False),
}


def _load_items():
    """Load items.json from package data directory."""
    items_path = DATA_DIR / "items.json"
    if not items_path.exists():
        return []
    with open(items_path) as f:
        return json.load(f)


def _load_catalogue_recipes():
    """Load recipes from game catalogue if available."""
    import sys
    # In frozen .exe, catalogue is cached next to the executable
    if getattr(sys, "frozen", False):
        cache_dir = Path(sys.executable).parent / "icons"
    else:
        cache_dir = DATA_DIR / "icons"
    cat_path = cache_dir / "game_catalogue.json"
    if not cat_path.exists():
        return []
    with open(cat_path) as f:
        data = json.load(f)
    return data.get("recipes", [])


def _format_item(item_id: str, amount: int) -> str:
    """Format an item reference as 'Name x2' or 'Name'."""
    name = get_item_display_name(item_id)
    if amount > 1:
        return f"{name} x{amount}"
    return name


class RecipeFinderTab(QWidget):
    def __init__(self):
        super().__init__()
        self._data = None
        self._all_recipes = _load_catalogue_recipes()
        self._all_items = _load_items()
        self._build_ui()
        if self._all_recipes:
            self._populate_recipe_table(self._all_recipes)
        else:
            self._populate_fallback_table()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Top bar: search + category filter + unlock
        top = QHBoxLayout()

        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("Search recipes by name or ingredient...")
        self._search_edit.textChanged.connect(self._apply_filter)
        top.addWidget(self._search_edit)

        self._category_combo = QComboBox()
        self._category_combo.addItems(list(_RECIPE_CATEGORIES.keys()))
        self._category_combo.currentTextChanged.connect(lambda _: self._apply_filter())
        top.addWidget(self._category_combo)

        layout.addLayout(top)

        # Info bar
        info_bar = QHBoxLayout()
        self._count_label = QLabel("0 recipes")
        info_bar.addWidget(self._count_label)
        info_bar.addStretch()
        self._known_count_label = QLabel("0 recipes unlocked")
        info_bar.addWidget(self._known_count_label)

        self._unlock_btn = QPushButton("Unlock All Refiner Recipes")
        self._unlock_btn.clicked.connect(self._on_unlock_all)
        info_bar.addWidget(self._unlock_btn)
        layout.addLayout(info_bar)

        # Note if no game data
        self._note = QLabel(
            "Note: Recipe data requires game data extraction via "
            "Tools \u2192 Extract Game Icons. Showing food item catalogue as fallback."
        )
        self._note.setWordWrap(True)
        self._note.setStyleSheet("color: #888; font-size: 11px; margin: 2px 0;")
        self._note.setVisible(not self._all_recipes)
        layout.addWidget(self._note)

        # Table
        self._table = QTableWidget()
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels(
            ["Result", "Ingredients", "Type", "Time"]
        )
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self._table.setAlternatingRowColors(True)
        self._table.setSortingEnabled(True)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self._table)

    def _populate_recipe_table(self, recipes):
        """Populate the table with actual recipe data (inputs → output)."""
        self._table.setSortingEnabled(False)
        self._table.setRowCount(len(recipes))

        for row, recipe in enumerate(recipes):
            # Result column
            result = recipe.get("result", {})
            result_id = result.get("id", "")
            result_amt = result.get("amount", 1)
            result_text = _format_item(result_id, result_amt)

            result_item = QTableWidgetItem(result_text)
            result_item.setToolTip(result_id)
            pixmap = get_item_icon(result_id)
            if pixmap is not None:
                result_item.setIcon(QIcon(pixmap))
            self._table.setItem(row, 0, result_item)

            # Ingredients column
            ingredients = recipe.get("ingredients", [])
            ing_parts = []
            ing_ids = []
            for ing in ingredients:
                ing_id = ing.get("id", "")
                ing_amt = ing.get("amount", 1)
                ing_parts.append(_format_item(ing_id, ing_amt))
                ing_ids.append(ing_id)

            ing_text = " + ".join(ing_parts)
            ing_item = QTableWidgetItem(ing_text)
            ing_item.setToolTip(" + ".join(ing_ids))
            # Use first ingredient's icon
            if ing_ids:
                pixmap = get_item_icon(ing_ids[0])
                if pixmap is not None:
                    ing_item.setIcon(QIcon(pixmap))
            self._table.setItem(row, 1, ing_item)

            # Type column
            recipe_type = "Cooking" if recipe.get("cooking") else "Refining"
            self._table.setItem(row, 2, QTableWidgetItem(recipe_type))

            # Time column
            time_val = recipe.get("time", 0)
            time_item = QTableWidgetItem()
            time_item.setData(Qt.DisplayRole, f"{time_val:.0f}s")
            self._table.setItem(row, 3, time_item)

        self._table.setSortingEnabled(True)
        self._count_label.setText(f"{len(recipes)} recipes")

    def _populate_fallback_table(self):
        """Fallback: show food items from items.json when no recipe data."""
        food_items = [i for i in self._all_items if i.get("cooking") == "true"]
        self._table.setHorizontalHeaderLabels(["Item", "Name", "Category", "Value"])
        self._table.setSortingEnabled(False)
        self._table.setRowCount(len(food_items))

        for row, item in enumerate(food_items):
            item_id = item.get("id", "")
            id_item = QTableWidgetItem(item.get("name", "") or item_id)
            id_item.setToolTip(item_id)
            pixmap = get_item_icon(item_id)
            if pixmap is not None:
                id_item.setIcon(QIcon(pixmap))
            self._table.setItem(row, 0, id_item)
            self._table.setItem(row, 1, QTableWidgetItem(item.get("name", "")))
            self._table.setItem(row, 2, QTableWidgetItem(item.get("type", "")))

            value_item = QTableWidgetItem()
            base_val = item.get("multiplier", "1")
            value_item.setData(
                Qt.DisplayRole, int(base_val) if base_val.isdigit() else 0
            )
            self._table.setItem(row, 3, value_item)

        self._table.setSortingEnabled(True)
        self._count_label.setText(f"{len(food_items)} food items")

    def _apply_filter(self):
        search = self._search_edit.text().lower().strip()
        category = self._category_combo.currentText()
        cat_filter = _RECIPE_CATEGORIES.get(category, _RECIPE_CATEGORIES["All Recipes"])

        if not self._all_recipes:
            return  # Fallback mode doesn't support filtering by recipe type

        filtered = []
        for recipe in self._all_recipes:
            if not cat_filter(recipe):
                continue
            if search:
                # Search in result name, ingredient names, and IDs
                result_id = recipe.get("result", {}).get("id", "")
                result_name = get_item_display_name(result_id).lower()
                ing_names = " ".join(
                    get_item_display_name(i.get("id", "")).lower()
                    for i in recipe.get("ingredients", [])
                )
                ing_ids = " ".join(
                    i.get("id", "").lower() for i in recipe.get("ingredients", [])
                )
                searchable = f"{result_id.lower()} {result_name} {ing_names} {ing_ids}"
                if search not in searchable:
                    continue
            filtered.append(recipe)

        self._populate_recipe_table(filtered)

    def set_data(self, psd: dict):
        self._data = psd
        known = psd.get("KnownRefinerRecipes", [])
        self._known_count_label.setText(f"{len(known)} recipes unlocked")

    def _on_unlock_all(self):
        if self._data is None:
            return
        known = self._data.get("KnownRefinerRecipes", [])
        existing = set(known)
        for i in range(_MAX_REFINER_RECIPES):
            recipe_id = f"^REFINERECIPE_{i}"
            if recipe_id not in existing:
                known.append(recipe_id)
        self._data["KnownRefinerRecipes"] = known
        self._known_count_label.setText(f"{len(known)} recipes unlocked")
