# ZipMould Stage 2 + Stage 4 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tune all four ZipMould variants on the train split via Optuna TPE, validate non-regression on dev, and run a single-shot McNemar test on the held-out test split against `heuristic-only`, `aco-vanilla`, and `backtracking`.

**Architecture:** Two new experiment packages mirroring `experiments/stage1/` — `experiments/stage2/` (Optuna study + dev gate + analysis) and `experiments/stage4/` (test-set dispatcher + McNemar analysis). Tuned configs land under `configs/tuned/`. Search uses Optuna's SQLite backend so studies are resumable.

**Tech Stack:** Optuna 4.x (TPE sampler, SQLite storage), joblib (parallel run dispatch), Polars (results aggregation), Pydantic v2 (`SolverConfig`), Numba (kernel — already cached). Per project rules: `uv` for all Python invocations, `ruff`/`ty`/`pyright`/`bandit` static gates.

**Spec:** `docs/superpowers/specs/2026-04-25-zipmould-stage2-stage4-design.md`

---

### Task 1: Add Optuna dependency

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Add `optuna` to `[dependencies]`**

Open `/home/gtkacz/Codes/slime-mould/pyproject.toml` and append `"optuna>=4.0,<5",` to the `dependencies` list. Final list should look like:

```toml
dependencies = [
    "cbor2>=5.9,<6",
    "numpy>=2.4,<3",
    "numba>=0.65,<0.66",
    "pydantic>=2.13,<3",
    "polars>=1.40,<2",
    "joblib>=1.5,<2",
    "typer>=0.15,<1",
    "tqdm>=4.67,<5",
    "loguru>=0.7.3,<0.8",
    "optuna>=4.0,<5",
]
```

- [ ] **Step 2: Sync dependencies**

Run: `uv sync`
Expected: Resolves and installs `optuna` plus its transitive deps (`alembic`, `sqlalchemy`, `colorlog`, `PyYAML`).

- [ ] **Step 3: Smoke-import Optuna**

Run: `uv run python -c "import optuna; print(optuna.__version__)"`
Expected: prints a version `4.x.y` and exits 0.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "chore(deps): add optuna for Stage-2 hyperparameter tuning"
```

---

### Task 2: Create Stage 2 package skeleton and manifest

**Files:**
- Create: `experiments/stage2/__init__.py`
- Create: `experiments/stage2/manifest.toml`

- [ ] **Step 1: Create the package init**

Write `/home/gtkacz/Codes/slime-mould/experiments/stage2/__init__.py`:

```python
"""Stage-2 hyperparameter tuning for ZipMould variants.

Per docs/superpowers/specs/2026-04-25-zipmould-stage2-stage4-design.md:
runs Optuna TPE searches on the train split for all four variants,
followed by a dev-set non-regression gate.
"""
```

- [ ] **Step 2: Create the manifest**

Write `/home/gtkacz/Codes/slime-mould/experiments/stage2/manifest.toml`:

```toml
# Stage-2 manifest: hyperparameter tuning grid.
#
# Per spec §3, tunes 4 variants on the train split. Each variant
# gets an independent Optuna TPE study with `n_trials` trials.
# Each trial evaluates over `seeds` x train_split runs.

stage = "stage2"
split = "train"
seeds = [0, 1, 2, 3, 4]
n_trials = 50
n_startup_trials = 10
sampler_seed = 42
global_seed = 0

[[variants]]
name = "zipmould-uni-signed"
pheromone_mode = "unified"
tau_signed = true

[[variants]]
name = "zipmould-uni-positive"
pheromone_mode = "unified"
tau_signed = false

[[variants]]
name = "zipmould-strat-signed"
pheromone_mode = "stratified"
tau_signed = true

[[variants]]
name = "zipmould-strat-positive"
pheromone_mode = "stratified"
tau_signed = false
```

- [ ] **Step 3: Verify manifest parses**

Run: `uv run python -c "import tomllib, pathlib; print(tomllib.loads(pathlib.Path('experiments/stage2/manifest.toml').read_text()))"`
Expected: prints a dict with `stage`, `split`, `seeds`, `n_trials`, and a `variants` list of length 4. Exits 0.

- [ ] **Step 4: Commit**

```bash
git add experiments/stage2/__init__.py experiments/stage2/manifest.toml
git commit -m "feat(stage2): manifest and package skeleton"
```

---

### Task 3: Search-space module

**Files:**
- Create: `experiments/stage2/search_space.py`

- [ ] **Step 1: Write the search space module**

Write `/home/gtkacz/Codes/slime-mould/experiments/stage2/search_space.py`:

```python
"""Optuna search space for Stage-2 ZipMould tuning.

Per spec §2, defines 9 tunable knobs and the per-variant pinned
parameters. ``build_config`` consumes an Optuna ``Trial`` and returns
a fully-validated ``SolverConfig`` with the variant's structural
choices baked in.
"""

from __future__ import annotations

from typing import Final

import optuna  # pyright: ignore[reportMissingTypeStubs]

from zipmould.config import SolverConfig

PINNED_GLOBAL: Final[dict[str, object]] = {
    "iter_cap": 200,
    "wall_clock_s": 300.0,
    "tau_0": 0.0,
    "beta1": "N_squared",
    "beta2": 1.0,
    "beta3": "10_N_squared",
    "visible_walkers": 5,
    "frame_interval": 5,
    "tau_delta_epsilon": 1e-3,
}

VARIANT_PINS: Final[dict[str, dict[str, object]]] = {
    "zipmould-uni-signed": {"pheromone_mode": "unified", "tau_signed": True},
    "zipmould-uni-positive": {"pheromone_mode": "unified", "tau_signed": False},
    "zipmould-strat-signed": {"pheromone_mode": "stratified", "tau_signed": True},
    "zipmould-strat-positive": {"pheromone_mode": "stratified", "tau_signed": False},
}


def build_config(trial: optuna.Trial, variant: str) -> SolverConfig:
    """Materialize a SolverConfig for a single Optuna trial."""
    if variant not in VARIANT_PINS:
        msg = f"unknown variant {variant!r}; expected one of {sorted(VARIANT_PINS)}"
        raise ValueError(msg)

    sampled: dict[str, object] = {
        "gamma_man": trial.suggest_float("gamma_man", 0.1, 4.0, log=True),
        "gamma_warns": trial.suggest_float("gamma_warns", 0.1, 4.0, log=True),
        "gamma_art": trial.suggest_float("gamma_art", 0.1, 4.0, log=True),
        "gamma_par": trial.suggest_float("gamma_par", 0.0, 2.0, log=False),
        "alpha": trial.suggest_float("alpha", 0.1, 4.0, log=True),
        "beta": trial.suggest_float("beta", 0.1, 4.0, log=True),
        "z": trial.suggest_float("z", 0.0, 0.5, log=False),
        "tau_max": trial.suggest_float("tau_max", 1.0, 50.0, log=True),
        "population": trial.suggest_int("population", 10, 60),
    }

    body: dict[str, object] = {**PINNED_GLOBAL, **VARIANT_PINS[variant], **sampled}
    return SolverConfig.model_validate(body)
```

- [ ] **Step 2: Smoke-verify the search space**

Run:

```bash
uv run python -c "
import optuna
from experiments.stage2.search_space import build_config, VARIANT_PINS
study = optuna.create_study(direction='maximize')
trial = study.ask()
cfg = build_config(trial, 'zipmould-uni-signed')
assert cfg.pheromone_mode == 'unified'
assert cfg.tau_signed is True
assert cfg.iter_cap == 200
assert 0.1 <= cfg.gamma_man <= 4.0
print('OK', cfg.config_hash())
"
```

Expected: prints `OK <16-hex-digest>` and exits 0.

- [ ] **Step 3: Commit**

```bash
git add experiments/stage2/search_space.py
git commit -m "feat(stage2): Optuna search space for 9 tunable knobs"
```

---

### Task 4: Per-trial objective function

**Files:**
- Create: `experiments/stage2/objective.py`

- [ ] **Step 1: Write the objective module**

Write `/home/gtkacz/Codes/slime-mould/experiments/stage2/objective.py`:

```python
"""Per-trial objective: count solved (puzzle, seed) pairs on a split.

Spec §3.2. Dispatches `len(seeds) * len(puzzle_ids)` runs through
``zipmould.solver.api.solve`` via joblib and returns the integer
count of solved pairs. Worker exceptions are caught and treated as
``solved=False`` so a single crashing puzzle does not abort a trial.
"""

from __future__ import annotations

from typing import Final

from joblib import Parallel, delayed  # pyright: ignore[reportMissingTypeStubs]
from loguru import logger

from zipmould.config import SolverConfig
from zipmould.io.puzzles import load_corpus
from zipmould.puzzle import Puzzle
from zipmould.solver.api import solve

CONDITION_PREFIX: Final[str] = "stage2-trial"


def _run_one(
    puzzle: Puzzle,
    config: SolverConfig,
    seed: int,
    global_seed: int,
    variant: str,
) -> bool:
    try:
        result = solve(
            puzzle,
            config,
            seed=seed,
            trace=False,
            global_seed=global_seed,
            condition=f"{CONDITION_PREFIX}-{variant}",
        )
    except Exception as exc:  # tolerate kernel/feasibility surprises
        logger.opt(exception=exc).debug(
            "trial worker failed: variant={} puzzle={} seed={}",
            variant,
            puzzle.id,
            seed,
        )
        return False
    return bool(result.solved)


def evaluate(
    config: SolverConfig,
    puzzle_ids: list[str],
    seeds: list[int],
    *,
    variant: str,
    global_seed: int,
    n_jobs: int = -1,
) -> int:
    """Return number of solved (puzzle, seed) pairs for ``config`` over the given grid."""
    corpus = load_corpus()
    puzzles = [corpus[pid] for pid in puzzle_ids]

    flags: list[bool] = Parallel(n_jobs=n_jobs, backend="loky", verbose=0)(  # pyright: ignore[reportUnknownVariableType, reportAssignmentType]
        delayed(_run_one)(p, config, s, global_seed, variant)  # pyright: ignore[reportUnknownArgumentType]
        for p in puzzles
        for s in seeds
    )
    return int(sum(flags))
```

- [ ] **Step 2: Smoke-verify on dev split with default config**

Run:

```bash
uv run python -c "
from zipmould.config import SolverConfig
from zipmould.io.puzzles import load_split
from experiments.stage2.objective import evaluate
cfg = SolverConfig.from_toml(__import__('pathlib').Path('configs/default.toml')).model_copy(update={'pheromone_mode': 'unified', 'tau_signed': True})
ids = load_split('dev')[:5]
solved = evaluate(cfg, ids, [0, 1], variant='zipmould-uni-signed', global_seed=0, n_jobs=2)
print('solved:', solved, 'of', len(ids) * 2)
assert 0 <= solved <= len(ids) * 2
"
```

Expected: prints e.g. `solved: 7 of 10` and exits 0.

- [ ] **Step 3: Commit**

```bash
git add experiments/stage2/objective.py
git commit -m "feat(stage2): joblib-parallel objective counting solved pairs"
```

---

### Task 5: Tune driver

**Files:**
- Create: `experiments/stage2/tune.py`

- [ ] **Step 1: Write the driver**

Write `/home/gtkacz/Codes/slime-mould/experiments/stage2/tune.py`:

```python
"""Stage-2 driver: per-variant Optuna TPE study.

Spec §3.3. Loads the manifest, iterates over variants, runs an
Optuna study per variant against the train split. Studies are
persisted under ``experiments/stage2/out/study_<variant>.db``
(SQLite) so a crash can be resumed via ``load_if_exists=True``.
"""

from __future__ import annotations

import tomllib
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
) -> "Any":
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
        logger.info("Stage-2 tuning {} ({} trials, {} train puzzles, {} seeds)", name, trials, len(train_ids), len(seeds))
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
        logger.info("Stage-2 done {}: best_value={}, best_params={}", name, study.best_value, study.best_params)


if __name__ == "__main__":
    app()
```

- [ ] **Step 2: Dry-run with one trial on one variant**

Run: `uv run python -m experiments.stage2.tune --variant zipmould-uni-signed --n-trials 1`

Expected: prints a tqdm progress bar to 1/1, logs `Stage-2 done zipmould-uni-signed: best_value=<int>, best_params={...}`, creates `experiments/stage2/out/study_zipmould-uni-signed.db`. Exits 0.

- [ ] **Step 3: Verify the study persists and is resumable**

Run:

```bash
uv run python -c "
import optuna
s = optuna.load_study(study_name='zipmould-stage2-zipmould-uni-signed', storage='sqlite:///experiments/stage2/out/study_zipmould-uni-signed.db')
print('trials:', len(s.trials), 'best_value:', s.best_value)
assert len(s.trials) >= 1
"
```

Expected: prints `trials: 1 best_value: <int>`. Exits 0.

- [ ] **Step 4: Commit**

```bash
git add experiments/stage2/tune.py
git commit -m "feat(stage2): per-variant Optuna TPE driver with SQLite resume"
```

---

### Task 6: Dev gate module

**Files:**
- Create: `experiments/stage2/dev_gate.py`

- [ ] **Step 1: Write the dev-gate module**

Write `/home/gtkacz/Codes/slime-mould/experiments/stage2/dev_gate.py`:

```python
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
    df = pl.read_parquet(str(parquet_path))
    sub = df.filter((pl.col("condition") == variant) & (~pl.col("failed")))
    grouped = sub.group_by("puzzle_id").agg(pl.col("solved").any().alias("solved_any"))
    return int(grouped["solved_any"].sum())


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
        logger.info("dev-gate {}: tuned={} default={} -> {}", name, tuned_solved, default_solved, decision)

    report_path = out_dir / "dev_gate.json"
    report_path.write_text(
        json.dumps([asdict(r) for r in results], indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    logger.info("dev-gate report -> {}", report_path)


if __name__ == "__main__":
    app()
```

- [ ] **Step 2: Verify dev-gate module imports clean**

Run: `uv run python -c "from experiments.stage2.dev_gate import main, GateResult; print('OK')"`
Expected: prints `OK`. Exits 0.

- [ ] **Step 3: Commit**

```bash
git add experiments/stage2/dev_gate.py
git commit -m "feat(stage2): dev gate with non-regression check and TOML lock"
```

---

### Task 7: Stage 2 analyze module

**Files:**
- Create: `experiments/stage2/analyze.py`

- [ ] **Step 1: Write the analyze module**

Write `/home/gtkacz/Codes/slime-mould/experiments/stage2/analyze.py`:

```python
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
            }
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
```

- [ ] **Step 2: Smoke-import**

Run: `uv run python -c "from experiments.stage2.analyze import main; print('OK')"`
Expected: prints `OK`. Exits 0.

- [ ] **Step 3: Commit**

```bash
git add experiments/stage2/analyze.py
git commit -m "feat(stage2): winner-pick analysis aggregating study + dev gate"
```

---

### Task 8: Run Stage 2 (full)

**Files:** none modified — this is a data-producing run.

- [ ] **Step 1: Confirm clean tree before run**

Run: `git status --porcelain`
Expected: empty output (clean tree). If not, commit/stash first so `git_sha`/`git_dirty` on result rows are meaningful.

- [ ] **Step 2: Execute the full Stage-2 grid**

Run: `uv run python -m experiments.stage2.tune 2>&1 | tee /tmp/stage2_tune.log`
Expected: four tqdm progress bars (one per variant), each running 50 trials. `loguru` logs `Stage-2 done <variant>: best_value=<int>` four times. Total wall: a few minutes. Final exit code 0.

- [ ] **Step 3: Verify all four study DBs exist with 50 trials each**

Run:

```bash
uv run python -c "
import optuna
for v in ['zipmould-uni-signed', 'zipmould-uni-positive', 'zipmould-strat-signed', 'zipmould-strat-positive']:
    s = optuna.load_study(study_name=f'zipmould-stage2-{v}', storage=f'sqlite:///experiments/stage2/out/study_{v}.db')
    print(v, 'trials=', len(s.trials), 'best=', s.best_value)
    assert len(s.trials) == 50
"
```

Expected: prints four lines, each with `trials= 50` and a non-zero `best=`. Exits 0.

---

### Task 9: Run dev gate and pick winner

**Files:** none modified directly — produces `configs/tuned/*.toml`, `experiments/stage2/out/dev_gate.json`, `experiments/stage2/out/winner.json`.

- [ ] **Step 1: Run the dev gate**

Run: `uv run python -m experiments.stage2.dev_gate 2>&1 | tee /tmp/stage2_dev_gate.log`
Expected: four `loguru` log lines `dev-gate <variant>: tuned=N default=M -> locked|reverted`. `experiments/stage2/out/dev_gate.json` contains four entries. `configs/tuned/{uni-signed,uni-positive,strat-signed,strat-positive}.toml` all exist.

- [ ] **Step 2: Pick the overall winner**

Run: `uv run python -m experiments.stage2.analyze 2>&1 | tee /tmp/stage2_analyze.log`
Expected: writes `experiments/stage2/out/winner.json`, logs `Stage-2 winner: <variant> (dev_solved=N, default=M)`. Exits 0.

- [ ] **Step 3: Inspect the winner**

Run: `uv run python -c "import json,pathlib; print(json.dumps(json.loads(pathlib.Path('experiments/stage2/out/winner.json').read_text())['winner'], indent=2))"`
Expected: prints a JSON object with `variant`, `dev_solved`, `decision="locked: ..."` (or reverted), `locked_config_path`. The `variant` field identifies the Stage-4 candidate.

- [ ] **Step 4: Commit Stage 2 artifacts**

```bash
git add configs/tuned/ experiments/stage2/out/dev_gate.json experiments/stage2/out/winner.json
git commit -m "feat(stage2): tuned configs and dev-gate outputs"
```

(The Optuna SQLite files are kept locally but excluded — see Task 14 for `.gitignore` updates.)

---

### Task 10: Stage 4 package skeleton and manifest

**Files:**
- Create: `experiments/stage4/__init__.py`
- Create: `experiments/stage4/manifest.toml`

- [ ] **Step 1: Read the Stage-2 winner to wire the manifest**

Run: `uv run python -c "import json,pathlib; w=json.loads(pathlib.Path('experiments/stage2/out/winner.json').read_text())['winner']; print(w['variant'], w['locked_config_path'])"`
Expected: prints e.g. `zipmould-uni-signed configs/tuned/zipmould-uni-signed.toml`. Note both values for the next step.

- [ ] **Step 2: Create the package init**

Write `/home/gtkacz/Codes/slime-mould/experiments/stage4/__init__.py`:

```python
"""Stage-4 single-shot test evaluation.

Per docs/superpowers/specs/2026-04-25-zipmould-stage2-stage4-design.md:
30 seeds x 37 test puzzles x 4 conditions = 4,440 runs against the
held-out test split. One McNemar paired test against the strongest
baseline (expected: backtracking).
"""
```

- [ ] **Step 3: Create the manifest (substitute the winner config path from Step 1)**

Write `/home/gtkacz/Codes/slime-mould/experiments/stage4/manifest.toml` (replace `<WINNER_PATH>` with the path printed in Step 1, e.g. `configs/tuned/zipmould-uni-signed.toml`):

```toml
# Stage-4 manifest: held-out test evaluation.
#
# Per spec §5, runs the Stage-2-tuned winner against three baselines
# on the test split. One McNemar test, no peeking at test data
# during tuning.

stage = "stage4"
split = "test"
seeds = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29]
trace_seeds = [0]

[[conditions]]
name = "tuned-winner"
config = "<WINNER_PATH>"

[[conditions]]
name = "heuristic-only"
config = "configs/ablations/heuristic-only.toml"

[[conditions]]
name = "aco-vanilla"
config = "configs/ablations/aco-vanilla.toml"

[[conditions]]
name = "backtracking"
config = "configs/ablations/backtracking.toml"
```

- [ ] **Step 4: Verify manifest parses with the substituted path**

Run: `uv run python -c "import tomllib,pathlib; m=tomllib.loads(pathlib.Path('experiments/stage4/manifest.toml').read_text()); assert pathlib.Path(m['conditions'][0]['config']).exists(), m['conditions'][0]['config']; print('OK', m['conditions'][0]['config'])"`
Expected: prints `OK <path>`. Exits 0.

- [ ] **Step 5: Commit**

```bash
git add experiments/stage4/__init__.py experiments/stage4/manifest.toml
git commit -m "feat(stage4): manifest pinning Stage-2 winner against baselines"
```

---

### Task 11: Stage 4 dispatcher

**Files:**
- Create: `experiments/stage4/run.py`

- [ ] **Step 1: Write the dispatcher (mirrors `experiments/stage1/run.py` but with a `tuned-winner` row in the registry that resolves to the zipmould solver)**

Write `/home/gtkacz/Codes/slime-mould/experiments/stage4/run.py`:

```python
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
```

- [ ] **Step 2: Smoke-import**

Run: `uv run python -c "from experiments.stage4.run import main; print('OK')"`
Expected: prints `OK`. Exits 0.

- [ ] **Step 3: Commit**

```bash
git add experiments/stage4/run.py
git commit -m "feat(stage4): test-set dispatcher mirroring Stage-1 layout"
```

---

### Task 12: Stage 4 analyze module

**Files:**
- Create: `experiments/stage4/analyze.py`

- [ ] **Step 1: Write the analyze module**

Write `/home/gtkacz/Codes/slime-mould/experiments/stage4/analyze.py`:

```python
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
    secondary = [
        mcnemar_paired(df, baseline=b, candidate=CANDIDATE) for b in BASELINES if b != strongest_baseline
    ]

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
```

- [ ] **Step 2: Smoke-import**

Run: `uv run python -c "from experiments.stage4.analyze import main; print('OK')"`
Expected: prints `OK`. Exits 0.

- [ ] **Step 3: Commit**

```bash
git add experiments/stage4/analyze.py
git commit -m "feat(stage4): McNemar analysis against strongest test baseline"
```

---

### Task 13: Run Stage 4

**Files:** none modified — produces `experiments/stage4/out/results.parquet`, `summary.json`, `report.json`.

- [ ] **Step 1: Confirm clean tree**

Run: `git status --porcelain`
Expected: empty output. If not, commit pending work first so `git_sha` on result rows is meaningful.

- [ ] **Step 2: Execute Stage 4**

Run: `uv run python -m experiments.stage4.run 2>&1 | tee /tmp/stage4_run.log`
Expected: tqdm progress bar to 4440/4440 (4 conditions × 37 puzzles × 30 seeds), final log line `Stage-4 done: solved=N, failed=0`. `experiments/stage4/out/results.parquet` and `summary.json` exist.

- [ ] **Step 3: Run the analysis**

Run: `uv run python -m experiments.stage4.analyze 2>&1 | tee /tmp/stage4_analyze.log`
Expected: log line `Stage-4 primary: tuned-winner vs <baseline> -> n=37 b=B c=C stat=S sig=...`. `experiments/stage4/out/report.json` exists with `primary_mcnemar` populated.

- [ ] **Step 4: Inspect and commit results**

Run: `cat experiments/stage4/out/report.json`
Verify by-condition solve counts make sense (`tuned-winner` ≥ Stage-1 default by inspection; `backtracking` likely high).

```bash
git add experiments/stage4/out/summary.json experiments/stage4/out/report.json
git commit -m "feat(stage4): test-set evaluation results"
```

(`results.parquet` is excluded — see Task 14.)

---

### Task 14: Quality gates and gitignore

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: Append result-data globs to `.gitignore`**

Open `/home/gtkacz/Codes/slime-mould/.gitignore` and append:

```
# Stage-2/4 large or local-only artifacts
experiments/stage2/out/study_*.db
experiments/stage2/out/study_*.db-journal
experiments/stage2/out/aggregate.parquet
experiments/stage4/out/results.parquet
experiments/stage4/out/aggregate.parquet
experiments/stage4/out/traces/
```

- [ ] **Step 2: Run all static gates over the new code**

Run: `uv run ruff check src/ experiments/stage2/ experiments/stage4/`
Expected: `All checks passed!`

Run: `uv run ty check src/zipmould experiments/stage2 experiments/stage4`
Expected: 0 errors.

Run: `uv run pyright --strict experiments/stage2 experiments/stage4 src/zipmould`
Expected: 0 errors, 0 warnings (warnings on stub-less optuna are acceptable per pyproject `reportMissingTypeStubs="warning"`).

Run: `uv run bandit -r experiments/stage2 experiments/stage4`
Expected: no high-severity findings.

- [ ] **Step 3: Commit**

```bash
git add .gitignore
git commit -m "chore(stage2,stage4): exclude large artifacts; pass static gates"
```

---

### Task 15: Findings note

**Files:**
- Create: `docs/superpowers/findings/2026-04-25-stage2-stage4-results.md`

- [ ] **Step 1: Pull the headline numbers**

Run:

```bash
uv run python -c "
import json, pathlib
w = json.loads(pathlib.Path('experiments/stage2/out/winner.json').read_text())['winner']
g = json.loads(pathlib.Path('experiments/stage2/out/dev_gate.json').read_text())
r = json.loads(pathlib.Path('experiments/stage4/out/report.json').read_text())
print('WINNER:', w['variant'], 'dev_solved=', w['dev_solved'], 'default=', w['dev_default_solved'])
print('GATE_DECISIONS:', {row['variant']: row['decision'] for row in g})
print('TEST_COUNTS:', r['by_condition_solve_counts'])
print('PRIMARY:', r['primary_mcnemar'])
"
```

Expected: prints four lines summarizing the Stage-2/4 outcome. Note these for the next step.

- [ ] **Step 2: Write the findings note (substitute the numbers from Step 1)**

Write `/home/gtkacz/Codes/slime-mould/docs/superpowers/findings/2026-04-25-stage2-stage4-results.md` (with actual numbers substituted into the placeholders below):

```markdown
# Stage 2 + Stage 4 Results

**Date:** 2026-04-25
**Spec:** docs/superpowers/specs/2026-04-25-zipmould-stage2-stage4-design.md

## Stage 2 outcome

| Variant | Dev solved (tuned) | Dev solved (default) | Decision |
|---|---|---|---|
| zipmould-uni-signed | <N> | <M> | <decision> |
| zipmould-uni-positive | <N> | <M> | <decision> |
| zipmould-strat-signed | <N> | <M> | <decision> |
| zipmould-strat-positive | <N> | <M> | <decision> |

**Overall winner:** `<variant>` with dev_solved=<N>.

## Stage 4 outcome

| Condition | Test solved (of 37) |
|---|---|
| tuned-winner | <N> |
| heuristic-only | <N> |
| aco-vanilla | <N> |
| backtracking | <N> |

**Primary McNemar test** (`tuned-winner` vs `<strongest baseline>`): n=<n>, b=<b>, c=<c>, stat=<s>, significant=<bool>. **Decision:** <decision>.

## Notes

<one paragraph on what the result means for the algorithm, e.g.
"closes/does not close gap to backtracking", residual failure modes,
ideas for follow-up if the gap remains>.
```

- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/findings/2026-04-25-stage2-stage4-results.md
git commit -m "docs(stage2,stage4): findings note for tuned ZipMould vs baselines"
```
