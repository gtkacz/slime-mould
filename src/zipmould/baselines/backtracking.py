"""Time-limited DFS backtracking baseline.

Implements iterative depth-first search over the Hamiltonian-path
problem, with three prunes:

  1. Waypoint ordering: a cell containing waypoint k+1 is illegal until
     waypoint k has been claimed.
  2. Parity prune: the remaining cell counts on each colour class must
     stay within +/- 1.
  3. Articulation prune: if removing the current cell leaves the
     remaining-free subgraph disconnected, the partial path cannot be
     extended to a Hamiltonian path; backtrack.

Termination on first success or wall-clock expiry.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import numpy as np

from zipmould.feasibility import precheck
from zipmould.solver.api import (
    RunResult,
    _git_sha_and_dirty,  # pyright: ignore[reportPrivateUsage]
    _library_versions,  # pyright: ignore[reportPrivateUsage]
)
from zipmould.solver.state import pack

if TYPE_CHECKING:
    from zipmould.config import SolverConfig
    from zipmould.puzzle import Coord, Puzzle


def _articulation_ok(
    cur: int,
    visited: np.ndarray,  # type: ignore[type-arg]
    adjacency: np.ndarray,  # type: ignore[type-arg]
    adjacency_count: np.ndarray,  # type: ignore[type-arg]
    expected_remaining: int,
) -> bool:
    """BFS over unvisited cells from any unvisited neighbour of cur."""
    del adjacency_count
    n = visited.shape[0]
    n_slots = int(adjacency.shape[1])
    start = -1
    for i in range(n_slots):
        nb = int(adjacency[cur, i])
        if nb < 0:
            continue
        if not visited[nb]:
            start = nb
            break
    if start < 0:
        return expected_remaining == 0
    seen = np.zeros(n, dtype=np.bool_)
    seen[cur] = True
    seen[start] = True
    stack: list[int] = [start]
    reached = 0
    while stack:
        c = stack.pop()
        reached += 1
        for i in range(n_slots):
            nb = int(adjacency[c, i])
            if nb < 0:
                continue
            if visited[nb] or seen[nb]:
                continue
            seen[nb] = True
            stack.append(nb)
    return reached == expected_remaining


def solve(  # noqa: PLR0912, PLR0915
    puzzle: Puzzle,
    config: SolverConfig,
    *,
    seed: int,
    trace: bool = False,
    global_seed: int = 0,
    condition: str = "backtracking",
    freeze_pheromone: bool = False,
) -> RunResult:
    """DFS backtracking with parity + articulation prunes, time-limited."""
    del seed, trace, global_seed, condition, freeze_pheromone

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

    state = pack(puzzle, config)
    n = int(state.N)
    n_cells = int(state.N2)
    L = int(state.L)  # noqa: N806
    K = int(state.K)  # noqa: N806
    waypoint_cells = np.asarray(state.waypoint_cells, dtype=np.int32)
    waypoint_of = np.asarray(state.waypoint_of, dtype=np.int32)
    adjacency = np.asarray(state.adjacency, dtype=np.int32)
    adjacency_count = np.asarray(state.adjacency_count, dtype=np.int32)
    parity = np.asarray(state.parity_table, dtype=np.int32)

    visited = np.zeros(n_cells, dtype=np.bool_)
    path = np.full(L, -1, dtype=np.int32)
    path[0] = int(waypoint_cells[0])
    visited[path[0]] = True

    f0_remaining = int(state.f0_total) - (1 if int(parity[path[0]]) == 0 else 0)
    f1_remaining = int(state.f1_total) - (1 if int(parity[path[0]]) == 1 else 0)

    start_time = time.perf_counter()
    deadline = start_time + float(config.wall_clock_s)
    iters = 0
    best_len = 1
    best_path: np.ndarray | None = None  # type: ignore[type-arg]
    solved = False

    stack_cur: list[int] = [int(path[0])]
    stack_seg: list[int] = [1]
    stack_iter: list[int] = [0]

    n_slots = int(adjacency.shape[1])
    while stack_cur:
        if time.perf_counter() > deadline:
            break
        iters += 1
        cur = stack_cur[-1]
        seg = stack_seg[-1]
        nb_i = stack_iter[-1]
        depth = len(stack_cur)
        if depth > best_len:
            best_len = depth
            best_path = path[:depth].copy()
        if depth == L and seg == K:
            solved = True
            break
        if nb_i >= n_slots:
            visited[cur] = False
            if int(parity[cur]) == 0:
                f0_remaining += 1
            else:
                f1_remaining += 1
            stack_cur.pop()
            stack_seg.pop()
            stack_iter.pop()
            if stack_cur:
                stack_iter[-1] += 1
            continue
        nb = int(adjacency[cur, nb_i])
        if nb < 0:
            stack_iter[-1] += 1
            continue
        if visited[nb]:
            stack_iter[-1] += 1
            continue
        w_of = int(waypoint_of[nb])
        if w_of > 0 and w_of != seg + 1:
            stack_iter[-1] += 1
            continue
        new_seg = seg + 1 if w_of == seg + 1 else seg
        new_f0 = f0_remaining - (1 if int(parity[nb]) == 0 else 0)
        new_f1 = f1_remaining - (1 if int(parity[nb]) == 1 else 0)
        if abs(new_f0 - new_f1) > 1:
            stack_iter[-1] += 1
            continue
        remaining = L - (depth + 1)
        if remaining > 0 and not _articulation_ok(nb, visited, adjacency, adjacency_count, remaining):
            stack_iter[-1] += 1
            continue
        path[depth] = nb
        visited[nb] = True
        f0_remaining = new_f0
        f1_remaining = new_f1
        stack_cur.append(nb)
        stack_seg.append(new_seg)
        stack_iter.append(0)

    elapsed = time.perf_counter() - start_time

    best_fitness = float(best_len)
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
