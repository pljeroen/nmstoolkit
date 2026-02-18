"""UI localization helpers for runtime language switching."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QAbstractButton,
    QComboBox,
    QGroupBox,
    QLabel,
    QLineEdit,
    QMenu,
    QMenuBar,
    QStatusBar,
    QTabWidget,
    QTableWidget,
    QTreeWidget,
    QWidget,
)

from nmstoolkit.paths import resource_dir

_LANGUAGE_TO_CATALOGUE = {
    "english": "en",
    "german": "de",
    "dutch": "nl",
}


class UiI18n:
    """Runtime UI translation store and widget retranslator."""

    def __init__(self) -> None:
        self._language = "english"
        self._catalogue: Dict[str, str] = {}

    def set_language(self, language: str) -> None:
        token = (language or "english").strip().lower()
        self._language = token or "english"
        self._catalogue = self._load_catalogue(self._language)

    def translate(self, text: str) -> str:
        if not text:
            return text
        return self._catalogue.get(text, text)

    def apply_to_widget(self, root: QWidget) -> None:
        if root is None:
            return
        self._translate_widget(root)
        for widget in root.findChildren(QWidget):
            self._translate_widget(widget)

    def apply_to_menu_bar(self, menu_bar: QMenuBar) -> None:
        if menu_bar is None:
            return
        for action in menu_bar.actions():
            self._translate_action(action)

    def _load_catalogue(self, language: str) -> Dict[str, str]:
        code = _LANGUAGE_TO_CATALOGUE.get(language, "en")
        path = resource_dir() / "i18n" / f"{code}.json"
        if not path.exists():
            return {}
        try:
            parsed = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
        if not isinstance(parsed, dict):
            return {}
        strings = parsed.get("strings", {})
        if not isinstance(strings, dict):
            return {}
        return {
            str(k): str(v)
            for k, v in strings.items()
            if isinstance(k, str) and isinstance(v, str)
        }

    def _translate_widget(self, widget: QWidget) -> None:
        window_title = widget.windowTitle()
        if window_title:
            source = _source_text(widget, "window_title", window_title)
            widget.setWindowTitle(self.translate(source))

        if isinstance(widget, QLabel):
            source = _source_text(widget, "label_text", widget.text())
            widget.setText(self.translate(source))
            if widget.toolTip():
                source_tip = _source_text(widget, "label_tooltip", widget.toolTip())
                widget.setToolTip(self.translate(source_tip))
            return

        if isinstance(widget, QAbstractButton):
            source = _source_text(widget, "button_text", widget.text())
            widget.setText(self.translate(source))
            if widget.toolTip():
                source_tip = _source_text(widget, "button_tooltip", widget.toolTip())
                widget.setToolTip(self.translate(source_tip))
            return

        if isinstance(widget, QGroupBox):
            source = _source_text(widget, "group_title", widget.title())
            widget.setTitle(self.translate(source))
            return

        if isinstance(widget, QLineEdit):
            if widget.placeholderText():
                source = _source_text(widget, "lineedit_placeholder", widget.placeholderText())
                widget.setPlaceholderText(self.translate(source))
            return

        if isinstance(widget, QComboBox):
            sources = widget.property("_i18n_combo_sources")
            if not isinstance(sources, list) or len(sources) != widget.count():
                sources = [widget.itemText(idx) for idx in range(widget.count())]
                widget.setProperty("_i18n_combo_sources", sources)
            for idx, source in enumerate(sources):
                widget.setItemText(idx, self.translate(source))
            if widget.placeholderText():
                source = _source_text(widget, "combo_placeholder", widget.placeholderText())
                widget.setPlaceholderText(self.translate(source))
            return

        if isinstance(widget, QTabWidget):
            sources = widget.property("_i18n_tab_sources")
            if not isinstance(sources, list) or len(sources) != widget.count():
                sources = [widget.tabText(idx) for idx in range(widget.count())]
                widget.setProperty("_i18n_tab_sources", sources)
            for idx, source in enumerate(sources):
                widget.setTabText(idx, self.translate(source))
            return

        if isinstance(widget, QTableWidget):
            for idx in range(widget.columnCount()):
                item = widget.horizontalHeaderItem(idx)
                if item is not None:
                    source = item.data(Qt.ItemDataRole.UserRole + 777)
                    if not isinstance(source, str):
                        source = item.text()
                        item.setData(Qt.ItemDataRole.UserRole + 777, source)
                    item.setText(self.translate(source))
            for idx in range(widget.rowCount()):
                item = widget.verticalHeaderItem(idx)
                if item is not None:
                    source = item.data(Qt.ItemDataRole.UserRole + 777)
                    if not isinstance(source, str):
                        source = item.text()
                        item.setData(Qt.ItemDataRole.UserRole + 777, source)
                    item.setText(self.translate(source))
            return

        if isinstance(widget, QTreeWidget):
            for idx in range(widget.columnCount()):
                source = widget.headerItem().data(idx, Qt.ItemDataRole.UserRole + 777)
                if not isinstance(source, str):
                    source = widget.headerItem().text(idx)
                    widget.headerItem().setData(idx, Qt.ItemDataRole.UserRole + 777, source)
                widget.headerItem().setText(idx, self.translate(source))
            return

        if isinstance(widget, QMenu):
            source = _source_text(widget, "menu_title", widget.title())
            widget.setTitle(self.translate(source))
            for action in widget.actions():
                self._translate_action(action)
            return

        if isinstance(widget, QStatusBar):
            # Keep current status message readable in selected language when static.
            message = widget.currentMessage()
            if message:
                source = _source_text(widget, "status_message", message)
                widget.showMessage(self.translate(source))

    def _translate_action(self, action: QAction) -> None:
        text = action.text()
        if text:
            source = _source_text(action, "action_text", text)
            action.setText(self.translate(source))
        tip = action.statusTip()
        if tip:
            source_tip = _source_text(action, "action_statustip", tip)
            action.setStatusTip(self.translate(source_tip))
        tooltip = action.toolTip()
        if tooltip:
            source_tooltip = _source_text(action, "action_tooltip", tooltip)
            action.setToolTip(self.translate(source_tooltip))
        menu = action.menu()
        if menu is not None:
            source_menu = _source_text(menu, "menu_title", menu.title())
            menu.setTitle(self.translate(source_menu))
            for child_action in menu.actions():
                self._translate_action(child_action)


def _source_text(obj, suffix: str, current: str) -> str:
    prop = f"_i18n_source_{suffix}"
    source = obj.property(prop)
    if isinstance(source, str) and source:
        return source
    if not current:
        return ""
    obj.setProperty(prop, current)
    return current


_UI_I18N = UiI18n()


def set_ui_language(language: str) -> None:
    _UI_I18N.set_language(language)


def ui_tr(text: str) -> str:
    return _UI_I18N.translate(text)


def apply_ui_translation(root: QWidget) -> None:
    _UI_I18N.apply_to_widget(root)


def apply_menu_translation(menu_bar: QMenuBar) -> None:
    _UI_I18N.apply_to_menu_bar(menu_bar)


def available_ui_languages() -> list[str]:
    """Return UI language tokens backed by bundled i18n catalogues."""
    i18n_dir = resource_dir() / "i18n"
    available = []
    for token, code in _LANGUAGE_TO_CATALOGUE.items():
        if (i18n_dir / f"{code}.json").exists():
            available.append(token)
    if "english" not in available:
        available.insert(0, "english")
    return available
