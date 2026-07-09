#!/usr/bin/env python3
"""Procedurally draws every sprite the game uses and writes them to assets/.

Run from the repository root:  python3 tools/generate_assets.py
Requires Pillow (only for regenerating art; the game itself needs pygame only).

Sprites are drawn at 4x resolution and downscaled with Lanczos so curves and
diagonals come out smooth.
"""

import os
import random
import sys

from PIL import Image, ImageDraw

S = 4  # supersampling factor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")

OUTLINE = (35, 28, 24, 255)


def canvas(w, h):
    img = Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0))
    return img, ImageDraw.Draw(img)


def save(img, *path):
    out = os.path.join(ASSETS, *path)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    img = img.resize((img.width // S, img.height // S), Image.LANCZOS)
    img.save(out)
    print("wrote", os.path.relpath(out, ROOT))


def rect(d, x0, y0, x1, y1, fill, outline=OUTLINE, width=1):
    d.rectangle([x0 * S, y0 * S, x1 * S, y1 * S], fill=fill,
                outline=outline, width=width * S)


def poly(d, pts, fill, outline=OUTLINE, width=1):
    d.polygon([(x * S, y * S) for x, y in pts], fill=fill,
              outline=outline, width=width * S)


def ell(d, x0, y0, x1, y1, fill, outline=OUTLINE, width=1):
    d.ellipse([x0 * S, y0 * S, x1 * S, y1 * S], fill=fill,
              outline=outline, width=width * S)


def line(d, pts, fill, width=1):
    d.line([(x * S, y * S) for x, y in pts], fill=fill, width=width * S)


def shade(color, f):
    """Lighten (f>1) or darken (f<1) an RGB(A) color."""
    r, g, b = color[:3]
    return (min(255, int(r * f)), min(255, int(g * f)), min(255, int(b * f)),
            255)


# ================================================================= tiles

def speckle(d, w, h, colors, n, rng, dot=1.4):
    for _ in range(n):
        x = rng.uniform(1, w - 2)
        y = rng.uniform(1, h - 2)
        c = rng.choice(colors)
        d.ellipse([x * S, y * S, (x + dot) * S, (y + dot) * S], fill=c)


def tile_grass(name, base, seed):
    rng = random.Random(seed)
    img, d = canvas(32, 32)
    d.rectangle([0, 0, 32 * S, 32 * S], fill=base)
    speckle(d, 32, 32, [shade(base, 1.12), shade(base, 0.9),
                        shade(base, 1.2)], 42, rng)
    # a few grass blades
    for _ in range(10):
        x = rng.uniform(2, 29)
        y = rng.uniform(3, 30)
        line(d, [(x, y), (x + 0.6, y - 2.2)], shade(base, 1.3), 1)
    save(img, "tiles", name)


def tile_water():
    rng = random.Random(7)
    base = (52, 108, 176, 255)
    img, d = canvas(32, 32)
    d.rectangle([0, 0, 32 * S, 32 * S], fill=base)
    speckle(d, 32, 32, [shade(base, 1.12), shade(base, 0.88)], 30, rng)
    for _ in range(6):
        x = rng.uniform(2, 22)
        y = rng.uniform(3, 29)
        line(d, [(x, y), (x + rng.uniform(4, 8), y)], shade(base, 1.35), 1)
    save(img, "tiles", "water.png")


def tile_sand():
    rng = random.Random(11)
    base = (206, 184, 128, 255)
    img, d = canvas(32, 32)
    d.rectangle([0, 0, 32 * S, 32 * S], fill=base)
    speckle(d, 32, 32, [shade(base, 1.1), shade(base, 0.9)], 36, rng)
    save(img, "tiles", "sand.png")


def tile_rock(name, base, glint=None, seed=13):
    rng = random.Random(seed)
    img, d = canvas(32, 32)
    d.rectangle([0, 0, 32 * S, 32 * S], fill=base)
    speckle(d, 32, 32, [shade(base, 1.18), shade(base, 0.8)], 34, rng)
    # angular crags
    for _ in range(5):
        x = rng.uniform(2, 24)
        y = rng.uniform(4, 26)
        w = rng.uniform(4, 8)
        poly(d, [(x, y + 3), (x + w * 0.5, y - 2), (x + w, y + 3)],
             shade(base, 1.05), outline=shade(base, 0.6))
    if glint:
        for _ in range(6):
            x = rng.uniform(3, 27)
            y = rng.uniform(3, 27)
            ell(d, x, y, x + 2.2, y + 2.2, glint, outline=shade(glint, 0.6))
    save(img, "tiles", name)


def obj_tree():
    img, d = canvas(32, 44)
    # trunk
    rect(d, 14, 30, 18, 42, (110, 74, 44, 255))
    # foliage: three stacked blobs
    green = (52, 122, 48, 255)
    ell(d, 5, 14, 27, 34, green)
    ell(d, 7, 6, 25, 24, shade(green, 1.12))
    ell(d, 10, 1, 22, 15, shade(green, 1.25))
    save(img, "tiles", "tree.png")


def obj_stump():
    img, d = canvas(32, 44)
    rect(d, 13, 34, 19, 42, (110, 74, 44, 255))
    ell(d, 12, 32, 20, 37, (168, 128, 84, 255))
    save(img, "tiles", "stump.png")


def obj_stone_deposit():
    rng = random.Random(21)
    img, d = canvas(32, 32)
    grey = (138, 138, 140, 255)
    for (x, y, w, h) in [(3, 14, 16, 14), (14, 10, 15, 15), (8, 20, 14, 10)]:
        ell(d, x, y, x + w, y + h, shade(grey, rng.uniform(0.9, 1.15)))
    ell(d, 12, 6, 24, 16, shade(grey, 1.2))
    save(img, "tiles", "stone_deposit.png")


# ============================================================== buildings

def hut(d, x0, y0, w, wall, roof, wall_h=18, roof_h=14):
    """Simple gabled house; returns ground line y."""
    gy = y0 + roof_h + wall_h
    rect(d, x0, y0 + roof_h, x0 + w, gy, wall)
    # door shadow line at base
    line(d, [(x0, gy), (x0 + w, gy)], shade(wall, 0.6), 1)
    poly(d, [(x0 - 2, y0 + roof_h), (x0 + w / 2, y0 - 1),
             (x0 + w + 2, y0 + roof_h)], roof)
    poly(d, [(x0 - 2, y0 + roof_h), (x0 + w / 2, y0 - 1),
             (x0 + w / 2, y0 + 3), (x0 + 2, y0 + roof_h + 2)],
         shade(roof, 1.18), outline=None)
    return gy


def door(d, cx, gy, wall):
    rect(d, cx - 3, gy - 9, cx + 3, gy, (72, 48, 30, 255))
    ell(d, cx - 3, gy - 12, cx + 3, gy - 6, (72, 48, 30, 255))


def window(d, cx, cy):
    rect(d, cx - 2.5, cy - 2.5, cx + 2.5, cy + 2.5, (240, 224, 150, 255))


def building_base(w, h):
    return canvas(w, h)


def draw_woodcutter():
    img, d = canvas(64, 76)
    wall = (150, 106, 62, 255)
    gy = hut(d, 8, 26, 40, wall, (96, 66, 40, 255))
    door(d, 28, gy, wall)
    window(d, 16, gy - 12)
    # log pile on the right
    for i, (lx, ly) in enumerate([(50, 68), (56, 68), (53, 62)]):
        ell(d, lx - 5, ly - 3, lx + 5, ly + 3, (128, 88, 52, 255))
        ell(d, lx + 2.5, ly - 2, lx + 5, ly + 2, (200, 162, 108, 255))
    # axe in stump
    rect(d, 4, 66, 10, 72, (110, 74, 44, 255))
    line(d, [(7, 66), (11, 58)], (110, 74, 44, 255), 1)
    poly(d, [(9, 57), (14, 59), (11, 62)], (176, 176, 184, 255))
    save(img, "buildings", "woodcutter.png")


def draw_sawmill():
    img, d = canvas(64, 76)
    wall = (162, 122, 74, 255)
    gy = hut(d, 6, 24, 44, wall, (110, 78, 46, 255))
    door(d, 28, gy, wall)
    # circular saw blade on the wall
    ell(d, 10, gy - 18, 22, gy - 6, (196, 196, 204, 255))
    ell(d, 14.5, gy - 13.5, 17.5, gy - 10.5, (110, 110, 118, 255))
    # plank stack
    for i in range(3):
        rect(d, 52, 66 - i * 4, 63, 69 - i * 4, (214, 178, 118, 255))
    save(img, "buildings", "sawmill.png")


def draw_stonecutter():
    img, d = canvas(64, 76)
    wall = (156, 150, 142, 255)
    gy = hut(d, 8, 26, 40, wall, (104, 100, 96, 255))
    door(d, 28, gy, wall)
    window(d, 40, gy - 12)
    # rock pile
    grey = (140, 140, 144, 255)
    ell(d, 48, 62, 62, 72, grey)
    ell(d, 52, 56, 63, 66, shade(grey, 1.15))
    save(img, "buildings", "stonecutter.png")


def draw_farm():
    img, d = canvas(64, 76)
    wall = (188, 148, 96, 255)
    gy = hut(d, 4, 24, 38, wall, (170, 60, 48, 255))
    door(d, 23, gy, wall)
    window(d, 12, gy - 12)
    # wheat patch
    wheat = (216, 186, 82, 255)
    rect(d, 46, 52, 63, 72, shade(wheat, 0.75))
    rng = random.Random(3)
    for _ in range(22):
        x = rng.uniform(47, 62)
        y = rng.uniform(53, 71)
        line(d, [(x, y + 2), (x, y - 2)], wheat, 1)
        ell(d, x - 0.8, y - 3.2, x + 0.8, y - 1.6, shade(wheat, 1.2),
            outline=None)
    save(img, "buildings", "farm.png")


def draw_mill():
    img, d = canvas(64, 76)
    body = (196, 186, 168, 255)
    # tapered tower
    poly(d, [(20, 24), (44, 24), (40, 70), (24, 70)], body)
    poly(d, [(16, 26), (32, 8), (48, 26)], (120, 84, 50, 255))
    door(d, 32, 70, body)
    window(d, 32, 42)
    # sails
    hub = (32, 20)
    sail = (222, 216, 200, 255)
    for dx, dy in [(16, -10), (-16, 10), (10, 16), (-10, -16)]:
        poly(d, [(hub[0], hub[1]), (hub[0] + dx, hub[1] + dy),
                 (hub[0] + dx * 0.75 + dy * 0.22,
                  hub[1] + dy * 0.75 - dx * 0.22)], sail)
    ell(d, 29.5, 17.5, 34.5, 22.5, (90, 62, 38, 255))
    save(img, "buildings", "mill.png")


def draw_bakery():
    img, d = canvas(64, 76)
    wall = (206, 162, 116, 255)
    gy = hut(d, 6, 28, 42, wall, (150, 94, 62, 255))
    door(d, 20, gy, wall)
    # chimney + smoke
    rect(d, 40, 20, 47, 36, (120, 100, 92, 255))
    for i, (sx, sy, r) in enumerate([(44, 15, 3), (47, 9, 3.6), (51, 3, 4)]):
        ell(d, sx - r, sy - r, sx + r, sy + r, (225, 225, 228, 210),
            outline=None)
    # bread sign
    ell(d, 32, gy - 18, 46, gy - 10, (196, 138, 66, 255))
    line(d, [(35, gy - 16), (43, gy - 13)], shade((196, 138, 66), 1.3), 1)
    save(img, "buildings", "bakery.png")


def draw_goldmine():
    img, d = canvas(64, 76)
    hill = (124, 116, 110, 255)
    poly(d, [(2, 72), (32, 22), (62, 72)], hill)
    poly(d, [(10, 72), (32, 34), (54, 72)], shade(hill, 1.1), outline=None)
    # tunnel with wooden frame
    rect(d, 22, 48, 42, 72, (60, 46, 34, 255))
    ell(d, 22, 40, 42, 56, (60, 46, 34, 255))
    rect(d, 20, 46, 24, 72, (128, 90, 52, 255))
    rect(d, 40, 46, 44, 72, (128, 90, 52, 255))
    rect(d, 19, 43, 45, 48, (128, 90, 52, 255))
    # gold glints on hill
    for gx, gy2 in [(14, 62), (50, 58), (44, 66)]:
        ell(d, gx, gy2, gx + 3, gy2 + 3, (238, 196, 62, 255))
    save(img, "buildings", "goldmine.png")


def draw_mint():
    img, d = canvas(64, 76)
    wall = (172, 158, 140, 255)
    gy = hut(d, 6, 26, 44, wall, (94, 88, 110, 255))
    door(d, 28, gy, wall)
    # chimney
    rect(d, 42, 18, 49, 34, (110, 104, 120, 255))
    ell(d, 44, 10, 52, 18, (230, 230, 234, 200), outline=None)
    # coin sign
    ell(d, 12, gy - 20, 24, gy - 8, (240, 198, 60, 255))
    ell(d, 15, gy - 17, 21, gy - 11, shade((240, 198, 60), 0.85))
    save(img, "buildings", "mint.png")


def draw_barracks():
    img, d = canvas(64, 76)
    wall = (150, 146, 152, 255)
    gy = hut(d, 5, 30, 46, wall, (86, 96, 128, 255), wall_h=22, roof_h=12)
    door(d, 28, gy, wall)
    # crenellation
    for i in range(4):
        rect(d, 7 + i * 12, 26, 13 + i * 12, 31, wall)
    # banner
    line(d, [(56, 70), (56, 34)], (110, 74, 44, 255), 1)
    poly(d, [(56, 34), (64, 38), (56, 42)], (60, 90, 190, 255))
    # shield sign
    poly(d, [(14, gy - 22), (24, gy - 22), (24, gy - 12), (19, gy - 7),
             (14, gy - 12)], (60, 90, 190, 255))
    line(d, [(14, gy - 17), (24, gy - 17)], (226, 226, 230, 255), 1)
    save(img, "buildings", "barracks.png")


def draw_tower(name, banner):
    img, d = canvas(32, 72)
    stone = (158, 154, 150, 255)
    rect(d, 8, 20, 24, 68, stone)
    for i, y in enumerate(range(24, 64, 8)):
        for x in range(9, 22, 5):
            rect(d, x + (i % 2) * 2, y, x + 4 + (i % 2) * 2, y + 3,
                 shade(stone, 0.9), outline=None)
    # crenellation
    for x in (6, 13.5, 21):
        rect(d, x, 14, x + 5, 21, stone)
    # arrow slit
    rect(d, 14.5, 34, 17.5, 44, (50, 44, 40, 255))
    # banner
    line(d, [(16, 14), (16, 2)], (110, 74, 44, 255), 1)
    poly(d, [(16, 2), (27, 5), (16, 9)], banner)
    save(img, "buildings", name)


def draw_castle(name, banner, wallc):
    img, d = canvas(96, 110)
    stone = wallc
    # side towers
    for tx in (4, 68):
        rect(d, tx, 34, tx + 24, 104, stone)
        for x in (tx - 2, tx + 8, tx + 18):
            rect(d, x, 28, x + 6, 36, stone)
        rect(d, tx + 9, 52, tx + 15, 62, (50, 44, 40, 255))
    # keep
    rect(d, 22, 48, 74, 104, shade(stone, 1.08))
    for i in range(5):
        rect(d, 24 + i * 10, 42, 30 + i * 10, 50, shade(stone, 1.08))
    # brick texture
    rng = random.Random(5)
    for _ in range(26):
        x = rng.uniform(6, 86)
        y = rng.uniform(38, 98)
        rect(d, x, y, x + 5, y + 2.5, shade(stone, 0.9), outline=None)
    # gate
    rect(d, 40, 84, 56, 104, (72, 48, 30, 255))
    ell(d, 40, 76, 56, 92, (72, 48, 30, 255))
    line(d, [(48, 78), (48, 104)], shade((72, 48, 30), 1.5), 1)
    # windows
    window(d, 32, 66)
    window(d, 64, 66)
    # flag
    line(d, [(48, 40), (48, 12)], (110, 74, 44, 255), 1)
    poly(d, [(48, 12), (66, 17), (48, 22)], banner)
    save(img, "buildings", name)


def draw_site():
    img, d = canvas(64, 64)
    # dirt patch
    ell(d, 2, 40, 62, 62, (150, 118, 82, 255))
    # plank frame
    for x0, y0, x1, y1 in [(10, 52, 54, 56), (14, 44, 50, 48)]:
        rect(d, x0, y0, x1, y1, (204, 168, 112, 255))
    line(d, [(16, 58), (28, 30)], (204, 168, 112, 255), 2)
    line(d, [(48, 58), (36, 30)], (204, 168, 112, 255), 2)
    line(d, [(28, 30), (36, 30)], (204, 168, 112, 255), 2)
    # stone blocks
    rect(d, 6, 34, 16, 42, (150, 150, 154, 255))
    rect(d, 48, 36, 58, 44, (150, 150, 154, 255))
    save(img, "buildings", "site.png")


# ================================================================== units

def draw_unit(name, tunic, hat=None, tool=None):
    img, d = canvas(22, 30)
    skin = (232, 188, 152, 255)
    # legs
    rect(d, 7, 22, 10, 29, (92, 64, 40, 255))
    rect(d, 12, 22, 15, 29, (92, 64, 40, 255))
    # body
    rect(d, 6, 12, 16, 23, tunic)
    # arms
    rect(d, 4, 13, 7, 20, shade(tunic, 0.85))
    rect(d, 15, 13, 18, 20, shade(tunic, 0.85))
    # head
    ell(d, 6.5, 2, 15.5, 12, skin)
    if hat == "cap":
        poly(d, [(6, 6), (11, 0.5), (16, 6)], shade(tunic, 1.2))
    elif hat == "helm":
        ell(d, 6, 1.5, 16, 8.5, (168, 168, 178, 255))
        rect(d, 6, 5, 16, 7, (168, 168, 178, 255), outline=None)
    if tool == "hammer":
        line(d, [(18, 19), (21, 12)], (110, 74, 44, 255), 1)
        rect(d, 18.5, 9.5, 22, 13, (150, 150, 158, 255))
    elif tool == "sword":
        line(d, [(18, 20), (21.5, 9)], (210, 210, 220, 255), 1)
        line(d, [(17, 17), (21, 18.5)], (120, 84, 50, 255), 1)
        # shield on other arm
        ell(d, 1, 12, 8, 21, shade(tunic, 1.25))
    elif tool == "pick":
        line(d, [(18, 20), (20, 10)], (110, 74, 44, 255), 1)
        line(d, [(16.5, 10.5), (22, 12.5)], (150, 150, 158, 255), 1)
    save(img, "units", name)


# =================================================================== ui

def icon_base():
    return canvas(20, 20)


def icon_log():
    img, d = icon_base()
    ell(d, 1, 6, 19, 14, (128, 88, 52, 255))
    ell(d, 13, 6.5, 19, 13.5, (208, 170, 116, 255))
    ell(d, 15, 8.5, 17, 11.5, (150, 110, 70, 255))
    save(img, "ui", "icon_log.png")


def icon_plank():
    img, d = icon_base()
    for i in range(3):
        rect(d, 2, 3 + i * 5, 18, 7 + i * 5, (214, 178, 118, 255))
    save(img, "ui", "icon_plank.png")


def icon_stone():
    img, d = icon_base()
    grey = (150, 150, 154, 255)
    poly(d, [(3, 15), (6, 6), (13, 4), (17, 10), (15, 16), (6, 17)], grey)
    line(d, [(7, 7), (12, 14)], shade(grey, 0.8), 1)
    save(img, "ui", "icon_stone.png")


def icon_grain():
    img, d = icon_base()
    wheat = (216, 186, 82, 255)
    for x in (6, 10, 14):
        line(d, [(x, 18), (x, 8)], shade(wheat, 0.8), 1)
        for y in (5, 8, 11):
            ell(d, x - 2, y - 1.6, x + 2, y + 1.6, wheat)
    save(img, "ui", "icon_grain.png")


def icon_flour():
    img, d = icon_base()
    sack = (222, 214, 196, 255)
    poly(d, [(4, 18), (4, 8), (7, 4), (13, 4), (16, 8), (16, 18)], sack)
    rect(d, 7.5, 2, 12.5, 5.5, shade(sack, 0.85))
    ell(d, 7, 10, 13, 14, (250, 250, 250, 255), outline=None)
    save(img, "ui", "icon_flour.png")


def icon_bread():
    img, d = icon_base()
    crust = (196, 138, 66, 255)
    ell(d, 2, 6, 18, 15, crust)
    for x in (6, 10, 14):
        line(d, [(x - 1.4, 8.5), (x + 1.4, 10.5)], shade(crust, 1.35), 1)
    save(img, "ui", "icon_bread.png")


def icon_ore():
    img, d = icon_base()
    grey = (120, 116, 112, 255)
    poly(d, [(3, 15), (6, 6), (13, 4), (17, 10), (15, 16), (6, 17)], grey)
    for x, y in [(7, 8), (12, 12), (11, 7)]:
        ell(d, x, y, x + 2.6, y + 2.6, (238, 196, 62, 255))
    save(img, "ui", "icon_ore.png")


def icon_coin():
    img, d = icon_base()
    gold = (240, 198, 60, 255)
    ell(d, 2, 2, 18, 18, gold)
    ell(d, 5, 5, 15, 15, shade(gold, 0.86))
    line(d, [(10, 7), (10, 13)], shade(gold, 1.3), 1)
    save(img, "ui", "icon_coin.png")


def icon_pop():
    img, d = icon_base()
    skin = (232, 188, 152, 255)
    ell(d, 6, 1, 14, 9, skin)
    poly(d, [(3, 19), (5, 10), (15, 10), (17, 19)], (60, 90, 190, 255))
    save(img, "ui", "icon_pop.png")


def icon_sword():
    img, d = icon_base()
    line(d, [(4, 16), (14, 4)], (210, 210, 220, 255), 2)
    line(d, [(5, 11), (10, 16)], (120, 84, 50, 255), 2)
    line(d, [(3, 17), (5, 15)], (120, 84, 50, 255), 2)
    save(img, "ui", "icon_sword.png")


# =================================================================== main

def main():
    random.seed(1)
    grass = (96, 152, 72, 255)
    tile_grass("grass.png", grass, 1)
    tile_grass("grass2.png", shade(grass, 0.94), 2)
    tile_water()
    tile_sand()
    tile_rock("rock.png", (128, 124, 122, 255))
    tile_rock("gold.png", (134, 122, 100, 255), glint=(238, 196, 62, 255),
              seed=17)
    obj_tree()
    obj_stump()
    obj_stone_deposit()

    draw_castle("castle.png", (60, 90, 190, 255), (162, 158, 154, 255))
    draw_castle("enemy_hq.png", (190, 56, 48, 255), (140, 128, 124, 255))
    draw_woodcutter()
    draw_sawmill()
    draw_stonecutter()
    draw_farm()
    draw_mill()
    draw_bakery()
    draw_goldmine()
    draw_mint()
    draw_barracks()
    draw_tower("tower.png", (60, 90, 190, 255))
    draw_tower("enemy_tower.png", (190, 56, 48, 255))
    draw_site()

    draw_unit("settler.png", (60, 90, 190, 255), hat="cap")
    draw_unit("builder.png", (188, 148, 60, 255), hat="cap", tool="hammer")
    draw_unit("worker.png", (108, 116, 124, 255), hat="cap", tool="pick")
    draw_unit("soldier.png", (60, 90, 190, 255), hat="helm", tool="sword")
    draw_unit("enemy_soldier.png", (190, 56, 48, 255), hat="helm",
              tool="sword")

    icon_log()
    icon_plank()
    icon_stone()
    icon_grain()
    icon_flour()
    icon_bread()
    icon_ore()
    icon_coin()
    icon_pop()
    icon_sword()
    print("done.")


if __name__ == "__main__":
    sys.exit(main())
