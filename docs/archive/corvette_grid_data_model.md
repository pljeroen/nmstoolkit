# Corvette Grid Data Model — Investigation Notes

**Date**: 2026-02-19
**Save analyzed**: save30.hg (st_76561198078575175)
**Ships found**: 3 completed corvettes + 1 active draft

## Key Finding: Build Grid Is NOT Stored Per-Ship

The completed corvette's `ship["Inventory"]` contains **regular items and substances only** — no build modules (B_ prefix). The build grid with module placement is stored ONLY in `CorvetteStorageInventory` (a player-level field), linked to one ship via `CorvetteEditAssociatedShipIndex`.

### Data Structure Map

```
PlayerStateData:
  CorvetteStorageInventory:     # THE build grid (Width=10, Height=16)
    Slots: [B_ modules with X,Y]
  CorvetteStorageLayout:        # Just metadata {Slots: 10, Seed, Level}
  CorvetteEditAssociatedShipIndex: 3   # Links to ShipOwnership[3]
  CorvetteEditShipName: ""
  CorvetteDraftShipSeed: 0

  ShipOwnership[3] "Delete me":   # Completed corvette (currently-edited)
    Inventory:           Width=10, Height=5,  0 B_ modules, 4 regular items
    Inventory_TechOnly:  Width=10, Height=6, 32 tech items
    InventoryLayout:     {Slots: 10, Seed: [true, "0x1"], Level: 1}
    Resource.Seed:       0x68B61790

  ShipOwnership[5] "BigBoy":     # Completed corvette (NOT linked)
    Inventory:           Width=10, Height=12, 0 slots (empty!)
    Inventory_TechOnly:  Width=10, Height=6, 44 tech items
    InventoryLayout:     {Slots: 10, Seed: [true, "0x1"], Level: 1}
    Resource.Seed:       0x68B88733

  ShipOwnership[6] "Sokamaki's Voyage SR3":  # Completed corvette (NOT linked)
    Inventory:           Width=10, Height=12, 7 regular items
    Inventory_TechOnly:  Width=10, Height=6, 42 tech items
    InventoryLayout:     {Slots: 10, Seed: [true, "0x1"], Level: 1}
    Resource.Seed:       0x68B88733
```

### Implications for 3D View

| Scenario | Source for Build Grid | Available? |
|----------|----------------------|------------|
| Draft mode | `CorvetteStorageInventory` | Always |
| Completed, currently-edited | `CorvetteStorageInventory` (via index match) | Yes |
| Completed, NOT currently-edited | NOWHERE | **No** |

## Grid Layout Analysis

Grid: 10 columns × 16 rows (only rows 0-11 occupied = 111 modules)

```
     |    0     |    1     |    2     |    3     |    4     |    5     |    6     |    7     |    8     |    9     |
Y= 0 |  HAB_A   |  HAB1_A  |  HAB_B   |  HAB1_B  |  DECO_O  |  HAB1_C  |  WNG_A   |  WNG_B   | STR_E_N  |  WNG_D   |
Y= 1 |  WNG_E   |  WNG_F   |  WNG_G   |  WNG_H   |  WNG_I   |  WNG_J   |  WNG_K   |  WNG_L   |  WNG_M   |  WNG_N   |
Y= 2 | WNG_O_0  | WNG_O_1  | WNG_O_2  | STR_A_N  | STR_B_N  | STR_C_N  | STR_D_N  |  TRU_A   | STR_F_N  | STR_G_N  |
Y= 3 | STR_H_N  | STR_I_N  | STR_J_N  | STR_K_N  | STR_L_N  | STR_M_N  | STR_N_N  | STR_O_N  | STR_P_N  | STR_Q_N  |
Y= 4 | STR_R_N  | STR_S_N  | STR_A_NE | STR_B_NE | STR_C_NE | STR_D_NE | STR_E_NE | STR_F_NE | STR_G_NE | STR_H_NE |
Y= 5 | STR_I_NE | STR_J_NE | STR_K_NE | STR_L_NE | CON_L_0  | CON_L_1  | CON_L_2  | CON_L_3  |  CON_6   |  CON_4   |
Y= 6 |  CON_5   |  CON_7   |  CON_8   |  CON_9   |  CON_10  |  CON_11  |  CON_12  |  CON_13  |  CON_14  |  CON_15  |
Y= 7 |  CON2_0  |  CON2_1  |  CON2_2  |  CON2_3  |  COK_A   |  COK_B   |  COK_D   |  DECO_A  |  DECO_B  |  DECO_C  |
Y= 8 |  DECO_D  |  DECO_E  |  DECO_F  |  DECO_G  |  DECO_H  |  DECO_I  |  DECO_J  |  DECO_K  |  DECO_L  |  DECO_M  |
Y= 9 | DECO_N_0 | DECO_N_1 |  HAB_C   |  DECO_P  |  TUR_A   |  TRU_B   |  TUR_C   |  TRU_D   |  GEN_0   |  GEN_1   |
Y=10 |  GEN_2   |  GEN_3   |  LND_A   |  LND_B   |  ALK_A   |  ALK_B   |  ALK_C   |  SHL_A   |  SHL_B   |  SHL_C   |
Y=11 | STR_M_NE |          |          |          |          |          |          |          |          |          |
```

### Position Coordinates

- **Positions are ABSOLUTE grid coordinates**, NOT relative to a starting block
- X range: 0-9 (Width=10), Y range: 0-11 (occupied), grid Height=16
- Every module occupies exactly ONE cell — no shared cells
- ValidSlotIndices covers X[0-9] Y[0-11] = 120 cells, of which 111 are occupied

### Module Per-Slot Fields

Every slot has exactly these fields:
```json
{
  "Type": {"InventoryType": "Product"},    // Always "Product" for B_ modules
  "Id": "^B_COK_A",                         // Module ID with ^ prefix
  "Amount": 10,                             // Varies (not position-related)
  "MaxAmount": 500,                         // Always 500 for B_ modules
  "DamageFactor": 0.0,                      // Always 0.0
  "FullyInstalled": true,                   // Always true
  "AddedAutomatically": false,              // Always false
  "Index": {"X": 4, "Y": 7}                // Grid position (absolute)
}
```

No additional position, rotation, or offset fields exist. The grid position is the only spatial data.

### Grid Model: 2D Blueprint with Height

**Each grid cell = one module placement.** The grid is a top-down 2D blueprint.
All modules occupy exactly ONE cell (1×1 in grid X,Y). No multi-cell grid footprints.

The "1x2" in scene filenames describes the module's **3D HEIGHT** (2 units tall),
not grid occupancy. Modules with walkable interiors (HAB, COK) are taller.

Module 3D block sizes (width × height × depth):
- **1×1×1**: STR, DECO, CON, CON2, TRU, TUR, GEN, SHL, ALK, LND, HAB1
- **1×2×1**: COK, HAB, WNG, BTRU (tall — have interiors or exterior esthetics)
- **1×3×1**: One special block type (TBD — user reports one exists)
- **No blocks with depth > 1** — all modules are 1 deep

Players design ships by placing modules in the grid:
- Adjacent HABs/COKs → large connected interior walkable space
- WNGs on the outside → wing esthetics
- DECOs on top/bottom/sides → finishing touches
- STR/CON → structural framework
- Functional modules (TRU, GEN, SHL, etc.) → ship systems

### Scene File Naming Convention

The "1x2" and "1x1" in scene filenames encode the model HEIGHT, not grid span:

| Type | Height | Scene Pattern | Notes |
|------|--------|---------------|-------|
| COK  | 2      | `cockpit_1x2_{v}` | Cockpit with interior |
| HAB  | 2      | `hab_{v}_1x2_core` | Habitation with interior |
| HAB1 | 1      | `hab_{v}_1x1_core` | Access module (no interior) |
| WNG  | 2      | `ext_wing_{v}_1x2_placement` | Tall wing piece |
| BTRU | 2      | (not in this save) | Big thruster/engine |
| TRU  | 1      | `ext_backthrusters_{v}_1x1_placement` | Small thruster |
| All others | 1 | Various `_1x1_` patterns | Standard height |

**Note**: icon_provider.py maps `HAB→HAB1X1` and `HAB1→HAB1X2` which appears SWAPPED
vs scene files. The scene file names should be trusted since they reference the 3D model.

### Additional Module Types Found in items.json

Not present in this corvette's grid but exist as game items:
- **B_BTRU** (A,B,C) — Big Thruster (1×2×1). The "1×2 engine" user mentioned.
- **B_WNG_*_R** — Right-side wing variants (mirrored). Each WNG type has an _R variant.
- **B_ALK_Z_*** — Alternate airlock orientation
- **B_WALL_*** — Interior wall decorations (TOIL, KITC, BUNK, CARG, etc.)
- **B_STR_*_NW**, **B_STR_*_Y_*** — Additional structural directions and Y-variants
- **B_DOOR0**, **B_STAIRS0** — Interior elements
- **B_CON_R_*** — Right-side connectors (vs B_CON_L_* left-side)

### Module Categories and Counts

| Category | Prefix | Count | Rows |
|----------|--------|-------|------|
| STR (Structure) | B_STR_*_N, B_STR_*_NE | 32 | 2-5, 11 |
| DECO (Decoration) | B_DECO_* | 17 | 0, 7-9 |
| CON (Connector) | B_CON_* | 16 | 5-7 |
| WNG (Wing) | B_WNG_* | 16 | 0-2 |
| GEN (Generator) | B_GEN_* | 4 | 9-10 |
| CON2 (Connector v2) | B_CON2_* | 4 | 7 |
| HAB (Habitation) | B_HAB_* | 3 | 0, 9 |
| HAB1 (Access Module) | B_HAB1_* | 3 | 0 |
| COK (Cockpit) | B_COK_* | 3 | 7 |
| SHL (Shield) | B_SHL_* | 3 | 10 |
| ALK (Airlock) | B_ALK_* | 3 | 10 |
| TRU (Thruster) | B_TRU_* | 3 | 2, 9 |
| LND (Landing Gear) | B_LND_* | 2 | 10 |
| TUR (Turret) | B_TUR_* | 2 | 9 |

### Row Semantic Mapping

```
Row 0:   HAB + HAB1 + WNG + DECO + STR  — Top/bow of ship
Row 1:   WNG × 10                         — Wings (full row)
Row 2:   WNG + STR + TRU                  — Wings/structure/thrusters
Row 3-4: STR × 10                         — Core structure
Row 5:   STR + CON_L + CON               — Structure → connector transition
Row 6:   CON × 10                         — Connectors (full row)
Row 7:   CON2 + COK + DECO               — Cockpit section
Row 8:   DECO × 10                        — Decorations (full row)
Row 9:   DECO + HAB + TUR + TRU + GEN    — Mixed rear utilities
Row 10:  GEN + LND + ALK + SHL           — Bottom utilities
Row 11:  STR (one outlier)                — Edge piece
```

## Bugs Found in Current Code

### Bug 1: Wrong Inventory Source for Completed Corvettes
`corvette_tab.py:912` — `_selected_inventory_for_3d()` returns `ship.get("Inventory", {})`
for completed corvettes. This inventory has **zero B_ modules**. Should use
`CorvetteStorageInventory` when `CorvetteEditAssociatedShipIndex` matches the ship.

### Bug 2: Footprint Misinterpreted — Height Treated as Grid Depth
`corvette_3d_view.py:727-729` — For 1×2 modules (COK, HAB, WNG), offset_z = 0.5 shifts the
model HALF A CELL along the grid row axis (Z in world space). This causes overlap with the
module in the adjacent grid row. The "2" in (1,2) footprint is the module's 3D HEIGHT (Y axis),
not grid depth (Z axis). Fix:
- offset_z should ALWAYS be 0 (all modules are 1 deep in the grid)
- The footprint height should scale the model's Y extent in `_fit_meshes_to_cell`
- Position: (X, height_offset, Y_row) — no Z shifting

### Bug 3: Artificial Layering Creates Wrong Layout
The 3-layer split creates a stacked view that doesn't represent the actual ship structure.
Rows 0-5 on top, rows 6-11 in middle, rows 12-15 (empty) at bottom — this puts wings above
the cockpit and generators at the same height as the cockpit, which is wrong.

### Bug 4: Non-Linked Completed Corvettes Have No Build Grid
For completed corvettes not linked via `CorvetteEditAssociatedShipIndex`, the build grid
is simply not available in the save file. The 3D view should show a message.
