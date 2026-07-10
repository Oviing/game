"""Mobile units. One class, dispatched by ``role`` and ``team``.

Roles:
  carrier  - hauls goods between producers/consumers and the castle
  builder  - walks to a construction site and raises it, then becomes a carrier
  worker   - bound to a gather building; harvests nearby trees/stone
  soldier  - fights; player soldiers are selectable, enemies raid/guard

Positions are float tile coordinates; a unit is rendered centred on its tile.
"""

import math

from . import constants as C
from . import pathfinding as pf


class Unit:
    _next_id = 0

    def __init__(self, game, tx, ty, role, team="player"):
        self.game = game
        self.x = float(tx)
        self.y = float(ty)
        self.role = role
        self.team = team
        self.path = []
        self.state = "idle"
        self.carrying = None       # resource name a carrier/worker holds
        self.job = None            # carrier's current Job
        self.home = None           # castle (carrier) / building (worker/builder)
        self.target_tile = None    # a resource tile or destination
        self.work_timer = 0
        self.move_goal = None      # soldier explicit move order (tile)
        self.attack_target = None  # soldier's current foe (Unit or Building)
        self.leash_center = None   # guards stay within a leash of this tile
        self.leash_radius = C.ENEMY_GUARD_LEASH
        self.max_hp = 1
        self.hp = 1
        # combat stats (set from constants.TROOPS for soldiers)
        self.troop = None
        self.sprite = None
        self.dps = C.TROOPS["marine"]["dps"]
        self.speed = C.TROOPS["marine"]["speed"]
        self.range = C.MELEE_RANGE
        self.shoot_cd = 0.0
        self._repath_cd = 0.0
        self.facing = 1
        self.id = Unit._next_id
        Unit._next_id += 1

    # -------------------------------------------------- helpers
    @property
    def tile(self):
        return int(round(self.x)), int(round(self.y))

    @property
    def dead(self):
        return self.hp <= 0

    def take_damage(self, amount):
        self.hp -= amount

    def apply_troop(self, troop_name):
        d = C.TROOPS[troop_name]
        self.troop = troop_name
        self.sprite = d["sprite"]
        self.team = d["team"]
        self.max_hp = d["hp"]
        self.hp = d["hp"]
        self.dps = d["dps"]
        self.speed = d["speed"]
        self.range = d["range"]

    @property
    def ranged(self):
        return self.range > C.MELEE_RANGE + 0.5

    def set_dest(self, goal, goal_walkable=True):
        start = self.tile
        path = pf.find_path(self.game.world, start, goal,
                            goal_walkable=goal_walkable)
        self.path = path if path else []
        return path is not None

    def _advance(self, dt, speed):
        """Move along path; return True when the path is exhausted."""
        if not self.path:
            return True
        tx, ty = self.path[0]
        dx, dy = tx - self.x, ty - self.y
        dist = math.hypot(dx, dy)
        if dist < 1e-6:
            self.path.pop(0)
            return not self.path
        if dx > 0.05:
            self.facing = 1
        elif dx < -0.05:
            self.facing = -1
        step = speed * dt
        if dist <= step:
            self.x, self.y = float(tx), float(ty)
            self.path.pop(0)
            return not self.path
        self.x += dx / dist * step
        self.y += dy / dist * step
        return False

    # -------------------------------------------------- update dispatch
    def update(self, dt):
        if self.role == "carrier":
            self._update_carrier(dt)
        elif self.role == "worker":
            self._update_worker(dt)
        elif self.role == "builder":
            self._update_builder(dt)
        elif self.role == "soldier":
            self._update_soldier(dt)

    # -------------------------------------------------- carrier
    def _update_carrier(self, dt):
        eco = self.game.economy
        world = self.game.world
        if self.state == "idle":
            job = eco.claim_nearest(self.tile, world)
            if job is None:
                return
            if job.building.dead:
                eco.cancel_job(job)
                return
            self.job = job
            if job.mode == "to_castle":
                job.building.out_reserved += 1
                self.set_dest(job.building.access_tile(world))
            else:  # to_building: pick up from castle first
                self.set_dest(eco.castle.access_tile(world))
            self.state = "to_source"
        elif self.state == "to_source":
            if self._advance(dt, C.UNIT_SPEED):
                self._carrier_pickup()
        elif self.state == "to_dest":
            if self._advance(dt, C.UNIT_SPEED):
                self._carrier_dropoff()

    def _carrier_pickup(self):
        eco = self.game.economy
        world = self.game.world
        j = self.job
        if j.building.dead:
            self._abort_job()
            return
        if j.mode == "to_castle":
            if j.building.out_buffer > 0:
                j.building.out_buffer -= 1
                j.building.out_reserved = max(0, j.building.out_reserved - 1)
                self.carrying = j.resource
            else:
                j.building.out_reserved = max(0, j.building.out_reserved - 1)
                self._abort_job()
                return
            self.set_dest(eco.castle.access_tile(world))
        else:  # to_building: take from castle stock
            eco.stock[j.resource] = max(0, eco.stock[j.resource] - 1)
            eco.reserved[j.resource] = max(0, eco.reserved[j.resource] - 1)
            self.carrying = j.resource
            self.set_dest(j.building.access_tile(world))
        self.state = "to_dest"

    def _carrier_dropoff(self):
        eco = self.game.economy
        j = self.job
        if j.mode == "to_castle":
            eco.add(j.resource, 1)
        else:
            if j.building.dead:
                eco.add(j.resource, 1)  # salvage back to castle
            else:
                j.building.in_buffer[j.resource] += 1
                j.building.in_incoming[j.resource] = max(
                    0, j.building.in_incoming[j.resource] - 1)
        self.carrying = None
        self.job = None
        self.state = "idle"

    def _abort_job(self):
        if self.job:
            self.game.economy.cancel_job(self.job)
        self.job = None
        self.carrying = None
        self.state = "idle"

    # -------------------------------------------------- worker (gatherer)
    def _update_worker(self, dt):
        home = self.home
        world = self.game.world
        if home is None or home.dead:
            self.role = "carrier"
            self.home = self.game.castle
            self.state = "idle"
            return
        if self.state == "idle":
            if home.out_buffer >= C.OUTPUT_BUFFER_CAP:
                return
            cx, cy = int(home.center_tile()[0]), int(home.center_tile()[1])
            spots = world.find_objects(cx, cy, home.d["radius"],
                                       home.d["gathers"])
            if not spots:
                return
            self.target_tile = spots[0]
            if self.set_dest(self.target_tile, goal_walkable=False):
                self.state = "to_resource"
        elif self.state == "to_resource":
            tx, ty = self.target_tile
            t = world.tile_at(tx, ty)
            if t.obj != home.d["gathers"] or t.obj_hp <= 0:
                self.state = "idle"   # someone/thing took it; pick again
                return
            if self._advance(dt, C.UNIT_SPEED):
                self.state = "working"
                self.work_timer = home.work_ticks
        elif self.state == "working":
            self.work_timer -= 1
            if self.work_timer <= 0:
                tx, ty = self.target_tile
                world.harvest(tx, ty, self.game.tick)
                self.carrying = home.output
                self.set_dest(home.access_tile(world))
                self.state = "returning"
        elif self.state == "returning":
            if self._advance(dt, C.UNIT_SPEED):
                if home.out_buffer < C.OUTPUT_BUFFER_CAP:
                    home.out_buffer += 1
                self.carrying = None
                self.state = "idle"

    # -------------------------------------------------- builder
    def _update_builder(self, dt):
        site = self.home
        world = self.game.world
        if site is None or site.dead or site.complete:
            self._become_carrier()
            return
        if self.state != "building":
            if self._advance(dt, C.UNIT_SPEED):
                self.state = "building"
        else:
            site.build_progress += 1
            if site.build_progress >= C.BUILDER_BUILD_TICKS:
                self.game.finish_construction(site)
                self._become_carrier()

    def _become_carrier(self):
        self.role = "carrier"
        self.home = self.game.castle
        self.state = "idle"
        self.target_tile = None
        self.path = []

    # -------------------------------------------------- soldier
    def _update_soldier(self, dt):
        speed = self.speed
        self._repath_cd -= dt
        if self.shoot_cd > 0:
            self.shoot_cd -= dt

        tgt = self.attack_target
        if tgt is not None and _is_dead(tgt):
            self.attack_target = None
            tgt = None

        # guards/scouts abandon a chase that pulls them too far from their post
        if self.leash_center is not None:
            lx, ly = self.leash_center
            if math.hypot(self.x - lx, self.y - ly) > self.leash_radius:
                self.attack_target = None
                tgt = None
                self.move_goal = self.leash_center

        # acquire a target automatically when idle or attack-moving
        if tgt is None:
            tgt = self._acquire_target()
            self.attack_target = tgt

        if tgt is not None:
            tx, ty = _target_tile(tgt)
            d = math.hypot(self.x - tx, self.y - ty)
            reach = self.range + _target_radius(tgt)
            if d <= reach:
                self.path = []
                tgt.take_damage(self.dps * dt)
                self.facing = 1 if tx >= self.x else -1
                if self.ranged and self.shoot_cd <= 0:
                    self.game.add_shot(((self.x + 0.5) * C.TILE,
                                        (self.y + 0.5) * C.TILE),
                                       (tx * C.TILE, ty * C.TILE), self.team)
                    self.shoot_cd = 0.35
                return
            # close the distance
            if not self.path or self._repath_cd <= 0:
                self.set_dest((int(round(tx)), int(round(ty))),
                              goal_walkable=False)
                self._repath_cd = 0.4
            self._advance(dt, speed)
            return

        # no target: obey move order
        if self.move_goal is not None:
            if self._advance(dt, speed):
                self.move_goal = None

    def _acquire_target(self):
        game = self.game
        best = None
        best_d = C.AGGRO_RANGE
        lc = self.leash_center

        def in_leash(px, py):
            if lc is None:
                return True
            return math.hypot(px - lc[0], py - lc[1]) <= self.leash_radius

        if self.team == "player":
            foes = game.enemy_units
        else:
            foes = game.player_soldiers
        for u in foes:
            if u.dead:
                continue
            d = math.hypot(self.x - u.x, self.y - u.y)
            if d < best_d and in_leash(u.x, u.y):
                best_d = d
                best = u
        # enemy soldiers also target buildings (so raids do damage)
        if self.team == "enemy":
            for b in game.buildings:
                if b.owner != "player" or b.dead:
                    continue
                bx, by = b.center_tile()
                d = math.hypot(self.x - bx, self.y - by)
                if d < best_d and in_leash(bx, by):
                    best_d = d
                    best = b
        return best


# -------------------------------------------------- free helpers
def _is_dead(t):
    return getattr(t, "dead", False)


def _target_tile(t):
    if hasattr(t, "center_tile"):
        return t.center_tile()
    return t.x, t.y


def _target_radius(t):
    # buildings are big; approximate half-diagonal so melee lands at the edge
    if hasattr(t, "w"):
        return max(t.w, t.h) * 0.5
    return 0.0
