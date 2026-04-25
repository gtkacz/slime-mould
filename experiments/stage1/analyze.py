"""Stage-1 analysis: aggregate results.parquet and print a decision report.

Applies the McNemar paired test from ``zipmould.metrics`` for every
ZipMould variant against each non-ZipMould baseline.  Prints a JSON
report and writes it to ``experiments/stage1/out/report.json``.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import polars as pl
from loguru import logger

from zipmould.logging_config import configure_logging
from zipmould.metrics import aggregate, load_results, mcnemar_paired

ZIPMOULD_VARIANTS: tuple[str, ...] = (
    "zipmould-uni-signed",
    "zipmould-uni-positive",
    "zipmould-strat-signed",
    "zipmould-strat-positive",
)
BASELINES: tuple[str, ...] = ("aco-vanilla", "heuristic-only", "random", "backtracking")


def main(out_dir: Path | str = Path("experiments/stage1/out")) -> None:
    """Aggregate Stage-1 results and emit JSON report."""
    configure_logging()
    out_dir_p = Path(out_dir)
    df = load_results(out_dir_p / "results.parquet")
    agg = aggregate(df)
    agg.write_parquet(out_dir_p / "aggregate.parquet")

    rows: list[dict[str, Any]] = []
    for variant in ZIPMOULD_VARIANTS:
        for baseline in BASELINES:
            r = mcnemar_paired(df, baseline=baseline, candidate=variant)
            rows.append(asdict(r))
            logger.info(
                "{} vs {}: n={} b={} c={} stat={:.3f} significant={} ({})",
                variant,
                baseline,
                r.n,
                r.b,
                r.c,
                r.statistic,
                r.significant,
                r.decision,
            )

    report = {
        "by_condition": (
            df.group_by("condition")
            .agg(
                solved=pl.col("solved").sum().cast(pl.Int64),
                failed=pl.col("failed").sum().cast(pl.Int64),
                total=pl.len(),
            )
            .sort("condition")
            .to_dicts()
        ),
        "mcnemar": rows,
    }
    (out_dir_p / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    logger.info("Wrote report to {}", out_dir_p / "report.json")


if __name__ == "__main__":
    main()
