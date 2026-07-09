"""Buildings: construction sites, production logic, gathering, military.

A Building is placed as a construction *site* (unless spawned complete, like
the castle). A builder walks over and raises ``build_progress`` until it turns
active. Producers convert buffered inputs into buffered outputs on a timer;
gatherers own a worker that harvests map objects; military buildings train
soldiers or shoot.
"""

from collections import defaultdict

from . import constants as C


class Building:
    def __init__(self, type_name, tx, ty, owner="player", complete=False):
        d = C.BUILDINGS[type_name]
        self.type = type_name
        self.d = d
        self.kind = d["kind"]
        self.label = d.get("label", type_name)
        self.x = tx
        self.y = ty
        self.w, self.h = d["size"]
        self.owner = owner
        self.max_hp = d["hp"]
        self.hp = d["hp"]

        self.complete = complete
        self.build_progress = 0
        self.builder = None            # assigned Unit while under construction

        self.output = d.get("output")
        self.inputs = d.get("inputs", {})
        self.work_ticks = d.get("work_ticks", 0)

        self.in_buffer = defaultdict(int)
        self.in_incoming = defaultdict(int)
        self.out_buffer = 0
        self.out_reserved = 0

        self.producing = False
        self.produce_timer = 0

        self.worker = None             # gather worker (Unit)
        self.attack_cd = 0.0
        self._access = None
        self.flash = 0                 # damage flash frames

    # -------------------------------------------------- geometry
    def footprint(self):
        for dy in range(self.h):
            for dx in range(self.w):
                yield self.x + dx, self.y + dy

    def center_tile(self):
        return self.x + self.w / 2.0, self.y + self.h / 2.0

    def center_px(self):
        cx, cy = self.center_tile()
        return cx * C.TILE, cy * C.TILE

    def access_tile(self, world):
        """A walkable tile just outside the footprint (cached)."""
        if self._access and world.is_walkable(*self._access):
            return self._access
        ring = []
        for dx in range(-1, self.w + 1):
            ring.append((self.x + dx, self.y - 1))
            ring.append((self.x + dx, self.y + self.h))
        for dy in range(-1, self.h + 1):
            ring.append((self.x - 1, self.y + dy))
            ring.append((self.x + self.w, self.y + dy))
        for (x, y) in ring:
            if world.is_walkable(x, y):
                self._access = (x, y)
                return self._access
        # fallback: building's own top-left even if blocked
        self._access = (self.x, self.y)
        return self._access

    def occupy(self, world, blocked=True):
        for x, y in self.footprint():
            if world.in_bounds(x, y):
                world.tiles[y][x].blocked = blocked

    # -------------------------------------------------- combat
    def take_damage(self, amount):
        self.hp -= amount
        self.flash = 6
        if self.hp < 0:
            self.hp = 0

    @property
    def dead(self):
        return self.hp <= 0

    # -------------------------------------------------- per-tick update
    def update(self, game):
        if self.flash > 0:
            self.flash -= 1
        if not self.complete:
            return
        if self.kind == "produce":
            self._update_produce(game)
        elif self.kind == "military" and self.d.get("trains"):
            self._update_barracks(game)
        elif self.kind == "military" and "attack_dps" in self.d:
            self._update_tower(game)

    def _update_produce(self, game):
        if not self.producing:
            if self.out_buffer >= C.OUTPUT_BUFFER_CAP:
                return
            if all(self.in_buffer[r] >= n for r, n in self.inputs.items()):
                for r, n in self.inputs.items():
                    self.in_buffer[r] -= n
                self.producing = True
                self.produce_timer = self.work_ticks
        else:
            self.produce_timer -= 1
            if self.produce_timer <= 0:
                self.producing = False
                self.out_buffer += 1

    def _update_barracks(self, game):
        if self.producing:
            self.produce_timer -= 1
            if self.produce_timer <= 0:
                self.producing = False
                game.spawn_soldier(self)
            return
        if game.soldier_count() >= C.MAX_SETTLERS:
            return
        if all(self.in_buffer[r] >= n for r, n in self.inputs.items()):
            for r, n in self.inputs.items():
                self.in_buffer[r] -= n
            self.producing = True
            self.produce_timer = self.work_ticks

    def _update_tower(self, game):
        if self.attack_cd > 0:
            self.attack_cd -= game.dt
            return
        rng = self.d["attack_range"]
        cx, cy = self.center_tile()
        target = None
        best = rng * rng
        foes = game.enemy_units if self.owner == "player" else game.player_soldiers
        for u in foes:
            if u.dead:
                continue
            d = (u.x - cx) ** 2 + (u.y - cy) ** 2
            if d <= best:
                best = d
                target = u
        if target is not None:
            target.take_damage(self.d["attack_dps"] * 0.5)  # fires twice/sec
            self.attack_cd = 0.5
            game.add_shot(self.center_px(), (target.x * C.TILE, target.y * C.TILE),
                          self.owner)
