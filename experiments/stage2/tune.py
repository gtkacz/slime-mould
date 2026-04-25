"""Stage-2 driver: per-variant Optuna TPE study.

Spec §3.3. Loads the manifest, iterates over variants, runs an
Optuna study per variant against the train split. Studies are
persisted under ``experiments/stage2/out/study_<variant>.db``
(SQLite) so a crash can be resumed via ``load_if_exists=True``.
"""

from __future__ import annotations

import tomllib
from collections.abc import Callable
from pathlib import Path
from typing import Any

import optuna  # pyright: ignore[reportMissingTypeStubs]
import typer
from loguru import logger
from optuna.samplers import TPESampler  # pyright: ignore[reportMissingTypeStubs]

from experiments.stage2.objective import evaluate
from experiments.stage2.search_space import build_config
from zipmould.io.puzzles import load_split
from zipmould.logging_config import configure_logging

app = typer.Typer(add_completion=False, no_args_is_help=False)


def _objective_for(
    variant: str,
    train_ids: list[str],
    seeds: list[int],
    global_seed: int,
) -> Callable[[optuna.Trial], int]:
    def _obj(trial: optuna.Trial) -> int:
        cfg = build_config(trial, variant)
        return evaluate(
            cfg,
            train_ids,
            seeds,
            variant=variant,
            global_seed=global_seed,
        )

    return _obj


@app.command()
def main(
    manifest_path: Path = Path("experiments/stage2/manifest.toml"),
    out_dir: Path = Path("experiments/stage2/out"),
    variant: str | None = typer.Option(None, help="Restrict to a single variant"),
    n_trials: int | None = typer.Option(None, help="Override n_trials from manifest"),
) -> None:
    """Run Optuna TPE studies for each variant declared in the manifest."""
    configure_logging()
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest = tomllib.loads(manifest_path.read_text(encoding="utf-8"))
    seeds: list[int] = list(map(int, manifest["seeds"]))
    train_ids: list[str] = load_split(str(manifest["split"]))
    sampler_seed: int = int(manifest["sampler_seed"])
    n_startup: int = int(manifest["n_startup_trials"])
    global_seed: int = int(manifest["global_seed"])
    trials: int = int(n_trials if n_trials is not None else manifest["n_trials"])

    variants: list[dict[str, Any]] = list(manifest["variants"])
    if variant is not None:
        variants = [v for v in variants if v["name"] == variant]
        if not variants:
            msg = f"variant {variant!r} not found in manifest"
            raise typer.BadParameter(msg)

    for v in variants:
        name = str(v["name"])
        logger.info(
            "Stage-2 tuning {} ({} trials, {} train puzzles, {} seeds)",
            name,
            trials,
            len(train_ids),
            len(seeds),
        )
        storage = f"sqlite:///{(out_dir / f'study_{name}.db').as_posix()}"
        study = optuna.create_study(  # pyright: ignore[reportUnknownMemberType]
            study_name=f"zipmould-stage2-{name}",
            direction="maximize",
            storage=storage,
            load_if_exists=True,
            sampler=TPESampler(multivariate=True, n_startup_trials=n_startup, seed=sampler_seed),
        )
        study.optimize(  # pyright: ignore[reportUnknownMemberType]
            _objective_for(name, train_ids, seeds, global_seed),
            n_trials=trials,
            show_progress_bar=True,
            gc_after_trial=True,
        )
        logger.info(
            "Stage-2 done {}: best_value={}, best_params={}",
            name,
            study.best_value,
            study.best_params,
        )


if __name__ == "__main__":
    app()
