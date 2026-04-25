"""Stage-2 dev gate: confirm tuned configs do not regress vs Stage-1 defaults.

Spec §4. For each variant:
  1. Load the variant's best params from its Optuna study.
  2. Materialize and persist the tuned SolverConfig to
     ``configs/tuned/<variant>.toml``.
  3. Evaluate the tuned config on the dev split (10 seeds x 37 puzzles).
  4. Compare against the Stage-1 default count from
     ``experiments/stage1/out/results.parquet``.
  5. If tuned >= default, lock the tuned config; else fall back.
"""

from __future__ import annotations

import json
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path

import optuna  # pyright: ignore[reportMissingTypeStubs]
import polars as pl
import typer
from loguru import logger

from experiments.stage2.objective import evaluate
from experiments.stage2.search_space import PINNED_GLOBAL, VARIANT_PINS
from zipmould.config import SolverConfig
from zipmould.io.puzzles import load_split
from zipmould.logging_config import configure_logging

app = typer.Typer(add_completion=False, no_args_is_help=False)

DEV_SEEDS: list[int] = list(range(10))


@dataclass(frozen=True, slots=True)
class GateResult:
    variant: str
    tuned_solved: int
    default_solved: int
    n_trials_total: int
    decision: str
    locked_config_path: str


def _params_to_toml(params: dict[str, float | int], variant: str) -> str:
    """Render a tuned SolverConfig back to TOML for archival under configs/tuned/."""
    body: dict[str, object] = {**PINNED_GLOBAL, **VARIANT_PINS[variant], **params}
    cfg = SolverConfig.model_validate(body)
    dumped = cfg.model_dump(mode="json")
    lines = ["[solver]"]
    for k, v in sorted(dumped.items()):
        if isinstance(v, str):
            lines.append(f'{k} = "{v}"')
        elif isinstance(v, bool):
            lines.append(f"{k} = {'true' if v else 'false'}")
        else:
            lines.append(f"{k} = {v}")
    return "\n".join(lines) + "\n"


def _default_solved_from_stage1(variant: str, parquet_path: Path) -> int:
    # Counts (puzzle, seed) pairs to match `evaluate(...)`'s grain so the
    # `tuned >= default` decision is apples-to-apples.
    df = pl.read_parquet(str(parquet_path))
    sub = df.filter((pl.col("condition") == variant) & (~pl.col("failed")))
    return int(sub["solved"].sum())


@app.command()
def main(
    manifest_path: Path = Path("experiments/stage2/manifest.toml"),
    studies_dir: Path = Path("experiments/stage2/out"),
    tuned_dir: Path = Path("configs/tuned"),
    stage1_parquet: Path = Path("experiments/stage1/out/results.parquet"),
    out_dir: Path = Path("experiments/stage2/out"),
) -> None:
    """Run the dev gate for every variant; persist tuned configs and a JSON report."""
    configure_logging()
    out_dir.mkdir(parents=True, exist_ok=True)
    tuned_dir.mkdir(parents=True, exist_ok=True)

    manifest = tomllib.loads(manifest_path.read_text(encoding="utf-8"))
    global_seed: int = int(manifest["global_seed"])
    dev_ids: list[str] = load_split("dev")

    results: list[GateResult] = []
    for v in manifest["variants"]:
        name = str(v["name"])
        study_path = studies_dir / f"study_{name}.db"
        if not study_path.exists():
            logger.warning("missing study for {}; skipping", name)
            continue
        storage = f"sqlite:///{study_path.as_posix()}"
        study = optuna.load_study(  # pyright: ignore[reportUnknownMemberType]
            study_name=f"zipmould-stage2-{name}",
            storage=storage,
        )
        best = dict(study.best_params)

        body: dict[str, object] = {**PINNED_GLOBAL, **VARIANT_PINS[name], **best}
        tuned_cfg = SolverConfig.model_validate(body)

        tuned_solved = evaluate(
            tuned_cfg,
            dev_ids,
            DEV_SEEDS,
            variant=name,
            global_seed=global_seed,
        )
        default_solved = _default_solved_from_stage1(name, stage1_parquet)

        if tuned_solved >= default_solved:
            decision = "locked: tuned >= default"
            toml_text = _params_to_toml(best, name)
        else:
            decision = "reverted: tuned < default"
            default_cfg = SolverConfig.from_toml(Path("configs/default.toml")).model_copy(
                update=VARIANT_PINS[name],  # type: ignore[arg-type]
            )
            toml_text = _params_to_toml(
                {k: v for k, v in default_cfg.model_dump(mode="json").items() if k in best},
                name,
            )

        config_path = tuned_dir / f"{name}.toml"
        config_path.write_text(toml_text, encoding="utf-8")

        gate = GateResult(
            variant=name,
            tuned_solved=tuned_solved,
            default_solved=default_solved,
            n_trials_total=len(study.trials),
            decision=decision,
            locked_config_path=str(config_path),
        )
        results.append(gate)
        logger.info(
            "dev-gate {}: tuned={} default={} -> {}",
            name,
            tuned_solved,
            default_solved,
            decision,
        )

    report_path = out_dir / "dev_gate.json"
    report_path.write_text(
        json.dumps([asdict(r) for r in results], indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    logger.info("dev-gate report -> {}", report_path)


if __name__ == "__main__":
    app()
