# Working Assumptions: Starship Figurines and Trails

Date compiled: 2026-02-17

Purpose:
- Capture current online assumptions in one place.
- Mark confidence and uncertainty explicitly.
- Define a concrete plan to verify against game data/code instead of relying on community pages.

## Scope
- Starship figurines (cockpit bobbleheads).
- Starship trails.
- Adjacency/synergy behavior between the above.

## Online assumptions (to verify)

### Figurines
| Item | Assumed effect | Confidence | Notes |
|---|---|---:|---|
| Polo Figurine | `+5% Maneuvering` | High | Consistent in current community references. |
| Artemis Figurine | `+5% Boost` | High | Also documented as synergy anchor with Polo/trails. |
| Atlas Figurine | `+50 LY Warp Range` | High | Numeric value consistently listed. |
| Null Figurine | `+5% Shield` | High | Numeric value consistently listed. |
| Nada Figurine | Launch-cost reduction (`-5%` or older `-10%`) | Medium | Newer references show `-5%`; older code-derived posts show `-10%`. |
| Apollo Figurine | Ship weapon damage bonus (numeric unclear) | Medium-Low | Some sources list non-numeric bonus; older posts mention `+8`. |

### Trails
| Item | Assumed effect | Confidence | Notes |
|---|---|---:|---|
| Chromatic Starship Trail | `+1% Ship Boost` | High | Explicit value present in current references. |
| Other starship trail variants (color/special) | Generally `+1% Ship Boost` | Medium | Community listings suggest this; needs direct table verification. |
| Trail adjacency with figurines | Trail + Polo/Artemis synergy exists | Medium-High | Explicitly stated for Chromatic; generalized to all trails is an assumption. |

### Adjacency model assumption
- Figurine/trail synergy likely depends on technology family/category grouping in technology table data.
- Exact stacking math may vary per item and should be treated as unverified until extracted from MBIN/EXML data.

## Sources used
- https://www.nomansskyresources.com/starship-blueprints/polo-figurine
- https://www.nomansskyresources.com/starship-blueprints/artemis-figurine
- https://www.nomansskyresources.com/starship-blueprints/atlas-figurine
- https://www.nomansskyresources.com/starship-blueprints/-null--figurine
- https://www.nomansskyresources.com/starship-blueprints/nada-figurine
- https://www.nomansskyresources.com/starship-blueprints/apollo-figurine
- https://www.nomansskyresources.com/starship-blueprints/chromatic-starship-trail
- https://www.nomansskyresources.com/tech-layout-and-adjacency-bonus
- Historical/community code-derived discussion (older values): https://steamcommunity.com/app/275850/discussions/0/2451595390221827681/

---

## Verification plan against game code/data

Goal:
- Replace assumptions with extracted values from current game tables.

### Step 1: Extract and parse technology table from game files
Use existing pipeline in this repo (`game_data_pipeline.py`) with MBINCompiler.

Expected source table:
- `metadata/reality/tables/nms_reality_gctechnologytable.mbin`

### Step 2: Produce a focused audit list for figurines/trails
Generate a machine-readable dump with:
- technology ID
- localized display name
- category (`TechnologyCategory`)
- stat bonuses (`StatsType`, bonus, level)
- any fields related to adjacency/synergy (from raw EXML if not currently parsed)

Suggested command (from repo root):

```bash
PYTHONPATH=src .venv/bin/python - <<'PY'
from nmstoolkit.core.game_data_pipeline import build_catalogue
from pathlib import Path
import json

pak_dir = Path("/path/to/NMS/GAMEDATA/PCBANKS")
mbin = Path("src/nmstoolkit/data/ExternalTools/MBINCompiler/MBINCompiler-linux")

cat = build_catalogue(pak_dir, mbin)
rows = []
for t in cat.technologies:
    name = (t.get("display_name") or t.get("name") or "").upper()
    if "FIGURINE" in name or "TRAIL" in name:
        rows.append({
            "id": t.get("id"),
            "display_name": t.get("display_name"),
            "name_key": t.get("name"),
            "category": t.get("category"),
            "stat_bonuses": t.get("stat_bonuses"),
        })
print(json.dumps(rows, indent=2))
PY
```

### Step 3: Inspect raw EXML for hidden/adjacency fields
If parser output is insufficient, inspect raw EXML entries for the same IDs and capture:
- adjacency group/family fields
- multiplier fields
- special-case synergy declarations

Action:
- extend `parse_technology_table()` in `src/nmstoolkit/core/exml_parser.py` to include those fields in structured output.

### Step 4: Lock results in tests
Add tests asserting expected values for a known extracted fixture:
- figurine stats
- trail stats
- category/group keys for adjacency

Proposed files:
- `tests/core/test_technology_figurine_trail_values.py`
- fixture JSON produced from extracted table (version-tagged)

### Step 5: Version pinning
Record game/MBINCompiler version used for extraction in the resulting audit artifact so future changes are traceable.

---

## Decision policy until verification is complete
- Treat all figurine/trail values as provisional.
- Prefer current extracted table values over community sources when conflicts appear.
- Keep UI wording explicit (`estimated` / `unverified`) where exact game math is not yet proven by extraction.

---

## Local extraction status (executed)

Completed on this machine against:
- `<NMS_GAME_DIR>/GAMEDATA/PCBANKS`
- `MBINCompiler-linux` from `src/nmstoolkit/data/ExternalTools/MBINCompiler/`

Artifact:
- `docs/figurine-trail-audit.json`

Current extracted totals:
- `16` entries matched (`7` figurines, `9` trails)

Notable extracted values (from table stat bonuses):
- `T_BOBBLE_POLO`: `Ship_BoostManeuverability = 1.05` (~+5%)
- `T_BOBBLE_ART`: `Ship_Boost = 1.05` (~+5%)
- `T_BOBBLE_ATLAS`: `Ship_Hyperdrive_JumpDistance = 50`
- `T_BOBBLE_NULL`: `Ship_Armour_Shield_Strength = 0.05`
- `T_BOBBLE_NADA`: `Ship_Launcher_TakeOffCost = 0.9` (~10% reduction)
- `T_BOBBLE_APOLLO`: `Ship_Weapons_Guns_Damage = 8`
- `T_SHIP_*` trails found in table: `Ship_Boost = 1.01` (~+1%) per trail entry
