"""Shared helpers for template-level 3D previews."""

from __future__ import annotations

import math
import shutil
from pathlib import Path
from functools import lru_cache
from typing import Callable, List, Optional, Tuple

from PySide6.QtCore import QSettings, QThread, Signal
from PySide6.QtWidgets import QApplication

from nmstoolkit.core.mesh_data import Mesh, Transform
from nmstoolkit.paths import external_tools_dir


class PreviewLoadThread(QThread):
    """Runs mesh loading in a worker thread and returns results to the UI thread."""

    completed = Signal(int, object, str)

    def __init__(
        self,
        request_id: int,
        resource_filename: str,
        loader: Callable[[str], Tuple[List[object], str]],
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._request_id = request_id
        self._resource_filename = resource_filename
        self._loader = loader

    def run(self) -> None:
        try:
            meshes, status = self._loader(self._resource_filename)
        except Exception as exc:
            meshes, status = [], f"Preview unavailable: load failed ({exc})."
        self.completed.emit(self._request_id, meshes, status)


def seed_to_text(seed_value) -> str:
    if isinstance(seed_value, list) and len(seed_value) >= 2:
        return str(seed_value[1])
    if isinstance(seed_value, str) and seed_value:
        return seed_value
    return "—"


def configure_preview_view(view) -> None:
    """Apply consistent framing defaults for template-level previews."""
    if hasattr(view, "set_grid_visible"):
        view.set_grid_visible(False)
    if hasattr(view, "set_layering_enabled"):
        view.set_layering_enabled(False)
    if hasattr(view, "_cam_distance"):
        view._cam_distance = 5.0  # type: ignore[attr-defined]
    if hasattr(view, "_cam_target"):
        view._cam_target = [0.0, 0.0, 0.0]  # type: ignore[attr-defined]
    if hasattr(view, "_cam_pitch"):
        view._cam_pitch = 24.0  # type: ignore[attr-defined]
    if hasattr(view, "_cam_yaw"):
        view._cam_yaw = 38.0  # type: ignore[attr-defined]


def find_scene_resource_filename(payload: dict) -> str:
    """Best-effort lookup for a .SCENE.MBIN path in an entity dict."""
    if not isinstance(payload, dict):
        return ""

    resource = payload.get("Resource", {})
    if isinstance(resource, dict):
        filename = resource.get("Filename", "")
        if isinstance(filename, str) and filename:
            return filename

    queue = [payload]
    seen = set()
    while queue:
        node = queue.pop(0)
        if id(node) in seen:
            continue
        seen.add(id(node))
        if isinstance(node, dict):
            filename = node.get("Filename")
            if isinstance(filename, str) and filename.upper().endswith(".SCENE.MBIN"):
                return filename
            for value in node.values():
                if isinstance(value, (dict, list)):
                    queue.append(value)
        elif isinstance(node, list):
            for value in node:
                if isinstance(value, (dict, list)):
                    queue.append(value)
    return ""


def _settings_game_dir() -> Optional[Path]:
    settings = QSettings("NMSToolkit", "NMSToolkit")
    game_dir_value = settings.value("game_dir", "")
    if not game_dir_value:
        return None
    return Path(str(game_dir_value))


@lru_cache(maxsize=1)
def _entity_scene_files() -> tuple[str, ...]:
    try:
        from nmstoolkit.adapters.hgpak_adapter import HgpakAdapter
    except Exception:
        return tuple()
    game_dir = _settings_game_dir()
    if game_dir is None:
        return tuple()
    pak_dir = _resolve_pak_dir(game_dir)
    if pak_dir is None:
        return tuple()
    scene_pak = pak_dir / "NMSARC.EntitySceneMBIN.pak"
    if not scene_pak.exists():
        return tuple()
    with HgpakAdapter.from_path(scene_pak) as pak:
        return tuple(str(f) for f in pak.list_files())


def _existing_scene(candidates: list[str]) -> str:
    files = set(f.lower() for f in _entity_scene_files())
    if not files:
        return ""
    for candidate in candidates:
        if candidate.lower() in files:
            return candidate
    return ""


def resolve_vehicle_scene(default_name: str) -> str:
    key = (default_name or "").strip().lower()
    mapping = {
        "roamer": "models/common/vehicles/buggy/buggy.scene.mbin",
        "nomad": "models/common/vehicles/hover/hovercraft.scene.mbin",
        "colossus": "models/common/vehicles/rover/rover.scene.mbin",
        "pilgrim": "models/common/vehicles/bike/bike.scene.mbin",
        "nautilon": "models/common/vehicles/submarine/submarine.scene.mbin",
        "minotaur": "models/common/vehicles/mech_suit/mech_suit.scene.mbin",
        "motorcycle": "models/common/vehicles/wheeledbike/wheeledbike.scene.mbin",
    }
    scene = mapping.get(key, "")
    return _existing_scene([scene]) if scene else ""


def resolve_frigate_scene(frigate_class: str) -> str:
    key = (frigate_class or "").strip().upper()
    mapping = {
        "COMBAT": "models/common/spacecraft/frigates/combatfrigate.scene.mbin",
        "DIPLOMACY": "models/common/spacecraft/frigates/diplomaticfrigate.scene.mbin",
        "EXPLORATION": "models/common/spacecraft/frigates/sciencefrigate.scene.mbin",
        "INDUSTRIAL": "models/common/spacecraft/frigates/industrialfrigate.scene.mbin",
        "SUPPORT": "models/common/spacecraft/frigates/supportfrigate.scene.mbin",
        "DEEPSPACE": "models/common/spacecraft/frigates/livingfrigate_proc.scene.mbin",
        "DEEPSPACECOMMON": "models/common/spacecraft/frigates/livingfrigate_proc.scene.mbin",
        "GHOSTSHIP": "models/common/spacecraft/frigates/ghostshipfrigate.scene.mbin",
        "NORMANDY": "models/common/spacecraft/frigates/normandyfrigate.scene.mbin",
    }
    scene = mapping.get(key, "")
    return _existing_scene([scene]) if scene else ""


def resolve_companion_scene(creature_id: str) -> str:
    token = (creature_id or "").lstrip("^").strip().lower()
    token_compact = token.replace("_", "").replace("-", "")
    if not token:
        return ""
    direct = {
        "cat": "models/planets/creatures/catrig/cat.scene.mbin",
        "trex": "models/planets/creatures/trexrig/trex.scene.mbin",
        "largebutterfly": "models/planets/creatures/butterflyrig/largebutterfly.scene.mbin",
        "smallbutterfly": "models/planets/creatures/butterflyrig/butterfly.scene.mbin",
        "beetle": "models/planets/creatures/beetlerig/beetle.scene.mbin",
        "blob": "models/planets/creatures/blobrig/blob.scene.mbin",
        "diplo": "models/planets/biomes/rainforest/largecreature/diplodocus/diplodocus.scene.mbin",
        "antelope": "models/planets/creatures/anteloperig/antelope.scene.mbin",
        "hoverpet": "models/common/robots/hoverpet.scene.mbin",
        "robotcat": "models/common/robots/quadrupedpet.scene.mbin",
        "robotdeer": "models/common/robots/quadrupedpet.scene.mbin",
        "robotantelope": "models/common/robots/quadrupedpet.scene.mbin",
    }
    preferred = []
    if token in direct:
        preferred.append(direct[token])
    if token_compact in direct:
        preferred.append(direct[token_compact])

    files = _entity_scene_files()
    if not files:
        return ""
    exact_name = f"{token}.scene.mbin"
    for path in files:
        pl = path.lower()
        if pl.endswith("/" + exact_name):
            return pl

    for path in files:
        pl = path.lower()
        if not pl.endswith(".scene.mbin"):
            continue
        if "/animation/" in pl or "/anim/" in pl:
            continue
        name = Path(pl).name
        name_compact = name.replace("_", "").replace("-", "")
        if (token in name or token_compact in name_compact) and (
            "models/planets/creatures/" in pl or "models/common/robots/" in pl
        ):
            preferred.append(pl)
    if preferred:
        return _existing_scene(preferred)
    return ""


def resolve_fossil_scene(fossil_id: str) -> str:
    token = (fossil_id or "").lstrip("^").split("#", 1)[0].upper()
    if not token:
        return ""
    if token.startswith("BLD_SKULL"):
        return _existing_scene(
            [
                "models/planets/biomes/common/buildings/parts/buildableparts/decoration/expeditionrewardskull04.scene.mbin",
                "models/space/poi/skull.scene.mbin",
            ]
        )
    if token.startswith("PROC_FOSS"):
        return _existing_scene(
            [
                "models/planets/biomes/common/rareresource/ground/fossil_body.scene.mbin",
                "models/planets/biomes/common/buildings/parts/buildableparts/decoration/fossils/body.scene.mbin",
            ]
        )

    if "_SKULL" in token:
        return _existing_scene(
            [
                "models/planets/biomes/common/buildings/parts/buildableparts/decoration/fossils/skulls.scene.mbin",
                "models/planets/biomes/common/rareresource/ground/fossil_skull.scene.mbin",
            ]
        )
    if "_BODY" in token:
        return _existing_scene(
            [
                "models/planets/biomes/common/buildings/parts/buildableparts/decoration/fossils/body.scene.mbin",
                "models/planets/biomes/common/rareresource/ground/fossil_body.scene.mbin",
            ]
        )
    if "_LIMBS" in token:
        return _existing_scene(
            [
                "models/planets/biomes/common/buildings/parts/buildableparts/decoration/fossils/arms.scene.mbin",
                "models/planets/biomes/common/rareresource/ground/fossil_limbs.scene.mbin",
            ]
        )
    if "_TAIL" in token:
        return _existing_scene(
            [
                "models/planets/biomes/common/buildings/parts/buildableparts/decoration/fossils/tail.scene.mbin",
                "models/planets/biomes/common/rareresource/ground/fossil_tail.scene.mbin",
            ]
        )

    type_map = {
        "FOS_QUAD": "models/planets/biomes/common/buildings/parts/buildableparts/decoration/fossils/quadruped.scene.mbin",
        "FOS_BI": "models/planets/biomes/common/buildings/parts/buildableparts/decoration/fossils/biped.scene.mbin",
        "FOS_BIRD": "models/planets/biomes/common/buildings/parts/buildableparts/decoration/fossils/bird.scene.mbin",
        "FOS_WORM": "models/planets/biomes/common/buildings/parts/buildableparts/decoration/fossils/worm.scene.mbin",
        "FOS_GRUN": "models/planets/biomes/common/buildings/parts/buildableparts/decoration/fossils/grunt.scene.mbin",
    }
    for prefix, scene in type_map.items():
        if token.startswith(prefix):
            return _existing_scene([scene])
    return ""


def resolve_settlement_scene(settlement_race: str) -> str:
    """Resolve a representative settlement scene for preview."""
    key = (settlement_race or "").strip().lower()
    candidates = []
    if "builder" in key or "autophage" in key:
        candidates.extend(
            [
                "models/planets/biomes/common/buildings/settlement/tower_builders.scene.mbin",
                "models/planets/biomes/common/buildings/settlement/monument/monument0builders.scene.mbin",
            ]
        )
    else:
        candidates.extend(
            [
                "models/planets/biomes/common/buildings/settlement/tower_stone.scene.mbin",
                "models/planets/biomes/common/buildings/settlement/monument/monument0.scene.mbin",
                "models/planets/biomes/common/buildings/settlement/summary_terminal.scene.mbin",
            ]
        )
    return _existing_scene(candidates)


def _normalize_ref(path: str) -> str:
    return path.replace("\\", "/").lower()


def _resolve_pak_dir(game_dir: Path) -> Optional[Path]:
    pcbanks = game_dir / "GAMEDATA" / "PCBANKS"
    if pcbanks.exists():
        return pcbanks
    pcbanks = game_dir / "PCBANKS"
    if pcbanks.exists():
        return pcbanks
    if game_dir.name.upper() == "PCBANKS" and game_dir.exists():
        return game_dir
    return None


def _find_mbin_compiler(pak_dir: Path) -> Optional[Path]:
    ext_dir = external_tools_dir() / "MBINCompiler"
    candidates = [
        ext_dir / "MBINCompiler.exe",
        ext_dir / "MBINCompiler",
        ext_dir / "MBINCompiler-linux",
        Path("/tmp/nms_exml/MBINCompiler"),
        pak_dir / "MBINCompiler.exe",
        pak_dir / "MBINCompiler",
        pak_dir.parent / "MBINCompiler.exe",
        pak_dir.parent / "MBINCompiler",
        pak_dir.parent.parent / "MBINCompiler.exe",
        pak_dir.parent.parent / "MBINCompiler",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    found = shutil.which("MBINCompiler") or shutil.which("MBINCompiler.exe")
    return Path(found) if found else None


def _rotate_xyz(
    v: tuple[float, float, float], rot_deg: tuple[float, float, float]
) -> tuple[float, float, float]:
    x, y, z = v
    rx, ry, rz = (math.radians(rot_deg[0]), math.radians(rot_deg[1]), math.radians(rot_deg[2]))
    cy, sy = math.cos(rx), math.sin(rx)
    y, z = y * cy - z * sy, y * sy + z * cy
    cx, sx = math.cos(ry), math.sin(ry)
    x, z = x * cx + z * sx, -x * sx + z * cx
    cz, sz = math.cos(rz), math.sin(rz)
    x, y = x * cz - y * sz, x * sz + y * cz
    return (x, y, z)


def _normalize_vec3(v: tuple[float, float, float]) -> tuple[float, float, float]:
    x, y, z = v
    m = math.sqrt(x * x + y * y + z * z)
    if m <= 1e-9:
        return (0.0, 0.0, 1.0)
    return (x / m, y / m, z / m)


def _combine_transform(parent: Transform, local: Transform) -> Transform:
    psx, psy, psz = parent.scale
    lpx, lpy, lpz = local.position
    sp = (lpx * psx, lpy * psy, lpz * psz)
    rp = _rotate_xyz(sp, parent.rotation)
    return Transform(
        position=(parent.position[0] + rp[0], parent.position[1] + rp[1], parent.position[2] + rp[2]),
        rotation=(
            parent.rotation[0] + local.rotation[0],
            parent.rotation[1] + local.rotation[1],
            parent.rotation[2] + local.rotation[2],
        ),
        scale=(psx * local.scale[0], psy * local.scale[1], psz * local.scale[2]),
    )


def _scene_geometry_instances(scene_root) -> list[tuple[str, Transform]]:
    out: list[tuple[str, Transform]] = []

    def walk(node, world: Transform):
        composed = _combine_transform(world, node.transform)
        if node.geometry_ref and str(node.node_type).upper() != "COLLISION":
            out.append((node.geometry_ref, composed))
        for child in node.children:
            walk(child, composed)

    walk(scene_root, Transform.identity())
    return out


def _apply_transform_to_mesh(mesh: Mesh, transform: Transform) -> Mesh:
    px, py, pz = transform.position
    sx, sy, sz = transform.scale
    rot = transform.rotation

    vertices = []
    for vx, vy, vz in mesh.vertices:
        x, y, z = vx * sx, vy * sy, vz * sz
        x, y, z = _rotate_xyz((x, y, z), rot)
        vertices.append((x + px, y + py, z + pz))

    normals = []
    for nx, ny, nz in mesh.normals:
        x, y, z = _rotate_xyz((nx, ny, nz), rot)
        normals.append(_normalize_vec3((x, y, z)))

    return Mesh(
        vertices=tuple(vertices),
        normals=tuple(normals),
        uvs=mesh.uvs,
        indices=mesh.indices,
    )


def _mesh_is_valid(mesh: Mesh) -> bool:
    if mesh.vertex_count == 0 or mesh.index_count == 0:
        return False
    if max(mesh.indices, default=-1) >= mesh.vertex_count:
        return False
    return True


def load_template_preview_meshes(resource_filename: str) -> Tuple[List[object], str]:
    try:
        from nmstoolkit.adapters.hgpak_adapter import HgpakAdapter
        from nmstoolkit.adapters.mbin_compiler_adapter import MbinCompilerAdapter
        from nmstoolkit.core.geometry_exml_fallback import parse_geometry_aabb_fallback
        from nmstoolkit.core.geometry_parser import parse_geometry
        from nmstoolkit.core.geometry_stream_exml_parser import parse_geometry_stream_exml
        from nmstoolkit.core.scene_parser import parse_scene
    except Exception as exc:
        return [], f"Preview unavailable: dependency import failed ({exc})."

    settings = QSettings("NMSToolkit", "NMSToolkit")
    game_dir_value = settings.value("game_dir", "")
    if not game_dir_value:
        return [], "Preview unavailable: set game directory first."
    pak_dir = _resolve_pak_dir(Path(str(game_dir_value)))
    if pak_dir is None:
        return [], "Preview unavailable: PCBANKS not found in configured game directory."
    mbin_compiler = _find_mbin_compiler(pak_dir)
    if mbin_compiler is None:
        return [], "Preview unavailable: MBINCompiler not found."

    scene_path = _normalize_ref(resource_filename)
    scene_pak = pak_dir / "NMSARC.EntitySceneMBIN.pak"
    if not scene_pak.exists():
        return [], "Preview unavailable: NMSARC.EntitySceneMBIN.pak missing."

    converter = MbinCompilerAdapter(mbin_compiler)
    with HgpakAdapter.from_path(scene_pak) as pak:
        scene_files = {_normalize_ref(f): f for f in pak.list_files()}
        found_scene = scene_files.get(scene_path)
        if not found_scene:
            return [], "Preview unavailable: scene not found in gamefiles."
        scene_bytes = pak.extract(paths=[found_scene])[found_scene]

    scene_exml = converter.convert(scene_bytes)
    scene_root = parse_scene(scene_exml)
    instances = [(_normalize_ref(r), t) for r, t in _scene_geometry_instances(scene_root) if r]
    if not instances:
        return [], "Preview unavailable: scene contains no geometry references."

    geo_map = {}
    missing = {r for r, _ in instances}
    for mesh_pak in sorted(pak_dir.glob("NMSARC.Mesh*.pak")):
        if not missing:
            break
        with HgpakAdapter.from_path(mesh_pak) as pak:
            files = {_normalize_ref(f): f for f in pak.list_files()}
            to_extract = []
            for ref in list(missing):
                data_ref = ref.replace(".geometry.mbin", ".geometry.data.mbin")
                found_any = False
                for candidate in (ref, ref + ".pc"):
                    if candidate in files:
                        to_extract.append(files[candidate])
                        found_any = True
                for data_candidate in (data_ref, data_ref + ".pc"):
                    if data_candidate in files:
                        to_extract.append(files[data_candidate])
                if found_any:
                    missing.discard(ref)
            if not to_extract:
                continue
            extracted = pak.extract(paths=to_extract)
            for p, b in extracted.items():
                n = _normalize_ref(p)
                geo_map[n] = b
                if n.endswith(".pc"):
                    geo_map[n[:-3]] = b

    decoded_by_ref = {}
    meshes: List[Mesh] = []
    stream_ok = 0
    binary_ok = 0
    fallback_ok = 0
    for ref, world in instances:
        base_meshes = decoded_by_ref.get(ref)
        if base_meshes is None:
            base_meshes = []
            decoded_by_ref[ref] = base_meshes
            geo_bytes = geo_map.get(ref) or geo_map.get(ref + ".pc")
            if geo_bytes is None:
                continue
            geo_exml = ""
            try:
                geo_exml = converter.convert(geo_bytes)
            except Exception:
                pass
            data_ref = ref.replace(".geometry.mbin", ".geometry.data.mbin")
            data_bytes = geo_map.get(data_ref) or geo_map.get(data_ref + ".pc")
            if geo_exml and data_bytes is not None:
                try:
                    stream_exml = converter.convert(data_bytes)
                    stream_meshes = parse_geometry_stream_exml(geo_exml, stream_exml)
                    if stream_meshes:
                        base_meshes = [m for m in stream_meshes if _mesh_is_valid(m)]
                        if base_meshes:
                            stream_ok += 1
                        decoded_by_ref[ref] = base_meshes
                except Exception:
                    pass
            if not base_meshes:
                binary_meshes = parse_geometry(geo_bytes)
                if binary_meshes:
                    base_meshes = [m for m in binary_meshes if _mesh_is_valid(m)]
                    if base_meshes:
                        binary_ok += 1
                    decoded_by_ref[ref] = base_meshes
            if not base_meshes and geo_exml:
                fallback = parse_geometry_aabb_fallback(geo_exml)
                base_meshes = [m for m in fallback if _mesh_is_valid(m)]
                if base_meshes:
                    fallback_ok += 1
                decoded_by_ref[ref] = base_meshes
        if not base_meshes:
            continue
        meshes.extend(_apply_transform_to_mesh(m, world) for m in base_meshes)

    QApplication.processEvents()
    if not meshes:
        return [], "Preview unavailable: no renderable mesh data found."
    full_refs = stream_ok + binary_ok
    if full_refs and not fallback_ok:
        fidelity = "full geometry render"
    elif full_refs and fallback_ok:
        fidelity = "mixed geometry render"
    else:
        fidelity = "fallback geometry render"
    return meshes, (
        f"Preview loaded ({len(meshes)} meshes; {fidelity}; "
        f"stream={stream_ok}, binary={binary_ok}, fallback={fallback_ok})."
    )
