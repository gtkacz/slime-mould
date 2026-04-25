"""Heuristic-only baseline: ZipMould with pheromone frozen and alpha=0.

This isolates the contribution of the heuristic mixture from the
pheromone-feedback loop.  We do not duplicate the kernel — we call
``zipmould.solver.api.solve`` with a config override that zeroes alpha
and forces freeze_pheromone=True.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from zipmould.solver.api import solve as _zipmould_solve

if TYPE_CHECKING:
    from zipmould.config import SolverConfig
    from zipmould.puzzle import Puzzle
    from zipmould.solver.api import RunResult


def solve(
    puzzle: Puzzle,
    config: SolverConfig,
    *,
    seed: int,
    trace: bool = False,
    global_seed: int = 0,
    condition: str = "heuristic-only",
    freeze_pheromone: bool = False,
) -> RunResult:
    """Run ZipMould with alpha forced to 0 and pheromone frozen."""
    del freeze_pheromone

    cfg = config.model_copy(update={"alpha": 0.0})
    return _zipmould_solve(
        puzzle,
        cfg,
        seed=seed,
        trace=trace,
        global_seed=global_seed,
        condition=condition,
        freeze_pheromone=True,
    )
