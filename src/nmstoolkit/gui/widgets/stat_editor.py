"""Numeric stat editor widget."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QSpinBox


class StatEditor(QSpinBox):
    """Spin box for editing numeric stats."""

    value_changed = Signal(int)

    def __init__(self, label: str = "", minimum: int = 0, maximum: int = 99999):
        super().__init__()
        self.setRange(minimum, maximum)
        self.valueChanged.connect(self.value_changed.emit)

    def set_value(self, value):
        self.blockSignals(True)
        self.setValue(int(value) if value is not None else 0)
        self.blockSignals(False)
