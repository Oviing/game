"""Loads sprite PNGs from assets/ and exposes them as pygame Surfaces.

If a PNG is missing (e.g. the repo was checked out without running the
generator), we fall back to a labelled placeholder so the game still runs.
Call load() once after pygame.display is initialised.
"""

import os

import pygame

from . import constants as C

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSET_DIR = os.path.join(ROOT, "assets")

# name -> Surface, populated by load()
images = {}


def _placeholder(size=(32, 32), color=(200, 40, 200)):
    surf = pygame.Surface(size, pygame.SRCALPHA)
    surf.fill((*color, 255))
    pygame.draw.rect(surf, (0, 0, 0), surf.get_rect(), 1)
    return surf


def _load_one(key, relpath, required_size=None):
    path = os.path.join(ASSET_DIR, relpath)
    try:
        surf = pygame.image.load(path).convert_alpha()
    except (pygame.error, FileNotFoundError):
        surf = _placeholder(required_size or (32, 32))
    images[key] = surf
    return surf


def load():
    """Populate the module-level ``images`` dict. Idempotent."""
    if images:
        return images

    tiles = {
        "grass": "tiles/grass.png",
        "grass2": "tiles/grass2.png",
        "water": "tiles/water.png",
        "sand": "tiles/sand.png",
        "rock": "tiles/rock.png",
        "gold": "tiles/gold.png",
        "tree": "tiles/tree.png",
        "stump": "tiles/stump.png",
        "stone_deposit": "tiles/stone_deposit.png",
    }
    for key, rel in tiles.items():
        _load_one(key, rel)

    building_files = {
        "castle": "buildings/castle.png",
        "enemy_hq": "buildings/enemy_hq.png",
        "woodcutter": "buildings/woodcutter.png",
        "sawmill": "buildings/sawmill.png",
        "stonecutter": "buildings/stonecutter.png",
        "farm": "buildings/farm.png",
        "mill": "buildings/mill.png",
        "bakery": "buildings/bakery.png",
        "goldmine": "buildings/goldmine.png",
        "mint": "buildings/mint.png",
        "barracks": "buildings/barracks.png",
        "tower": "buildings/tower.png",
        "enemy_tower": "buildings/enemy_tower.png",
        "site": "buildings/site.png",
    }
    for key, rel in building_files.items():
        _load_one("b_" + key, rel)

    unit_files = {
        "colonist": "units/colonist.png",
        "builder": "units/builder.png",
        "worker": "units/worker.png",
        # player troops
        "marine": "units/marine.png",
        "ranger": "units/ranger.png",
        "heavy": "units/heavy.png",
        # enemy troops
        "alien": "units/alien.png",
        "spitter": "units/spitter.png",
        "scout": "units/scout.png",
    }
    for key, rel in unit_files.items():
        _load_one("u_" + key, rel)

    icon_files = {
        C.LOG: "ui/icon_log.png",
        C.PLANK: "ui/icon_plank.png",
        C.STONE: "ui/icon_stone.png",
        C.GRAIN: "ui/icon_grain.png",
        C.FLOUR: "ui/icon_flour.png",
        C.BREAD: "ui/icon_bread.png",
        C.ORE: "ui/icon_ore.png",
        C.COIN: "ui/icon_coin.png",
        "pop": "ui/icon_pop.png",
        "sword": "ui/icon_sword.png",
    }
    for key, rel in icon_files.items():
        _load_one("i_" + key, rel)

    return images


def tile(name):
    return images["grass" if name not in images else name]


def building_img(kind):
    return images.get("b_" + kind, images.get("b_woodcutter"))


def unit_img(name):
    return images.get("u_" + name, images.get("u_colonist"))


def icon(name):
    return images.get("i_" + name)
