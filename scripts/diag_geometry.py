#!/usr/bin/env python3
"""Diagnostic: dump geometry metadata and index values for ship preview debugging.

Run from the project root with the venv active:
    python3 scripts/diag_geometry.py

Requires game data to be configured (same as the app).
Writes results to /tmp/nms_geo_diag_full.txt
"""

import os
import struct
import sys
from pathlib import Path
from xml.etree.ElementTree import fromstring

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from nmstoolkit.adapters.hgpak_adapter import HgpakAdapter
from nmstoolkit.adapters.mbin_compiler_adapter import MbinCompilerAdapter


def _find_game_dir():
    """Try to find game dir from QSettings (same as app)."""
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
    """Find MBINCompiler binary — mirrors app search logic."""
    import shutil
    # Check standard ExternalTools location (same as app)
    import platform
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
        Path("/tmp/nms_exml/MBINCompiler"),
        pak_dir / "MBINCompiler.exe",
        pak_dir / "MBINCompiler",
        pak_dir.parent / "MBINCompiler.exe",
        pak_dir.parent / "MBINCompiler",
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


def _int_prop(root, name, default=0):
    node = root.find(f"Property[@name='{name}']")
    if node is None:
        return default
    try:
        return int(node.get("value", str(default)))
    except ValueError:
        return default


def main():
    out_path = Path("/tmp/nms_geo_diag_full.txt")
    lines = []

    def log(msg):
        lines.append(msg)
        print(msg)

    log("=== NMS Geometry Diagnostic ===")

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

    log(f"pak_dir: {pak_dir}")
    log(f"mbin_compiler: {mbin_compiler}")

    converter = MbinCompilerAdapter(mbin_compiler)

    # Find a ship scene to test with
    # Use sentinelship as diagnostic target (same as previous diagnostic)
    test_ref = "models/common/spacecraft/sentinelship/sentinelship_proc.scene.mbin"
    scene_pak = pak_dir / "NMSARC.EntitySceneMBIN.pak"

    if not scene_pak.exists():
        log(f"ERROR: {scene_pak} not found")
        out_path.write_text("\n".join(lines))
        return

    # Extract scene and find geometry ref
    from nmstoolkit.core.scene_parser import parse_scene
    with HgpakAdapter.from_path(scene_pak) as pak:
        files = {_normalize_ref(f): f for f in pak.list_files()}
        for candidate in (test_ref, test_ref + ".pc"):
            nc = _normalize_ref(candidate)
            if nc in files:
                extracted = pak.extract(paths=[files[nc]])
                scene_bytes = list(extracted.values())[0]
                break
        else:
            # Try to find any ship scene
            log(f"WARNING: {test_ref} not found, looking for alternatives...")
            ship_scenes = [f for f in files if "spacecraft" in f and f.endswith(".scene.mbin")]
            if not ship_scenes:
                log("ERROR: No ship scenes found")
                out_path.write_text("\n".join(lines))
                return
            nc = ship_scenes[0]
            log(f"Using: {nc}")
            extracted = pak.extract(paths=[files[nc]])
            scene_bytes = list(extracted.values())[0]

    scene_exml = converter.convert(scene_bytes)
    scene = parse_scene(scene_exml)

    # Find first geometry ref
    geo_ref = scene.geometry_ref
    log(f"\nScene geometry_ref: {geo_ref}")

    if not geo_ref:
        # Walk children
        def find_geo(node, depth=0):
            if node.geometry_ref:
                return node.geometry_ref
            for c in node.children:
                r = find_geo(c, depth + 1)
                if r:
                    return r
            return None
        geo_ref = find_geo(scene)
        log(f"Found geo_ref in children: {geo_ref}")

    if not geo_ref:
        log("ERROR: No geometry ref found in scene")
        out_path.write_text("\n".join(lines))
        return

    # Normalize refs (lowercase, forward slash) — same as app
    geo_ref = _normalize_ref(geo_ref)
    data_ref = geo_ref.replace(".geometry.mbin", ".geometry.data.mbin")
    log(f"\nLooking for:")
    log(f"  geo: {geo_ref}")
    log(f"  data: {data_ref}")

    # Search ALL mesh PAKs, also report any .geometry.data files found
    geo_map = {}
    for mesh_pak in sorted(pak_dir.glob("NMSARC.Mesh*.pak")):
        with HgpakAdapter.from_path(mesh_pak) as pak:
            files = {_normalize_ref(f): f for f in pak.list_files()}
            # Report any geometry.data files in this PAK for our ship
            ship_prefix = geo_ref.rsplit("/", 1)[0] if "/" in geo_ref else ""
            data_files_in_pak = [f for f in files if "geometry.data" in f and ship_prefix in f]
            if data_files_in_pak:
                log(f"  DATA FILES in {mesh_pak.name}: {data_files_in_pak}")
            to_extract = []
            for candidate in (geo_ref, geo_ref + ".pc"):
                if candidate in files:
                    to_extract.append(files[candidate])
            for candidate in (data_ref, data_ref + ".pc"):
                if candidate in files:
                    to_extract.append(files[candidate])
            if to_extract:
                extracted = pak.extract(paths=to_extract)
                for p, b in extracted.items():
                    n = _normalize_ref(p)
                    geo_map[n] = b
                    if n.endswith(".pc"):
                        geo_map[n[:-3]] = b
                log(f"  Extracted from {mesh_pak.name}: {list(extracted.keys())}")

    norm_geo = geo_ref
    norm_data = data_ref

    geo_bytes = geo_map.get(norm_geo) or geo_map.get(norm_geo + ".pc")
    raw_data = geo_map.get(norm_data) or geo_map.get(norm_data + ".pc")

    if not geo_bytes:
        log("ERROR: .geometry.mbin not found in PAK files")
        out_path.write_text("\n".join(lines))
        return

    log(f"\n=== GEOMETRY MBIN ===")
    log(f"geo_bytes size: {len(geo_bytes)}")
    log(f"raw_data size: {len(raw_data) if raw_data else 'NOT FOUND'}")

    # Convert geometry MBIN to EXML
    try:
        geo_exml = converter.convert(geo_bytes)
    except Exception as e:
        log(f"ERROR converting geometry MBIN: {e}")
        out_path.write_text("\n".join(lines))
        return

    log(f"geo_exml size: {len(geo_exml)}")

    # Parse the EXML root
    g_root = fromstring(geo_exml)

    # Dump ALL root-level properties
    log(f"\n=== ROOT PROPERTIES ===")
    for prop in g_root.findall("Property"):
        name = prop.get("name", "?")
        value = prop.get("value", None)
        if value is not None and name not in ("VertexLayout", "PositionVertexLayout", "StreamMetaDataArray"):
            log(f"  {name} = {value}")

    # Check for array properties that give us vertex ranges
    for array_name in ("MeshVertRStart", "MeshVertREnd", "MeshAABBMin", "MeshAABBMax",
                        "IndexBuffer", "BoundHullVertSt", "BoundHullVertEd"):
        arr = g_root.find(f"Property[@name='{array_name}']")
        if arr is not None:
            children = arr.findall("Property")
            log(f"  {array_name}: {len(children)} entries")
            if array_name in ("MeshVertRStart", "MeshVertREnd") and children:
                vals = [c.get("value", "?") for c in children[:10]]
                log(f"    first 10: {vals}")

    # Dump vertex layouts
    log(f"\n=== VERTEX LAYOUTS ===")
    for layout_name in ("VertexLayout", "PositionVertexLayout"):
        layout = g_root.find(f"Property[@name='{layout_name}']")
        if layout is not None:
            stride = _int_prop(layout, "Stride")
            log(f"  {layout_name}: stride={stride}")
            elems = layout.find("Property[@name='VertexElements']")
            if elems is not None:
                for e in elems.findall("Property"):
                    sem = _int_prop(e, "SemanticID")
                    typ = _int_prop(e, "Type")
                    off = _int_prop(e, "Offset")
                    log(f"    SemanticID={sem} Type={typ} Offset={off}")

    # Dump StreamMetaData
    log(f"\n=== STREAM META DATA ===")
    parent = g_root.find("Property[@name='StreamMetaDataArray']")
    if parent is None:
        log("  NOT FOUND!")
        out_path.write_text("\n".join(lines))
        return

    entries = parent.findall("Property")
    log(f"  Total entries: {len(entries)}")

    meta_list = []
    for e in entries:
        id_node = e.find("Property[@name='IdString']")
        mesh_id = ""
        if id_node is not None:
            # IdString can be nested (GcFilename)
            val = id_node.get("value", "")
            if val:
                mesh_id = val
            else:
                inner = id_node.find("Property[@name='Value']")
                if inner is not None:
                    mesh_id = inner.get("value", "")
        m = {
            "id": mesh_id,
            "vd_off": _int_prop(e, "VertexDataOffset"),
            "vd_size": _int_prop(e, "VertexDataSize"),
            "vpd_off": _int_prop(e, "VertexPositionDataOffset"),
            "vpd_size": _int_prop(e, "VertexPositionDataSize"),
            "id_off": _int_prop(e, "IndexDataOffset"),
            "id_size": _int_prop(e, "IndexDataSize"),
        }
        meta_list.append(m)

    # Show first 10 entries
    for i, m in enumerate(meta_list[:10]):
        log(f"  [{i}] id={m['id'][:50]}")
        log(f"      pos: off={m['vpd_off']} size={m['vpd_size']}")
        log(f"      vert: off={m['vd_off']} size={m['vd_size']}")
        log(f"      idx: off={m['id_off']} size={m['id_size']}")

    # Compute section bases (our current method)
    pos_section_end = 0
    vert_section_end = 0
    for m in meta_list:
        pe = m["vpd_off"] + m["vpd_size"]
        if pe > pos_section_end:
            pos_section_end = pe
        ve = m["vd_off"] + m["vd_size"]
        if ve > vert_section_end:
            vert_section_end = ve
    vert_base = pos_section_end
    idx_base = pos_section_end + vert_section_end

    log(f"\n=== COMPUTED SECTION BASES ===")
    log(f"  pos_section_end (=vert_base): {pos_section_end}")
    log(f"  vert_section_end: {vert_section_end}")
    log(f"  idx_base: {idx_base}")
    if raw_data:
        log(f"  raw_data total size: {len(raw_data)}")
        computed_total = idx_base + sum(m["id_size"] for m in meta_list)
        log(f"  computed total (idx_base + all idx sizes): {computed_total}")
        idx_section_end = max((m["id_off"] + m["id_size"]) for m in meta_list) if meta_list else 0
        log(f"  max(idx_off + idx_size): {idx_section_end}")
        log(f"  idx_base + idx_section_end: {idx_base + idx_section_end}")

    if not raw_data:
        log("\nNo raw_data — cannot test index parsing")
        out_path.write_text("\n".join(lines))
        return

    # Check first few bytes of raw_data for MBIN header
    log(f"\n=== RAW DATA HEADER CHECK ===")
    first_16 = raw_data[:16]
    log(f"  First 16 bytes (hex): {first_16.hex()}")
    log(f"  First 4 bytes as u32: {struct.unpack_from('<I', raw_data, 0)[0]:#010x}")
    if first_16[:4] == b'\xcc\xcc\xcc\xcc' or struct.unpack_from('<I', raw_data, 0)[0] in (0xCCCCCCCC, 0xFFFFFFFF):
        log("  WARNING: Looks like MBIN header! Data may need header skip.")

    # Test actual index reading for first non-collision mesh
    log(f"\n=== INDEX VALIDATION (first 5 non-collision meshes) ===")
    is_16bit = _int_prop(g_root, "Indices16Bit") == 1
    log(f"  is_16bit: {is_16bit}")
    pos_stride = _int_prop(g_root.find("Property[@name='PositionVertexLayout']"), "Stride") if g_root.find("Property[@name='PositionVertexLayout']") else 0
    log(f"  position stride: {pos_stride}")

    tested = 0
    for m in meta_list:
        if "collision" in m["id"].lower():
            continue
        if tested >= 5:
            break
        tested += 1

        pos_off = m["vpd_off"]
        pos_size = m["vpd_size"]
        idx_off_section = m["id_off"]
        idx_size = m["id_size"]

        if pos_size <= 0 or idx_size <= 0:
            log(f"\n  [{m['id'][:40]}] SKIPPED (pos_size={pos_size} idx_size={idx_size})")
            continue

        vert_count = pos_size // pos_stride if pos_stride > 0 else 0

        vert_off = m["vd_off"]
        vert_size = m["vd_size"]

        # Method A: section-relative (our current fix) — idx_base + idx_off
        abs_idx_off_A = idx_base + idx_off_section

        # Method B: absolute (original code) — idx_off directly
        abs_idx_off_B = idx_off_section

        # Method C: relative to VertexDataOffset — vd_off + id_off
        abs_idx_off_C = vert_off + idx_off_section

        log(f"\n  [{m['id'][:40]}]")
        log(f"    vert_count={vert_count} idx_size={idx_size}")
        log(f"    vd_off={vert_off} vd_size={vert_size} vpd_off={pos_off}")
        log(f"    idx_off={idx_off_section}  (== vd_size? {idx_off_section == vert_size})")
        log(f"    vd_off + vd_size + idx_size = {vert_off + vert_size + idx_size}  (== vpd_off? {vert_off + vert_size + idx_size == pos_off})")
        log(f"    Method A (section base): {abs_idx_off_A}")
        log(f"    Method B (absolute): {abs_idx_off_B}")
        log(f"    Method C (vd_off + id_off): {abs_idx_off_C}")

        # Only test Method C (vd_off + idx_off) — the structurally correct one
        abs_off = abs_idx_off_C
        if abs_off + idx_size > len(raw_data):
            log(f"    Method C: OUT OF BOUNDS (off={abs_off} + size={idx_size} > {len(raw_data)})")
            continue

        idx_bytes = raw_data[abs_off:abs_off + idx_size]

        # Test both 16-bit and 32-bit index reading
        for bits, fmt_char, elem_size in [(16, "H", 2), (32, "I", 4)]:
            count = idx_size // elem_size
            if count == 0:
                continue
            indices = struct.unpack_from(f"<{count}{fmt_char}", idx_bytes, 0)
            min_idx = min(indices)
            max_idx = max(indices)
            valid_local = max_idx < vert_count if vert_count > 0 else False
            log(f"    {bits}-bit: count={count} min={min_idx} max={max_idx} valid_local={valid_local}")

    log(f"\n=== DONE ===")
    log(f"Results written to {out_path}")
    out_path.write_text("\n".join(lines))


if __name__ == "__main__":
    main()
