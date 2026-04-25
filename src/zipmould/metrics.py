"""Metrics: aggregate Stage-1 Parquet results and compute McNemar tests.

Stage-1 produces a long-format Parquet table with one row per
(puzzle_id, condition, seed) triple.  This module provides:

  * ``aggregate(df)``: per-(puzzle, condition) reductions
        - solved_any (bool): any seed solved
        - best_fitness (float): max best_fitness across seeds
        - median_iters (int): median iters across seeds
        - p50_wall_ms / p90_wall_ms (float)
  * ``mcnemar_paired(df, baseline, candidate)``: paired McNemar test on
    solved-any flags between two conditions, using the design.md §10
    decision rule (b > c and b > c + 1.96 * sqrt(b + c)).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import polars as pl


@dataclass(frozen=True, slots=True)
class McNemarResult:
    baseline: str
    candidate: str
    n: int
    b: int
    c: int
    statistic: float
    significant: bool
    decision: str


def load_results(path: Path | str) -> pl.DataFrame:
    """Load Parquet results table written by ``experiments/stage1/run.py``."""
    return pl.read_parquet(str(path))


def aggregate(df: pl.DataFrame) -> pl.DataFrame:
    """Reduce per-(puzzle, condition, seed) rows to per-(puzzle, condition)."""
    return (
        df.group_by(["puzzle_id", "condition"])
        .agg(
            solved_any=pl.col("solved").any(),
            best_fitness=pl.col("best_fitness").max(),
            median_iters=pl.col("iters").median().cast(pl.Int64),
            p50_wall_ms=pl.col("wall_ms").median(),
            p90_wall_ms=pl.col("wall_ms").quantile(0.9),
        )
        .sort(["condition", "puzzle_id"])
    )


def mcnemar_paired(
    df: pl.DataFrame,
    baseline: str,
    candidate: str,
) -> McNemarResult:
    """Paired McNemar test on solved-any flags per design.md §10."""
    agg = aggregate(df)
    pivot = (
        agg.filter(pl.col("condition").is_in([baseline, candidate]))
        .pivot(values="solved_any", index="puzzle_id", on="condition")
        .drop_nulls([baseline, candidate])
    )
    n = pivot.height
    if n == 0:
        return McNemarResult(baseline, candidate, 0, 0, 0, 0.0, False, "no overlap")
    b = int(pivot.filter((~pl.col(baseline)) & pl.col(candidate)).height)
    c = int(pivot.filter(pl.col(baseline) & (~pl.col(candidate))).height)
    if b + c == 0:
        return McNemarResult(baseline, candidate, n, 0, 0, 0.0, False, "tied: no discordant pairs")
    threshold = c + 1.96 * math.sqrt(b + c)
    significant = b > c and b > threshold
    statistic = (b - c) / math.sqrt(b + c) if (b + c) > 0 else 0.0
    if significant:
        decision = "candidate wins"
    elif b > c:
        decision = "trend favours candidate"
    else:
        decision = "no improvement"
    return McNemarResult(baseline, candidate, n, b, c, statistic, significant, decision)
