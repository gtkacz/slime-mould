"""Stage-4 analysis: single McNemar test on the test split.

Spec §5.4. Computes the paired McNemar test of ``tuned-winner`` vs
each baseline; flags the strongest baseline (highest test solve count
excluding tuned-winner) as the primary comparison. Per pre-registered
decision rule from docs/design.md §10, significant if b > c and
b > c + 1.96 sqrt(b + c).
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import polars as pl
import typer
from loguru import logger

from zipmould.logging_config import configure_logging
from zipmould.metrics import aggregate, load_results, mcnemar_paired

app = typer.Typer(add_completion=False, no_args_is_help=False)

CANDIDATE: str = "tuned-winner"
BASELINES: tuple[str, ...] = ("aco-vanilla", "heuristic-only", "backtracking")


def _solve_counts(df: pl.DataFrame) -> dict[str, int]:
    agg = aggregate(df)
    out: dict[str, int] = {}
    for cond in (CANDIDATE, *BASELINES):
        sub = agg.filter(pl.col("condition") == cond)
        out[cond] = int(sub["solved_any"].sum()) if not sub.is_empty() else 0
    return out


@app.command()
def main(out_dir: Path = Path("experiments/stage4/out")) -> None:
    """Aggregate Stage-4 results and emit a JSON report with one McNemar test."""
    configure_logging()
    out_dir.mkdir(parents=True, exist_ok=True)
    df = load_results(out_dir / "results.parquet")
    agg = aggregate(df)
    agg.write_parquet(out_dir / "aggregate.parquet")

    counts = _solve_counts(df)
    strongest_baseline = max(BASELINES, key=lambda b: counts[b])

    primary = mcnemar_paired(df, baseline=strongest_baseline, candidate=CANDIDATE)
    secondary = [mcnemar_paired(df, baseline=b, candidate=CANDIDATE) for b in BASELINES if b != strongest_baseline]

    report: dict[str, Any] = {
        "by_condition_solve_counts": counts,
        "strongest_baseline": strongest_baseline,
        "primary_mcnemar": asdict(primary),
        "secondary_mcnemar": [asdict(r) for r in secondary],
    }
    (out_dir / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    logger.info(
        "Stage-4 primary: {} vs {} -> n={} b={} c={} stat={:.3f} sig={} ({})",
        CANDIDATE,
        strongest_baseline,
        primary.n,
        primary.b,
        primary.c,
        primary.statistic,
        primary.significant,
        primary.decision,
    )


if __name__ == "__main__":
    app()
