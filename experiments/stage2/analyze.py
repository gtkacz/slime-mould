"""Stage-2 analysis: aggregate study DBs + dev-gate report into a winner pick.

Spec §4. Picks the overall Stage-2 winner across the four variant
families: highest dev-gate ``tuned_solved`` (after the gate), ties
broken by lowest median ``iters_used`` on solved dev puzzles.
Writes ``experiments/stage2/out/winner.json`` for Stage 4.
"""

from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import Any

import optuna  # pyright: ignore[reportMissingTypeStubs]
import polars as pl
import typer
from loguru import logger

from zipmould.logging_config import configure_logging

app = typer.Typer(add_completion=False, no_args_is_help=False)


def _median_iters_solved(parquet_path: Path, condition: str) -> float | None:
    if not parquet_path.exists():
        return None
    df = pl.read_parquet(str(parquet_path))
    sub = df.filter((pl.col("condition") == condition) & pl.col("solved"))
    if sub.is_empty():
        return None
    return float(sub["iters"].median())


@app.command()
def main(
    manifest_path: Path = Path("experiments/stage2/manifest.toml"),
    studies_dir: Path = Path("experiments/stage2/out"),
    dev_gate_path: Path = Path("experiments/stage2/out/dev_gate.json"),
    stage1_parquet: Path = Path("experiments/stage1/out/results.parquet"),
    out_dir: Path = Path("experiments/stage2/out"),
) -> None:
    """Pick the overall winner and emit ``winner.json`` + a study summary."""
    configure_logging()
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest = tomllib.loads(manifest_path.read_text(encoding="utf-8"))
    gate_rows: list[dict[str, Any]] = json.loads(dev_gate_path.read_text(encoding="utf-8"))
    by_variant = {row["variant"]: row for row in gate_rows}

    rankings: list[dict[str, Any]] = []
    for v in manifest["variants"]:
        name = str(v["name"])
        if name not in by_variant:
            continue
        gate = by_variant[name]
        median_iters = _median_iters_solved(stage1_parquet, name)

        study_path = studies_dir / f"study_{name}.db"
        n_trials = 0
        best_value: float | None = None
        if study_path.exists():
            storage = f"sqlite:///{study_path.as_posix()}"
            study = optuna.load_study(  # pyright: ignore[reportUnknownMemberType]
                study_name=f"zipmould-stage2-{name}",
                storage=storage,
            )
            n_trials = len(study.trials)
            best_value = float(study.best_value) if study.best_trial is not None else None

        rankings.append(
            {
                "variant": name,
                "dev_solved": int(gate["tuned_solved"]),
                "dev_default_solved": int(gate["default_solved"]),
                "decision": str(gate["decision"]),
                "median_iters_solved_stage1": median_iters,
                "study_n_trials": n_trials,
                "study_best_train_solved": best_value,
                "locked_config_path": str(gate["locked_config_path"]),
            },
        )

    rankings.sort(
        key=lambda r: (-int(r["dev_solved"]), float(r["median_iters_solved_stage1"] or 1e18)),
    )
    winner = rankings[0] if rankings else None

    report = {"rankings": rankings, "winner": winner}
    report_path = out_dir / "winner.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if winner is not None:
        logger.info(
            "Stage-2 winner: {} (dev_solved={}, default={})",
            winner["variant"],
            winner["dev_solved"],
            winner["dev_default_solved"],
        )
    else:
        logger.warning("Stage-2 produced no winner — dev_gate.json empty")


if __name__ == "__main__":
    app()
