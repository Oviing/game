"""Player economy: the central warehouse (at the castle) plus the transport
job queue that carriers service.

Everything routes through the castle warehouse, Settlers-style: producers
send their output to the warehouse, and consumers pull their inputs from it.
"""

from collections import defaultdict

from . import constants as C


class Job:
    """A single hauling task claimed by one carrier.

    mode 'to_castle': carry one ``resource`` from ``building`` to the castle.
    mode 'to_building': carry one ``resource`` from the castle to ``building``.
    """
    __slots__ = ("mode", "resource", "building")

    def __init__(self, mode, resource, building):
        self.mode = mode
        self.resource = resource
        self.building = building


class Economy:
    def __init__(self):
        self.stock = defaultdict(int)
        self.reserved = defaultdict(int)   # castle stock promised to jobs
        for r, n in C.STARTING_STOCK.items():
            self.stock[r] = n
        self.jobs = []

    # -------------------------------------------------- stock helpers
    def available(self, resource):
        return self.stock[resource] - self.reserved[resource]

    def can_afford(self, cost):
        return all(self.stock[r] >= n for r, n in cost.items())

    def spend(self, cost):
        for r, n in cost.items():
            self.stock[r] -= n

    def add(self, resource, n=1):
        self.stock[resource] += n

    # -------------------------------------------------- job generation
    def generate_jobs(self, buildings):
        """(Re)build the open-job list from current producer/consumer state.

        Reservations already attached to in-flight carriers are respected;
        we only post jobs for goods that are not yet spoken for.
        """
        # Count how much is already promised by open (unclaimed) jobs so we
        # don't post duplicates for the same unit.
        open_to_castle = defaultdict(int)      # building -> count
        open_to_building = defaultdict(lambda: defaultdict(int))
        for j in self.jobs:
            if j.mode == "to_castle":
                open_to_castle[j.building] += 1
            else:
                open_to_building[j.building][j.resource] += 1

        for b in buildings:
            if not b.complete or b.owner != "player":
                continue
            # producer -> castle
            if b.output:
                ready = b.out_buffer - b.out_reserved - open_to_castle[b]
                for _ in range(max(0, ready)):
                    self.jobs.append(Job("to_castle", b.output, b))
            # consumer <- castle
            for res, need_each in b.inputs.items():
                cap = C.INPUT_BUFFER_CAP
                have = b.in_buffer[res] + b.in_incoming[res]
                already = open_to_building[b][res]
                want = cap - have - already
                avail = self.available(res)
                n = max(0, min(want, avail))
                for _ in range(n):
                    self.reserved[res] += 1
                    b.in_incoming[res] += 1
                    self.jobs.append(Job("to_building", res, b))

    def claim_nearest(self, unit_tile, world):
        """Pop and return the open job whose source is closest to unit_tile.

        Source is the castle for delivery jobs, the building for pickups.
        Distance uses cheap Manhattan on tile coords.
        """
        if not self.jobs:
            return None
        best_i = None
        best_d = 1e18
        ux, uy = unit_tile
        for i, j in enumerate(self.jobs):
            if j.mode == "to_castle":
                sx, sy = j.building.access_tile(world)
            else:
                sx, sy = self.castle.access_tile(world)
            d = abs(sx - ux) + abs(sy - uy)
            if d < best_d:
                best_d = d
                best_i = i
        if best_i is None:
            return None
        return self.jobs.pop(best_i)

    def cancel_job(self, job):
        """Return a job's reservations to the pool (carrier gave up)."""
        if job.mode == "to_building":
            self.reserved[job.resource] = max(
                0, self.reserved[job.resource] - 1)
            job.building.in_incoming[job.resource] = max(
                0, job.building.in_incoming[job.resource] - 1)
        # to_castle jobs reserve on the building side (out_reserved), which is
        # only taken when the carrier actually picks up, so nothing to undo.
