"""Stage-4 dispatcher: held-out test eval.

Mirrors ``experiments/stage1/run.py`` with a 4-condition manifest
focused on the test split. The ``tuned-winner`` condition resolves
to ``zipmould.solver.api:solve``; baselines reuse the same solver
registry as Stage 1.
"""

from __future__ import annotations

import importlib
import json
import sys
import tomllib
import traceback
from collections.abc import Callable
from pathlib import Path
from typing import Any

import polars as pl
from joblib import Parallel, delayed  # pyright: ignore[reportMissingTypeStubs]
from loguru import logger
from tqdm import tqdm

from zipmould.config import SolverConfig
from zipmould.io.puzzles import load_corpus, load_split
from zipmould.io.trace import write_cbor
from zipmould.logging_config import configure_logging
from zipmould.solver.api import RunResult

_SOLVER_REGISTRY: dict[str, str] = {
    "tuned-winner": "zipmould.solver.api:solve",
    "aco-vanilla": "zipmould.baselines.aco_vanilla:solve",
    "heuristic-only": "zipmould.baselines.heuristic_only:solve",
    "backtracking": "zipmould.baselines.backtracking:solve",
}


def _resolve(name: str) -> Callable[..., RunResult]:
    mod_name, attr = _SOLVER_REGISTRY[name].split(":")
    return getattr(importlib.import_module(mod_name), attr)  # pyright: ignore[reportAny]


def _row_from_result(
    r: RunResult,
    *,
    puzzle_id: str,
    condition: str,
    seed: int,
    global_seed: int,
) -> dict[str, Any]:
    return {
        "puzzle_id": puzzle_id,
        "condition": condition,
        "seed": int(seed),
        "global_seed": int(global_seed),
        "config_hash": r.config_hash,
        "solved": bool(r.solved),
        "infeasible": bool(r.infeasible),
        "feasibility_reason": r.feasibility_reason,
        "best_fitness": float(r.best_fitness),
        "best_fitness_normalised": float(r.best_fitness_normalised),
        "iters": int(r.iters_used),
        "wall_ms": float(r.wall_clock_s * 1000.0),
        "failed": False,
        "failure_reason": None,
        "git_sha": r.git_sha,
        "git_dirty": bool(r.git_dirty),
    }


def _failed_row(
    *,
    puzzle_id: str,
    condition: str,
    seed: int,
    global_seed: int,
    config_hash: str,
    reason: str,
) -> dict[str, Any]:
    return {
        "puzzle_id": puzzle_id,
        "condition": condition,
        "seed": int(seed),
        "global_seed": int(global_seed),
        "config_hash": config_hash,
        "solved": False,
        "infeasible": False,
        "feasibility_reason": None,
        "best_fitness": 0.0,
        "best_fitness_normalised": 0.0,
        "iters": 0,
        "wall_ms": 0.0,
        "failed": True,
        "failure_reason": reason,
        "git_sha": "",
        "git_dirty": False,
    }


def _run_one(
    condition: str,
    config_path: str,
    puzzle_id: str,
    seed: int,
    global_seed: int,
    want_trace: bool,
    out_dir: str,
) -> dict[str, Any]:
    cfg = SolverConfig.from_toml(Path(config_path))
    try:
        corpus = load_corpus()
        puzzle = corpus[puzzle_id]
        solver = _resolve(condition)
        result: RunResult = solver(
            puzzle,
            cfg,
            seed=seed,
            trace=want_trace,
            global_seed=global_seed,
            condition=condition,
        )
        if want_trace and result.trace is not None:
            traces_dir = Path(out_dir) / "traces" / condition
            traces_dir.mkdir(parents=True, exist_ok=True)
            write_cbor(result.trace, traces_dir / f"{puzzle_id}__seed{seed}.cbor")
        return _row_from_result(
            result,
            puzzle_id=puzzle_id,
            condition=condition,
            seed=seed,
            global_seed=global_seed,
        )
    except Exception as exc:
        logger.opt(exception=exc).debug("worker failed: {} / {} / seed={}", condition, puzzle_id, seed)
        return _failed_row(
            puzzle_id=puzzle_id,
            condition=condition,
            seed=seed,
            global_seed=global_seed,
            config_hash=cfg.config_hash(),
            reason=f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}",
        )


def main(
    workers: int = -1,
    out_dir: Path | str = Path("experiments/stage4/out"),
    manifest_path: Path | str = Path("experiments/stage4/manifest.toml"),
    global_seed: int = 0,
) -> None:
    """Dispatch the Stage-4 grid and write results.parquet under out_dir."""
    configure_logging()
    out_dir_p = Path(out_dir)
    out_dir_p.mkdir(parents=True, exist_ok=True)
    manifest = tomllib.loads(Path(manifest_path).read_text(encoding="utf-8"))
    split_name = str(manifest["split"])
    seeds = list(map(int, manifest["seeds"]))
    trace_seeds = set(map(int, manifest.get("trace_seeds", [0])))
    conditions = manifest["conditions"]

    puzzle_ids = load_split(split_name)
    logger.info(
        "Stage-4: {} conditions x {} puzzles x {} seeds = {} jobs",
        len(conditions),
        len(puzzle_ids),
        len(seeds),
        len(conditions) * len(puzzle_ids) * len(seeds),
    )

    jobs: list[tuple[str, str, str, int, bool]] = []
    for cond in conditions:
        cname = str(cond["name"])
        cpath = str(cond["config"])
        jobs.extend((cname, cpath, pid, s, s in trace_seeds) for pid in puzzle_ids for s in seeds)

    rows: list[dict[str, Any]] = Parallel(n_jobs=workers, backend="loky", verbose=0)(  # pyright: ignore[reportUnknownVariableType, reportAssignmentType]
        delayed(_run_one)(c, p, pid, s, global_seed, t, str(out_dir_p))  # pyright: ignore[reportUnknownArgumentType]
        for (c, p, pid, s, t) in tqdm(jobs, desc="stage4", file=sys.stderr)
    )

    df = pl.DataFrame(rows)
    df.write_parquet(out_dir_p / "results.parquet")
    summary = {
        "n_jobs": len(jobs),
        "n_failed": int(df["failed"].sum()),
        "n_solved": int(df["solved"].sum()),
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
    }
    (out_dir_p / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    logger.info("Stage-4 done: solved={}, failed={}", summary["n_solved"], summary["n_failed"])


if __name__ == "__main__":
    main()
