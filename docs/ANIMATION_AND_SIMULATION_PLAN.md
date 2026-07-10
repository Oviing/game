# A-Class Upgrade Plan — Animation & Game-Logic Simulation

Goal: raise **Astro Settlers** from "functional" to **A-class** polish — fluid
sprite animation, a real effects/particle layer, projectile-based combat, and a
robust simulation core (decoupled fixed-step sim with render interpolation, unit
steering/avoidance, formations). Constraint preserved: **pure pygame, all art
generated in-repo, no external assets.**

## Context — what exists today

- **Loop:** fixed 60 Hz logic via `Game.tick_once()`, speed scaling through a
  time accumulator (`game.py`).
- **Units:** single static frame per role; positions slide linearly between
  tiles; facing = horizontal flip only (`units.py`, `game.py:_draw_unit`).
- **Combat:** instant damage; ranged draws a one-frame line (`add_shot`); the
  only "effect" is a building damage flash.
- **No** walk cycles, attack/death animations, particles, projectiles, or
  render/sim decoupling.

## Design pillars

1. **Decoupled simulation & rendering (interpolation).** Sim advances in fixed
   ticks; the renderer draws at the monitor's rate and **interpolates** each
   entity between its previous and current tick position (`alpha` in [0,1]).
   Result: buttery motion independent of sim rate or the 1×/2×/3× multiplier.
2. **Data-driven animation.** Sprite *sheets* (rows = state, cols = frames); an
   `Animator` advances frames by dt with per-state fps/loop; entity state
   (idle / walk / work / attack / hit / die) selects the row. 4- or 8-direction
   facing.
3. **Effects & particles.** A pooled particle system: footstep dust, muzzle
   flash, impact sparks, explosions, smelter smoke, build dust, resource "pop"
   icons, floating damage numbers.
4. **Projectile combat.** Ranged attacks spawn a *traveling* projectile (plasma
   bolt) with speed + target lead and an impact effect; melee gets a lunge +
   hit-flash + short attack frames; deaths play a death animation, then leave a
   fading corpse/wreck.
5. **Local steering / avoidance.** Boids-style *separation* so units stop
   stacking, *arrival* slowing near the goal, and simple **formations** for
   group move orders. A uniform-grid **spatial hash** makes neighbor and target
   queries cheap.
6. **Feedback polish.** Camera easing, animated selection rings, move-order
   ping, tweened health bars, animated building "working" glow/parts,
   construction rise, optional ambient day-tint, and SFX hooks.

## Architecture changes

New modules:
- `siedler/anim.py` — `SpriteSheet`, `Animator`, and an `ANIMATIONS` table
  (frame counts, fps, loop flags, per-state row indices).
- `siedler/effects.py` — `Particle`, `ParticleSystem`, `FloatingText`,
  `Projectile` + a registry updated/drawn each frame (render-only).
- `siedler/spatial.py` — uniform grid hash for O(1)-ish neighbor queries; reused
  by steering *and* target acquisition (replaces the current O(n) scans in
  `units.py:_acquire_target`).

Changed modules:
- `game.py` — split `update()` into fixed-step `simulate()` and a
  variable-rate `render(alpha)`; store `prev_x/prev_y` on entities each tick and
  interpolate; own the `ParticleSystem` + projectile list; formalize **render
  layers** (ground → decals/shadows → y-sorted entities → effects → HUD).
- `units.py` — add prev-pos; the state machine emits **animation states** and
  **events** (`on_fire`, `on_hit`, `on_death`); integrate steering; add attack
  wind-up/recover timing that drives the attack animation; ranged attacks spawn
  a projectile instead of applying instant damage.
- `buildings.py` — working-state animation timers; emit smoke/glow while
  producing; construction "rise" reveal; resource-pop effect on output.
- `tools/generate_assets.py` — emit multi-frame **sheets**: walk cycles (per
  direction), work/attack/die frames, building animation frames (smelter glow,
  rig drill bob, dome lights), projectile + particle textures, and soft
  **shadow** blobs. Frames drawn parametrically to keep the generator compact.
- `constants.py` — `SIM_HZ`, animation/particle tuning, projectile stats,
  steering weights, formation spacing.

## Phasing (each phase is independently shippable)

- **Phase 1 — Simulation core.** Decouple sim/render + interpolation; y-sorted
  layered renderer; entity shadows. Biggest smoothness win, minimal new art.
- **Phase 2 — Unit animation.** Walk/idle sheets + `Animator` + 4/8-dir facing;
  footstep dust.
- **Phase 3 — Combat feel.** Projectiles, muzzle/impact particles, hit flash,
  attack + death animations, floating damage numbers.
- **Phase 4 — Steering & formations.** Separation + arrival, spatial hash, group
  formations, target-query speedup.
- **Phase 5 — Building life.** Working animations, smoke/glow, construction
  rise, resource pops.
- **Phase 6 — Polish & audio.** Camera easing, selection/command feedback, HUD
  tweens, optional procedural SFX, ambient tint.

## Verification

Headless (extend `selftest.py`):
- **Interpolation:** `alpha` stays in [0,1]; a teleport (spawn / path reset)
  snaps `prev=curr` (no streak) — assert no interpolated position lies far
  outside the segment.
- **Projectiles:** a ranged attack applies damage **on impact after travel**,
  not instantly (target HP unchanged for the first few frames, then drops).
- **Death flow:** a killed unit enters the `die` state, plays out, then is
  culled.
- **Steering:** after a group move, no two units permanently occupy the same
  tile (no overlap/deadlock); all reach near their formation slots.
- **Determinism:** identical seed + fixed step ⇒ identical state hash after N
  ticks, and the 1×/2×/3× multiplier does **not** change outcomes (particles &
  interpolation must never feed back into the sim).

Visual:
- Capture N sequential frames → assemble a GIF / contact strip and inspect walk
  cycles, projectile arcs, explosions, and smelter smoke.

Performance:
- Log frame time with ~200 units + active particles; confirm the spatial hash
  keeps neighbor/target queries cheap (compare against the current linear scan).

## Risks & constraints

- **All art stays procedural** — multi-frame sheets grow the generator; mitigate
  with parametric per-frame drawing helpers.
- **Interpolation vs. teleports** — always reset `prev` on spawn/path-reset to
  avoid smear.
- **Determinism** — keep the sim tick-based and integer-friendly; particles,
  projectile *visuals*, interpolation, and camera easing are **render-only** and
  never mutate sim state (projectile *damage* resolves in the sim on impact).
