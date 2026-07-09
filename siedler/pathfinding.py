"""A* pathfinding over the tile grid with 8-way movement.

Units are small in number so a per-request A* is fine. Paths are lists of
(x, y) tile coordinates from just after the start up to and including the
goal. Diagonal moves are blocked from cutting building/water corners.
"""

import heapq

from . import constants as C

_NEIGHBORS = [(-1, 0), (1, 0), (0, -1), (0, 1),
              (-1, -1), (-1, 1), (1, -1), (1, 1)]


def _heur(ax, ay, bx, by):
    dx = abs(ax - bx)
    dy = abs(ay - by)
    # octile distance
    return (dx + dy) + (1.41421356 - 2) * min(dx, dy)


def find_path(world, start, goal, goal_walkable=True, max_expand=6000):
    """Return a path (list of tiles) from start to goal, or None.

    If ``goal_walkable`` is False the goal tile itself need not be walkable
    (used to path *up to* a building/resource): search stops when adjacent.
    """
    sx, sy = start
    gx, gy = goal
    if (sx, sy) == (gx, gy):
        return []

    def walkable(x, y):
        return world.is_walkable(x, y)

    def is_goal(x, y):
        if goal_walkable:
            return (x, y) == (gx, gy)
        # reached if standing on goal or orthogonally/diagonally adjacent
        return max(abs(x - gx), abs(y - gy)) <= 1

    open_heap = [(0.0, sx, sy)]
    came = {}
    gscore = {(sx, sy): 0.0}
    expanded = 0

    while open_heap:
        _, cx, cy = heapq.heappop(open_heap)
        if is_goal(cx, cy):
            return _reconstruct(came, (cx, cy))
        expanded += 1
        if expanded > max_expand:
            return None
        base = gscore[(cx, cy)]
        for dx, dy in _NEIGHBORS:
            nx, ny = cx + dx, cy + dy
            if not world.in_bounds(nx, ny):
                continue
            target_is_goal = not goal_walkable and (nx, ny) == (gx, gy)
            if not walkable(nx, ny) and not target_is_goal:
                continue
            if dx != 0 and dy != 0:
                # don't cut corners past blocked orthogonal tiles
                if not walkable(cx + dx, cy) or not walkable(cx, cy + dy):
                    continue
            step = 1.41421356 if (dx and dy) else 1.0
            ng = base + step
            if ng < gscore.get((nx, ny), 1e18):
                gscore[(nx, ny)] = ng
                came[(nx, ny)] = (cx, cy)
                f = ng + _heur(nx, ny, gx, gy)
                heapq.heappush(open_heap, (f, nx, ny))
    return None


def _reconstruct(came, node):
    path = [node]
    while node in came:
        node = came[node]
        path.append(node)
    path.reverse()
    return path[1:]  # drop the start tile
