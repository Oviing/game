"""The Game object: owns the world, economy, buildings and units, runs the
fixed-timestep logic loop, handles input, and renders everything.

Can be driven headlessly (see selftest.py): construct Game(), call
place_building(...) and tick_once() directly without ever calling run().
"""

import math
import os
import random

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from . import assets
from . import constants as C
from .buildings import Building
from .camera import Camera
from .economy import Economy
from .enemy import EnemyCamp
from .ui import HUD, HUD_H
from .units import Unit

TICK = 1.0 / C.TICKS_PER_SECOND


class Game:
    def __init__(self, seed=None, headless=False):
        pygame.display.init()
        pygame.font.init()
        self.headless = headless
        flags = 0
        self.screen = pygame.display.set_mode((C.SCREEN_W, C.SCREEN_H), flags)
        pygame.display.set_caption("Siedler — a Settlers-like game")
        self.clock = pygame.time.Clock()
        assets.load()
        self.view_h = C.SCREEN_H - HUD_H
        self.seed = seed
        self.new_game(seed)

    # ================================================== setup
    def new_game(self, seed=None):
        from .world import World
        self.world = World(seed)
        self.camera = Camera(C.SCREEN_W, self.view_h)
        self.economy = Economy()
        self.buildings = []
        self.units = []            # player civilians (carrier/worker/builder)
        self.player_soldiers = []
        self.enemy_units = []
        self.shots = []            # (from_px, to_px, ttl, owner)
        self.messages = []         # (text, ttl_frames)
        self.tick = 0
        self.time_accum = 0.0
        self.dt = TICK
        self.speed = 1
        self.paused = False
        self.result = None
        self.build_type = None
        self.selection = None
        self.drag_start = None
        self.drag_now = None
        self.last_spawn = 0
        self._mm_surf = None

        cx, cy = C.MAP_W // 2, C.MAP_H // 2
        self.castle = Building("castle", cx - 1, cy - 1, owner="player",
                               complete=True)
        self.castle.occupy(self.world)
        self.buildings.append(self.castle)
        self.economy.castle = self.castle
        self.camera.center_on_tile(cx, cy)

        # a few starting carriers
        ax, ay = self.castle.access_tile(self.world)
        for _ in range(4):
            self._spawn_unit(ax, ay, "carrier")

        # enemy stronghold across the map
        self._place_enemy_camp()

        self.hud = HUD(self)
        self.notify("Build Mining Rigs and Smelters to make alloy.")

    def _place_enemy_camp(self):
        cx, cy = C.MAP_W // 2, C.MAP_H // 2
        best = None
        for _ in range(200):
            x = random.randint(6, C.MAP_W - 9)
            y = random.randint(6, C.MAP_H - 9)
            if math.hypot(x - cx, y - cy) < 26:
                continue
            if self._area_land(x, y, 3, 3):
                best = (x, y)
                break
        if best is None:
            best = (min(C.MAP_W - 9, cx + 24), cy)
        # clear a footing
        for dy in range(-1, 4):
            for dx in range(-1, 4):
                tx, ty = best[0] + dx, best[1] + dy
                if self.world.in_bounds(tx, ty):
                    t = self.world.tiles[ty][tx]
                    if t.terrain in (C.WATER, C.ROCK, C.GOLD_ROCK):
                        t.terrain = C.GRASS
                    t.obj = None
                    t.obj_hp = 0
        self.enemy = EnemyCamp(self, best[0], best[1])

    def _area_land(self, x, y, w, h):
        for dy in range(h):
            for dx in range(w):
                if not self.world.is_land(x + dx, y + dy):
                    return False
        return True

    # ================================================== spawning
    def _spawn_unit(self, tx, ty, role):
        u = Unit(self, tx, ty, role)
        u.home = self.castle
        self.units.append(u)
        return u

    def spawn_soldier(self, barracks, troop="marine"):
        ax, ay = barracks.access_tile(self.world)
        u = Unit(self, ax, ay, "soldier", team="player")
        u.apply_troop(troop)
        self.player_soldiers.append(u)
        self.notify("%s ready for duty!" % C.TROOPS[troop]["label"])
        return u

    def queue_recruit(self, barracks, troop):
        """Spend resources now and queue a troop at the barracks."""
        if not barracks.complete or not barracks.d.get("recruits"):
            return False
        if self.soldier_count() + len(barracks.recruit_queue) >= C.MAX_SETTLERS:
            self.notify("Troop capacity reached.")
            return False
        cost = C.TROOPS[troop]["cost"]
        if not self.economy.can_afford(cost):
            self.notify("Not enough resources for %s."
                        % C.TROOPS[troop]["label"])
            return False
        self.economy.spend(cost)
        barracks.recruit_queue.append(troop)
        return True

    def soldier_count(self):
        return len(self.player_soldiers)

    def _free_unit(self):
        """An idle carrier to repurpose, or a fresh one if under the cap."""
        for u in self.units:
            if u.role == "carrier" and u.state == "idle" and u.job is None \
                    and u.carrying is None:
                return u
        if len(self.units) < C.MAX_SETTLERS:
            ax, ay = self.castle.access_tile(self.world)
            return self._spawn_unit(ax, ay, "carrier")
        return None

    # ================================================== building placement
    def can_place(self, type_name, tx, ty):
        d = C.BUILDINGS[type_name]
        w, h = d["size"]
        if not self.economy.can_afford(d.get("cost", {})):
            return False
        for dx in range(w):
            for dy in range(h):
                x, y = tx + dx, ty + dy
                if not self.world.in_bounds(x, y):
                    return False
                t = self.world.tiles[y][x]
                if t.terrain not in C.WALKABLE_TERRAIN or t.blocked or t.obj:
                    return False
        # territory: near an existing player building
        ccx, ccy = tx + w / 2, ty + h / 2
        near = False
        for b in self.buildings:
            if b.owner != "player":
                continue
            bx, by = b.center_tile()
            if math.hypot(ccx - bx, ccy - by) <= C.TERRITORY_RADIUS:
                near = True
                break
        if not near:
            return False
        if d.get("needs_gold"):
            if not self._adjacent_gold(tx, ty, w, h):
                return False
        return True

    def _adjacent_gold(self, tx, ty, w, h):
        for dx in range(-1, w + 1):
            for dy in range(-1, h + 1):
                if self.world.is_gold_rock(tx + dx, ty + dy):
                    return True
        return False

    def place_building(self, type_name, tx, ty):
        if not self.can_place(type_name, tx, ty):
            return None
        d = C.BUILDINGS[type_name]
        self.economy.spend(d.get("cost", {}))
        b = Building(type_name, tx, ty, owner="player", complete=False)
        b.occupy(self.world)
        b.builder = None
        self.buildings.append(b)
        return b

    def finish_construction(self, site):
        site.complete = True
        site.build_progress = C.BUILDER_BUILD_TICKS
        self.notify("%s completed." % site.label)

    # ================================================== messages / fx
    def notify(self, text):
        self.messages.append([text, 240])

    def add_shot(self, a, b, owner):
        self.shots.append([a, b, 6, owner])

    # ================================================== main loop
    def run(self):
        running = True
        while running:
            dt = self.clock.tick(60) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif not self.handle_event(event):
                    running = False
            keys = pygame.key.get_pressed()
            mouse = pygame.mouse.get_pos()
            if mouse[1] < self.view_h:
                self.camera.handle_keys(keys, mouse, dt)
            else:
                self.camera.handle_keys(keys, None, dt)
            self.update(dt)
            self.render()
            pygame.display.flip()
        pygame.quit()

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if self.build_type:
                    self.build_type = None
                elif self.result:
                    return False
                else:
                    self.selection = None
            elif event.key == pygame.K_SPACE:
                self.paused = not self.paused
            elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                self.speed = {pygame.K_1: 1, pygame.K_2: 2,
                              pygame.K_3: 3}[event.key]
                self.paused = False
            elif event.key == pygame.K_r and self.result:
                self.new_game(None)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            self._on_mouse_down(event)
        elif event.type == pygame.MOUSEBUTTONUP:
            self._on_mouse_up(event)
        elif event.type == pygame.MOUSEMOTION:
            if self.drag_start:
                self.drag_now = event.pos
        return True

    # ------------------------------------------------ input helpers
    def _on_mouse_down(self, event):
        if self.result:
            return
        pos = event.pos
        if event.button == 1:
            if self.hud.in_hud(pos):
                self._hud_click(pos)
                return
            if self.build_type:
                tx, ty = self.camera.screen_to_tile(*pos)
                b = self.place_building(self.build_type, tx, ty)
                if b:
                    if not (pygame.key.get_mods() & pygame.KMOD_SHIFT):
                        self.build_type = None
                else:
                    self.notify("Can't build there.")
                return
            self.drag_start = pos
            self.drag_now = pos
        elif event.button == 3:
            self._right_click(pos)

    def _hud_click(self, pos):
        # recruit buttons take priority when a barracks is selected
        if self.selection and self.selection[0] == "building":
            b = self.selection[1]
            if b.owner == "player" and b.complete and b.d.get("recruits"):
                troop = self.hud.recruit_button_at(pos)
                if troop:
                    self.queue_recruit(b, troop)
                    return
        bt = self.hud.button_at(pos)
        if bt:
            self.build_type = None if self.build_type == bt else bt
            self.selection = None
            return
        tile = self.hud.minimap_tile_at(pos)
        if tile:
            self.camera.center_on_tile(*tile)

    def _on_mouse_up(self, event):
        if event.button != 1 or self.drag_start is None:
            return
        start = self.drag_start
        end = event.pos
        self.drag_start = None
        self.drag_now = None
        if abs(end[0] - start[0]) < 6 and abs(end[1] - start[1]) < 6:
            self._single_click(end)
        else:
            self._box_select(start, end)

    def _single_click(self, pos):
        if pos[1] >= self.view_h:
            return
        wx, wy = self.camera.screen_to_world(*pos)
        # soldier?
        for u in self.player_soldiers:
            if u.dead:
                continue
            if math.hypot((u.x + 0.5) * C.TILE - wx,
                          (u.y + 0.5) * C.TILE - wy) < 16:
                self.selection = ("soldiers", [u])
                return
        # building?
        tx, ty = int(wx // C.TILE), int(wy // C.TILE)
        for b in self.buildings:
            if b.x <= tx < b.x + b.w and b.y <= ty < b.y + b.h:
                self.selection = ("building", b)
                return
        self.selection = None

    def _box_select(self, start, end):
        x0, x1 = sorted((start[0], end[0]))
        y0, y1 = sorted((start[1], end[1]))
        rect = pygame.Rect(x0, y0, x1 - x0, y1 - y0)
        picked = []
        for u in self.player_soldiers:
            if u.dead:
                continue
            sx, sy = self.camera.world_to_screen((u.x + 0.5) * C.TILE,
                                                 (u.y + 0.5) * C.TILE)
            if rect.collidepoint(sx, sy):
                picked.append(u)
        self.selection = ("soldiers", picked) if picked else None

    def _right_click(self, pos):
        if self.build_type:
            self.build_type = None
            return
        if not self.selection or self.selection[0] != "soldiers":
            return
        sols = [s for s in self.selection[1] if not s.dead]
        if not sols:
            return
        wx, wy = self.camera.screen_to_world(*pos)
        tx, ty = int(wx // C.TILE), int(wy // C.TILE)
        # attack target?
        target = None
        for u in self.enemy_units:
            if not u.dead and math.hypot((u.x + 0.5) * C.TILE - wx,
                                         (u.y + 0.5) * C.TILE - wy) < 18:
                target = u
                break
        if target is None:
            for b in self.buildings:
                if b.owner == "enemy" and not b.dead and \
                        b.x <= tx < b.x + b.w and b.y <= ty < b.y + b.h:
                    target = b
                    break
        for i, s in enumerate(sols):
            if target is not None:
                s.attack_target = target
                s.move_goal = None
            else:
                s.attack_target = None
                ox = (i % 3) - 1
                oy = (i // 3) - 1
                gx = max(0, min(C.MAP_W - 1, tx + ox))
                gy = max(0, min(C.MAP_H - 1, ty + oy))
                s.move_goal = (float(gx), float(gy))
                s.set_dest((gx, gy))

    # ================================================== update
    def update(self, real_dt):
        # message fade regardless of pause
        for m in self.messages:
            m[1] -= 1
        self.messages = [m for m in self.messages if m[1] > 0]
        for s in self.shots:
            s[2] -= 1
        self.shots = [s for s in self.shots if s[2] > 0]

        if self.paused or self.result:
            return
        self.time_accum += real_dt * self.speed
        steps = 0
        while self.time_accum >= TICK and steps < 8:
            self.tick_once()
            self.time_accum -= TICK
            steps += 1

    def tick_once(self):
        self.dt = TICK
        self.tick += 1
        self.world.update_regrow(self.tick)
        self.economy.generate_jobs(self.buildings)
        for b in self.buildings:
            b.update(self)
        for u in self.units:
            u.update(self.dt)
        for u in self.player_soldiers:
            u.update(self.dt)
        for u in self.enemy_units:
            u.update(self.dt)
        self.enemy.update()
        self._manage_population()
        self._cleanup()
        self._check_end()

    def _manage_population(self):
        if self.tick - self.last_spawn >= C.SETTLER_SPAWN_TICKS \
                and len(self.units) < C.MAX_SETTLERS:
            ax, ay = self.castle.access_tile(self.world)
            self._spawn_unit(ax, ay, "carrier")
            self.last_spawn = self.tick

        for b in self.buildings:
            if b.owner != "player" or b.dead:
                continue
            if b.complete and b.kind == "gather" and \
                    (b.worker is None or b.worker.dead
                     or b.worker.role != "worker"):
                u = self._free_unit()
                if u:
                    self._assign_worker(u, b)
            elif not b.complete and (b.builder is None or b.builder.dead
                                     or b.builder.home is not b):
                u = self._free_unit()
                if u:
                    self._assign_builder(u, b)

    def _assign_worker(self, u, b):
        b.worker = u
        u.role = "worker"
        u.home = b
        u.job = None
        u.carrying = None
        u.state = "idle"
        u.path = []
        ax, ay = b.access_tile(self.world)
        u.x, u.y = float(ax), float(ay)

    def _assign_builder(self, u, b):
        b.builder = u
        u.role = "builder"
        u.home = b
        u.job = None
        u.carrying = None
        u.state = "to_site"
        u.set_dest(b.access_tile(self.world))

    def _cleanup(self):
        # remove dead soldiers/buildings
        dead_b = [b for b in self.buildings if b.dead]
        for b in dead_b:
            b.occupy(self.world, blocked=False)
            if b.worker:
                b.worker.home = None
            for troop in list(b.recruit_queue) + \
                    ([b.recruiting] if b.recruiting else []):
                for r, n in C.TROOPS.get(troop, {}).get("cost", {}).items():
                    self.economy.add(r, n)
        self.buildings = [b for b in self.buildings if not b.dead]
        self.player_soldiers = [u for u in self.player_soldiers if not u.dead]
        self.enemy_units = [u for u in self.enemy_units if not u.dead]
        if self.selection and self.selection[0] == "building" \
                and self.selection[1].dead:
            self.selection = None

    def _check_end(self):
        if self.castle.dead:
            self.result = "lose"
        elif self.enemy.hq.dead:
            self.result = "win"

    # ================================================== render
    def render(self):
        self.screen.fill((30, 40, 50))
        self._render_world()
        if self.build_type:
            self._render_ghost()
        if self.drag_start and self.drag_now:
            x0, y0 = self.drag_start
            x1, y1 = self.drag_now
            r = pygame.Rect(min(x0, x1), min(y0, y1),
                            abs(x1 - x0), abs(y1 - y0))
            pygame.draw.rect(self.screen, (120, 230, 120), r, 1)
        self.hud.draw(self.screen)

    def _render_world(self):
        cam = self.camera
        x0, y0, x1, y1 = cam.visible_tile_range()
        # clip rendering to the play area (above the HUD)
        prev_clip = self.screen.get_clip()
        self.screen.set_clip(pygame.Rect(0, 0, C.SCREEN_W, self.view_h))

        # terrain
        for ty in range(y0, y1):
            for tx in range(x0, x1):
                t = self.world.tiles[ty][tx]
                img = self._terrain_img(t.terrain, tx, ty)
                sx, sy = cam.tile_to_screen(tx, ty)
                self.screen.blit(img, (sx, sy))

        # depth-sorted sprites: objects, buildings, units
        sprites = []
        for ty in range(y0, y1):
            for tx in range(x0, x1):
                t = self.world.tiles[ty][tx]
                if t.obj == C.OBJ_TREE:
                    sprites.append(((ty + 1), 0, "tree", tx, ty))
                elif t.obj == C.OBJ_STONE:
                    sprites.append(((ty + 1), 0, "stone", tx, ty))
        for b in self.buildings:
            if b.x + b.w < x0 or b.x > x1 or b.y + b.h < y0 or b.y > y1:
                continue
            sprites.append((b.y + b.h, 1, "building", b, None))
        for u in self.units + self.player_soldiers + self.enemy_units:
            sprites.append((u.y + 1, 2, "unit", u, None))
        sprites.sort(key=lambda s: (s[0], s[1]))
        for s in sprites:
            self._draw_sprite(s)

        # selection highlights + health bars
        self._draw_overlays()
        self.screen.set_clip(prev_clip)

    def _terrain_img(self, terrain, tx, ty):
        if terrain == C.GRASS:
            return assets.images["grass" if (tx + ty) % 2 else "grass2"]
        return assets.images.get(terrain, assets.images["grass"])

    def _draw_sprite(self, s):
        kind = s[2]
        cam = self.camera
        if kind == "tree":
            tx, ty = s[3], s[4]
            img = assets.images["tree"]
            sx, sy = cam.tile_to_screen(tx, ty)
            self.screen.blit(img, (sx, sy + C.TILE - img.get_height()))
        elif kind == "stone":
            tx, ty = s[3], s[4]
            img = assets.images["stone_deposit"]
            sx, sy = cam.tile_to_screen(tx, ty)
            self.screen.blit(img, (sx, sy))
        elif kind == "building":
            self._draw_building(s[3])
        elif kind == "unit":
            self._draw_unit(s[3])

    def _draw_building(self, b):
        cam = self.camera
        if b.complete:
            img = assets.building_img(b.type)
        else:
            img = assets.images["b_site"]
            img = pygame.transform.smoothscale(img, (b.w * C.TILE,
                                                     b.h * C.TILE))
        sx, _ = cam.tile_to_screen(b.x, b.y)
        _, sby = cam.tile_to_screen(b.x, b.y + b.h)
        top = sby - img.get_height()
        left = sx + (b.w * C.TILE - img.get_width()) // 2
        if b.flash > 0:
            img = img.copy()
            img.fill((120, 40, 40, 90), special_flags=pygame.BLEND_RGBA_ADD)
        self.screen.blit(img, (left, top))
        # construction progress bar
        if not b.complete:
            frac = b.build_progress / C.BUILDER_BUILD_TICKS
            self._world_bar(b, frac, (240, 200, 80))
        elif b.hp < b.max_hp:
            self._world_bar(b, b.hp / b.max_hp,
                            (120, 200, 120) if b.owner == "player"
                            else (220, 90, 80))

    def _world_bar(self, b, frac, color):
        cam = self.camera
        sx, sy = cam.tile_to_screen(b.x, b.y)
        w = b.w * C.TILE
        y = sy - 8
        pygame.draw.rect(self.screen, (20, 18, 16), (sx, y, w, 5))
        pygame.draw.rect(self.screen, color,
                         (sx, y, int(w * max(0, min(1, frac))), 5))

    def _draw_unit(self, u):
        cam = self.camera
        if u.role == "soldier":
            name = u.sprite or "marine"
        else:
            name = {"carrier": "colonist", "builder": "builder",
                    "worker": "worker"}[u.role]
        img = assets.unit_img(name)
        if u.facing < 0:
            img = pygame.transform.flip(img, True, False)
        cx = (u.x + 0.5) * C.TILE - cam.x
        feet = (u.y + 1) * C.TILE - cam.y
        left = int(cx - img.get_width() / 2)
        top = int(feet - img.get_height())
        self.screen.blit(img, (left, top))
        # carried good
        if u.carrying:
            ic = assets.icon(u.carrying)
            if ic:
                ic = pygame.transform.smoothscale(ic, (14, 14))
                self.screen.blit(ic, (left + img.get_width() - 6, top - 6))
        # soldier health bar
        if u.role == "soldier" and u.hp < u.max_hp:
            w = 20
            bx = int(cx - w / 2)
            by = top - 6
            pygame.draw.rect(self.screen, (20, 18, 16), (bx, by, w, 4))
            col = (120, 200, 120) if u.team == "player" else (220, 90, 80)
            pygame.draw.rect(self.screen, col,
                             (bx, by, int(w * u.hp / u.max_hp), 4))

    def _draw_overlays(self):
        cam = self.camera
        # shots
        for a, b, ttl, owner in self.shots:
            col = (255, 240, 150) if owner == "player" else (255, 150, 150)
            pygame.draw.line(self.screen, col,
                             (a[0] - cam.x, a[1] - cam.y),
                             (b[0] - cam.x, b[1] - cam.y), 2)
        # selection
        if self.selection:
            if self.selection[0] == "building":
                b = self.selection[1]
                sx, sy = cam.tile_to_screen(b.x, b.y)
                pygame.draw.rect(self.screen, (250, 230, 120),
                                 (sx, sy, b.w * C.TILE, b.h * C.TILE), 2)
                if b.owner == "player" and b.kind == "gather":
                    self._draw_radius(b)
            elif self.selection[0] == "soldiers":
                for u in self.selection[1]:
                    if u.dead:
                        continue
                    cx = (u.x + 0.5) * C.TILE - cam.x
                    feet = (u.y + 1) * C.TILE - cam.y
                    pygame.draw.ellipse(self.screen, (120, 240, 120),
                                        (cx - 11, feet - 6, 22, 10), 2)

    def _draw_radius(self, b):
        cam = self.camera
        cx, cy = b.center_tile()
        r = b.d.get("radius", 0) * C.TILE
        px = int(cx * C.TILE - cam.x)
        py = int(cy * C.TILE - cam.y)
        surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(surf, (255, 255, 255, 30), (r, r), r)
        pygame.draw.circle(surf, (255, 255, 255, 70), (r, r), r, 1)
        self.screen.blit(surf, (px - r, py - r))

    def _render_ghost(self):
        pos = pygame.mouse.get_pos()
        if pos[1] >= self.view_h:
            return
        tx, ty = self.camera.screen_to_tile(*pos)
        d = C.BUILDINGS[self.build_type]
        w, h = d["size"]
        ok = self.can_place(self.build_type, tx, ty)
        sx, sy = self.camera.tile_to_screen(tx, ty)
        surf = pygame.Surface((w * C.TILE, h * C.TILE), pygame.SRCALPHA)
        surf.fill((90, 220, 90, 90) if ok else (220, 80, 80, 90))
        self.screen.blit(surf, (sx, sy))
        img = assets.building_img(self.build_type)
        img = img.copy()
        img.set_alpha(160)
        bottom = sy + h * C.TILE
        self.screen.blit(img, (sx + (w * C.TILE - img.get_width()) // 2,
                               bottom - img.get_height()))
