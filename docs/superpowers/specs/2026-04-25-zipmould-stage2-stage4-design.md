# ZipMould Stage 2 + Stage 4 Design Spec

**Date:** 2026-04-25
**Status:** Approved (Section 1) → ready for implementation plan

## 0. Context and goal

Stage 1 is complete. The four ZipMould variants beat the three weak baselines (heuristic-only, aco-vanilla, random) per McNemar at p < 0.05 with the strongest variant (`zipmould-uni-signed`) winning by ~22 pp over heuristic-only. None of the four variants beats `backtracking` yet. The variants ranked tightly: uni-signed > strat-signed > strat-positive ≈ uni-positive, with a spread small enough that hyperparameter tuning can plausibly flip the order.

User priority: "make it actually work well" — i.e. close the gap to backtracking on test, not paper-defensibility. The pre-registered Stage-2 protocol in `docs/design.md` mandates 30 random train puzzles per trial and tuning a single locked-in variant. This spec deviates: tune all four variants on the **full** train split with the same trial budget, then test once on the held-out split.

## 1. Pipeline architecture (approved)

```
Stage 2 (tune)  →  Dev gate (validate)  →  Stage 4 (test, single shot)
 train split          dev split                test split
 171 puzzles          37 puzzles               37 puzzles
```

- **Stage 2** — independent Optuna TPE searches, one per variant family.
- **Dev gate** — confirm each tuned config does not regress on dev vs the Stage-1 default for that variant; pick the overall winner across the four families.
- **Stage 4** — single-shot test eval, `tuned-winner` against `heuristic-only`, `aco-vanilla`, `backtracking`. One McNemar test on test split, no hyperparameter peek.

## 2. Search space (approved)

9 knobs per variant, `iter_cap` held at the Stage-1 default of 200 to keep the dev gate apples-to-apples.

| Knob | Range | Scale | Optuna call |
|---|---|---|---|
| `gamma_man` | 0.1 – 4.0 | log | `suggest_float(..., log=True)` |
| `gamma_warns` | 0.1 – 4.0 | log | `suggest_float(..., log=True)` |
| `gamma_art` | 0.1 – 4.0 | log | `suggest_float(..., log=True)` |
| `gamma_par` | 0.0 – 2.0 | linear | `suggest_float(..., log=False)` |
| `alpha` | 0.1 – 4.0 | log | `suggest_float(..., log=True)` |
| `beta` | 0.1 – 4.0 | log | `suggest_float(..., log=True)` |
| `z` | 0.0 – 0.5 | linear | `suggest_float(..., log=False)` |
| `tau_max` | 1.0 – 50.0 | log | `suggest_float(..., log=True)` |
| `population` | 10 – 60 | int | `suggest_int(..., log=False)` |

Pinned per variant: `pheromone_mode` ∈ {`unified`, `stratified`}, `tau_signed` ∈ {`true`, `false`}. Pinned globally: `iter_cap=200`, `wall_clock_s=300.0`, `tau_0=0.0`, `beta1="N_squared"`, `beta2=1.0`, `beta3="10_N_squared"`, `visible_walkers=5`, `frame_interval=5`, `tau_delta_epsilon=0.001`.

## 3. Stage 2 — Optuna study

### 3.1 File layout

```
experiments/stage2/
├── __init__.py
├── manifest.toml          # variants, trial budget, seeds, trial-eval grid
├── search_space.py        # build_config(trial, variant) -> SolverConfig
├── objective.py           # evaluate(config, train_ids, seeds) -> float
├── tune.py                # driver: per-variant Optuna study
├── dev_gate.py            # validates tuned configs on dev
├── analyze.py             # aggregates studies, picks overall winner
└── out/                   # study DBs, tuned configs, JSON reports
```

### 3.2 Per-trial protocol

For each Optuna trial of a variant:

1. Sample 9 hyperparameters from the search space.
2. Materialize a `SolverConfig` with the variant's pinned `pheromone_mode` and `tau_signed`, plus the sampled knobs.
3. Dispatch `5 seeds × 171 train puzzles = 855` runs through `zipmould.solver.api.solve` via `joblib.Parallel(n_jobs=-1, backend="loky")`.
4. Objective: number of `(puzzle, seed)` pairs solved. Optuna maximizes.

Per-trial budget at observed 8.5 ms/run, sequential: ~7.3 s. With 16-core parallelism: ~0.5 s. With Numba JIT warmup amortized across the study, total Stage-2 wall is dominated by Optuna overhead, not solver runtime.

### 3.3 Study configuration

Per variant:

```python
import optuna

study = optuna.create_study(
    study_name=f"zipmould-stage2-{variant}",
    direction="maximize",
    storage=f"sqlite:///experiments/stage2/out/study_{variant}.db",
    load_if_exists=True,
    sampler=optuna.samplers.TPESampler(
        multivariate=True,
        n_startup_trials=10,
        seed=42,
    ),
)
study.optimize(objective_for(variant), n_trials=50, show_progress_bar=True)
```

50 trials per variant × 4 variants = 200 trials total, matching the original pre-reg compute budget but spread across the variant axis.

### 3.4 Trial seeds and global seed

Each trial uses fixed seeds `[0, 1, 2, 3, 4]` for evaluation; differences between trials come from the sampled hyperparameters (which change `cfg_hash` and therefore the kernel-derived seed via `derive_kernel_seed(global_seed, seed, puzzle_id, cfg_hash)`). This makes trials independent across the search but reproducible per (trial config, seed). `global_seed=0` for the entire Stage 2.

### 3.5 Failure handling

A worker exception during a trial yields `solved=False` for that `(puzzle, seed)` pair, mirroring Stage 1's failure-tolerant policy. Optuna sees a slightly worse objective and continues. A trial with all 855 evaluations crashing is still recorded (objective=0) so the search avoids that region.

## 4. Dev gate

After Stage 2 completes for a variant:

1. Pull `study.best_params`, materialize a `SolverConfig`, write it to `configs/tuned/<variant>.toml`.
2. Run the variant's tuned config on the dev split with the **same protocol as Stage 1**: 10 seeds × 37 dev puzzles = 370 runs.
3. Run the variant's Stage-1 default config on dev as well (or pull from `experiments/stage1/out/results.parquet` to avoid recompute).
4. Compare solved-any-per-puzzle counts:
   - **Pass (lock tuned)**: tuned solved ≥ default solved on dev.
   - **Fail (revert)**: tuned solved < default solved → fall back to Stage-1 default for that variant family.

Pick the **overall winner** across the four families: highest dev solved count after the gate, ties broken by lowest median `iters_used` on solved puzzles.

## 5. Stage 4 — test eval

### 5.1 File layout

```
experiments/stage4/
├── __init__.py
├── manifest.toml          # tuned-winner + 3 baselines, test split, 30 seeds
├── run.py                 # mirrors experiments/stage1/run.py
├── analyze.py             # single McNemar test
└── out/                   # results.parquet, report.json
```

### 5.2 Conditions

Four conditions only:

| Condition | Config |
|---|---|
| `tuned-winner` | `configs/tuned/<dev-gate-winner>.toml` |
| `heuristic-only` | `configs/ablations/heuristic-only.toml` |
| `aco-vanilla` | `configs/ablations/aco-vanilla.toml` |
| `backtracking` | `configs/ablations/backtracking.toml` |

`random` and the three non-winning ZipMould variants are not part of Stage 4 — Stage 1 already ranked them, no test-set peek is justified.

### 5.3 Protocol

- Seeds: `[0..29]` (30 seeds, per pre-reg).
- Puzzles: 37 test puzzles.
- Total runs: `30 × 37 × 4 = 4,440`.
- `global_seed=0` (same as Stage 1/2 to keep seed derivation consistent).
- Trace seeds: `[0]` only (mirror Stage 1).

### 5.4 Statistics

Single McNemar paired test on solved-any-per-puzzle: `tuned-winner` vs the strongest baseline on test (expected: `backtracking`). Report b, c, statistic, significance per `zipmould.metrics.mcnemar_paired`. The pre-registered conclusion rule from `docs/design.md` §10 is: significant if b > c **and** b > c + 1.96 √(b+c).

Secondary descriptive numbers (no second hypothesis test): condition-level solve counts, mean iters-to-solve, mean wall_ms.

## 6. Determinism, reproducibility, hashing

- `cfg_hash` (blake2b of canonical JSON of `SolverConfig`) is logged for every run; differences between Stage-1 and Stage-2 results are trivially traceable.
- Optuna study DB (`study_<variant>.db`) is committed-or-archived as the source of truth for which trial produced the locked config.
- `git_sha` and `git_dirty` are captured on every run row. Stage 4 runs MUST be on a clean tree.

## 7. Error handling

- Trial-level: any worker exception is caught at the joblib boundary, logged via `loguru`, and converted to `solved=False`. The trial proceeds.
- Study-level: Optuna's SQLite storage is resumable; if the driver dies, restart picks up where it left off via `load_if_exists=True`.
- Dev-gate-level: if Optuna found zero improvements (best == startup random), the gate reverts to default and logs `decision="reverted: tuned ≤ default"`.
- Stage-4-level: any failed run writes a `failed=True` row (Stage-1 pattern). The McNemar analysis treats failed rows as `solved=False` (conservative).

## 8. Dependencies

Add to `[dependencies]` in `pyproject.toml`:

```toml
"optuna>=4.0,<5",
```

Optuna's SQLite backend is via stdlib `sqlite3`; no extra deps. The TPE sampler ships with the core package.

## 9. Verification checklist

The implementation plan is complete when:

- [ ] `uv run python -m experiments.stage2.tune --variant zipmould-uni-signed --n-trials 1` produces `study_zipmould-uni-signed.db` with one trial.
- [ ] `uv run python -m experiments.stage2.tune` (all 4 variants × 50 trials) produces 4 study DBs.
- [ ] `uv run python -m experiments.stage2.dev_gate` writes `configs/tuned/<variant>.toml` for variants that pass the gate.
- [ ] `uv run python -m experiments.stage2.analyze` emits a JSON report identifying the overall winner.
- [ ] `uv run python -m experiments.stage4.run` writes `experiments/stage4/out/results.parquet` (4,440 rows).
- [ ] `uv run python -m experiments.stage4.analyze` writes `report.json` with the single McNemar result.
- [ ] All static gates pass: `ruff check`, `ty check`, `pyright --strict`, `bandit -r src/ experiments/`.

## 10. Out of scope

- Stage 3 (re-ablation) — pre-reg lists it as optional; skipping per user priority.
- Tuning `iter_cap` — held fixed; could be a stretch experiment if Stage 4 reveals depth-limited failure.
- Tuning the parameters held in string sentinels (`beta1="N_squared"`, `beta3="10_N_squared"`) — these are size-derived defaults, not free parameters.
- Cross-puzzle-size tuning (separate searches for small vs large grids) — the user has not requested it; full train coverage already sees the size distribution.
