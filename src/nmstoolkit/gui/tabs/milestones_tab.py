"""Milestones & Reputation editor tab."""

from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from nmstoolkit.gui.widgets.stat_editor import StatEditor


# Reputation stat IDs → friendly names
_REPUTATION_STATS = [
    ("^TRA_STANDING", "Gek"),
    ("^WAR_STANDING", "Vy'keen"),
    ("^EXP_STANDING", "Korvax"),
    ("^PIRATE_STAND", "Pirate"),
    ("^BUI_STANDING", "Builder"),
    ("^NEXUS_STAND", "Nexus"),
]

_GUILD_STATS = [
    ("^EGUILD_STAND", "Explorer Guild"),
    ("^TGUILD_STAND", "Trader Guild"),
    ("^WGUILD_STAND", "Warrior Guild"),
]

# Friendly names for stat IDs
_STAT_FRIENDLY = {
    # Discovery
    "^DISC_SYSTEMS": "Systems Discovered",
    "^DISC_PLANETS": "Planets Discovered",
    "^DISC_CREATURES": "Creatures Discovered",
    "^DISC_FLORA": "Flora Discovered",
    "^DISC_MINERALS": "Minerals Discovered",
    "^DISC_ABAND": "Abandoned Buildings Found",
    "^DISC_ALL_CREATU": "Planets Fully Scanned (Fauna)",
    "^DISC_CRE_AIR": "Air Creatures Discovered",
    "^DISC_CRE_CAVE": "Cave Creatures Discovered",
    "^DISC_CRE_LAND": "Land Creatures Discovered",
    "^DISC_CRE_WATER": "Water Creatures Discovered",
    "^DISC_CRE_WEIRD": "Exotic Creatures Discovered",
    "^DISC_P_COLD": "Cold Planets Discovered",
    "^DISC_P_DEAD": "Dead Planets Discovered",
    "^DISC_P_DUST": "Dust Planets Discovered",
    "^DISC_P_HOT": "Hot Planets Discovered",
    "^DISC_P_LAVA": "Volcanic Planets Discovered",
    "^DISC_P_LUSH": "Lush Planets Discovered",
    "^DISC_P_RAD": "Radioactive Planets Discovered",
    "^DISC_P_RGB": "Exotic Planets Discovered",
    "^DISC_P_TOX": "Toxic Planets Discovered",
    "^DISC_P_WEIRD": "Anomalous Planets Discovered",
    "^DISC_RARE_SYS": "Rare Systems Discovered",
    "^DISC_WAYPOINTS": "Waypoints Discovered",
    "^DIS_CREA_BANK": "Creature Scans Uploaded",
    "^DIS_FLORA_BANK": "Flora Scans Uploaded",
    "^DIS_FLORA_BARR": "Barren Flora Discovered",
    "^DIS_FLORA_FROZ": "Frozen Flora Discovered",
    "^DIS_FLORA_HOT": "Hot Flora Discovered",
    "^DIS_FLORA_LUSH": "Lush Flora Discovered",
    "^DIS_FLORA_RADIO": "Radioactive Flora Discovered",
    "^DIS_FLORA_TOXIC": "Toxic Flora Discovered",
    "^DIS_FLORA_WEIRD": "Exotic Flora Discovered",
    "^DIS_MIN_BANK": "Mineral Scans Uploaded",
    "^DIS_PLANET_BANK": "Planet Scans Uploaded",
    "^RARE_SCANNED": "Rare Creatures Scanned",
    "^BIG_SCAN_CRE": "Largest Creature Scan Value",
    "^BIG_SCAN_MIN": "Largest Mineral Scan Value",
    "^BIG_SCAN_PLA": "Largest Flora Scan Value",
    "^BIG_SELLER": "Largest Single Sale",
    # Words
    "^WORDS_LEARNT": "Words Learnt (Total)",
    "^BWORDS_LEARNT": "Builder Words Learnt",
    "^EWORDS_LEARNT": "Korvax Words Learnt",
    "^TWORDS_LEARNT": "Gek Words Learnt",
    "^WWORDS_LEARNT": "Vy'keen Words Learnt",
    # Distance
    "^DIST_WALKED": "Distance Walked",
    "^DIST_FLY": "Distance Flown",
    "^DIST_WARP": "Warps",
    "^DIST_JETPACK": "Jetpack Distance",
    "^DIST_PULSE": "Pulse Distance",
    "^DIST_EXO": "Exocraft Distance",
    "^DIST_SUB": "Submarine Distance",
    "^DIST_SWAM": "Distance Swam",
    "^DIST_CRE_RIDE": "Creature Ride Distance",
    "^DIST_PET_RIDE": "Pet Ride Distance",
    "^CAVE_WALK": "Cave Exploration Distance",
    # Combat
    "^SENTINEL_KILLS": "Sentinels Killed",
    "^PIRATES_KILLED": "Pirates Killed",
    "^ENEMIES_KILLED": "Enemies Killed",
    "^DRONES_KILLED": "Drones Killed",
    "^WALKERS_KILLED": "Walkers Killed",
    "^MECHS_KILLED": "Sentinel Mechs Killed",
    "^QUADS_KILLED": "Quads Killed",
    "^CREATURES_KILL": "Creatures Killed",
    "^FIENDS_KILLED": "Biological Horrors Killed",
    "^SPIDERS_KILLED": "Spiders Killed",
    "^MINIWORM_KILL": "Sandworms Killed",
    "^C_SENT_KILLS": "Corrupted Sentinel Kills",
    "^POLICE_KILLED": "Space Police Killed",
    "^TRADERS_KILLED": "Traders Killed",
    "^PREDS_KILLED": "Predators Killed",
    "^FLORA_KILLED": "Flora Destroyed",
    "^BOUNTIES": "Bounties Collected",
    "^SPACE_BATTLES": "Space Battles",
    "^MISSION_PIRATES": "Pirate Missions Completed",
    "^AMMO_FIRED": "Ammo Fired",
    # Survival
    "^DEATHS": "Deaths",
    "^LONGEST_LIFE": "Longest Life (seconds)",
    "^LONGEST_LIFE_EX": "Longest Extreme Life (seconds)",
    "^EXTREME_WALK": "Extreme Survival Distance",
    "^STORM_WALK": "Storm Survival Distance",
    "^EX_HOT_WALK": "Extreme Heat Survival",
    "^EX_RAD_WALK": "Extreme Radiation Survival",
    "^EX_TOX_WALK": "Extreme Toxic Survival",
    # Economy
    "^MONEY": "Total Units",
    "^MONEY_EVER": "Units Earned (Lifetime)",
    "^NANITES": "Total Nanites",
    "^NANITES_EVER": "Nanites Earned (Lifetime)",
    "^TRADE_UNITS": "Trade Units",
    "^TRADE_VALUE": "Trade Value",
    "^SMUGGLE_VALUE": "Smuggling Value",
    "^QS_SPENT": "Quicksilver Spent",
    "^QS_REWARDS_ON": "Quicksilver Rewards Earned",
    # Crafting & Resources
    "^ITEMS_CRAFTED": "Items Crafted",
    "^COOKING": "Meals Cooked",
    "^RES_EXTRACTED": "Resources Extracted",
    "^PLANTS_GATHERED": "Plants Gathered",
    "^PLANTS_PLANTED": "Plants Planted",
    "^PROC_PRODS": "Procedural Products Found",
    "^PROC_TECH_COUNT": "Procedural Tech Found",
    "^STORM_CRYSTALS": "Storm Crystals Collected",
    "^GRAVBALLS": "Gravitino Balls Collected",
    # Base Building
    "^PARTS_PLACED": "Base Parts Placed",
    "^BASEPARTS_GOT": "Base Parts Unlocked",
    "^ITEMS_TELEPRT": "Items Teleported",
    # Ships & Vehicles
    "^SHIPS_BOUGHT": "Ships Bought",
    "^SHIP_SUMMON": "Ships Summoned",
    "^FRIGATES": "Frigates Owned",
    "^EXPEDITIONS": "Frigate Expeditions Sent",
    "^TIMES_IN_SPACE": "Times Entered Space",
    "^BLACKHOLE_WARPS": "Black Hole Warps",
    "^PORTAL_WARPS": "Portal Warps",
    "^SENT_SHIP_CLAIM": "Sentinel Ships Claimed",
    # Pets & Creatures
    "^PETS_ADOPTED": "Pets Adopted",
    "^PETS_OWNED": "Pets Currently Owned",
    "^CREATURES_FED": "Creatures Fed",
    "^POOP_COLLECTED": "Creature Poop Collected",
    "^EGGS_GOT": "Companion Eggs Obtained",
    "^EGG_PODS": "Egg Pods Collected",
    # Fishing
    "^FISH_CAUGHT": "Fish Caught",
    "^FISH_KILLS": "Fish Killed",
    "^FISH_RELEASED": "Fish Released",
    "^FISH_TRAPPED": "Fish Trapped",
    "^FISH_CASH": "Fishing Earnings",
    # Reputation & NPCs
    "^TRA_STANDING": "Gek Standing",
    "^WAR_STANDING": "Vy'keen Standing",
    "^EXP_STANDING": "Korvax Standing",
    "^PIRATE_STAND": "Pirate Standing",
    "^BUI_STANDING": "Builder Standing",
    "^NEXUS_STAND": "Nexus Standing",
    "^EGUILD_STAND": "Explorer Guild",
    "^TGUILD_STAND": "Trader Guild",
    "^WGUILD_STAND": "Warrior Guild",
    "^ALIENS_MET": "Aliens Met",
    "^TRA_MET": "Gek Met",
    "^WAR_MET": "Vy'keen Met",
    "^EXP_MET": "Korvax Met",
    "^BUI_MET": "Builders Met",
    "^NPCS_RESCUED": "NPCs Rescued",
    # Multiplayer
    "^PLAY_SESSIONS": "Play Sessions",
    "^APP_SESSIONS": "App Sessions",
    "^MP_SESSIONS": "Multiplayer Sessions",
    "^MP_FULL_COUNT": "MP Full Groups",
    "^MP_FULL_TIME": "MP Time in Groups",
    "^MP_REP_FAILS": "MP Reputation Fails",
    "^MP_DEPOT_DONE": "MP Depot Missions Done",
    "^MP_DEPOT_HACK": "MP Depots Hacked",
    "^MP_EVENT_INDEX": "MP Event Index",
    "^MP_MIS_ACCESS": "MP Missions Accessed",
    "^NEXUS_MISSIONS": "Nexus Missions Completed",
    "^NEXUS_MISS_PQ": "Nexus Planet Quality Missions",
    "^NEXUS_MISS_QS": "Nexus QS Missions",
    "^GLOBAL_MISSION": "Community Missions",
    "^EMOTES": "Emotes Used",
    "^PHOTO_MODE_USED": "Photo Mode Used",
    "^PHOTO_COLD": "Cold Planet Photos",
    "^PHOTO_RAD": "Radioactive Planet Photos",
    # Lore & Story
    "^ATLAS_LOOPS": "Atlas Loops Completed",
    "^ATLAS_LORE": "Atlas Lore Found",
    "^ATLAS_PATH": "Atlas Path Progress",
    "^ATLAS_STORY": "Atlas Story Progress",
    "^CORE_LORE": "Core Lore Found",
    "^ABAND_LORE": "Abandoned Building Lore",
    "^BASECOMP_LORE": "Base Computer Lore",
    "^BIOSHIP_LORE": "Living Ship Lore",
    "^BUG_LORE": "Bug Lore",
    "^EXOTUT_LORE": "Exocraft Tutorial Progress",
    "^FARMER_LORE": "Farmer Quest Progress",
    "^OVERSEER_LORE": "Overseer Quest Progress",
    "^SCIENTIST_LORE": "Scientist Quest Progress",
    "^WEAPGUY_LORE": "Weapon Research Progress",
    "^PIRATES_LORE": "Pirate Lore Found",
    "^ROBOMISS_LORE": "Robot Mission Lore",
    "^SENT_MISS_LORE": "Sentinel Mission Lore",
    "^LIB_EXP_LORE": "Korvax Library Lore",
    "^LIB_TRA_LORE": "Gek Library Lore",
    "^LIB_WAR_LORE": "Vy'keen Library Lore",
    "^WATERSTORY_LORE": "Water Lore Found",
    "^WORM_LORE": "Sandworm Lore Found",
    "^HOME_REALITY": "Home Reality Progress",
    "^COMM_06_STORY": "Community Story Ch.6",
    "^COMM_09_DAY": "Community Story Day Count",
    "^COMM_09_ODD_DAY": "Community Story Odd Days",
    "^BUILDERS_INTRO": "Builder Intro Progress",
    # Settlements
    "^JUDGEMENTS": "Settlement Judgements Made",
    "^JM": "Settlement Missions",
    "^JM_BANKED": "Settlement Missions Banked",
    # Milestones & Seasons
    "^S_MILESTONES": "Season Milestones",
    "^TIME": "Total Play Time (seconds)",
    # Missions
    "^BDONE_MISSIONS": "Builder Missions Done",
    "^TDONE_MISSIONS": "Trader Missions Done",
    "^WDONE_MISSIONS": "Warrior Missions Done",
    "^WGDONE_MISSIONS": "Warrior Guild Missions Done",
    "^PIRATE_MISSIONS": "Pirate Missions Done",
    "^PIRATE_MYSTERY": "Pirate Mysteries Solved",
    "^PIRATE_SYSTEMS": "Pirate Systems Visited",
    # Misc
    "^ARTIFACT_HINTS": "Ancient Artifact Hints",
    "^ASTEROIDS": "Asteroids Mined",
    "^BIOFRIG_ATT": "Bio Frigate Attempts",
    "^BIOFRIG_EXP": "Bio Frigate Expeditions",
    "^BIOFRIG_FUE": "Bio Frigate Fuel Used",
    "^BONES_FOUND": "Ancient Bones Found",
    "^CHARTS_USED": "Navigation Charts Used",
    "^CORRUPT_PILLAR": "Corrupted Pillars Found",
    "^CRUISE": "Cruise Control",
    "^CRUISE_PROG": "Cruise Progress",
    "^DEPOTS_BROKEN": "Supply Depots Raided",
    "^DRONE_J_ALT": "Drone Alt. Journey",
    "^DRONE_PARTS": "Drone Parts Collected",
    "^DRONE_SHARDS": "Drone Shards Collected",
    "^ESEEN_SYSTEMS": "Korvax Systems Seen",
    "^TSEEN_SYSTEMS": "Gek Systems Seen",
    "^WSEEN_SYSTEMS": "Vy'keen Systems Seen",
    "^FIEND_EGG": "Whispering Eggs Collected",
    "^FPODS_BROKEN": "Flora Pods Broken",
    "^GRABBED": "Times Grabbed by Creatures",
    "^GUNSLOTREPAIRS": "Multi-Tool Slot Repairs",
    "^HEAD_REPAIRS": "Headset Repairs",
    "^PIR_FREI_SEEN": "Pirate Freighters Seen",
    "^PIR_FREI_WINS": "Pirate Freighter Battles Won",
    "^REWARD_SEED": "Reward Seeds",
    "^ROBOT2_SHOWN": "Robot Encounters",
    "^SALVAGE_LOOTED": "Salvage Looted",
    "^SPACE_POI": "Space Points of Interest",
    "^STATION_MARKER": "Space Stations Marked",
    "^STATION_VISITED": "Space Stations Visited",
    "^SURVEY_GAS": "Gas Hotspots Surveyed",
    "^SURVEY_POW": "Power Hotspots Surveyed",
    "^TECH_BOUGHT": "Tech Modules Bought",
    "^TREASURE_FOUND": "Buried Treasure Found",
    "^TUNNELLED": "Distance Tunnelled",
    "^VISIT_HOT": "Hot Planets Visited",
    "^VISIT_LUSH": "Lush Planets Visited",
    "^VISIT_PLANETS": "Planets Visited",
    "^VISIT_RAD": "Radioactive Planets Visited",
    "^VISIT_TOX": "Toxic Planets Visited",
    "^VISIT_WEIRD": "Anomalous Planets Visited",
    "^WORMHUNT": "Sandworm Hunts",
}


class MilestonesTab(QWidget):
    def __init__(self):
        super().__init__()
        self._data = None
        self._stats_by_id = {}
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Reputation — from GLOBAL_STATS standing entries
        rep_group = QGroupBox("Race Reputation (from Stats)")
        rep_layout = QFormLayout(rep_group)
        self._rep_editors = {}
        for stat_id, label in _REPUTATION_STATS:
            editor = StatEditor(label, -100, 999999)
            editor.value_changed.connect(
                lambda val, sid=stat_id: self._on_rep_changed(sid, val)
            )
            rep_layout.addRow(f"{label}:", editor)
            self._rep_editors[stat_id] = editor
        layout.addWidget(rep_group)

        # Guild standing
        guild_group = QGroupBox("Guild Standing")
        guild_layout = QFormLayout(guild_group)
        self._guild_editors = {}
        for stat_id, label in _GUILD_STATS:
            editor = StatEditor(label, 0, 999999)
            editor.value_changed.connect(
                lambda val, sid=stat_id: self._on_rep_changed(sid, val)
            )
            guild_layout.addRow(f"{label}:", editor)
            self._guild_editors[stat_id] = editor
        layout.addWidget(guild_group)

        # Stats table
        self._table = QTableWidget()
        self._table.setColumnCount(3)
        self._table.setHorizontalHeaderLabels(["Stat", "Int Value", "Float Value"])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self._table.setAlternatingRowColors(True)
        self._table.setSortingEnabled(True)
        layout.addWidget(self._table)

    def set_data(self, psd: dict):
        self._data = psd

        # Extract stats and build lookup
        global_stats = self._extract_global_stats(psd)
        self._stats_by_id = {}
        for stat in global_stats:
            sid = stat.get("Id", "")
            if sid:
                self._stats_by_id[sid] = stat

        # Populate reputation editors from stats
        for stat_id, editor in self._rep_editors.items():
            stat = self._stats_by_id.get(stat_id, {})
            val = stat.get("Value", {})
            editor.set_value(val.get("IntValue", 0) if isinstance(val, dict) else 0)

        for stat_id, editor in self._guild_editors.items():
            stat = self._stats_by_id.get(stat_id, {})
            val = stat.get("Value", {})
            editor.set_value(val.get("IntValue", 0) if isinstance(val, dict) else 0)

        # Sort stats: non-zero first, then by friendly name
        global_stats.sort(key=lambda s: (
            s.get("Value", {}).get("IntValue", 0) == 0
            and s.get("Value", {}).get("FloatValue", 0.0) == 0.0,
            _STAT_FRIENDLY.get(s.get("Id", ""), s.get("Id", ""))
        ))

        self._table.setSortingEnabled(False)
        self._table.setRowCount(len(global_stats))
        for row, stat in enumerate(global_stats):
            stat_id = stat.get("Id", "")
            friendly = _STAT_FRIENDLY.get(stat_id, stat_id.lstrip("^"))
            val = stat.get("Value", {})
            int_val = val.get("IntValue", 0)
            float_val = val.get("FloatValue", 0.0)

            self._table.setItem(row, 0, QTableWidgetItem(friendly))
            self._table.setItem(row, 1, QTableWidgetItem(str(int_val) if int_val != 0 else ""))
            float_str = f"{float_val:.1f}" if float_val != 0.0 else ""
            self._table.setItem(row, 2, QTableWidgetItem(float_str))

        self._table.setSortingEnabled(True)

        if not global_stats:
            self._table.setRowCount(1)
            self._table.setItem(0, 0, QTableWidgetItem("No stats data found"))
            self._table.setItem(0, 1, QTableWidgetItem("—"))
            self._table.setItem(0, 2, QTableWidgetItem("—"))

    def _on_rep_changed(self, stat_id: str, value: int):
        """Write changed reputation value back to the Stats array."""
        stat = self._stats_by_id.get(stat_id)
        if stat is not None:
            val = stat.get("Value", {})
            if isinstance(val, dict):
                val["IntValue"] = value
            else:
                stat["Value"] = {"IntValue": value, "FloatValue": 0.0, "Denominator": 0}

    @staticmethod
    def _extract_global_stats(psd: dict) -> list:
        """Extract GLOBAL_STATS from the Stats array."""
        stats_groups = psd.get("Stats", [])
        if not isinstance(stats_groups, list):
            return []
        for group in stats_groups:
            if isinstance(group, dict) and group.get("GroupId") == "^GLOBAL_STATS":
                return group.get("Stats", [])
        return []
