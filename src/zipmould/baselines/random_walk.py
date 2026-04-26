"""Uniform-random walker over legal moves.

This is the weakest baseline in the design.md ablation grid.  At each
step we enumerate legal neighbours (in-bounds, not blocked, not visited,
respecting wall constraints, and respecting waypoint ordering) and pick
one uniformly at random.  We declare success only when the walker has
covered exactly L cells in the correct waypoint order and terminates on
the last waypoint.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import numpy as np

from zipmould.feasibility import precheck
from zipmould.fitness import fitness as _fitness
from zipmould.rng import make_rng
from zipmould.solver.api import (
    RunResult,
    _git_sha_and_dirty,  # pyright: ignore[reportPrivateUsage]
    _library_versions,  # pyright: ignore[reportPrivateUsage]
)
from zipmould.solver.state import pack

if TYPE_CHECKING:
    from zipmould.config import SolverConfig
    from zipmould.puzzle import Coord, Puzzle


def solve(  # noqa: PLR0915
    puzzle: Puzzle,
    config: SolverConfig,
    *,
    seed: int,
    trace: bool = False,
    global_seed: int = 0,
    condition: str = "random",
    freeze_pheromone: bool = False,
) -> RunResult:
    """Random-walk baseline; ignores all pheromone/heuristic knobs."""
    del trace, condition, freeze_pheromone

    cfg_hash = config.config_hash()
    versions = _library_versions()
    git_sha, git_dirty = _git_sha_and_dirty()

    feas = precheck(puzzle)
    if not feas.feasible:
        return RunResult(
            solved=False,
            infeasible=True,
            feasibility_reason=feas.reason,
            solution=None,
            iters_used=0,
            wall_clock_s=0.0,
            best_fitness=0.0,
            best_fitness_normalised=0.0,
            trace=None,
            config_hash=cfg_hash,
            versions=versions,
            git_sha=git_sha,
            git_dirty=git_dirty,
        )

    rng = make_rng(
        global_seed=global_seed,
        run_seed=seed,
        puzzle_id=puzzle.id,
        config_hash=cfg_hash,
    )
    state = pack(puzzle, config)
    n = int(state.N)
    n_cells = int(state.N2)
    L = int(state.L)  # noqa: N806
    K = int(state.K)  # noqa: N806
    waypoint_cells = np.asarray(state.waypoint_cells, dtype=np.int32)

    start_time = time.perf_counter()
    best_path: np.ndarray | None = None  # type: ignore[type-arg]
    best_len = 0
    best_segment = 1
    iters = 0
    solved = False

    while time.perf_counter() - start_time < float(config.wall_clock_s) and iters < int(config.iter_cap):
        iters += 1
        path = np.full(L, -1, dtype=np.int32)
        visited = np.zeros(n_cells, dtype=np.bool_)
        path[0] = int(waypoint_cells[0])
        visited[path[0]] = True
        segment = 1
        path_len = 1
        dead = False
        while path_len < L and not dead:
            cur = int(path[path_len - 1])
            legal: list[int] = []
            for nb_idx in range(int(state.adjacency.shape[1])):
                nb = int(state.adjacency[cur, nb_idx])
                if nb < 0:
                    continue
                if visited[nb]:
                    continue
                w_of = int(state.waypoint_of[nb])
                if w_of >= 0 and w_of != segment + 1:
                    continue
                legal.append(nb)
            if not legal:
                dead = True
                break
            choice = int(rng.integers(0, len(legal)))
            nxt = legal[choice]
            path[path_len] = nxt
            visited[nxt] = True
            path_len += 1
            w_of = int(state.waypoint_of[nxt])
            if w_of == segment + 1:
                segment += 1
        if path_len > best_len:
            best_len = path_len
            best_segment = segment
            best_path = path.copy()
        if path_len == L and segment == K and int(path[path_len - 1]) == int(waypoint_cells[K - 1]):
            solved = True
            break

    elapsed = time.perf_counter() - start_time

    last_cell = int(best_path[best_len - 1]) if (best_path is not None and best_len > 0) else int(waypoint_cells[0])
    best_fitness = float(
        _fitness(
            int(best_len),
            int(best_segment),
            int(last_cell),
            waypoint_cells,
            L,
            K,
            n,
            float(state.beta1),
            float(state.beta2),
            float(state.beta3),
        )
    )
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
