# Astro Settlers — a Settlers-like space colony game for macOS

A top-down, real-time colony and strategy game inspired by **The Settlers IV**,
re-themed as an **alien-planet colony**. Written in Python with **pygame**.
Grow an economy through branching production chains, **recruit troops**, and
destroy the alien hive — all with hand-generated pixel art (no external assets).

---

## Requirements

- **macOS** (also runs on Linux/Windows), with **Python 3.9+**
- **pygame** (the only runtime dependency)

## Install & run (macOS)

```bash
# 1. Get Python 3 (skip if you already have it)
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

You start with a **Command Center** (your warehouse and colonist source) and a
handful of colonists. Across the map lurks an **Alien Hive** that scouts your
territory and sends raids. Build an economy, recruit troops, and destroy the
hive.

- **Win:** destroy the Alien Hive.
- **Lose:** your Command Center is destroyed.

### Controls

| Action | Control |
| --- | --- |
| Scroll the map | Arrow keys / **WASD**, or push the mouse to a screen edge |
| Open a building to place | Click its button in the **BUILD** bar (bottom-left) |
| Place the building | Left-click a valid (green) tile; **Shift** to place several |
| Cancel placing | Right-click or **Esc** |
| Select a building / troops | Left-click it; drag a box to select many troops |
| **Recruit troops** | Select a **Barracks**, then click a troop button in the panel |
| Move / attack with troops | Select troops, then **right-click** a spot or an enemy |
| Pause | **Space** |
| Game speed | **1** / **2** / **3** |
| Jump the camera | Click on the **minimap** (bottom-right) |
| Restart after a win/loss | **R** |

Colonists spawn automatically at the Command Center over time (up to a cap).
Idle colonists become **carriers** that haul goods; they are also drafted as
**builders** for construction sites and as **workers** for extraction rigs.

---

## Economy: production chains

Everything is stored at the Command Center and carried to wherever it is needed.

```
Mining Rig ──ore──▶ Smelter ──alloy──▶ (build everything)
Excavator ──mineral──▶ (build everything)

Bio-Dome ──biomass──▶ Processor ──protein──▶ Food Synth ──rations──┐
                                                                    ▼
Crystal Extractor (on a seam, eats rations) ──crystal──▶ Fabricator ──credits──┐
                                                                                ▼
                                              Barracks (credits + rations) ──▶ Troops
```

| Building | Consumes | Produces | Notes |
| --- | --- | --- | --- |
| Mining Rig | — | ore | Drones extract ore from nearby ore nodes (they regrow) |
| Smelter | ore | alloy | |
| Excavator | — | mineral | Quarries nearby mineral rock |
| Bio-Dome | — | biomass | |
| Processor | biomass | protein | |
| Food Synth | protein | rations | |
| Crystal Extractor | rations | crystal | Must be built next to a **crystal seam** |
| Fabricator | crystal + ore | credits | |
| Barracks | credits + rations (per troop) | **troops** | Select it to recruit |
| Defense Turret | — | — | Auto-fires on hostiles in range |

Buildings cost **alloy** and **mineral** (deducted when you place them), so your
first priorities are Mining Rigs, a Smelter, and an Excavator. Place extraction
rigs near their resource — select a rig to see its work radius.

---

## Troops & combat

Select a **Barracks** to open the recruit panel and spend resources to queue any
of three troop types (each has its own sprite and stats):

| Troop | Role | HP | Damage | Range | Cost |
| --- | --- | --- | --- | --- | --- |
| **Marine** | balanced melee | 60 | medium | melee | 2 credits + 1 rations |
| **Ranger** | fragile ranged | 42 | low | **shoots at range** | 2 credits + 1 alloy |
| **Heavy** | tanky bruiser | 120 | high | melee | 3 credits + 1 rations + 2 alloy |

- Select troops and **right-click** to move; right-click an enemy unit or
  building to attack. Troops also auto-engage nearby foes; Rangers fire from a
  distance.
- Build **Defense Turrets** along your frontier for automatic defense.

### The Alien Hive reacts to you

The enemy is not passive:

- The **hive reinforces** its garrison over time, so losses are replaced.
- **Scouts** patrol the map; if they **spot your colony**, they trigger an
  **early raid** aimed at what they saw ("Alien scouts have spotted your
  colony!").
- **Raids escalate** — later waves are bigger and mix melee **Aliens** with
  ranged **Spitters**.

Don't wait too long before mounting your own assault on the hive.

---

## Project layout

```
main.py                 Entry point (python3 main.py)
selftest.py             Headless smoke test of economy + recruitment + combat
requirements.txt
siedler/
  constants.py          Balance: costs, timings, TROOPS table, enemy tuning
  assets.py             Loads the PNG sprites
  world.py              Procedural terrain (value noise) + map objects
  camera.py             Scrolling viewport and coordinate transforms
  pathfinding.py        A* over the tile grid
  economy.py            Warehouse stock + carrier job queue
  buildings.py          Construction, production, extraction, recruit queue
  units.py              Carrier / builder / worker / troop state machines
  enemy.py              Alien hive: reinforcement, scouts, escalating raids
  ui.py                 HUD: resource bar, build + recruit panels, minimap
  game.py               Main loop, input, rendering, win/lose
tools/
  generate_assets.py    Draws every sprite with Pillow (space theme)
assets/                 Generated PNGs (tiles, buildings, units, icons)
```

## Development

Run the headless test suite (no window needed):

```bash
SDL_VIDEODRIVER=dummy python3 selftest.py
```

It builds the ore→alloy chain, recruits all three troop types, verifies a
Ranger deals damage from range, confirms an alien scout triggers an early raid,
and razes the hive to win — all headless.

To tweak the game, edit `siedler/constants.py` (build costs, production times,
the `TROOPS` table, raid schedule, scout detection, map size).
