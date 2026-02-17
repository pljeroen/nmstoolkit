"""Inventory grid widget — displays NMS inventory slots in a grid."""

import copy
import json
from typing import Optional, Tuple

from PySide6.QtCore import QMimeData, QPoint, Qt, Signal
from PySide6.QtGui import QColor, QDrag, QFont, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QGridLayout,
    QLabel,
    QMenu,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
from nmstoolkit.paths import resource_dir

DATA_DIR = resource_dir()

_CATALOGUE = None
_ICON_PROVIDER = None
_CLIPBOARD_SLOT: Optional[dict] = None

# Type → (background color, border accent)
_TYPE_COLORS = {
    "Substance": ("#2d5a3d", "#4a7"),
    "Product": ("#5a4a2d", "#a84"),
    "Technology": ("#2d3a5a", "#48a"),
}
_EMPTY_COLORS = ("#2a2a2e", "#555")
_LOCKED_COLORS = ("#1a1a1e", "#333")
_SPECIAL_BORDER = "#dd2"  # Gold — supercharged slot accent

_MIME_TYPE = "application/x-nms-slot-pos"


def _get_type_colors(inv_type: str) -> Tuple[str, str]:
    """Return (background, border) color pair for an inventory type."""
    return _TYPE_COLORS.get(inv_type, _EMPTY_COLORS)


def set_clipboard_slot(slot_data: Optional[dict]):
    """Set the module-level clipboard slot data."""
    global _CLIPBOARD_SLOT
    _CLIPBOARD_SLOT = copy.deepcopy(slot_data) if slot_data is not None else None


def get_clipboard_slot() -> Optional[dict]:
    """Get the module-level clipboard slot data (deep copy)."""
    if _CLIPBOARD_SLOT is None:
        return None
    return copy.deepcopy(_CLIPBOARD_SLOT)


def set_catalogue(catalogue):
    """Set the active GameCatalogue for item name resolution."""
    global _CATALOGUE
    _CATALOGUE = catalogue


def set_icon_provider(provider):
    """Set the active IconProvider for item icon display."""
    global _ICON_PROVIDER
    _ICON_PROVIDER = provider


def _load_item_names():
    """Load item ID -> name mapping from items.json (static fallback).

    items.json stores substance IDs with ^ prefix (e.g. ^FUEL1 -> Carbon)
    but save data uses bare IDs (FUEL1). Index both forms so bare lookups work.
    """
    items_path = DATA_DIR / "items.json"
    if not items_path.exists():
        return {}
    with open(items_path, "r", encoding="utf-8") as f:
        items = json.load(f)
    names = {}
    for item in items:
        item_id = item["id"]
        name = item["name"]
        names[item_id] = name
        if item_id.startswith("^"):
            names[item_id[1:]] = name
    return names


def _load_item_symbols():
    """Load item ID -> symbol mapping from items.json."""
    items_path = DATA_DIR / "items.json"
    if not items_path.exists():
        return {}
    with open(items_path, "r", encoding="utf-8") as f:
        items = json.load(f)
    result = {}
    for item in items:
        symbol = item.get("symbol", "")
        if symbol:
            result[item["id"]] = symbol
        else:
            name = item.get("name", "")
            if name:
                result[item["id"]] = name[:2]
    return result


_ITEM_NAMES = None
_ITEM_SYMBOLS = None


def _get_item_name(item_id: str) -> str:
    """Resolve an item ID to a display name.

    Priority: items.json (curated proper-case names) > catalogue display_name
    (game locale is ALL CAPS) > catalogue locale fallback > raw ID.
    """
    global _ITEM_NAMES

    # 1. items.json has curated proper-case names — check first
    if _ITEM_NAMES is None:
        _ITEM_NAMES = _load_item_names()

    name = _ITEM_NAMES.get(item_id)
    if name:
        return name
    # Procedural items in items.json
    if "#" in item_id:
        base_id = item_id.split("#")[0]
        name = _ITEM_NAMES.get(base_id)
        if name:
            return name

    # 1b. Fossil items get friendly names
    from nmstoolkit.gui.tabs.fossils_tab import is_fossil_item, friendly_fossil_name
    if is_fossil_item(item_id):
        return friendly_fossil_name(item_id)

    # 2. Catalogue display_name (ALL CAPS from game locale, title-cased)
    if _CATALOGUE is not None:
        item = _CATALOGUE.find_item(item_id)
        if item is None and item_id.startswith("^"):
            item = _CATALOGUE.find_item(item_id[1:])
        if item is not None:
            display = item.get("display_name", item.get("name", ""))
            if display:
                return _title_case_name(display)
        # Procedural items: strip #nnnnn suffix and try base type
        if "#" in item_id:
            base_id = item_id.split("#")[0]
            item = _CATALOGUE.find_item(base_id)
            if item is None and base_id.startswith("^"):
                item = _CATALOGUE.find_item(base_id[1:])
            if item is not None:
                display = item.get("display_name", item.get("name", ""))
                if display:
                    return _title_case_name(display)
        # Locale fallback: resolve locale keys not in product/substance/technology tables
        bare = item_id.lstrip("^")
        locale_name = _CATALOGUE.locale.get(bare) or _CATALOGUE.locale.get(item_id)
        if locale_name:
            return _title_case_name(locale_name)

    return item_id.lstrip("^") if item_id else "Empty"


def _title_case_name(name: str) -> str:
    """Convert ALL CAPS game names to title case, preserving special formatting.

    'CARBON' -> 'Carbon', 'DI-HYDROGEN' -> 'Di-Hydrogen',
    'METAL PLATING' -> 'Metal Plating'
    """
    if not name or not name.isupper():
        return name
    # str.title() handles spaces and hyphens correctly
    return name.title()


def _get_item_symbol(item_id: str) -> str:
    """Get a short symbol/abbreviation for an item (e.g., 'C' for Carbon)."""
    global _ITEM_SYMBOLS
    if not item_id:
        return ""
    if _ITEM_SYMBOLS is None:
        _ITEM_SYMBOLS = _load_item_symbols()
    return _ITEM_SYMBOLS.get(item_id, "")


def _get_item_pixmap(item_id: str, size: int = 32) -> Optional[QPixmap]:
    """Get a QPixmap icon for an item ID, or None if unavailable."""
    if _ICON_PROVIDER is None:
        return None
    png_path = _ICON_PROVIDER.get_pixmap_path(item_id)
    if png_path is None:
        return None
    pixmap = QPixmap(str(png_path))
    if pixmap.isNull():
        return None
    return pixmap.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)


def get_item_display_name(item_id: str) -> str:
    """Public API: resolve item ID to display name."""
    return _get_item_name(item_id)


def get_item_icon(item_id: str, size: int = 20) -> Optional[QPixmap]:
    """Public API: get icon pixmap for an item ID.

    Returns a real icon from the icon provider if available,
    otherwise a colored placeholder with the item's symbol.
    """
    pixmap = _get_item_pixmap(item_id, size)
    if pixmap is not None:
        return pixmap
    if not item_id:
        return None
    # Determine type colors from the item ID prefix
    inv_type = _guess_item_type(item_id)
    bg, border = _get_type_colors(inv_type)
    symbol = _get_item_symbol(item_id)
    if not symbol:
        # Use first letter of display name as symbol
        name = _get_item_name(item_id)
        symbol = name[:2] if name and name != item_id else item_id.lstrip("^")[:2]
    return _create_placeholder_pixmap(symbol, bg, border, size=size)


def _guess_item_type(item_id: str) -> str:
    """Guess the inventory type (Substance/Product/Technology) from an item ID."""
    if not item_id:
        return ""
    uid = item_id.upper().lstrip("^")
    # Technology items
    if any(uid.startswith(p) for p in [
        "UP_", "UT_", "U_", "TECH", "SHIP_", "SUIT_", "WEAPON_", "VEHICLE_",
        "YOURFREIG", "YOURSHIP", "YOURSUIT", "YOURMULTI", "YOURVEHIC",
        "HYPERDRIVE", "SHIELD", "LASER", "JETPACK", "SCANNER", "BOLT",
        "PHOTON", "PULSE", "ROCKET", "TERRAIN", "FREIGHT", "MECH_",
    ]):
        return "Technology"
    # Substances
    if any(uid.startswith(p) for p in [
        "FUEL", "LAND", "WATER", "CAVE", "RADIO", "GAS", "ASTEROID",
        "STELLAR", "OXYGEN", "CARBON", "SODIUM", "COBALT", "FERRITE",
        "COPPER", "CADMIUM", "EMERIL", "INDIUM", "CHROMATIC",
        "DIHYDROGEN", "DEUTERIUM", "TRITIUM", "CONDENSED",
        "JELLY", "LAUNCHSUB",
    ]):
        return "Substance"
    # Default to Product
    return "Product"


def _create_placeholder_pixmap(
    symbol: str, bg_color: str, border_color: str, size: int = 32
) -> QPixmap:
    """Draw a colored square with a symbol letter as a placeholder icon."""
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(0, 0, 0, 0))

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    bg = QColor(bg_color)
    border = QColor(border_color)

    painter.setPen(border)
    painter.setBrush(bg)
    painter.drawRoundedRect(1, 1, size - 2, size - 2, 3, 3)

    if symbol:
        painter.setPen(QColor("#eee"))
        font = QFont("monospace")
        font_size = max(8, size // 3)
        font.setPixelSize(font_size)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(0, 0, size, size, Qt.AlignCenter, symbol)

    painter.end()
    return pixmap


def _make_slot_style(
    bg: str, border: str, left_accent: str = "", special: bool = False,
) -> str:
    """Build a stylesheet string for a slot widget."""
    style = (
        f"background: qlineargradient("
        f"x1:0, y1:0, x2:1, y2:1, "
        f"stop:0 {bg}, stop:1 {_darken(bg)});"
        f"border: 1px solid {border};"
        f"border-radius: 3px;"
    )
    if special:
        style += (
            f"border-left: 3px solid {_SPECIAL_BORDER};"
            f"border-top: 3px solid {_SPECIAL_BORDER};"
        )
    elif left_accent:
        style += f"border-left: 3px solid {left_accent};"
    return style


def _darken(hex_color: str) -> str:
    """Darken a hex color by ~20%."""
    c = QColor(hex_color)
    return QColor(
        max(0, int(c.red() * 0.8)),
        max(0, int(c.green() * 0.8)),
        max(0, int(c.blue() * 0.8)),
    ).name()


def _lighten(hex_color: str) -> str:
    """Lighten a hex color for hover."""
    c = QColor(hex_color)
    return QColor(
        min(255, int(c.red() * 1.3 + 30)),
        min(255, int(c.green() * 1.3 + 30)),
        min(255, int(c.blue() * 1.3 + 30)),
    ).name()


class SlotWidget(QWidget):
    """A single inventory slot."""

    clicked = Signal(int, int)  # x, y coordinates
    right_clicked = Signal(int, int)  # x, y coordinates

    def __init__(self, index: int, locked: bool = False, x: int = 0, y: int = 0, special: bool = False):
        super().__init__()
        self._index = index
        self._locked = locked
        self._x = x
        self._y = y
        self._special = special
        self._inv_type = ""
        self._drag_start_pos = None
        self._drag_started = False
        self._grid = None
        self.setFixedSize(80, 80)
        self.setAcceptDrops(not locked)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(0)

        self._icon_label = QLabel()
        self._icon_label.setAlignment(Qt.AlignCenter)
        self._icon_label.setFixedHeight(34)
        self._icon_label.setStyleSheet("border: none;")
        layout.addWidget(self._icon_label)

        self._name_label = QLabel()
        self._name_label.setAlignment(Qt.AlignCenter)
        self._name_label.setStyleSheet("font-size: 10px; color: #ddd; border: none;")
        self._name_label.setWordWrap(True)
        layout.addWidget(self._name_label)

        self._amount_label = QLabel()
        self._amount_label.setAlignment(Qt.AlignCenter)
        self._amount_label.setStyleSheet("font-size: 10px; color: #aaa; border: none;")
        layout.addWidget(self._amount_label)

        self._apply_style()

    def _apply_style(self):
        """Apply style based on current state."""
        if self._locked:
            bg, border = _LOCKED_COLORS
            self.setStyleSheet(_make_slot_style(bg, border))
        elif self._inv_type:
            bg, border = _get_type_colors(self._inv_type)
            self.setStyleSheet(_make_slot_style(bg, border, left_accent=border, special=self._special))
        else:
            bg, border = _EMPTY_COLORS
            self.setStyleSheet(_make_slot_style(bg, border, special=self._special))

    @property
    def is_locked(self) -> bool:
        return self._locked

    @is_locked.setter
    def is_locked(self, value: bool):
        self._locked = value
        self.setAcceptDrops(not value)
        if value:
            self._inv_type = ""
            self._icon_label.clear()
            self._name_label.setText("")
            self._amount_label.setText("")
        self._apply_style()

    def set_slot_data(self, slot: dict):
        item_id = slot.get("Id", "")
        amount = slot.get("Amount", 0)
        max_amount = slot.get("MaxAmount", 0)
        self._inv_type = slot.get("Type", {}).get("InventoryType", "")

        name = _get_item_name(item_id) if item_id else "Empty"

        if item_id:
            pixmap = _get_item_pixmap(item_id)
            if pixmap is not None:
                self._icon_label.setPixmap(pixmap)
            else:
                symbol = _get_item_symbol(item_id)
                bg, border = _get_type_colors(self._inv_type)
                placeholder = _create_placeholder_pixmap(symbol, bg, border, size=32)
                self._icon_label.setPixmap(placeholder)

            self._name_label.setText(name)
            self._amount_label.setText(f"{amount}/{max_amount}")
        else:
            self._inv_type = ""
            self._icon_label.clear()
            self._name_label.setText("")
            self._amount_label.setText("")

        self._apply_style()

    def clear_slot(self):
        self._inv_type = ""
        self._icon_label.clear()
        self._name_label.setText("")
        self._amount_label.setText("")
        self._apply_style()

    def enterEvent(self, event):
        if not self._locked:
            if self._inv_type:
                _, border = _get_type_colors(self._inv_type)
            else:
                _, border = _EMPTY_COLORS
            hover_border = _lighten(border)
            current = self.styleSheet()
            # Swap border color for hover highlight
            self.setStyleSheet(current.replace(
                f"border: 1px solid {border}",
                f"border: 1px solid {hover_border}",
            ))
        super().enterEvent(event)

    def leaveEvent(self, event):
        if not self._locked:
            self._apply_style()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_start_pos = event.position().toPoint()
            self._drag_started = False
        elif event.button() == Qt.RightButton:
            self.right_clicked.emit(self._x, self._y)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            if not self._drag_started and self._drag_start_pos is not None:
                self.clicked.emit(self._x, self._y)
            self._drag_start_pos = None
            self._drag_started = False
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton):
            return
        if self._drag_start_pos is None:
            return
        if self._locked:
            return
        distance = (event.position().toPoint() - self._drag_start_pos).manhattanLength()
        if distance < QApplication.startDragDistance():
            return

        self._drag_started = True
        drag = QDrag(self)
        mime = QMimeData()
        mime.setData(_MIME_TYPE, json.dumps({"x": self._x, "y": self._y}).encode())
        drag.setMimeData(mime)

        pixmap = self.grab()
        drag.setPixmap(pixmap)
        drag.setHotSpot(QPoint(pixmap.width() // 2, pixmap.height() // 2))

        drag.exec(Qt.MoveAction | Qt.CopyAction)

    def dragEnterEvent(self, event):
        if self._locked:
            event.ignore()
            return
        if event.mimeData().hasFormat(_MIME_TYPE):
            event.acceptProposedAction()
            # Highlight as drop target
            self.setStyleSheet(
                self.styleSheet() + "border: 2px solid #fff;"
            )
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self._apply_style()
        super().dragLeaveEvent(event)

    def dropEvent(self, event):
        if self._locked:
            event.ignore()
            return
        mime = event.mimeData()
        if not mime.hasFormat(_MIME_TYPE):
            event.ignore()
            return

        data = json.loads(bytes(mime.data(_MIME_TYPE)).decode())
        src_x, src_y = data["x"], data["y"]

        grid = self._grid
        if grid is None:
            event.ignore()
            return

        modifiers = event.modifiers() if hasattr(event, 'modifiers') else event.keyboardModifiers()
        if modifiers & Qt.ControlModifier:
            grid.copy_slot_to(src_x, src_y, self._x, self._y)
        else:
            grid.swap_slots(src_x, src_y, self._x, self._y)

        self._apply_style()
        event.acceptProposedAction()

    def contextMenuEvent(self, event):
        self.right_clicked.emit(self._x, self._y)
        event.accept()


def _make_empty_slot(x: int, y: int) -> dict:
    """Create an empty slot entry at position (x, y)."""
    return {
        "Type": {"InventoryType": "Substance"},
        "Id": "",
        "Amount": 0,
        "MaxAmount": 0,
        "DamageFactor": 0.0,
        "FullyInstalled": True,
        "Index": {"X": x, "Y": y},
    }


class InventoryGrid(QWidget):
    """Grid of inventory slots with editing support."""

    slot_clicked = Signal(int, int)  # x, y of clicked slot

    def __init__(self, title: str = ""):
        super().__init__()
        self._title = title
        self._inventory = None
        self._slots = []  # kept for backward compat
        self._slot_widgets = {}  # (x, y) -> SlotWidget
        self._no_slots_label = None
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        self._grid_widget = QWidget()
        self._grid_layout = QGridLayout(self._grid_widget)
        self._grid_layout.setSpacing(2)
        scroll.setWidget(self._grid_widget)
        outer.addWidget(scroll)

    def set_inventory(self, inventory: dict):
        self._inventory = inventory

        # Clear existing widgets
        for widget in self._slot_widgets.values():
            widget.deleteLater()
        for slot in self._slots:
            if slot not in self._slot_widgets.values():
                slot.deleteLater()
        self._slots.clear()
        self._slot_widgets.clear()

        # Remove any previous "no slots" label
        if hasattr(self, "_no_slots_label") and self._no_slots_label is not None:
            self._no_slots_label.deleteLater()
            self._no_slots_label = None

        width = inventory.get("Width", 6)
        height = inventory.get("Height", 5)
        if width <= 0:
            width = 6
        if height <= 0:
            height = 5

        valid_indices = inventory.get("ValidSlotIndices", [])
        valid_set = {(v["X"], v["Y"]) for v in valid_indices}

        special_slots = inventory.get("SpecialSlots", [])
        special_set = {(s["Index"]["X"], s["Index"]["Y"]) for s in special_slots}

        # If the inventory is essentially empty (no valid slots, no slot data,
        # and no meaningful dimensions), show a message instead of dark grid
        slots_data = inventory.get("Slots", [])
        if not valid_set and not slots_data and not inventory.get("Width") and not inventory.get("Height"):
            self._no_slots_label = QLabel("No slots configured in this inventory")
            self._no_slots_label.setAlignment(Qt.AlignCenter)
            self._no_slots_label.setStyleSheet(
                "color: #888; font-size: 13px; padding: 40px;"
            )
            self._grid_layout.addWidget(self._no_slots_label, 0, 0)
            return

        slots_data = inventory.get("Slots", [])
        slots_by_pos = {}
        for slot in slots_data:
            idx = slot.get("Index", {})
            pos = (idx.get("X", 0), idx.get("Y", 0))
            slots_by_pos[pos] = slot

        for y in range(height):
            for x in range(width):
                pos = (x, y)
                locked = pos not in valid_set
                flat_index = y * width + x

                is_special = pos in special_set
                widget = SlotWidget(flat_index, locked=locked, x=x, y=y, special=is_special)
                widget._grid = self

                if not locked and pos in slots_by_pos:
                    widget.set_slot_data(slots_by_pos[pos])

                widget.clicked.connect(self._on_slot_clicked)
                widget.right_clicked.connect(self._on_slot_right_clicked)

                self._slot_widgets[pos] = widget
                self._slots.append(widget)
                self._grid_layout.addWidget(widget, y, x)

    def get_slot_widget(self, x: int, y: int) -> Optional[SlotWidget]:
        """Get the SlotWidget at grid position (x, y)."""
        return self._slot_widgets.get((x, y))

    def _find_slot_data(self, x: int, y: int) -> Optional[dict]:
        """Find the Slots entry for position (x, y)."""
        if self._inventory is None:
            return None
        for slot in self._inventory.get("Slots", []):
            idx = slot.get("Index", {})
            if idx.get("X") == x and idx.get("Y") == y:
                return slot
        return None

    def _is_valid(self, x: int, y: int) -> bool:
        """Check if position is in ValidSlotIndices."""
        if self._inventory is None:
            return False
        for v in self._inventory.get("ValidSlotIndices", []):
            if v["X"] == x and v["Y"] == y:
                return True
        return False

    def swap_slots(self, src_x: int, src_y: int, dst_x: int, dst_y: int):
        """Swap the contents of two slots in-place, preserving their positions."""
        if src_x == dst_x and src_y == dst_y:
            return

        src_slot = self._find_slot_data(src_x, src_y)
        dst_slot = self._find_slot_data(dst_x, dst_y)

        if src_slot is None:
            src_slot = _make_empty_slot(src_x, src_y)
            self._inventory["Slots"].append(src_slot)
        if dst_slot is None:
            dst_slot = _make_empty_slot(dst_x, dst_y)
            self._inventory["Slots"].append(dst_slot)

        swap_keys = ("Type", "Id", "Amount", "MaxAmount", "DamageFactor", "FullyInstalled")
        for key in swap_keys:
            src_val = copy.deepcopy(src_slot.get(key))
            dst_val = copy.deepcopy(dst_slot.get(key))
            src_slot[key] = dst_val
            dst_slot[key] = src_val

        self._refresh_slot_widget(src_x, src_y)
        self._refresh_slot_widget(dst_x, dst_y)

    def copy_slot_to(self, src_x: int, src_y: int, dst_x: int, dst_y: int):
        """Copy source slot data to target position, preserving target index."""
        src_slot = self._find_slot_data(src_x, src_y)
        if src_slot is None:
            return

        dst_slot = self._find_slot_data(dst_x, dst_y)
        if dst_slot is None:
            dst_slot = _make_empty_slot(dst_x, dst_y)
            self._inventory["Slots"].append(dst_slot)

        for key in ("Type", "Id", "Amount", "MaxAmount", "DamageFactor", "FullyInstalled"):
            if key in src_slot:
                dst_slot[key] = copy.deepcopy(src_slot[key])
        dst_slot["Index"] = {"X": dst_x, "Y": dst_y}

        self._refresh_slot_widget(dst_x, dst_y)

    def _refresh_slot_widget(self, x: int, y: int):
        """Re-render a slot widget from its data."""
        widget = self._slot_widgets.get((x, y))
        if widget is None:
            return
        slot = self._find_slot_data(x, y)
        if slot is not None:
            widget.set_slot_data(slot)
        else:
            widget.clear_slot()

    def _on_slot_clicked(self, x: int, y: int):
        widget = self._slot_widgets.get((x, y))
        if widget is None or widget.is_locked:
            return
        self.slot_clicked.emit(x, y)
        self._open_slot_editor(x, y)

    def _on_slot_right_clicked(self, x: int, y: int):
        self._show_context_menu(x, y)

    def _open_slot_editor(self, x: int, y: int):
        from nmstoolkit.gui.widgets.slot_editor import SlotEditor

        slot = self._find_slot_data(x, y)
        if slot is None:
            slot = _make_empty_slot(x, y)
            self._inventory["Slots"].append(slot)

        editor = SlotEditor(slot, self._inventory, parent=self)
        if editor.exec() == SlotEditor.Accepted:
            widget = self._slot_widgets.get((x, y))
            if widget is not None:
                widget.set_slot_data(slot)

    def _show_context_menu(self, x: int, y: int):
        widget = self._slot_widgets.get((x, y))
        if widget is None:
            return

        menu = QMenu(self)
        locked = widget.is_locked

        if not locked:
            edit_action = menu.addAction("Edit Slot...")
            edit_action.triggered.connect(lambda: self._open_slot_editor(x, y))

            copy_action = menu.addAction("Copy Slot")
            copy_action.triggered.connect(lambda: self.copy_slot(x, y))

            paste_action = menu.addAction("Paste Slot")
            paste_action.setEnabled(get_clipboard_slot() is not None)
            paste_action.triggered.connect(lambda: self.paste_slot(x, y))

            clear_action = menu.addAction("Clear Slot")
            clear_action.triggered.connect(lambda: self.clear_slot(x, y))

            menu.addSeparator()

            max_action = menu.addAction("Max Stack")
            max_action.triggered.connect(lambda: self.max_stack(x, y))

            menu.addSeparator()

            is_special = widget._special
            sc_label = "Remove Supercharged" if is_special else "Set Supercharged"
            sc_action = menu.addAction(sc_label)
            sc_action.triggered.connect(lambda: self.toggle_special(x, y))

            disable_action = menu.addAction("Disable Slot")
            disable_action.triggered.connect(lambda: self.disable_slot(x, y))
        else:
            enable_action = menu.addAction("Enable Slot")
            enable_action.triggered.connect(lambda: self.enable_slot(x, y))

        menu.addSeparator()
        enable_all_action = menu.addAction("Enable All Slots")
        enable_all_action.triggered.connect(self.enable_all_slots)

        # Optimizer (only if there are tech items)
        has_tech = any(
            s.get("Type", {}).get("InventoryType") == "Technology" and s.get("Id")
            for s in (self._inventory or {}).get("Slots", [])
        )
        if has_tech:
            menu.addSeparator()
            opt_action = menu.addAction("Optimize Tech Layout")
            opt_action.triggered.connect(self._optimize_layout)

        menu.popup(widget.mapToGlobal(widget.rect().center()))

    def clear_slot(self, x: int, y: int):
        """Clear the slot at (x, y) -- set Id to empty, Amount to 0."""
        slot = self._find_slot_data(x, y)
        if slot is not None:
            slot["Id"] = ""
            slot["Amount"] = 0
            slot["MaxAmount"] = 0
            widget = self._slot_widgets.get((x, y))
            if widget is not None:
                widget.set_slot_data(slot)

    def max_stack(self, x: int, y: int):
        """Set Amount = MaxAmount for slot at (x, y)."""
        slot = self._find_slot_data(x, y)
        if slot is not None:
            slot["Amount"] = slot.get("MaxAmount", 0)
            widget = self._slot_widgets.get((x, y))
            if widget is not None:
                widget.set_slot_data(slot)

    def copy_slot(self, x: int, y: int):
        """Copy slot data at (x, y) to the module-level clipboard."""
        slot = self._find_slot_data(x, y)
        if slot is not None:
            set_clipboard_slot(slot)

    def paste_slot(self, x: int, y: int):
        """Paste clipboard data to slot at (x, y), preserving position."""
        clipboard = get_clipboard_slot()
        if clipboard is None:
            return

        slot = self._find_slot_data(x, y)
        if slot is None:
            slot = _make_empty_slot(x, y)
            self._inventory["Slots"].append(slot)

        original_index = {"X": x, "Y": y}
        for key in ("Type", "Id", "Amount", "MaxAmount", "DamageFactor", "FullyInstalled"):
            if key in clipboard:
                if isinstance(clipboard[key], dict):
                    slot[key] = copy.deepcopy(clipboard[key])
                else:
                    slot[key] = clipboard[key]
        slot["Index"] = original_index

        widget = self._slot_widgets.get((x, y))
        if widget is not None:
            widget.set_slot_data(slot)

    def enable_slot(self, x: int, y: int):
        """Add position to ValidSlotIndices and create an empty slot entry."""
        if self._inventory is None:
            return

        if not self._is_valid(x, y):
            self._inventory.setdefault("ValidSlotIndices", []).append({"X": x, "Y": y})

        if self._find_slot_data(x, y) is None:
            self._inventory["Slots"].append(_make_empty_slot(x, y))

        widget = self._slot_widgets.get((x, y))
        if widget is not None:
            widget.is_locked = False
            slot = self._find_slot_data(x, y)
            if slot is not None:
                widget.set_slot_data(slot)

    def disable_slot(self, x: int, y: int):
        """Remove position from ValidSlotIndices and remove slot entry."""
        if self._inventory is None:
            return

        self._inventory["ValidSlotIndices"] = [
            v for v in self._inventory["ValidSlotIndices"]
            if not (v["X"] == x and v["Y"] == y)
        ]

        self._inventory["Slots"] = [
            s for s in self._inventory["Slots"]
            if not (s.get("Index", {}).get("X") == x and s.get("Index", {}).get("Y") == y)
        ]

        widget = self._slot_widgets.get((x, y))
        if widget is not None:
            widget.is_locked = True

    def toggle_special(self, x: int, y: int):
        """Toggle supercharged status on a slot."""
        if self._inventory is None:
            return
        if not self._is_valid(x, y):
            return

        special_slots = self._inventory.setdefault("SpecialSlots", [])
        # Check if already special
        for i, s in enumerate(special_slots):
            idx = s.get("Index", {})
            if idx.get("X") == x and idx.get("Y") == y:
                special_slots.pop(i)
                widget = self._slot_widgets.get((x, y))
                if widget is not None:
                    widget._special = False
                    widget._apply_style()
                return

        # Add as special
        special_slots.append({
            "Type": {"InventorySpecialSlotType": "TechBonus"},
            "Index": {"X": x, "Y": y},
        })
        widget = self._slot_widgets.get((x, y))
        if widget is not None:
            widget._special = True
            widget._apply_style()

    def _optimize_layout(self):
        """Run the tech layout optimizer on the current inventory."""
        if self._inventory is None:
            return

        from PySide6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self, "Optimize Tech Layout",
            "Rearrange technology items for maximum adjacency bonuses?\n\n"
            "Non-tech items will not be moved.",
        )
        if reply != QMessageBox.Yes:
            return

        from nmstoolkit.gui.widgets.slot_optimizer import optimize_tech_layout
        optimize_tech_layout(self._inventory, _CATALOGUE)
        self.set_inventory(self._inventory)

    def enable_all_slots(self):
        """Enable every position in the grid."""
        if self._inventory is None:
            return

        width = self._inventory.get("Width", 6)
        height = self._inventory.get("Height", 5)

        for y in range(height):
            for x in range(width):
                if not self._is_valid(x, y):
                    self.enable_slot(x, y)
