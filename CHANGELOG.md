# Changelog

All notable changes to this project will be documented in this file.

## [0.2.7-beta] - 2026-02-15

### Added
- Constellation editor — optimize, reset, backup/restore star map travel lines
- Path optimizer using nearest-neighbor + 2-opt (91% distance reduction, stdlib only)
- VisitedSystems count and total path length display

## [0.2.6-beta] - 2026-02-15

### Added
- Base library — save, browse, and swap bases from persistent local storage
- Library panel with Save Current, Load/Swap, and Delete buttons
- Base export/import as portable JSON files

## [0.2.5-beta] - 2026-02-15

### Added
- Settlement perks editor with dropdown add/remove (61 known perks)
- Squadron pilot ship selection from player's owned ships
- Fossil tab shows friendly names instead of raw IDs
- Discovery tab undiscovered-only filter with decoded galactic addresses
- Galaxy atlas HTML export (self-contained single file, dark theme)
- Expedition tab Twitch/Platform rewards table with add/remove

### Changed
- Units currency now uses unsigned 32-bit values (fixes display of large values)
- Settlement tab improved layout with production output and stat write-back

## [0.2.4-beta] - 2026-02-14

### Added
- Base part budget table with per-base part counts, wire counts, and sortable columns
- Total parts shown with percentage of 16K save limit
- Budget table click syncs with base selector

## [0.2.3-beta] - 2026-02-14

### Added
- Expedition reward filter by expedition number
- Unlock all rewards button for offline replay
- Milestone and reputation tracking (Gek, Vy'keen, Korvax, guilds)

### Fixed
- Settlement tab ownership detection via seed matching
- Gene traits: dynamic descriptor list with add/remove buttons
- Display name resolution for caret-prefixed items

## [0.2.2-beta] - 2026-02-13

### Added
- Fossils tab showing fossil pieces across inventories and assembled base displays
- Fish finder reference guide

### Fixed
- Icon resolution for caret-prefixed items in catalogue lookup

## [0.2.1-beta] - 2026-02-13

### Added
- 3D corvette builder with game mesh rendering (PyOpenGL 3.3+ shaders)
- Corvette mesh extraction pipeline from PAK files with JSON disk cache
- Domain model for 3D meshes: Mesh, SceneNode, Transform
- Binary GEOMETRY.MBIN parser (half-float positions, INT_2_10_10_10_REV normals)

## [0.2.0-beta] - 2026-02-12

### Added
- External Dependencies dialog with MBINCompiler one-click download
- NMS file format and data architecture reference in README

### Changed
- Switched build from PyInstaller to Nuitka standalone to avoid AV false positives

## [0.1.0] - 2026-02-15

### Added
- Locale resolution fallback for tech items, season names, and reward names
- Expedition tab resolves locale keys (e.g. `^UI_SEASON_19_NAME` -> "Corvette")
- Recipe tab refresh mechanism after game data extraction
- Broadened corvette detection (model filename + corvette module IDs)
- Corvette module icon mapping (B_COK, B_HAB, B_WNG, etc.)
- External Dependencies dialog with MBINCompiler one-click download
- Tests and Architecture badges in README

### Fixed
- Recipe tab showing empty despite catalogue existing
- Raw locale keys displayed instead of resolved names in expedition tab
- Corvette tab not detecting corvettes without BIGGS model path
- Missing icons for corvette modules
