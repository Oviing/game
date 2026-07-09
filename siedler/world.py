"""Procedural terrain: a tile grid plus map objects (trees, stone deposits).

Terrain is generated from cheap value-noise (a couple of octaves of a seeded
random lattice, bilinearly interpolated) so no numpy/noise dependency is
needed. The result is a mix of grass plains, water, beaches, rock mountains
and a couple of gold-bearing mountains.
"""

import math
import random

from . import constants as C


class Tile:
    __slots__ = ("terrain", "obj", "obj_hp", "regrow_at", "blocked")

    def __init__(self, terrain):
        self.terrain = terrain
        self.obj = None          # OBJ_TREE / OBJ_STONE / None
        self.obj_hp = 0          # remaining harvests
        self.regrow_at = None    # tick when a felled tree regrows
        self.blocked = False     # occupied by a building footprint


class ValueNoise:
    def __init__(self, seed, period):
        self.period = period
        rng = random.Random(seed)
        n = 256
        self.grid = [[rng.random() for _ in range(n)] for _ in range(n)]
        self.n = n

    def _lattice(self, xi, yi):
        return self.grid[yi % self.n][xi % self.n]

    @staticmethod
    def _smooth(t):
        return t * t * (3 - 2 * t)

    def sample(self, x, y):
        x /= self.period
        y /= self.period
        x0, y0 = int(math.floor(x)), int(math.floor(y))
        fx, fy = self._smooth(x - x0), self._smooth(y - y0)
        v00 = self._lattice(x0, y0)
        v10 = self._lattice(x0 + 1, y0)
        v01 = self._lattice(x0, y0 + 1)
        v11 = self._lattice(x0 + 1, y0 + 1)
        top = v00 + (v10 - v00) * fx
        bot = v01 + (v11 - v01) * fx
        return top + (bot - top) * fy


class World:
    def __init__(self, seed=None):
        self.w = C.MAP_W
        self.h = C.MAP_H
        self.seed = seed if seed is not None else random.randint(0, 1 << 30)
        self.rng = random.Random(self.seed)
        self.tiles = [[Tile(C.GRASS) for _ in range(self.w)]
                      for _ in range(self.h)]
        self.gold_spots = []
        self._generate()

    # ----------------------------------------------------------------
    def _generate(self):
        elev = ValueNoise(self.seed * 3 + 1, period=13)
        elev2 = ValueNoise(self.seed * 3 + 2, period=6)
        moist = ValueNoise(self.seed * 7 + 5, period=17)

        cx, cy = self.w / 2, self.h / 2
        maxd = math.hypot(cx, cy)

        for y in range(self.h):
            for x in range(self.w):
                e = elev.sample(x, y) * 0.65 + elev2.sample(x, y) * 0.35
                # push elevation down toward the edges -> water rings the map
                d = math.hypot(x - cx, y - cy) / maxd
                e -= (d ** 2) * 0.55
                m = moist.sample(x, y)

                t = self.tiles[y][x]
                if e < 0.28:
                    t.terrain = C.WATER
                elif e < 0.33:
                    t.terrain = C.SAND
                elif e > 0.74:
                    t.terrain = C.ROCK
                else:
                    t.terrain = C.GRASS
                    # forests in moist grassland
                    if m > 0.62 and self.rng.random() < 0.55:
                        t.obj = C.OBJ_TREE
                        t.obj_hp = 1
                    elif m < 0.32 and self.rng.random() < 0.05:
                        t.obj = C.OBJ_STONE
                        t.obj_hp = self.rng.randint(6, 12)

        self._scatter_stone_near_rock(elev)
        self._place_gold()
        self._clear_center()

    def _scatter_stone_near_rock(self, elev):
        # add stone deposits on grass tiles adjacent to rock
        for y in range(1, self.h - 1):
            for x in range(1, self.w - 1):
                t = self.tiles[y][x]
                if t.terrain != C.GRASS or t.obj:
                    continue
                near_rock = any(
                    self.tiles[y + dy][x + dx].terrain == C.ROCK
                    for dy in (-1, 0, 1) for dx in (-1, 0, 1))
                if near_rock and self.rng.random() < 0.4:
                    t.obj = C.OBJ_STONE
                    t.obj_hp = self.rng.randint(8, 16)

    def _place_gold(self):
        # convert a few rock clusters to gold rock
        rocks = [(x, y) for y in range(self.h) for x in range(self.w)
                 if self.tiles[y][x].terrain == C.ROCK]
        self.rng.shuffle(rocks)
        placed = 0
        for (x, y) in rocks:
            if placed >= 3:
                break
            # only if it has grass neighbours (minable)
            if not self._has_grass_neighbour(x, y):
                continue
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    nx, ny = x + dx, y + dy
                    if self.in_bounds(nx, ny) and \
                            self.tiles[ny][nx].terrain == C.ROCK:
                        self.tiles[ny][nx].terrain = C.GOLD_ROCK
            self.gold_spots.append((x, y))
            placed += 1

    def _has_grass_neighbour(self, x, y):
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                nx, ny = x + dx, y + dy
                if self.in_bounds(nx, ny) and \
                        self.tiles[ny][nx].terrain in C.WALKABLE_TERRAIN:
                    return True
        return False

    def _clear_center(self):
        # guarantee a buildable clearing where the player's castle sits
        cx, cy = self.w // 2, self.h // 2
        for dy in range(-4, 6):
            for dx in range(-4, 6):
                x, y = cx + dx, cy + dy
                if self.in_bounds(x, y):
                    t = self.tiles[y][x]
                    if t.terrain in (C.WATER, C.ROCK, C.GOLD_ROCK):
                        t.terrain = C.GRASS
                    if abs(dx) < 3 and abs(dy) < 3:
                        t.obj = None
                        t.obj_hp = 0

    # ----------------------------------------------------------------
    def in_bounds(self, x, y):
        return 0 <= x < self.w and 0 <= y < self.h

    def tile_at(self, x, y):
        return self.tiles[y][x]

    def is_land(self, x, y):
        if not self.in_bounds(x, y):
            return False
        return self.tiles[y][x].terrain in C.WALKABLE_TERRAIN

    def is_walkable(self, x, y):
        """Walkable for units: land, no blocking object, not built on."""
        if not self.in_bounds(x, y):
            return False
        t = self.tiles[y][x]
        if t.terrain not in C.WALKABLE_TERRAIN:
            return False
        if t.blocked:
            return False
        if t.obj == C.OBJ_STONE:
            return False
        return True

    def is_gold_rock(self, x, y):
        return self.in_bounds(x, y) and \
            self.tiles[y][x].terrain == C.GOLD_ROCK

    def find_objects(self, cx, cy, radius, obj_kind):
        """Return coords of harvestable objects within radius, nearest first."""
        found = []
        r = int(radius)
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                x, y = cx + dx, cy + dy
                if not self.in_bounds(x, y):
                    continue
                t = self.tiles[y][x]
                if t.obj == obj_kind and t.obj_hp > 0:
                    if dx * dx + dy * dy <= radius * radius:
                        found.append((dx * dx + dy * dy, x, y))
        found.sort()
        return [(x, y) for _, x, y in found]

    def harvest(self, x, y, tick):
        """Remove one unit from an object. Felled trees regrow after a delay."""
        t = self.tiles[y][x]
        if t.obj_hp <= 0:
            return False
        was_tree = t.obj == C.OBJ_TREE
        t.obj_hp -= 1
        if t.obj_hp <= 0:
            t.obj = None
            if was_tree:
                # remember this spot so a sapling grows back here later
                t.regrow_at = tick + C.TREE_REGROW_TICKS
        return True

    def update_regrow(self, tick):
        """Regrow felled trees whose timer has elapsed (if still clear)."""
        for row in self.tiles:
            for t in row:
                if t.regrow_at is not None and tick >= t.regrow_at:
                    t.regrow_at = None
                    if (t.terrain == C.GRASS and t.obj is None
                            and not t.blocked):
                        t.obj = C.OBJ_TREE
                        t.obj_hp = 1
