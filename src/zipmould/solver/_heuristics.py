"""@njit heuristic components per design.md §3.3.

Each component returns a real-valued score; the kernel applies softplus
and gamma exponentiation once at the call site to keep the inner sum
predictable. Articulation returns -inf when removing the candidate
cell would isolate part of the unvisited free subgraph.

Caller contract for h_warnsdorff / h_articulation:
- cell_next MUST NOT be pre-marked in `visited` on entry; both helpers
  set then clear the bit themselves and a pre-existing mark would be
  silently lost on exit.
- work_stack passed to h_articulation MUST have length >= n2 to hold
  the worst-case flood-fill of the entire free subgraph; Numba does
  not bounds-check ndarray writes inside @njit code.
"""

from __future__ import annotations

import math

import numba as nb
import numpy as np

NEG_INF = -1.0e30


@nb.njit(cache=True, inline="always")  # type: ignore[misc]
def _bit_test(visited: np.ndarray, walker_id: int, cell: int) -> bool:  # type: ignore[type-arg]
    word = cell >> 6
    bit = cell & 63
    return (visited[walker_id, word] >> np.uint64(bit)) & np.uint64(1) == np.uint64(1)


@nb.njit(cache=True, inline="always")  # type: ignore[misc]
def _bit_set(visited: np.ndarray, walker_id: int, cell: int) -> None:  # type: ignore[type-arg]
    word = cell >> 6
    bit = cell & 63
    visited[walker_id, word] |= np.uint64(1) << np.uint64(bit)


@nb.njit(cache=True, inline="always")  # type: ignore[misc]
def _bit_clear(visited: np.ndarray, walker_id: int, cell: int) -> None:  # type: ignore[type-arg]
    word = cell >> 6
    bit = cell & 63
    visited[walker_id, word] &= ~(np.uint64(1) << np.uint64(bit))


@nb.njit(cache=True)  # type: ignore[misc]
def softplus(x: float) -> float:
    if x > 30.0:  # noqa: PLR2004
        return x
    if x < -30.0:  # noqa: PLR2004
        return 0.0
    return math.log1p(math.exp(x))


@nb.njit(cache=True)  # type: ignore[misc]
def h_manhattan(
    cell_next: int,
    segment: int,
    K: int,  # noqa: N803
    waypoint_cells: np.ndarray,  # type: ignore[type-arg]
    manhattan_table: np.ndarray,  # type: ignore[type-arg]
) -> float:
    if segment >= K:
        return 0.0
    return -float(manhattan_table[cell_next, segment])


@nb.njit(cache=True)  # type: ignore[misc]
def _onward_count(
    walker_id: int,
    cell_next: int,
    segment: int,
    waypoint_of: np.ndarray,  # type: ignore[type-arg]
    visited: np.ndarray,  # type: ignore[type-arg]
    adjacency: np.ndarray,  # type: ignore[type-arg]
) -> int:
    cnt = 0
    for d in range(4):
        nb_cell = adjacency[cell_next, d]
        if nb_cell < 0:
            continue
        if _bit_test(visited, walker_id, nb_cell):
            continue
        wlabel = waypoint_of[nb_cell]
        if wlabel >= 1 and wlabel != segment + 1:
            continue
        cnt += 1
    return cnt


@nb.njit(cache=True)  # type: ignore[misc]
def h_warnsdorff(
    walker_id: int,
    cell_next: int,
    segment: int,
    visited: np.ndarray,  # type: ignore[type-arg]
    adjacency: np.ndarray,  # type: ignore[type-arg]
    waypoint_of: np.ndarray,  # type: ignore[type-arg]
) -> float:
    _bit_set(visited, walker_id, cell_next)
    cnt = _onward_count(walker_id, cell_next, segment, waypoint_of, visited, adjacency)
    _bit_clear(visited, walker_id, cell_next)
    return -float(cnt)


@nb.njit(cache=True)  # type: ignore[misc]
def h_articulation(
    walker_id: int,
    cell_next: int,
    visited: np.ndarray,  # type: ignore[type-arg]
    adjacency: np.ndarray,  # type: ignore[type-arg]
    n2: int,
    path_len_after: int,
    L: int,  # noqa: N803
    work_stack: np.ndarray,  # type: ignore[type-arg]
) -> float:
    if path_len_after >= L:
        return 0.0

    _bit_set(visited, walker_id, cell_next)
    seed = -1
    for d in range(4):
        nb_cell = adjacency[cell_next, d]
        if nb_cell < 0:
            continue
        if not _bit_test(visited, walker_id, nb_cell):
            seed = nb_cell
            break
    if seed < 0:
        _bit_clear(visited, walker_id, cell_next)
        return NEG_INF

    # BFS over the free subgraph using a queue laid out as work_stack[0:tail].
    # We need an explicit list of every cell we mark so cleanup can clear
    # exactly those cells; a flood-fill cleanup would spill into the walker's
    # pre-existing visited path through cell_next.
    head = 0
    tail = 0
    work_stack[tail] = seed
    tail += 1
    _bit_set(visited, walker_id, seed)

    while head < tail:
        cur = int(work_stack[head])
        head += 1
        for d in range(4):
            nb_cell = adjacency[cur, d]
            if nb_cell < 0:
                continue
            if _bit_test(visited, walker_id, nb_cell):
                continue
            _bit_set(visited, walker_id, nb_cell)
            work_stack[tail] = nb_cell
            tail += 1

    reached = tail

    for i in range(tail):
        _bit_clear(visited, walker_id, int(work_stack[i]))

    _bit_clear(visited, walker_id, cell_next)

    expected = L - path_len_after
    if reached == expected:
        return 0.0
    return NEG_INF


@nb.njit(cache=True)  # type: ignore[misc]
def h_parity(
    cell_next: int,
    walker_id: int,
    f0_remaining: np.ndarray,  # type: ignore[type-arg]
    f1_remaining: np.ndarray,  # type: ignore[type-arg]
    parity_table: np.ndarray,  # type: ignore[type-arg]
) -> float:
    p = parity_table[cell_next]
    if p == 0:
        f0r = f0_remaining[walker_id] - 1
        f1r = f1_remaining[walker_id]
    else:
        f0r = f0_remaining[walker_id]
        f1r = f1_remaining[walker_id] - 1
    diff = f0r - f1r
    if diff < 0:
        diff = -diff
    if diff <= 1:
        return 0.1
    return -0.1
