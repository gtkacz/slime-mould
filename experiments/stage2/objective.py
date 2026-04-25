"""Per-trial objective: count solved (puzzle, seed) pairs on a split.

Spec §3.2. Dispatches `len(seeds) * len(puzzle_ids)` runs through
``zipmould.solver.api.solve`` via joblib and returns the integer
count of solved pairs. Worker exceptions are caught and treated as
``solved=False`` so a single crashing puzzle does not abort a trial.
"""

from __future__ import annotations

from typing import Final

from joblib import Parallel, delayed  # pyright: ignore[reportMissingTypeStubs]
from loguru import logger

from zipmould.config import SolverConfig
from zipmould.io.puzzles import load_corpus
from zipmould.puzzle import Puzzle
from zipmould.solver.api import solve

CONDITION_PREFIX: Final[str] = "stage2-trial"


def _run_one(
    puzzle: Puzzle,
    config: SolverConfig,
    seed: int,
    global_seed: int,
    variant: str,
) -> bool:
    try:
        result = solve(
            puzzle,
            config,
            seed=seed,
            trace=False,
            global_seed=global_seed,
            condition=f"{CONDITION_PREFIX}-{variant}",
        )
    except Exception as exc:
        logger.opt(exception=exc).debug(
            "trial worker failed: variant={} puzzle={} seed={}",
            variant,
            puzzle.id,
            seed,
        )
        return False
    return bool(result.solved)


def evaluate(
    config: SolverConfig,
    puzzle_ids: list[str],
    seeds: list[int],
    *,
    variant: str,
    global_seed: int,
    n_jobs: int = -1,
) -> int:
    """Return number of solved (puzzle, seed) pairs for ``config`` over the given grid."""
    corpus = load_corpus()
    puzzles = [corpus[pid] for pid in puzzle_ids]

    flags: list[bool] = Parallel(n_jobs=n_jobs, backend="loky", verbose=0)(  # pyright: ignore[reportUnknownVariableType, reportAssignmentType]
        delayed(_run_one)(p, config, s, global_seed, variant)  # pyright: ignore[reportUnknownArgumentType]
        for p in puzzles
        for s in seeds
    )
    return int(sum(flags))
