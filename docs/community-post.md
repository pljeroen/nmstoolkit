# NMS Toolkit — No Man's Sky Save Editor

Full desktop save editor for No Man's Sky with broad tab coverage, automated tests, and continuous iteration.

**GitHub**: https://github.com/pljeroen/nmstoolkit (MIT, free, open source)
**Download**: Windows .exe on the Releases page — no install required

## What It Does

Visual editor for NMS save files: inventories (exosuit/ships/multitools/freighter/vehicles) with drag-and-drop, ship/multitool/companion management with cross-save vault, 3D corvette builder rendering actual game meshes via OpenGL, settlement editor, base library with budget tracking and export/import, expedition tools with offline replay, discovery browser with constellation path optimizer, galaxy atlas HTML export, and more.

## Development Notes

Architecture and feature direction are user-led. AI tooling accelerates implementation, testing, and refactors. Key technical areas include reverse-engineering save/asset formats, OpenGL rendering from extracted meshes, and path optimization for constellation editing.

## Tech

Python 3.9+, PySide6, PyOpenGL, hexagonal architecture, Nuitka standalone builds, GitHub Actions CI/CD.

## Security

Reads/writes local save files only. No network access, no data transmission, no credentials. Full source on GitHub.

## Try It

```
git clone https://github.com/pljeroen/nmstoolkit.git
pip install -e ".[dev]"
python -m nmstoolkit.app
```

Feedback welcome on GitHub.
