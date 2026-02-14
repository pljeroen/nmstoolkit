# NMS Toolkit

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
