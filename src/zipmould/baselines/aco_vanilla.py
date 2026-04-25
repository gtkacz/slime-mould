"""Classical ACO baseline.

Differences from ZipMould (design.md §6.1):
  * Pheromone is unsigned-positive (tau_signed=False).
  * Deposit is fitness-proportional and positive only (no rank weights).
  * Evaporation is a constant rho (no SMA oscillator/contraction terms).
  * No restart noise injection.

Walker step (legality, softmax sampling) is identical to ZipMould; only
the pheromone update is varied.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import numba as nb
import numpy as np

from zipmould.fitness import fitness as _fitness
from zipmould.rng import derive_kernel_seed
from zipmould.solver._kernel import _init_walker, _seed_kernel, _walker_run  # pyright: ignore[reportPrivateUsage]
from zipmould.solver.api import (
    RunResult,
    _git_sha_and_dirty,  # pyright: ignore[reportPrivateUsage]
    _library_versions,  # pyright: ignore[reportPrivateUsage]
)
from zipmould.solver.state import pack

if TYPE_CHECKING:
    from zipmould.config import SolverConfig
    from zipmould.puzzle import Coord, Puzzle


_RHO: float = 0.1
_Q: float = 1.0
_TAU_FLOOR: float = 1e-9


@nb.njit(cache=True, fastmath=False)  # type: ignore[misc]
def _aco_update(  # pyright: ignore[reportUnusedFunction]
    tau: np.ndarray,  # type: ignore[type-arg]
    path: np.ndarray,  # type: ignore[type-arg]
    path_len: np.ndarray,  # type: ignore[type-arg]
    edge_of: np.ndarray,  # type: ignore[type-arg]
    walker_fitness: np.ndarray,  # type: ignore[type-arg]
    rho: float,
    q: float,
    tau_floor: float,
    n_walkers: int,
    adjacency: np.ndarray,  # type: ignore[type-arg]
) -> None:
    """Classical evaporation + fitness-proportional deposit on tau[0]."""
    n_edges = tau.shape[1]
    for e in range(n_edges):
        tau[0, e] = (1.0 - rho) * tau[0, e]

    for w in range(n_walkers):
        deposit = q * float(walker_fitness[w])
        plen = int(path_len[w])
        for s in range(plen - 1):
            c = int(path[w, s])
            cn = int(path[w, s + 1])
            for ai in range(4):
                if int(adjacency[c, ai]) == cn:
                    e = int(edge_of[c, ai])
                    if e >= 0:
                        tau[0, e] += deposit
                    break

    for e in range(n_edges):
        if tau[0, e] < tau_floor:  # noqa: PLR1730 - max() not @njit-supported on float scalars in older Numba
            tau[0, e] = tau_floor


def solve(
    puzzle: Puzzle,
    config: SolverConfig,
    *,
    seed: int,
    trace: bool = False,
    global_seed: int = 0,
    condition: str = "aco-vanilla",
    freeze_pheromone: bool = False,
) -> RunResult:
    """Vanilla ACO baseline using classical evaporate+deposit on a unified tau."""
    del trace, condition, freeze_pheromone

    cfg = config.model_copy(update={"pheromone_mode": "unified", "tau_signed": False})
    cfg_hash = cfg.config_hash()
    versions = _library_versions()
    git_sha, git_dirty = _git_sha_and_dirty()

    state = pack(puzzle, cfg)
    work_stack = np.zeros(state.N2 * 2, dtype=np.int32)
    kseed = derive_kernel_seed(
        global_seed=global_seed,
        run_seed=seed,
        puzzle_id=puzzle.id,
        config_hash=cfg_hash,
    )
    _seed_kernel(int(kseed))

    n = int(state.N)
    L = int(state.L)  # noqa: N806
    K = int(state.K)  # noqa: N806
    n_walkers = int(state.n_walkers)
    waypoint_cells = np.asarray(state.waypoint_cells, dtype=np.int32)

    start_time = time.perf_counter()
    iters = 0
    best_fitness = 0.0
    best_path: np.ndarray | None = None  # type: ignore[type-arg]
    best_len = 0
    solved = False

    while time.perf_counter() - start_time < float(cfg.wall_clock_s) and iters < int(cfg.iter_cap):
        iters += 1
        for w in range(n_walkers):
            _init_walker(
                w,
                state.pos,
                state.visited,
                state.path,
                state.path_len,
                state.segment,
                state.status,
                state.f0_remaining,
                state.f1_remaining,
                state.waypoint_cells,
                state.parity_table,
                state.f0_total,
                state.f1_total,
            )
            _walker_run(
                w,
                state.pos,
                state.visited,
                state.path,
                state.path_len,
                state.segment,
                state.status,
                state.f0_remaining,
                state.f1_remaining,
                state.adjacency,
                state.edge_of,
                state.waypoint_of,
                state.parity_table,
                state.manhattan_table,
                state.waypoint_cells,
                state.tau,
                state.pheromone_mode,
                state.n_stripes,
                state.K,
                state.L,
                state.N2,
                state.alpha,
                state.beta,
                state.gamma_man,
                state.gamma_warns,
                state.gamma_art,
                state.gamma_par,
                work_stack,
            )
            plen = int(state.path_len[w])
            seg = int(state.segment[w])
            last_cell = int(state.path[w, plen - 1]) if plen > 0 else int(waypoint_cells[0])
            f = float(
                _fitness(
                    plen,
                    seg,
                    last_cell,
                    waypoint_cells,
                    L,
                    K,
                    n,
                    float(state.beta1),
                    float(state.beta2),
                    float(state.beta3),
                )
            )
            state.walker_fitness[w] = f
            if f > best_fitness:
                best_fitness = f
                best_len = plen
                best_path = state.path[w, :plen].copy()
            if int(state.status[w]) == 2:  # noqa: PLR2004
                solved = True
                best_fitness = f
                best_len = plen
                best_path = state.path[w, :plen].copy()
                break
        if solved:
            break
        _aco_update(
            state.tau,
            state.path,
            state.path_len,
            state.edge_of,
            state.walker_fitness,
            _RHO,
            _Q,
            _TAU_FLOOR,
            n_walkers,
            state.adjacency,
        )

    elapsed = time.perf_counter() - start_time

    max_f = float(L) + float(state.beta1) * float(K) + float(state.beta2) + float(state.beta3)
    best_normalised = best_fitness / max_f if max_f > 0 else 0.0

    solution: tuple[Coord, ...] | None = None
    if solved and best_path is not None:
        solution = tuple((int(c) // n, int(c) % n) for c in best_path[:best_len])

    return RunResult(
        solved=solved,
        infeasible=False,
        feasibility_reason=None,
        solution=solution,
        iters_used=iters,
        wall_clock_s=elapsed,
        best_fitness=best_fitness,
        best_fitness_normalised=best_normalised,
        trace=None,
        config_hash=cfg_hash,
        versions=versions,
        git_sha=git_sha,
        git_dirty=git_dirty,
    )
