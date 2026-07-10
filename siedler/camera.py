"""Viewport / camera: maps world tile coordinates to screen pixels and back,
and handles scrolling via keyboard and screen-edge panning."""

from . import constants as C


class Camera:
    def __init__(self, view_w, view_h):
        self.view_w = view_w      # visible area in pixels (excludes HUD)
        self.view_h = view_h
        self.x = 0.0              # top-left world pixel currently shown
        self.y = 0.0
        self.speed = 520.0        # pixels per second

    @property
    def max_x(self):
        return max(0, C.MAP_W * C.TILE - self.view_w)

    @property
    def max_y(self):
        return max(0, C.MAP_H * C.TILE - self.view_h)

    def clamp(self):
        self.x = max(0, min(self.x, self.max_x))
        self.y = max(0, min(self.y, self.max_y))

    def center_on_tile(self, tx, ty):
        self.x = tx * C.TILE - self.view_w / 2
        self.y = ty * C.TILE - self.view_h / 2
        self.clamp()

    def handle_keys(self, keys, mouse_pos, dt, allow_edge=True):
        import pygame
        dx = dy = 0.0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            dx -= 1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            dx += 1
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            dy -= 1
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            dy += 1
        if allow_edge and mouse_pos is not None:
            mx, my = mouse_pos
            edge = 24
            if 0 <= my < self.view_h:
                if mx < edge:
                    dx -= 1
                elif mx > self.view_w - edge:
                    dx += 1
                if my < edge:
                    dy -= 1
                elif my > self.view_h - edge:
                    dy += 1
        self.x += dx * self.speed * dt
        self.y += dy * self.speed * dt
        self.clamp()

    # -------------------------------------------------- transforms
    def world_to_screen(self, wx, wy):
        return int(wx - self.x), int(wy - self.y)

    def tile_to_screen(self, tx, ty):
        return int(tx * C.TILE - self.x), int(ty * C.TILE - self.y)

    def screen_to_world(self, sx, sy):
        return sx + self.x, sy + self.y

    def screen_to_tile(self, sx, sy):
        wx, wy = self.screen_to_world(sx, sy)
        return int(wx // C.TILE), int(wy // C.TILE)

    def visible_tile_range(self):
        x0 = int(self.x // C.TILE)
        y0 = int(self.y // C.TILE)
        x1 = int((self.x + self.view_w) // C.TILE) + 1
        y1 = int((self.y + self.view_h) // C.TILE) + 1
        return (max(0, x0), max(0, y0),
                min(C.MAP_W, x1), min(C.MAP_H, y1))
