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

    # --- recruitment: barracks + queue each troop type ------------------
    for r in (C.COIN, C.BREAD, C.PLANK, C.STONE):
        game.economy.stock[r] = 40
    bk_spot = find_spot(game, (cx, cy), 2)
    bk = game.place_building("barracks", *bk_spot)
    check(bk is not None, "placed a barracks")
    fast_forward(game, 4000)
    check(bk.complete, "barracks finished construction")

    for troop in C.PLAYER_TROOPS:
        before = game.economy.stock[C.COIN]
        ok = game.queue_recruit(bk, troop)
        check(ok, "queued a %s" % troop)
        check(game.economy.stock[C.COIN] < before,
              "queuing %s spent credits" % troop)
    have_types = set()
    for _ in range(8000):
        game.tick_once()
        for u in game.player_soldiers:
            have_types.add(u.troop)
        if {"marine", "ranger", "heavy"} <= have_types:
            break
    check({"marine", "ranger", "heavy"} <= have_types,
          "recruited all three troop types (%s)" % sorted(have_types))

    # --- ranged combat: a ranger damages from range without closing -----
    ranger = next(u for u in game.player_soldiers if u.troop == "ranger")
    check(ranger.ranged, "ranger is a ranged unit (range %.1f)" % ranger.range)
    dummy = game.enemy.hq
    hp0 = dummy.hp
    # park the ranger ~4 tiles from the hive edge and lock target
    ex, ey = game.enemy.center
    ranger.x, ranger.y = float(ex + 4), float(ey)
    ranger.attack_target = dummy
    ranger.move_goal = None
    fast_forward(game, 300)
    d_after = ((ranger.x - ex) ** 2 + (ranger.y - ey) ** 2) ** 0.5
    check(dummy.hp < hp0, "ranger damaged the hive from range")
    check(d_after > 2.5, "ranger stayed at range (did not melee-rush)")

    # --- enemy: scouts trigger an early reactive raid -------------------
    g2 = Game(seed=3, headless=True)
    check(len(g2.enemy.scouts) >= 1, "enemy hive fields scouts")
    spy = g2.spawn_soldier(g2.enemy.hq, "marine")  # a decoy to be spotted
    spy.max_hp = spy.hp = 1_000_000              # survive the test window
    raids_before = g2.enemy.raid_num
    reacted = False
    for _ in range(8 * C.TICKS_PER_SECOND):
        if g2.enemy.scouts:                       # glue the decoy to a scout
            s0 = g2.enemy.scouts[0]
            spy.x, spy.y = s0.x + 0.5, s0.y
            spy.attack_target = None
            spy.move_goal = None
        g2.tick_once()
        if g2.enemy.raid_num > raids_before:
            reacted = True
            break
    check(reacted, "enemy scout detection triggered an early raid")

    # --- combat: a squad razes the hive to win --------------------------
    hq = game.enemy.hq
    ex, ey = game.enemy.center
    squad = [game.spawn_soldier(bk, "heavy") for _ in range(4)]
    hq_hp0 = hq.hp
    for k, sdr in enumerate(squad):
        sdr.max_hp = sdr.hp = 1_000_000     # durable enough to finish the test
        sdr.x, sdr.y = float(ex + 3 + k), float(ey + 3)
        sdr.attack_target = hq
    fast_forward(game, 1600)
    check(hq.hp < hq_hp0 or hq.dead,
          "player squad razed the alien hive (%d -> %d)" % (hq_hp0, hq.hp))
    check(game.result == "win" or hq.dead,
          "destroying the hive wins the game")

    # --- stability: long run without crashing ---------------------------
    fast_forward(game, 3000)
    check(game.tick > 0, "game ran %d ticks without crashing" % game.tick)

    print("\nALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except AssertionError as e:
        print("\nSELFTEST FAILED:", e)
        sys.exit(1)
