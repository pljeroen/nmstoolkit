"""Main application window."""

from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import Qt, QSettings
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from nmstoolkit.backup import create_backup
from nmstoolkit.core.icon_cache import IconCache
from nmstoolkit.core.icon_extractor import IconExtractor
from nmstoolkit.core.save_file import SaveFile
from nmstoolkit.core.save_scanner import SaveProfile, scan_for_profiles
from nmstoolkit.gui.widgets.icon_provider import IconProvider
from nmstoolkit.gui.tabs.json_editor_tab import JsonEditorTab
from nmstoolkit.gui.tabs.exosuit_tab import ExosuitTab
from nmstoolkit.gui.tabs.ships_tab import ShipsTab
from nmstoolkit.gui.tabs.corvette_tab import CorvetteTab
from nmstoolkit.gui.tabs.multitools_tab import MultitoolsTab
from nmstoolkit.gui.tabs.squadron_tab import SquadronTab
from nmstoolkit.gui.tabs.freighter_tab import FreighterTab
from nmstoolkit.gui.tabs.frigates_tab import FrigatesTab
from nmstoolkit.gui.tabs.vehicles_tab import VehiclesTab
from nmstoolkit.gui.tabs.companions_tab import CompanionsTab
from nmstoolkit.gui.tabs.bases_tab import BasesTab
from nmstoolkit.gui.tabs.settlements_tab import SettlementsTab
from nmstoolkit.gui.tabs.discoveries_tab import DiscoveriesTab
from nmstoolkit.gui.tabs.milestones_tab import MilestonesTab
from nmstoolkit.gui.tabs.expedition_tab import ExpeditionTab
from nmstoolkit.gui.tabs.account_tab import AccountTab
from nmstoolkit.gui.tabs.recipe_finder_tab import RecipeFinderTab
from nmstoolkit.gui.tabs.fish_finder_tab import FishFinderTab

DATA_DIR = Path(__file__).parent.parent / "data"
KEY_MAP_PATH = DATA_DIR / "jsonmap.txt"
ACCOUNT_KEY_MAP_PATH = DATA_DIR / "jsonmapac.txt"


def _detect_save_dirs() -> List[Path]:
    """Return candidate NMS save directories that exist on this system."""
    candidates = []
    home = Path.home()

    # Steam (Linux/Proton)
    steam_linux = home / ".local/share/Steam/steamapps/compatdata/275850/pfx/drive_c/users/steamuser/AppData/Roaming/HelloGames/NMS"
    if steam_linux.exists():
        candidates.append(steam_linux)

    # Steam (Windows)
    steam_win = Path("C:/Users") / home.name / "AppData/Roaming/HelloGames/NMS"
    if steam_win.exists():
        candidates.append(steam_win)

    # GOG (Windows)
    gog = home / "AppData/Roaming/HelloGames/NMS"
    if gog.exists() and gog not in candidates:
        candidates.append(gog)

    return candidates


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NMS Toolkit — No Man's Sky Save Editor")
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)

        self._save_file: Optional[SaveFile] = None
        self._save_path: Optional[Path] = None
        self._account_file: Optional[SaveFile] = None
        self._account_path: Optional[Path] = None

        self._profiles: List[SaveProfile] = []
        self._settings = QSettings("NMSToolkit", "NMSToolkit")

        self._auto_load_icons()
        self._build_ui()
        self._build_menu()
        self._scan_saves()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(4, 4, 4, 4)

        # Save selector bar
        selector_bar = QWidget()
        selector_layout = QHBoxLayout(selector_bar)
        selector_layout.setContentsMargins(4, 2, 4, 2)

        selector_layout.addWidget(QLabel("Profile:"))
        self._profile_combo = QComboBox()
        self._profile_combo.setMinimumWidth(200)
        self._profile_combo.currentIndexChanged.connect(self._on_profile_changed)
        selector_layout.addWidget(self._profile_combo)

        selector_layout.addWidget(QLabel("Slot:"))
        self._slot_combo = QComboBox()
        self._slot_combo.setMinimumWidth(250)
        selector_layout.addWidget(self._slot_combo)

        self._load_slot_btn = QPushButton("Load")
        self._load_slot_btn.clicked.connect(self._on_load_slot)
        self._load_slot_btn.setEnabled(False)
        selector_layout.addWidget(self._load_slot_btn)

        selector_layout.addStretch()

        self._context_combo = QComboBox()
        self._context_combo.addItems(["Base Context", "Expedition Context"])
        self._context_combo.setEnabled(False)
        self._context_combo.currentIndexChanged.connect(self._on_context_changed)
        selector_layout.addWidget(QLabel("Context:"))
        selector_layout.addWidget(self._context_combo)

        layout.addWidget(selector_bar)

        # File info label
        self._file_label = QLabel("No file loaded")
        self._file_label.setStyleSheet("color: #aaa; font-size: 11px; margin-left: 4px;")
        layout.addWidget(self._file_label)

        # Tab widget
        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(True)
        layout.addWidget(self._tabs)

        # Create placeholder tabs (populated when save is loaded)
        self._main_tab = self._create_main_tab()
        self._tabs.addTab(self._main_tab, "Main")

        # Editor tabs — created but populated on load
        self._json_tab = JsonEditorTab()
        self._exosuit_tab = ExosuitTab()
        self._ships_tab = ShipsTab()
        self._corvette_tab = CorvetteTab()
        self._multitools_tab = MultitoolsTab()
        self._squadron_tab = SquadronTab()
        self._freighter_tab = FreighterTab()
        self._frigates_tab = FrigatesTab()
        self._vehicles_tab = VehiclesTab()
        self._companions_tab = CompanionsTab()
        self._bases_tab = BasesTab()
        self._settlements_tab = SettlementsTab()
        self._discoveries_tab = DiscoveriesTab()
        self._milestones_tab = MilestonesTab()
        self._expedition_tab = ExpeditionTab()
        self._account_tab = AccountTab()
        self._recipe_finder_tab = RecipeFinderTab()
        self._fish_finder_tab = FishFinderTab()

        self._tabs.addTab(self._exosuit_tab, "Exosuit")
        self._tabs.addTab(self._ships_tab, "Ships")
        self._tabs.addTab(self._corvette_tab, "Corvette")
        self._tabs.addTab(self._multitools_tab, "Multitool")
        self._tabs.addTab(self._squadron_tab, "Squadron")
        self._tabs.addTab(self._freighter_tab, "Freighter")
        self._tabs.addTab(self._frigates_tab, "Frigates")
        self._tabs.addTab(self._vehicles_tab, "Vehicles")
        self._tabs.addTab(self._companions_tab, "Companions")
        self._tabs.addTab(self._bases_tab, "Bases & Storage")
        self._tabs.addTab(self._settlements_tab, "Settlements")
        self._tabs.addTab(self._discoveries_tab, "Discovery")
        self._tabs.addTab(self._milestones_tab, "Milestones")
        self._tabs.addTab(self._expedition_tab, "Expedition")
        self._tabs.addTab(self._recipe_finder_tab, "Recipes")
        self._tabs.addTab(self._fish_finder_tab, "Fish Finder")
        self._tabs.addTab(self._account_tab, "Account")
        self._tabs.addTab(self._json_tab, "JSON Editor")

        # Status bar
        self.statusBar().showMessage("Ready")

    def _create_main_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        form = QFormLayout()
        self._save_path_label = QLabel("—")
        self._version_label = QLabel("—")
        self._platform_label = QLabel("—")
        self._game_mode_label = QLabel("—")
        self._save_name_label = QLabel("—")
        self._context_label = QLabel("—")

        form.addRow("Save File:", self._save_path_label)
        form.addRow("Version:", self._version_label)
        form.addRow("Platform:", self._platform_label)
        form.addRow("Game Mode:", self._game_mode_label)
        form.addRow("Save Name:", self._save_name_label)
        form.addRow("Active Context:", self._context_label)
        layout.addLayout(form)

        # Buttons
        btn_layout = QHBoxLayout()
        self._reload_btn = QPushButton("Reload")
        self._reload_btn.clicked.connect(self._on_reload)
        self._reload_btn.setEnabled(False)
        btn_layout.addWidget(self._reload_btn)

        self._save_btn = QPushButton("Save Changes")
        self._save_btn.clicked.connect(self._on_save)
        self._save_btn.setEnabled(False)
        btn_layout.addWidget(self._save_btn)

        self._save_as_btn = QPushButton("Save As...")
        self._save_as_btn.clicked.connect(self._on_save_as)
        self._save_as_btn.setEnabled(False)
        btn_layout.addWidget(self._save_as_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        layout.addStretch()
        return widget

    def _build_menu(self):
        menu = self.menuBar()

        file_menu = menu.addMenu("&File")
        file_menu.addAction("&Open Save...", self._on_open, "Ctrl+O")
        file_menu.addAction("Open &Account Data...", self._on_open_account)
        file_menu.addSeparator()
        file_menu.addAction("Add Save &Directory...", self._on_add_save_dir)
        file_menu.addAction("&Rescan Saves", self._scan_saves, "Ctrl+R")
        file_menu.addSeparator()
        file_menu.addAction("&Save", self._on_save, "Ctrl+S")
        file_menu.addAction("Save &As...", self._on_save_as, "Ctrl+Shift+S")
        file_menu.addSeparator()
        file_menu.addAction("&Quit", self.close, "Ctrl+Q")

        tools_menu = menu.addMenu("&Tools")
        tools_menu.addAction("Extract Game &Icons...", self._on_extract_icons)

    # ------------------------------------------------------------------
    # Icon extraction
    # ------------------------------------------------------------------

    def _auto_load_icons(self):
        """Load cached icons and catalogue at startup if available.

        Rebuilds icon_map from catalogue if the catalogue has more items
        than the current map (handles stale maps from prior sessions).
        """
        cache_dir = DATA_DIR / "icons"

        from nmstoolkit.gui.widgets.inventory_grid import set_icon_provider, set_catalogue
        from nmstoolkit.core.game_catalogue import GameCatalogue

        # Load cached catalogue if available
        catalogue = None
        cat_path = cache_dir / "game_catalogue.json"
        if cat_path.exists():
            try:
                catalogue = GameCatalogue.from_json(cat_path.read_text())
                set_catalogue(catalogue)
            except Exception:
                pass

        icon_cache = IconCache(cache_dir)
        extractor = IconExtractor(Path(), cache_dir)
        icon_map = extractor.load_icon_map()

        # Rebuild icon_map from catalogue if stale
        if catalogue is not None:
            all_items = catalogue.products + catalogue.substances + catalogue.technologies
            rebuilt_map = {}
            for item in all_items:
                item_id = item.get("id", "")
                icon_path = item.get("icon", "")
                if not item_id or not icon_path:
                    continue
                if icon_cache.get_icon(icon_path) is not None:
                    rebuilt_map[item_id] = icon_path
                    if not item_id.startswith("^"):
                        rebuilt_map["^" + item_id] = icon_path

            if len(rebuilt_map) > len(icon_map):
                icon_map = rebuilt_map
                extractor.save_icon_map(icon_map)

        if not icon_map:
            return

        provider = IconProvider(icon_cache, catalogue, icon_map=icon_map)
        set_icon_provider(provider)

    def _on_extract_icons(self):
        """Extract game icons from PAK and build catalogue-based icon map."""
        last_game_dir = self._settings.value(
            "game_dir", "/media/sf_tdd/No Man's Sky"
        )
        game_dir = QFileDialog.getExistingDirectory(
            self, "Select NMS Game Directory", last_game_dir
        )
        if not game_dir:
            return

        self._settings.setValue("game_dir", game_dir)
        game_path = Path(game_dir)

        # Auto-detect pak_dir: user may have selected game root, GAMEDATA, or PCBANKS
        pak_dir = game_path / "GAMEDATA" / "PCBANKS"
        if not pak_dir.exists():
            if (game_path / "PCBANKS").exists():
                pak_dir = game_path / "PCBANKS"
                game_path = game_path.parent  # fix game_path for IconExtractor
            elif game_path.name.upper() == "PCBANKS":
                pak_dir = game_path
                game_path = game_path.parent.parent
            elif (game_path / "NMSARC.TexUI.pak").exists():
                pak_dir = game_path
                game_path = game_path.parent.parent

        cache_dir = DATA_DIR / "icons"

        extractor = IconExtractor(game_path, cache_dir)

        progress = QProgressDialog("Extracting icon textures from PAK...", None, 0, 0, self)
        progress.setWindowTitle("Extract Game Icons")
        progress.setMinimumDuration(0)
        progress.show()
        QApplication.processEvents()

        count = extractor.extract_all_icons()

        if count == 0:
            progress.close()
            QMessageBox.warning(
                self, "No Icons Found",
                f"No icon textures found in:\n{game_path}\n\n"
                "Check that the game directory contains GAMEDATA/PCBANKS/NMSARC.TexUI.pak"
            )
            return

        progress.setLabelText(f"Building game catalogue ({count} icons extracted)...")
        QApplication.processEvents()

        # Build catalogue from EXML to get real DDS paths
        icon_map = {}
        mbin_compiler = self._find_mbin_compiler(pak_dir)

        if mbin_compiler is not None:
            try:
                from nmstoolkit.core.game_data_pipeline import build_catalogue
                from nmstoolkit.gui.widgets.inventory_grid import set_catalogue

                cat = build_catalogue(str(pak_dir), str(mbin_compiler))
                set_catalogue(cat)

                # Save catalogue for future sessions
                cat_path = cache_dir / "game_catalogue.json"
                cat_path.write_text(cat.to_json())

                # Build icon_map from catalogue: real DDS paths matched to cache
                icon_cache = IconCache(cache_dir)
                all_items = cat.products + cat.substances + cat.technologies
                for item in all_items:
                    item_id = item.get("id", "")
                    icon_path = item.get("icon", "")
                    if not item_id or not icon_path:
                        continue
                    if icon_cache.get_icon(icon_path) is not None:
                        icon_map[item_id] = icon_path
                        if not item_id.startswith("^"):
                            icon_map["^" + item_id] = icon_path

            except Exception as e:
                progress.close()
                QMessageBox.warning(
                    self, "Catalogue Build Failed",
                    f"Icon textures extracted ({count}), but catalogue build failed:\n{e}\n\n"
                    "Icons extracted but matching will be limited."
                )

        # Fallback: fuzzy matching from items.json if catalogue failed
        if not icon_map:
            items_path = DATA_DIR / "items.json"
            dds_paths = []
            for png_file in cache_dir.glob("*.png"):
                dds_path = png_file.stem.replace("_", "/") + ".dds"
                dds_paths.append(dds_path)
            icon_map = extractor.build_icon_map(items_path, dds_paths)

        extractor.save_icon_map(icon_map)
        progress.close()

        # Wire the icon provider
        from nmstoolkit.gui.widgets.inventory_grid import set_icon_provider, _CATALOGUE

        icon_cache = IconCache(cache_dir)
        provider = IconProvider(icon_cache, _CATALOGUE, icon_map=icon_map)
        set_icon_provider(provider)

        if self._save_file:
            self._populate_tabs()

        QMessageBox.information(
            self, "Icons Extracted",
            f"Extracted {count} icon textures.\n"
            f"Mapped {len(icon_map)} items to icons.\n\n"
            "Icons will load automatically on next startup."
        )

    @staticmethod
    def _find_mbin_compiler(pak_dir: Path) -> Path | None:
        """Locate MBINCompiler — check common locations."""
        import shutil
        candidates = [
            Path("/tmp/nms_exml/MBINCompiler"),
            pak_dir / "MBINCompiler.exe",
            pak_dir / "MBINCompiler",
            pak_dir.parent / "MBINCompiler.exe",
            pak_dir.parent / "MBINCompiler",
            pak_dir.parent.parent / "MBINCompiler.exe",
            pak_dir.parent.parent / "MBINCompiler",
        ]
        for c in candidates:
            if c.exists():
                return c
        # Check system PATH
        found = shutil.which("MBINCompiler") or shutil.which("MBINCompiler.exe")
        if found:
            return Path(found)
        return None

    # ------------------------------------------------------------------
    # Save scanning and selection
    # ------------------------------------------------------------------

    def _get_custom_save_dirs(self) -> List[Path]:
        """Load user-configured save directories from QSettings."""
        raw = self._settings.value("custom_save_dirs", [])
        if isinstance(raw, str):
            raw = [raw] if raw else []
        return [Path(d) for d in raw if d]

    def _set_custom_save_dirs(self, dirs: List[Path]):
        self._settings.setValue("custom_save_dirs", [str(d) for d in dirs])

    def _scan_saves(self):
        """Scan known + custom directories for save profiles and populate dropdowns."""
        base_dirs = _detect_save_dirs() + self._get_custom_save_dirs()
        self._profiles = scan_for_profiles(base_dirs)

        self._profile_combo.blockSignals(True)
        self._profile_combo.clear()

        if not self._profiles:
            self._profile_combo.addItem("No saves found")
            self._load_slot_btn.setEnabled(False)
        else:
            for profile in self._profiles:
                label = f"st_{profile.steam_id}" if not profile.steam_id.startswith("st_") else profile.steam_id
                slot_count = len(profile.save_slots)
                self._profile_combo.addItem(f"{label} ({slot_count} slots)")
            self._load_slot_btn.setEnabled(True)

        self._profile_combo.blockSignals(False)
        self._on_profile_changed(self._profile_combo.currentIndex())

        count = sum(len(p.save_slots) for p in self._profiles)
        self.statusBar().showMessage(
            f"Found {len(self._profiles)} profile(s) with {count} save slot(s)"
        )

    def _on_profile_changed(self, index: int):
        """Populate slot dropdown when profile selection changes."""
        self._slot_combo.clear()
        if index < 0 or index >= len(self._profiles):
            self._load_slot_btn.setEnabled(False)
            return

        profile = self._profiles[index]
        for slot in profile.save_slots:
            name = slot.save_name or f"Slot {slot.slot_number}"
            self._slot_combo.addItem(f"Slot {slot.slot_number}: {name}")

        self._load_slot_btn.setEnabled(len(profile.save_slots) > 0)

    def _on_load_slot(self):
        """Load the currently selected save slot."""
        profile_idx = self._profile_combo.currentIndex()
        slot_idx = self._slot_combo.currentIndex()

        if profile_idx < 0 or profile_idx >= len(self._profiles):
            return
        profile = self._profiles[profile_idx]
        if slot_idx < 0 or slot_idx >= len(profile.save_slots):
            return

        slot = profile.save_slots[slot_idx]
        self._load_save(slot.path)

    def _on_add_save_dir(self):
        """Let the user add a custom save directory."""
        directory = QFileDialog.getExistingDirectory(
            self, "Select Save Directory", str(Path.home())
        )
        if not directory:
            return

        custom_dirs = self._get_custom_save_dirs()
        new_dir = Path(directory)
        if new_dir not in custom_dirs:
            custom_dirs.append(new_dir)
            self._set_custom_save_dirs(custom_dirs)

        self._scan_saves()

    # ------------------------------------------------------------------
    # File open / load
    # ------------------------------------------------------------------

    def _on_open(self):
        last_dir = self._settings.value("last_open_dir", str(Path.home()))
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Save File", last_dir,
            "NMS Save Files (*.hg);;All Files (*)"
        )
        if not path:
            return

        self._settings.setValue("last_open_dir", str(Path(path).parent))
        self._load_save(Path(path))

    def _on_open_account(self):
        last_dir = self._settings.value("last_open_dir", str(Path.home()))
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Account Data", last_dir,
            "Account Data (accountdata.hg);;NMS Files (*.hg);;All Files (*)"
        )
        if not path:
            return

        self._settings.setValue("last_open_dir", str(Path(path).parent))
        self._load_account(Path(path))

    def _load_save(self, path: Path):
        try:
            sf = SaveFile.load(path, KEY_MAP_PATH)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load save:\n{e}")
            return

        self._save_file = sf
        self._save_path = path
        self._update_main_tab()
        self._populate_tabs()

        self._reload_btn.setEnabled(True)
        self._save_btn.setEnabled(True)
        self._save_as_btn.setEnabled(True)
        self._context_combo.setEnabled(sf.expedition_context is not None)

        self._file_label.setText(str(path))
        self.statusBar().showMessage(f"Loaded {path.name}")

        # Try to load account data from same directory
        account_path = path.parent / "accountdata.hg"
        if account_path.exists() and self._account_file is None:
            self._load_account(account_path)

    def _load_account(self, path: Path):
        try:
            af = SaveFile.load(path, ACCOUNT_KEY_MAP_PATH)
        except Exception as e:
            QMessageBox.warning(self, "Warning", f"Failed to load account data:\n{e}")
            return

        self._account_file = af
        self._account_path = path
        self._account_tab.set_data(af.data)
        self.statusBar().showMessage(f"Loaded account data from {path.name}")

    def _update_main_tab(self):
        sf = self._save_file
        self._save_path_label.setText(str(self._save_path))
        self._version_label.setText(str(sf.version))
        self._platform_label.setText(sf.platform or "—")
        self._context_label.setText(sf.active_context or "—")

        common = sf.data.get("CommonStateData", {})
        self._save_name_label.setText(common.get("SaveName", "—"))

        ctx = sf.base_context
        if ctx:
            self._game_mode_label.setText(str(ctx.get("GameMode", "—")))

    def _populate_tabs(self):
        sf = self._save_file
        context = "base" if self._context_combo.currentIndex() == 0 else "expedition"
        psd = sf.player_state_data(context)

        if psd is None:
            self.statusBar().showMessage(f"No {context} context data available")
            return

        self._exosuit_tab.set_data(psd)
        self._ships_tab.set_data(psd)
        self._corvette_tab.set_data(psd)
        self._multitools_tab.set_data(psd)
        self._squadron_tab.set_data(psd)
        self._freighter_tab.set_data(psd)
        self._frigates_tab.set_data(psd)
        self._vehicles_tab.set_data(psd)
        self._companions_tab.set_data(psd)
        self._bases_tab.set_data(psd)
        self._settlements_tab.set_data(psd)
        self._discoveries_tab.set_data(sf.data.get("DiscoveryManagerData", {}))
        self._milestones_tab.set_data(psd)
        self._expedition_tab.set_data(
            psd, common_state=sf.data.get("CommonStateData", {})
        )
        self._recipe_finder_tab.set_data(psd)
        self._fish_finder_tab.set_data(psd)
        self._json_tab.set_data(sf.data)

    def _on_context_changed(self, index):
        if self._save_file:
            self._populate_tabs()

    def _on_reload(self):
        if self._save_path:
            self._load_save(self._save_path)

    def _on_save(self):
        if not self._save_file or not self._save_path:
            return
        self._do_save(self._save_path)

    def _on_save_as(self):
        if not self._save_file:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save As", str(self._save_path or ""),
            "NMS Save Files (*.hg);;All Files (*)"
        )
        if path:
            self._do_save(Path(path))

    def _do_save(self, path: Path):
        try:
            if path.exists():
                backup_path = create_backup(path)
                self.statusBar().showMessage(f"Backup created: {backup_path.name}")

            self._save_file.save(path)
            self._save_path = path
            self.statusBar().showMessage(f"Saved to {path.name}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save:\n{e}")
