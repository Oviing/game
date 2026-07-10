"""Central definitions: tiles, resources, buildings, units, balance values.

All timers are in logic ticks; the game runs TICKS_PER_SECOND logic ticks
per real second at 1x speed.

Theme note: this is a top-down alien-planet colony. Internal identifiers keep
their original names for stability, but everything the player sees is sci-fi.
Mapping of internal key -> displayed concept:
  terrain grass=regolith, water=chasm, sand=dust, rock=ridge, gold=crystal seam
  object  tree=ore node, stone_deposit=mineral rock
  resource log=ore, plank=alloy, stone=mineral, grain=biomass, flour=protein,
           bread=rations, ore=crystal, coin=credits
  building woodcutter=Mining Rig, sawmill=Smelter, stonecutter=Excavator,
           farm=Bio-Dome, mill=Processor, bakery=Food Synth,
           goldmine=Crystal Extractor, mint=Fabricator, barracks=Barracks,
           tower=Defense Turret, castle=Command Center, enemy_hq=Alien Hive
"""

TILE = 32
MAP_W = 72
MAP_H = 72

SCREEN_W = 1280
SCREEN_H = 800

TICKS_PER_SECOND = 60

# ---------------------------------------------------------------- terrain
GRASS = "grass"        # regolith plains (walkable)
WATER = "water"        # chasm (impassable)
ROCK = "rock"          # rock ridge, unwalkable
GOLD_ROCK = "gold"     # crystal seam; extractors go next to it
SAND = "sand"          # dust flats (walkable)

WALKABLE_TERRAIN = {GRASS, SAND}

# map objects sitting on tiles
OBJ_TREE = "tree"          # ore node (renewable)
OBJ_STONE = "stone_deposit"  # mineral rock

# ---------------------------------------------------------------- resources
LOG = "log"
PLANK = "plank"
STONE = "stone"
GRAIN = "grain"
FLOUR = "flour"
BREAD = "bread"
ORE = "ore"
COIN = "coin"

RESOURCES = [LOG, PLANK, STONE, GRAIN, FLOUR, BREAD, ORE, COIN]

# player-facing names for the internal resource keys above
RESOURCE_LABEL = {
    LOG: "ore", PLANK: "alloy", STONE: "mineral", GRAIN: "biomass",
    FLOUR: "protein", BREAD: "rations", ORE: "crystal", COIN: "credits",
}

STARTING_STOCK = {LOG: 6, PLANK: 12, STONE: 8, GRAIN: 0, FLOUR: 0,
                  BREAD: 4, ORE: 0, COIN: 0}

# ---------------------------------------------------------------- buildings
# kind:
#   hq       - command center: storehouse + colonist spawn
#   gather   - a worker walks to a map object nearby and brings resource back
#   produce  - converts input buffer -> output buffer on a timer
#   military - barracks (recruits troops) / turret (shoots)
BUILDINGS = {
    "castle": dict(
        label="Command Center", kind="hq", size=(3, 3), hp=800, cost={},
        buildable=False,
    ),
    "woodcutter": dict(
        label="Mining Rig", kind="gather", size=(2, 2), hp=180,
        cost={PLANK: 2}, gathers=OBJ_TREE, output=LOG, work_ticks=240,
        radius=8,
        tip="Drones extract ore from nearby ore nodes.",
    ),
    "stonecutter": dict(
        label="Excavator", kind="gather", size=(2, 2), hp=180,
        cost={PLANK: 2}, gathers=OBJ_STONE, output=STONE, work_ticks=300,
        radius=8,
        tip="Excavates minerals from nearby mineral rock.",
    ),
    "sawmill": dict(
        label="Smelter", kind="produce", size=(2, 2), hp=200,
        cost={PLANK: 2, STONE: 1}, inputs={LOG: 1}, output=PLANK,
        work_ticks=300,
        tip="Smelts ore into metal alloy.",
    ),
    "farm": dict(
        label="Bio-Dome", kind="produce", size=(2, 2), hp=200,
        cost={PLANK: 3}, inputs={}, output=GRAIN, work_ticks=420,
        tip="Grows biomass. Needs no input.",
    ),
    "mill": dict(
        label="Processor", kind="produce", size=(2, 2), hp=200,
        cost={PLANK: 2, STONE: 1}, inputs={GRAIN: 1}, output=FLOUR,
        work_ticks=300,
        tip="Refines biomass into protein.",
    ),
    "bakery": dict(
        label="Food Synth", kind="produce", size=(2, 2), hp=200,
        cost={PLANK: 2, STONE: 2}, inputs={FLOUR: 1}, output=BREAD,
        work_ticks=300,
        tip="Synthesizes protein into rations.",
    ),
    "goldmine": dict(
        label="Crystal Extractor", kind="produce", size=(2, 2), hp=220,
        cost={PLANK: 3, STONE: 1}, inputs={BREAD: 1}, output=ORE,
        work_ticks=360, needs_gold=True,
        tip="Consumes rations to mine crystal. Build beside a crystal seam.",
    ),
    "mint": dict(
        label="Fabricator", kind="produce", size=(2, 2), hp=220,
        cost={PLANK: 2, STONE: 2}, inputs={ORE: 1, LOG: 1}, output=COIN,
        work_ticks=360,
        tip="Fabricates crystal (with ore) into credits.",
    ),
    "barracks": dict(
        label="Barracks", kind="military", size=(2, 2), hp=300,
        cost={PLANK: 3, STONE: 3}, recruits=True,
        tip="Select it to recruit Marines, Rangers and Heavies.",
    ),
    "tower": dict(
        label="Defense Turret", kind="military", size=(1, 1), hp=350,
        cost={STONE: 3, PLANK: 1}, work_ticks=0,
        attack_range=5.0, attack_dps=14.0,
        tip="Auto-fires on hostiles in range.",
    ),
    "enemy_hq": dict(
        label="Alien Hive", kind="hq", size=(3, 3), hp=900,
        cost={}, buildable=False,
    ),
    "enemy_tower": dict(
        label="Alien Spire", kind="military", size=(1, 1), hp=300,
        cost={}, buildable=False,
        attack_range=5.0, attack_dps=12.0,
    ),
}

BUILD_MENU = ["woodcutter", "sawmill", "stonecutter", "farm", "mill",
              "bakery", "goldmine", "mint", "barracks", "tower"]

# how many input units a building buffers at most (per input resource)
INPUT_BUFFER_CAP = 3
# produced goods waiting for pickup at most
OUTPUT_BUFFER_CAP = 3

# territory: may build within this many tiles of command center / owned buildings
TERRITORY_RADIUS = 10

# ---------------------------------------------------------------- units
UNIT_SPEED = 2.6            # tiles per second (carriers/colonists)
SETTLER_SPAWN_TICKS = 420   # command center produces a colonist this often
MAX_SETTLERS = 14           # carriers/builders cap (troops not counted)

MELEE_RANGE = 0.9           # tiles
AGGRO_RANGE = 4.5           # auto-engage distance
BUILDER_BUILD_TICKS = 360   # construction time once builder is on site

# ---------------------------------------------------------------- troops
# range <= MELEE_RANGE means a melee unit; larger means it shoots.
# cost is spent from the warehouse when the recruit is queued.
TROOPS = {
    "marine": dict(
        label="Marine", team="player", sprite="marine",
        hp=60, dps=11.0, speed=2.3, range=MELEE_RANGE,
        cost={COIN: 2, BREAD: 1}, recruit_ticks=240,
        tip="Balanced melee trooper.",
    ),
    "ranger": dict(
        label="Ranger", team="player", sprite="ranger",
        hp=42, dps=8.0, speed=2.5, range=5.0,
        cost={COIN: 2, PLANK: 1}, recruit_ticks=260,
        tip="Fragile ranged trooper; shoots from afar.",
    ),
    "heavy": dict(
        label="Heavy", team="player", sprite="heavy",
        hp=120, dps=15.0, speed=1.6, range=MELEE_RANGE,
        cost={COIN: 3, BREAD: 1, PLANK: 2}, recruit_ticks=360,
        tip="Slow, tanky bruiser that wrecks buildings.",
    ),
    # --- enemy troop types ---
    "alien": dict(
        label="Alien", team="enemy", sprite="alien",
        hp=55, dps=9.0, speed=2.2, range=MELEE_RANGE,
        cost={}, recruit_ticks=0,
    ),
    "spitter": dict(
        label="Spitter", team="enemy", sprite="spitter",
        hp=40, dps=7.0, speed=2.1, range=4.5,
        cost={}, recruit_ticks=0,
    ),
    "scout": dict(
        label="Scout", team="enemy", sprite="scout",
        hp=30, dps=5.0, speed=3.1, range=MELEE_RANGE,
        cost={}, recruit_ticks=0,
    ),
}

PLAYER_TROOPS = ["marine", "ranger", "heavy"]

# ---------------------------------------------------------------- enemy AI
RAID_FIRST_TICKS = 60 * TICKS_PER_SECOND      # first raid after 60 s
RAID_PERIOD_TICKS = 100 * TICKS_PER_SECOND    # then every 100 s
RAID_SIZE_START = 2
RAID_SIZE_MAX = 6
ENEMY_GUARDS = 4            # troops defending the hive at start
ENEMY_GUARD_LEASH = 8.0     # guards chase this far from the hive

# hive reinforcement: regrows guards over time up to a cap
ENEMY_TRAIN_TICKS = 16 * TICKS_PER_SECOND
ENEMY_MAX_GUARDS = 9

# scouts patrol widely; if they spot the player they trigger an early raid
SCOUT_COUNT = 2
SCOUT_LEASH = 24.0
SCOUT_DETECT_RANGE = 9.0
RAID_REACT_MIN_GAP = 25 * TICKS_PER_SECOND     # min ticks between reactive raids

TREE_REGROW_TICKS = 90 * TICKS_PER_SECOND     # a mined ore node regrows
