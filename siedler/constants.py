"""Central definitions: tiles, resources, buildings, units, balance values.

All timers are in logic ticks; the game runs TICKS_PER_SECOND logic ticks
per real second at 1x speed.
"""

TILE = 32
MAP_W = 72
MAP_H = 72

SCREEN_W = 1280
SCREEN_H = 800

TICKS_PER_SECOND = 60

# ---------------------------------------------------------------- terrain
GRASS = "grass"
WATER = "water"
ROCK = "rock"          # mountain, unwalkable
GOLD_ROCK = "gold"     # gold-bearing mountain, mines go next to it
SAND = "sand"

WALKABLE_TERRAIN = {GRASS, SAND}

# map objects sitting on tiles
OBJ_TREE = "tree"
OBJ_STONE = "stone_deposit"

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

STARTING_STOCK = {LOG: 6, PLANK: 12, STONE: 8, GRAIN: 0, FLOUR: 0,
                  BREAD: 4, ORE: 0, COIN: 0}

# ---------------------------------------------------------------- buildings
# kind:
#   hq       - castle: storehouse + settler spawn
#   gather   - worker walks to a map object nearby and brings resource back
#   produce  - converts input buffer -> output buffer on a timer
#   military - barracks (trains soldiers) / tower (shoots)
BUILDINGS = {
    "castle": dict(
        label="Castle", kind="hq", size=(3, 3), hp=800, cost={},
        buildable=False,
    ),
    "woodcutter": dict(
        label="Woodcutter", kind="gather", size=(2, 2), hp=180,
        cost={PLANK: 2}, gathers=OBJ_TREE, output=LOG, work_ticks=240,
        radius=8,
        tip="Worker fells nearby trees and yields logs.",
    ),
    "stonecutter": dict(
        label="Stonecutter", kind="gather", size=(2, 2), hp=180,
        cost={PLANK: 2}, gathers=OBJ_STONE, output=STONE, work_ticks=300,
        radius=8,
        tip="Worker quarries nearby stone deposits.",
    ),
    "sawmill": dict(
        label="Sawmill", kind="produce", size=(2, 2), hp=200,
        cost={PLANK: 2, STONE: 1}, inputs={LOG: 1}, output=PLANK,
        work_ticks=300,
        tip="Saws logs into planks.",
    ),
    "farm": dict(
        label="Farm", kind="produce", size=(2, 2), hp=200,
        cost={PLANK: 3}, inputs={}, output=GRAIN, work_ticks=420,
        tip="Grows grain. Needs no input.",
    ),
    "mill": dict(
        label="Mill", kind="produce", size=(2, 2), hp=200,
        cost={PLANK: 2, STONE: 1}, inputs={GRAIN: 1}, output=FLOUR,
        work_ticks=300,
        tip="Grinds grain into flour.",
    ),
    "bakery": dict(
        label="Bakery", kind="produce", size=(2, 2), hp=200,
        cost={PLANK: 2, STONE: 2}, inputs={FLOUR: 1}, output=BREAD,
        work_ticks=300,
        tip="Bakes flour into bread.",
    ),
    "goldmine": dict(
        label="Gold Mine", kind="produce", size=(2, 2), hp=220,
        cost={PLANK: 3, STONE: 1}, inputs={BREAD: 1}, output=ORE,
        work_ticks=360, needs_gold=True,
        tip="Miners eat bread and dig gold ore. Build beside gold rock.",
    ),
    "mint": dict(
        label="Mint", kind="produce", size=(2, 2), hp=220,
        cost={PLANK: 2, STONE: 2}, inputs={ORE: 1, LOG: 1}, output=COIN,
        work_ticks=360,
        tip="Smelts ore (with log fuel) into gold coins.",
    ),
    "barracks": dict(
        label="Barracks", kind="military", size=(2, 2), hp=300,
        cost={PLANK: 3, STONE: 3}, inputs={COIN: 2, BREAD: 1},
        work_ticks=420, trains=True,
        tip="Trains a soldier from 2 coins and 1 bread.",
    ),
    "tower": dict(
        label="Guard Tower", kind="military", size=(1, 1), hp=350,
        cost={STONE: 3, PLANK: 1}, work_ticks=0,
        attack_range=5.0, attack_dps=14.0,
        tip="Shoots at enemies in range.",
    ),
    "enemy_hq": dict(
        label="Enemy Stronghold", kind="hq", size=(3, 3), hp=900,
        cost={}, buildable=False,
    ),
    "enemy_tower": dict(
        label="Enemy Tower", kind="military", size=(1, 1), hp=300,
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

# territory: may build within this many tiles of castle / owned buildings
TERRITORY_RADIUS = 10

# ---------------------------------------------------------------- units
UNIT_SPEED = 2.6            # tiles per second (carriers/settlers)
SOLDIER_SPEED = 2.2
SETTLER_SPAWN_TICKS = 420   # castle produces a settler this often
MAX_SETTLERS = 14           # carriers/builders cap (soldiers not counted)

SOLDIER_HP = 60
SOLDIER_DPS = 10.0
ENEMY_SOLDIER_HP = 55
ENEMY_SOLDIER_DPS = 9.0
MELEE_RANGE = 0.9           # tiles
AGGRO_RANGE = 4.0           # auto-engage distance
BUILDER_BUILD_TICKS = 360   # construction time once builder is on site

# ---------------------------------------------------------------- enemy AI
RAID_FIRST_TICKS = 60 * TICKS_PER_SECOND      # first raid after 60 s
RAID_PERIOD_TICKS = 100 * TICKS_PER_SECOND    # then every 100 s
RAID_SIZE_START = 2
RAID_SIZE_MAX = 5
ENEMY_GUARDS = 4            # soldiers defending the camp
ENEMY_GUARD_LEASH = 7.0     # guards chase this far from camp

TREE_REGROW_TICKS = 90 * TICKS_PER_SECOND     # a felled tree regrows
