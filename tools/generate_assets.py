#!/usr/bin/env python3
"""Procedurally draws every sprite the game uses (space-colony theme) and
writes them to assets/.

Run from the repository root:  python3 tools/generate_assets.py
Requires Pillow (only for regenerating art; the game itself needs pygame only).

Sprites are drawn at 4x resolution and downscaled with Lanczos for smooth
edges. Output filenames are kept stable so siedler/assets.py keeps loading them.
"""

import os
import random
import sys

from PIL import Image, ImageDraw

S = 4  # supersampling factor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")

OUTLINE = (26, 24, 32, 255)


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
    r, g, b = color[:3]
    return (min(255, int(r * f)), min(255, int(g * f)), min(255, int(b * f)),
            255)


# palette
METAL = (150, 156, 168, 255)
METAL_D = (96, 102, 116, 255)
BLUE = (66, 130, 224, 255)
CYAN = (94, 220, 232, 255)
GLASS = (150, 214, 226, 255)
AMBER = (240, 176, 70, 255)
ALIEN = (176, 66, 120, 255)
ALIEN_D = (120, 44, 92, 255)
BIO = (150, 226, 130, 255)
RED = (208, 66, 60, 255)


# ================================================================= tiles

def speckle(d, w, h, colors, n, rng, dot=1.4):
    for _ in range(n):
        x = rng.uniform(1, w - 2)
        y = rng.uniform(1, h - 2)
        c = rng.choice(colors)
        d.ellipse([x * S, y * S, (x + dot) * S, (y + dot) * S], fill=c)


def tile_regolith(name, base, seed):
    rng = random.Random(seed)
    img, d = canvas(32, 32)
    d.rectangle([0, 0, 32 * S, 32 * S], fill=base)
    speckle(d, 32, 32, [shade(base, 1.12), shade(base, 0.88),
                        shade(base, 1.2)], 44, rng)
    # small craters
    for _ in range(3):
        x = rng.uniform(3, 27)
        y = rng.uniform(3, 27)
        r = rng.uniform(2, 4)
        ell(d, x, y, x + r, y + r, shade(base, 0.82), outline=None)
        ell(d, x, y - 0.6, x + r, y + r - 0.6, shade(base, 1.12),
            outline=None)
    save(img, "tiles", name)


def tile_chasm():
    rng = random.Random(7)
    base = (26, 32, 52, 255)
    img, d = canvas(32, 32)
    d.rectangle([0, 0, 32 * S, 32 * S], fill=base)
    speckle(d, 32, 32, [shade(base, 1.5), shade(base, 0.7)], 26, rng)
    for _ in range(4):
        x = rng.uniform(2, 20)
        y = rng.uniform(3, 29)
        line(d, [(x, y), (x + rng.uniform(4, 8), y)], shade(base, 1.7), 1)
    save(img, "tiles", "water.png")


def tile_dust():
    rng = random.Random(11)
    base = (196, 170, 130, 255)
    img, d = canvas(32, 32)
    d.rectangle([0, 0, 32 * S, 32 * S], fill=base)
    speckle(d, 32, 32, [shade(base, 1.08), shade(base, 0.9)], 36, rng)
    save(img, "tiles", "sand.png")


def tile_rock(name, base, crystals=False, seed=13):
    rng = random.Random(seed)
    img, d = canvas(32, 32)
    d.rectangle([0, 0, 32 * S, 32 * S], fill=base)
    speckle(d, 32, 32, [shade(base, 1.18), shade(base, 0.8)], 30, rng)
    for _ in range(5):
        x = rng.uniform(2, 24)
        y = rng.uniform(4, 26)
        w = rng.uniform(4, 8)
        poly(d, [(x, y + 3), (x + w * 0.5, y - 2), (x + w, y + 3)],
             shade(base, 1.05), outline=shade(base, 0.6))
    if crystals:
        for _ in range(5):
            x = rng.uniform(4, 26)
            y = rng.uniform(6, 26)
            h = rng.uniform(4, 8)
            poly(d, [(x, y + h), (x + 1.6, y), (x + 3.2, y + h)],
                 CYAN, outline=shade(CYAN, 0.6))
    save(img, "tiles", name)


def obj_ore_node():
    # a boulder with glowing amber ore veins (renewable "ore node")
    img, d = canvas(32, 40)
    rock = (120, 116, 124, 255)
    poly(d, [(4, 38), (6, 20), (14, 12), (24, 14), (28, 26), (26, 38)],
         rock)
    poly(d, [(10, 24), (16, 16), (22, 20)], shade(rock, 1.16), outline=None)
    for (a, b) in [((10, 30), (16, 22)), ((18, 32), (22, 24)),
                   ((13, 36), (17, 30))]:
        line(d, [a, b], AMBER, 1)
        ell(d, b[0] - 1, b[1] - 1, b[0] + 1.4, b[1] + 1.4,
            shade(AMBER, 1.2), outline=None)
    save(img, "tiles", "tree.png")


def obj_stump():
    img, d = canvas(32, 40)
    rock = (120, 116, 124, 255)
    poly(d, [(8, 38), (10, 30), (22, 30), (24, 38)], rock)
    save(img, "tiles", "stump.png")


def obj_mineral():
    rng = random.Random(21)
    img, d = canvas(32, 32)
    grey = (126, 132, 144, 255)
    for (x, y, w, h) in [(3, 15, 15, 13), (14, 11, 14, 14), (8, 20, 13, 9)]:
        ell(d, x, y, x + w, y + h, shade(grey, rng.uniform(0.9, 1.15)))
    # bluish mineral flecks
    for _ in range(5):
        x = rng.uniform(6, 24)
        y = rng.uniform(14, 26)
        ell(d, x, y, x + 2, y + 2, (120, 170, 210, 255), outline=None)
    save(img, "tiles", "stone_deposit.png")


# ============================================================== buildings

def panel_lines(d, x0, y0, x1, y1, col):
    for yy in range(int(y0) + 4, int(y1), 6):
        line(d, [(x0, yy), (x1, yy)], shade(col, 0.82), 1)


def module(d, x0, y0, w, wall, roof, wall_h=18, roof_h=10, flat=True):
    gy = y0 + roof_h + wall_h
    rect(d, x0, y0 + roof_h, x0 + w, gy, wall)
    panel_lines(d, x0 + 1, y0 + roof_h, x0 + w - 1, gy, wall)
    if flat:
        rect(d, x0 - 2, y0 + roof_h - 3, x0 + w + 2, y0 + roof_h, roof)
    else:
        poly(d, [(x0 - 2, y0 + roof_h), (x0 + w / 2, y0 - 1),
                 (x0 + w + 2, y0 + roof_h)], roof)
    return gy


def door(d, cx, gy, col=(40, 44, 60, 255)):
    rect(d, cx - 3, gy - 9, cx + 3, gy, col)
    ell(d, cx - 3, gy - 12, cx + 3, gy - 6, col)


def glow_window(d, cx, cy, col=CYAN):
    rect(d, cx - 2.5, cy - 2.5, cx + 2.5, cy + 2.5, col)


def antenna(d, x, top, col=METAL, tip=CYAN):
    line(d, [(x, top + 12), (x, top)], col, 1)
    ell(d, x - 1.6, top - 1.6, x + 1.6, top + 1.6, tip, outline=None)


def draw_mining_rig():
    img, d = canvas(64, 76)
    gy = module(d, 8, 30, 40, METAL, METAL_D)
    door(d, 20, gy)
    glow_window(d, 38, gy - 12)
    # drill derrick
    poly(d, [(44, 70), (52, 30), (60, 70)], METAL_D)
    line(d, [(48, 50), (56, 50)], METAL, 1)
    line(d, [(46, 60), (58, 60)], METAL, 1)
    poly(d, [(50, 70), (52, 74), (54, 70)], AMBER, outline=None)
    antenna(d, 14, 22)
    save(img, "buildings", "woodcutter.png")


def draw_smelter():
    img, d = canvas(64, 76)
    gy = module(d, 6, 28, 44, METAL, METAL_D)
    door(d, 22, gy)
    # furnace glow
    rect(d, 30, gy - 14, 42, gy - 2, (40, 30, 30, 255))
    rect(d, 31, gy - 8, 41, gy - 2, (240, 140, 60, 255), outline=None)
    # chimney with heat shimmer
    rect(d, 12, 16, 20, 30, METAL_D)
    for i, (sx, sy, r) in enumerate([(16, 12, 3), (19, 7, 3.4)]):
        ell(d, sx - r, sy - r, sx + r, sy + r, (220, 160, 120, 160),
            outline=None)
    save(img, "buildings", "sawmill.png")


def draw_excavator():
    img, d = canvas(64, 76)
    gy = module(d, 8, 30, 40, (150, 150, 156, 255), (96, 96, 104, 255))
    door(d, 20, gy)
    glow_window(d, 38, gy - 12, GLASS)
    # scoop arm
    line(d, [(48, 66), (58, 50)], METAL_D, 2)
    poly(d, [(56, 46), (62, 50), (60, 56), (54, 54)], METAL)
    save(img, "buildings", "stonecutter.png")


def draw_biodome():
    img, d = canvas(64, 76)
    # base ring
    rect(d, 10, 56, 54, 70, METAL_D)
    door(d, 32, 70)
    # glass dome
    ell(d, 8, 24, 56, 72, (150, 214, 226, 210))
    ell(d, 8, 24, 56, 72, None, outline=shade(GLASS, 0.7), width=1)
    line(d, [(32, 26), (32, 60)], shade(GLASS, 0.7), 1)
    ell(d, 12, 40, 52, 72, None, outline=shade(GLASS, 0.7), width=1)
    # plants inside
    for x in (20, 30, 40):
        line(d, [(x, 60), (x, 50)], (70, 160, 80, 255), 1)
        ell(d, x - 2, 46, x + 2, 51, BIO, outline=None)
    save(img, "buildings", "farm.png")


def draw_processor():
    img, d = canvas(64, 76)
    gy = module(d, 8, 30, 40, METAL, METAL_D)
    door(d, 20, gy)
    # rotating drum
    ell(d, 34, gy - 20, 52, gy - 4, (176, 182, 194, 255))
    ell(d, 40, gy - 14, 46, gy - 8, METAL_D)
    antenna(d, 14, 22)
    save(img, "buildings", "mill.png")


def draw_foodsynth():
    img, d = canvas(64, 76)
    gy = module(d, 6, 30, 44, METAL, (90, 120, 90, 255))
    door(d, 20, gy)
    # nutrient tanks
    for tx in (34, 42):
        rect(d, tx, gy - 18, tx + 5, gy - 2, (120, 200, 150, 255))
        ell(d, tx, gy - 21, tx + 5, gy - 15, (120, 200, 150, 255))
    glow_window(d, 14, gy - 12, BIO)
    save(img, "buildings", "bakery.png")


def draw_crystal_extractor():
    img, d = canvas(64, 76)
    hill = (108, 104, 112, 255)
    poly(d, [(2, 72), (32, 24), (62, 72)], hill)
    poly(d, [(12, 72), (32, 36), (52, 72)], shade(hill, 1.1), outline=None)
    # tunnel
    rect(d, 24, 50, 40, 72, (36, 40, 56, 255))
    ell(d, 24, 42, 40, 58, (36, 40, 56, 255))
    rect(d, 22, 48, 26, 72, METAL)
    rect(d, 38, 48, 42, 72, METAL)
    rect(d, 21, 45, 43, 50, METAL)
    # crystals on hill
    for (cx, cy, h) in [(14, 60, 8), (50, 56, 9), (44, 64, 6)]:
        poly(d, [(cx, cy), (cx + 2, cy - h), (cx + 4, cy)], CYAN,
             outline=shade(CYAN, 0.6))
    save(img, "buildings", "goldmine.png")


def draw_fabricator():
    img, d = canvas(64, 76)
    gy = module(d, 6, 28, 44, (156, 150, 170, 255), (100, 96, 120, 255))
    door(d, 28, gy)
    # coin/credit press
    ell(d, 12, gy - 20, 24, gy - 8, AMBER)
    ell(d, 15, gy - 17, 21, gy - 11, shade(AMBER, 0.85))
    rect(d, 40, 16, 48, 30, METAL_D)
    ell(d, 42, 9, 50, 17, (220, 210, 180, 170), outline=None)
    save(img, "buildings", "mint.png")


def draw_barracks():
    img, d = canvas(64, 76)
    gy = module(d, 5, 32, 46, (140, 148, 160, 255), (80, 96, 128, 255),
                wall_h=20, roof_h=8)
    door(d, 28, gy)
    # armored plating + stripe
    line(d, [(5, 40), (51, 40)], BLUE, 2)
    for i in range(4):
        rect(d, 7 + i * 12, 28, 13 + i * 12, 32, METAL_D)
    # emblem
    poly(d, [(14, gy - 22), (24, gy - 22), (24, gy - 12), (19, gy - 7),
             (14, gy - 12)], BLUE)
    line(d, [(19, gy - 20), (19, gy - 10)], (226, 226, 230, 255), 1)
    line(d, [(15, gy - 15), (23, gy - 15)], (226, 226, 230, 255), 1)
    antenna(d, 46, 22, tip=BLUE)
    save(img, "buildings", "barracks.png")


def draw_turret(name, accent):
    img, d = canvas(32, 72)
    rect(d, 8, 30, 24, 68, METAL)
    panel_lines(d, 9, 32, 23, 66, METAL)
    # turret head
    ell(d, 6, 20, 26, 36, METAL_D)
    # barrel
    rect(d, 15, 12, 19, 24, (60, 64, 78, 255))
    ell(d, 14.5, 24, 17.5, 30, accent, outline=None)
    rect(d, 6, 28, 10, 34, accent, outline=None)
    save(img, "buildings", name)


def draw_command_center(name, accent, wallc):
    img, d = canvas(96, 110)
    stone = wallc
    # side towers
    for tx in (4, 68):
        rect(d, tx, 40, tx + 24, 104, stone)
        panel_lines(d, tx + 1, 42, tx + 23, 102, stone)
        rect(d, tx + 9, 54, tx + 15, 62, accent)
    # central keep with dome
    rect(d, 22, 52, 74, 104, shade(stone, 1.06))
    ell(d, 22, 30, 74, 66, shade(stone, 1.12))
    ell(d, 30, 34, 66, 58, (150, 214, 226, 150), outline=shade(GLASS, 0.7))
    # brick / panel texture
    rng = random.Random(5)
    for _ in range(22):
        x = rng.uniform(8, 86)
        y = rng.uniform(56, 98)
        rect(d, x, y, x + 5, y + 2.5, shade(stone, 0.9), outline=None)
    # gate
    rect(d, 40, 84, 56, 104, (40, 44, 60, 255))
    ell(d, 40, 76, 56, 92, (40, 44, 60, 255))
    line(d, [(48, 78), (48, 104)], accent, 1)
    glow_window(d, 32, 70, accent)
    glow_window(d, 64, 70, accent)
    # comms mast
    antenna(d, 48, 14, tip=accent)
    save(img, "buildings", name)


def draw_hive(name):
    img, d = canvas(96, 110)
    body = ALIEN
    # organic mound
    ell(d, 6, 40, 90, 106, body)
    ell(d, 18, 24, 78, 92, shade(body, 1.1))
    ell(d, 32, 12, 64, 60, shade(body, 1.18))
    # pulsing pods
    rng = random.Random(9)
    for _ in range(10):
        x = rng.uniform(16, 78)
        y = rng.uniform(40, 96)
        r = rng.uniform(3, 6)
        ell(d, x, y, x + r, y + r, shade(BIO, 0.9), outline=ALIEN_D)
    # maw
    ell(d, 40, 74, 60, 96, (30, 16, 26, 255))
    for i in range(4):
        poly(d, [(42 + i * 4.5, 78), (44 + i * 4.5, 84), (46 + i * 4.5, 78)],
             (220, 210, 200, 255), outline=None)
    # spikes
    for (sx, sy) in [(30, 24), (48, 12), (66, 24)]:
        poly(d, [(sx, sy + 8), (sx + 2, sy - 6), (sx + 4, sy + 8)],
             ALIEN_D, outline=None)
    save(img, "buildings", name)


def draw_spire(name):
    img, d = canvas(32, 72)
    poly(d, [(10, 68), (16, 14), (22, 68)], ALIEN)
    poly(d, [(13, 40), (16, 14), (19, 40)], shade(ALIEN, 1.15), outline=None)
    ell(d, 12, 20, 20, 30, (30, 16, 26, 255))
    ell(d, 14, 22, 18, 27, BIO, outline=None)
    for yy in (44, 54, 62):
        ell(d, 11, yy, 15, yy + 3, shade(BIO, 0.9), outline=ALIEN_D)
    save(img, "buildings", name)


def draw_site():
    img, d = canvas(64, 64)
    ell(d, 2, 42, 62, 62, (150, 120, 92, 255))
    # metal scaffold frame
    for x0, y0, x1, y1 in [(10, 52, 54, 56), (14, 44, 50, 48)]:
        rect(d, x0, y0, x1, y1, METAL)
    line(d, [(16, 58), (28, 30)], METAL, 2)
    line(d, [(48, 58), (36, 30)], METAL, 2)
    line(d, [(28, 30), (36, 30)], METAL, 2)
    rect(d, 6, 34, 16, 42, METAL_D)
    ell(d, 44, 36, 52, 42, CYAN, outline=None)
    save(img, "buildings", "site.png")


# ================================================================== units

def humanoid(name, suit, visor=CYAN, weapon=None, bulky=False, helmet=True):
    img, d = canvas(22, 30)
    skin = (232, 196, 168, 255)
    bw = 12 if bulky else 10
    bx = 11 - bw / 2
    # legs
    rect(d, bx + 1, 22, bx + bw / 2 - 0.5, 29, shade(suit, 0.7))
    rect(d, bx + bw / 2 + 0.5, 22, bx + bw - 1, 29, shade(suit, 0.7))
    # torso (armor)
    rect(d, bx, 12, bx + bw, 23, suit)
    line(d, [(11, 12), (11, 23)], shade(suit, 1.2), 1)
    # arms
    rect(d, bx - 2, 13, bx, 20, shade(suit, 0.85))
    rect(d, bx + bw, 13, bx + bw + 2, 20, shade(suit, 0.85))
    # head
    if helmet:
        ell(d, 6.5, 2, 15.5, 12, shade(suit, 1.05))
        rect(d, 7.5, 6, 14.5, 9, visor, outline=None)  # visor
    else:
        ell(d, 6.5, 2, 15.5, 12, skin)
    if weapon == "rifle":
        line(d, [(bx + bw, 16), (bx + bw + 6, 13)], (60, 64, 78, 255), 1)
        ell(d, bx + bw + 5.5, 12, bx + bw + 7.5, 14, CYAN, outline=None)
    elif weapon == "longrifle":
        line(d, [(bx + bw - 1, 17), (bx + bw + 9, 11)], (60, 64, 78, 255), 1)
        ell(d, bx + bw + 8, 10, bx + bw + 10.5, 12.5, CYAN, outline=None)
    elif weapon == "cannon":
        rect(d, bx + bw, 12, bx + bw + 7, 17, (60, 64, 78, 255))
        ell(d, bx + bw + 6, 12, bx + bw + 10, 17, (240, 140, 60, 255),
            outline=None)
    elif weapon == "tool":
        line(d, [(bx + bw, 19), (bx + bw + 3, 11)], (150, 120, 60, 255), 1)
        rect(d, bx + bw + 1.5, 8.5, bx + bw + 5, 12, METAL)
    elif weapon == "pick":
        line(d, [(bx + bw, 20), (bx + bw + 2, 10)], (150, 120, 60, 255), 1)
        line(d, [(bx + bw - 1, 10.5), (bx + bw + 5, 12.5)], METAL, 1)
    save(img, "units", name)


def alien_unit(name, body, ranged=False, small=False):
    img, d = canvas(22, 30)
    sc = 0.8 if small else 1.0
    cx = 11
    # legs / tentacles
    for ox in (-3, 3):
        line(d, [(cx + ox, 22), (cx + ox * 1.4, 29)], shade(body, 0.7), 2)
    # body
    bw = 11 * sc
    ell(d, cx - bw / 2, 12, cx + bw / 2, 25, body)
    ell(d, cx - bw / 2 + 1, 13, cx + bw / 2 - 1, 20, shade(body, 1.15),
        outline=None)
    # head
    ell(d, cx - 4 * sc, 3, cx + 4 * sc, 12, shade(body, 1.08))
    # eyes (bio-glow)
    for ox in (-2, 2):
        ell(d, cx + ox * sc - 1, 6, cx + ox * sc + 1, 8, BIO, outline=None)
    # arms / claws
    line(d, [(cx - bw / 2, 15), (cx - bw / 2 - 3, 20)], shade(body, 0.8), 2)
    if ranged:
        # spit tube
        line(d, [(cx + bw / 2, 15), (cx + bw / 2 + 5, 12)],
             shade(body, 0.7), 2)
        ell(d, cx + bw / 2 + 4, 10.5, cx + bw / 2 + 7, 13.5, BIO,
            outline=None)
    else:
        line(d, [(cx + bw / 2, 15), (cx + bw / 2 + 3, 20)],
             shade(body, 0.8), 2)
    save(img, "units", name)


# =================================================================== ui

def icon_base():
    return canvas(20, 20)


def icon_ore():  # log -> ore chunk
    img, d = icon_base()
    grey = (124, 120, 128, 255)
    poly(d, [(3, 15), (6, 6), (13, 4), (17, 10), (15, 16), (6, 17)], grey)
    for x, y in [(7, 9), (12, 12), (11, 8)]:
        ell(d, x, y, x + 2.4, y + 2.4, AMBER, outline=None)
    save(img, "ui", "icon_log.png")


def icon_alloy():  # plank -> metal bars
    img, d = icon_base()
    for i in range(3):
        rect(d, 2, 4 + i * 5, 18, 8 + i * 5, (176, 182, 194, 255))
        line(d, [(3, 5 + i * 5), (17, 5 + i * 5)], (210, 216, 226, 255), 1)
    save(img, "ui", "icon_plank.png")


def icon_mineral():  # stone -> crystal chunk (grey/blue)
    img, d = icon_base()
    grey = (138, 146, 160, 255)
    poly(d, [(4, 16), (7, 6), (13, 4), (16, 11), (13, 17), (7, 17)], grey)
    poly(d, [(7, 6), (13, 4), (10, 11)], (120, 170, 210, 255), outline=None)
    save(img, "ui", "icon_stone.png")


def icon_biomass():  # grain -> green pod
    img, d = icon_base()
    for x in (7, 11):
        line(d, [(x, 18), (x, 8)], (70, 150, 80, 255), 1)
        ell(d, x - 2.5, 4, x + 2.5, 12, BIO)
    save(img, "ui", "icon_grain.png")


def icon_protein():  # flour -> nutrient canister
    img, d = icon_base()
    rect(d, 6, 4, 14, 18, (150, 200, 170, 255))
    rect(d, 6, 4, 14, 7, (110, 160, 130, 255))
    ell(d, 8, 9, 12, 13, (240, 255, 245, 255), outline=None)
    save(img, "ui", "icon_flour.png")


def icon_rations():  # bread -> ration pack
    img, d = icon_base()
    rect(d, 3, 6, 17, 15, (196, 150, 90, 255))
    line(d, [(3, 10), (17, 10)], (150, 110, 66, 255), 1)
    rect(d, 8, 6, 12, 15, (150, 110, 66, 255), outline=None)
    save(img, "ui", "icon_bread.png")


def icon_crystal():  # ore -> cyan crystal
    img, d = icon_base()
    poly(d, [(10, 2), (14, 9), (10, 18), (6, 9)], CYAN,
         outline=shade(CYAN, 0.6))
    line(d, [(10, 3), (10, 17)], shade(CYAN, 1.3), 1)
    save(img, "ui", "icon_ore.png")


def icon_credits():  # coin -> credit chip
    img, d = icon_base()
    rect(d, 3, 4, 17, 16, AMBER)
    rect(d, 3, 4, 17, 16, None, outline=shade(AMBER, 0.6), width=1)
    rect(d, 11, 6, 15, 9, shade(AMBER, 0.8), outline=None)
    line(d, [(5, 12), (12, 12)], shade(AMBER, 1.25), 1)
    save(img, "ui", "icon_coin.png")


def icon_pop():
    img, d = icon_base()
    ell(d, 6, 1, 14, 9, (232, 196, 168, 255))
    poly(d, [(3, 19), (5, 10), (15, 10), (17, 19)], BLUE)
    save(img, "ui", "icon_pop.png")


def icon_sword():  # generic troop icon (blaster)
    img, d = icon_base()
    rect(d, 3, 9, 14, 13, (70, 74, 88, 255))
    rect(d, 12, 7, 17, 11, (70, 74, 88, 255))
    ell(d, 15, 6.5, 18.5, 10, CYAN, outline=None)
    rect(d, 5, 13, 8, 17, (70, 74, 88, 255))
    save(img, "ui", "icon_sword.png")


# =================================================================== main

def main():
    random.seed(1)
    regolith = (150, 96, 72, 255)
    tile_regolith("grass.png", regolith, 1)
    tile_regolith("grass2.png", shade(regolith, 0.92), 2)
    tile_chasm()
    tile_dust()
    tile_rock("rock.png", (110, 108, 116, 255))
    tile_rock("gold.png", (104, 110, 118, 255), crystals=True, seed=17)
    obj_ore_node()
    obj_stump()
    obj_mineral()

    draw_command_center("castle.png", CYAN, (158, 162, 172, 255))
    draw_hive("enemy_hq.png")
    draw_mining_rig()
    draw_smelter()
    draw_excavator()
    draw_biodome()
    draw_processor()
    draw_foodsynth()
    draw_crystal_extractor()
    draw_fabricator()
    draw_barracks()
    draw_turret("tower.png", CYAN)
    draw_spire("enemy_tower.png")
    draw_site()

    # player civilians
    humanoid("colonist.png", BLUE, helmet=True)
    humanoid("builder.png", (210, 170, 60, 255), weapon="tool", helmet=True)
    humanoid("worker.png", (120, 128, 140, 255), weapon="pick", helmet=True)
    # player troops
    humanoid("marine.png", (60, 96, 200, 255), weapon="rifle")
    humanoid("ranger.png", (70, 150, 180, 255), weapon="longrifle")
    humanoid("heavy.png", (44, 70, 150, 255), weapon="cannon", bulky=True)
    # enemy troops
    alien_unit("alien.png", ALIEN)
    alien_unit("spitter.png", (150, 90, 170, 255), ranged=True)
    alien_unit("scout.png", (200, 90, 90, 255), small=True)

    icon_ore()
    icon_alloy()
    icon_mineral()
    icon_biomass()
    icon_protein()
    icon_rations()
    icon_crystal()
    icon_credits()
    icon_pop()
    icon_sword()
    print("done.")


if __name__ == "__main__":
    sys.exit(main())
