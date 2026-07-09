# Siedler — a Settlers IV–like game for macOS

A top-down, real-time settlement and strategy game inspired by **The Settlers IV**,
written in Python with **pygame**. Grow an economy through branching production
chains, raise an army, and raze the enemy stronghold — all with hand-generated
pixel art (no external assets).

---

## Requirements

- **macOS** (also runs on Linux/Windows), with **Python 3.9+**
- **pygame** (the only runtime dependency)

## Install & run (macOS)

```bash
# 1. Get Python 3 (skip if you already have it)
#    Either from https://www.python.org/downloads/ or via Homebrew:
brew install python

# 2. Install pygame
python3 -m pip install pygame

# 3. Run the game from the project folder
python3 main.py
```

Optional: start on a fixed map with `python3 main.py --seed 5`.

> The images in `assets/` are already included. You only need Pillow
> (`python3 -m pip install pillow`) if you want to regenerate them with
> `python3 tools/generate_assets.py`.

---

## How to play

You start with a **Castle** (your warehouse and settler source) and a handful of
settlers. Somewhere across the map sits a red **enemy stronghold** that will send
raids at your town. Build an economy, train soldiers, and destroy the enemy HQ.

- **Win:** destroy the enemy stronghold (red keep).
- **Lose:** your Castle is destroyed.

### Controls

| Action | Control |
| --- | --- |
| Scroll the map | Arrow keys / **WASD**, or push the mouse to a screen edge |
| Open a building to place | Click its button in the **BUILD** bar (bottom-left) |
| Place the building | Left-click a valid (green) tile; **Shift** to place several |
| Cancel placing | Right-click or **Esc** |
| Select a building / soldiers | Left-click it; drag a box to select many soldiers |
| Move / attack with soldiers | Select soldiers, then **right-click** a spot or an enemy |
| Pause | **Space** |
| Game speed | **1** / **2** / **3** |
| Jump the camera | Click on the **minimap** (bottom-right) |
| Restart after a win/loss | **R** |

Settlers spawn automatically at the Castle over time (up to a cap). Idle settlers
become **carriers** that haul goods; they are also drafted as **builders** for
construction sites and as **workers** for gathering huts.

---

## Economy: production chains

Everything is stored at the Castle and carried to wherever it is needed.

```
Woodcutter ──logs──▶ Sawmill ──planks──▶ (build everything)
Stonecutter ──stone──▶ (build everything)

Farm ──grain──▶ Mill ──flour──▶ Bakery ──bread──┐
                                                 ▼
Gold Mine (on gold rock, eats bread) ──ore──▶ Mint ──coins──┐
                                                             ▼
                                        Barracks (coins + bread) ──▶ Soldier
```

| Building | Consumes | Produces | Notes |
| --- | --- | --- | --- |
| Woodcutter | — | logs | Worker fells nearby trees (trees regrow) |
| Sawmill | logs | planks | |
| Stonecutter | — | stone | Worker quarries nearby stone deposits |
| Farm | — | grain | |
| Mill | grain | flour | |
| Bakery | flour | bread | |
| Gold Mine | bread | ore | Must be built next to **gold rock** |
| Mint | ore + log | coins | |
| Barracks | coins + bread | **soldier** | |
| Guard Tower | — | — | Shoots enemies in range |

Buildings cost **planks** and **stone** (deducted when you place them), so your
first priorities are woodcutters, a sawmill, and a stonecutter. Place gathering
huts near their resource — select a hut to see its work radius.

---

## Combat

- Train soldiers at the **Barracks** (needs coins and bread — i.e. the full
  gold and food chains).
- Select soldiers and **right-click** to move them; right-click an enemy unit or
  building to attack it. Soldiers also auto-engage nearby foes.
- Build **Guard Towers** along your frontier for automatic defense.
- The enemy sends periodic **raids** that grow larger over time, so don't wait
  too long before mounting your own assault on their stronghold.

---

## Project layout

```
main.py                 Entry point (python3 main.py)
selftest.py             Headless smoke test of the economy + combat systems
requirements.txt
siedler/
  constants.py          Tunable balance: costs, timings, map size
  assets.py             Loads the PNG sprites
  world.py              Procedural terrain (value noise) + map objects
  camera.py             Scrolling viewport and coordinate transforms
  pathfinding.py        A* over the tile grid
  economy.py            Warehouse stock + carrier job queue
  buildings.py          Construction, production, gathering, military
  units.py              Carrier / builder / worker / soldier state machines
  enemy.py              Enemy stronghold and raid AI
  ui.py                 HUD: resource bar, build menu, minimap, overlays
  game.py               Main loop, input, rendering, win/lose
tools/
  generate_assets.py    Draws every sprite with Pillow
assets/                 Generated PNGs (tiles, buildings, units, icons)
```

## Development

Run the headless test suite (no window needed):

```bash
SDL_VIDEODRIVER=dummy python3 selftest.py
```

It builds a woodcutter and sawmill, fast-forwards the simulation, and verifies
that logs are gathered, planks are produced, a soldier is trained, an enemy raid
spawns, and combat damages the enemy HQ.

To tweak the game, edit the values in `siedler/constants.py` (build costs,
production times, unit speeds, raid schedule, map size).
