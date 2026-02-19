#!/usr/bin/env python3
"""Diagnostic: extract corvette placement scene root transforms from game PAK files.

Run from the project root with the venv active:
    .venv/bin/python scripts/diag_corvette_transforms.py

For each corvette module type, finds both parts scenes and placement scenes,
parses their root transforms (position, rotation, scale), and outputs a
comparison table. This reveals what rotation each module needs in the 3D grid.

Writes results to /tmp/nms_corvette_transforms.txt
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from nmstoolkit.adapters.hgpak_adapter import HgpakAdapter
from nmstoolkit.adapters.mbin_compiler_adapter import MbinCompilerAdapter
from nmstoolkit.core.scene_parser import parse_scene


def _find_game_dir():
    try:
        from PySide6.QtCore import QSettings
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance() or QApplication(sys.argv)
        s = QSettings("NMSToolkit", "NMSToolkit")
        gd = s.value("game_dir", "")
        if gd:
            return Path(gd)
    except Exception:
        pass
    return None


def _resolve_pak_dir(game_dir):
    for sub in ("GAMEDATA/PCBANKS", "PCBANKS"):
        p = game_dir / sub
        if p.is_dir():
            return p
    if game_dir.name == "PCBANKS":
        return game_dir
    return None


def _find_mbin_compiler(pak_dir):
    import platform
    import shutil
    if platform.system() == "Darwin":
        ext_base = Path.home() / "Library" / "Application Support" / "nmstoolkit"
    elif platform.system() == "Windows":
        ext_base = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "nmstoolkit"
    else:
        ext_base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "nmstoolkit"
    ext_dir = ext_base / "ExternalTools" / "MBINCompiler"
    candidates = [
        ext_dir / "MBINCompiler.exe",
        ext_dir / "MBINCompiler",
        ext_dir / "MBINCompiler-linux",
        pak_dir / "MBINCompiler.exe",
        pak_dir / "MBINCompiler",
    ]
    for c in candidates:
        if c.exists():
            return c
    w = shutil.which("MBINCompiler") or shutil.which("MBINCompiler.exe")
    if w:
        return Path(w)
    return None


def _normalize_ref(path):
    return path.replace("\\", "/").lower()


# All corvette module scene candidates — parts first, then placement
# Structured as: (module_prefix, variant, [(scene_path, scene_type), ...])
_MODULE_SCENE_MAP = {
    "B_COK": {
        "parts": "models/common/spacecraft/biggs/modules/parts/cockpit_1x2_{v}.scene.mbin",
        "placement": "models/common/spacecraft/biggs/modules/cockpit_{v}_1x2_placement.scene.mbin",
    },
    "B_HAB1": {
        "parts": "models/common/spacecraft/biggs/modules/parts/hab_{v}_1x1_core.scene.mbin",
        "placement": "models/common/spacecraft/biggs/modules/hab_{v}_1x1_placement.scene.mbin",
    },
    "B_HAB": {
        "parts": "models/common/spacecraft/biggs/modules/parts/hab_{v}_1x2_core.scene.mbin",
        "placement": "models/common/spacecraft/biggs/modules/hab_{v}_1x2_placement.scene.mbin",
    },
    "B_WNG": {
        "parts": "models/common/spacecraft/biggs/modules/parts/wing_{v}_l.scene.mbin",
        "placement": "models/common/spacecraft/biggs/modules/ext_wing_{v}_1x2_placement.scene.mbin",
    },
    "B_TRU": {
        "parts": "models/common/spacecraft/biggs/modules/parts/backthruster_{v}.scene.mbin",
        "placement": "models/common/spacecraft/biggs/modules/ext_backthrusters_{v}_1x1_placement.scene.mbin",
    },
    "B_TUR": {
        "parts": None,
        "placement": "models/common/spacecraft/biggs/modules/ext_turret_1x1_placement.scene.mbin",
    },
    "B_CON": {
        "parts": "models/common/spacecraft/biggs/modules/parts/connectors/connector_1x1_{v}.scene.mbin",
        "placement": "models/common/spacecraft/biggs/modules/ext_connector_1x1_{v}_placement.scene.mbin",
    },
    "B_SHL": {
        "parts": "models/common/spacecraft/biggs/modules/parts/shieldgenerator_{v}.scene.mbin",
        "placement": "models/common/spacecraft/biggs/modules/ext_shieldgen_{v}_1x1_placement.scene.mbin",
    },
    "B_ALK": {
        "parts": "models/common/spacecraft/biggs/modules/parts/airlock_nesw_{v}.scene.mbin",
        "placement": "models/common/spacecraft/biggs/modules/exthatch_airlock_{v}_1x1_placement.scene.mbin",
    },
    "B_GEN": {
        "parts": "models/common/spacecraft/biggs/modules/parts/generator_{v}.scene.mbin",
        "placement": "models/common/spacecraft/biggs/modules/ext_gen_1x1_{v}_placement.scene.mbin",
    },
    "B_STR": {
        "parts": "models/common/spacecraft/biggs/modules/parts/structural/structural_1x1_y_0.scene.mbin",
        "placement": "models/common/spacecraft/biggs/modules/ext_structural_1x1_placement.scene.mbin",
    },
    "B_LND": {
        "parts": "models/common/spacecraft/biggs/modules/parts/landinggear_leg_{v}.scene.mbin",
        "placement": "models/common/spacecraft/biggs/modules/ext_landinggear_1x1_placement.scene.mbin",
    },
}

_VARIANTS = ["a", "b", "c", "d", "e"]


def main():
    out_path = Path("/tmp/nms_corvette_transforms.txt")
    lines = []

    def log(msg):
        lines.append(msg)
        print(msg)

    log("=== NMS Corvette Module Transform Diagnostic ===\n")

    game_dir = _find_game_dir()
    if not game_dir:
        log("ERROR: Cannot find game_dir from QSettings")
        out_path.write_text("\n".join(lines))
        return

    pak_dir = _resolve_pak_dir(game_dir)
    if not pak_dir:
        log(f"ERROR: Cannot find PCBANKS in {game_dir}")
        out_path.write_text("\n".join(lines))
        return

    mbin_compiler = _find_mbin_compiler(pak_dir)
    if not mbin_compiler:
        log("ERROR: Cannot find MBINCompiler")
        out_path.write_text("\n".join(lines))
        return

    log(f"game_dir: {game_dir}")
    log(f"pak_dir: {pak_dir}")
    log(f"mbin_compiler: {mbin_compiler}\n")

    # Open scene PAK
    scene_pak = pak_dir / "NMSARC.EntitySceneMBIN.pak"
    if not scene_pak.exists():
        log(f"ERROR: Scene PAK not found: {scene_pak}")
        out_path.write_text("\n".join(lines))
        return

    converter = MbinCompilerAdapter(mbin_compiler)

    with HgpakAdapter.from_path(scene_pak) as pak:
        all_files = pak.list_files()
        file_index = {_normalize_ref(f): f for f in all_files}

        log(f"Scene PAK: {len(all_files)} files\n")

        # Also index biggs-related files for discovery
        biggs_files = sorted(f for f in all_files if "biggs" in f.lower())
        log(f"Biggs-related files in scene PAK: {len(biggs_files)}")
        for f in biggs_files[:20]:
            log(f"  {f}")
        if len(biggs_files) > 20:
            log(f"  ... and {len(biggs_files) - 20} more")
        log("")

        # For each module type, try to extract transforms
        log("=" * 80)
        log("MODULE TRANSFORMS")
        log("=" * 80)

        for prefix, templates in _MODULE_SCENE_MAP.items():
            log(f"\n--- {prefix} ---")

            found_any = False
            for variant in _VARIANTS:
                for scene_type in ("parts", "placement"):
                    template = templates.get(scene_type)
                    if template is None:
                        continue

                    scene_path = template.format(v=variant)
                    norm = _normalize_ref(scene_path)
                    actual = file_index.get(norm)
                    if actual is None:
                        # Try with .pc suffix
                        actual = file_index.get(norm + ".pc")

                    if actual is None:
                        continue

                    found_any = True
                    log(f"\n  [{scene_type.upper()}] {actual}")

                    try:
                        data = pak.extract(paths=[actual])
                        scene_bytes = data.get(actual, b"")
                        if not scene_bytes:
                            log("    ERROR: empty extraction")
                            continue

                        exml = converter.convert(scene_bytes)
                        if not exml:
                            log("    ERROR: MBINCompiler conversion failed")
                            continue

                        scene_node = parse_scene(exml)

                        # Root transform
                        t = scene_node.transform
                        log(f"    Root name: {scene_node.name}")
                        log(f"    Position:  ({t.position[0]:.4f}, {t.position[1]:.4f}, {t.position[2]:.4f})")
                        log(f"    Rotation:  ({t.rotation[0]:.4f}, {t.rotation[1]:.4f}, {t.rotation[2]:.4f})")
                        log(f"    Scale:     ({t.scale[0]:.4f}, {t.scale[1]:.4f}, {t.scale[2]:.4f})")
                        log(f"    Geo ref:   {scene_node.geometry_ref or '(none)'}")
                        log(f"    Children:  {len(scene_node.children)}")

                        # Walk children to show hierarchy
                        for i, child in enumerate(scene_node.children[:5]):
                            ct = child.transform
                            has_rot = any(abs(r) > 0.001 for r in ct.rotation)
                            rot_str = f" ROT=({ct.rotation[0]:.1f},{ct.rotation[1]:.1f},{ct.rotation[2]:.1f})" if has_rot else ""
                            log(f"      child[{i}] name={child.name} pos=({ct.position[0]:.2f},{ct.position[1]:.2f},{ct.position[2]:.2f}){rot_str} geo={'YES' if child.geometry_ref else 'no'}")
                        if len(scene_node.children) > 5:
                            log(f"      ... +{len(scene_node.children) - 5} more children")

                    except Exception as exc:
                        log(f"    ERROR: {exc}")

                if found_any:
                    break  # Only need one variant per module type

            if not found_any:
                log(f"  No scenes found in PAK")

    log("\n\n=== DONE ===")
    out_path.write_text("\n".join(lines), encoding="utf-8")
    log(f"Results written to {out_path}")


if __name__ == "__main__":
    main()
