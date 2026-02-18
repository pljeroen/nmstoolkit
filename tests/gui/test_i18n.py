"""Tests for runtime UI translation infrastructure."""

from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QVBoxLayout, QWidget


def _qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_widget_translation_round_trip_preserves_source_text():
    _qapp()
    root = QWidget()
    layout = QVBoxLayout(root)
    label = QLabel("Main")
    button = QPushButton("Reload")
    layout.addWidget(label)
    layout.addWidget(button)

    from nmstoolkit.gui.i18n import apply_ui_translation, set_ui_language

    set_ui_language("dutch")
    apply_ui_translation(root)
    assert label.text() == "Overzicht"
    assert button.text() == "Herladen"

    # Switching again should translate from original English source, not NL output.
    set_ui_language("german")
    apply_ui_translation(root)
    assert label.text() == "Start"
    assert button.text() == "Neu laden"


def test_tab_text_translates_from_original_source_each_switch():
    _qapp()
    from PySide6.QtWidgets import QTabWidget

    tabs = QTabWidget()
    tabs.addTab(QWidget(), "Companions")

    from nmstoolkit.gui.i18n import apply_ui_translation, set_ui_language

    set_ui_language("dutch")
    apply_ui_translation(tabs)
    assert tabs.tabText(0) == "Metgezellen"

    set_ui_language("german")
    apply_ui_translation(tabs)
    assert tabs.tabText(0) == "Begleiter"
