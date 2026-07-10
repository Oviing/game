"""Alien Hive: a hostile HQ with spires and guards that reinforces itself,
sends escalating mixed-type raids, and runs scouts that patrol and trigger an
early reactive raid when they spot the player's colony.

Destroying the Hive wins the game.
"""

import math
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

        # two flanking spires
        for (dx, dy) in [(-2, 0), (4, 0)]:
            self._try_place("enemy_tower", tx + dx, ty + dy)

        # standing guards defend the hive
        self.guards = []
        for _ in range(C.ENEMY_GUARDS):
            self.guards.append(self._spawn_soldier("alien", guard=True))

        # scouts range far and watch for the player
        self.scouts = []
        for _ in range(C.SCOUT_COUNT):
            sc = self._spawn_soldier("scout", guard=True)
            sc.leash_radius = C.SCOUT_LEASH
            self._send_patrol(sc)
            self.scouts.append(sc)

        self.next_raid = C.RAID_FIRST_TICKS
        self.raid_num = 0
        self.train_timer = C.ENEMY_TRAIN_TICKS
        self.last_reaction = -C.RAID_REACT_MIN_GAP

    # ------------------------------------------------ setup helpers
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
        for r in range(2, 9):
            for _ in range(14):
                x = cx + random.randint(-r, r)
                y = cy + random.randint(-r, r)
                if w.is_walkable(x, y):
                    return x, y
        return cx, cy

    def _spawn_soldier(self, troop, guard=False):
        x, y = self._free_spawn_tile()
        u = Unit(self.game, x, y, "soldier", team="enemy")
        u.apply_troop(troop)
        if guard:
            u.leash_center = (float(self.center[0]), float(self.center[1]))
            u.leash_radius = C.ENEMY_GUARD_LEASH
        self.game.enemy_units.append(u)
        return u

    def _send_patrol(self, scout):
        w = self.game.world
        cx, cy = self.center
        for _ in range(20):
            ang = random.uniform(0, math.tau)
            r = random.uniform(8, C.SCOUT_LEASH - 2)
            gx = int(cx + math.cos(ang) * r)
            gy = int(cy + math.sin(ang) * r)
            if w.is_walkable(gx, gy):
                scout.move_goal = (float(gx), float(gy))
                scout.attack_target = None
                return

    # ------------------------------------------------ per-tick AI
    def update(self):
        if self.hq.dead:
            return
        tick = self.game.tick

        # reinforce the standing garrison over time
        self.train_timer -= 1
        if self.train_timer <= 0:
            self.train_timer = C.ENEMY_TRAIN_TICKS
            self.guards = [g for g in self.guards if not g.dead]
            if len(self.guards) < C.ENEMY_MAX_GUARDS:
                troop = random.choice(["alien", "alien", "spitter"])
                self.guards.append(self._spawn_soldier(troop, guard=True))

        # keep scouts wandering; re-task idle ones
        for sc in list(self.scouts):
            if sc.dead:
                self.scouts.remove(sc)
                continue
            if sc.move_goal is None and sc.attack_target is None:
                self._send_patrol(sc)

        # scouts spotting the player trigger an early, targeted raid
        if tick - self.last_reaction >= C.RAID_REACT_MIN_GAP:
            spot = self._scout_detection()
            if spot is not None:
                self.last_reaction = tick
                self.next_raid = min(self.next_raid, tick + 3 * C.TICKS_PER_SECOND)
                self._pending_target = spot

        # scheduled / reactive raids
        if tick >= self.next_raid:
            self._launch_raid()
            self.next_raid = tick + C.RAID_PERIOD_TICKS

    def _scout_detection(self):
        game = self.game
        targets = game.units + game.player_soldiers + \
            [b for b in game.buildings if b.owner == "player"]
        for sc in self.scouts:
            if sc.dead:
                continue
            for t in targets:
                tx = getattr(t, "x", None)
                if tx is None:
                    cx, cy = t.center_tile()
                else:
                    cx, cy = t.x, t.y
                if math.hypot(sc.x - cx, sc.y - cy) <= C.SCOUT_DETECT_RANGE:
                    game.notify("Alien scouts have spotted your colony!")
                    return (cx, cy)
        return None

    def _launch_raid(self):
        size = min(C.RAID_SIZE_START + self.raid_num, C.RAID_SIZE_MAX)
        self.raid_num += 1

        # pick a destination: a spotted location, else the command center
        target = getattr(self, "_pending_target", None)
        self._pending_target = None
        if target is None:
            goal = self.game.castle.access_tile(self.game.world)
        else:
            goal = (int(target[0]), int(target[1]))

        # escalating mixed composition: more spitters as raids grow
        for i in range(size):
            if self.raid_num >= 3 and i % 3 == 2:
                troop = "spitter"
            else:
                troop = "alien"
            u = self._spawn_soldier(troop, guard=False)
            u.move_goal = (float(goal[0]), float(goal[1]))
        self.game.notify("An alien raid is inbound! (%d)" % size)
