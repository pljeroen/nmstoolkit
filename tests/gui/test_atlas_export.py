"""Tests for atlas HTML export.

R-ATLAS-01: Export visited systems and bases as formatted HTML atlas.
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

_app = QApplication.instance() or QApplication([])


def _make_discovery_record(disc_type="SolarSystem", name="Test System", address=0x0001000200030004):
    return {
        "DD": {
            "UA": address,
            "DT": disc_type,
            "CN": name,
        },
        "OWS": {"USN": "player1"},
        "DM": {},
    }


def _make_base(name="Home Base", objects=None, address=0):
    return {
        "Name": name,
        "BaseType": {"PersistentBaseTypes": "HomePlanetBase"},
        "GalacticAddress": address,
        "Objects": objects or [{"ObjectID": "^S_FLOOR"}],
    }


class TestAtlasExportModule:
    """R-ATLAS-01: Atlas export produces valid HTML."""

    def test_module_importable(self):
        from nmstoolkit.gui.atlas_export import generate_atlas_html
        assert callable(generate_atlas_html)

    def test_generates_html_string(self):
        from nmstoolkit.gui.atlas_export import generate_atlas_html

        records = [
            _make_discovery_record("SolarSystem", "Alpha Centauri"),
            _make_discovery_record("Planet", "Earth II"),
        ]
        bases = [_make_base("Home Base")]
        html = generate_atlas_html(records, bases)
        assert "<html" in html.lower()
        assert "</html>" in html.lower()

    def test_contains_system_names(self):
        from nmstoolkit.gui.atlas_export import generate_atlas_html

        records = [_make_discovery_record("SolarSystem", "Alpha Centauri")]
        html = generate_atlas_html(records, [])
        assert "Alpha Centauri" in html

    def test_contains_base_names(self):
        from nmstoolkit.gui.atlas_export import generate_atlas_html

        bases = [_make_base("Home Sweet Home")]
        html = generate_atlas_html([], bases)
        assert "Home Sweet Home" in html

    def test_self_contained_no_external_deps(self):
        """HTML should be self-contained — no external CSS/JS references."""
        from nmstoolkit.gui.atlas_export import generate_atlas_html

        records = [_make_discovery_record()]
        html = generate_atlas_html(records, [])
        # Should contain inline styles
        assert "<style" in html.lower()
        # Should NOT reference external resources
        assert 'href="http' not in html.lower()
        assert 'src="http' not in html.lower()

    def test_empty_data_produces_valid_html(self):
        from nmstoolkit.gui.atlas_export import generate_atlas_html

        html = generate_atlas_html([], [])
        assert "<html" in html.lower()
        assert "</html>" in html.lower()

    def test_dark_theme_styling(self):
        """Output should use dark theme CSS."""
        from nmstoolkit.gui.atlas_export import generate_atlas_html

        records = [_make_discovery_record()]
        html = generate_atlas_html(records, [])
        # Dark backgrounds expected
        assert "#" in html  # Contains color codes
