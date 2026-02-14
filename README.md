# NMS Toolkit

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Build](https://img.shields.io/github/actions/workflow/status/pljeroen/nmstoolkit/build-release.yml?label=build)](https://github.com/pljeroen/nmstoolkit/actions)
[![Release](https://img.shields.io/github/v/release/pljeroen/nmstoolkit?include_prereleases&label=release)](https://github.com/pljeroen/nmstoolkit/releases)
[![Status: Experimental](https://img.shields.io/badge/status-experimental-orange.svg)]()

> **WARNING: This software is experimental and under active development.**
> **Always back up your save files before using this tool.**
> **Saves are located in `%APPDATA%/HelloGames/NMS/` (Windows) or `~/.local/share/Steam/steamapps/compatdata/275850/` (Linux/Proton).**
> **The authors are not responsible for corrupted or lost save data.**

No Man's Sky save editor and toolkit.

## Features

- Full inventory editing (exosuit, ships, multitools, freighter, vehicles)
- Companion/pet editing with gene modification support
- Squadron, frigate, and settlement management
- Base storage viewing
- Expedition progress and offline replay
- Recipe finder with refiner recipe unlock
- Fish finder reference guide
- Milestone and reputation tracking
- Discovery browser
- Game icon extraction from PAK files
- Drag-and-drop inventory slot management

## Installation

```bash
pip install -e ".[dev]"
```

## Usage

```bash
nmstoolkit
```

Or run directly:

```bash
python -c "from nmstoolkit.app import main; main()"
```

## Development

```bash
# Run tests
python -m pytest tests/ -q

# Run with coverage
python -m pytest tests/ --cov=nmstoolkit
```

## License

MIT License - see [LICENSE](LICENSE) for details.
