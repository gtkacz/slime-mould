"""Feasibility prechecks per docs/design.md §3.9.

These are necessary-but-not-sufficient: passing them does not guarantee
a Hamiltonian path exists, but failing them proves no algorithm can
solve the puzzle. Cheap O(N²) work, run once per puzzle before the
solver loop starts.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Literal

from zipmould.puzzle import Coord, Edge, Puzzle

FeasibilityFailure = Literal[
    "waypoint_blocked",
    "waypoint_unreachable",
    "free_subgraph_disconnected",
    "parity_imbalance",
    "endpoint_parity_mismatch",
]


@dataclass(frozen=True, slots=True)
class FeasibilityReport:
    feasible: bool
    reason: FeasibilityFailure | None
    f0_count: int
    f1_count: int
    reachable_count: int


def _adjacent(
    c: Coord,
    n: int,
    walls: frozenset[Edge],
    blocked: frozenset[Coord],
) -> list[Coord]:
    r, col = c
    out: list[Coord] = []
    for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        nr, nc = r + dr, col + dc
        if not (0 <= nr < n and 0 <= nc < n):
            continue
        nb: Coord = (nr, nc)
        if nb in blocked:
            continue
        edge: Edge = (c, nb) if c <= nb else (nb, c)
        if edge in walls:
            continue
        out.append(nb)
    return out


def precheck(puzzle: Puzzle) -> FeasibilityReport:
    free = puzzle.free_cells()

    for w in puzzle.waypoints:
        if w not in free:
            return FeasibilityReport(False, "waypoint_blocked", 0, 0, 0)

    f0 = sum(1 for (r, c) in free if (r + c) % 2 == 0)
    f1 = len(free) - f0

    start = puzzle.waypoints[0]
    seen: set[Coord] = {start}
    queue: deque[Coord] = deque([start])
    while queue:
        cur = queue.popleft()
        for nb in _adjacent(cur, puzzle.N, puzzle.walls, puzzle.blocked):
            if nb not in seen:
                seen.add(nb)
                queue.append(nb)

    reach_count = len(seen)

    for w in puzzle.waypoints[1:]:
        if w not in seen:
            return FeasibilityReport(False, "waypoint_unreachable", f0, f1, reach_count)

    if frozenset(seen) != free:
        return FeasibilityReport(False, "free_subgraph_disconnected", f0, f1, reach_count)

    if abs(f0 - f1) > 1:
        return FeasibilityReport(False, "parity_imbalance", f0, f1, reach_count)

    w1 = puzzle.waypoints[0]
    wk = puzzle.waypoints[-1]
    w1_parity = (w1[0] + w1[1]) % 2
    wk_parity = (wk[0] + wk[1]) % 2

    if f0 != f1:
        larger_parity = 0 if f0 > f1 else 1
        endpoint_mismatch = w1_parity != larger_parity or wk_parity != larger_parity
    else:
        endpoint_mismatch = w1_parity == wk_parity

    if endpoint_mismatch:
        return FeasibilityReport(False, "endpoint_parity_mismatch", f0, f1, reach_count)

    return FeasibilityReport(True, None, f0, f1, reach_count)
