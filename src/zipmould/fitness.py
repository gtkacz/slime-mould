"""@njit fitness evaluator.

Follows design.md §3.6: coverage + waypoint progress + Manhattan
proximity to next waypoint + success bonus. The progress term is
clipped to its limiting value `beta_2` when `segment >= K` (no next
waypoint to head toward).
"""

from __future__ import annotations

import numba as nb
import numpy as np


@nb.njit(cache=True, fastmath=False)  # type: ignore[misc]
def fitness(
    path_len: int,
    segment: int,
    last_cell: int,
    waypoint_cells: np.ndarray,  # type: ignore[type-arg]
    L: int,  # noqa: N803
    K: int,  # noqa: N803
    N: int,  # noqa: N803
    beta_1: float,
    beta_2: float,
    beta_3: float,
) -> float:
    coverage = float(path_len)
    waypoint_term = beta_1 * float(segment)

    if segment >= K:
        progress = beta_2
    else:
        next_w = int(waypoint_cells[segment])
        last_r = last_cell // N
        last_c = last_cell % N
        nw_r = next_w // N
        nw_c = next_w % N
        d_m = abs(last_r - nw_r) + abs(last_c - nw_c)
        progress = beta_2 / (1.0 + float(d_m))

    success = beta_3 if path_len == L and last_cell == int(waypoint_cells[K - 1]) and segment == K else 0.0

    return coverage + waypoint_term + progress + success
