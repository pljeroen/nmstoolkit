# NMS Toolkit

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-610%20passing-brightgreen.svg)]()
[![Architecture](https://img.shields.io/badge/architecture-hexagonal-purple.svg)]()
[![Build](https://img.shields.io/github/actions/workflow/status/pljeroen/nmstoolkit/build-release.yml?label=build)](https://github.com/pljeroen/nmstoolkit/actions)
[![Release](https://img.shields.io/github/v/release/pljeroen/nmstoolkit?include_prereleases&label=release)](https://github.com/pljeroen/nmstoolkit/releases)
[![Status: Experimental](https://img.shields.io/badge/status-experimental-orange.svg)]()

> **WARNING: This software is experimental and under active development.**
> **Always back up your save files before using this tool.**
> **Saves are located in `%APPDATA%/HelloGames/NMS/` (Windows) or `~/.local/share/Steam/steamapps/compatdata/275850/` (Linux/Proton).**
> **The authors are not responsible for corrupted or lost save data.**

No Man's Sky save editor and toolkit.

## Features

- Full inventory editing (exosuit, ships, multitools, freighter, vehicles, exocraft) with unsigned 32-bit Units support
- Companion/pet editing with gene modification (dynamic trait list, add/remove genes)
- Squadron, frigate, and corvette management
- Settlement editing with seed-based ownership, stat write-back, production output, race/address/buildings
- Base part budget table with per-base part counts, wire counts, and sortable columns
- Base library — save, browse, and swap bases from a persistent local library
- Base export/import as portable JSON files
- Fossil tracker — pieces across inventories and assembled displays in bases
- Expedition progress, reward filter by expedition, unlock all rewards, offline replay, Twitch/Platform rewards
- Account data editing (account-wide settings)
- 3D corvette builder with game mesh rendering (PyOpenGL)
- Recipe finder with refiner recipe unlock
- Fish finder reference guide
- Milestone and reputation tracking (Gek, Vy'keen, Korvax, guilds)
- Discovery browser with hex address fallback for unnamed entries
- Constellation editor — optimize, reset, backup/restore star map travel lines (NN + 2-opt path optimizer)
- Raw JSON editor for direct save data manipulation
- Game icon extraction and corvette model extraction from PAK files
- Drag-and-drop inventory slot management with adjacency optimization

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

---

## NMS File Formats and Data Architecture

This section documents how No Man's Sky stores its data and how this toolkit reads and writes it. If you're building your own NMS tools, this is the reference you need.

### Save Files (.hg)

Save files live in:
- **Windows**: `%APPDATA%/HelloGames/NMS/st_<steamid>/`
- **Linux/Proton**: `~/.local/share/Steam/steamapps/compatdata/275850/pfx/drive_c/users/steamuser/AppData/Roaming/HelloGames/NMS/st_<steamid>/`

Each profile directory contains:
- `save.hg`, `save2.hg` ... `save15.hg` — save slots (slot 1 = `save.hg`, slot N = `saveN.hg`)
- `mf_save.hg`, `mf_save2.hg` ... — corresponding metadata files
- `accountdata.hg` — account-level data (plain JSON, not compressed)

#### .hg LZ4 Block Format

Save files (except `accountdata.hg`) use a custom LZ4 block compression format:

```
[Block 1][Block 2]...[Block N]

Each block:
  Magic number    4 bytes  little-endian  0xFEEDA1E5
  Compressed size 4 bytes  little-endian
  Uncompressed sz 4 bytes  little-endian  (512KB = 0x80000, except last block)
  Padding         4 bytes  (zeros)
  LZ4 data        <compressed_size> bytes
```

Decompressed content is JSON with a trailing null byte. The JSON keys are obfuscated (3-character codes). A mapping file (`jsonmap.txt`) translates between obfuscated and readable keys:

```
F2P → Version
6f= → PlayerStateData
;l5 → Inventory
:No → Slots
b2n → Id
1o9 → Amount
```

#### Save JSON Structure (readable keys)

```
{
  "Version": 46002,
  "Platform": "PC",
  "ActiveContext": "Main",
  "BaseContext": {
    "PlayerStateData": {
      "Inventory": { ... },          // Exosuit general
      "Inventory_TechOnly": { ... }, // Exosuit technology
      "Inventory_Cargo": { ... },    // Exosuit cargo
      "ShipInventory": { ... },
      "WeaponInventory": { ... },
      "FreighterInventory": { ... },
      ...
      "ShipOwnership": [ ... ],      // Array of owned ships
      "WeaponOwnership": [ ... ],    // Array of owned multitools
      ...
    }
  },
  "ExpeditionContext": { ... }       // Same structure, expedition save
}
```

#### Inventory Format

Every inventory (exosuit, ship, multitool, freighter, vehicle) follows the same structure:

```json
{
  "Slots": [
    {
      "Type": { "InventoryType": "Substance" },
      "Id": "FUEL1",
      "Amount": 250,
      "MaxAmount": 250,
      "DamageFactor": 0,
      "Index": { "X": 0, "Y": 0 }
    }
  ],
  "ValidSlotIndices": [
    { "X": 0, "Y": 0 },
    { "X": 1, "Y": 0 }
  ],
  "SpecialSlots": [
    {
      "Type": { "InventorySpecialSlotType": "TechBonus" },
      "Index": { "X": 0, "Y": 0 }
    }
  ],
  "Width": 6,
  "Height": 4
}
```

**Inventory types**: `Substance`, `Product`, `Technology`

**Special slots** (supercharged): positions in `SpecialSlots` with type `TechBonus` receive an adjacency bonus multiplier. Exosuit tech inventories typically have 3, ships have 4.

**Item ID prefixes in saves**:
- `^` prefix: marks installed (non-removable) technologies (e.g., `^LASER`, `^YOURSHIP_LAUNCH`)
- `YOURSHIP_*`, `YOURSUIT_*`, `YOURMULTI_*`, `YOURFREIG_*`, `YOURVEHIC_*`: installed base technologies. These are inventory-specific aliases that don't appear in the technology table. Map them to catalogue IDs by stripping the prefix (e.g., `YOURSHIP_LASER` → `LASER`, `YOURSHIP_PULSEDRIVE` → `SHIPJUMP1`)
- `UP_*`, `UA_*`, `U_*`: upgrade modules with tier digits (e.g., `UP_LASER1`, `UA_HYP3`). Map to base tech by prefix (e.g., `UP_LASER` → `LASER`, `UA_HYP` → `HYPERDRIVE`)
- `#nnnnn` suffix: procedural generation seed (e.g., `^UP_BOLT4#52847`). Strip for icon/catalogue lookup

### Game Data Files (.pak)

NMS stores game data in PSARC archives (`.pak` files) in the `GAMEDATA/PCBANKS/` directory. The relevant PAK files:

| PAK File | Contents |
|----------|----------|
| `NMSARC.Precache.pak` | Game tables: products, substances, technologies, recipes, seasons, proc tech |
| `NMSARC.MetadataEtc.pak` | Language/locale files |
| `NMSARC.TexUI.pak` | UI textures including all item/technology icons (DDS format) |

#### PAK Format (PSARC)

Standard PSARC archives — no encryption, no custom format. Use any PSARC reader (we use [hgpaktool](https://github.com/monkeyman192/hgpaktool)).

#### MBIN → EXML Conversion

Game tables inside PAK files are in `.mbin` format (compiled binary). Convert to `.exml` (XML) using [MBINCompiler](https://github.com/monkeyman192/MBINCompiler):

```bash
MBINCompiler.exe input.mbin    # Produces input.MXML (EXML format)
```

On Linux, run MBINCompiler through Wine — the adapter handles this automatically.

#### EXML Structure

EXML files use a flat `Property` tree with `name`/`value` attributes:

```xml
<Data template="cGcProductTable">
  <Property name="Table">
    <Property value="GcProductData.xml">
      <Property name="ID" value="FUEL1" />
      <Property name="Name" value="UI_FUEL1_NAME" />
      <Property name="BaseValue" value="6" />
      <Property name="Icon" value="GcResource.xml">
        <Property name="Filename" value="TEXTURES/UI/FRONTEND/ICONS/SUBSTANCES/SUBSTANCE.FUEL.1.DDS" />
      </Property>
      <Property name="Category" value="GcRealitySubstanceCategory.xml">
        <Property name="SubstanceCategory" value="Fuel" />
      </Property>
      <Property name="Type" value="GcProductCategory.xml">
        <Property name="ProductCategory" value="Consumable" />
      </Property>
      <Property name="Requirements">
        <Property value="GcTechnologyRequirement.xml">
          <Property name="ID" value="CARBON" />
          <Property name="Amount" value="50" />
        </Property>
      </Property>
    </Property>
  </Property>
</Data>
```

Key patterns:
- Simple fields: `<Property name="ID" value="FUEL1" />`
- Nested typed objects: `<Property name="Icon" value="GcResource.xml">` with children
- Lists: Parent `<Property name="Table">` containing entries with `value="GcTypeName"` or `_index` attributes
- Locale references: Name/description fields contain locale keys (e.g., `UI_FUEL1_NAME`) resolved from language files

#### Game Tables

The tables extracted and their MBIN paths within `NMSARC.Precache.pak`:

| Table | MBIN Path | Template |
|-------|-----------|----------|
| Products | `metadata/reality/tables/nms_reality_gcproducttable.mbin` | `cGcProductTable` |
| Substances | `metadata/reality/tables/nms_reality_gcsubstancetable.mbin` | `cGcSubstanceTable` |
| Technologies | `metadata/reality/tables/nms_reality_gctechnologytable.mbin` | `cGcTechnologyTable` |
| Proc Tech | `metadata/reality/tables/nms_reality_gcproceduraltechnologytable.mbin` | `cGcProceduralTechnologyTable` |
| Recipes | `metadata/reality/tables/nms_reality_gcrecipetable.mbin` | `cGcRecipeTable` |
| Seasons | `metadata/reality/tables/historicalseasondatatable.mbin` | `cGcHistoricalSeasonDataTable` |

**Procedural technology** entries reference a base technology `Template` field. Their icons come from the base tech (e.g., proc tech `UP_LASER1` has template `LASER`, so use `LASER`'s icon).

#### Language/Locale Files

Locale strings are split across multiple files in `NMSARC.MetadataEtc.pak`:

```
language/nms_loc1_english.mbin
language/nms_loc4_english.mbin
language/nms_loc5_english.mbin
language/nms_loc6_english.mbin
language/nms_loc7_english.mbin
language/nms_loc8_english.mbin
language/nms_loc9_english.mbin
language/nms_update3_english.mbin
```

Each is a `cTkLocalisationTable` with `Id`/`English` pairs. Merge all files to get complete coverage. Replace `english` with your target language code for localization.

### Icon Extraction Pipeline

Icons are DDS textures stored in `NMSARC.TexUI.pak` under `TEXTURES/UI/FRONTEND/ICONS/`. The full pipeline:

```
NMSARC.TexUI.pak
  → Extract all DDS files under TEXTURES/UI/FRONTEND/ICONS/
  → Convert DDS → PNG thumbnails (64x64, via Pillow)
  → Cache PNGs to disk (flat filenames, e.g. textures_ui_frontend_icons_substances_substance.fuel.1.png)
  → Build icon_map.json: { "FUEL1": "textures/ui/frontend/icons/substances/substance.fuel.1.dds", ... }
```

**Icon map building**: Match catalogue items to DDS files by normalizing the `icon` field from the catalogue entry (strip path separators and extension, lowercase) against DDS basenames. Both exact and fuzzy matching are used.

**Icon resolution at runtime** (priority order):
1. Exact match in `icon_map.json`
2. Strip `#nnnnn` procedural suffix, retry icon_map
3. Catalogue lookup (exact item ID)
4. Catalogue lookup with stripped procedural suffix
5. `YOUR*` prefix resolution → lookup resolved ID
6. `UP_`/`UA_`/`U_` upgrade prefix resolution → lookup resolved ID

### Data Pipeline Summary

```
NMS Install
├── GAMEDATA/PCBANKS/
│   ├── NMSARC.Precache.pak ──→ Extract MBINs ──→ MBINCompiler ──→ EXML ──→ Parse tables
│   │                                                                         ├── Products
│   │                                                                         ├── Substances
│   │                                                                         ├── Technologies
│   │                                                                         ├── Proc Tech
│   │                                                                         ├── Recipes
│   │                                                                         └── Seasons
│   │
│   ├── NMSARC.MetadataEtc.pak ──→ Extract MBINs ──→ MBINCompiler ──→ Locale strings
│   │
│   └── NMSARC.TexUI.pak ──→ Extract DDS ──→ Pillow DDS→PNG ──→ Icon cache
│
└── Merged result: GameCatalogue (JSON) + icon_map.json + cached PNGs

Save Directory
├── st_<steamid>/
│   ├── save.hg ──→ LZ4 decompress ──→ Key unmap ──→ JSON with readable keys
│   ├── save2.hg
│   └── accountdata.hg ──→ Plain JSON (no compression)
```

### External Dependencies

| Dependency | Purpose | Required? |
|-----------|---------|-----------|
| [hgpaktool](https://github.com/monkeyman192/hgpaktool) | PSARC/PAK archive reading | Yes, for game data extraction |
| [MBINCompiler](https://github.com/monkeyman192/MBINCompiler) | MBIN → EXML conversion | Yes, for game data extraction |
| [Pillow](https://pillow.readthedocs.io/) | DDS → PNG icon conversion | Yes, for icon extraction |
| [lz4](https://pypi.org/project/lz4/) | .hg save file compression | Yes, for save read/write |
| [PySide6](https://doc.qt.io/qtforpython-6/) | GUI framework | Yes, for the editor GUI |

### Project Architecture

```
src/nmstoolkit/
├── core/                        # Domain layer (pure logic, stdlib + lz4 only)
│   ├── codec.py                 # .hg LZ4 compress/decompress + key mapping
│   ├── save_file.py             # SaveFile model (load/save with key unmapping)
│   ├── save_scanner.py          # Find save profiles and slots on disk
│   ├── exml_parser.py           # EXML → Python dicts (products, substances, tech, recipes, seasons, locale)
│   ├── game_catalogue.py        # GameCatalogue: immutable container for all parsed game data
│   ├── game_data_pipeline.py    # Orchestrates PAK → MBIN → EXML → GameCatalogue extraction
│   ├── icon_cache.py            # DDS → PNG conversion and disk caching
│   ├── icon_extractor.py        # PAK icon extraction + item-to-DDS mapping
│   ├── mesh_data.py             # Domain model: Mesh, SceneNode, Transform
│   ├── geometry_parser.py       # Binary GEOMETRY.MBIN parser (half-float, packed normals)
│   ├── scene_parser.py          # SCENE EXML → SceneNode tree
│   └── corvette_mesh_pipeline.py # Mesh extraction + caching orchestration
│
├── adapters/                    # External integrations
│   ├── hgpak_adapter.py         # PAK reading via hgpaktool
│   └── mbin_compiler_adapter.py # MBIN→EXML via MBINCompiler (supports Wine on Linux)
│
├── gui/
│   ├── main_window.py           # Main application window
│   ├── tabs/                    # One tab per editor section
│   │   ├── exosuit_tab.py
│   │   ├── ships_tab.py
│   │   ├── corvette_tab.py      # Corvette builder with 2D/3D toggle
│   │   ├── companions_tab.py    # Pet editing with gene trait modification
│   │   ├── settlements_tab.py   # Settlement stats, production, race/address/buildings
│   │   ├── bases_tab.py         # Base storage, budget table, library, export/import
│   │   ├── fossils_tab.py       # Fossil pieces and base displays
│   │   ├── expedition_tab.py    # Expedition progress, rewards, Twitch/Platform, replay
│   │   ├── discoveries_tab.py   # Discovery browser, constellation optimizer
│   │   ├── recipe_finder_tab.py
│   │   ├── milestones_tab.py
│   │   ├── account_tab.py
│   │   ├── freighter_tab.py
│   │   ├── frigates_tab.py
│   │   ├── vehicles_tab.py
│   │   ├── multitools_tab.py
│   │   ├── squadron_tab.py
│   │   ├── fish_finder_tab.py
│   │   └── json_editor_tab.py   # 20 tabs total
│   └── widgets/
│       ├── inventory_grid.py    # Reusable inventory grid with drag-and-drop
│       ├── slot_editor.py       # Single-slot detail editor
│       ├── slot_optimizer.py    # Adjacency bonus optimizer
│       ├── icon_provider.py     # Item ID → icon resolution with prefix fallbacks
│       ├── corvette_3d_view.py  # OpenGL 3D corvette viewport
│       ├── stat_editor.py       # Numeric stat spin box
│       ├── enum_selector.py     # Enum combo box selector
│       └── seed_editor.py       # Hex seed editor
│
├── data/                        # Static data files
│   ├── jsonmap.txt              # Obfuscated → readable key mapping
│   ├── jsonmapac.txt            # Account data key mapping
│   ├── items.json               # Static item database (fallback)
│   ├── frigates.json            # Frigate trait reference data
│   ├── inventory.json           # Inventory structure reference
│   ├── rewards.json             # Reward ID reference
│   ├── settlements.json         # Settlement reference data
│   ├── words.json               # Alien word reference
│   └── templates/               # JSON templates (ship, companion, multitool, slot)
│
└── app.py                       # Entry point
```

## License

MIT License - see [LICENSE](LICENSE) for details.
