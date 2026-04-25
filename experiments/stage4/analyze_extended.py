"""Stage-4 extended analyses.

Complementary descriptive statistics beyond the pre-registered McNemar
test, supporting a more honest narrative without significance-chasing
on a locked test result. Inputs: ``experiments/stage4/out/results.parquet``.
Output: ``experiments/stage4/out/extended_report.json``.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import polars as pl


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


def seed_reliability(df: pl.DataFrame) -> list[dict[str, Any]]:
    """Per-condition seed-level reliability across the 37-puzzle test set.

    Reports total solve rate, the count of puzzles solved by every seed
    (perfect reliability), the count never solved (zero reliability),
    and the median per-puzzle solve rate.
    """
    per_pc = df.group_by(["condition", "puzzle_id"]).agg(
        n_seeds=pl.len(),
        n_solved=pl.col("solved").sum(),
        seed_solve_rate=pl.col("solved").mean(),
    )
    return (
        per_pc.group_by("condition")
        .agg(
            n_puzzles=pl.len(),
            puzzles_perfect=(pl.col("seed_solve_rate") >= 1.0).sum(),
            puzzles_never=(pl.col("seed_solve_rate") <= 0.0).sum(),
            median_puzzle_solve_rate=pl.col("seed_solve_rate").median(),
        )
        .sort("condition")
        .to_dicts()
    )
