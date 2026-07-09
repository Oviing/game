"""Heads-up display: resource bar, build menu, selection panel, minimap,
transient messages and the win/lose overlay. Also does HUD hit-testing so the
game loop can route clicks."""

import pygame

from . import constants as C
from . import assets

HUD_H = 140
BAR_H = 34

PANEL_BG = (44, 40, 36)
PANEL_EDGE = (96, 84, 68)
TEXT = (238, 232, 220)
DIM = (176, 168, 156)
GOOD = (120, 200, 120)
BAD = (216, 110, 96)
GOLDC = (240, 198, 60)


class HUD:
    def __init__(self, game):
        self.game = game
        pygame.font.init()
        self.font = pygame.font.SysFont("arialrounded,arial,dejavusans", 16)
        self.small = pygame.font.SysFont("arial,dejavusans", 13)
        self.big = pygame.font.SysFont("arial,dejavusans", 40, bold=True)
        self.mid = pygame.font.SysFont("arial,dejavusans", 22, bold=True)

        self.panel_rect = pygame.Rect(0, C.SCREEN_H - HUD_H, C.SCREEN_W, HUD_H)
        # minimap on the right of the panel
        mm = HUD_H - 16
        self.mm_rect = pygame.Rect(C.SCREEN_W - mm - 8,
                                   C.SCREEN_H - HUD_H + 8, mm, mm)
        # build buttons grid on the left
        self.buttons = []   # (rect, build_type)
        bx = 12
        by = C.SCREEN_H - HUD_H + 30
        bw, bh = 96, 46
        cols = 5
        for i, t in enumerate(C.BUILD_MENU):
            r = pygame.Rect(bx + (i % cols) * (bw + 6),
                            by + (i // cols) * (bh + 6), bw, bh)
            self.buttons.append((r, t))

    # -------------------------------------------------- hit testing
    def in_hud(self, pos):
        return self.panel_rect.collidepoint(pos) or pos[1] < BAR_H

    def button_at(self, pos):
        for r, t in self.buttons:
            if r.collidepoint(pos):
                return t
        return None

    def minimap_tile_at(self, pos):
        if not self.mm_rect.collidepoint(pos):
            return None
        fx = (pos[0] - self.mm_rect.x) / self.mm_rect.w
        fy = (pos[1] - self.mm_rect.y) / self.mm_rect.h
        return int(fx * C.MAP_W), int(fy * C.MAP_H)

    # -------------------------------------------------- drawing
    def draw(self, surf):
        self._draw_resource_bar(surf)
        self._draw_panel(surf)
        self._draw_messages(surf)
        if self.game.result:
            self._draw_result(surf)

    def _draw_resource_bar(self, surf):
        bar = pygame.Surface((C.SCREEN_W, BAR_H), pygame.SRCALPHA)
        bar.fill((30, 28, 25, 225))
        surf.blit(bar, (0, 0))
        eco = self.game.economy
        x = 10
        for res in C.RESOURCES:
            ic = assets.icon(res)
            if ic:
                surf.blit(pygame.transform.smoothscale(ic, (20, 20)),
                          (x, 7))
            txt = self.font.render(str(eco.stock[res]), True, TEXT)
            surf.blit(txt, (x + 22, 8))
            x += 22 + txt.get_width() + 18
        # population + soldiers on the right
        pop = assets.icon("pop")
        sw = assets.icon("sword")
        surf.blit(pygame.transform.smoothscale(pop, (20, 20)),
                  (C.SCREEN_W - 190, 7))
        surf.blit(self.font.render(
            "%d/%d" % (len(self.game.units), C.MAX_SETTLERS), True, TEXT),
            (C.SCREEN_W - 166, 8))
        surf.blit(pygame.transform.smoothscale(sw, (20, 20)),
                  (C.SCREEN_W - 108, 7))
        surf.blit(self.font.render(
            str(len(self.game.player_soldiers)), True, TEXT),
            (C.SCREEN_W - 84, 8))
        # speed indicator
        spd = "PAUSED" if self.game.paused else "%dx" % self.game.speed
        s = self.small.render(spd, True, GOLDC)
        surf.blit(s, (C.SCREEN_W - 44, 10))

    def _draw_panel(self, surf):
        pygame.draw.rect(surf, PANEL_BG, self.panel_rect)
        pygame.draw.line(surf, PANEL_EDGE, self.panel_rect.topleft,
                         (C.SCREEN_W, self.panel_rect.top), 2)
        # section header
        sel = self.game.selection
        if sel and sel[0] == "building":
            self._draw_building_info(surf, sel[1])
        elif sel and sel[0] == "soldiers":
            self._draw_soldiers_info(surf, sel[1])
        else:
            self._draw_build_menu(surf)
        self._draw_minimap(surf)

    def _draw_build_menu(self, surf):
        surf.blit(self.small.render("BUILD  (or click a building/soldiers)",
                                    True, DIM),
                  (12, self.panel_rect.top + 10))
        mx, my = pygame.mouse.get_pos()
        eco = self.game.economy
        for r, t in self.buttons:
            d = C.BUILDINGS[t]
            afford = eco.can_afford(d.get("cost", {}))
            selected = self.game.build_type == t
            bg = (70, 84, 60) if selected else (58, 54, 48)
            if not afford:
                bg = (58, 46, 44)
            pygame.draw.rect(surf, bg, r, border_radius=5)
            pygame.draw.rect(surf, PANEL_EDGE if not selected else GOOD, r,
                             2, border_radius=5)
            img = assets.building_img(t)
            th = 32
            iw = int(img.get_width() * th / img.get_height())
            surf.blit(pygame.transform.smoothscale(img, (iw, th)),
                      (r.x + 4, r.y + r.h - th - 2))
            name = self.small.render(d["label"], True,
                                     TEXT if afford else BAD)
            surf.blit(name, (r.x + 4, r.y + 3))
            if r.collidepoint((mx, my)):
                self._tooltip(surf, (mx, my), t)

    def _tooltip(self, surf, pos, t):
        d = C.BUILDINGS[t]
        lines = [d["label"]]
        cost = d.get("cost", {})
        if cost:
            lines.append("Cost: " + ", ".join(
                "%d %s" % (n, r) for r, n in cost.items()))
        if d.get("inputs"):
            lines.append("Needs: " + ", ".join(
                "%s" % r for r in d["inputs"]))
        if d.get("output"):
            lines.append("Makes: " + d["output"])
        if d.get("tip"):
            lines.append(d["tip"])
        w = max(self.small.size(ln)[0] for ln in lines) + 16
        h = len(lines) * 16 + 10
        x = min(pos[0] + 14, C.SCREEN_W - w - 4)
        y = pos[1] - h - 10
        box = pygame.Surface((w, h), pygame.SRCALPHA)
        box.fill((20, 18, 16, 235))
        surf.blit(box, (x, y))
        pygame.draw.rect(surf, PANEL_EDGE, (x, y, w, h), 1)
        for i, ln in enumerate(lines):
            surf.blit(self.small.render(ln, True, TEXT), (x + 8, y + 5 + i * 16))

    def _draw_building_info(self, surf, b):
        top = self.panel_rect.top + 10
        surf.blit(self.mid.render(b.label, True, TEXT), (14, top))
        img = assets.building_img(b.type)
        th = 60
        iw = int(img.get_width() * th / img.get_height())
        surf.blit(pygame.transform.smoothscale(img, (iw, th)), (14, top + 28))
        x = 14 + iw + 20
        y = top + 30
        # HP
        self._bar(surf, x, y, 160, 12, b.hp / b.max_hp, GOOD)
        surf.blit(self.small.render("HP %d/%d" % (b.hp, b.max_hp), True, DIM),
                  (x + 168, y - 2))
        y += 22
        if not b.complete:
            frac = b.build_progress / C.BUILDER_BUILD_TICKS
            self._bar(surf, x, y, 160, 12, frac, GOLDC)
            surf.blit(self.small.render("Building %d%%" % int(frac * 100),
                                        True, DIM), (x + 168, y - 2))
            return
        # inputs / outputs
        if b.inputs:
            surf.blit(self.small.render("Inputs:", True, DIM), (x, y))
            xx = x + 56
            for res in b.inputs:
                ic = assets.icon(res)
                if ic:
                    surf.blit(pygame.transform.smoothscale(ic, (18, 18)),
                              (xx, y - 2))
                surf.blit(self.small.render(str(b.in_buffer[res]), True, TEXT),
                          (xx + 20, y))
                xx += 46
            y += 22
        if b.output:
            surf.blit(self.small.render("Output:", True, DIM), (x, y))
            ic = assets.icon(b.output)
            if ic:
                surf.blit(pygame.transform.smoothscale(ic, (18, 18)),
                          (x + 56, y - 2))
            surf.blit(self.small.render(str(b.out_buffer), True, TEXT),
                      (x + 78, y))
        if b.d.get("trains") and b.producing:
            surf.blit(self.small.render("Training soldier...", True, GOLDC),
                      (x, y))

    def _draw_soldiers_info(self, surf, sols):
        top = self.panel_rect.top + 12
        alive = [s for s in sols if not s.dead]
        surf.blit(self.mid.render("Soldiers: %d" % len(alive), True, TEXT),
                  (14, top))
        surf.blit(self.small.render(
            "Right-click to move or attack. Destroy the red stronghold to win.",
            True, DIM), (14, top + 32))
        sw = assets.icon("sword")
        if sw:
            surf.blit(pygame.transform.smoothscale(sw, (40, 40)), (14, top + 54))

    def _bar(self, surf, x, y, w, h, frac, color):
        frac = max(0.0, min(1.0, frac))
        pygame.draw.rect(surf, (24, 22, 20), (x, y, w, h))
        pygame.draw.rect(surf, color, (x, y, int(w * frac), h))
        pygame.draw.rect(surf, PANEL_EDGE, (x, y, w, h), 1)

    def _draw_minimap(self, surf):
        mm = self.mm_rect
        pygame.draw.rect(surf, (18, 30, 40), mm)
        game = self.game
        world = game.world
        # cached terrain surface
        if getattr(game, "_mm_surf", None) is None:
            game._mm_surf = self._render_mm_terrain(world)
        surf.blit(pygame.transform.scale(game._mm_surf, (mm.w, mm.h)),
                  (mm.x, mm.y))
        sx = mm.w / C.MAP_W
        sy = mm.h / C.MAP_H
        for b in game.buildings:
            col = (90, 140, 240) if b.owner == "player" else (230, 80, 70)
            pygame.draw.rect(surf, col,
                             (mm.x + b.x * sx, mm.y + b.y * sy,
                              max(2, b.w * sx), max(2, b.h * sy)))
        for u in game.player_soldiers:
            pygame.draw.rect(surf, (150, 200, 255),
                             (mm.x + u.x * sx, mm.y + u.y * sy, 2, 2))
        for u in game.enemy_units:
            pygame.draw.rect(surf, (255, 150, 140),
                             (mm.x + u.x * sx, mm.y + u.y * sy, 2, 2))
        # camera rectangle
        cam = game.camera
        rx = mm.x + (cam.x / C.TILE) * sx
        ry = mm.y + (cam.y / C.TILE) * sy
        rw = (cam.view_w / C.TILE) * sx
        rh = (cam.view_h / C.TILE) * sy
        pygame.draw.rect(surf, (250, 250, 250), (rx, ry, rw, rh), 1)
        pygame.draw.rect(surf, PANEL_EDGE, mm, 2)

    def _render_mm_terrain(self, world):
        s = pygame.Surface((C.MAP_W, C.MAP_H))
        colors = {
            C.WATER: (52, 108, 176), C.SAND: (206, 184, 128),
            C.GRASS: (96, 152, 72), C.ROCK: (128, 124, 122),
            C.GOLD_ROCK: (200, 168, 70),
        }
        for y in range(C.MAP_H):
            for x in range(C.MAP_W):
                t = world.tiles[y][x]
                c = colors.get(t.terrain, (96, 152, 72))
                if t.obj == C.OBJ_TREE:
                    c = (58, 110, 52)
                s.set_at((x, y), c)
        return s

    def _draw_messages(self, surf):
        y = BAR_H + 8
        for msg, ttl in self.game.messages:
            a = min(255, ttl * 4)
            t = self.mid.render(msg, True, (255, 240, 180))
            box = pygame.Surface((t.get_width() + 20, t.get_height() + 8),
                                 pygame.SRCALPHA)
            box.fill((20, 18, 16, min(200, a)))
            surf.blit(box, (C.SCREEN_W // 2 - box.get_width() // 2, y))
            surf.blit(t, (C.SCREEN_W // 2 - t.get_width() // 2, y + 4))
            y += t.get_height() + 12

    def _draw_result(self, surf):
        overlay = pygame.Surface((C.SCREEN_W, C.SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        surf.blit(overlay, (0, 0))
        win = self.game.result == "win"
        text = "VICTORY!" if win else "DEFEAT"
        color = GOOD if win else BAD
        t = self.big.render(text, True, color)
        surf.blit(t, (C.SCREEN_W // 2 - t.get_width() // 2,
                      C.SCREEN_H // 2 - 60))
        sub = ("You razed the enemy stronghold." if win
               else "Your castle has fallen.")
        s = self.mid.render(sub, True, TEXT)
        surf.blit(s, (C.SCREEN_W // 2 - s.get_width() // 2,
                      C.SCREEN_H // 2))
        r = self.small.render("Press R to play again, or Esc to quit.",
                              True, DIM)
        surf.blit(r, (C.SCREEN_W // 2 - r.get_width() // 2,
                      C.SCREEN_H // 2 + 40))
