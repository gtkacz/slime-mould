"""Command-line entrypoints for zipmould.

Subcommands:
  * ``solve``     : run a single puzzle through one condition
  * ``inspect``   : print summary metadata for a puzzle id
  * ``run-stage`` : alias to ``experiments.stage1.run`` for convenience
"""

from __future__ import annotations

import importlib
import json
from collections.abc import Callable
from pathlib import Path
from typing import Annotated, Any

import typer
from loguru import logger

from zipmould.config import SolverConfig
from zipmould.io.puzzles import load_corpus
from zipmould.logging_config import configure_logging

app = typer.Typer(no_args_is_help=True, add_completion=False)

_DEFAULT_VIZ_HOST = "127.0.0.1"
_DEFAULT_VIZ_PORT = 8000

viz_app = typer.Typer(no_args_is_help=True, help="Visualizer commands.")
app.add_typer(viz_app, name="viz")


@viz_app.command("serve")
def viz_serve_cmd(
    host: Annotated[str, typer.Option(help="Bind host.")] = _DEFAULT_VIZ_HOST,
    port: Annotated[int, typer.Option(help="Bind port.")] = _DEFAULT_VIZ_PORT,
    reload: Annotated[bool, typer.Option(help="Enable uvicorn auto-reload.")] = False,
) -> None:
    """Run the FastAPI visualizer server."""
    import uvicorn

    configure_logging()
    uvicorn.run(
        "zipmould.viz.server:create_app",
        host=host,
        port=port,
        factory=True,
        reload=reload,
    )


_CONDITION_TO_SOLVER: dict[str, str] = {
    "zipmould-uni-signed": "zipmould.solver.api:solve",
    "zipmould-uni-positive": "zipmould.solver.api:solve",
    "zipmould-strat-signed": "zipmould.solver.api:solve",
    "zipmould-strat-positive": "zipmould.solver.api:solve",
    "aco-vanilla": "zipmould.baselines.aco_vanilla:solve",
    "heuristic-only": "zipmould.baselines.heuristic_only:solve",
    "random": "zipmould.baselines.random_walk:solve",
    "backtracking": "zipmould.baselines.backtracking:solve",
}


def _resolve_solver(condition: str) -> Callable[..., Any]:
    """Map a condition name to a callable matching the solver protocol."""
    if condition not in _CONDITION_TO_SOLVER:
        msg = f"unknown condition {condition!r}"
        raise typer.BadParameter(msg)
    mod_name, attr = _CONDITION_TO_SOLVER[condition].split(":")
    return getattr(importlib.import_module(mod_name), attr)  # pyright: ignore[reportAny]


@app.command("solve")
def solve_cmd(
    puzzle_id: Annotated[str, typer.Argument(help="Puzzle identifier from the CBOR corpus.")],
    condition: Annotated[
        str, typer.Option(help="Experimental condition; matches configs/ablations/<name>.toml.")
    ] = "zipmould-uni-signed",
    seed: Annotated[int, typer.Option(help="Run seed.")] = 0,
    global_seed: Annotated[int, typer.Option(help="Experiment-wide global seed.")] = 0,
    trace: Annotated[bool, typer.Option(help="Emit a CBOR trace next to the result.")] = False,
    config_path: Annotated[
        Path | None,
        typer.Option("--config", help="Override TOML config; defaults to configs/ablations/<condition>.toml."),
    ] = None,
    out: Annotated[Path | None, typer.Option(help="Optional output path for the JSON RunResult summary.")] = None,
) -> None:
    """Solve a single puzzle under the named condition."""
    configure_logging()
    cfg_path = config_path or Path(f"configs/ablations/{condition}.toml")
    cfg = SolverConfig.from_toml(cfg_path)
    corpus = load_corpus()
    if puzzle_id not in corpus:
        msg = f"puzzle_id {puzzle_id!r} not in corpus"
        raise typer.BadParameter(msg)
    puzzle = corpus[puzzle_id]
    solver = _resolve_solver(condition)
    logger.info("Solving {} under {} (seed={}, global_seed={})", puzzle_id, condition, seed, global_seed)
    result = solver(puzzle, cfg, seed=seed, trace=trace, global_seed=global_seed, condition=condition)
    summary = {
        "puzzle_id": puzzle_id,
        "condition": condition,
        "seed": seed,
        "solved": result.solved,
        "infeasible": result.infeasible,
        "best_fitness": result.best_fitness,
        "best_fitness_normalised": result.best_fitness_normalised,
        "iters_used": result.iters_used,
        "wall_clock_s": result.wall_clock_s,
        "config_hash": result.config_hash,
        "git_sha": result.git_sha,
        "git_dirty": result.git_dirty,
    }
    text = json.dumps(summary, indent=2, sort_keys=True)
    typer.echo(text)
    if out is not None:
        out.write_text(text + "\n", encoding="utf-8")


@app.command("inspect")
def inspect_cmd(
    puzzle_id: Annotated[str, typer.Argument(help="Puzzle identifier.")],
) -> None:
    """Print summary metadata for a single puzzle."""
    configure_logging()
    corpus = load_corpus()
    if puzzle_id not in corpus:
        msg = f"puzzle_id {puzzle_id!r} not in corpus"
        raise typer.BadParameter(msg)
    pz = corpus[puzzle_id]
    typer.echo(
        json.dumps(
            {
                "puzzle_id": pz.id,
                "name": pz.name,
                "N": pz.N,
                "K": pz.K,
                "L": pz.L(),
                "blocked": len(pz.blocked),
                "walls": len(pz.walls),
                "difficulty": pz.difficulty,
            },
            indent=2,
            sort_keys=True,
        )
    )


@app.command("run-stage")
def run_stage_cmd(
    stage: Annotated[str, typer.Argument(help="Stage identifier; only 'stage1' is supported initially.")],
    workers: Annotated[int, typer.Option(help="joblib worker count; -1 = all cores.")] = -1,
    out_dir: Annotated[Path, typer.Option(help="Output directory for results.parquet and traces/.")] = Path(
        "experiments/stage1/out"
    ),
) -> None:
    """Dispatch a multi-condition experiment stage."""
    configure_logging()
    if stage != "stage1":
        msg = "only 'stage1' is supported"
        raise typer.BadParameter(msg)
    runner = importlib.import_module("experiments.stage1.run")
    runner.main(workers=workers, out_dir=out_dir)  # pyright: ignore[reportAny]


def main() -> None:
    """Console-script entrypoint."""
    app()


if __name__ == "__main__":
    main()
