"""Kernel state and packing/unpacking — the only meeting point of the
outer Pydantic/dataclass layer and the @njit array kernel.

`pack(puzzle, config)` resolves the string sentinels `"N_squared"` and
`"10_N_squared"` from `SolverConfig` into floats using the puzzle's
`N`, then precomputes the Manhattan / parity / adjacency / waypoint
tables once per run.
"""

from __future__ import annotations

from typing import NamedTuple

import numpy as np

from zipmould.config import SolverConfig
from zipmould.puzzle import Coord, Puzzle


class KernelState(NamedTuple):
    L: int
    N: int
    N2: int
    K: int
    E: int
    n_walkers: int
    n_stripes: int
    pheromone_mode: int
    tau_signed: int

    alpha: float
    beta: float
    beta1: float
    beta2: float
    beta3: float
    gamma_man: float
    gamma_warns: float
    gamma_art: float
    gamma_par: float
    tau_max: float
    tau_clip_min: float
    tau_0: float
    z: float

    iter_cap: int
    visible_walkers: int
    frame_interval: int
    tau_delta_epsilon: float

    tau: np.ndarray  # type: ignore[type-arg]
    pos: np.ndarray  # type: ignore[type-arg]
    visited: np.ndarray  # type: ignore[type-arg]
    path: np.ndarray  # type: ignore[type-arg]
    path_len: np.ndarray  # type: ignore[type-arg]
    segment: np.ndarray  # type: ignore[type-arg]
    status: np.ndarray  # type: ignore[type-arg]
    f0_remaining: np.ndarray  # type: ignore[type-arg]
    f1_remaining: np.ndarray  # type: ignore[type-arg]
    walker_fitness: np.ndarray  # type: ignore[type-arg]

    manhattan_table: np.ndarray  # type: ignore[type-arg]
    parity_table: np.ndarray  # type: ignore[type-arg]
    adjacency: np.ndarray  # type: ignore[type-arg]
    adjacency_count: np.ndarray  # type: ignore[type-arg]
    edge_of: np.ndarray  # type: ignore[type-arg]
    edge_endpoints: np.ndarray  # type: ignore[type-arg]
    waypoint_cells: np.ndarray  # type: ignore[type-arg]
    waypoint_of: np.ndarray  # type: ignore[type-arg]
    f0_total: int
    f1_total: int


def _resolve_beta1(value: float | str, n: int) -> float:
    return float(n * n) if value == "N_squared" else float(value)


def _resolve_beta3(value: float | str, n: int) -> float:
    return 10.0 * float(n * n) if value == "10_N_squared" else float(value)


def _build_adjacency(puzzle: Puzzle) -> tuple[np.ndarray, np.ndarray, np.ndarray, int]:  # type: ignore[type-arg]
    n = puzzle.N
    n2 = n * n
    adj = np.full((n2, 4), -1, dtype=np.int16)
    edge_of = np.full((n2, 4), -1, dtype=np.int32)
    edges_seen: dict[tuple[int, int], int] = {}
    deltas = ((-1, 0), (1, 0), (0, -1), (0, 1))

    for r in range(n):
        for c in range(n):
            here = r * n + c
            if (r, c) in puzzle.blocked:
                continue
            for dir_idx, (dr, dc) in enumerate(deltas):
                nr, nc = r + dr, c + dc
                if not (0 <= nr < n and 0 <= nc < n):
                    continue
                nb = (nr, nc)
                if nb in puzzle.blocked:
                    continue
                a, b = ((r, c), nb) if (r, c) <= nb else (nb, (r, c))
                if (a, b) in puzzle.walls:
                    continue
                nb_idx = nr * n + nc
                adj[here, dir_idx] = nb_idx
                key = (here, nb_idx) if here < nb_idx else (nb_idx, here)
                if key not in edges_seen:
                    edges_seen[key] = len(edges_seen)
                edge_of[here, dir_idx] = edges_seen[key]

    n_edges = len(edges_seen)
    edge_endpoints = np.zeros((n_edges, 2), dtype=np.int32)
    for (a, b), eid in edges_seen.items():
        edge_endpoints[eid, 0] = a
        edge_endpoints[eid, 1] = b
    return adj, edge_of, edge_endpoints, n_edges


def _build_manhattan(puzzle: Puzzle, waypoint_cells: np.ndarray) -> np.ndarray:  # type: ignore[type-arg]
    n = puzzle.N
    n2 = n * n
    K = puzzle.K  # noqa: N806
    table = np.zeros((n2, K), dtype=np.int16)
    for cell in range(n2):
        cr, cc = cell // n, cell % n
        for k in range(K):
            wc = int(waypoint_cells[k])
            wr, wcol = wc // n, wc % n
            table[cell, k] = abs(cr - wr) + abs(cc - wcol)
    return table


def _build_parity(n: int) -> np.ndarray:  # type: ignore[type-arg]
    table = np.zeros(n * n, dtype=np.int8)
    for r in range(n):
        for c in range(n):
            table[r * n + c] = (r + c) & 1
    return table


def pack(puzzle: Puzzle, config: SolverConfig) -> KernelState:
    waypoint_of_max = int(np.iinfo(np.int8).max)
    if waypoint_of_max < puzzle.K:
        msg = (
            f"waypoint_of dtype int8 cannot represent K={puzzle.K} "
            f"(max {waypoint_of_max})"
        )
        raise ValueError(msg)
    n = puzzle.N
    n2 = n * n
    K = puzzle.K  # noqa: N806
    L = puzzle.L()  # noqa: N806
    blocked_mask = np.zeros(n2, dtype=np.bool_)
    for r, c in puzzle.blocked:
        blocked_mask[r * n + c] = True

    adjacency, edge_of, edge_endpoints, n_edges = _build_adjacency(puzzle)
    adjacency_count = (adjacency >= 0).sum(axis=1).astype(np.int16)

    waypoint_cells = np.array(
        [r * n + c for (r, c) in puzzle.waypoints], dtype=np.int16
    )
    waypoint_of = np.full(n2, -1, dtype=np.int8)
    for k, wcell in enumerate(waypoint_cells, start=1):
        waypoint_of[int(wcell)] = k

    manhattan_table = _build_manhattan(puzzle, waypoint_cells)
    parity_table = _build_parity(n)

    f0_total = int(np.sum((parity_table == 0) & (~blocked_mask)))
    f1_total = int(np.sum((parity_table == 1) & (~blocked_mask)))

    n_walkers = int(config.population)
    n_stripes = (K - 1) if (config.pheromone_mode == "stratified" and K > 1) else 1
    pher_mode_int = 1 if config.pheromone_mode == "stratified" else 0
    tau_signed_int = 1 if config.tau_signed else 0

    tau_clip_min = -float(config.tau_max) if config.tau_signed else 0.0
    tau_init = float(config.tau_0)
    tau = np.full((n_stripes, max(n_edges, 1)), tau_init, dtype=np.float32)

    visited_words = (n2 + 63) // 64
    pos = np.zeros(n_walkers, dtype=np.int16)
    visited = np.zeros((n_walkers, visited_words), dtype=np.uint64)
    path = np.zeros((n_walkers, L), dtype=np.int16)
    path_len = np.zeros(n_walkers, dtype=np.int16)
    segment = np.zeros(n_walkers, dtype=np.int8)
    status = np.zeros(n_walkers, dtype=np.int8)
    f0_remaining = np.zeros(n_walkers, dtype=np.int32)
    f1_remaining = np.zeros(n_walkers, dtype=np.int32)
    walker_fitness = np.zeros(n_walkers, dtype=np.float64)

    return KernelState(
        L=L,
        N=n,
        N2=n2,
        K=K,
        E=max(n_edges, 1),
        n_walkers=n_walkers,
        n_stripes=n_stripes,
        pheromone_mode=pher_mode_int,
        tau_signed=tau_signed_int,
        alpha=float(config.alpha),
        beta=float(config.beta),
        beta1=_resolve_beta1(config.beta1, n),
        beta2=float(config.beta2),
        beta3=_resolve_beta3(config.beta3, n),
        gamma_man=float(config.gamma_man),
        gamma_warns=float(config.gamma_warns),
        gamma_art=float(config.gamma_art),
        gamma_par=float(config.gamma_par),
        tau_max=float(config.tau_max),
        tau_clip_min=tau_clip_min,
        tau_0=tau_init,
        z=float(config.z),
        iter_cap=int(config.iter_cap),
        visible_walkers=int(config.visible_walkers),
        frame_interval=int(config.frame_interval),
        tau_delta_epsilon=float(config.tau_delta_epsilon),
        tau=tau,
        pos=pos,
        visited=visited,
        path=path,
        path_len=path_len,
        segment=segment,
        status=status,
        f0_remaining=f0_remaining,
        f1_remaining=f1_remaining,
        walker_fitness=walker_fitness,
        manhattan_table=manhattan_table,
        parity_table=parity_table,
        adjacency=adjacency,
        adjacency_count=adjacency_count,
        edge_of=edge_of,
        edge_endpoints=edge_endpoints,
        waypoint_cells=waypoint_cells,
        waypoint_of=waypoint_of,
        f0_total=f0_total,
        f1_total=f1_total,
    )


def unpack_path(state: KernelState, walker_id: int) -> tuple[Coord, ...]:
    n = state.N
    plen = int(state.path_len[walker_id])
    raw = state.path[walker_id, :plen]
    return tuple((int(c) // n, int(c) % n) for c in raw)
