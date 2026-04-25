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

from zipmould.fitness import fitness
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

    if path_len[walker_id] == L and segment[walker_id] == K and next_cell == int(waypoint_cells[K - 1]):
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


@nb.njit(cache=True)  # type: ignore[misc]
def _argsort_desc(values: np.ndarray) -> np.ndarray:  # type: ignore[type-arg]  # pyright: ignore[reportUnusedFunction]
    n = values.shape[0]
    idx = np.empty(n, dtype=np.int32)
    for i in range(n):
        idx[i] = i
    for i in range(1, n):
        key = idx[i]
        kv = values[key]
        j = i - 1
        while j >= 0 and values[idx[j]] < kv:
            idx[j + 1] = idx[j]
            j -= 1
        idx[j + 1] = key
    return idx


@nb.njit(cache=True)  # type: ignore[misc]
def _segment_at_step(  # pyright: ignore[reportUnusedFunction]
    walker_id: int,
    step: int,
    path: np.ndarray,  # type: ignore[type-arg]
    waypoint_of: np.ndarray,  # type: ignore[type-arg]
    K: int,  # noqa: N803
) -> int:
    seg = 1
    for s in range(step + 1):
        cell = int(path[walker_id, s])
        wlabel = waypoint_of[cell]
        if wlabel >= 1 and wlabel <= K:
            seg = wlabel
    return seg


@nb.njit(cache=True)  # type: ignore[misc]
def _pheromone_update(  # noqa: PLR0912  # pyright: ignore[reportUnusedFunction]
    tau: np.ndarray,  # type: ignore[type-arg]
    walker_fitness: np.ndarray,  # type: ignore[type-arg]
    path: np.ndarray,  # type: ignore[type-arg]
    path_len: np.ndarray,  # type: ignore[type-arg]
    edge_of: np.ndarray,  # type: ignore[type-arg]
    waypoint_of: np.ndarray,  # type: ignore[type-arg]
    adjacency: np.ndarray,  # type: ignore[type-arg]
    n_walkers: int,
    n_stripes: int,
    pheromone_mode: int,
    K: int,  # noqa: N803
    t: int,
    T: int,  # noqa: N803
    z: float,
    tau_max: float,
    tau_clip_min: float,
) -> None:
    progress = float(t) / float(T)
    v_b = math.tanh(1.0 - progress)
    v_c = 1.0 - progress

    n = n_walkers
    rank = _argsort_desc(walker_fitness)
    weights = np.zeros(n, dtype=np.float64)
    if n > 1:
        denom = float(n - 1)
        for i in range(n):
            r = -1
            for j in range(n):
                if rank[j] == i:
                    r = j + 1
                    break
            weights[i] = (float(n) - 2.0 * float(r) + 1.0) / denom
    else:
        weights[0] = 1.0

    n_stripes_actual = tau.shape[0]
    n_edges = tau.shape[1]
    deposit = np.zeros((n_stripes_actual, n_edges), dtype=np.float64)

    for w in range(n):
        plen = int(path_len[w])
        if plen <= 1:
            continue
        prev_cell = int(path[w, 0])
        seg_now = 1
        wlabel0 = waypoint_of[prev_cell]
        if wlabel0 >= 1:
            seg_now = wlabel0
        for s in range(1, plen):
            cur_cell = int(path[w, s])
            eid = -1
            for d in range(4):
                if int(adjacency[prev_cell, d]) == cur_cell:
                    eid = int(edge_of[prev_cell, d])
                    break
            if eid >= 0:
                stripe = (seg_now - 1) if pheromone_mode == 1 else 0
                if stripe < 0:  # noqa: PLR1730
                    stripe = 0
                if stripe >= n_stripes_actual:
                    stripe = n_stripes_actual - 1
                deposit[stripe, eid] += weights[w]
            wlabel = waypoint_of[cur_cell]
            if wlabel >= 1:
                seg_now = wlabel
            prev_cell = cur_cell

    for s in range(n_stripes_actual):
        for e in range(n_edges):
            new_val = v_c * float(tau[s, e]) + v_b * deposit[s, e]
            if z > 0.0 and np.random.random() < z:
                new_val = np.random.normal(0.0, tau_max / 4.0)
            if new_val > tau_max:  # noqa: PLR1730
                new_val = tau_max
            if new_val < tau_clip_min:  # noqa: PLR1730
                new_val = tau_clip_min
            tau[s, e] = new_val


@nb.njit(cache=True)  # type: ignore[misc]
def _run_iteration(  # pyright: ignore[reportUnusedFunction]
    pos: np.ndarray,  # type: ignore[type-arg]
    visited: np.ndarray,  # type: ignore[type-arg]
    path: np.ndarray,  # type: ignore[type-arg]
    path_len: np.ndarray,  # type: ignore[type-arg]
    segment: np.ndarray,  # type: ignore[type-arg]
    status: np.ndarray,  # type: ignore[type-arg]
    f0_remaining: np.ndarray,  # type: ignore[type-arg]
    f1_remaining: np.ndarray,  # type: ignore[type-arg]
    walker_fitness: np.ndarray,  # type: ignore[type-arg]
    adjacency: np.ndarray,  # type: ignore[type-arg]
    edge_of: np.ndarray,  # type: ignore[type-arg]
    waypoint_of: np.ndarray,  # type: ignore[type-arg]
    parity_table: np.ndarray,  # type: ignore[type-arg]
    manhattan_table: np.ndarray,  # type: ignore[type-arg]
    waypoint_cells: np.ndarray,  # type: ignore[type-arg]
    tau: np.ndarray,  # type: ignore[type-arg]
    pheromone_mode: int,
    n_walkers: int,
    n_stripes: int,
    K: int,  # noqa: N803
    L: int,  # noqa: N803
    N2: int,  # noqa: N803
    N: int,  # noqa: N803
    alpha: float,
    beta_log: float,
    gamma_man: float,
    gamma_warns: float,
    gamma_art: float,
    gamma_par: float,
    beta1: float,
    beta2: float,
    beta3: float,
    f0_total: int,
    f1_total: int,
    work_stack: np.ndarray,  # type: ignore[type-arg]
    t: int,
    T: int,  # noqa: N803
    z: float,
    tau_max: float,
    tau_clip_min: float,
    freeze_pheromone: int,
) -> int:
    for w in range(n_walkers):
        _init_walker(
            w,
            pos,
            visited,
            path,
            path_len,
            segment,
            status,
            f0_remaining,
            f1_remaining,
            waypoint_cells,
            parity_table,
            f0_total,
            f1_total,
        )
        _walker_run(
            w,
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

    for w in range(n_walkers):
        plen = int(path_len[w])
        last_cell = int(path[w, plen - 1]) if plen > 0 else int(waypoint_cells[0])
        f = fitness(plen, int(segment[w]), last_cell, waypoint_cells, L, K, N, beta1, beta2, beta3)
        walker_fitness[w] = f

    solved_walker = -1
    for w in range(n_walkers):
        if status[w] == 2:  # noqa: PLR2004
            solved_walker = w
            break

    if freeze_pheromone == 0:
        _pheromone_update(
            tau,
            walker_fitness,
            path,
            path_len,
            edge_of,
            waypoint_of,
            adjacency,
            n_walkers,
            n_stripes,
            pheromone_mode,
            K,
            t,
            T,
            z,
            tau_max,
            tau_clip_min,
        )

    if solved_walker >= 0:
        return solved_walker
    return -1


@nb.njit(cache=True)  # type: ignore[misc]
def _seed_kernel(seed: int) -> None:  # pyright: ignore[reportUnusedFunction]
    np.random.seed(seed)


@nb.njit(cache=True)  # type: ignore[misc]
def _diff_tau(  # pyright: ignore[reportUnusedFunction]
    prev: np.ndarray,  # type: ignore[type-arg]
    cur: np.ndarray,  # type: ignore[type-arg]
    eps: float,
    scratch: np.ndarray,  # type: ignore[type-arg]
) -> int:
    n_stripes = cur.shape[0]
    n_edges = cur.shape[1]
    cnt = 0
    for s in range(n_stripes):
        for e in range(n_edges):
            d = float(cur[s, e]) - float(prev[s, e])
            if d > eps or d < -eps:
                scratch[cnt, 0] = e
                scratch[cnt, 1] = s
                scratch[cnt, 2] = d
                cnt += 1
    return cnt


@nb.njit(cache=True)  # type: ignore[misc]
def _kernel_run(  # noqa: PLR0912  # pyright: ignore[reportUnusedFunction]
    pos: np.ndarray,  # type: ignore[type-arg]
    visited: np.ndarray,  # type: ignore[type-arg]
    path: np.ndarray,  # type: ignore[type-arg]
    path_len: np.ndarray,  # type: ignore[type-arg]
    segment: np.ndarray,  # type: ignore[type-arg]
    status: np.ndarray,  # type: ignore[type-arg]
    f0_remaining: np.ndarray,  # type: ignore[type-arg]
    f1_remaining: np.ndarray,  # type: ignore[type-arg]
    walker_fitness: np.ndarray,  # type: ignore[type-arg]
    adjacency: np.ndarray,  # type: ignore[type-arg]
    edge_of: np.ndarray,  # type: ignore[type-arg]
    waypoint_of: np.ndarray,  # type: ignore[type-arg]
    parity_table: np.ndarray,  # type: ignore[type-arg]
    manhattan_table: np.ndarray,  # type: ignore[type-arg]
    waypoint_cells: np.ndarray,  # type: ignore[type-arg]
    tau: np.ndarray,  # type: ignore[type-arg]
    pheromone_mode: int,
    n_walkers: int,
    n_stripes: int,
    K: int,  # noqa: N803
    L: int,  # noqa: N803
    N2: int,  # noqa: N803
    N: int,  # noqa: N803
    alpha: float,
    beta_log: float,
    gamma_man: float,
    gamma_warns: float,
    gamma_art: float,
    gamma_par: float,
    beta1: float,
    beta2: float,
    beta3: float,
    f0_total: int,
    f1_total: int,
    work_stack: np.ndarray,  # type: ignore[type-arg]
    iter_cap: int,
    z: float,
    tau_max: float,
    tau_clip_min: float,
    freeze_pheromone: int,
    seed: int,
    frame_interval: int,
    visible_walkers: int,
    tau_delta_epsilon: float,
    frame_t: np.ndarray,  # type: ignore[type-arg]
    frame_v_b: np.ndarray,  # type: ignore[type-arg]
    frame_v_c: np.ndarray,  # type: ignore[type-arg]
    frame_best_w: np.ndarray,  # type: ignore[type-arg]
    frame_best_fitness: np.ndarray,  # type: ignore[type-arg]
    frame_walker_ids: np.ndarray,  # type: ignore[type-arg]
    frame_walker_cells: np.ndarray,  # type: ignore[type-arg]
    frame_walker_segments: np.ndarray,  # type: ignore[type-arg]
    frame_walker_status: np.ndarray,  # type: ignore[type-arg]
    frame_walker_fitness: np.ndarray,  # type: ignore[type-arg]
    frame_tau_count: np.ndarray,  # type: ignore[type-arg]
    frame_tau_payload: np.ndarray,  # type: ignore[type-arg]
    tau_prev: np.ndarray,  # type: ignore[type-arg]
    tau_scratch: np.ndarray,  # type: ignore[type-arg]
) -> int:
    _seed_kernel(seed)
    solved_iter = -1
    n_frames = 0

    for s in range(n_stripes):
        for e in range(tau_prev.shape[1]):
            tau_prev[s, e] = 0.0

    for t in range(iter_cap):
        res = _run_iteration(
            pos,
            visited,
            path,
            path_len,
            segment,
            status,
            f0_remaining,
            f1_remaining,
            walker_fitness,
            adjacency,
            edge_of,
            waypoint_of,
            parity_table,
            manhattan_table,
            waypoint_cells,
            tau,
            pheromone_mode,
            n_walkers,
            n_stripes,
            K,
            L,
            N2,
            N,
            alpha,
            beta_log,
            gamma_man,
            gamma_warns,
            gamma_art,
            gamma_par,
            beta1,
            beta2,
            beta3,
            f0_total,
            f1_total,
            work_stack,
            t,
            iter_cap,
            z,
            tau_max,
            tau_clip_min,
            freeze_pheromone,
        )

        if (t % frame_interval) == 0 or res >= 0:
            best_w = 0
            best_f = walker_fitness[0]
            for w in range(1, n_walkers):
                if walker_fitness[w] > best_f:
                    best_f = walker_fitness[w]
                    best_w = w
            progress = float(t) / float(iter_cap)
            frame_t[n_frames] = t
            frame_v_b[n_frames] = math.tanh(1.0 - progress)
            frame_v_c[n_frames] = 1.0 - progress
            frame_best_w[n_frames] = best_w
            frame_best_fitness[n_frames] = best_f
            for k in range(visible_walkers):
                if k < n_walkers:
                    cell = int(path[k, max(int(path_len[k]) - 1, 0)])
                    frame_walker_ids[n_frames, k] = k
                    frame_walker_cells[n_frames, k] = cell
                    frame_walker_segments[n_frames, k] = int(segment[k])
                    frame_walker_status[n_frames, k] = int(status[k])
                    frame_walker_fitness[n_frames, k] = walker_fitness[k]
                else:
                    frame_walker_ids[n_frames, k] = -1
            cnt = _diff_tau(tau_prev, tau, tau_delta_epsilon, tau_scratch)
            frame_tau_count[n_frames] = cnt
            for i in range(cnt):
                frame_tau_payload[n_frames, i, 0] = tau_scratch[i, 0]
                frame_tau_payload[n_frames, i, 1] = tau_scratch[i, 1]
                frame_tau_payload[n_frames, i, 2] = tau_scratch[i, 2]
            for s in range(n_stripes):
                for e in range(tau.shape[1]):
                    tau_prev[s, e] = tau[s, e]
            n_frames += 1

        if res >= 0:
            solved_iter = t
            break

    return n_frames if solved_iter < 0 else (n_frames | (1 << 30))
