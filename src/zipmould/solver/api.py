"""Top-level solver entry point composing feasibility, kernel, and trace assembly."""

from __future__ import annotations

import subprocess
import sys
import time
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

import numpy as np

from zipmould.config import SolverConfig
from zipmould.feasibility import precheck
from zipmould.io.trace import (
    TRACE_SCHEMA_VERSION,
    BestPath,
    Frame,
    TauDelta,
    Trace,
    TraceFooter,
    TraceHeader,
    WalkerSnapshot,
)
from zipmould.puzzle import Coord, Puzzle
from zipmould.rng import derive_kernel_seed
from zipmould.solver._kernel import _kernel_run  # pyright: ignore[reportPrivateUsage]
from zipmould.solver.state import KernelState, pack, unpack_path


@dataclass(frozen=True, slots=True)
class RunResult:
    solved: bool
    infeasible: bool
    feasibility_reason: str | None
    solution: tuple[Coord, ...] | None
    iters_used: int
    wall_clock_s: float
    best_fitness: float
    best_fitness_normalised: float
    trace: Trace | None
    config_hash: str
    versions: Mapping[str, str]
    git_sha: str
    git_dirty: bool


def _library_versions() -> dict[str, str]:
    from importlib.metadata import version

    import joblib as _joblib
    import numba as _numba
    import polars as _polars
    import pydantic as _pydantic

    return {
        "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "numpy": np.__version__,
        "numba": _numba.__version__,
        "pydantic": _pydantic.VERSION,
        "polars": _polars.__version__,
        "joblib": _joblib.__version__,
        "cbor2": version("cbor2"),
    }


def _git_sha_and_dirty() -> tuple[str, bool]:
    try:
        sha = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()  # noqa: S603, S607
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ("unknown", False)
    try:
        diff = subprocess.check_output(["git", "status", "--porcelain"], text=True)  # noqa: S603, S607
        return (sha, bool(diff.strip()))
    except subprocess.CalledProcessError:
        return (sha, False)


def _max_fitness(L: int, K: int, beta1: float, beta2: float, beta3: float) -> float:  # noqa: N803
    return float(L) + beta1 * float(K) + beta2 + beta3


def _build_trace(
    puzzle: Puzzle,
    config: SolverConfig,
    state: KernelState,
    seed: int,
    n_frames: int,
    iters_used: int,
    wall_clock_s: float,
    solved: bool,
    solution: tuple[Coord, ...] | None,
    best_fitness: float,
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
) -> Trace:
    n = puzzle.N
    mode_str: Literal["unified", "stratified"] = (
        "stratified" if state.pheromone_mode == 1 else "unified"
    )

    frames: list[Frame] = []
    for fi in range(n_frames):
        edges_raw: list[tuple[int, int, float]] = []
        for j in range(int(frame_tau_count[fi])):
            eid = int(frame_tau_payload[fi, j, 0])
            stripe = int(frame_tau_payload[fi, j, 1])
            delta = float(frame_tau_payload[fi, j, 2])
            edges_raw.append((eid, stripe if mode_str == "stratified" else -1, delta))
        td = TauDelta(mode=mode_str, edges=tuple(edges_raw))

        best_w = int(frame_best_w[fi])
        path_len = int(state.path_len[best_w])
        best_path = tuple(
            (int(state.path[best_w, s]) // n, int(state.path[best_w, s]) % n)
            for s in range(path_len)
        )
        bp = BestPath(path=best_path, fitness=float(frame_best_fitness[fi]))

        walkers: list[WalkerSnapshot] = []
        for k in range(state.visible_walkers):
            wid = int(frame_walker_ids[fi, k])
            if wid < 0:
                continue
            cell = int(frame_walker_cells[fi, k])
            stat_code = int(frame_walker_status[fi, k])
            stat_name: Literal["alive", "dead-end", "complete"] = (
                "alive" if stat_code == 0 else ("dead-end" if stat_code == 1 else "complete")
            )
            walkers.append(
                WalkerSnapshot(
                    id=wid,
                    cell=(cell // n, cell % n),
                    segment=int(frame_walker_segments[fi, k]),
                    status=stat_name,
                    fitness=float(frame_walker_fitness[fi, k]),
                )
            )

        frames.append(
            Frame(
                t=int(frame_t[fi]),
                v_b=float(frame_v_b[fi]),
                v_c=float(frame_v_c[fi]),
                tau_delta=td,
                best=bp,
                walkers=tuple(walkers),
            )
        )

    header = TraceHeader(
        N=puzzle.N,
        K=puzzle.K,
        L=puzzle.L(),
        waypoints=puzzle.waypoints,
        walls=tuple(sorted(puzzle.walls)),
        blocked=tuple(sorted(puzzle.blocked)),
    )
    footer = TraceFooter(
        solved=solved,
        infeasible=False,
        solution=solution,
        iterations_used=iters_used,
        wall_clock_s=wall_clock_s,
        best_fitness=best_fitness,
    )
    return Trace(
        version=TRACE_SCHEMA_VERSION,
        puzzle_id=puzzle.id,
        config=config.model_dump(mode="json"),
        seed=seed,
        header=header,
        frames=tuple(frames),
        footer=footer,
    )


def solve(  # noqa: PLR0915
    puzzle: Puzzle,
    config: SolverConfig,
    *,
    seed: int,
    trace: bool = False,
    global_seed: int = 0,
    condition: str = "zipmould-uni-signed",
    freeze_pheromone: bool = False,
) -> RunResult:
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
    work_stack = np.zeros(state.N2 * 2, dtype=np.int32)
    kernel_seed = derive_kernel_seed(global_seed, seed, puzzle.id, cfg_hash)

    n_frame_slots = config.iter_cap // config.frame_interval + 2
    n_edges = state.tau.shape[1]
    max_tau_payload = max(n_edges * state.n_stripes, 1)

    frame_t = np.zeros(n_frame_slots, dtype=np.int32)
    frame_v_b = np.zeros(n_frame_slots, dtype=np.float64)
    frame_v_c = np.zeros(n_frame_slots, dtype=np.float64)
    frame_best_w = np.zeros(n_frame_slots, dtype=np.int32)
    frame_best_fitness = np.zeros(n_frame_slots, dtype=np.float64)
    frame_walker_ids = np.full((n_frame_slots, max(config.visible_walkers, 1)), -1, dtype=np.int32)
    frame_walker_cells = np.zeros((n_frame_slots, max(config.visible_walkers, 1)), dtype=np.int32)
    frame_walker_segments = np.zeros((n_frame_slots, max(config.visible_walkers, 1)), dtype=np.int32)
    frame_walker_status = np.zeros((n_frame_slots, max(config.visible_walkers, 1)), dtype=np.int32)
    frame_walker_fitness = np.zeros((n_frame_slots, max(config.visible_walkers, 1)), dtype=np.float64)
    frame_tau_count = np.zeros(n_frame_slots, dtype=np.int32)
    frame_tau_payload = np.zeros((n_frame_slots, max_tau_payload, 3), dtype=np.float64)
    tau_prev = np.zeros_like(state.tau)
    tau_scratch = np.zeros((max_tau_payload, 3), dtype=np.float64)

    t0 = time.perf_counter()
    encoded = _kernel_run(
        state.pos, state.visited, state.path, state.path_len, state.segment, state.status,
        state.f0_remaining, state.f1_remaining, state.walker_fitness,
        state.adjacency, state.edge_of, state.waypoint_of, state.parity_table,
        state.manhattan_table, state.waypoint_cells, state.tau,
        state.pheromone_mode, state.n_walkers, state.n_stripes, state.K, state.L, state.N2, state.N,
        state.alpha, state.beta, state.gamma_man, state.gamma_warns, state.gamma_art, state.gamma_par,
        state.beta1, state.beta2, state.beta3, state.f0_total, state.f1_total, work_stack,
        config.iter_cap, state.z, state.tau_max, state.tau_clip_min,
        1 if freeze_pheromone else 0,
        int(kernel_seed),
        config.frame_interval, config.visible_walkers, state.tau_delta_epsilon,
        frame_t, frame_v_b, frame_v_c, frame_best_w, frame_best_fitness,
        frame_walker_ids, frame_walker_cells, frame_walker_segments,
        frame_walker_status, frame_walker_fitness,
        frame_tau_count, frame_tau_payload,
        tau_prev, tau_scratch,
    )
    elapsed = time.perf_counter() - t0

    n_frames = int(encoded) & ((1 << 30) - 1)
    solved_bit = (int(encoded) >> 30) & 1

    solved = False
    solved_walker = -1
    for w in range(state.n_walkers):
        if int(state.status[w]) == 2:  # noqa: PLR2004
            solved = True
            solved_walker = w
            break

    if solved and solved_walker >= 0:
        solution = unpack_path(state, solved_walker)
        best_fitness = float(state.walker_fitness[solved_walker])
    else:
        best_idx = int(np.argmax(state.walker_fitness))
        solution = None
        best_fitness = float(state.walker_fitness[best_idx])

    iters_used = int(frame_t[max(n_frames - 1, 0)]) + 1 if n_frames > 0 else 0
    if solved_bit and n_frames > 0:
        iters_used = int(frame_t[n_frames - 1]) + 1

    max_f = _max_fitness(state.L, state.K, state.beta1, state.beta2, state.beta3)
    norm = best_fitness / max_f if max_f > 0 else 0.0

    trace_obj: Trace | None = None
    if trace:
        trace_obj = _build_trace(
            puzzle, config, state, seed, n_frames, iters_used, elapsed,
            solved, solution, best_fitness,
            frame_t, frame_v_b, frame_v_c, frame_best_w, frame_best_fitness,
            frame_walker_ids, frame_walker_cells, frame_walker_segments,
            frame_walker_status, frame_walker_fitness,
            frame_tau_count, frame_tau_payload,
        )

    return RunResult(
        solved=solved,
        infeasible=False,
        feasibility_reason=None,
        solution=solution,
        iters_used=iters_used,
        wall_clock_s=elapsed,
        best_fitness=best_fitness,
        best_fitness_normalised=norm,
        trace=trace_obj,
        config_hash=cfg_hash,
        versions=versions,
        git_sha=git_sha,
        git_dirty=git_dirty,
    )


class KernelError(RuntimeError):
    """Raised when the kernel reports `status==3` (engineering fault)."""


class DeterminismError(RuntimeError):
    """Raised by the regression harness if a re-run differs."""
