"""Atlas HTML export — generates a self-contained HTML atlas of discoveries and bases."""

from nmstoolkit.gui.tabs.bases_tab import _decode_galactic_address


def _escape(text: str) -> str:
    """Escape HTML special characters."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def generate_atlas_html(records: list, bases: list) -> str:
    """Generate a self-contained HTML atlas from discovery records and bases.

    Args:
        records: List of discovery record dicts (DD, OWS, DM structure).
        bases: List of base dicts (Name, BaseType, Objects, GalacticAddress).

    Returns:
        Complete HTML string with inline CSS, no external dependencies.
    """
    # Categorize discoveries
    systems = []
    planets = []
    other = []
    for record in records:
        dd = record.get("DD", {})
        dm = record.get("DM", {})
        disc_type = dd.get("DT", "")
        name = ""
        if isinstance(dm, dict):
            name = dm.get("CN", "")
        if not name:
            name = dd.get("CN", "") or dd.get("N", "") or ""
        address = dd.get("UA", 0)
        addr_str = _decode_galactic_address(address)
        entry = {"name": name or "(Unknown)", "address": addr_str, "type": disc_type}

        if disc_type == "SolarSystem":
            systems.append(entry)
        elif disc_type == "Planet":
            planets.append(entry)
        else:
            other.append(entry)

    # Build HTML sections
    sections = []

    if systems:
        rows = "\n".join(
            f'<tr><td>{_escape(s["name"])}</td><td>{_escape(s["address"])}</td></tr>'
            for s in systems
        )
        sections.append(
            f"<h2>Solar Systems ({len(systems)})</h2>\n"
            f"<table><tr><th>Name</th><th>Address</th></tr>\n{rows}</table>"
        )

    if planets:
        rows = "\n".join(
            f'<tr><td>{_escape(p["name"])}</td><td>{_escape(p["address"])}</td></tr>'
            for p in planets
        )
        sections.append(
            f"<h2>Planets ({len(planets)})</h2>\n"
            f"<table><tr><th>Name</th><th>Address</th></tr>\n{rows}</table>"
        )

    if other:
        rows = "\n".join(
            f'<tr><td>{_escape(o["type"])}</td><td>{_escape(o["name"])}</td>'
            f'<td>{_escape(o["address"])}</td></tr>'
            for o in other
        )
        sections.append(
            f"<h2>Other Discoveries ({len(other)})</h2>\n"
            f"<table><tr><th>Type</th><th>Name</th><th>Address</th></tr>\n{rows}</table>"
        )

    if bases:
        rows = "\n".join(
            f'<tr><td>{_escape(b.get("Name", "") or "(Unnamed)")}</td>'
            f'<td>{_escape(_get_base_type(b))}</td>'
            f"<td>{len(b.get('Objects', []))}</td></tr>"
            for b in bases
        )
        sections.append(
            f"<h2>Bases ({len(bases)})</h2>\n"
            f"<table><tr><th>Name</th><th>Type</th><th>Parts</th></tr>\n{rows}</table>"
        )

    if not sections:
        sections.append("<p>No discoveries or bases to display.</p>")

    body = "\n".join(sections)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Atlas Export</title>
<style>
body {{
    background: #1a1a2e; color: #e0e0e0; font-family: 'Segoe UI', sans-serif;
    margin: 0; padding: 20px;
}}
h1 {{ color: #00d4ff; border-bottom: 2px solid #16213e; padding-bottom: 10px; }}
h2 {{ color: #0f3460; background: #16213e; padding: 8px 12px; border-radius: 4px; }}
table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
th {{ background: #16213e; color: #00d4ff; padding: 8px 12px; text-align: left; }}
td {{ padding: 6px 12px; border-bottom: 1px solid #16213e; }}
tr:hover {{ background: #16213e; }}
p {{ color: #888; }}
</style>
</head>
<body>
<h1>Atlas Export</h1>
<p>Systems: {len(systems)} | Planets: {len(planets)} | Other: {len(other)} | Bases: {len(bases)}</p>
{body}
</body>
</html>"""


def _get_base_type(base: dict) -> str:
    """Extract base type string."""
    bt = base.get("BaseType", {})
    if isinstance(bt, dict):
        return bt.get("PersistentBaseTypes", "")
    return str(bt) if bt else ""
