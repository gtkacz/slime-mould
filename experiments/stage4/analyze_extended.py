"""Stage-4 extended analyses.

Complementary descriptive statistics beyond the pre-registered McNemar
test, supporting a more honest narrative without significance-chasing
on a locked test result. Inputs: ``experiments/stage4/out/results.parquet``.
Output: ``experiments/stage4/out/extended_report.json``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl
import typer
from loguru import logger

from zipmould.logging_config import configure_logging
from zipmould.metrics import aggregate, load_results

from experiments.stage4.analyze import BASELINES, CANDIDATE, _solve_counts

app = typer.Typer(add_completion=False, no_args_is_help=False)


def paired_bootstrap_diff(
    pivot: pl.DataFrame,
    baseline: str,
    candidate: str,
    n_boot: int = 10_000,
    rng_seed: int = 20260425,
    ci_level: float = 0.95,
) -> dict[str, Any]:
    """Paired bootstrap CI on (candidate_solved - baseline_solved) per puzzle.

    `pivot` is one row per puzzle with bool columns for each condition.
    Resamples puzzles with replacement; returns the empirical CI of the
    sum-of-diffs across the resampled puzzle set.
    """
    base = pivot[baseline].cast(pl.Int64).to_numpy()
    cand = pivot[candidate].cast(pl.Int64).to_numpy()
    diffs = cand - base
    n = int(diffs.shape[0])
    rng = np.random.default_rng(rng_seed)
    idx = rng.integers(0, n, size=(n_boot, n))
    boot_sums = diffs[idx].sum(axis=1).astype(np.float64)
    alpha = (1.0 - ci_level) / 2.0
    return {
        "n_puzzles": n,
        "observed_diff": int(diffs.sum()),
        "ci_low": float(np.quantile(boot_sums, alpha)),
        "ci_high": float(np.quantile(boot_sums, 1.0 - alpha)),
        "median_boot_diff": float(np.median(boot_sums)),
        "n_boot": int(n_boot),
        "ci_level": float(ci_level),
        "rng_seed": int(rng_seed),
    }
