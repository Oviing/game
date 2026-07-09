"""Enemy stronghold: a hostile HQ with towers and guards that periodically
sends raiding waves toward the player's castle. Destroying the HQ wins the
game."""

import random

from . import constants as C
from .buildings import Building
from .units import Unit


class EnemyCamp:
    def __init__(self, game, tx, ty):
        self.game = game
        self.hq = Building("enemy_hq", tx, ty, owner="enemy", complete=True)
        self.hq.occupy(game.world)
        game.buildings.append(self.hq)
        self.center = (tx + 1, ty + 1)

        # two flanking towers
        for (dx, dy) in [(-2, 0), (4, 0)]:
            self._try_place("enemy_tower", tx + dx, ty + dy)

        # standing guards
        for _ in range(C.ENEMY_GUARDS):
            self._spawn_soldier(guard=True)

        self.next_raid = C.RAID_FIRST_TICKS
        self.raid_num = 0

    def _try_place(self, kind, x, y):
        w = self.game.world
        if not w.in_bounds(x, y) or not w.is_land(x, y):
            return
        b = Building(kind, x, y, owner="enemy", complete=True)
        b.occupy(w)
        self.game.buildings.append(b)

    def _free_spawn_tile(self):
        w = self.game.world
        cx, cy = self.center
        for r in range(2, 8):
            for _ in range(12):
                x = cx + random.randint(-r, r)
                y = cy + random.randint(-r, r)
                if w.is_walkable(x, y):
                    return x, y
        return cx, cy

    def _spawn_soldier(self, guard=False):
        x, y = self._free_spawn_tile()
        u = Unit(self.game, x, y, "soldier", team="enemy")
        u.max_hp = C.ENEMY_SOLDIER_HP
        u.hp = C.ENEMY_SOLDIER_HP
        if guard:
            u.leash_center = (float(self.center[0]), float(self.center[1]))
        self.game.enemy_units.append(u)
        return u

    def update(self):
        if self.hq.dead:
            return
        if self.game.tick >= self.next_raid:
            self._launch_raid()
            self.next_raid += C.RAID_PERIOD_TICKS

    def _launch_raid(self):
        size = min(C.RAID_SIZE_START + self.raid_num, C.RAID_SIZE_MAX)
        self.raid_num += 1
        castle = self.game.castle
        goal = castle.access_tile(self.game.world)
        for _ in range(size):
            u = self._spawn_soldier(guard=False)
            u.move_goal = (float(goal[0]), float(goal[1]))
        self.game.notify("An enemy raid is approaching!")
