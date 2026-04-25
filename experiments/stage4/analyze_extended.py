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

from zipmould.metrics import aggregate


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

    Reports the puzzle count, the count of puzzles solved by every seed
    (perfect reliability), the count never solved by any seed (zero
    reliability), and the median per-puzzle solve rate across the
    condition's puzzles.
    """
    per_pc = df.group_by(["condition", "puzzle_id"]).agg(
        n_seeds=pl.len(),
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


def asymmetric_puzzles(
    df: pl.DataFrame,
    baseline: str,
    candidate: str,
) -> dict[str, list[str]]:
    """Identify puzzles where solved_any differs between two conditions.

    Returns three sorted lists: puzzles only the candidate solved, puzzles
    only the baseline solved, and puzzles neither solved.
    """
    agg = aggregate(df)
    pivot = (
        agg.filter(pl.col("condition").is_in([baseline, candidate]))
        .pivot(values="solved_any", index="puzzle_id", on="condition")
        .drop_nulls([baseline, candidate])
    )
    cand_only = sorted(
        pivot.filter((~pl.col(baseline)) & pl.col(candidate))["puzzle_id"].to_list(),
    )
    base_only = sorted(
        pivot.filter(pl.col(baseline) & (~pl.col(candidate)))["puzzle_id"].to_list(),
    )
    both_fail = sorted(
        pivot.filter((~pl.col(baseline)) & (~pl.col(candidate)))["puzzle_id"].to_list(),
    )
    return {
        "candidate_only": cand_only,
        "baseline_only": base_only,
        "both_fail": both_fail,
    }


def efficiency_compare(
    df: pl.DataFrame,
    baseline: str,
    candidate: str,
) -> dict[str, Any]:
    """Paired iters/wall-ms diff on (puzzle, seed) pairs both conditions solved.

    Returns N pairs and quartiles of (candidate - baseline) for both metrics.
    A negative median means the candidate is faster on the intersected set.
    """
    base = (
        df.filter((pl.col("condition") == baseline) & pl.col("solved"))
        .select(["puzzle_id", "seed", "iters", "wall_ms"])
        .rename({"iters": "iters_base", "wall_ms": "wall_ms_base"})
    )
    cand = (
        df.filter((pl.col("condition") == candidate) & pl.col("solved"))
        .select(["puzzle_id", "seed", "iters", "wall_ms"])
        .rename({"iters": "iters_cand", "wall_ms": "wall_ms_cand"})
    )
    joined = base.join(cand, on=["puzzle_id", "seed"], how="inner")
    if joined.is_empty():
        return {
            "n_pairs": 0,
            "iters_diff_quartiles": None,
            "wall_ms_diff_quartiles": None,
        }
    diff_iters = (joined["iters_cand"].to_numpy() - joined["iters_base"].to_numpy()).astype(np.float64)
    diff_wall = (joined["wall_ms_cand"].to_numpy() - joined["wall_ms_base"].to_numpy()).astype(np.float64)
    return {
        "n_pairs": int(joined.height),
        "iters_diff_quartiles": [float(np.quantile(diff_iters, q)) for q in (0.25, 0.5, 0.75)],
        "wall_ms_diff_quartiles": [float(np.quantile(diff_wall, q)) for q in (0.25, 0.5, 0.75)],
    }
