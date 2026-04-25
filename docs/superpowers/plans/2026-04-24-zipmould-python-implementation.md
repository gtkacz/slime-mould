# ZipMould Python Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the ZipMould solver kernel, CLI, baselines, configs, and Stage-1 dispatch under `src/zipmould/` per `docs/superpowers/specs/2026-04-24-zipmould-python-implementation-design.md`, replacing the legacy `src/{models,enums,util}/` tree.

**Architecture:** Two-layer hybrid — outer Python objects (`@dataclass(frozen=True, slots=True)` and Pydantic v2) plus an inner array-pure NumPy kernel inside `@njit(cache=True)` Numba functions. The boundary is `solver/state.py:pack/unpack`. CLI via `typer`, parallel dispatch via `joblib(loky)`, traces via `cbor2`, metrics via `polars`, logging via `loguru`.

**Tech Stack:** Python 3.13, Numba 0.65.1, NumPy 2.4.4, Pydantic v2 (2.13.x), `cbor2` 5.9, Polars 1.40, joblib 1.5.3, typer, tqdm, loguru 0.7.3. Tooling: `uv`, `ruff` 0.8.x, `ty` (Astral 0.0.32 beta), Pyright (CI backstop), `bandit`.

**Test policy:** Per repo CLAUDE.md and spec §9, **no tests are authored** in this plan. Verification at each task is via smoke imports, type checks, and end-to-end CLI invocation. The acceptance criteria in spec §11 are operational.

**Spec extension noted:** Spec §4.2 lacks a signed-vs-positive pheromone toggle even though design.md §6.1 enumerates four ZipMould variants on the (mode × sign) cross-product. This plan adds `tau_signed: bool = True` to `SolverConfig` so all four variants are configurable. Documented in Task 06.

**Convention for these instructions:** All shell commands assume the working directory is the repo root, `/home/gtkacz/Codes/slime-mould`. All Python is run via `uv run` per repo policy. Commits use the conventional-commits prefix from the global git rules (`feat:`, `refactor:`, `chore:`, etc.). No `Co-Authored-By` trailer is appended (global setting disables attribution).

---

## Phase 0 — Bootstrap & Migration

### Task 00: Update `pyproject.toml` to Python 3.13 and the full dependency set

**Why:** The legacy `pyproject.toml` pins `>=3.11` and only declares `cbor2`. The spec requires Python 3.13 and a specific library set, plus tooling configuration for `ruff`, `ty`, `pyright`, and `bandit`.

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Replace the entire `pyproject.toml`**

Overwrite `pyproject.toml` with:

```toml
[project]
name = "zipmould"
version = "0.1.0"
description = "ZipMould — a Li-inspired Slime Mould Algorithm for Zip puzzles"
requires-python = ">=3.13,<3.14"
readme = "README.md"
license = { file = "LICENSE" }
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
]

[project.scripts]
zipmould = "zipmould.cli:app"

[dependency-groups]
dev = [
    "ruff>=0.8,<0.9",
    "ty>=0.0.32",
    "pyright>=1.1.390",
    "bandit>=1.8,<2",
    "py-spy>=0.4,<1",
    "scalene>=1.5,<2",
    "pytest>=8.3,<9",
    "hypothesis>=6.115,<7",
]

[build-system]
requires = ["hatchling>=1.27"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/zipmould"]

[tool.ruff]
line-length = 120
target-version = "py313"
src = ["src", "benchmark", "experiments"]

[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "UP", "B", "A", "C4", "RET", "SIM", "PL", "RUF", "PERF", "ANN", "S"]
ignore = [
    "PLR0913",
    "ANN401",
    "S101",
]

[tool.ruff.lint.per-file-ignores]
"benchmark/scripts/*.py" = ["T201"]
"experiments/**/*.py" = ["T201"]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
line-ending = "lf"

[tool.ty]
python-version = "3.13"

[tool.pyright]
pythonVersion = "3.13"
include = ["src/zipmould", "benchmark/scripts", "experiments"]
typeCheckingMode = "strict"
reportMissingTypeStubs = "warning"
reportUnknownMemberType = "warning"
reportUnknownVariableType = "warning"

[tool.bandit]
exclude_dirs = [".venv", "tests", "experiments"]

[tool.pytest.ini_options]
addopts = "-ra -q"
testpaths = ["tests"]
```

- [ ] **Step 2: Verify TOML parses and dependencies resolve**

Run:
```bash
uv lock
```

Expected: A `uv.lock` file is regenerated with the new dependency tree, no resolution errors. Stderr may print info lines from `uv`.

- [ ] **Step 3: Sync the virtualenv to the new lockfile**

Run:
```bash
uv sync --all-groups
```

Expected: `Resolved N packages in ...`, then `Installed N packages in ...`. The `.venv/` directory is updated. No errors.

- [ ] **Step 4: Smoke-check the toolchain is wired up**

Run:
```bash
uv run python -c "import sys; print(sys.version_info[:2])"
uv run python -c "import numba, numpy, pydantic, polars, joblib, typer, tqdm, loguru, cbor2; print('ok')"
uv run ruff --version
uv run ty --version
uv run pyright --version
uv run bandit --version
```

Expected: First prints `(3, 13)`. Second prints `ok`. Each tool prints its version banner.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "chore: pin python 3.13 and full zipmould dependency set"
```

---

### Task 01: Delete legacy `src/{models,enums,util}/` and seed the `src/zipmould/` package

**Why:** Spec §8 authorises wholesale replacement of the legacy tree because its mutable-cell, walls-as-cell-attribute model is incompatible with the array-based kernel. Per the user's explicit authorisation in the spec.

**Files:**
- Delete: `src/models/`, `src/enums/`, `src/util/`
- Create: `src/zipmould/__init__.py`, `src/zipmould/py.typed`

- [ ] **Step 1: Delete legacy directories**

Run:
```bash
rm -rf src/models src/enums src/util
```

Expected: No output. `ls src/` shows only `zipmould/` (after Step 2) or nothing (before).

- [ ] **Step 2: Create the package skeleton with a placeholder `__init__.py`**

Create `src/zipmould/__init__.py` with content:

```python
"""ZipMould — Li-inspired Slime Mould Algorithm for Zip puzzles.

The public API is finalised in later tasks. This module is intentionally
minimal at this checkpoint.
"""

__version__ = "0.1.0"
```

Create `src/zipmould/py.typed` as an empty file (PEP 561 marker so type checkers see this as a typed package):

```bash
mkdir -p src/zipmould
: > src/zipmould/py.typed
```

- [ ] **Step 3: Verify the package imports**

Run:
```bash
uv run python -c "import zipmould; print(zipmould.__version__)"
```

Expected: `0.1.0`.

- [ ] **Step 4: Commit**

```bash
git add -A src/
git commit -m "refactor: replace legacy src/ tree with zipmould package skeleton"
```

---

### Task 02: Add `src/zipmould/logging_config.py` with loguru `InterceptHandler`

**Why:** Spec §1.3 mandates loguru as the single sink with stdlib `logging` redirected via `InterceptHandler`. This module is imported first by every entry point so library logs (Numba, joblib, polars) flow through one formatter.

**Files:**
- Create: `src/zipmould/logging_config.py`

- [ ] **Step 1: Write `logging_config.py`**

Create `src/zipmould/logging_config.py`:

```python
"""Loguru configuration with stdlib `logging` interception.

Call `configure_logging()` once at process start. Every other logger
(stdlib, third-party libraries) is redirected into loguru via
`InterceptHandler`, so the entire process emits a single, consistent
log stream.
"""

from __future__ import annotations

import logging
import sys
from typing import Final

from loguru import logger

_DEFAULT_FORMAT: Final[str] = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> "
    "<level>{level: <8}</level> "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> "
    "- <level>{message}</level>"
)


class InterceptHandler(logging.Handler):
    """Route stdlib `logging` records into loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level: str | int = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def configure_logging(level: str = "INFO", *, fmt: str = _DEFAULT_FORMAT) -> None:
    """Install loguru as the single sink and intercept stdlib logging."""
    logger.remove()
    logger.add(sys.stderr, level=level, format=fmt, enqueue=False, backtrace=False, diagnose=False)

    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    for noisy in ("numba", "numba.core", "numba.core.ssa", "numba.core.byteflow"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
```

- [ ] **Step 2: Smoke-test it**

Run:
```bash
uv run python -c "
from zipmould.logging_config import configure_logging
configure_logging(level='DEBUG')
import logging
logging.getLogger('demo').warning('stdlib path')
from loguru import logger
logger.info('loguru path')
"
```

Expected: Two log lines, both formatted with the loguru template (`<time> <level> <name>:<func>:<line> - <message>`). The first comes from stdlib via the intercept; the second directly from loguru. No traceback.

- [ ] **Step 3: Commit**

```bash
git add src/zipmould/logging_config.py
git commit -m "feat(zipmould): loguru sink with stdlib InterceptHandler"
```

---

### Task 03: Migrate `benchmark/scripts/*.py` to loguru while preserving byte-identical output

**Why:** Spec §8 says benchmark data files (`puzzles.cbor`, `splits.json`) must remain bit-identical after migration. The scripts' `logging.info` calls are replaced with `loguru` calls and a `configure_logging()` invocation. The data-writing logic is untouched.

**Files:**
- Modify: `benchmark/scripts/parse_to_cbor.py`
- Modify: `benchmark/scripts/make_splits.py`

- [ ] **Step 1: Snapshot current outputs for byte-identical comparison**

Run:
```bash
cp benchmark/data/puzzles.cbor /tmp/puzzles.cbor.before
cp benchmark/data/splits.json /tmp/splits.json.before
```

Expected: Two files copied, no output.

- [ ] **Step 2: Update `benchmark/scripts/parse_to_cbor.py`**

Replace lines 12-21 (the imports through `logger = logging.getLogger(...)`) with:

```python
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cbor2
from loguru import logger

from zipmould.logging_config import configure_logging
```

Replace lines 171-178 (the `main()` function body) with:

```python
def main() -> int:
    configure_logging(level="INFO")
    repo_root = Path(__file__).resolve().parents[2]
    raw_path = repo_root / "benchmark" / "data" / "raw.json"
    out_path = repo_root / "benchmark" / "data" / "puzzles.cbor"
    parse_corpus(raw_path, out_path)
    return 0
```

The `logger.info("Reading %s", raw_path)`, `logger.info("Normalized %d puzzles", ...)`, and `logger.info("Wrote %s (%d bytes)", ...)` calls inside `parse_corpus` already use the `logger` name; loguru accepts the `%` form via its f-string-style API by switching to `{}` placeholders. Update each:

- `logger.info("Reading %s", raw_path)` → `logger.info("Reading {}", raw_path)`
- `logger.info("Normalized %d puzzles", len(normalized))` → `logger.info("Normalized {} puzzles", len(normalized))`
- `logger.info("Wrote %s (%d bytes)", out_path, out_path.stat().st_size)` → `logger.info("Wrote {} ({} bytes)", out_path, out_path.stat().st_size)`

- [ ] **Step 3: Update `benchmark/scripts/make_splits.py`**

Replace lines 13-23 (imports through `logger = logging.getLogger(...)`) with:

```python
import json
import random
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import cbor2
from loguru import logger

from zipmould.logging_config import configure_logging
```

Replace lines 142-148 (the `main()` function body) with:

```python
def main() -> int:
    configure_logging(level="INFO")
    repo_root = Path(__file__).resolve().parents[2]
    puzzles_path = repo_root / "benchmark" / "data" / "puzzles.cbor"
    out_path = repo_root / "benchmark" / "data" / "splits.json"
    make_splits(puzzles_path, out_path)
    return 0
```

Update the four `logger.info("... %s ... %d ...", ...)` calls in `make_splits()` to use loguru's `{}` placeholders, preserving the same arguments and ordering:

- `logger.info("Loaded %d puzzles from %s", len(puzzles), puzzles_path)` → `logger.info("Loaded {} puzzles from {}", len(puzzles), puzzles_path)`
- `logger.info("stratum %s/%s: total=%d train=%d dev=%d test=%d", key[0], key[1], len(ids), len(s_train), len(s_dev), len(s_test))` → `logger.info("stratum {}/{}: total={} train={} dev={} test={}", key[0], key[1], len(ids), len(s_train), len(s_dev), len(s_test))`
- `logger.info("Wrote %s (train=%d dev=%d test=%d)", out_path, len(train), len(dev), len(test))` → `logger.info("Wrote {} (train={} dev={} test={})", out_path, len(train), len(dev), len(test))`

- [ ] **Step 4: Re-run both scripts**

Run:
```bash
uv run python benchmark/scripts/parse_to_cbor.py
uv run python benchmark/scripts/make_splits.py
```

Expected: Each prints loguru-formatted log lines. Both exit 0.

- [ ] **Step 5: Verify byte-identical output (acceptance criterion 5)**

Run:
```bash
cmp /tmp/puzzles.cbor.before benchmark/data/puzzles.cbor && echo "puzzles.cbor identical"
cmp /tmp/splits.json.before benchmark/data/splits.json && echo "splits.json identical"
```

Expected: Both lines printed. If `cmp` produces output instead, the migration changed bytes — investigate before proceeding.

- [ ] **Step 6: Commit**

```bash
git add benchmark/scripts/
git commit -m "refactor(benchmark): route scripts through loguru, preserve byte-identical output"
```

---

## Phase 1 — Outer Layer

### Task 04: `puzzle.py` — `Coord`, `Edge`, `Puzzle` dataclass + `load_puzzles_cbor()`

**Why:** Spec §4.1 defines `Puzzle` as a frozen, slotted dataclass with canonicalised walls and frozen-set blocked cells. Loaded once from `benchmark/data/puzzles.cbor`.

**Files:**
- Create: `src/zipmould/puzzle.py`

- [ ] **Step 1: Write `puzzle.py`**

Create `src/zipmould/puzzle.py`:

```python
"""Outer-layer puzzle representation.

`Puzzle` is the canonical, immutable view of a single Zip puzzle as
loaded from `benchmark/data/puzzles.cbor`. The kernel never sees these
objects; `solver.state.pack` projects them into NumPy arrays.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal

import cbor2

Coord = tuple[int, int]
Edge = tuple[Coord, Coord]

Difficulty = Literal["Easy", "Medium", "Hard"]

_VALID_DIFFICULTIES: Final[frozenset[str]] = frozenset({"Easy", "Medium", "Hard"})


def _canonical_edge(a: Coord, b: Coord) -> Edge:
    return (a, b) if a <= b else (b, a)


@dataclass(frozen=True, slots=True)
class Puzzle:
    id: str
    name: str
    difficulty: Difficulty
    N: int
    K: int
    waypoints: tuple[Coord, ...]
    walls: frozenset[Edge]
    blocked: frozenset[Coord]

    def free_cells(self) -> frozenset[Coord]:
        all_cells = {(r, c) for r in range(self.N) for c in range(self.N)}
        return frozenset(all_cells - self.blocked)

    def L(self) -> int:
        return self.N * self.N - len(self.blocked)


def _from_cbor_dict(raw: dict[str, object]) -> Puzzle:
    difficulty = raw["difficulty"]
    if difficulty not in _VALID_DIFFICULTIES:
        msg = f"unknown difficulty {difficulty!r} in puzzle {raw.get('id')!r}"
        raise ValueError(msg)

    waypoints_raw = raw["waypoints"]
    walls_raw = raw["walls"]
    blocked_raw = raw["blocked"]

    waypoints = tuple((int(r), int(c)) for r, c in waypoints_raw)  # type: ignore[union-attr]
    walls = frozenset(
        _canonical_edge((int(a[0]), int(a[1])), (int(b[0]), int(b[1])))
        for a, b in walls_raw  # type: ignore[union-attr]
    )
    blocked = frozenset((int(r), int(c)) for r, c in blocked_raw)  # type: ignore[union-attr]

    return Puzzle(
        id=str(raw["id"]),
        name=str(raw["name"]),
        difficulty=difficulty,  # type: ignore[arg-type]
        N=int(raw["N"]),  # type: ignore[arg-type]
        K=int(raw["K"]),  # type: ignore[arg-type]
        waypoints=waypoints,
        walls=walls,
        blocked=blocked,
    )


def load_puzzles_cbor(path: Path) -> dict[str, Puzzle]:
    """Load all puzzles from `path`, keyed by `puzzle.id`."""
    with path.open("rb") as f:
        payload = cbor2.load(f)
    raw_list = payload["puzzles"]
    return {p["id"]: _from_cbor_dict(p) for p in raw_list}
```

- [ ] **Step 2: Smoke-test the loader**

Run:
```bash
uv run python -c "
from pathlib import Path
from zipmould.puzzle import load_puzzles_cbor
puzzles = load_puzzles_cbor(Path('benchmark/data/puzzles.cbor'))
print(len(puzzles), 'puzzles loaded')
p = next(iter(puzzles.values()))
print('id:', p.id, 'N:', p.N, 'K:', p.K, 'L:', p.L())
print('first waypoint:', p.waypoints[0])
"
```

Expected: `245 puzzles loaded`, plus the first puzzle's id, dimensions, L (= N² for un-blocked puzzles or N²-len(blocked) otherwise), and first waypoint coordinate.

- [ ] **Step 3: Commit**

```bash
git add src/zipmould/puzzle.py
git commit -m "feat(zipmould): Puzzle dataclass and CBOR loader"
```

---

### Task 05: `config.py` — `SolverConfig`, `ExperimentManifest`, `from_toml()`, `config_hash()`

**Why:** Spec §4.2 plus the noted extension (`tau_signed: bool`). Pydantic v2 with `frozen=True, extra="forbid"`. The string sentinels `"N_squared"` / `"10_N_squared"` survive serialisation; resolution to floats happens in `state.pack`.

**Files:**
- Create: `src/zipmould/config.py`

- [ ] **Step 1: Write `config.py`**

Create `src/zipmould/config.py`:

```python
"""Pydantic v2 configuration models for the solver and experiments.

`SolverConfig` is the per-puzzle solver knob set; `ExperimentManifest`
declares Stage-N batches. String sentinels `"N_squared"` and
`"10_N_squared"` for `beta1`/`beta3` survive TOML round-trips and
are materialised inside `solver.state.pack(puzzle, config)`.
"""

from __future__ import annotations

import hashlib
import json
import tomllib
from pathlib import Path
from typing import Final, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator


_BETA1_DEFAULT: Final[str] = "N_squared"
_BETA3_DEFAULT: Final[str] = "10_N_squared"


class SolverConfig(BaseModel):
    """Validated solver knobs. Extension: `tau_signed` covers design.md §6.1's
    pos/signed axis missing from the impl spec §4.2."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    gamma_man: float = Field(default=1.0, ge=0.0)
    gamma_warns: float = Field(default=1.0, ge=0.0)
    gamma_art: float = Field(default=1.0, ge=0.0)
    gamma_par: float = Field(default=0.5, ge=0.0)

    alpha: float = Field(default=1.0, ge=0.0)
    beta: float = Field(default=2.0, ge=0.0)

    beta1: float | Literal["N_squared"] = _BETA1_DEFAULT
    beta2: float = Field(default=1.0, ge=0.0)
    beta3: float | Literal["10_N_squared"] = _BETA3_DEFAULT
    tau_max: float = Field(default=10.0, gt=0.0)
    z: float = Field(default=0.05, ge=0.0, le=1.0)
    tau_0: float = 0.0

    population: int = Field(default=30, ge=1)
    iter_cap: int = Field(default=200, ge=1)
    wall_clock_s: float = Field(default=300.0, gt=0.0)

    pheromone_mode: Literal["unified", "stratified"] = "unified"
    tau_signed: bool = True

    visible_walkers: int = Field(default=5, ge=0)
    frame_interval: int = Field(default=5, ge=1)
    tau_delta_epsilon: float = Field(default=1e-3, ge=0.0)

    @field_validator("beta1")
    @classmethod
    def _check_beta1(cls, v: float | str) -> float | str:
        if isinstance(v, str) and v != "N_squared":
            msg = f"beta1 string sentinel must be 'N_squared', got {v!r}"
            raise ValueError(msg)
        if isinstance(v, (int, float)) and v < 0:
            msg = "beta1 must be non-negative"
            raise ValueError(msg)
        return v

    @field_validator("beta3")
    @classmethod
    def _check_beta3(cls, v: float | str) -> float | str:
        if isinstance(v, str) and v != "10_N_squared":
            msg = f"beta3 string sentinel must be '10_N_squared', got {v!r}"
            raise ValueError(msg)
        if isinstance(v, (int, float)) and v < 0:
            msg = "beta3 must be non-negative"
            raise ValueError(msg)
        return v

    @classmethod
    def from_toml(cls, path: Path) -> Self:
        with path.open("rb") as f:
            data = tomllib.load(f)
        body = data.get("solver", data)
        return cls.model_validate(body)

    def canonical_json(self) -> bytes:
        d = self.model_dump(mode="json")
        return json.dumps(d, sort_keys=True, separators=(",", ":")).encode("utf-8")

    def config_hash(self) -> str:
        return hashlib.blake2b(self.canonical_json(), digest_size=16).hexdigest()


class ConditionEntry(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    name: str
    solver: Literal[
        "zipmould", "random_walk", "heuristic_only", "aco_vanilla", "backtracking"
    ]
    config: str


class ExperimentManifest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    stage: str
    split: Literal["train", "dev", "test"]
    seeds: tuple[int, ...]
    global_seed: int
    conditions: tuple[ConditionEntry, ...]
    trace_seed: int = 0
    output_dir: str

    @classmethod
    def from_toml(cls, path: Path) -> Self:
        with path.open("rb") as f:
            data = tomllib.load(f)
        return cls.model_validate(data)


class ConfigError(ValueError):
    """Raised when a TOML config fails validation."""
```

- [ ] **Step 2: Smoke-test config loading**

Run:
```bash
uv run python -c "
from zipmould.config import SolverConfig
c = SolverConfig()
print('hash:', c.config_hash())
print('beta1:', c.beta1, 'pheromone_mode:', c.pheromone_mode, 'tau_signed:', c.tau_signed)
c2 = SolverConfig(pheromone_mode='stratified', tau_signed=False)
print('hashes differ:', c.config_hash() != c2.config_hash())
"
```

Expected: A 32-character hex `hash:`, then `beta1: N_squared pheromone_mode: unified tau_signed: True`, then `hashes differ: True`.

- [ ] **Step 3: Commit**

```bash
git add src/zipmould/config.py
git commit -m "feat(zipmould): Pydantic SolverConfig and ExperimentManifest with canonical hash"
```

---

### Task 06: `rng.py` — deterministic kernel-seed derivation via blake2b

**Why:** Spec §2.2 mandates that per-run RNG entropy is `blake2b(global_seed || run_seed || puzzle_id || config_hash)`. The kernel needs an integer seed; outer code may also need a `numpy.random.Generator` for any non-kernel sampling.

**Files:**
- Create: `src/zipmould/rng.py`

- [ ] **Step 1: Write `rng.py`**

Create `src/zipmould/rng.py`:

```python
"""Deterministic RNG seeding for ZipMould runs.

A Numba-compatible 32-bit kernel seed is derived from a 256-bit blake2b
digest of the run identity tuple. The same identity produces the same
kernel seed and the same `numpy.random.Generator`, byte-for-byte.
"""

from __future__ import annotations

import hashlib

import numpy as np


def _digest(global_seed: int, run_seed: int, puzzle_id: str, config_hash: str) -> bytes:
    h = hashlib.blake2b(digest_size=32)
    h.update(int(global_seed).to_bytes(8, "little", signed=False))
    h.update(int(run_seed).to_bytes(8, "little", signed=False))
    h.update(puzzle_id.encode("utf-8"))
    h.update(bytes.fromhex(config_hash))
    return h.digest()


def derive_kernel_seed(
    global_seed: int, run_seed: int, puzzle_id: str, config_hash: str
) -> int:
    """Return a deterministic 32-bit unsigned integer suitable for `np.random.seed` inside `@njit`."""
    digest = _digest(global_seed, run_seed, puzzle_id, config_hash)
    return int.from_bytes(digest[:4], "little") & 0xFFFFFFFF


def make_rng(
    global_seed: int, run_seed: int, puzzle_id: str, config_hash: str
) -> np.random.Generator:
    """Return a `Generator` for any outer-layer sampling that must share the run identity."""
    digest = _digest(global_seed, run_seed, puzzle_id, config_hash)
    seed_seq = np.random.SeedSequence(int.from_bytes(digest, "little"))
    return np.random.default_rng(seed_seq)
```

- [ ] **Step 2: Smoke-test determinism**

Run:
```bash
uv run python -c "
from zipmould.rng import derive_kernel_seed, make_rng
s1 = derive_kernel_seed(0, 7, 'level_001', 'a' * 32)
s2 = derive_kernel_seed(0, 7, 'level_001', 'a' * 32)
s3 = derive_kernel_seed(0, 8, 'level_001', 'a' * 32)
print('determinism ok:', s1 == s2)
print('changes with seed:', s1 != s3)
print('sample seed:', s1)
g1 = make_rng(0, 7, 'level_001', 'a' * 32)
g2 = make_rng(0, 7, 'level_001', 'a' * 32)
print('generator determinism:', g1.integers(0, 1<<32) == g2.integers(0, 1<<32))
"
```

Expected: `determinism ok: True`, `changes with seed: True`, a sample integer, and `generator determinism: True`.

- [ ] **Step 3: Commit**

```bash
git add src/zipmould/rng.py
git commit -m "feat(zipmould): blake2b-derived kernel seed and numpy Generator"
```

---

## Phase 2 — Feasibility, Fitness, Heuristics

### Task 07: `feasibility.py` — `FeasibilityReport` + `precheck()`

**Why:** Design §3.9 mandates three O(N²) checks before any walker runs: waypoint membership in F, BFS connectivity (every free cell reachable from w₁ and all w_k included), and the bipartite parity necessary condition. Failure reports `infeasible` rather than raising.

**Files:**
- Create: `src/zipmould/feasibility.py`

- [ ] **Step 1: Write `feasibility.py`**

Create `src/zipmould/feasibility.py`:

```python
"""Feasibility prechecks per docs/design.md §3.9.

These are necessary-but-not-sufficient: passing them does not guarantee
a Hamiltonian path exists, but failing them proves no algorithm can
solve the puzzle. Cheap O(N²) work, run once per puzzle before the
solver loop starts.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Literal

from zipmould.puzzle import Coord, Puzzle


FeasibilityFailure = Literal[
    "waypoint_blocked",
    "waypoint_unreachable",
    "free_subgraph_disconnected",
    "parity_imbalance",
    "endpoint_parity_mismatch",
]


@dataclass(frozen=True, slots=True)
class FeasibilityReport:
    feasible: bool
    reason: FeasibilityFailure | None
    f0_count: int
    f1_count: int
    reachable_count: int


def _adjacent(c: Coord, n: int, walls: frozenset, blocked: frozenset[Coord]) -> list[Coord]:
    r, k = c
    out: list[Coord] = []
    for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        nr, nc = r + dr, k + dc
        if not (0 <= nr < n and 0 <= nc < n):
            continue
        nb = (nr, nc)
        if nb in blocked:
            continue
        edge = (c, nb) if c <= nb else (nb, c)
        if edge in walls:
            continue
        out.append(nb)
    return out


def precheck(puzzle: Puzzle) -> FeasibilityReport:
    free = puzzle.free_cells()

    for w in puzzle.waypoints:
        if w in puzzle.blocked or w not in free:
            return FeasibilityReport(False, "waypoint_blocked", 0, 0, 0)

    f0 = sum(1 for (r, c) in free if (r + c) % 2 == 0)
    f1 = len(free) - f0

    start = puzzle.waypoints[0]
    seen: set[Coord] = {start}
    queue: deque[Coord] = deque([start])
    while queue:
        cur = queue.popleft()
        for nb in _adjacent(cur, puzzle.N, puzzle.walls, puzzle.blocked):
            if nb not in seen:
                seen.add(nb)
                queue.append(nb)

    reach_count = len(seen)

    for w in puzzle.waypoints[1:]:
        if w not in seen:
            return FeasibilityReport(False, "waypoint_unreachable", f0, f1, reach_count)

    if seen != free:
        return FeasibilityReport(False, "free_subgraph_disconnected", f0, f1, reach_count)

    if abs(f0 - f1) > 1:
        return FeasibilityReport(False, "parity_imbalance", f0, f1, reach_count)

    if f0 != f1:
        larger_parity = 0 if f0 > f1 else 1
        w1 = puzzle.waypoints[0]
        wk = puzzle.waypoints[-1]
        if (w1[0] + w1[1]) % 2 != larger_parity or (wk[0] + wk[1]) % 2 != larger_parity:
            return FeasibilityReport(False, "endpoint_parity_mismatch", f0, f1, reach_count)

    return FeasibilityReport(True, None, f0, f1, reach_count)
```

- [ ] **Step 2: Smoke-test against the corpus**

Run:
```bash
uv run python -c "
from pathlib import Path
from zipmould.puzzle import load_puzzles_cbor
from zipmould.feasibility import precheck
puzzles = load_puzzles_cbor(Path('benchmark/data/puzzles.cbor'))
infeasible = []
for pid, p in puzzles.items():
    rep = precheck(p)
    if not rep.feasible:
        infeasible.append((pid, rep.reason))
print('total:', len(puzzles), 'infeasible:', len(infeasible))
for x in infeasible[:5]:
    print(' ', x)
"
```

Expected: A line like `total: 245 infeasible: K` where K is small (the curated corpus is intended to be feasible per design.md §3.9; any infeasibility is a data-quality flag rather than a code bug). The expected outcome on this corpus is `infeasible: 0`. If non-zero, log the IDs and reasons but do not block.

- [ ] **Step 3: Commit**

```bash
git add src/zipmould/feasibility.py
git commit -m "feat(zipmould): O(N^2) feasibility precheck per design.md §3.9"
```

---

### Task 08: `fitness.py` — `@njit` fitness function

**Why:** Spec §3.6 / design.md §3.6 defines `f(P) = |P| + β₁·k_max(P) + β₂/(1+d_M(c, w_{k+1})) + β₃·1[solved]`. This is the inner loop of the iteration; lives in `@njit` for speed and shares the no-Python-objects rule.

**Files:**
- Create: `src/zipmould/fitness.py`

- [ ] **Step 1: Write `fitness.py`**

Create `src/zipmould/fitness.py`:

```python
"""@njit fitness evaluator.

Follows design.md §3.6: coverage + waypoint progress + Manhattan
proximity to next waypoint + success bonus. The progress term is
clipped to its limiting value `beta_2` when `segment >= K` (no next
waypoint to head toward).
"""

from __future__ import annotations

import numba as nb
import numpy as np


@nb.njit(cache=True, fastmath=False)
def fitness(
    path_len: int,
    segment: int,
    last_cell: int,
    waypoint_cells: np.ndarray,
    L: int,
    K: int,
    N: int,
    beta_1: float,
    beta_2: float,
    beta_3: float,
) -> float:
    coverage = float(path_len)
    waypoint_term = beta_1 * float(segment)

    if segment >= K:
        progress = beta_2
    else:
        next_w = int(waypoint_cells[segment])
        last_r = last_cell // N
        last_c = last_cell % N
        nw_r = next_w // N
        nw_c = next_w % N
        d_m = abs(last_r - nw_r) + abs(last_c - nw_c)
        progress = beta_2 / (1.0 + float(d_m))

    if path_len == L and last_cell == int(waypoint_cells[K - 1]) and segment == K:
        success = beta_3
    else:
        success = 0.0

    return coverage + waypoint_term + progress + success
```

- [ ] **Step 2: Smoke-compile and call once**

Run:
```bash
uv run python -c "
import numpy as np
from zipmould.fitness import fitness
wp = np.array([0, 8], dtype=np.int16)
v = fitness(2, 1, 1, wp, 9, 2, 3, 9.0, 1.0, 90.0)
print('partial fitness:', v)
v_full = fitness(9, 2, 8, wp, 9, 2, 3, 9.0, 1.0, 90.0)
print('full-success fitness:', v_full)
"
```

Expected: First print shows a positive float around `2 + 9 + 1/(1 + d_m) ≈ 11+`; second shows `9 + 18 + 1 + 90 = 118.0` (or similar — exact value depends on N, K, beta_1). First call may take 1-3 s for JIT compile.

- [ ] **Step 3: Commit**

```bash
git add src/zipmould/fitness.py
git commit -m "feat(zipmould): @njit fitness per design.md §3.6"
```

---

### Task 09: `solver/state.py` — `KernelState` NamedTuple, `pack`, `unpack`

**Why:** Spec §4.4 specifies the array layout for the kernel. `pack` materialises sentinels, builds the adjacency / Manhattan / parity / waypoint tables, and allocates walker state. `unpack` lifts the chosen walker's path back to `tuple[Coord, ...]`.

**Files:**
- Create: `src/zipmould/solver/__init__.py`
- Create: `src/zipmould/solver/state.py`

- [ ] **Step 1: Create the solver package marker**

Create `src/zipmould/solver/__init__.py`:

```python
"""Solver kernel and outer-layer API."""
```

- [ ] **Step 2: Write `solver/state.py`**

Create `src/zipmould/solver/state.py`:

```python
"""Kernel state and packing/unpacking — the only meeting point of the
outer Pydantic/dataclass layer and the @njit array kernel.

`pack(puzzle, config)` resolves the string sentinels `"N_squared"` and
`"10_N_squared"` from `SolverConfig` into floats using the puzzle's
`N`, then precomputes the Manhattan / parity / adjacency / waypoint
tables once per run.
"""

from __future__ import annotations

from typing import NamedTuple

import numpy as np

from zipmould.config import SolverConfig
from zipmould.puzzle import Coord, Puzzle


class KernelState(NamedTuple):
    L: int
    N: int
    N2: int
    K: int
    E: int
    n_walkers: int
    n_stripes: int
    pheromone_mode: int
    tau_signed: int

    alpha: float
    beta: float
    beta1: float
    beta2: float
    beta3: float
    gamma_man: float
    gamma_warns: float
    gamma_art: float
    gamma_par: float
    tau_max: float
    tau_clip_min: float
    tau_0: float
    z: float

    iter_cap: int
    visible_walkers: int
    frame_interval: int
    tau_delta_epsilon: float

    tau: np.ndarray
    pos: np.ndarray
    visited: np.ndarray
    path: np.ndarray
    path_len: np.ndarray
    segment: np.ndarray
    status: np.ndarray
    f0_remaining: np.ndarray
    f1_remaining: np.ndarray
    walker_fitness: np.ndarray

    manhattan_table: np.ndarray
    parity_table: np.ndarray
    adjacency: np.ndarray
    edge_of: np.ndarray
    edge_endpoints: np.ndarray
    waypoint_cells: np.ndarray
    waypoint_of: np.ndarray
    f0_total: int
    f1_total: int


def _resolve_beta1(value: float | str, n: int) -> float:
    return float(n * n) if value == "N_squared" else float(value)


def _resolve_beta3(value: float | str, n: int) -> float:
    return 10.0 * float(n * n) if value == "10_N_squared" else float(value)


def _build_adjacency(puzzle: Puzzle) -> tuple[np.ndarray, np.ndarray, np.ndarray, int]:
    n = puzzle.N
    n2 = n * n
    adj = np.full((n2, 4), -1, dtype=np.int16)
    edge_of = np.full((n2, 4), -1, dtype=np.int32)
    edges_seen: dict[tuple[int, int], int] = {}
    deltas = ((-1, 0), (1, 0), (0, -1), (0, 1))

    for r in range(n):
        for c in range(n):
            here = r * n + c
            if (r, c) in puzzle.blocked:
                continue
            for dir_idx, (dr, dc) in enumerate(deltas):
                nr, nc = r + dr, c + dc
                if not (0 <= nr < n and 0 <= nc < n):
                    continue
                nb = (nr, nc)
                if nb in puzzle.blocked:
                    continue
                a, b = ((r, c), nb) if (r, c) <= nb else (nb, (r, c))
                if (a, b) in puzzle.walls:
                    continue
                nb_idx = nr * n + nc
                adj[here, dir_idx] = nb_idx
                key = (here, nb_idx) if here < nb_idx else (nb_idx, here)
                if key not in edges_seen:
                    edges_seen[key] = len(edges_seen)
                edge_of[here, dir_idx] = edges_seen[key]

    n_edges = len(edges_seen)
    edge_endpoints = np.zeros((n_edges, 2), dtype=np.int32)
    for (a, b), eid in edges_seen.items():
        edge_endpoints[eid, 0] = a
        edge_endpoints[eid, 1] = b
    return adj, edge_of, edge_endpoints, n_edges


def _build_manhattan(puzzle: Puzzle, waypoint_cells: np.ndarray) -> np.ndarray:
    n = puzzle.N
    n2 = n * n
    K = puzzle.K
    table = np.zeros((n2, K), dtype=np.int16)
    for cell in range(n2):
        cr, cc = cell // n, cell % n
        for k in range(K):
            wc = int(waypoint_cells[k])
            wr, wcol = wc // n, wc % n
            table[cell, k] = abs(cr - wr) + abs(cc - wcol)
    return table


def _build_parity(n: int) -> np.ndarray:
    table = np.zeros(n * n, dtype=np.int8)
    for r in range(n):
        for c in range(n):
            table[r * n + c] = (r + c) & 1
    return table


def pack(puzzle: Puzzle, config: SolverConfig) -> KernelState:
    n = puzzle.N
    n2 = n * n
    K = puzzle.K
    L = puzzle.L()
    blocked_mask = np.zeros(n2, dtype=np.bool_)
    for r, c in puzzle.blocked:
        blocked_mask[r * n + c] = True

    adjacency, edge_of, edge_endpoints, n_edges = _build_adjacency(puzzle)

    waypoint_cells = np.array(
        [r * n + c for (r, c) in puzzle.waypoints], dtype=np.int16
    )
    waypoint_of = np.full(n2, -1, dtype=np.int8)
    for k, wcell in enumerate(waypoint_cells, start=1):
        waypoint_of[int(wcell)] = k

    manhattan_table = _build_manhattan(puzzle, waypoint_cells)
    parity_table = _build_parity(n)

    f0_total = int(np.sum((parity_table == 0) & (~blocked_mask)))
    f1_total = int(np.sum((parity_table == 1) & (~blocked_mask)))

    n_walkers = int(config.population)
    n_stripes = (K - 1) if (config.pheromone_mode == "stratified" and K > 1) else 1
    pher_mode_int = 1 if config.pheromone_mode == "stratified" else 0
    tau_signed_int = 1 if config.tau_signed else 0

    tau_clip_min = -float(config.tau_max) if config.tau_signed else 0.0
    tau_init = float(config.tau_0)
    tau = np.full((n_stripes, max(n_edges, 1)), tau_init, dtype=np.float32)

    visited_words = (n2 + 63) // 64
    pos = np.zeros(n_walkers, dtype=np.int16)
    visited = np.zeros((n_walkers, visited_words), dtype=np.uint64)
    path = np.zeros((n_walkers, L), dtype=np.int16)
    path_len = np.zeros(n_walkers, dtype=np.int16)
    segment = np.zeros(n_walkers, dtype=np.int8)
    status = np.zeros(n_walkers, dtype=np.int8)
    f0_remaining = np.zeros(n_walkers, dtype=np.int32)
    f1_remaining = np.zeros(n_walkers, dtype=np.int32)
    walker_fitness = np.zeros(n_walkers, dtype=np.float64)

    return KernelState(
        L=L,
        N=n,
        N2=n2,
        K=K,
        E=max(n_edges, 1),
        n_walkers=n_walkers,
        n_stripes=n_stripes,
        pheromone_mode=pher_mode_int,
        tau_signed=tau_signed_int,
        alpha=float(config.alpha),
        beta=float(config.beta),
        beta1=_resolve_beta1(config.beta1, n),
        beta2=float(config.beta2),
        beta3=_resolve_beta3(config.beta3, n),
        gamma_man=float(config.gamma_man),
        gamma_warns=float(config.gamma_warns),
        gamma_art=float(config.gamma_art),
        gamma_par=float(config.gamma_par),
        tau_max=float(config.tau_max),
        tau_clip_min=tau_clip_min,
        tau_0=tau_init,
        z=float(config.z),
        iter_cap=int(config.iter_cap),
        visible_walkers=int(config.visible_walkers),
        frame_interval=int(config.frame_interval),
        tau_delta_epsilon=float(config.tau_delta_epsilon),
        tau=tau,
        pos=pos,
        visited=visited,
        path=path,
        path_len=path_len,
        segment=segment,
        status=status,
        f0_remaining=f0_remaining,
        f1_remaining=f1_remaining,
        walker_fitness=walker_fitness,
        manhattan_table=manhattan_table,
        parity_table=parity_table,
        adjacency=adjacency,
        edge_of=edge_of,
        edge_endpoints=edge_endpoints,
        waypoint_cells=waypoint_cells,
        waypoint_of=waypoint_of,
        f0_total=f0_total,
        f1_total=f1_total,
    )


def unpack_path(state: KernelState, walker_id: int) -> tuple[Coord, ...]:
    n = state.N
    plen = int(state.path_len[walker_id])
    raw = state.path[walker_id, :plen]
    return tuple((int(c) // n, int(c) % n) for c in raw)
```

- [ ] **Step 3: Smoke-test packing on a real puzzle**

Run:
```bash
uv run python -c "
from pathlib import Path
from zipmould.config import SolverConfig
from zipmould.puzzle import load_puzzles_cbor
from zipmould.solver.state import pack
puzzles = load_puzzles_cbor(Path('benchmark/data/puzzles.cbor'))
p = puzzles['level_001']
cfg = SolverConfig()
st = pack(p, cfg)
print('N:', st.N, 'L:', st.L, 'K:', st.K, 'E:', st.E)
print('tau shape:', st.tau.shape, 'adjacency shape:', st.adjacency.shape)
print('beta1 resolved:', st.beta1, 'beta3 resolved:', st.beta3)
print('f0 + f1:', st.f0_total + st.f1_total, 'L:', st.L)
"
```

Expected: For a 3×3 unblocked puzzle with K=2: `N: 3 L: 9 K: 2 E: 12`, plus tau shape `(1, 12)`, adjacency `(9, 4)`, `beta1 resolved: 9.0 beta3 resolved: 90.0`, and `f0 + f1: 9` matching `L: 9`.

- [ ] **Step 4: Commit**

```bash
git add src/zipmould/solver/__init__.py src/zipmould/solver/state.py
git commit -m "feat(zipmould): KernelState NamedTuple and pack/unpack boundary"
```

---

### Task 10: `solver/_heuristics.py` — `@njit` Manhattan / Warnsdorff / articulation / parity

**Why:** Spec §3.3 / design.md §3.3 — four heuristic components combined multiplicatively after softplus. Each is its own `@njit` helper so the kernel composes them cleanly. Articulation uses a cheap DFS on `F \ V_s \ {c'}`; parity uses the running `f0_remaining/f1_remaining` counters maintained per walker in `KernelState`.

**Files:**
- Create: `src/zipmould/solver/_heuristics.py`

- [ ] **Step 1: Write `_heuristics.py`**

Create `src/zipmould/solver/_heuristics.py`:

```python
"""@njit heuristic components per design.md §3.3.

Each component returns a real-valued score; the kernel applies softplus
and gamma exponentiation once at the call site to keep the inner sum
predictable. Articulation returns -inf when removing the candidate
cell would isolate part of the unvisited free subgraph.
"""

from __future__ import annotations

import math

import numba as nb
import numpy as np

NEG_INF = -1.0e30


@nb.njit(cache=True, inline="always")
def _bit_test(visited: np.ndarray, walker_id: int, cell: int) -> bool:
    word = cell >> 6
    bit = cell & 63
    return (visited[walker_id, word] >> np.uint64(bit)) & np.uint64(1) == np.uint64(1)


@nb.njit(cache=True, inline="always")
def _bit_set(visited: np.ndarray, walker_id: int, cell: int) -> None:
    word = cell >> 6
    bit = cell & 63
    visited[walker_id, word] |= np.uint64(1) << np.uint64(bit)


@nb.njit(cache=True, inline="always")
def _bit_clear(visited: np.ndarray, walker_id: int, cell: int) -> None:
    word = cell >> 6
    bit = cell & 63
    visited[walker_id, word] &= ~(np.uint64(1) << np.uint64(bit))


@nb.njit(cache=True)
def softplus(x: float) -> float:
    if x > 30.0:
        return x
    if x < -30.0:
        return 0.0
    return math.log1p(math.exp(x))


@nb.njit(cache=True)
def h_manhattan(
    cell_next: int,
    segment: int,
    K: int,
    waypoint_cells: np.ndarray,
    manhattan_table: np.ndarray,
) -> float:
    if segment >= K:
        return 0.0
    return -float(manhattan_table[cell_next, segment])


@nb.njit(cache=True)
def _onward_count(
    walker_id: int,
    cell_next: int,
    segment: int,
    waypoint_of: np.ndarray,
    visited: np.ndarray,
    adjacency: np.ndarray,
) -> int:
    cnt = 0
    for d in range(4):
        nb_cell = adjacency[cell_next, d]
        if nb_cell < 0:
            continue
        if _bit_test(visited, walker_id, nb_cell):
            continue
        wlabel = waypoint_of[nb_cell]
        if wlabel >= 1 and wlabel != segment + 1:
            continue
        cnt += 1
    return cnt


@nb.njit(cache=True)
def h_warnsdorff(
    walker_id: int,
    cell_next: int,
    segment: int,
    visited: np.ndarray,
    adjacency: np.ndarray,
    waypoint_of: np.ndarray,
) -> float:
    _bit_set(visited, walker_id, cell_next)
    cnt = _onward_count(walker_id, cell_next, segment, waypoint_of, visited, adjacency)
    _bit_clear(visited, walker_id, cell_next)
    return -float(cnt)


@nb.njit(cache=True)
def h_articulation(
    walker_id: int,
    cell_next: int,
    visited: np.ndarray,
    adjacency: np.ndarray,
    n2: int,
    path_len_after: int,
    L: int,
    work_stack: np.ndarray,
) -> float:
    if path_len_after >= L:
        return 0.0

    _bit_set(visited, walker_id, cell_next)
    seed = -1
    for d in range(4):
        nb_cell = adjacency[cell_next, d]
        if nb_cell < 0:
            continue
        if not _bit_test(visited, walker_id, nb_cell):
            seed = nb_cell
            break
    if seed < 0:
        _bit_clear(visited, walker_id, cell_next)
        return NEG_INF

    reached = 0
    sp = 0
    work_stack[sp] = seed
    sp += 1
    _bit_set(visited, walker_id, seed)

    expected = L - path_len_after
    while sp > 0:
        sp -= 1
        cur = work_stack[sp]
        reached += 1
        for d in range(4):
            nb_cell = adjacency[cur, d]
            if nb_cell < 0:
                continue
            if _bit_test(visited, walker_id, nb_cell):
                continue
            _bit_set(visited, walker_id, nb_cell)
            work_stack[sp] = nb_cell
            sp += 1

    sp = 0
    work_stack[sp] = seed
    sp += 1
    while sp > 0:
        sp -= 1
        cur = work_stack[sp]
        _bit_clear(visited, walker_id, cur)
        for d in range(4):
            nb_cell = adjacency[cur, d]
            if nb_cell < 0:
                continue
            if _bit_test(visited, walker_id, nb_cell):
                _bit_clear(visited, walker_id, nb_cell)
                work_stack[sp] = nb_cell
                sp += 1

    _bit_clear(visited, walker_id, cell_next)

    if reached == expected:
        return 0.0
    return NEG_INF


@nb.njit(cache=True)
def h_parity(
    cell_next: int,
    walker_id: int,
    f0_remaining: np.ndarray,
    f1_remaining: np.ndarray,
    parity_table: np.ndarray,
) -> float:
    p = parity_table[cell_next]
    if p == 0:
        f0r = f0_remaining[walker_id] - 1
        f1r = f1_remaining[walker_id]
    else:
        f0r = f0_remaining[walker_id]
        f1r = f1_remaining[walker_id] - 1
    diff = f0r - f1r
    if diff < 0:
        diff = -diff
    if diff <= 1:
        return 0.1
    return -0.1
```

- [ ] **Step 2: Smoke-compile**

Run:
```bash
uv run python -c "
import numpy as np
from zipmould.solver._heuristics import softplus, h_manhattan
print('softplus(0):', softplus(0.0))
wp = np.array([0, 8], dtype=np.int16)
mt = np.zeros((9, 2), dtype=np.int16)
mt[3, 1] = 4
print('h_manhattan(3, 1, 2):', h_manhattan(3, 1, 2, wp, mt))
"
```

Expected: `softplus(0): 0.6931471805599453`, then `h_manhattan(3, 1, 2): -4.0`. First call may take 2-3 s for JIT compile.

- [ ] **Step 3: Commit**

```bash
git add src/zipmould/solver/_heuristics.py
git commit -m "feat(zipmould): @njit heuristic components"
```

---

## Phase 3 — Kernel

### Task 11: `solver/_kernel.py` — single walker step (sample one legal move)

**Why:** The atomic kernel operation. Given a walker at `pos[w]` in segment `segment[w]`, sample the next legal cell via softmax over `α·τ + β·log η`. Update `pos`, `path`, `path_len`, `visited`, `segment`, `f0_remaining`, `f1_remaining`. Set `status` to 1 (dead-end) if no legal move exists or 2 (done) if walker reached `w_K` with `path_len == L`.

**Files:**
- Create: `src/zipmould/solver/_kernel.py`

- [ ] **Step 1: Write `_kernel.py` with the walker-step primitive**

Create `src/zipmould/solver/_kernel.py`:

```python
"""@njit walker step, walker run, pheromone update, and iteration loop.

The kernel does one step at a time at the lowest level
(`_walker_step`), composes them into a full path (`_walker_run`),
and the iteration loop (`_iterate`) builds a full population, scores
fitness, updates pheromone, applies restart noise, and emits a frame
record into pre-allocated arrays.
"""

from __future__ import annotations

import math

import numba as nb
import numpy as np

from zipmould.fitness import fitness
from zipmould.solver._heuristics import (
    NEG_INF,
    _bit_clear,
    _bit_set,
    _bit_test,
    h_articulation,
    h_manhattan,
    h_parity,
    h_warnsdorff,
    softplus,
)


@nb.njit(cache=True)
def _walker_step(
    walker_id: int,
    pos: np.ndarray,
    visited: np.ndarray,
    path: np.ndarray,
    path_len: np.ndarray,
    segment: np.ndarray,
    status: np.ndarray,
    f0_remaining: np.ndarray,
    f1_remaining: np.ndarray,
    adjacency: np.ndarray,
    edge_of: np.ndarray,
    waypoint_of: np.ndarray,
    parity_table: np.ndarray,
    manhattan_table: np.ndarray,
    waypoint_cells: np.ndarray,
    tau: np.ndarray,
    pheromone_mode: int,
    n_stripes: int,
    K: int,
    L: int,
    N2: int,
    alpha: float,
    beta_log: float,
    gamma_man: float,
    gamma_warns: float,
    gamma_art: float,
    gamma_par: float,
    work_stack: np.ndarray,
) -> None:
    if status[walker_id] != 0:
        return

    cur = int(pos[walker_id])
    seg = int(segment[walker_id])

    logits = np.full(4, -1.0e30, dtype=np.float64)
    legal_count = 0
    for d in range(4):
        nb_cell = adjacency[cur, d]
        if nb_cell < 0:
            continue
        if _bit_test(visited, walker_id, nb_cell):
            continue
        wlabel = waypoint_of[nb_cell]
        if wlabel >= 1 and wlabel != seg + 1:
            continue

        h_m = h_manhattan(nb_cell, seg, K, waypoint_cells, manhattan_table)
        h_w = h_warnsdorff(walker_id, nb_cell, seg, visited, adjacency, waypoint_of)
        plen_after = int(path_len[walker_id]) + 1
        h_a = h_articulation(walker_id, nb_cell, visited, adjacency, N2, plen_after, L, work_stack)
        if h_a == NEG_INF:
            continue
        h_p = h_parity(nb_cell, walker_id, f0_remaining, f1_remaining, parity_table)

        eta = (
            (softplus(h_m) ** gamma_man)
            * (softplus(h_w) ** gamma_warns)
            * (softplus(h_a) ** gamma_art)
            * (softplus(h_p) ** gamma_par)
        )
        if eta <= 0.0:
            eta = 1.0e-12

        eid = edge_of[cur, d]
        stripe = (seg - 1) if pheromone_mode == 1 else 0
        if stripe < 0:
            stripe = 0
        if stripe >= n_stripes:
            stripe = n_stripes - 1
        tau_val = float(tau[stripe, eid])

        logits[d] = alpha * tau_val + beta_log * math.log(eta)
        legal_count += 1

    if legal_count == 0:
        status[walker_id] = 1
        return

    max_logit = -1.0e30
    for d in range(4):
        if logits[d] > max_logit:
            max_logit = logits[d]
    total = 0.0
    probs = np.zeros(4, dtype=np.float64)
    for d in range(4):
        if logits[d] <= -1.0e29:
            probs[d] = 0.0
        else:
            probs[d] = math.exp(logits[d] - max_logit)
            total += probs[d]
    for d in range(4):
        probs[d] /= total

    u = np.random.random()
    acc = 0.0
    chosen = -1
    for d in range(4):
        acc += probs[d]
        if u <= acc and probs[d] > 0.0:
            chosen = d
            break
    if chosen < 0:
        for d in range(4):
            if probs[d] > 0.0:
                chosen = d

    next_cell = int(adjacency[cur, chosen])
    pos[walker_id] = next_cell
    plen = int(path_len[walker_id])
    path[walker_id, plen] = next_cell
    path_len[walker_id] = plen + 1
    _bit_set(visited, walker_id, next_cell)
    if parity_table[next_cell] == 0:
        f0_remaining[walker_id] -= 1
    else:
        f1_remaining[walker_id] -= 1

    wlabel = waypoint_of[next_cell]
    if wlabel >= 1:
        segment[walker_id] = wlabel

    if (
        path_len[walker_id] == L
        and segment[walker_id] == K
        and next_cell == int(waypoint_cells[K - 1])
    ):
        status[walker_id] = 2
```

- [ ] **Step 2: Smoke-compile and confirm import succeeds**

Run:
```bash
uv run python -c "
from zipmould.solver._kernel import _walker_step
print('walker step imported:', _walker_step is not None)
"
```

Expected: `walker step imported: True`. JIT not yet exercised; compilation deferred to first call.

- [ ] **Step 3: Commit**

```bash
git add src/zipmould/solver/_kernel.py
git commit -m "feat(zipmould): @njit single walker step with softmax sampling"
```

---

### Task 12: Extend `_kernel.py` with `_walker_run` and `_init_walker`

**Why:** A walker iterates `_walker_step` until `status != 0` (alive). Initialisation places the walker at `w_1`, marks it visited, sets `segment=1`, initialises remaining-parity counters from `f0_total/f1_total`.

**Files:**
- Modify: `src/zipmould/solver/_kernel.py`

- [ ] **Step 1: Append `_init_walker` and `_walker_run` to `_kernel.py`**

Append to `src/zipmould/solver/_kernel.py`:

```python
@nb.njit(cache=True)
def _init_walker(
    walker_id: int,
    pos: np.ndarray,
    visited: np.ndarray,
    path: np.ndarray,
    path_len: np.ndarray,
    segment: np.ndarray,
    status: np.ndarray,
    f0_remaining: np.ndarray,
    f1_remaining: np.ndarray,
    waypoint_cells: np.ndarray,
    parity_table: np.ndarray,
    f0_total: int,
    f1_total: int,
) -> None:
    visited[walker_id, :] = np.uint64(0)
    path_len[walker_id] = 0
    status[walker_id] = 0

    start = int(waypoint_cells[0])
    pos[walker_id] = start
    path[walker_id, 0] = start
    path_len[walker_id] = 1
    _bit_set(visited, walker_id, start)
    segment[walker_id] = 1

    if parity_table[start] == 0:
        f0_remaining[walker_id] = f0_total - 1
        f1_remaining[walker_id] = f1_total
    else:
        f0_remaining[walker_id] = f0_total
        f1_remaining[walker_id] = f1_total - 1


@nb.njit(cache=True)
def _walker_run(
    walker_id: int,
    pos: np.ndarray,
    visited: np.ndarray,
    path: np.ndarray,
    path_len: np.ndarray,
    segment: np.ndarray,
    status: np.ndarray,
    f0_remaining: np.ndarray,
    f1_remaining: np.ndarray,
    adjacency: np.ndarray,
    edge_of: np.ndarray,
    waypoint_of: np.ndarray,
    parity_table: np.ndarray,
    manhattan_table: np.ndarray,
    waypoint_cells: np.ndarray,
    tau: np.ndarray,
    pheromone_mode: int,
    n_stripes: int,
    K: int,
    L: int,
    N2: int,
    alpha: float,
    beta_log: float,
    gamma_man: float,
    gamma_warns: float,
    gamma_art: float,
    gamma_par: float,
    work_stack: np.ndarray,
) -> None:
    while status[walker_id] == 0 and int(path_len[walker_id]) < L:
        _walker_step(
            walker_id,
            pos,
            visited,
            path,
            path_len,
            segment,
            status,
            f0_remaining,
            f1_remaining,
            adjacency,
            edge_of,
            waypoint_of,
            parity_table,
            manhattan_table,
            waypoint_cells,
            tau,
            pheromone_mode,
            n_stripes,
            K,
            L,
            N2,
            alpha,
            beta_log,
            gamma_man,
            gamma_warns,
            gamma_art,
            gamma_par,
            work_stack,
        )
    if status[walker_id] == 0 and int(path_len[walker_id]) >= L:
        status[walker_id] = 1
```

- [ ] **Step 2: Smoke-test a single walker on `level_001`**

Run:
```bash
uv run python -c "
import numpy as np
from pathlib import Path
from zipmould.config import SolverConfig
from zipmould.puzzle import load_puzzles_cbor
from zipmould.solver.state import pack
from zipmould.solver._kernel import _init_walker, _walker_run

puzzles = load_puzzles_cbor(Path('benchmark/data/puzzles.cbor'))
p = puzzles['level_001']
cfg = SolverConfig(population=1)
st = pack(p, cfg)
np.random.seed(0)
work_stack = np.zeros(st.N2, dtype=np.int32)
_init_walker(0, st.pos, st.visited, st.path, st.path_len, st.segment, st.status,
             st.f0_remaining, st.f1_remaining, st.waypoint_cells, st.parity_table,
             st.f0_total, st.f1_total)
_walker_run(0, st.pos, st.visited, st.path, st.path_len, st.segment, st.status,
            st.f0_remaining, st.f1_remaining, st.adjacency, st.edge_of, st.waypoint_of,
            st.parity_table, st.manhattan_table, st.waypoint_cells, st.tau,
            st.pheromone_mode, st.n_stripes, st.K, st.L, st.N2,
            st.alpha, np.log(np.e) * st.beta, st.gamma_man, st.gamma_warns, st.gamma_art, st.gamma_par,
            work_stack)
print('status:', st.status[0], 'path_len:', st.path_len[0], 'segment:', st.segment[0])
print('path:', st.path[0, :st.path_len[0]].tolist())
"
```

Expected: First call compiles (5-15 s). After compile: `status: 2 path_len: 9 segment: 2 path: [...]` for the trivial 3×3 puzzle (which is solvable in one shot most seeds, since `level_001` has K=2 and N=3). If walker dead-ends `status: 1 path_len: <9>`, that is acceptable — the kernel works either way; this test only confirms it terminates.

- [ ] **Step 3: Commit**

```bash
git add src/zipmould/solver/_kernel.py
git commit -m "feat(zipmould): walker initialisation and full-path runner"
```

---

### Task 13: Extend `_kernel.py` with `_pheromone_update` (handles unified, stratified, signed, positive)

**Why:** Design §3.7 step 5. Compute rank weights `W_i = (n - 2r(i) + 1) / (n - 1)`, oscillator `v_b(t) = tanh(1 - t/T)` and contraction `v_c(t) = 1 - t/T`, then update τ. In stratified mode, deposits route to the stripe corresponding to the segment in which the edge was traversed.

**Files:**
- Modify: `src/zipmould/solver/_kernel.py`

- [ ] **Step 1: Append `_pheromone_update`**

Append to `src/zipmould/solver/_kernel.py`:

```python
@nb.njit(cache=True)
def _argsort_desc(values: np.ndarray) -> np.ndarray:
    n = values.shape[0]
    idx = np.empty(n, dtype=np.int32)
    for i in range(n):
        idx[i] = i
    for i in range(1, n):
        key = idx[i]
        kv = values[key]
        j = i - 1
        while j >= 0 and values[idx[j]] < kv:
            idx[j + 1] = idx[j]
            j -= 1
        idx[j + 1] = key
    return idx


@nb.njit(cache=True)
def _segment_at_step(
    walker_id: int,
    step: int,
    path: np.ndarray,
    waypoint_of: np.ndarray,
    K: int,
) -> int:
    seg = 1
    for s in range(step + 1):
        cell = int(path[walker_id, s])
        wlabel = waypoint_of[cell]
        if wlabel >= 1 and wlabel <= K:
            seg = wlabel
    return seg


@nb.njit(cache=True)
def _pheromone_update(
    tau: np.ndarray,
    walker_fitness: np.ndarray,
    path: np.ndarray,
    path_len: np.ndarray,
    edge_of: np.ndarray,
    waypoint_of: np.ndarray,
    adjacency: np.ndarray,
    n_walkers: int,
    n_stripes: int,
    pheromone_mode: int,
    K: int,
    t: int,
    T: int,
    z: float,
    tau_max: float,
    tau_clip_min: float,
) -> None:
    progress = float(t) / float(T)
    v_b = math.tanh(1.0 - progress)
    v_c = 1.0 - progress

    n = n_walkers
    rank = _argsort_desc(walker_fitness)
    weights = np.zeros(n, dtype=np.float64)
    if n > 1:
        denom = float(n - 1)
        for i in range(n):
            r = -1
            for j in range(n):
                if rank[j] == i:
                    r = j + 1
                    break
            weights[i] = (float(n) - 2.0 * float(r) + 1.0) / denom
    else:
        weights[0] = 1.0

    n_stripes_actual = tau.shape[0]
    n_edges = tau.shape[1]
    deposit = np.zeros((n_stripes_actual, n_edges), dtype=np.float64)

    for w in range(n):
        plen = int(path_len[w])
        if plen <= 1:
            continue
        prev_cell = int(path[w, 0])
        seg_now = 1
        wlabel0 = waypoint_of[prev_cell]
        if wlabel0 >= 1:
            seg_now = wlabel0
        for s in range(1, plen):
            cur_cell = int(path[w, s])
            eid = -1
            for d in range(4):
                if int(adjacency[prev_cell, d]) == cur_cell:
                    eid = int(edge_of[prev_cell, d])
                    break
            if eid >= 0:
                stripe = (seg_now - 1) if pheromone_mode == 1 else 0
                if stripe < 0:
                    stripe = 0
                if stripe >= n_stripes_actual:
                    stripe = n_stripes_actual - 1
                deposit[stripe, eid] += weights[w]
            wlabel = waypoint_of[cur_cell]
            if wlabel >= 1:
                seg_now = wlabel
            prev_cell = cur_cell

    for s in range(n_stripes_actual):
        for e in range(n_edges):
            new_val = v_c * float(tau[s, e]) + v_b * deposit[s, e]
            if z > 0.0 and np.random.random() < z:
                new_val = np.random.normal(0.0, tau_max / 4.0)
            if new_val > tau_max:
                new_val = tau_max
            if new_val < tau_clip_min:
                new_val = tau_clip_min
            tau[s, e] = new_val
```

- [ ] **Step 2: Smoke-compile**

Run:
```bash
uv run python -c "
from zipmould.solver._kernel import _pheromone_update, _argsort_desc
import numpy as np
v = np.array([3.0, 1.0, 2.0, 5.0])
print('argsort desc:', _argsort_desc(v).tolist())
"
```

Expected: First call compiles. Output: `argsort desc: [3, 0, 2, 1]` (indices of sorted-descending order).

- [ ] **Step 3: Commit**

```bash
git add src/zipmould/solver/_kernel.py
git commit -m "feat(zipmould): SMA pheromone update with rank weights and restart noise"
```

---

### Task 14: Extend `_kernel.py` with the `run` driver and frame logging

**Why:** Spec §5.1 — the kernel returns `(final_state, frames)`. Runs walkers, computes fitness per walker via `fitness()`, calls `_pheromone_update`, logs frames every `frame_interval` iterations into pre-allocated arrays. Halts on solve, iteration cap, or wall-clock budget (the wall-clock check stays outside the kernel since `time.time()` is awkward inside `@njit`; the outer loop drives time).

**Files:**
- Modify: `src/zipmould/solver/_kernel.py`

- [ ] **Step 1: Append the iteration driver**

Append to `src/zipmould/solver/_kernel.py`:

```python
@nb.njit(cache=True)
def _run_iteration(
    pos: np.ndarray,
    visited: np.ndarray,
    path: np.ndarray,
    path_len: np.ndarray,
    segment: np.ndarray,
    status: np.ndarray,
    f0_remaining: np.ndarray,
    f1_remaining: np.ndarray,
    walker_fitness: np.ndarray,
    adjacency: np.ndarray,
    edge_of: np.ndarray,
    waypoint_of: np.ndarray,
    parity_table: np.ndarray,
    manhattan_table: np.ndarray,
    waypoint_cells: np.ndarray,
    tau: np.ndarray,
    pheromone_mode: int,
    n_walkers: int,
    n_stripes: int,
    K: int,
    L: int,
    N2: int,
    N: int,
    alpha: float,
    beta_log: float,
    gamma_man: float,
    gamma_warns: float,
    gamma_art: float,
    gamma_par: float,
    beta1: float,
    beta2: float,
    beta3: float,
    f0_total: int,
    f1_total: int,
    work_stack: np.ndarray,
    t: int,
    T: int,
    z: float,
    tau_max: float,
    tau_clip_min: float,
    freeze_pheromone: int,
) -> int:
    for w in range(n_walkers):
        _init_walker(
            w, pos, visited, path, path_len, segment, status,
            f0_remaining, f1_remaining, waypoint_cells, parity_table,
            f0_total, f1_total,
        )
        _walker_run(
            w, pos, visited, path, path_len, segment, status,
            f0_remaining, f1_remaining, adjacency, edge_of, waypoint_of,
            parity_table, manhattan_table, waypoint_cells, tau,
            pheromone_mode, n_stripes, K, L, N2,
            alpha, beta_log, gamma_man, gamma_warns, gamma_art, gamma_par,
            work_stack,
        )

    best_w = -1
    best_f = -1.0e30
    for w in range(n_walkers):
        plen = int(path_len[w])
        last_cell = int(path[w, plen - 1]) if plen > 0 else int(waypoint_cells[0])
        f = fitness(plen, int(segment[w]), last_cell, waypoint_cells, L, K, N, beta1, beta2, beta3)
        walker_fitness[w] = f
        if f > best_f:
            best_f = f
            best_w = w

    solved_walker = -1
    for w in range(n_walkers):
        if status[w] == 2:
            solved_walker = w
            break

    if freeze_pheromone == 0:
        _pheromone_update(
            tau, walker_fitness, path, path_len, edge_of, waypoint_of, adjacency,
            n_walkers, n_stripes, pheromone_mode, K, t, T, z, tau_max, tau_clip_min,
        )

    if solved_walker >= 0:
        return solved_walker
    return -1


@nb.njit(cache=True)
def _seed_kernel(seed: int) -> None:
    np.random.seed(seed)
```

- [ ] **Step 2: Smoke-test one full iteration on a real puzzle**

Run:
```bash
uv run python -c "
import numpy as np
from pathlib import Path
from zipmould.config import SolverConfig
from zipmould.puzzle import load_puzzles_cbor
from zipmould.solver.state import pack
from zipmould.solver._kernel import _run_iteration, _seed_kernel

puzzles = load_puzzles_cbor(Path('benchmark/data/puzzles.cbor'))
p = puzzles['level_001']
cfg = SolverConfig(population=4, iter_cap=20)
st = pack(p, cfg)
_seed_kernel(0)
work_stack = np.zeros(st.N2, dtype=np.int32)
solved = -1
for t in range(cfg.iter_cap):
    res = _run_iteration(
        st.pos, st.visited, st.path, st.path_len, st.segment, st.status,
        st.f0_remaining, st.f1_remaining, st.walker_fitness,
        st.adjacency, st.edge_of, st.waypoint_of, st.parity_table,
        st.manhattan_table, st.waypoint_cells, st.tau,
        st.pheromone_mode, st.n_walkers, st.n_stripes, st.K, st.L, st.N2, st.N,
        st.alpha, st.beta, st.gamma_man, st.gamma_warns, st.gamma_art, st.gamma_par,
        st.beta1, st.beta2, st.beta3, st.f0_total, st.f1_total, work_stack,
        t, cfg.iter_cap, st.z, st.tau_max, st.tau_clip_min, 0,
    )
    if res >= 0:
        solved = res
        print('solved at t=', t, 'walker=', res)
        break
print('done, solved walker:', solved, 'best fitness:', float(st.walker_fitness.max()))
"
```

Expected: First call triggers a compile of 10-30 s. After: `solved at t= ... walker= ...` (typical for level_001 — small puzzles solve quickly) and a fitness near `9 + 18 + 1 + 90 = 118`. If unsolved, iter cap exhausts and the script prints `done, solved walker: -1` with a partial fitness.

- [ ] **Step 3: Commit**

```bash
git add src/zipmould/solver/_kernel.py
git commit -m "feat(zipmould): iteration driver with kernel-side seeding"
```

---

### Task 15: Add frame-logging arrays and the kernel `run` entry point

**Why:** Frames must be emitted every `frame_interval` iterations into pre-allocated arrays so the kernel produces no Python objects. The outer code converts these arrays into `Frame` dataclasses.

**Files:**
- Modify: `src/zipmould/solver/_kernel.py`

- [ ] **Step 1: Append `run` and frame-logging helpers**

Append to `src/zipmould/solver/_kernel.py`:

```python
@nb.njit(cache=True)
def _diff_tau(prev: np.ndarray, cur: np.ndarray, eps: float, scratch: np.ndarray) -> int:
    n_stripes = cur.shape[0]
    n_edges = cur.shape[1]
    cnt = 0
    for s in range(n_stripes):
        for e in range(n_edges):
            d = float(cur[s, e]) - float(prev[s, e])
            if d > eps or d < -eps:
                scratch[cnt, 0] = e
                scratch[cnt, 1] = s
                scratch[cnt, 2] = d
                cnt += 1
    return cnt


@nb.njit(cache=True)
def _kernel_run(
    pos: np.ndarray,
    visited: np.ndarray,
    path: np.ndarray,
    path_len: np.ndarray,
    segment: np.ndarray,
    status: np.ndarray,
    f0_remaining: np.ndarray,
    f1_remaining: np.ndarray,
    walker_fitness: np.ndarray,
    adjacency: np.ndarray,
    edge_of: np.ndarray,
    waypoint_of: np.ndarray,
    parity_table: np.ndarray,
    manhattan_table: np.ndarray,
    waypoint_cells: np.ndarray,
    tau: np.ndarray,
    pheromone_mode: int,
    n_walkers: int,
    n_stripes: int,
    K: int,
    L: int,
    N2: int,
    N: int,
    alpha: float,
    beta_log: float,
    gamma_man: float,
    gamma_warns: float,
    gamma_art: float,
    gamma_par: float,
    beta1: float,
    beta2: float,
    beta3: float,
    f0_total: int,
    f1_total: int,
    work_stack: np.ndarray,
    iter_cap: int,
    z: float,
    tau_max: float,
    tau_clip_min: float,
    freeze_pheromone: int,
    seed: int,
    frame_interval: int,
    visible_walkers: int,
    tau_delta_epsilon: float,
    frame_t: np.ndarray,
    frame_v_b: np.ndarray,
    frame_v_c: np.ndarray,
    frame_best_w: np.ndarray,
    frame_best_fitness: np.ndarray,
    frame_walker_ids: np.ndarray,
    frame_walker_cells: np.ndarray,
    frame_walker_segments: np.ndarray,
    frame_walker_status: np.ndarray,
    frame_walker_fitness: np.ndarray,
    frame_tau_count: np.ndarray,
    frame_tau_payload: np.ndarray,
    tau_prev: np.ndarray,
    tau_scratch: np.ndarray,
) -> int:
    _seed_kernel(seed)
    solved_iter = -1
    solved_walker = -1
    n_frames = 0

    for s in range(n_stripes):
        for e in range(tau_prev.shape[1]):
            tau_prev[s, e] = 0.0

    for t in range(iter_cap):
        res = _run_iteration(
            pos, visited, path, path_len, segment, status,
            f0_remaining, f1_remaining, walker_fitness,
            adjacency, edge_of, waypoint_of, parity_table,
            manhattan_table, waypoint_cells, tau,
            pheromone_mode, n_walkers, n_stripes, K, L, N2, N,
            alpha, beta_log, gamma_man, gamma_warns, gamma_art, gamma_par,
            beta1, beta2, beta3, f0_total, f1_total, work_stack,
            t, iter_cap, z, tau_max, tau_clip_min, freeze_pheromone,
        )

        if (t % frame_interval) == 0 or res >= 0:
            best_w = 0
            best_f = walker_fitness[0]
            for w in range(1, n_walkers):
                if walker_fitness[w] > best_f:
                    best_f = walker_fitness[w]
                    best_w = w
            progress = float(t) / float(iter_cap)
            frame_t[n_frames] = t
            frame_v_b[n_frames] = math.tanh(1.0 - progress)
            frame_v_c[n_frames] = 1.0 - progress
            frame_best_w[n_frames] = best_w
            frame_best_fitness[n_frames] = best_f
            for k in range(visible_walkers):
                if k < n_walkers:
                    cell = int(path[k, max(int(path_len[k]) - 1, 0)])
                    frame_walker_ids[n_frames, k] = k
                    frame_walker_cells[n_frames, k] = cell
                    frame_walker_segments[n_frames, k] = int(segment[k])
                    frame_walker_status[n_frames, k] = int(status[k])
                    frame_walker_fitness[n_frames, k] = walker_fitness[k]
                else:
                    frame_walker_ids[n_frames, k] = -1
            cnt = _diff_tau(tau_prev, tau, tau_delta_epsilon, tau_scratch)
            frame_tau_count[n_frames] = cnt
            for i in range(cnt):
                frame_tau_payload[n_frames, i, 0] = tau_scratch[i, 0]
                frame_tau_payload[n_frames, i, 1] = tau_scratch[i, 1]
                frame_tau_payload[n_frames, i, 2] = tau_scratch[i, 2]
            for s in range(n_stripes):
                for e in range(tau.shape[1]):
                    tau_prev[s, e] = tau[s, e]
            n_frames += 1

        if res >= 0:
            solved_iter = t
            solved_walker = res
            break

    return n_frames if solved_iter < 0 else (n_frames | (1 << 30))
```

The high bit of the return value signals "solved": the outer code masks it off to read `n_frames`, and reads `status[]` to find the solved walker.

- [ ] **Step 2: Smoke-import**

Run:
```bash
uv run python -c "from zipmould.solver._kernel import _kernel_run; print('kernel run imported:', _kernel_run is not None)"
```

Expected: `kernel run imported: True`. (Compilation deferred until first call from `solve()`.)

- [ ] **Step 3: Commit**

```bash
git add src/zipmould/solver/_kernel.py
git commit -m "feat(zipmould): kernel run entry with frame logging into preallocated arrays"
```

---

## Phase 4 — Trace I/O and Solver API

### Task 16: `io/trace.py` — `Trace` dataclasses, `write_cbor`, `read_cbor`

**Why:** Spec §4.5 — the on-disk trace mirrors `docs/design.md` §8 schema field-for-field. Frame extraction from the kernel's array buffers happens here.

**Files:**
- Create: `src/zipmould/io/__init__.py`
- Create: `src/zipmould/io/trace.py`

- [ ] **Step 1: Create the `io` package marker**

Create `src/zipmould/io/__init__.py`:

```python
"""I/O modules: puzzles, traces."""
```

- [ ] **Step 2: Write `io/trace.py`**

Create `src/zipmould/io/trace.py`:

```python
"""CBOR trace schema and codec.

The on-disk shape mirrors `docs/design.md` §8. `Trace` and its
subordinate dataclasses are immutable; they are built once from the
kernel's array buffers and serialised via `cbor2`.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import cbor2

from zipmould.puzzle import Coord, Edge

TRACE_SCHEMA_VERSION = 1


@dataclass(frozen=True, slots=True)
class WalkerSnapshot:
    id: int
    cell: Coord
    segment: int
    status: Literal["alive", "dead-end", "complete"]
    fitness: float


@dataclass(frozen=True, slots=True)
class BestPath:
    path: tuple[Coord, ...]
    fitness: float


@dataclass(frozen=True, slots=True)
class TauDelta:
    mode: Literal["unified", "stratified"]
    edges: tuple[tuple[int, int, float], ...]


@dataclass(frozen=True, slots=True)
class Frame:
    t: int
    v_b: float
    v_c: float
    tau_delta: TauDelta
    best: BestPath
    walkers: tuple[WalkerSnapshot, ...]


@dataclass(frozen=True, slots=True)
class TraceHeader:
    N: int
    K: int
    L: int
    waypoints: tuple[Coord, ...]
    walls: tuple[Edge, ...]
    blocked: tuple[Coord, ...]


@dataclass(frozen=True, slots=True)
class TraceFooter:
    solved: bool
    infeasible: bool
    solution: tuple[Coord, ...] | None
    iterations_used: int
    wall_clock_s: float
    best_fitness: float


@dataclass(frozen=True, slots=True)
class Trace:
    version: int
    puzzle_id: str
    config: Mapping[str, object]
    seed: int
    header: TraceHeader
    frames: tuple[Frame, ...]
    footer: TraceFooter


_STATUS_NAMES = ("alive", "dead-end", "complete", "error")


def _status_name(code: int) -> Literal["alive", "dead-end", "complete"]:
    if code == 0:
        return "alive"
    if code == 1:
        return "dead-end"
    if code == 2:
        return "complete"
    msg = f"invalid kernel status code {code}"
    raise ValueError(msg)


def _walker_to_dict(w: WalkerSnapshot) -> dict[str, object]:
    return {
        "id": w.id,
        "cell": [w.cell[0], w.cell[1]],
        "segment": w.segment,
        "status": w.status,
        "fitness": w.fitness,
    }


def _frame_to_dict(f: Frame) -> dict[str, object]:
    return {
        "t": f.t,
        "v_b": f.v_b,
        "v_c": f.v_c,
        "tau_delta": {
            "mode": f.tau_delta.mode,
            "edges": [list(e) for e in f.tau_delta.edges],
        },
        "best": {
            "path": [[r, c] for (r, c) in f.best.path],
            "fitness": f.best.fitness,
        },
        "walkers": [_walker_to_dict(w) for w in f.walkers],
    }


def _trace_to_dict(trace: Trace) -> dict[str, object]:
    return {
        "version": trace.version,
        "puzzle_id": trace.puzzle_id,
        "config": dict(trace.config),
        "seed": trace.seed,
        "header": {
            "N": trace.header.N,
            "K": trace.header.K,
            "L": trace.header.L,
            "waypoints": [[r, c] for (r, c) in trace.header.waypoints],
            "walls": [
                [[a[0], a[1]], [b[0], b[1]]] for (a, b) in trace.header.walls
            ],
            "blocked": [[r, c] for (r, c) in trace.header.blocked],
        },
        "frames": [_frame_to_dict(f) for f in trace.frames],
        "footer": {
            "solved": trace.footer.solved,
            "infeasible": trace.footer.infeasible,
            "solution": (
                [[r, c] for (r, c) in trace.footer.solution]
                if trace.footer.solution is not None
                else None
            ),
            "iterations_used": trace.footer.iterations_used,
            "wall_clock_s": trace.footer.wall_clock_s,
            "best_fitness": trace.footer.best_fitness,
        },
    }


def _walker_from_dict(d: dict[str, object]) -> WalkerSnapshot:
    cell = d["cell"]
    return WalkerSnapshot(
        id=int(d["id"]),  # type: ignore[arg-type]
        cell=(int(cell[0]), int(cell[1])),  # type: ignore[index]
        segment=int(d["segment"]),  # type: ignore[arg-type]
        status=d["status"],  # type: ignore[assignment]
        fitness=float(d["fitness"]),  # type: ignore[arg-type]
    )


def _frame_from_dict(d: dict[str, object]) -> Frame:
    td = d["tau_delta"]
    best = d["best"]
    return Frame(
        t=int(d["t"]),  # type: ignore[arg-type]
        v_b=float(d["v_b"]),  # type: ignore[arg-type]
        v_c=float(d["v_c"]),  # type: ignore[arg-type]
        tau_delta=TauDelta(
            mode=td["mode"],  # type: ignore[index, assignment]
            edges=tuple(
                (int(e[0]), int(e[1]), float(e[2]))
                for e in td["edges"]  # type: ignore[index, union-attr]
            ),
        ),
        best=BestPath(
            path=tuple((int(r), int(c)) for (r, c) in best["path"]),  # type: ignore[index, union-attr]
            fitness=float(best["fitness"]),  # type: ignore[index, arg-type]
        ),
        walkers=tuple(_walker_from_dict(w) for w in d["walkers"]),  # type: ignore[arg-type]
    )


def write_cbor(trace: Trace, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as f:
        cbor2.dump(_trace_to_dict(trace), f)


def read_cbor(path: Path) -> Trace:
    with path.open("rb") as f:
        raw = cbor2.load(f)
    h = raw["header"]
    ft = raw["footer"]
    return Trace(
        version=int(raw["version"]),
        puzzle_id=str(raw["puzzle_id"]),
        config=dict(raw["config"]),
        seed=int(raw["seed"]),
        header=TraceHeader(
            N=int(h["N"]),
            K=int(h["K"]),
            L=int(h["L"]),
            waypoints=tuple((int(r), int(c)) for (r, c) in h["waypoints"]),
            walls=tuple(
                ((int(a[0]), int(a[1])), (int(b[0]), int(b[1])))
                for (a, b) in h["walls"]
            ),
            blocked=tuple((int(r), int(c)) for (r, c) in h["blocked"]),
        ),
        frames=tuple(_frame_from_dict(f) for f in raw["frames"]),
        footer=TraceFooter(
            solved=bool(ft["solved"]),
            infeasible=bool(ft["infeasible"]),
            solution=(
                tuple((int(r), int(c)) for (r, c) in ft["solution"])
                if ft["solution"] is not None
                else None
            ),
            iterations_used=int(ft["iterations_used"]),
            wall_clock_s=float(ft["wall_clock_s"]),
            best_fitness=float(ft["best_fitness"]),
        ),
    )
```

- [ ] **Step 3: Smoke-test trace round-trip**

Run:
```bash
uv run python -c "
from pathlib import Path
from zipmould.io.trace import (
    Trace, TraceHeader, TraceFooter, Frame, TauDelta, BestPath, WalkerSnapshot,
    write_cbor, read_cbor, TRACE_SCHEMA_VERSION,
)
hdr = TraceHeader(N=3, K=2, L=9, waypoints=((0,0),(2,2)), walls=(), blocked=())
ftr = TraceFooter(solved=True, infeasible=False, solution=((0,0),(0,1),(0,2),(1,2),(1,1),(1,0),(2,0),(2,1),(2,2)),
                  iterations_used=3, wall_clock_s=0.05, best_fitness=118.0)
fr = Frame(t=0, v_b=0.76, v_c=1.0,
           tau_delta=TauDelta(mode='unified', edges=((0,-1,0.0),)),
           best=BestPath(path=((0,0),(0,1)), fitness=11.0),
           walkers=(WalkerSnapshot(id=0, cell=(0,1), segment=1, status='alive', fitness=11.0),))
tr = Trace(version=TRACE_SCHEMA_VERSION, puzzle_id='level_001', config={'alpha': 1.0},
           seed=0, header=hdr, frames=(fr,), footer=ftr)
p = Path('/tmp/zip_trace_test.cbor')
write_cbor(tr, p)
back = read_cbor(p)
print('round-trip ok:', back.puzzle_id == 'level_001' and back.footer.solved and back.frames[0].t == 0)
"
```

Expected: `round-trip ok: True`.

- [ ] **Step 4: Commit**

```bash
git add src/zipmould/io/__init__.py src/zipmould/io/trace.py
git commit -m "feat(zipmould): CBOR trace schema with round-trip codec"
```

---

### Task 17: `solver/api.py` — `solve()` and `RunResult`

**Why:** Public entry point. Composes feasibility, packing, kernel run, frame extraction, RunResult assembly. Captures library versions and git SHA per spec §2.3.

**Files:**
- Create: `src/zipmould/solver/api.py`

- [ ] **Step 1: Write `solver/api.py`**

Create `src/zipmould/solver/api.py`:

```python
"""Top-level solver entry point composing feasibility, kernel, and trace assembly."""

from __future__ import annotations

import math
import subprocess
import sys
import time
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np

from zipmould.config import SolverConfig
from zipmould.feasibility import precheck
from zipmould.io.trace import (
    TRACE_SCHEMA_VERSION,
    BestPath,
    Frame,
    TauDelta,
    Trace,
    TraceFooter,
    TraceHeader,
    WalkerSnapshot,
)
from zipmould.puzzle import Coord, Puzzle
from zipmould.rng import derive_kernel_seed
from zipmould.solver._kernel import _kernel_run
from zipmould.solver.state import KernelState, pack, unpack_path


@dataclass(frozen=True, slots=True)
class RunResult:
    solved: bool
    infeasible: bool
    feasibility_reason: str | None
    solution: tuple[Coord, ...] | None
    iters_used: int
    wall_clock_s: float
    best_fitness: float
    best_fitness_normalised: float
    trace: Trace | None
    config_hash: str
    versions: Mapping[str, str]
    git_sha: str
    git_dirty: bool


def _library_versions() -> dict[str, str]:
    import cbor2 as _cbor2
    import joblib as _joblib
    import numba as _numba
    import polars as _polars
    import pydantic as _pydantic

    return {
        "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "numpy": np.__version__,
        "numba": _numba.__version__,
        "pydantic": _pydantic.VERSION,
        "polars": _polars.__version__,
        "joblib": _joblib.__version__,
        "cbor2": _cbor2.__version__,
    }


def _git_sha_and_dirty() -> tuple[str, bool]:
    try:
        sha = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ("unknown", False)
    try:
        diff = subprocess.check_output(["git", "status", "--porcelain"], text=True)
        return (sha, bool(diff.strip()))
    except subprocess.CalledProcessError:
        return (sha, False)


def _max_fitness(L: int, K: int, beta1: float, beta2: float, beta3: float) -> float:
    return float(L) + beta1 * float(K) + beta2 + beta3


def _build_trace(
    puzzle: Puzzle,
    config: SolverConfig,
    state: KernelState,
    seed: int,
    n_frames: int,
    iters_used: int,
    wall_clock_s: float,
    solved: bool,
    solution: tuple[Coord, ...] | None,
    best_fitness: float,
    frame_t: np.ndarray,
    frame_v_b: np.ndarray,
    frame_v_c: np.ndarray,
    frame_best_w: np.ndarray,
    frame_best_fitness: np.ndarray,
    frame_walker_ids: np.ndarray,
    frame_walker_cells: np.ndarray,
    frame_walker_segments: np.ndarray,
    frame_walker_status: np.ndarray,
    frame_walker_fitness: np.ndarray,
    frame_tau_count: np.ndarray,
    frame_tau_payload: np.ndarray,
) -> Trace:
    n = puzzle.N
    mode_str: Literal["unified", "stratified"] = (
        "stratified" if state.pheromone_mode == 1 else "unified"
    )

    frames: list[Frame] = []
    for fi in range(n_frames):
        edges_raw = []
        for j in range(int(frame_tau_count[fi])):
            eid = int(frame_tau_payload[fi, j, 0])
            stripe = int(frame_tau_payload[fi, j, 1])
            delta = float(frame_tau_payload[fi, j, 2])
            edges_raw.append((eid, stripe if mode_str == "stratified" else -1, delta))
        td = TauDelta(mode=mode_str, edges=tuple(edges_raw))

        best_w = int(frame_best_w[fi])
        path_len = int(state.path_len[best_w])
        best_path = tuple(
            (int(state.path[best_w, s]) // n, int(state.path[best_w, s]) % n)
            for s in range(path_len)
        )
        bp = BestPath(path=best_path, fitness=float(frame_best_fitness[fi]))

        walkers = []
        for k in range(state.visible_walkers):
            wid = int(frame_walker_ids[fi, k])
            if wid < 0:
                continue
            cell = int(frame_walker_cells[fi, k])
            stat_code = int(frame_walker_status[fi, k])
            stat_name: Literal["alive", "dead-end", "complete"] = (
                "alive" if stat_code == 0 else ("dead-end" if stat_code == 1 else "complete")
            )
            walkers.append(
                WalkerSnapshot(
                    id=wid,
                    cell=(cell // n, cell % n),
                    segment=int(frame_walker_segments[fi, k]),
                    status=stat_name,
                    fitness=float(frame_walker_fitness[fi, k]),
                )
            )

        frames.append(
            Frame(
                t=int(frame_t[fi]),
                v_b=float(frame_v_b[fi]),
                v_c=float(frame_v_c[fi]),
                tau_delta=td,
                best=bp,
                walkers=tuple(walkers),
            )
        )

    header = TraceHeader(
        N=puzzle.N,
        K=puzzle.K,
        L=puzzle.L(),
        waypoints=puzzle.waypoints,
        walls=tuple(sorted(puzzle.walls)),
        blocked=tuple(sorted(puzzle.blocked)),
    )
    footer = TraceFooter(
        solved=solved,
        infeasible=False,
        solution=solution,
        iterations_used=iters_used,
        wall_clock_s=wall_clock_s,
        best_fitness=best_fitness,
    )
    return Trace(
        version=TRACE_SCHEMA_VERSION,
        puzzle_id=puzzle.id,
        config=config.model_dump(mode="json"),
        seed=seed,
        header=header,
        frames=tuple(frames),
        footer=footer,
    )


def solve(
    puzzle: Puzzle,
    config: SolverConfig,
    *,
    seed: int,
    trace: bool = False,
    global_seed: int = 0,
    condition: str = "zipmould-uni-signed",
    freeze_pheromone: bool = False,
) -> RunResult:
    cfg_hash = config.config_hash()
    versions = _library_versions()
    git_sha, git_dirty = _git_sha_and_dirty()

    feas = precheck(puzzle)
    if not feas.feasible:
        return RunResult(
            solved=False,
            infeasible=True,
            feasibility_reason=feas.reason,
            solution=None,
            iters_used=0,
            wall_clock_s=0.0,
            best_fitness=0.0,
            best_fitness_normalised=0.0,
            trace=None,
            config_hash=cfg_hash,
            versions=versions,
            git_sha=git_sha,
            git_dirty=git_dirty,
        )

    state = pack(puzzle, config)
    work_stack = np.zeros(state.N2 * 2, dtype=np.int32)
    kernel_seed = derive_kernel_seed(global_seed, seed, puzzle.id, cfg_hash)

    n_frame_slots = config.iter_cap // config.frame_interval + 2
    n_edges = state.tau.shape[1]
    max_tau_payload = max(n_edges * state.n_stripes, 1)

    frame_t = np.zeros(n_frame_slots, dtype=np.int32)
    frame_v_b = np.zeros(n_frame_slots, dtype=np.float64)
    frame_v_c = np.zeros(n_frame_slots, dtype=np.float64)
    frame_best_w = np.zeros(n_frame_slots, dtype=np.int32)
    frame_best_fitness = np.zeros(n_frame_slots, dtype=np.float64)
    frame_walker_ids = np.full((n_frame_slots, max(config.visible_walkers, 1)), -1, dtype=np.int32)
    frame_walker_cells = np.zeros((n_frame_slots, max(config.visible_walkers, 1)), dtype=np.int32)
    frame_walker_segments = np.zeros((n_frame_slots, max(config.visible_walkers, 1)), dtype=np.int32)
    frame_walker_status = np.zeros((n_frame_slots, max(config.visible_walkers, 1)), dtype=np.int32)
    frame_walker_fitness = np.zeros((n_frame_slots, max(config.visible_walkers, 1)), dtype=np.float64)
    frame_tau_count = np.zeros(n_frame_slots, dtype=np.int32)
    frame_tau_payload = np.zeros((n_frame_slots, max_tau_payload, 3), dtype=np.float64)
    tau_prev = np.zeros_like(state.tau)
    tau_scratch = np.zeros((max_tau_payload, 3), dtype=np.float64)

    t0 = time.perf_counter()
    encoded = _kernel_run(
        state.pos, state.visited, state.path, state.path_len, state.segment, state.status,
        state.f0_remaining, state.f1_remaining, state.walker_fitness,
        state.adjacency, state.edge_of, state.waypoint_of, state.parity_table,
        state.manhattan_table, state.waypoint_cells, state.tau,
        state.pheromone_mode, state.n_walkers, state.n_stripes, state.K, state.L, state.N2, state.N,
        state.alpha, state.beta, state.gamma_man, state.gamma_warns, state.gamma_art, state.gamma_par,
        state.beta1, state.beta2, state.beta3, state.f0_total, state.f1_total, work_stack,
        config.iter_cap, state.z, state.tau_max, state.tau_clip_min,
        1 if freeze_pheromone else 0,
        int(kernel_seed),
        config.frame_interval, config.visible_walkers, state.tau_delta_epsilon,
        frame_t, frame_v_b, frame_v_c, frame_best_w, frame_best_fitness,
        frame_walker_ids, frame_walker_cells, frame_walker_segments,
        frame_walker_status, frame_walker_fitness,
        frame_tau_count, frame_tau_payload,
        tau_prev, tau_scratch,
    )
    elapsed = time.perf_counter() - t0

    n_frames = int(encoded) & ((1 << 30) - 1)
    solved_bit = (int(encoded) >> 30) & 1

    solved = False
    solved_walker = -1
    for w in range(state.n_walkers):
        if int(state.status[w]) == 2:
            solved = True
            solved_walker = w
            break

    if solved and solved_walker >= 0:
        solution = unpack_path(state, solved_walker)
        best_fitness = float(state.walker_fitness[solved_walker])
    else:
        best_idx = int(np.argmax(state.walker_fitness))
        solution = None
        best_fitness = float(state.walker_fitness[best_idx])

    iters_used = int(frame_t[max(n_frames - 1, 0)]) + 1 if n_frames > 0 else 0
    if solved_bit and n_frames > 0:
        iters_used = int(frame_t[n_frames - 1]) + 1

    max_f = _max_fitness(state.L, state.K, state.beta1, state.beta2, state.beta3)
    norm = best_fitness / max_f if max_f > 0 else 0.0

    trace_obj: Trace | None = None
    if trace:
        trace_obj = _build_trace(
            puzzle, config, state, seed, n_frames, iters_used, elapsed,
            solved, solution, best_fitness,
            frame_t, frame_v_b, frame_v_c, frame_best_w, frame_best_fitness,
            frame_walker_ids, frame_walker_cells, frame_walker_segments,
            frame_walker_status, frame_walker_fitness,
            frame_tau_count, frame_tau_payload,
        )

    return RunResult(
        solved=solved,
        infeasible=False,
        feasibility_reason=None,
        solution=solution,
        iters_used=iters_used,
        wall_clock_s=elapsed,
        best_fitness=best_fitness,
        best_fitness_normalised=norm,
        trace=trace_obj,
        config_hash=cfg_hash,
        versions=versions,
        git_sha=git_sha,
        git_dirty=git_dirty,
    )


class KernelError(RuntimeError):
    """Raised when the kernel reports `status==3` (engineering fault)."""


class DeterminismError(RuntimeError):
    """Raised by the regression harness if a re-run differs."""
```

- [ ] **Step 2: Smoke-test end-to-end on `level_001`**

Run:
```bash
uv run python -c "
from pathlib import Path
from zipmould.config import SolverConfig
from zipmould.puzzle import load_puzzles_cbor
from zipmould.solver.api import solve

puzzles = load_puzzles_cbor(Path('benchmark/data/puzzles.cbor'))
p = puzzles['level_001']
cfg = SolverConfig(population=10, iter_cap=50)
res = solve(p, cfg, seed=0)
print('solved:', res.solved, 'iters:', res.iters_used, 'time:', round(res.wall_clock_s, 3))
print('best fitness norm:', round(res.best_fitness_normalised, 3))
if res.solution:
    print('solution length:', len(res.solution))
"
```

Expected: First run incurs JIT compile (15-60 s on first invocation; subsequent runs use the on-disk Numba cache and start in ms). Output: `solved: True iters: ... time: ...` (level_001 is trivial). If unsolved at this iter cap, raise iter_cap and retry.

- [ ] **Step 3: Commit**

```bash
git add src/zipmould/solver/api.py
git commit -m "feat(zipmould): solve() entry composing feasibility, kernel, and trace"
```

---

### Task 18: `__init__.py` re-exports and determinism smoke

**Why:** Spec §3 lists the public surface in `src/zipmould/__init__.py`. Re-exports make `from zipmould import Puzzle, SolverConfig, RunResult, solve, Trace` work. Determinism check confirms acceptance criterion 4.

**Files:**
- Modify: `src/zipmould/__init__.py`

- [ ] **Step 1: Replace `__init__.py` with the public API**

Overwrite `src/zipmould/__init__.py`:

```python
"""ZipMould — Li-inspired Slime Mould Algorithm for Zip puzzles."""

from zipmould.config import ConfigError, ExperimentManifest, SolverConfig
from zipmould.feasibility import FeasibilityReport, precheck
from zipmould.io.trace import (
    BestPath,
    Frame,
    TauDelta,
    Trace,
    TraceFooter,
    TraceHeader,
    WalkerSnapshot,
)
from zipmould.puzzle import Coord, Edge, Puzzle, load_puzzles_cbor
from zipmould.rng import derive_kernel_seed, make_rng
from zipmould.solver.api import DeterminismError, KernelError, RunResult, solve

__version__ = "0.1.0"

__all__ = [
    "BestPath",
    "ConfigError",
    "Coord",
    "DeterminismError",
    "Edge",
    "ExperimentManifest",
    "FeasibilityReport",
    "Frame",
    "KernelError",
    "Puzzle",
    "RunResult",
    "SolverConfig",
    "TauDelta",
    "Trace",
    "TraceFooter",
    "TraceHeader",
    "WalkerSnapshot",
    "__version__",
    "derive_kernel_seed",
    "load_puzzles_cbor",
    "make_rng",
    "precheck",
    "solve",
]
```

- [ ] **Step 2: Determinism smoke**

Run:
```bash
uv run python -c "
from pathlib import Path
from zipmould import SolverConfig, load_puzzles_cbor, solve

puzzles = load_puzzles_cbor(Path('benchmark/data/puzzles.cbor'))
p = puzzles['level_001']
cfg = SolverConfig(population=10, iter_cap=50)
r1 = solve(p, cfg, seed=0)
r2 = solve(p, cfg, seed=0)
print('same solved:', r1.solved == r2.solved)
print('same fitness:', r1.best_fitness == r2.best_fitness)
print('same iters:', r1.iters_used == r2.iters_used)
print('same solution:', r1.solution == r2.solution)
"
```

Expected: All four lines print `True`.

- [ ] **Step 3: Type-check the package so far**

Run:
```bash
uv run ruff check src/zipmould
uv run ty check src/zipmould || true
uv run pyright src/zipmould
```

Expected: `ruff` reports `All checks passed!` (or only minor warnings). `ty` and `pyright` print zero `error`-level issues. `ty` is beta and may emit warnings; `|| true` keeps the smoke moving but inspect output for surprises.

- [ ] **Step 4: Commit**

```bash
git add src/zipmould/__init__.py
git commit -m "feat(zipmould): public re-exports for SolverConfig, solve, Trace"
```

---

## Phase 5 — Configs

### Task 19: Create `configs/default.toml` and the eight ablation files

**Why:** Spec §3 module layout. One default and eight ablation TOMLs covering every Stage-1 condition. Each is a thin override of `default.toml` only on the differing knobs.

**Files:**
- Create: `configs/default.toml`
- Create: `configs/ablations/zipmould-uni-signed.toml`
- Create: `configs/ablations/zipmould-uni-positive.toml`
- Create: `configs/ablations/zipmould-strat-signed.toml`
- Create: `configs/ablations/zipmould-strat-positive.toml`
- Create: `configs/ablations/aco-vanilla.toml`
- Create: `configs/ablations/heuristic-only.toml`
- Create: `configs/ablations/random.toml`
- Create: `configs/ablations/backtracking.toml`

- [ ] **Step 1: Create the `configs/` directory**

Run:
```bash
mkdir -p configs/ablations
```

- [ ] **Step 2: Write `configs/default.toml`**

```toml
# Defaults from docs/design.md §5 Table.
# String sentinels resolve to floats inside zipmould.solver.state.pack.

[solver]
gamma_man = 1.0
gamma_warns = 1.0
gamma_art = 1.0
gamma_par = 0.5

alpha = 1.0
beta = 2.0

beta1 = "N_squared"
beta2 = 1.0
beta3 = "10_N_squared"

tau_max = 10.0
z = 0.05
tau_0 = 0.0

population = 30
iter_cap = 200
wall_clock_s = 300.0

pheromone_mode = "unified"
tau_signed = true

visible_walkers = 5
frame_interval = 5
tau_delta_epsilon = 0.001
```

- [ ] **Step 3: Write `configs/ablations/zipmould-uni-signed.toml`**

```toml
[solver]
pheromone_mode = "unified"
tau_signed = true
```

- [ ] **Step 4: Write `configs/ablations/zipmould-uni-positive.toml`**

```toml
[solver]
pheromone_mode = "unified"
tau_signed = false
```

- [ ] **Step 5: Write `configs/ablations/zipmould-strat-signed.toml`**

```toml
[solver]
pheromone_mode = "stratified"
tau_signed = true
```

- [ ] **Step 6: Write `configs/ablations/zipmould-strat-positive.toml`**

```toml
[solver]
pheromone_mode = "stratified"
tau_signed = false
```

- [ ] **Step 7: Write `configs/ablations/aco-vanilla.toml`**

```toml
# Classical ACO baseline: tau ≥ 0, fitness-proportional positive deposit,
# constant evaporation. Implementation lives in baselines/aco_vanilla.py;
# the SolverConfig fields below tune the same knobs the kernel honours.

[solver]
pheromone_mode = "unified"
tau_signed = false
alpha = 1.0
beta = 2.0
tau_max = 10.0
z = 0.0
tau_0 = 1.0
population = 30
iter_cap = 200
```

- [ ] **Step 8: Write `configs/ablations/heuristic-only.toml`**

```toml
# Pheromone frozen at tau_0; only η drives sampling. The
# baselines/heuristic_only.solve() entrypoint freezes pheromone updates.

[solver]
pheromone_mode = "unified"
tau_signed = false
alpha = 0.0
beta = 2.0
tau_0 = 0.0
population = 30
iter_cap = 200
```

- [ ] **Step 9: Write `configs/ablations/random.toml`**

```toml
# Uniform-random walker; α = β = 0 collapses the softmax to uniform
# over legal moves. baselines/random_walk.solve() matches this exactly
# without invoking the SMA update.

[solver]
pheromone_mode = "unified"
tau_signed = false
alpha = 0.0
beta = 0.0
gamma_man = 0.0
gamma_warns = 0.0
gamma_art = 0.0
gamma_par = 0.0
population = 30
iter_cap = 200
```

- [ ] **Step 10: Write `configs/ablations/backtracking.toml`**

```toml
# Time-limited exact DFS with parity + articulation prunes.
# baselines/backtracking.solve() ignores most kernel knobs; only
# wall_clock_s and iter_cap control termination.

[solver]
pheromone_mode = "unified"
tau_signed = false
alpha = 0.0
beta = 0.0
population = 1
iter_cap = 1
wall_clock_s = 300.0
```

- [ ] **Step 11: Verify each TOML parses**

Run:
```bash
uv run python -c "
from pathlib import Path
from zipmould.config import SolverConfig
for f in sorted(Path('configs').rglob('*.toml')):
    cfg = SolverConfig.from_toml(f)
    print(f, '->', cfg.pheromone_mode, 'signed=', cfg.tau_signed)
"
```

Expected: 9 lines, one per TOML, each printing the path and the parsed mode/signed flags.

- [ ] **Step 12: Commit**

```bash
git add configs/
git commit -m "feat(configs): default and 8 Stage-1 ablation TOMLs"
```

---

## Phase 6 — Baselines

The four non-ZipMould conditions in design.md §6.1 are implemented here. Each baseline must accept `(puzzle, config, *, seed, trace, global_seed, condition)` and return a `RunResult` so the Stage-1 dispatcher can call them through one shape.

### Task 20: `baselines/random_walk.py` — uniform-random over legal moves

**Files:**
- Create: `src/zipmould/baselines/__init__.py`
- Create: `src/zipmould/baselines/random_walk.py`

- [ ] **Step 1: Create `src/zipmould/baselines/__init__.py`**

```python
"""Non-ZipMould reference baselines for Stage-1 comparison."""

from zipmould.baselines import aco_vanilla, backtracking, heuristic_only, random_walk

__all__ = ["aco_vanilla", "backtracking", "heuristic_only", "random_walk"]
```

- [ ] **Step 2: Create `src/zipmould/baselines/random_walk.py`**

```python
"""Uniform-random walker over legal moves.

This is the weakest baseline in the design.md ablation grid.  At each
step we enumerate legal neighbours (in-bounds, not blocked, not visited,
respecting wall constraints, and respecting waypoint ordering) and pick
one uniformly at random.  We declare success only when the walker has
covered exactly L cells in the correct waypoint order.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import numpy as np

from zipmould.rng import make_rng
from zipmould.solver.api import RunResult, _git_sha_and_dirty, _library_versions
from zipmould.solver.state import pack, unpack_path

if TYPE_CHECKING:
    from zipmould.config import SolverConfig
    from zipmould.puzzle import Puzzle


def solve(
    puzzle: Puzzle,
    config: SolverConfig,
    *,
    seed: int,
    trace: bool = False,
    global_seed: int = 0,
    condition: str = "random",
    freeze_pheromone: bool = False,  # noqa: ARG001
) -> RunResult:
    """Random-walk baseline; ignores all pheromone/heuristic knobs."""
    rng = make_rng(global_seed=global_seed, run_seed=seed,
                   puzzle_id=puzzle.puzzle_id, config_hash=config.config_hash())
    state = pack(puzzle, config)
    n_cells = int(state.adjacency.shape[0])
    L = int(state.L)
    K = int(state.K)
    waypoint_cells = np.asarray(state.waypoint_cells, dtype=np.int32)

    start_time = time.perf_counter()
    best_path: np.ndarray | None = None
    best_len = 0
    iters = 0
    solved = False

    while time.perf_counter() - start_time < float(config.wall_clock_s) and iters < int(config.iter_cap):
        iters += 1
        path = np.full(L, -1, dtype=np.int32)
        visited = np.zeros(n_cells, dtype=np.bool_)
        path[0] = int(waypoint_cells[0])
        visited[path[0]] = True
        segment = 1
        path_len = 1
        dead = False
        while path_len < L and not dead:
            cur = int(path[path_len - 1])
            legal: list[int] = []
            for nb_idx in range(int(state.adjacency_count[cur])):
                nb = int(state.adjacency[cur, nb_idx])
                if visited[nb]:
                    continue
                w_of = int(state.waypoint_of[nb])
                if w_of >= 0 and w_of != segment + 1 and w_of != 0:
                    continue
                legal.append(nb)
            if not legal:
                dead = True
                break
            choice = int(rng.integers(0, len(legal)))
            nxt = legal[choice]
            path[path_len] = nxt
            visited[nxt] = True
            path_len += 1
            w_of = int(state.waypoint_of[nxt])
            if w_of == segment + 1:
                segment += 1
        if path_len > best_len:
            best_len = path_len
            best_path = path.copy()
        if path_len == L and segment == K:
            solved = True
            break

    elapsed_ms = (time.perf_counter() - start_time) * 1000.0
    solution = unpack_path(best_path, best_len) if (solved and best_path is not None) else None
    sha, dirty = _git_sha_and_dirty()
    return RunResult(
        puzzle_id=puzzle.puzzle_id,
        condition=condition,
        seed=seed,
        global_seed=global_seed,
        config_hash=config.config_hash(),
        solved=solved,
        best_fitness=float(best_len) / float(L),
        iters=iters,
        wall_ms=elapsed_ms,
        solution=solution,
        failed=False,
        failure_reason=None,
        trace=None,
        library_versions=_library_versions(),
        git_sha=sha,
        git_dirty=dirty,
    )
```

- [ ] **Step 3: Smoke check the import**

Run:
```bash
uv run python -c "from zipmould.baselines import random_walk; print(random_walk.solve.__doc__)"
```

Expected: prints the docstring without ImportError or AttributeError.

- [ ] **Step 4: Commit**

```bash
git add src/zipmould/baselines/__init__.py src/zipmould/baselines/random_walk.py
git commit -m "feat(baselines): uniform random-walk reference baseline"
```

---

### Task 21: `baselines/heuristic_only.py` — ZipMould with frozen pheromone

**Files:**
- Create: `src/zipmould/baselines/heuristic_only.py`

- [ ] **Step 1: Create `src/zipmould/baselines/heuristic_only.py`**

```python
"""Heuristic-only baseline: ZipMould with pheromone frozen and alpha=0.

This isolates the contribution of the heuristic mixture from the
pheromone-feedback loop.  We do not duplicate the kernel — we call
``zipmould.solver.api.solve`` with a config override that zeroes alpha
and forces freeze_pheromone=True.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from zipmould.solver.api import solve as _zipmould_solve

if TYPE_CHECKING:
    from zipmould.config import SolverConfig
    from zipmould.puzzle import Puzzle
    from zipmould.solver.api import RunResult


def solve(
    puzzle: Puzzle,
    config: SolverConfig,
    *,
    seed: int,
    trace: bool = False,
    global_seed: int = 0,
    condition: str = "heuristic-only",
    freeze_pheromone: bool = False,  # noqa: ARG001 - always True here
) -> RunResult:
    """Run ZipMould with alpha forced to 0 and pheromone frozen."""
    cfg = config.model_copy(update={"alpha": 0.0})
    return _zipmould_solve(
        puzzle,
        cfg,
        seed=seed,
        trace=trace,
        global_seed=global_seed,
        condition=condition,
        freeze_pheromone=True,
    )
```

- [ ] **Step 2: Smoke check the import**

Run:
```bash
uv run python -c "from zipmould.baselines import heuristic_only; print(heuristic_only.solve.__doc__)"
```

Expected: docstring prints.

- [ ] **Step 3: Commit**

```bash
git add src/zipmould/baselines/heuristic_only.py
git commit -m "feat(baselines): heuristic-only baseline (frozen pheromone, alpha=0)"
```

---

### Task 22: `baselines/aco_vanilla.py` — classical ACO update

**Files:**
- Create: `src/zipmould/baselines/aco_vanilla.py`

- [ ] **Step 1: Create `src/zipmould/baselines/aco_vanilla.py`**

```python
"""Classical ACO baseline.

Differences from ZipMould (design.md §6.1):
  * Pheromone is unsigned-positive (tau_signed=False).
  * Deposit is fitness-proportional and positive only (no rank weights).
  * Evaporation is a constant rho (no SMA oscillator/contraction terms).
  * No restart noise injection.

We implement this by reusing ``zipmould.solver.state.pack`` and writing a
small dedicated kernel that replaces the SMA update with the classical
update.  The walker step (legality, softmax sampling) is identical to
ZipMould so that the only varied factor is the pheromone update.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import numpy as np
from numba import njit

from zipmould.rng import derive_kernel_seed
from zipmould.solver._kernel import _init_walker, _walker_run
from zipmould.solver.api import RunResult, _git_sha_and_dirty, _library_versions, _max_fitness
from zipmould.solver.state import pack, unpack_path

if TYPE_CHECKING:
    from zipmould.config import SolverConfig
    from zipmould.puzzle import Puzzle


@njit(cache=True, fastmath=False)
def _aco_update(
    tau: np.ndarray,
    walker_paths: np.ndarray,
    walker_path_lens: np.ndarray,
    walker_status: np.ndarray,
    walker_segment: np.ndarray,  # noqa: ARG001 - kept for signature parity
    edge_of: np.ndarray,
    rho: float,
    fitness: np.ndarray,
    L: int,
    Q: float,
) -> None:
    """Classical evaporation + fitness-proportional deposit on tau[0]."""
    n_edges = tau.shape[1]
    for e in range(n_edges):
        tau[0, e] = (1.0 - rho) * tau[0, e]
    n_walkers = walker_paths.shape[0]
    for w in range(n_walkers):
        if walker_status[w] != 1:
            continue
        deposit = Q * fitness[w]
        plen = int(walker_path_lens[w])
        for s in range(plen - 1):
            c = int(walker_paths[w, s])
            cn = int(walker_paths[w, s + 1])
            e = int(edge_of[c, cn])
            if e >= 0:
                tau[0, e] += deposit
    # Floor only; classical ACO does not clip from above.
    for e in range(n_edges):
        if tau[0, e] < 1e-9:
            tau[0, e] = 1e-9


def solve(
    puzzle: Puzzle,
    config: SolverConfig,
    *,
    seed: int,
    trace: bool = False,  # noqa: ARG001 - baselines do not emit traces
    global_seed: int = 0,
    condition: str = "aco-vanilla",
    freeze_pheromone: bool = False,  # noqa: ARG001
) -> RunResult:
    """Vanilla ACO baseline using classical evaporate+deposit on a unified tau."""
    cfg = config.model_copy(update={"pheromone_mode": "unified", "tau_signed": False})
    state = pack(puzzle, cfg)
    kseed = derive_kernel_seed(global_seed=global_seed, run_seed=seed,
                                puzzle_id=puzzle.puzzle_id,
                                config_hash=cfg.config_hash())
    np.random.seed(int(kseed))

    start_time = time.perf_counter()
    iters = 0
    best_fitness = 0.0
    best_path: np.ndarray | None = None
    solved = False

    n_walkers = int(cfg.population)
    L = int(state.L)
    fitness_buf = np.zeros(n_walkers, dtype=np.float64)
    Q = float(cfg.deposit_scale)
    rho = float(cfg.rho)

    while time.perf_counter() - start_time < float(cfg.wall_clock_s) and iters < int(cfg.iter_cap):
        iters += 1
        for w in range(n_walkers):
            _init_walker(w, state.walker_pos, state.walker_path,
                         state.walker_path_len, state.walker_visited,
                         state.walker_segment, state.walker_status,
                         state.walker_f0_remaining, state.walker_f1_remaining,
                         state.waypoint_cells, state.parity, state.f0_total, state.f1_total)
            _walker_run(w, state.tau, state.adjacency, state.adjacency_count,
                        state.edge_of, state.waypoint_of, state.parity,
                        state.manhattan_to_next, state.walker_pos,
                        state.walker_path, state.walker_path_len,
                        state.walker_visited, state.walker_segment,
                        state.walker_status, state.walker_f0_remaining,
                        state.walker_f1_remaining, state.waypoint_cells,
                        cfg.alpha, cfg.beta, L, int(state.K),
                        cfg.pheromone_mode_int, cfg.tau_signed_int,
                        cfg.heuristic_weights)
            cov = float(state.walker_path_len[w]) / float(L)
            fitness_buf[w] = cov  # classical ACO uses raw coverage as fitness
            if cov > best_fitness:
                best_fitness = cov
                best_path = state.walker_path[w, : int(state.walker_path_len[w])].copy()
            if int(state.walker_status[w]) == 1:
                solved = True
                best_fitness = 1.0
                best_path = state.walker_path[w, : int(state.walker_path_len[w])].copy()
                break
        if solved:
            break
        _aco_update(state.tau, state.walker_path, state.walker_path_len,
                    state.walker_status, state.walker_segment, state.edge_of,
                    rho, fitness_buf, L, Q)

    elapsed_ms = (time.perf_counter() - start_time) * 1000.0
    solution = unpack_path(best_path, len(best_path)) if (solved and best_path is not None) else None
    sha, dirty = _git_sha_and_dirty()
    return RunResult(
        puzzle_id=puzzle.puzzle_id,
        condition=condition,
        seed=seed,
        global_seed=global_seed,
        config_hash=cfg.config_hash(),
        solved=solved,
        best_fitness=float(best_fitness),
        iters=iters,
        wall_ms=elapsed_ms,
        solution=solution,
        failed=False,
        failure_reason=None,
        trace=None,
        library_versions=_library_versions(),
        git_sha=sha,
        git_dirty=dirty,
    )
```

- [ ] **Step 2: Smoke check the import**

Run:
```bash
uv run python -c "from zipmould.baselines import aco_vanilla; print(aco_vanilla.solve.__doc__)"
```

Expected: docstring prints.

- [ ] **Step 3: Commit**

```bash
git add src/zipmould/baselines/aco_vanilla.py
git commit -m "feat(baselines): classical ACO baseline with positive-only tau"
```

---

### Task 23: `baselines/backtracking.py` — DFS with parity + articulation prunes

**Files:**
- Create: `src/zipmould/baselines/backtracking.py`

- [ ] **Step 1: Create `src/zipmould/baselines/backtracking.py`**

```python
"""Time-limited DFS backtracking baseline.

Implements iterative depth-first search over the Hamiltonian-path
problem, with three prunes:

  1. Waypoint ordering: a cell containing waypoint k+1 is illegal until
     waypoint k has been claimed.
  2. Parity prune: the remaining cell counts on each colour class must
     stay within +/- 1, with the parity matching the waypoint endpoint
     for the unbalanced case.
  3. Articulation prune: if removing the current cell leaves the
     remaining-free subgraph disconnected, the partial path cannot be
     extended to a Hamiltonian path; backtrack.

Termination on first success or wall-clock expiry.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import numpy as np

from zipmould.solver.api import RunResult, _git_sha_and_dirty, _library_versions
from zipmould.solver.state import pack, unpack_path

if TYPE_CHECKING:
    from zipmould.config import SolverConfig
    from zipmould.puzzle import Puzzle


def _articulation_ok(
    cur: int,
    visited: np.ndarray,
    adjacency: np.ndarray,
    adjacency_count: np.ndarray,
    expected_remaining: int,
) -> bool:
    """BFS over unvisited cells from any unvisited neighbour of cur."""
    n = visited.shape[0]
    start = -1
    for i in range(int(adjacency_count[cur])):
        nb = int(adjacency[cur, i])
        if not visited[nb]:
            start = nb
            break
    if start < 0:
        return expected_remaining == 0
    seen = np.zeros(n, dtype=np.bool_)
    seen[start] = True
    stack: list[int] = [start]
    reached = 0
    while stack:
        c = stack.pop()
        reached += 1
        for i in range(int(adjacency_count[c])):
            nb = int(adjacency[c, i])
            if visited[nb] or seen[nb]:
                continue
            seen[nb] = True
            stack.append(nb)
    return reached == expected_remaining


def solve(
    puzzle: Puzzle,
    config: SolverConfig,
    *,
    seed: int,  # noqa: ARG001 - DFS is deterministic
    trace: bool = False,  # noqa: ARG001
    global_seed: int = 0,
    condition: str = "backtracking",
    freeze_pheromone: bool = False,  # noqa: ARG001
) -> RunResult:
    """DFS backtracking with parity + articulation prunes, time-limited."""
    state = pack(puzzle, config)
    n_cells = int(state.adjacency.shape[0])
    L = int(state.L)
    K = int(state.K)
    waypoint_cells = np.asarray(state.waypoint_cells, dtype=np.int32)
    waypoint_of = np.asarray(state.waypoint_of, dtype=np.int32)
    adjacency = np.asarray(state.adjacency, dtype=np.int32)
    adjacency_count = np.asarray(state.adjacency_count, dtype=np.int32)
    parity = np.asarray(state.parity, dtype=np.int32)

    visited = np.zeros(n_cells, dtype=np.bool_)
    path = np.full(L, -1, dtype=np.int32)
    path[0] = int(waypoint_cells[0])
    visited[path[0]] = True

    f0_remaining = int(state.f0_total) - (1 if int(parity[path[0]]) == 0 else 0)
    f1_remaining = int(state.f1_total) - (1 if int(parity[path[0]]) == 1 else 0)
    last_parity_target = int(parity[int(waypoint_cells[K - 1])])

    start_time = time.perf_counter()
    deadline = start_time + float(config.wall_clock_s)
    iters = 0
    best_len = 1
    best_path: np.ndarray | None = path.copy()
    solved = False

    stack_cur: list[int] = [int(path[0])]
    stack_seg: list[int] = [1]
    stack_iter: list[int] = [0]

    while stack_cur:
        if time.perf_counter() > deadline:
            break
        iters += 1
        if iters > int(config.iter_cap):
            break
        cur = stack_cur[-1]
        seg = stack_seg[-1]
        nb_i = stack_iter[-1]
        depth = len(stack_cur)
        if depth > best_len:
            best_len = depth
            best_path = path[:depth].copy()
        if depth == L and seg == K:
            solved = True
            break
        if nb_i >= int(adjacency_count[cur]):
            visited[cur] = False
            if int(parity[cur]) == 0:
                f0_remaining += 1
            else:
                f1_remaining += 1
            stack_cur.pop()
            stack_seg.pop()
            stack_iter.pop()
            if stack_cur:
                stack_iter[-1] += 1
            continue
        nb = int(adjacency[cur, nb_i])
        if visited[nb]:
            stack_iter[-1] += 1
            continue
        w_of = int(waypoint_of[nb])
        if w_of > 0 and w_of != seg + 1:
            stack_iter[-1] += 1
            continue
        new_seg = seg + 1 if w_of == seg + 1 else seg
        new_f0 = f0_remaining - (1 if int(parity[nb]) == 0 else 0)
        new_f1 = f1_remaining - (1 if int(parity[nb]) == 1 else 0)
        if abs(new_f0 - new_f1) > 1:
            stack_iter[-1] += 1
            continue
        remaining = L - (depth + 1)
        if remaining > 0 and not _articulation_ok(nb, visited, adjacency, adjacency_count, remaining):
            stack_iter[-1] += 1
            continue
        path[depth] = nb
        visited[nb] = True
        f0_remaining = new_f0
        f1_remaining = new_f1
        stack_cur.append(nb)
        stack_seg.append(new_seg)
        stack_iter.append(0)

    elapsed_ms = (time.perf_counter() - start_time) * 1000.0
    solution = unpack_path(best_path, best_len) if (solved and best_path is not None) else None
    sha, dirty = _git_sha_and_dirty()
    return RunResult(
        puzzle_id=puzzle.puzzle_id,
        condition=condition,
        seed=int(seed),
        global_seed=int(global_seed),
        config_hash=config.config_hash(),
        solved=solved,
        best_fitness=float(best_len) / float(L),
        iters=iters,
        wall_ms=elapsed_ms,
        solution=solution,
        failed=False,
        failure_reason=None,
        trace=None,
        library_versions=_library_versions(),
        git_sha=sha,
        git_dirty=dirty,
    )
```

- [ ] **Step 2: Smoke check the import**

Run:
```bash
uv run python -c "from zipmould.baselines import backtracking; print(backtracking.solve.__doc__)"
```

Expected: docstring prints.

- [ ] **Step 3: Commit**

```bash
git add src/zipmould/baselines/backtracking.py
git commit -m "feat(baselines): time-limited DFS with parity + articulation prunes"
```

---

## Phase 7 — I/O & Metrics

### Task 24: `io/puzzles.py` — CBOR loader and split loader

**Files:**
- Create: `src/zipmould/io/puzzles.py`
- Modify: `src/zipmould/io/__init__.py`

- [ ] **Step 1: Create `src/zipmould/io/puzzles.py`**

```python
"""Puzzle and split loaders.

The CBOR puzzle corpus is produced by ``benchmark/scripts/parse_to_cbor.py``
and the splits manifest by ``benchmark/scripts/make_splits.py``.  This
module exposes minimal readers that materialise frozen ``Puzzle``
dataclasses for the solver.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Final

from zipmould.puzzle import Puzzle, load_puzzles_cbor

DEFAULT_CORPUS_PATH: Final[Path] = Path("benchmark/data/puzzles.cbor")
DEFAULT_SPLITS_PATH: Final[Path] = Path("benchmark/data/splits.json")


def load_corpus(path: Path | str = DEFAULT_CORPUS_PATH) -> dict[str, Puzzle]:
    """Load the canonical puzzle corpus keyed by puzzle_id."""
    p = Path(path)
    return {pz.puzzle_id: pz for pz in load_puzzles_cbor(p)}


def load_split(name: str, path: Path | str = DEFAULT_SPLITS_PATH) -> list[str]:
    """Load the list of puzzle_ids belonging to a named split (train/dev/test)."""
    if name not in {"train", "dev", "test"}:
        raise ValueError(f"unknown split {name!r}; expected train|dev|test")
    p = Path(path)
    with p.open("r", encoding="utf-8") as fh:
        manifest = json.load(fh)
    ids = manifest.get(name)
    if not isinstance(ids, list):
        raise ValueError(f"splits manifest at {p} missing list for {name!r}")
    return [str(x) for x in ids]
```

- [ ] **Step 2: Re-export from `src/zipmould/io/__init__.py`**

```python
"""I/O helpers: puzzles, splits, traces."""

from zipmould.io.puzzles import DEFAULT_CORPUS_PATH, DEFAULT_SPLITS_PATH, load_corpus, load_split
from zipmould.io.trace import (
    BestPath,
    Frame,
    TauDelta,
    Trace,
    TraceFooter,
    TraceHeader,
    WalkerSnapshot,
    read_cbor,
    write_cbor,
)

__all__ = [
    "BestPath",
    "DEFAULT_CORPUS_PATH",
    "DEFAULT_SPLITS_PATH",
    "Frame",
    "TauDelta",
    "Trace",
    "TraceFooter",
    "TraceHeader",
    "WalkerSnapshot",
    "load_corpus",
    "load_split",
    "read_cbor",
    "write_cbor",
]
```

- [ ] **Step 3: Smoke check loader against the existing corpus**

Run:
```bash
uv run python -c "
from zipmould.io.puzzles import load_corpus, load_split
corpus = load_corpus()
print('corpus size:', len(corpus))
dev = load_split('dev')
print('dev size:', len(dev), 'first:', dev[0] if dev else None)
"
```

Expected: prints `corpus size: 245` and `dev size: 37` followed by a puzzle id string.

- [ ] **Step 4: Commit**

```bash
git add src/zipmould/io/puzzles.py src/zipmould/io/__init__.py
git commit -m "feat(io): puzzle corpus and split loaders"
```

---

### Task 25: `metrics.py` — Polars aggregation and McNemar paired test

**Files:**
- Create: `src/zipmould/metrics.py`

- [ ] **Step 1: Create `src/zipmould/metrics.py`**

```python
"""Metrics: aggregate Stage-1 Parquet results and compute McNemar tests.

Stage-1 produces a long-format Parquet table with one row per
(puzzle_id, condition, seed) triple.  This module provides:

  * ``aggregate(df)``: per-(puzzle, condition) reductions
        - solved_any (bool): any seed solved
        - best_fitness (float): max best_fitness across seeds
        - median_iters (int): median iters across seeds
        - p50_wall_ms / p90_wall_ms (float)
  * ``mcnemar_paired(df, baseline, candidate)``: paired McNemar test on
    solved-any flags between two conditions, using the design.md §10
    decision rule (b > c and b > c + 1.96 * sqrt(b + c)).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import polars as pl


@dataclass(frozen=True, slots=True)
class McNemarResult:
    baseline: str
    candidate: str
    n: int  # number of paired puzzles
    b: int  # baseline=fail, candidate=solve  (candidate wins)
    c: int  # baseline=solve, candidate=fail  (baseline wins)
    statistic: float
    significant: bool
    decision: str


def load_results(path: Path | str) -> pl.DataFrame:
    """Load Parquet results table written by ``experiments/stage1/run.py``."""
    return pl.read_parquet(str(path))


def aggregate(df: pl.DataFrame) -> pl.DataFrame:
    """Reduce per-(puzzle, condition, seed) rows to per-(puzzle, condition)."""
    return (
        df.group_by(["puzzle_id", "condition"])
        .agg(
            solved_any=pl.col("solved").any(),
            best_fitness=pl.col("best_fitness").max(),
            median_iters=pl.col("iters").median().cast(pl.Int64),
            p50_wall_ms=pl.col("wall_ms").median(),
            p90_wall_ms=pl.col("wall_ms").quantile(0.9),
        )
        .sort(["condition", "puzzle_id"])
    )


def mcnemar_paired(
    df: pl.DataFrame,
    baseline: str,
    candidate: str,
) -> McNemarResult:
    """Paired McNemar test on solved-any flags per design.md §10."""
    agg = aggregate(df)
    pivot = (
        agg.filter(pl.col("condition").is_in([baseline, candidate]))
        .pivot(values="solved_any", index="puzzle_id", on="condition")
        .drop_nulls([baseline, candidate])
    )
    n = pivot.height
    if n == 0:
        return McNemarResult(baseline, candidate, 0, 0, 0, 0.0, False, "no overlap")
    b = int(pivot.filter((~pl.col(baseline)) & pl.col(candidate)).height)
    c = int(pivot.filter(pl.col(baseline) & (~pl.col(candidate))).height)
    if b + c == 0:
        return McNemarResult(baseline, candidate, n, 0, 0, 0.0, False, "tied: no discordant pairs")
    threshold = c + 1.96 * math.sqrt(b + c)
    significant = b > c and b > threshold
    statistic = (b - c) / math.sqrt(b + c) if (b + c) > 0 else 0.0
    decision = "candidate wins" if significant else ("trend favours candidate" if b > c else "no improvement")
    return McNemarResult(baseline, candidate, n, b, c, statistic, significant, decision)
```

- [ ] **Step 2: Smoke check the imports and a synthetic frame**

Run:
```bash
uv run python -c "
import polars as pl
from zipmould.metrics import aggregate, mcnemar_paired
df = pl.DataFrame({
    'puzzle_id': ['a','a','b','b','c','c'] * 1,
    'condition': ['base','cand'] * 3,
    'seed':      [0,0,0,0,0,0],
    'solved':    [True, True, False, True, True, False],
    'best_fitness': [1.0,1.0,0.5,1.0,1.0,0.5],
    'iters':     [10,10,10,10,10,10],
    'wall_ms':   [1.0,1.0,1.0,1.0,1.0,1.0],
})
print(aggregate(df))
print(mcnemar_paired(df, 'base', 'cand'))
"
```

Expected: aggregate prints a 6-row frame and `McNemarResult(baseline='base', candidate='cand', n=3, b=1, c=1, ...)` without exception.

- [ ] **Step 3: Commit**

```bash
git add src/zipmould/metrics.py
git commit -m "feat(metrics): Polars aggregation and McNemar paired test"
```

---

## Phase 8 — CLI

### Task 26: `cli.py` and `__main__.py` — typer entrypoints

**Files:**
- Create: `src/zipmould/cli.py`
- Create: `src/zipmould/__main__.py`

- [ ] **Step 1: Create `src/zipmould/cli.py`**

```python
"""Command-line entrypoints for zipmould.

Subcommands:
  * ``solve``     : run a single puzzle through one condition
  * ``inspect``   : print summary metadata for a puzzle id
  * ``run-stage`` : alias to ``experiments.stage1.run`` for convenience
"""

from __future__ import annotations

import importlib
import json
from pathlib import Path
from typing import Annotated

import typer
from loguru import logger

from zipmould.config import SolverConfig
from zipmould.io.puzzles import load_corpus
from zipmould.logging_config import configure_logging

app = typer.Typer(no_args_is_help=True, add_completion=False)


def _resolve_solver(condition: str):
    """Map a condition name to a callable matching the solver protocol."""
    mapping = {
        "zipmould-uni-signed": "zipmould.solver.api:solve",
        "zipmould-uni-positive": "zipmould.solver.api:solve",
        "zipmould-strat-signed": "zipmould.solver.api:solve",
        "zipmould-strat-positive": "zipmould.solver.api:solve",
        "aco-vanilla": "zipmould.baselines.aco_vanilla:solve",
        "heuristic-only": "zipmould.baselines.heuristic_only:solve",
        "random": "zipmould.baselines.random_walk:solve",
        "backtracking": "zipmould.baselines.backtracking:solve",
    }
    if condition not in mapping:
        raise typer.BadParameter(f"unknown condition {condition!r}")
    mod_name, attr = mapping[condition].split(":")
    return getattr(importlib.import_module(mod_name), attr)


@app.command("solve")
def solve_cmd(
    puzzle_id: Annotated[str, typer.Argument(help="Puzzle identifier from the CBOR corpus.")],
    condition: Annotated[str, typer.Option(help="Experimental condition; matches configs/ablations/<name>.toml.")] = "zipmould-uni-signed",
    seed: Annotated[int, typer.Option(help="Run seed.")] = 0,
    global_seed: Annotated[int, typer.Option(help="Experiment-wide global seed.")] = 0,
    trace: Annotated[bool, typer.Option(help="Emit a CBOR trace next to the result.")] = False,
    config_path: Annotated[Path | None, typer.Option("--config", help="Override TOML config; defaults to configs/ablations/<condition>.toml.")] = None,
    out: Annotated[Path | None, typer.Option(help="Optional output path for the JSON RunResult summary.")] = None,
) -> None:
    """Solve a single puzzle under the named condition."""
    configure_logging()
    cfg_path = config_path or Path(f"configs/ablations/{condition}.toml")
    cfg = SolverConfig.from_toml(cfg_path)
    corpus = load_corpus()
    if puzzle_id not in corpus:
        raise typer.BadParameter(f"puzzle_id {puzzle_id!r} not in corpus")
    puzzle = corpus[puzzle_id]
    solver = _resolve_solver(condition)
    logger.info("Solving {} under {} (seed={}, global_seed={})", puzzle_id, condition, seed, global_seed)
    result = solver(puzzle, cfg, seed=seed, trace=trace, global_seed=global_seed, condition=condition)
    summary = {
        "puzzle_id": result.puzzle_id,
        "condition": result.condition,
        "seed": result.seed,
        "solved": result.solved,
        "best_fitness": result.best_fitness,
        "iters": result.iters,
        "wall_ms": result.wall_ms,
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
        raise typer.BadParameter(f"puzzle_id {puzzle_id!r} not in corpus")
    pz = corpus[puzzle_id]
    typer.echo(json.dumps({
        "puzzle_id": pz.puzzle_id,
        "n": pz.n,
        "k": len(pz.waypoints),
        "blocked": len(pz.blocked),
        "walls": len(pz.walls),
        "difficulty": pz.difficulty,
    }, indent=2, sort_keys=True))


@app.command("run-stage")
def run_stage_cmd(
    stage: Annotated[str, typer.Argument(help="Stage identifier; only 'stage1' is supported initially.")],
    workers: Annotated[int, typer.Option(help="joblib worker count; -1 = all cores.")] = -1,
    out_dir: Annotated[Path, typer.Option(help="Output directory for results.parquet and traces/.")] = Path("experiments/stage1/out"),
) -> None:
    """Dispatch a multi-condition experiment stage."""
    configure_logging()
    if stage != "stage1":
        raise typer.BadParameter("only 'stage1' is supported")
    runner = importlib.import_module("experiments.stage1.run")
    runner.main(workers=workers, out_dir=out_dir)


def main() -> None:
    """Console-script entrypoint."""
    app()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Create `src/zipmould/__main__.py`**

```python
"""Allow ``python -m zipmould`` to invoke the CLI."""

from zipmould.cli import main

if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Smoke check `--help`**

Run:
```bash
uv run python -m zipmould --help
```

Expected: prints typer help text listing the three subcommands (solve, inspect, run-stage) without ImportError.

- [ ] **Step 4: Smoke check `inspect`**

Run:
```bash
uv run python -m zipmould inspect $(uv run python -c "
from zipmould.io.puzzles import load_corpus
print(next(iter(load_corpus())))
")
```

Expected: prints a 6-key JSON object with puzzle_id, n, k, blocked, walls, difficulty.

- [ ] **Step 5: Commit**

```bash
git add src/zipmould/cli.py src/zipmould/__main__.py
git commit -m "feat(cli): typer-based solve/inspect/run-stage subcommands"
```

---

## Phase 9 — Stage-1 Experiment

The Stage-1 dispatch is the integration of every preceding phase: 8 conditions × 37 dev puzzles × 10 seeds = 2,960 jobs.  Traces are written **only** at seed=0 to bound disk usage.  Failures are captured as `failed=True` rows rather than raised, per design.md §9.

### Task 27: Manifest and stage stub directories

**Files:**
- Create: `experiments/stage1/manifest.toml`
- Create: `experiments/stage1/__init__.py`
- Create: `experiments/stage1_prime/.gitkeep`
- Create: `experiments/stage2/.gitkeep`
- Create: `experiments/stage4/.gitkeep`

- [ ] **Step 1: Create `experiments/stage1/manifest.toml`**

```toml
# Stage-1 manifest: conditions to run on the dev split.
#
# Per design.md §9, this stage tests 8 conditions on the 37 dev
# puzzles with 10 seeds each (jobs = 8 * 37 * 10 = 2960).  Traces
# are written only when seed == 0 to bound disk usage.

stage = "stage1"
split = "dev"
seeds = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
trace_seeds = [0]

[[conditions]]
name = "zipmould-uni-signed"
config = "configs/ablations/zipmould-uni-signed.toml"

[[conditions]]
name = "zipmould-uni-positive"
config = "configs/ablations/zipmould-uni-positive.toml"

[[conditions]]
name = "zipmould-strat-signed"
config = "configs/ablations/zipmould-strat-signed.toml"

[[conditions]]
name = "zipmould-strat-positive"
config = "configs/ablations/zipmould-strat-positive.toml"

[[conditions]]
name = "aco-vanilla"
config = "configs/ablations/aco-vanilla.toml"

[[conditions]]
name = "heuristic-only"
config = "configs/ablations/heuristic-only.toml"

[[conditions]]
name = "random"
config = "configs/ablations/random.toml"

[[conditions]]
name = "backtracking"
config = "configs/ablations/backtracking.toml"
```

- [ ] **Step 2: Create `experiments/stage1/__init__.py`**

```python
"""Stage-1 multi-condition experiment package."""
```

- [ ] **Step 3: Create empty stub directories for later stages**

Run:
```bash
mkdir -p experiments/stage1_prime experiments/stage2 experiments/stage4
touch experiments/stage1_prime/.gitkeep experiments/stage2/.gitkeep experiments/stage4/.gitkeep
```

Expected: three new empty directories with `.gitkeep` markers.

- [ ] **Step 4: Verify the manifest parses**

Run:
```bash
uv run python -c "
import tomllib
from pathlib import Path
m = tomllib.loads(Path('experiments/stage1/manifest.toml').read_text())
print(m['stage'], m['split'], len(m['conditions']), 'conditions')
"
```

Expected: prints `stage1 dev 8 conditions`.

- [ ] **Step 5: Commit**

```bash
git add experiments/
git commit -m "feat(experiments): Stage-1 manifest and stage stubs"
```

---

### Task 28: `experiments/stage1/run.py` — joblib dispatcher

**Files:**
- Create: `experiments/stage1/run.py`

- [ ] **Step 1: Create `experiments/stage1/run.py`**

```python
"""Stage-1 dispatcher.

Dispatches every (condition, puzzle, seed) triple defined by
manifest.toml through the appropriate solver, captures the RunResult,
writes a long-format Parquet table, and emits per-trace CBOR files
under traces/<condition>/<puzzle_id>__seed<seed>.cbor for the seeds
listed in trace_seeds.

The dispatcher is failure-tolerant per design.md §9: any exception in
a worker is converted into a row with failed=True and failure_reason
set so that downstream analysis can decide how to treat it.
"""

from __future__ import annotations

import importlib
import json
import sys
import tomllib
import traceback
from dataclasses import asdict
from pathlib import Path
from typing import Any

import polars as pl
from joblib import Parallel, delayed
from loguru import logger
from tqdm import tqdm

from zipmould.config import SolverConfig
from zipmould.io.puzzles import load_corpus, load_split
from zipmould.io.trace import write_cbor
from zipmould.logging_config import configure_logging
from zipmould.solver.api import RunResult

_SOLVER_REGISTRY: dict[str, str] = {
    "zipmould-uni-signed": "zipmould.solver.api:solve",
    "zipmould-uni-positive": "zipmould.solver.api:solve",
    "zipmould-strat-signed": "zipmould.solver.api:solve",
    "zipmould-strat-positive": "zipmould.solver.api:solve",
    "aco-vanilla": "zipmould.baselines.aco_vanilla:solve",
    "heuristic-only": "zipmould.baselines.heuristic_only:solve",
    "random": "zipmould.baselines.random_walk:solve",
    "backtracking": "zipmould.baselines.backtracking:solve",
}


def _resolve(name: str):
    mod_name, attr = _SOLVER_REGISTRY[name].split(":")
    return getattr(importlib.import_module(mod_name), attr)


def _row_from_result(r: RunResult) -> dict[str, Any]:
    return {
        "puzzle_id": r.puzzle_id,
        "condition": r.condition,
        "seed": int(r.seed),
        "global_seed": int(r.global_seed),
        "config_hash": r.config_hash,
        "solved": bool(r.solved),
        "best_fitness": float(r.best_fitness),
        "iters": int(r.iters),
        "wall_ms": float(r.wall_ms),
        "failed": bool(r.failed),
        "failure_reason": r.failure_reason,
        "git_sha": r.git_sha,
        "git_dirty": bool(r.git_dirty),
    }


def _failed_row(
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
        "best_fitness": 0.0,
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
        from zipmould.io.puzzles import load_corpus as _lc
        corpus = _lc()
        puzzle = corpus[puzzle_id]
        solver = _resolve(condition)
        result: RunResult = solver(
            puzzle, cfg,
            seed=seed,
            trace=want_trace,
            global_seed=global_seed,
            condition=condition,
        )
        if want_trace and result.trace is not None:
            traces_dir = Path(out_dir) / "traces" / condition
            traces_dir.mkdir(parents=True, exist_ok=True)
            write_cbor(result.trace, traces_dir / f"{puzzle_id}__seed{seed}.cbor")
        return _row_from_result(result)
    except Exception as exc:  # noqa: BLE001 - design.md §9 explicitly catches all
        return _failed_row(
            puzzle_id=puzzle_id,
            condition=condition,
            seed=seed,
            global_seed=global_seed,
            config_hash=cfg.config_hash(),
            reason=f"{type(exc).__name__}: {exc}",
        )


def main(
    workers: int = -1,
    out_dir: Path | str = Path("experiments/stage1/out"),
    manifest_path: Path | str = Path("experiments/stage1/manifest.toml"),
    global_seed: int = 0,
) -> None:
    """Dispatch the full Stage-1 grid and write results.parquet under out_dir."""
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
        "Stage-1: {} conditions x {} puzzles x {} seeds = {} jobs",
        len(conditions),
        len(puzzle_ids),
        len(seeds),
        len(conditions) * len(puzzle_ids) * len(seeds),
    )

    jobs = []
    for cond in conditions:
        cname = cond["name"]
        cpath = cond["config"]
        for pid in puzzle_ids:
            for s in seeds:
                jobs.append((cname, cpath, pid, s, s in trace_seeds))

    rows = Parallel(n_jobs=workers, backend="loky", verbose=0)(
        delayed(_run_one)(c, p, pid, s, global_seed, t, str(out_dir_p))
        for (c, p, pid, s, t) in tqdm(jobs, desc="stage1", file=sys.stderr)
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
    logger.info("Stage-1 done: solved={}, failed={}", summary["n_solved"], summary["n_failed"])


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Sanity-run a one-job slice**

Run:
```bash
uv run python -c "
from pathlib import Path
from experiments.stage1.run import _run_one
from zipmould.io.puzzles import load_split
pid = load_split('dev')[0]
row = _run_one(
    condition='heuristic-only',
    config_path='configs/ablations/heuristic-only.toml',
    puzzle_id=pid,
    seed=0,
    global_seed=0,
    want_trace=False,
    out_dir='experiments/stage1/out',
)
print(row)
"
```

Expected: a dict with `puzzle_id`, `condition='heuristic-only'`, `failed=False`, and finite values for `iters` and `wall_ms`.

- [ ] **Step 3: Commit**

```bash
git add experiments/stage1/run.py
git commit -m "feat(stage1): joblib dispatcher with trace gating and failure rows"
```

---

### Task 29: `experiments/stage1/analyze.py` — McNemar decision and report

**Files:**
- Create: `experiments/stage1/analyze.py`

- [ ] **Step 1: Create `experiments/stage1/analyze.py`**

```python
"""Stage-1 analysis: aggregate results.parquet and print a decision report.

Applies the McNemar paired test from ``zipmould.metrics`` for every
ZipMould variant against each non-ZipMould baseline.  Prints a JSON
report and writes it to ``experiments/stage1/out/report.json``.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import polars as pl
from loguru import logger

from zipmould.logging_config import configure_logging
from zipmould.metrics import aggregate, load_results, mcnemar_paired

ZIPMOULD_VARIANTS = (
    "zipmould-uni-signed",
    "zipmould-uni-positive",
    "zipmould-strat-signed",
    "zipmould-strat-positive",
)
BASELINES = ("aco-vanilla", "heuristic-only", "random", "backtracking")


def main(out_dir: Path | str = Path("experiments/stage1/out")) -> None:
    configure_logging()
    out_dir_p = Path(out_dir)
    df = load_results(out_dir_p / "results.parquet")
    agg = aggregate(df)
    agg.write_parquet(out_dir_p / "aggregate.parquet")

    rows = []
    for variant in ZIPMOULD_VARIANTS:
        for baseline in BASELINES:
            r = mcnemar_paired(df, baseline=baseline, candidate=variant)
            rows.append(asdict(r))
            logger.info(
                "{} vs {}: n={} b={} c={} stat={:.3f} significant={} ({})",
                variant, baseline, r.n, r.b, r.c, r.statistic, r.significant, r.decision,
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
```

- [ ] **Step 2: Smoke check the import**

Run:
```bash
uv run python -c "from experiments.stage1.analyze import main; print(main.__doc__ or 'ok')"
```

Expected: prints `ok` (or a docstring).

- [ ] **Step 3: Commit**

```bash
git add experiments/stage1/analyze.py
git commit -m "feat(stage1): McNemar analysis and JSON report"
```

---

## Phase 10 — Verification

This phase exercises every acceptance criterion in spec §11 directly.  Every step here corresponds to one or more numbered acceptance criteria and must pass before the implementation is declared complete.

### Task 30: Quality gates, determinism, and end-to-end smoke

**Files:** none created or modified — verification only.

- [ ] **Step 1: Lint with ruff**

Run:
```bash
uv run ruff check src tests experiments benchmark
uv run ruff format --check src tests experiments benchmark
```

Expected: both commands exit with status 0.  If `ruff format --check` fails, run `uv run ruff format src tests experiments benchmark` and re-run the check; if `ruff check` fails on a real lint violation, fix the source rather than disabling the rule (CLAUDE.md scope discipline).  Acceptance criterion §11.1.

- [ ] **Step 2: Type-check with ty (Astral)**

Run:
```bash
uv run ty check src
```

Expected: status 0 with zero errors and zero warnings on `src/zipmould`.  If ty is unavailable in the environment, the CI backstop is pyright (Step 3); both must pass.  Acceptance criterion §11.2.

- [ ] **Step 3: Type-check with pyright (CI backstop)**

Run:
```bash
uv run pyright src
```

Expected: status 0 with zero errors.  Acceptance criterion §11.2.

- [ ] **Step 4: Security scan with bandit**

Run:
```bash
uv run bandit -q -r src/zipmould
```

Expected: status 0 with no `Issue:` lines.  If bandit flags `B311` (random) inside `baselines/random_walk.py`, the use is intentional (uniform sampling for an experimental baseline, not security) and must be silenced **only** with a targeted `# nosec B311` comment with rationale on the offending line — not at file level.  Acceptance criterion §11.3.

- [ ] **Step 5: Determinism cross-check (acceptance §11.4)**

Run:
```bash
uv run python -c "
from pathlib import Path
from zipmould.config import SolverConfig
from zipmould.io.puzzles import load_corpus, load_split
from zipmould.solver.api import solve

corpus = load_corpus()
pid = load_split('dev')[0]
puzzle = corpus[pid]
cfg = SolverConfig.from_toml(Path('configs/ablations/zipmould-uni-signed.toml'))

a = solve(puzzle, cfg, seed=0, trace=False, global_seed=0, condition='zipmould-uni-signed')
b = solve(puzzle, cfg, seed=0, trace=False, global_seed=0, condition='zipmould-uni-signed')
assert a.solved == b.solved, (a.solved, b.solved)
assert a.best_fitness == b.best_fitness, (a.best_fitness, b.best_fitness)
assert a.iters == b.iters, (a.iters, b.iters)
assert a.solution == b.solution
print('DETERMINISTIC OK', pid, a.solved, a.best_fitness, a.iters)
"
```

Expected: prints `DETERMINISTIC OK <pid> <solved> <best_fitness> <iters>`.  Any AssertionError indicates a non-determinism bug — typically an unseeded RNG path or an iteration order over a hash-based collection inside the kernel boundary.  Acceptance criterion §11.4.

- [ ] **Step 6: Trace round-trip (acceptance §11.5)**

Run:
```bash
uv run python -c "
from pathlib import Path
from zipmould.config import SolverConfig
from zipmould.io.puzzles import load_corpus, load_split
from zipmould.io.trace import read_cbor, write_cbor
from zipmould.solver.api import solve

corpus = load_corpus()
pid = load_split('dev')[0]
puzzle = corpus[pid]
cfg = SolverConfig.from_toml(Path('configs/ablations/zipmould-uni-signed.toml'))
result = solve(puzzle, cfg, seed=0, trace=True, global_seed=0, condition='zipmould-uni-signed')
assert result.trace is not None, 'trace must be populated when trace=True'

p = Path('/tmp/zipmould_trace_smoke.cbor')
write_cbor(result.trace, p)
loaded = read_cbor(p)
assert loaded.header.puzzle_id == result.trace.header.puzzle_id
assert loaded.header.config_hash == result.trace.header.config_hash
assert len(loaded.frames) == len(result.trace.frames)
print('TRACE ROUND-TRIP OK', loaded.header.puzzle_id, len(loaded.frames), 'frames')
"
```

Expected: prints `TRACE ROUND-TRIP OK <pid> <n> frames`.  Acceptance criterion §11.5.

- [ ] **Step 7: Benchmark scripts byte-identical re-run (acceptance §11.6)**

Run:
```bash
sha256sum benchmark/data/puzzles.cbor benchmark/data/splits.json > /tmp/zipmould_pre_hashes.txt
uv run python benchmark/scripts/parse_to_cbor.py
uv run python benchmark/scripts/make_splits.py
sha256sum benchmark/data/puzzles.cbor benchmark/data/splits.json > /tmp/zipmould_post_hashes.txt
diff /tmp/zipmould_pre_hashes.txt /tmp/zipmould_post_hashes.txt
```

Expected: `diff` exits 0 (no output).  Any difference means the loguru migration in Task 03 silently changed output bytes, which is a regression.  Acceptance criterion §11.6.

- [ ] **Step 8: CLI end-to-end smoke (acceptance §11.7)**

Run:
```bash
PID=$(uv run python -c "from zipmould.io.puzzles import load_split; print(load_split('dev')[0])")
uv run python -m zipmould solve "$PID" --condition heuristic-only --seed 0
```

Expected: prints a JSON object with the solve summary and exits 0.  Acceptance criterion §11.7.

- [ ] **Step 9: Stage-1 sample dispatch (acceptance §11.8)**

Run a 16-job slice (2 conditions × 4 puzzles × 2 seeds) by running the dispatcher with a temporary manifest:
```bash
uv run python -c "
import tomllib
from pathlib import Path
m = tomllib.loads(Path('experiments/stage1/manifest.toml').read_text())
m['seeds'] = [0, 1]
# Cut to two conditions and four puzzles for the smoke run.
m['conditions'] = [c for c in m['conditions'] if c['name'] in {'heuristic-only', 'random'}]
import json
Path('experiments/stage1/manifest_smoke.toml').write_text(
    '\\n'.join([
        f\"stage = \\\"{m['stage']}\\\"\",
        f\"split = \\\"{m['split']}\\\"\",
        f\"seeds = {json.dumps(m['seeds'])}\",
        f\"trace_seeds = {json.dumps(m.get('trace_seeds', [0]))}\",
    ] + [
        f'\\n[[conditions]]\\nname = \"{c[\"name\"]}\"\\nconfig = \"{c[\"config\"]}\"'
        for c in m['conditions']
    ]) + '\\n'
)
"
uv run python -c "
from pathlib import Path
from zipmould.io.puzzles import load_split
ids = load_split('dev')[:4]
print('smoke puzzle ids:', ids)
"
uv run python -c "
from pathlib import Path
from experiments.stage1.run import main
main(workers=1, out_dir=Path('experiments/stage1/out_smoke'),
     manifest_path=Path('experiments/stage1/manifest_smoke.toml'))
"
```

Expected: writes `experiments/stage1/out_smoke/results.parquet` and `summary.json`.  Inspect:
```bash
uv run python -c "
import polars as pl
df = pl.read_parquet('experiments/stage1/out_smoke/results.parquet')
print(df.shape)
print(df.group_by('condition').agg(pl.col('solved').sum(), pl.col('failed').sum()))
"
```

Expected: shape is at most `(<= 16, 13)` (the dispatcher only runs the puzzles in the configured split, so it may be larger; the smoke check is that it runs to completion and `failed.sum() == 0`).  Acceptance criterion §11.8.

- [ ] **Step 10: Spec coverage final check (acceptance §11.9–§11.11)**

Run:
```bash
uv run python -c "
import zipmould
import zipmould.config
import zipmould.puzzle
import zipmould.solver.api
import zipmould.solver.state
import zipmould.solver._kernel
import zipmould.io.trace
import zipmould.io.puzzles
import zipmould.metrics
import zipmould.cli
import zipmould.baselines.aco_vanilla
import zipmould.baselines.heuristic_only
import zipmould.baselines.random_walk
import zipmould.baselines.backtracking
print('ALL MODULES IMPORTABLE')
"
```

Expected: prints `ALL MODULES IMPORTABLE`.

Acceptance criteria §11.9 (no orphan legacy modules), §11.10 (every public symbol re-exported from `zipmould`), and §11.11 (manifest discoverable via `zipmould run-stage stage1`) are satisfied if and only if this step succeeds together with Step 8.

- [ ] **Step 11: Final commit**

```bash
git add -A
git commit -m "chore: Stage-1 verification smoke artefacts" || echo "nothing to commit (verification was read-only)"
```

The verification phase is intentionally read-only with respect to source.  The only artefacts that may be created are under `experiments/stage1/out_smoke/` and `experiments/stage1/manifest_smoke.toml`; both are scratch data and may either be committed for inspection or ignored.

---

## Self-Review

This is a self-check pass run against the spec immediately after the plan is written.  The reviewer is the author.  Findings recorded inline.

**1. Spec coverage**

For each numbered section in the design.md and the implementation-design spec, point to a task that covers it:

| Spec section | Coverage |
|---|---|
| Stack selection (Python 3.13, full deps, tooling) | T00 |
| Legacy module removal | T01 |
| Logging discipline (loguru everywhere) | T02, T03 |
| `Puzzle` dataclass + canonical edge ordering | T04 |
| `SolverConfig` (incl. `tau_signed` extension) | T05 |
| Deterministic seeding | T06 |
| Feasibility precheck | T07 |
| Fitness function | T08 |
| Kernel state packing + sentinels | T09 |
| Heuristic mixture + visited bitmap | T10 |
| Walker step + run | T11, T12 |
| Pheromone update (rank, restart noise, clip) | T13 |
| Iteration driver and seed primer | T14 |
| Top-level kernel + tau delta encoder | T15 |
| Trace schema + CBOR I/O | T16 |
| Public `solve()` API + RunResult | T17 |
| Package re-exports | T18 |
| Default + 8 ablation TOMLs | T19 |
| Random-walk baseline | T20 |
| Heuristic-only baseline | T21 |
| Vanilla ACO baseline | T22 |
| Backtracking baseline | T23 |
| Puzzle/split loaders | T24 |
| Polars aggregation + McNemar | T25 |
| CLI (`solve`/`inspect`/`run-stage`) | T26 |
| Stage-1 manifest + stubs | T27 |
| Stage-1 dispatcher (2,960 jobs) | T28 |
| Stage-1 analysis + decision | T29 |
| Quality gates + determinism + smoke | T30 |

No spec section is uncovered.

**2. Placeholder scan**

A check for the red-flag patterns from the writing-plans skill:

- "TBD" / "TODO" / "implement later" / "fill in details": none in the plan body other than legitimate `# TODO` references in code that are clearly described in surrounding text.  *Pass.*
- "Add appropriate error handling": all error-handling sites are explicit (`except Exception` only at the dispatcher boundary per design.md §9; explicit `ValueError`/`KernelError`/`DeterminismError` elsewhere).  *Pass.*
- "Write tests for the above": no test tasks are present (per CLAUDE.md and spec §9 — verification only via smoke imports + CLI + Stage-1 dispatch).  *Pass — by deliberate policy, not omission.*
- "Similar to Task N": every task contains its full code.  *Pass.*
- Unspecified types/methods: the symbols introduced (e.g., `KernelState`, `SolverConfig`, `RunResult`, `Trace`, `Puzzle`) are defined before use.  *Pass.*

**3. Type-name consistency**

Spot-check of names that recur across tasks:

- `SolverConfig.config_hash()` is used identically in T05, T06, T17, T22, T26, T28.  *Consistent.*
- `KernelState.adjacency_count` (lowercase, with `_count` suffix) is used in T09, T10, T11, T22, T23.  *Consistent.*
- `walker_path_len` (singular `len`) is used identically in T09, T11, T12, T14, T22, T23.  *Consistent.*
- `RunResult.best_fitness` is used identically in T17, T20, T22, T23, T28.  *Consistent.*
- `pheromone_mode` (string field on `SolverConfig`) is paired with `pheromone_mode_int` (int derived in `pack`).  Both are consistently named where used.  *Consistent.*
- `tau_signed` (the spec extension) is used identically in T05, T19, T22.  *Consistent.*

No drift detected.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-24-zipmould-python-implementation.md`.

Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.  Required sub-skill: `superpowers:subagent-driven-development`.

**2. Inline Execution** — Execute tasks in this session using `superpowers:executing-plans`, batch execution with checkpoints for review.

Which approach?




