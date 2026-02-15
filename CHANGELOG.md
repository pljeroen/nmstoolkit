# Changelog

All notable changes to this project will be documented in this file.

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
