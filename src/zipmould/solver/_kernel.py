"""@njit walker step, walker run, pheromone update, and iteration loop.

The kernel does one step at a time at the lowest level
(`_walker_step`), composes them into a full path (`_walker_run`),
and the iteration loop (`_iterate`) builds a full population, scores
fitness, updates pheromone, applies restart noise, and emits a frame
record into pre-allocated arrays.
"""

from __future__ import annotations

import math

import numba as nb
import numpy as np

from zipmould.fitness import fitness  # noqa: F401  # pyright: ignore[reportUnusedImport]
from zipmould.solver._heuristics import (
    NEG_INF,
    _bit_clear,  # noqa: F401  # pyright: ignore[reportUnusedImport, reportPrivateUsage]
    _bit_set,  # pyright: ignore[reportPrivateUsage]
    _bit_test,  # pyright: ignore[reportPrivateUsage]
    h_articulation,
    h_manhattan,
    h_parity,
    h_warnsdorff,
    softplus,
)


@nb.njit(cache=True)  # type: ignore[misc]
def _walker_step(  # noqa: PLR0912, PLR0915  # pyright: ignore[reportUnusedFunction]
    walker_id: int,
    pos: np.ndarray,  # type: ignore[type-arg]
    visited: np.ndarray,  # type: ignore[type-arg]
    path: np.ndarray,  # type: ignore[type-arg]
    path_len: np.ndarray,  # type: ignore[type-arg]
    segment: np.ndarray,  # type: ignore[type-arg]
    status: np.ndarray,  # type: ignore[type-arg]
    f0_remaining: np.ndarray,  # type: ignore[type-arg]
    f1_remaining: np.ndarray,  # type: ignore[type-arg]
    adjacency: np.ndarray,  # type: ignore[type-arg]
    edge_of: np.ndarray,  # type: ignore[type-arg]
    waypoint_of: np.ndarray,  # type: ignore[type-arg]
    parity_table: np.ndarray,  # type: ignore[type-arg]
    manhattan_table: np.ndarray,  # type: ignore[type-arg]
    waypoint_cells: np.ndarray,  # type: ignore[type-arg]
    tau: np.ndarray,  # type: ignore[type-arg]
    pheromone_mode: int,
    n_stripes: int,
    K: int,  # noqa: N803
    L: int,  # noqa: N803
    N2: int,  # noqa: N803
    alpha: float,
    beta_log: float,
    gamma_man: float,
    gamma_warns: float,
    gamma_art: float,
    gamma_par: float,
    work_stack: np.ndarray,  # type: ignore[type-arg]
) -> None:
    if status[walker_id] != 0:
        return

    cur = int(pos[walker_id])
    seg = int(segment[walker_id])

    logits = np.full(4, -1.0e30, dtype=np.float64)
    legal_count = 0
    for d in range(4):
        nb_cell = adjacency[cur, d]
        if nb_cell < 0:
            continue
        if _bit_test(visited, walker_id, nb_cell):
            continue
        wlabel = waypoint_of[nb_cell]
        if wlabel >= 1 and wlabel != seg + 1:
            continue

        h_m = h_manhattan(nb_cell, seg, K, waypoint_cells, manhattan_table)
        h_w = h_warnsdorff(walker_id, nb_cell, seg, visited, adjacency, waypoint_of)
        plen_after = int(path_len[walker_id]) + 1
        h_a = h_articulation(walker_id, nb_cell, visited, adjacency, N2, plen_after, L, work_stack)
        if h_a == NEG_INF:
            continue
        h_p = h_parity(nb_cell, walker_id, f0_remaining, f1_remaining, parity_table)

        eta = (
            (softplus(h_m) ** gamma_man)
            * (softplus(h_w) ** gamma_warns)
            * (softplus(h_a) ** gamma_art)
            * (softplus(h_p) ** gamma_par)
        )
        if eta <= 0.0:
            eta = 1.0e-12

        eid = edge_of[cur, d]
        stripe = (seg - 1) if pheromone_mode == 1 else 0
        if stripe < 0:  # noqa: PLR1730
            stripe = 0
        if stripe >= n_stripes:
            stripe = n_stripes - 1
        tau_val = float(tau[stripe, eid])

        logits[d] = alpha * tau_val + beta_log * math.log(eta)
        legal_count += 1

    if legal_count == 0:
        status[walker_id] = 1
        return

    max_logit = -1.0e30
    for d in range(4):
        if logits[d] > max_logit:  # noqa: PLR1730
            max_logit = logits[d]
    total = 0.0
    probs = np.zeros(4, dtype=np.float64)
    for d in range(4):
        if logits[d] <= -1.0e29:  # noqa: PLR2004
            probs[d] = 0.0
        else:
            probs[d] = math.exp(logits[d] - max_logit)
            total += probs[d]
    for d in range(4):
        probs[d] /= total

    u = np.random.random()
    acc = 0.0
    chosen = -1
    for d in range(4):
        acc += probs[d]
        if u <= acc and probs[d] > 0.0:
            chosen = d
            break
    if chosen < 0:
        for d in range(4):
            if probs[d] > 0.0:
                chosen = d

    next_cell = int(adjacency[cur, chosen])
    pos[walker_id] = next_cell
    plen = int(path_len[walker_id])
    path[walker_id, plen] = next_cell
    path_len[walker_id] = plen + 1
    _bit_set(visited, walker_id, next_cell)
    if parity_table[next_cell] == 0:
        f0_remaining[walker_id] -= 1
    else:
        f1_remaining[walker_id] -= 1

    wlabel = waypoint_of[next_cell]
    if wlabel >= 1:
        segment[walker_id] = wlabel

    if (
        path_len[walker_id] == L
        and segment[walker_id] == K
        and next_cell == int(waypoint_cells[K - 1])
    ):
        status[walker_id] = 2


@nb.njit(cache=True)  # type: ignore[misc]
def _init_walker(  # pyright: ignore[reportUnusedFunction]
    walker_id: int,
    pos: np.ndarray,  # type: ignore[type-arg]
    visited: np.ndarray,  # type: ignore[type-arg]
    path: np.ndarray,  # type: ignore[type-arg]
    path_len: np.ndarray,  # type: ignore[type-arg]
    segment: np.ndarray,  # type: ignore[type-arg]
    status: np.ndarray,  # type: ignore[type-arg]
    f0_remaining: np.ndarray,  # type: ignore[type-arg]
    f1_remaining: np.ndarray,  # type: ignore[type-arg]
    waypoint_cells: np.ndarray,  # type: ignore[type-arg]
    parity_table: np.ndarray,  # type: ignore[type-arg]
    f0_total: int,
    f1_total: int,
) -> None:
    visited[walker_id, :] = np.uint64(0)
    path_len[walker_id] = 0
    status[walker_id] = 0

    start = int(waypoint_cells[0])
    pos[walker_id] = start
    path[walker_id, 0] = start
    path_len[walker_id] = 1
    _bit_set(visited, walker_id, start)
    segment[walker_id] = 1

    if parity_table[start] == 0:
        f0_remaining[walker_id] = f0_total - 1
        f1_remaining[walker_id] = f1_total
    else:
        f0_remaining[walker_id] = f0_total
        f1_remaining[walker_id] = f1_total - 1


@nb.njit(cache=True)  # type: ignore[misc]
def _walker_run(  # pyright: ignore[reportUnusedFunction]
    walker_id: int,
    pos: np.ndarray,  # type: ignore[type-arg]
    visited: np.ndarray,  # type: ignore[type-arg]
    path: np.ndarray,  # type: ignore[type-arg]
    path_len: np.ndarray,  # type: ignore[type-arg]
    segment: np.ndarray,  # type: ignore[type-arg]
    status: np.ndarray,  # type: ignore[type-arg]
    f0_remaining: np.ndarray,  # type: ignore[type-arg]
    f1_remaining: np.ndarray,  # type: ignore[type-arg]
    adjacency: np.ndarray,  # type: ignore[type-arg]
    edge_of: np.ndarray,  # type: ignore[type-arg]
    waypoint_of: np.ndarray,  # type: ignore[type-arg]
    parity_table: np.ndarray,  # type: ignore[type-arg]
    manhattan_table: np.ndarray,  # type: ignore[type-arg]
    waypoint_cells: np.ndarray,  # type: ignore[type-arg]
    tau: np.ndarray,  # type: ignore[type-arg]
    pheromone_mode: int,
    n_stripes: int,
    K: int,  # noqa: N803
    L: int,  # noqa: N803
    N2: int,  # noqa: N803
    alpha: float,
    beta_log: float,
    gamma_man: float,
    gamma_warns: float,
    gamma_art: float,
    gamma_par: float,
    work_stack: np.ndarray,  # type: ignore[type-arg]
) -> None:
    while status[walker_id] == 0 and int(path_len[walker_id]) < L:
        _walker_step(
            walker_id,
            pos,
            visited,
            path,
            path_len,
            segment,
            status,
            f0_remaining,
            f1_remaining,
            adjacency,
            edge_of,
            waypoint_of,
            parity_table,
            manhattan_table,
            waypoint_cells,
            tau,
            pheromone_mode,
            n_stripes,
            K,
            L,
            N2,
            alpha,
            beta_log,
            gamma_man,
            gamma_warns,
            gamma_art,
            gamma_par,
            work_stack,
        )
    if status[walker_id] == 0 and int(path_len[walker_id]) >= L:
        status[walker_id] = 1
