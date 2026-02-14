"""Dropdown selector for enum-like values."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox


class EnumSelector(QComboBox):
    """Dropdown for selecting from a fixed set of values."""

    selection_changed = Signal(str)

    def __init__(self, options: list[str] = None):
        super().__init__()
        if options:
            self.addItems(options)
        self.currentTextChanged.connect(self.selection_changed.emit)

    def set_value(self, value: str):
        index = self.findText(str(value))
        if index >= 0:
            self.setCurrentIndex(index)
