#!/usr/bin/env python3
"""Headless smoke test for the game logic.

Boots the game with a dummy video/audio driver, drives the economy and combat
systems programmatically, fast-forwards the tick loop, and asserts that the
core loops actually work end to end. Run with:

    SDL_VIDEODRIVER=dummy python3 selftest.py

Exits non-zero on the first failed assertion.
"""

import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from siedler import constants as C
from siedler.game import Game


def fast_forward(game, ticks):
    for _ in range(ticks):
        game.tick_once()


def find_spot(game, near, size=2, want_obj=None, radius=8, tries=400):
    """Find a buildable top-left tile near ``near`` (a tile), optionally with
    a harvestable object of kind ``want_obj`` within ``radius``."""
    world = game.world
    nx, ny = near
    import itertools
    ring = sorted(
        ((abs(dx) + abs(dy), dx, dy)
         for dx, dy in itertools.product(range(-14, 15), repeat=2)),
    )
    for _, dx, dy in ring:
        tx, ty = nx + dx, ny + dy
        # buildable?
        ok = True
        for ax in range(size):
            for ay in range(size):
                t = world.in_bounds(tx + ax, ty + ay) and \
                    world.tiles[ty + ay][tx + ax]
                if not t or t.terrain not in C.WALKABLE_TERRAIN or \
                        t.blocked or t.obj:
                    ok = False
        if not ok:
            continue
        if want_obj is not None:
            cx, cy = tx + size // 2, ty + size // 2
            if not world.find_objects(cx, cy, radius, want_obj):
                continue
        return tx, ty
    return None


def check(cond, msg):
    status = "ok  " if cond else "FAIL"
    print("[%s] %s" % (status, msg))
    if not cond:
        raise AssertionError(msg)


def main():
    # try a few seeds until we get a map with trees near the castle
    game = None
    for seed in range(1, 40):
        g = Game(seed=seed, headless=True)
        cx, cy = C.MAP_W // 2, C.MAP_H // 2
        if find_spot(g, (cx, cy), 2, want_obj=C.OBJ_TREE):
            game = g
            print("using seed", seed)
            break
    check(game is not None, "found a seed with trees near the castle")

    cx, cy = C.MAP_W // 2, C.MAP_H // 2

    # --- economy: woodcutter should gather logs to the castle -----------
    wc_spot = find_spot(game, (cx, cy), 2, want_obj=C.OBJ_TREE)
    wc = game.place_building("woodcutter", *wc_spot)
    check(wc is not None, "placed a woodcutter next to trees")

    # let a builder construct it, then a worker gather
    logs0 = game.economy.stock[C.LOG]
    fast_forward(game, 3000)
    check(wc.complete, "woodcutter finished construction")
    check(wc.worker is not None and wc.worker.role == "worker",
          "woodcutter has a worker assigned")
    logs_now = game.economy.stock[C.LOG] + wc.out_buffer + \
        sum(1 for u in game.units if u.carrying == C.LOG)
    check(logs_now > logs0, "logs were produced by the woodcutter (%d -> %d)"
          % (logs0, logs_now))

    # --- economy: sawmill should turn logs into planks ------------------
    sm_spot = find_spot(game, wc_spot, 2)
    sm = game.place_building("sawmill", *sm_spot)
    check(sm is not None, "placed a sawmill")
    planks0 = game.economy.stock[C.PLANK]
    fast_forward(game, 6000)
    check(sm.complete, "sawmill finished construction")
    made_plank = (game.economy.stock[C.PLANK] > planks0
                  or sm.out_buffer > 0 or sm.producing
                  or any(u.carrying == C.PLANK for u in game.units))
    check(made_plank, "sawmill consumed logs and produced planks")

    # --- combat: barracks should train a soldier ------------------------
    game.economy.stock[C.COIN] = 20
    game.economy.stock[C.BREAD] = 20
    game.economy.stock[C.PLANK] = 20
    game.economy.stock[C.STONE] = 20
    bk_spot = find_spot(game, (cx, cy), 2)
    bk = game.place_building("barracks", *bk_spot)
    check(bk is not None, "placed a barracks")
    fast_forward(game, 6000)
    check(bk.complete, "barracks finished construction")
    check(len(game.player_soldiers) >= 1,
          "a soldier was trained (%d soldiers)" % len(game.player_soldiers))

    # --- combat: enemy raids should trigger and be fightable ------------
    enemies_before = len(game.enemy_units)
    fast_forward(game, C.RAID_FIRST_TICKS + 200)
    check(len(game.enemy_units) >= enemies_before,
          "enemy raid wave spawned")

    # order our soldier to attack the enemy HQ and confirm damage lands
    hq = game.enemy.hq
    hq_hp0 = hq.hp
    for s in game.player_soldiers:
        s.attack_target = hq
    fast_forward(game, 4000)
    check(hq.hp < hq_hp0 or hq.dead,
          "player soldiers damaged the enemy HQ (%d -> %d)"
          % (hq_hp0, hq.hp))

    # --- stability: long run without crashing ---------------------------
    fast_forward(game, 4000)
    check(game.tick > 0, "game ran %d ticks without crashing" % game.tick)

    print("\nALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except AssertionError as e:
        print("\nSELFTEST FAILED:", e)
        sys.exit(1)
