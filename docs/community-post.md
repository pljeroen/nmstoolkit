# NMS Toolkit — No Man's Sky Save Editor, Built in a Day with Claude Code

Full desktop save editor for No Man's Sky — 20 editor tabs, 630 tests, 21K lines of Python, built from scratch in one day.

**GitHub**: https://github.com/pljeroen/nmstoolkit (MIT, free, open source)
**Download**: Windows .exe on the Releases page — no install required

## What It Does

Visual editor for NMS save files: inventories (exosuit/ships/multitools/freighter/vehicles) with drag-and-drop, ship/multitool/companion management with cross-save vault, 3D corvette builder rendering actual game meshes via OpenGL, settlement editor, base library with budget tracking and export/import, expedition tools with offline replay, discovery browser with constellation path optimizer, galaxy atlas HTML export, and more.

## How Claude Helped

I directed architecture and features. Claude Code wrote every line — source, tests, widgets. The harder wins: reverse-engineering the NMS save format (LZ4 blocks, obfuscated keys, binary geometry parsing), building an OpenGL 3.3 mesh renderer from PAK-extracted models, and a nearest-neighbor + 2-opt path optimizer that cuts constellation travel distance by 91%.

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
