# ZipMould — Python Implementation Design

**Status:** Pre-implementation. This document specifies the Python implementation plan for the algorithm pre-registered in [`docs/design.md`](../../design.md).
**Scope:** Solver kernel, CLI, configuration, baselines, trace I/O, and Stage-1 dispatch. Visualization, Stage-2/3/4 follow-ups, and unit tests are out of scope here (tests will be authored in a separate, explicit pass per repo policy).
**Pre-registration relationship:** This document only fixes *implementation* choices; it does not modify any pre-registered hypothesis, baseline, split, or decision rule from `docs/design.md`. Where the two ever conflict, `docs/design.md` is canonical and this document must be amended.

---

## 1. Stack and Toolchain

### 1.1 Language and runtime

- **Python 3.13** (CPython, not free-threaded). 3.14 is rejected because Polars and joblib do not yet ship cp314 wheels at the time of writing; 3.13 is the highest version on which the entire library set has stable wheels.
- Package and environment management via **`uv`** (per repo policy). Lockfile is committed.

### 1.2 Hot-path acceleration

- **Numba 0.65.1** (`@njit(cache=True, fastmath=False)`) for the walker step, pheromone update, fitness, and heuristic components. `fastmath=False` is required because the heuristic uses `softplus` and pheromone updates accumulate signed reals; reordering or denormal flushing would cause non-reproducible runs.
- **NumPy 2.4.4** for all kernel-resident state; no Python objects cross the `@njit` boundary.

### 1.3 Configuration, I/O, parallelism

| Concern | Library | Purpose |
|---|---|---|
| Config schema | **Pydantic v2** (2.13.x) | Validate `SolverConfig` and `ExperimentManifest` from TOML |
| Config format | **`tomllib`** (stdlib) | Load TOML; no `tomli` dependency on 3.13 |
| Trace I/O | **`cbor2` 5.9** | Per `docs/design.md` §8 schema; binary, deterministic |
| Puzzle I/O | **`cbor2`** | Already used by `benchmark/scripts/parse_to_cbor.py` |
| Cross-run metrics | **Polars 1.40** | Aggregate Stage-1 Parquet → analysis tables |
| Parallel dispatch | **joblib 1.5.3** with `backend="loky"` | 2,960 embarrassingly-parallel runs in Stage 1 |
| CLI | **typer** | `zipmould solve`, `zipmould run-stage`, `zipmould inspect` |
| Progress | **tqdm** | Per-stage progress bars; quiet mode for CI |
| Logging | **loguru 0.7.3** | Single sink; stdlib `InterceptHandler` redirects every other library's logging into loguru |

### 1.4 Quality tooling

- **`ruff`** (latest 0.8.x) + **`ruff format`** for lint and format. Configuration extends repo-level `pyproject.toml` `[tool.ruff]`.
- **`ty`** (Astral, 0.0.32 beta) as the primary type checker for local feedback.
- **Pyright** (latest) as the CI backstop, since `ty` is pre-1.0 and ships breaking changes weekly. Both must pass in CI; either failing is a hard gate. This dual-checker strategy is reviewed on each `ty` minor release with the intent to drop Pyright once `ty` reaches 1.0.
- **`bandit`** for static security analysis on `src/zipmould/`.
- **`py-spy`** (sampling, no instrumentation) and **`scalene`** (line-level CPU + GPU + memory) for profiling.
- **`pytest`** + **`hypothesis`** declared as dev dependencies but no tests authored until explicitly requested.

### 1.5 Excluded libraries (with reasons)

- **PyPy:** rejected — `cpyext` overhead defeats NumPy/Polars C-extension calls.
- **Cython / pybind11 / Rust pyo3:** rejected — Numba covers the same hot-path use cases without a build step on consumers' machines.
- **Pandas:** rejected — Polars is faster, has stricter schema semantics, and matches the Parquet-based output format.
- **`structlog`:** rejected — `loguru` is the user-chosen logger.
- **MyPy:** rejected — `ty` is the user-chosen type checker; Pyright is the CI backstop.

---

## 2. Architecture

### 2.1 Two-layer hybrid

The solver uses a **two-layer hybrid** of an outer object-oriented boundary and an inner array-pure kernel:

- **Outer layer (Python objects, `dataclass(frozen=True, slots=True)`):** `Puzzle`, `SolverConfig`, `RunResult`, `Trace`, `FeasibilityReport`, `ExperimentManifest`. Lives in normal Python; readable, validateable, testable, and serialisable.
- **Inner layer (NumPy arrays inside `@njit` functions):** `KernelState` (a `NamedTuple` of arrays), the walker step, the pheromone update, the fitness evaluator, and each heuristic component. No `dict`, no `list`, no `str`, no Python `object` references inside the kernel.

A thin **packing/unpacking** function, `state.pack(puzzle, config) -> KernelState` and `api.unpack(KernelState, ...) -> RunResult`, is the only place the two layers meet. This boundary is JIT-friendly and keeps the kernel free of boxing overhead.

Rejected alternatives, with reasons:

- *Pure OO* (per-walker `Walker` instance): readable but cannot be `@njit`-compiled; ~50× slower in pilot estimates.
- *Pure array-oriented* (everything as flat arrays at module scope): fast but unergonomic for config validation, trace assembly, and CLI integration.

### 2.2 Determinism contract

- Single-run determinism: given `(puzzle_id, config_hash, global_seed, run_seed)`, `solve(...)` returns a `RunResult` with bitwise-equal `solution`, `iters_used`, and `best_fitness`. Wall-clock fields are excluded from the contract.
- Per-run RNG is built from a `numpy.random.SeedSequence` whose entropy is derived from `blake2b(global_seed_bytes || run_seed_bytes || puzzle_id_bytes || config_hash_bytes)`, so changing any input changes the seed deterministically and changing only the puzzle identity does not produce correlated streams.
- Numba caches are versioned by source hash; `cache=True` is safe because we never mutate compiled functions at runtime.

### 2.3 Reproducibility artefacts

Every run emits, in addition to the `RunResult`:

- The resolved `SolverConfig` (post-Pydantic validation, with derived defaults like `beta1 = N²` materialised) as a TOML blob.
- The `config_hash` (blake2b of the canonicalised TOML).
- The library versions (`numpy.__version__`, `numba.__version__`, `polars.__version__`, etc.) and Python version.
- The git commit SHA and a `dirty` flag.

These travel with both the Parquet aggregate and the per-run CBOR traces.

---

## 3. Module Layout

All new code lives under `src/zipmould/`. The existing `src/models/`, `src/enums/`, and `src/util/` trees are deleted (user-authorised) since they describe an incompatible shape (mutable cell objects, walls-as-cell-property) that does not match the array-based kernel. `benchmark/` is kept as-is except for swapping its logger calls to loguru.

```
src/zipmould/
├── __init__.py                 # Public re-exports: Puzzle, SolverConfig, RunResult, solve, Trace
├── puzzle.py                   # Puzzle, Coord, Edge dataclasses; load_puzzles_cbor()
├── config.py                   # SolverConfig, ExperimentManifest (Pydantic v2)
├── feasibility.py              # §3.9 prechecks; FeasibilityReport
├── rng.py                      # make_rng(global_seed, run_seed, puzzle_id, config_hash) -> Generator
├── logging_config.py           # configure_logging(); InterceptHandler for stdlib
├── fitness.py                  # @njit fitness per §3.6
├── solver/
│   ├── __init__.py
│   ├── api.py                  # solve(puzzle, config, *, seed, trace, ...) -> RunResult
│   ├── state.py                # KernelState NamedTuple; pack/unpack
│   ├── _kernel.py              # @njit walker loop + pheromone update (private)
│   └── _heuristics.py          # @njit Manhattan / Warnsdorff / articulation / parity
├── baselines/
│   ├── __init__.py
│   ├── random_walk.py          # Uniform-random over legal moves; same encoding
│   ├── heuristic_only.py       # ZipMould with τ frozen at τ₀
│   ├── aco_vanilla.py          # Classic ACS update, no SMA term
│   └── backtracking.py         # Exact, with parity + articulation prunes
├── io/
│   ├── __init__.py
│   ├── puzzles.py              # CBOR load; dataset split loader
│   └── trace.py                # Trace dataclass; write_cbor / read_cbor per §8
├── metrics.py                  # Polars aggregation: Parquet -> analysis tables
└── cli.py                      # typer CLI: solve / run-stage / inspect
```

```
experiments/
├── stage1/
│   ├── manifest.toml           # 8 conditions × 37 dev puzzles × 10 seeds = 2,960 jobs
│   ├── run.py                  # Loads manifest, dispatches via joblib
│   └── analyze.py              # Polars + McNemar paired test per §10
├── stage1_prime/               # Stub (config tuning); same shape
├── stage2/                     # Stub (test-set evaluation)
└── stage4/                     # Stub (cross-puzzle generalisation)
```

```
configs/
├── default.toml                # Defaults from docs/design.md §5 Table
├── ablations/                  # One file per Stage-1 condition
│   ├── zipmould-uni-signed.toml
│   ├── zipmould-uni-positive.toml
│   ├── zipmould-strat-signed.toml
│   ├── zipmould-strat-positive.toml
│   ├── aco-vanilla.toml
│   ├── heuristic-only.toml
│   ├── random.toml
│   └── backtracking.toml
```

`benchmark/` keeps its current shape; only `benchmark/scripts/parse_to_cbor.py` and `benchmark/scripts/generate_splits.py` are re-pointed at loguru.

---

## 4. Public API

### 4.1 `puzzle.py`

```python
Coord = tuple[int, int]                # (row, col)
Edge  = tuple[Coord, Coord]            # canonicalised so a < b lexicographically

@dataclass(frozen=True, slots=True)
class Puzzle:
    id: str
    name: str
    difficulty: Literal["Easy", "Medium", "Hard"]
    N: int                              # grid side
    K: int                              # number of waypoints
    waypoints: tuple[Coord, ...]        # in label order; len == K
    walls: frozenset[Edge]              # canonicalised
    blocked: frozenset[Coord]

    def free_cells(self) -> frozenset[Coord]: ...
    def L(self) -> int: ...             # = N*N - len(blocked)
```

### 4.2 `config.py`

```python
class SolverConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    # §3.3 heuristic exponents
    gamma_man:   float = 1.0
    gamma_warns: float = 1.0
    gamma_art:   float = 1.0
    gamma_par:   float = 0.5

    # §3.5 sampling
    alpha: float = 1.0
    beta:  float = 2.0

    # §3.7 SMA update; "N_squared" / "10_N_squared" resolve at validation time
    beta1:   float | Literal["N_squared"]    = "N_squared"
    beta2:   float                           = 1.0
    beta3:   float | Literal["10_N_squared"] = "10_N_squared"
    tau_max: float = 10.0
    z:       float = 0.05
    tau_0:   float = 0.0

    # §3.8 termination
    population:   int   = 30
    iter_cap:     int   = 200
    wall_clock_s: float = 300.0

    # Stratification flag (§3.7 alt)
    pheromone_mode: Literal["unified", "stratified"] = "unified"

    # Trace controls (§8)
    visible_walkers: int = 5
    frame_interval: int  = 5

    @classmethod
    def from_toml(cls, path: Path) -> "SolverConfig": ...
```

The string sentinels `"N_squared"` and `"10_N_squared"` exist so the published config is self-documenting (`beta1 = "N_squared"` survives serialisation and reads correctly to a human); they are materialised to floats inside `state.pack(puzzle, config)`, which is the single point at which the config and the puzzle's `N` meet.

### 4.3 `solver/api.py`

```python
def solve(
    puzzle: Puzzle,
    config: SolverConfig,
    *,
    seed: int,
    trace: bool = False,
    global_seed: int = 0,
    condition: str = "zipmould-uni-signed",
) -> RunResult: ...

@dataclass(frozen=True, slots=True)
class RunResult:
    solved: bool
    infeasible: bool
    feasibility_reason: str | None
    solution: tuple[Coord, ...] | None
    iters_used: int
    wall_clock_s: float
    best_fitness: float
    best_fitness_normalised: float        # f / L per §3.6
    trace: Trace | None
    config_hash: str
    versions: Mapping[str, str]
    git_sha: str
    git_dirty: bool
```

### 4.4 `solver/state.py`

```python
class KernelState(NamedTuple):
    L: int
    N2: int
    K: int
    E: int
    tau:               np.ndarray   # float32[E] or float32[K-1, E]
    pos:               np.ndarray   # int16[n_walkers]
    visited:           np.ndarray   # uint64[n_walkers, ceil(N²/64)]
    path:              np.ndarray   # int16[n_walkers, L]
    path_len:          np.ndarray   # int16[n_walkers]
    segment:           np.ndarray   # int8[n_walkers]
    status:            np.ndarray   # int8[n_walkers]: 0=alive,1=dead,2=done,3=error
    manhattan_table:   np.ndarray   # int16[N², K]
    parity_table:      np.ndarray   # int8[N²]
    adjacency:         np.ndarray   # int16[N², 4], -1 padded
    waypoint_cells:    np.ndarray   # int16[K]
    waypoint_of:       np.ndarray   # int8[N²], -1 if not waypoint
```

`pack(puzzle, config) -> KernelState` materialises any string sentinels (`"N_squared"` etc.) and precomputes `manhattan_table`, `parity_table`, `adjacency`, `waypoint_cells`, `waypoint_of`. `unpack(kernel_state, ...)` lifts the chosen walker's path back to `tuple[Coord, ...]` for `RunResult`.

### 4.5 `io/trace.py`

The dataclasses mirror the CBOR schema in `docs/design.md` §8 one-for-one. Field names follow the schema exactly (snake_case for keys, `version` for schema version) so the round-trip `Trace ↔ CBOR map` is an identity transform on field names.

```python
@dataclass(frozen=True, slots=True)
class Trace:
    version: int                                  # schema version, starts at 1
    puzzle_id: str
    config: Mapping[str, object]                  # resolved SolverConfig as a plain dict
    seed: int
    header: TraceHeader
    frames: tuple[Frame, ...]
    footer: TraceFooter

@dataclass(frozen=True, slots=True)
class TraceHeader:
    N: int
    K: int
    L: int
    waypoints: tuple[Coord, ...]
    walls: tuple[Edge, ...]
    blocked: tuple[Coord, ...]

@dataclass(frozen=True, slots=True)
class Frame:
    t: int                                        # iteration index
    v_b: float                                    # best-of-iteration fitness
    v_c: float                                    # iteration-mean fitness
    tau_delta: TauDelta                           # sparse delta from previous logged frame
    best: BestPath                                # best walker's path + fitness this iter
    walkers: tuple[WalkerSnapshot, ...]           # length capped at config.visible_walkers

@dataclass(frozen=True, slots=True)
class TauDelta:
    mode: Literal["unified", "stratified"]
    edges: tuple[tuple[int, int, float], ...]     # (edge_id, field_k, delta); field_k=-1 in unified

@dataclass(frozen=True, slots=True)
class BestPath:
    path: tuple[Coord, ...]
    fitness: float

@dataclass(frozen=True, slots=True)
class WalkerSnapshot:
    id: int
    cell: Coord
    segment: int
    status: Literal["alive", "dead-end", "complete"]
    fitness: float

@dataclass(frozen=True, slots=True)
class TraceFooter:
    solved: bool
    infeasible: bool
    solution: tuple[Coord, ...] | None
    iterations_used: int
    wall_clock_s: float
    best_fitness: float

def write_cbor(trace: Trace, path: Path) -> None: ...
def read_cbor(path: Path) -> Trace: ...
```

Pheromone is *delta-encoded* per `docs/design.md` §8: the first emitted frame logs the full τ array via `tau_delta` (every edge listed); subsequent frames log only edges whose absolute change since the last logged frame exceeds a configurable ε. This is the schema-mandated mechanism for keeping per-trace size in the 50–150 KB band cited in §8.

---

## 5. Data Flow

### 5.1 Single solve

```
solve(puzzle, config, seed=...)
  │
  ├── feasibility.precheck(puzzle) ──► FeasibilityReport
  │     └─ if infeasible: return RunResult(infeasible=True, reason=...)
  │
  ├── rng.make_rng(global_seed, seed, puzzle.id, config_hash) ──► np.random.Generator
  │
  ├── state.pack(puzzle, resolved_config) ──► KernelState
  │
  ├── solver._kernel.run(state, rng_state, ...) ──► (final_state, frames)
  │     # walker loop, pheromone update, frame logging — all @njit
  │
  └── api.unpack(final_state, frames, ...) ──► RunResult
```

The kernel never sees the `Puzzle` or `SolverConfig` Python objects; only their packed array form.

### 5.2 Stage-1 dispatch

```
ExperimentManifest (TOML)
  │  conditions: 8
  │  puzzles:    37 (dev split)
  │  seeds:      10
  │  total:      2,960 jobs
  ▼
joblib.Parallel(n_jobs=cpu_count - 1, backend="loky")(
    delayed(_one_run)(condition, puzzle, seed, global_seed)
    for ... in itertools.product(conditions, puzzles, seeds)
)
  │
  ├─► Per-job: write Parquet row (always) + write CBOR trace (only if seed == 0)
  │
  ▼
metrics.aggregate(parquet_dir) ──► analysis tables (Polars)
  │
  ▼
analyze.py ──► McNemar paired test, decision rule per docs/design.md §10
```

Trace volume justification: 296 traces × ~100 KB each ≈ 30 MB at seed 0 only (`docs/design.md` §8 estimates 50–150 KB per trace), versus ~300 MB if every seed of every run wrote a trace. The research question for Stage 1 is "does SMA help on average," answered from the Parquet aggregate alone; traces exist for the visualizer and for case studies, where one representative seed per condition×puzzle is sufficient. The seed-0 cohort is intentional, not random: it is the only seed value for which all conditions share an identical RNG entropy seed, which makes seed-0 traces directly comparable across conditions.

Each Parquet row carries: `condition, puzzle_id, seed, solved, infeasible, iters_used, wall_clock_s, best_fitness, best_fitness_normalised, failed, error_class, error_message, config_hash, git_sha, library_versions`.

The `failed=True` row is load-bearing: a Numba boxing error in 1 of 2,960 jobs must not crash the dispatcher, but it must be visible to the analyst. `failed=True` rows are excluded from the McNemar contingency table and reported separately as a quality metric.

---

## 6. Error Handling

Errors are categorised by boundary, with a single rule per boundary so the behaviour is predictable and grep-able.

| Boundary | Trigger | Behaviour |
|---|---|---|
| TOML → `SolverConfig` | Pydantic validation failure | Raise `ConfigError` (subclass of `ValueError`); CLI exits 2 with the validation report. |
| `feasibility.precheck` | Puzzle proven infeasible (parity, articulation, waypoint reachability) | Return `RunResult(solved=False, infeasible=True, reason=...)`; do not raise. Solver counts this as a legitimate non-solve. |
| Iteration cap reached | `iters_used == iter_cap` | Return `RunResult(solved=False, ...)`; not an error. |
| Wall-clock cap reached | Elapsed ≥ `wall_clock_s` | Same as iteration cap; check at the top of each iteration only. |
| Kernel `status==3` (error) | Numba assertion or out-of-range index | Raise `KernelError`; in Stage-1 dispatch this becomes `failed=True` row, not a process crash. |
| `joblib` worker exception | Anything uncaught inside `_one_run` | Caught by the dispatcher; written as `failed=True` row with `error_class` and `error_message`. |
| CBOR I/O failure | Disk full, permission denied, schema violation | Raise; do not silently fall back. Trace loss is a research-integrity issue. |
| Determinism violation | Re-running a logged `(puzzle, config, seed)` produces a different `RunResult` | Caught by the regression-test harness (when authored); raises `DeterminismError`. |

The principle: a *legitimate solver failure* (infeasible, capped) is a `RunResult`; an *illegitimate engineering failure* (Numba bug, disk full, non-determinism) is an exception. Stage-1 dispatch wraps the latter into Parquet rows so one bug does not invalidate four hours of compute, but the rows are surfaced, not hidden.

---

## 7. Performance Budget

Targets (estimated from the design's parameters; to be confirmed by benchmarking before Stage 1 starts):

| Quantity | Estimate |
|---|---|
| Walker step (one move) | ~300 ns |
| Walker run (≤ L = N² steps, dead-ending earlier) | ~30 µs at N=10 |
| Pheromone update per iteration | ~5 µs |
| One iteration (population = 30) | ~1 ms |
| One run (T = 200 iterations) | ~200 ms |
| Stage 1 (2,960 runs) | ~10 minutes single-threaded |
| Stage 1 with `n_jobs = cpu_count - 1 = 7` | ~1.5 minutes |

The wall-clock cap `wall_clock_s = 300.0` exists for safety on N=10 puzzles with pathological pheromone configurations, not as a typical case. If the realised single-run mean is materially above 1 s, this section is updated and the cap is reconsidered.

`py-spy record` and `scalene` are used to validate the budget on the dev split before Stage 1 launches. Numba `@njit(cache=True)` reduces second-process startup to milliseconds.

---

## 8. Migration / Cleanup

The existing `src/` tree is replaced wholesale. Specifically deleted:

- `src/models/cell.py`, `src/models/grid.py`, `src/models/path.py`, `src/models/wall.py`
- `src/enums/directions.py`
- `src/util/cache.py`

These are deleted because their data model (mutable cells, walls-as-cell-attributes, OOP path representation) is incompatible with the array-based kernel and would only confuse readers. The user authorised this deletion explicitly.

`benchmark/data/` (raw.json, puzzles.cbor, splits.json) is preserved unchanged. `benchmark/scripts/parse_to_cbor.py` and `benchmark/scripts/generate_splits.py` are kept; their `print` / `logging` calls are replaced with `loguru` logger calls and a top-level `configure_logging()` invocation, but their output remains bit-identical (verified by re-running them and diffing the CBOR/JSON).

---

## 9. Testing Strategy (Documented, Not Authored)

Per repo policy (`CLAUDE.md`: "Only ever plan or write tests, unit or otherwise, if explicitly asked to"), no tests are authored as part of this plan. When tests are commissioned, the strategy is:

- **Unit:** `pytest` with one file per module. Heuristic functions, feasibility prechecks, RNG hashing, and config validation are pure and trivially unit-testable.
- **Property-based:** `hypothesis` for `move_legality` (invariants: visited set monotone, parity preserved, waypoint order monotone), pheromone update (bounds, signed mode, stratified mode), and config round-trips (TOML → SolverConfig → TOML).
- **Integration:** end-to-end `solve(...)` on a curated 5-puzzle subset across all 8 conditions.
- **Regression / determinism:** golden-file `RunResult` JSONs for `(puzzle, config, seed)` triples. Any byte change is a hard failure.
- **Smoke (CI):** `solve()` on one Easy puzzle in <2 s; `parse_to_cbor.py` round-trip; type-check (ty + Pyright); ruff; bandit.
- **Coverage target:** 80 % per repo policy, measured with `pytest --cov`.

---

## 10. Out of Scope

- The visualizer (`docs/design.md` §11.1).
- Stage 2 / 3 / 4 analysis code beyond stub directories.
- Any algorithmic change to ZipMould — that is `docs/design.md`'s territory.
- Test authoring — deferred to an explicit pass.
- Distributed execution (Ray, Dask). joblib `loky` is sufficient for 2,960 runs; revisit only if Stage 4 grows the budget by an order of magnitude.

---

## 11. Acceptance Criteria

Implementation is complete when, *without writing tests*:

1. `uv run python -m zipmould solve --puzzle <id> --config configs/default.toml --seed 0` returns a `RunResult` for any puzzle in `benchmark/data/puzzles.cbor`.
2. `uv run python -m zipmould run-stage stage1 --manifest experiments/stage1/manifest.toml` completes 2,960 jobs and writes a Parquet aggregate plus 296 CBOR traces.
3. `ruff check`, `ruff format --check`, `ty check`, `pyright`, and `bandit -r src/zipmould` all pass on a fresh checkout.
4. Re-running the same `(puzzle, config, seed, global_seed)` produces a bitwise-equal `RunResult.solution`, `iters_used`, and `best_fitness`.
5. The `benchmark/scripts/*.py` scripts produce bit-identical output to their pre-migration runs.
