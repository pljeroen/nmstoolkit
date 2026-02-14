"""Seed value editor widget."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QPushButton, QWidget

import random


class SeedEditor(QWidget):
    """Editor for NMS seed values (used for ship/multitool/companion appearance)."""

    seed_changed = Signal(str)

    def __init__(self, label: str = "Seed"):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._edit = QLineEdit()
        self._edit.setPlaceholderText("0x...")
        self._edit.textChanged.connect(self.seed_changed.emit)
        layout.addWidget(self._edit)

        randomize = QPushButton("Random")
        randomize.setFixedWidth(60)
        randomize.clicked.connect(self._randomize)
        layout.addWidget(randomize)

    def set_seed(self, value):
        self._edit.blockSignals(True)
        if isinstance(value, list) and len(value) == 2:
            # NMS seed format: [bool, "0x..."]
            self._edit.setText(str(value[1]))
        elif value is None:
            self._edit.setText("")
        else:
            self._edit.setText(str(value))
        self._edit.blockSignals(False)

    def seed(self) -> str:
        return self._edit.text()

    def _randomize(self):
        new_seed = f"0x{random.randint(0, 2**64 - 1):016X}"
        self._edit.setText(new_seed)
