"""JSON tree editor tab — raw view of save data."""

import json

from PySide6.QtCore import Qt, QModelIndex
from PySide6.QtGui import QFont, QShortcut, QKeySequence, QStandardItem, QStandardItemModel, QTextDocument
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTreeView,
    QVBoxLayout,
    QWidget,
)


class JsonEditorTab(QWidget):
    def __init__(self):
        super().__init__()
        self._data = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Horizontal)

        # Tree view (left)
        self._tree = QTreeView()
        self._tree.setHeaderHidden(False)
        self._tree.setAlternatingRowColors(True)
        self._model = QStandardItemModel()
        self._model.setHorizontalHeaderLabels(["Key", "Value", "Type"])
        self._tree.setModel(self._model)
        self._tree.clicked.connect(self._on_tree_click)
        splitter.addWidget(self._tree)

        # Text view (right)
        self._text = QPlainTextEdit()
        self._text.setReadOnly(True)
        font = QFont("Monospace", 10)
        font.setStyleHint(QFont.Monospace)
        self._text.setFont(font)
        splitter.addWidget(self._text)

        splitter.setSizes([300, 700])
        layout.addWidget(splitter)

        # Search bar (hidden by default, shown with Ctrl+F)
        self._search_bar = QWidget()
        search_layout = QHBoxLayout(self._search_bar)
        search_layout.setContentsMargins(4, 2, 4, 2)
        search_layout.addWidget(QLabel("Find:"))
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Search...")
        self._search_input.returnPressed.connect(self._find_next)
        search_layout.addWidget(self._search_input)
        next_btn = QPushButton("Next")
        next_btn.clicked.connect(self._find_next)
        search_layout.addWidget(next_btn)
        prev_btn = QPushButton("Previous")
        prev_btn.clicked.connect(self._find_previous)
        search_layout.addWidget(prev_btn)
        close_btn = QPushButton("X")
        close_btn.setFixedWidth(24)
        close_btn.clicked.connect(self._hide_search_bar)
        search_layout.addWidget(close_btn)
        self._search_bar.hide()
        layout.addWidget(self._search_bar)

        # Keyboard shortcuts
        find_shortcut = QShortcut(QKeySequence.Find, self)
        find_shortcut.activated.connect(self._show_search_bar)
        esc_shortcut = QShortcut(QKeySequence(Qt.Key_Escape), self._search_input)
        esc_shortcut.activated.connect(self._hide_search_bar)

    def set_data(self, data: dict):
        self._data = data
        self._model.clear()
        self._model.setHorizontalHeaderLabels(["Key", "Value", "Type"])
        root = self._model.invisibleRootItem()
        self._populate_tree(root, data)
        self._tree.expandToDepth(0)

        header = self._tree.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)

        # Show full JSON in text area
        self._text.setPlainText(json.dumps(data, indent=2, ensure_ascii=False))

    def _populate_tree(self, parent: QStandardItem, data, max_depth: int = 3, depth: int = 0):
        if isinstance(data, dict):
            for key, value in data.items():
                key_item = QStandardItem(str(key))
                key_item.setEditable(False)
                key_item.setData(value, Qt.UserRole)

                if isinstance(value, dict):
                    val_item = QStandardItem(f"{{{len(value)} keys}}")
                    type_item = QStandardItem("object")
                    parent.appendRow([key_item, val_item, type_item])
                    if depth < max_depth:
                        self._populate_tree(key_item, value, max_depth, depth + 1)
                elif isinstance(value, list):
                    val_item = QStandardItem(f"[{len(value)} items]")
                    type_item = QStandardItem("array")
                    parent.appendRow([key_item, val_item, type_item])
                    if depth < max_depth:
                        self._populate_tree(key_item, value, max_depth, depth + 1)
                else:
                    val_item = QStandardItem(str(value))
                    val_item.setEditable(False)
                    type_item = QStandardItem(type(value).__name__)
                    type_item.setEditable(False)
                    parent.appendRow([key_item, val_item, type_item])

        elif isinstance(data, list):
            for i, value in enumerate(data):
                key_item = QStandardItem(f"[{i}]")
                key_item.setEditable(False)
                key_item.setData(value, Qt.UserRole)

                if isinstance(value, dict):
                    val_item = QStandardItem(f"{{{len(value)} keys}}")
                    type_item = QStandardItem("object")
                    parent.appendRow([key_item, val_item, type_item])
                    if depth < max_depth:
                        self._populate_tree(key_item, value, max_depth, depth + 1)
                elif isinstance(value, list):
                    val_item = QStandardItem(f"[{len(value)} items]")
                    type_item = QStandardItem("array")
                    parent.appendRow([key_item, val_item, type_item])
                    if depth < max_depth:
                        self._populate_tree(key_item, value, max_depth, depth + 1)
                else:
                    val_item = QStandardItem(str(value))
                    val_item.setEditable(False)
                    type_item = QStandardItem(type(value).__name__)
                    type_item.setEditable(False)
                    parent.appendRow([key_item, val_item, type_item])

    def _on_tree_click(self, index: QModelIndex):
        item = self._model.itemFromIndex(index.siblingAtColumn(0))
        if item is None:
            return
        data = item.data(Qt.UserRole)
        if data is not None:
            self._text.setPlainText(json.dumps(data, indent=2, ensure_ascii=False))

    def _show_search_bar(self):
        """Show the find bar and focus the input."""
        self._search_bar.show()
        self._search_input.setFocus()
        self._search_input.selectAll()

    def _hide_search_bar(self):
        """Hide the find bar."""
        self._search_bar.hide()

    def _find_next(self) -> bool:
        """Find the next occurrence of the search text. Returns True if found."""
        text = self._search_input.text()
        if not text:
            return False
        return self._text.find(text)

    def _find_previous(self) -> bool:
        """Find the previous occurrence of the search text. Returns True if found."""
        text = self._search_input.text()
        if not text:
            return False
        return self._text.find(text, QTextDocument.FindFlag.FindBackward)
