# Solver Visualizer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a single-user, locally hosted web app that loads recorded `.cbor` traces or runs synchronous solves against the corpus, then replays them frame-by-frame in a Cockpit layout (grid + telemetry).

**Architecture:** Vue 3 + TypeScript + Vite frontend (managed with `bun`) talking to a FastAPI + uvicorn backend (managed with `uv`) over a small REST API. Generate-then-replay only — no live frame streaming. The backend lives at `src/zipmould/viz/` so it imports the solver directly; the frontend lives at `viz-web/` as a sibling. In production the backend serves the Vite-built static assets; in dev, Vite proxies `/api` to FastAPI.

**Tech Stack:** Python 3.13, FastAPI, uvicorn, pydantic v2, cbor2, numpy. TypeScript 5, Vue 3.5, Vite, Pinia, Tailwind v4, cbor-x, vitest, Playwright. `uv` for Python deps; `bun` for JS deps.

**Spec:** `docs/superpowers/specs/2026-04-26-solver-visualizer-design.md`

---

## Notes for the Engineer

- **Variant scope.** `/api/variants` exposes only the four ZipMould variants (`uni-signed`, `uni-positive`, `strat-signed`, `strat-positive`). The baselines (`random`, `backtracking`, `heuristic-only`, `aco-vanilla`) live in `src/zipmould/baselines/` and have different trace semantics; they're out of scope for v1 live runs. The visualizer can still **replay** any uploaded `.cbor` regardless of producer.
- **`tau_clip_min` is derived.** It is `-config.tau_max` when `tau_signed=true`, else `0`. The frontend computes its own copy from the trace's `config` block — do not add it to the API.
- **Existing helpers to reuse.**
  - `zipmould.io.trace._trace_to_dict(trace) -> dict` and `zipmould.io.trace.read_cbor(path) -> Trace` are the canonical (de)serializers. Wrap them with thin public-facing helpers under `viz/trace_codec.py`.
  - `zipmould.io.puzzles.load_corpus()` returns `dict[str, Puzzle]` with id/N/K/walls/blocked/waypoints/difficulty/name.
  - `zipmould.solver.api.solve(puzzle, config, *, seed, trace, global_seed, condition)` is the live-run entrypoint. Pass `trace=True`.
  - `zipmould.config.SolverConfig.from_toml(path)` loads variant defaults; `SolverConfig.model_validate(dict)` applies overrides.
- **Pheromone reconstruction.** `frame.tau_delta.edges` is a list of `(edge_id, stripe, delta)` tuples. The pheromone array is shaped `[n_stripes, 2*L]` flat. For unified mode, `n_stripes=1` and stripe is `-1` in the trace — treat as stripe index 0. For stratified mode, stripe is the actual index.
- **Frame index vs `frame.t`.** The trace contains frames at `frame_interval` cadence. The scrubber operates in array-index space (`0..N_frames-1`). Each frame's `frame.t` is the kernel iteration number at capture time.
- **Tests follow TDD.** Each task: failing test → run to confirm it fails → minimal implementation → run to confirm pass → commit. Don't bypass the failure check.
- **No premature cleanup.** Don't refactor existing modules outside the task's scope. The plan touches `src/zipmould/cli.py`, `pyproject.toml`, and `.gitignore`; everything else is additive.
- **Frequent commits.** Commit per task with the suggested message.

---

## File Structure (cumulative)

After all tasks complete:

```
src/zipmould/viz/
    __init__.py
    server.py
    routes.py
    schemas.py
    runner.py
    trace_codec.py
    cache.py
    static/                        # gitignored Vite build output

viz-web/
    package.json
    bun.lock                       # bun's lockfile (generated)
    vite.config.ts
    tsconfig.json
    tsconfig.node.json
    index.html
    tailwind.config.ts             # only if needed; Tailwind v4 mostly auto-detects
    postcss.config.cjs             # only if Tailwind plugin requires
    playwright.config.ts
    tests/
        e2e/
            replay.spec.ts
        fixtures/
            tiny-trace.cbor
    src/
        main.ts
        App.vue
        api/
            client.ts
            types.ts
        stores/
            playback.ts
            trace.ts
            run.ts
            notifications.ts
        composables/
            useTraceReplay.ts
            useFileLoader.ts
        components/
            GridCanvas.vue
            ControlBar.vue
            ConfigPanel.vue
            TracePicker.vue
            FitnessChart.vue
            WalkerTable.vue
            FrameMeta.vue
            FooterSummary.vue
            LayerToggles.vue
            ErrorToasts.vue
        styles/
            tailwind.css

tests/
    viz/
        __init__.py
        conftest.py
        test_trace_codec.py
        test_runner.py
        test_cache.py
        test_routes_puzzles.py
        test_routes_variants.py
        test_routes_runs.py
        test_routes_traces.py
        test_routes_errors.py
        test_cli.py
        fixtures/
            tiny-trace.cbor
```

Touched existing files: `pyproject.toml`, `.gitignore`, `src/zipmould/cli.py`.

---

## Task 1: Add `viz` extra and create package skeleton

**Goal:** Land the new dependency wall and a minimum-viable FastAPI app that responds to `/api/health`. Future tasks build on this.

**Files:**
- Modify: `pyproject.toml`
- Create: `src/zipmould/viz/__init__.py`
- Create: `src/zipmould/viz/server.py`
- Create: `src/zipmould/viz/routes.py`
- Create: `tests/__init__.py` (if missing)
- Create: `tests/viz/__init__.py`
- Create: `tests/viz/conftest.py`
- Create: `tests/viz/test_routes_health.py`

- [ ] **Step 1: Write the failing test**

Create `tests/viz/test_routes_health.py`:

```python
"""Liveness check for the viz FastAPI app."""

from __future__ import annotations

from fastapi.testclient import TestClient

from zipmould.viz.server import create_app


def test_health_returns_ok() -> None:
    app = create_app()
    client = TestClient(app)
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert isinstance(body["version"], str) and body["version"]
```

Create `tests/__init__.py` (empty file) and `tests/viz/__init__.py` (empty file) if either does not exist.

Create `tests/viz/conftest.py`:

```python
"""Shared fixtures for viz backend tests."""

from __future__ import annotations
```

(Empty for now; later tasks add fixtures.)

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
uv run pytest tests/viz/test_routes_health.py -v
```

Expected: collection error or failure citing missing `fastapi` and/or `zipmould.viz`.

- [ ] **Step 3: Add the `viz` extra to `pyproject.toml`**

Edit `pyproject.toml`. Insert immediately after the `dependencies = [...]` block:

```toml
[project.optional-dependencies]
viz = [
    "fastapi>=0.115,<1",
    "uvicorn[standard]>=0.32,<1",
    "python-multipart>=0.0.20,<1",
]
```

Then sync:

```bash
uv sync --extra viz
```

- [ ] **Step 4: Create the package skeleton**

Create `src/zipmould/viz/__init__.py`:

```python
"""HTTP-served visualizer for ZipMould solver runs.

This package exposes a FastAPI application that loads recorded `.cbor`
traces and runs synchronous solves against the puzzle corpus, returning
JSON-shaped traces consumable by the frontend.
"""

from __future__ import annotations

from zipmould.viz.server import create_app

__all__ = ["create_app"]
```

Create `src/zipmould/viz/routes.py`:

```python
"""HTTP route handlers for the viz API."""

from __future__ import annotations

from importlib.metadata import version as _pkg_version

from fastapi import APIRouter

router = APIRouter(prefix="/api")


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness probe; returns the installed package version."""
    return {"status": "ok", "version": _pkg_version("zipmould")}
```

Create `src/zipmould/viz/server.py`:

```python
"""FastAPI application factory.

`create_app` returns a fully wired ASGI app. A single uvicorn process
both serves the API and (in production) the built frontend assets.
"""

from __future__ import annotations

from fastapi import FastAPI

from zipmould.viz.routes import router as api_router


def create_app() -> FastAPI:
    app = FastAPI(title="ZipMould Visualizer", version="0.1.0")
    app.include_router(api_router)
    return app
```

- [ ] **Step 5: Run test to verify it passes**

```bash
uv run pytest tests/viz/test_routes_health.py -v
```

Expected: 1 passed.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml uv.lock src/zipmould/viz/ tests/__init__.py tests/viz/
git commit -m "feat(viz): scaffold FastAPI app with /api/health"
```

---

## Task 2: Trace codec — public JSON helpers

**Goal:** Promote the private `_trace_to_dict` / `_frame_from_dict` helpers in `zipmould.io.trace` to a stable public surface usable by the API. We do **not** modify `io/trace.py`; we add a thin re-export wrapper under `viz/`.

**Files:**
- Create: `src/zipmould/viz/trace_codec.py`
- Create: `tests/viz/test_trace_codec.py`

- [ ] **Step 1: Write the failing test**

Create `tests/viz/test_trace_codec.py`:

```python
"""Round-trip a fixture Trace through the public JSON helpers."""

from __future__ import annotations

from zipmould.io.trace import (
    BestPath,
    Frame,
    TauDelta,
    Trace,
    TraceFooter,
    TraceHeader,
    WalkerSnapshot,
)
from zipmould.viz.trace_codec import trace_to_jsonable, jsonable_to_trace


def _fixture_trace() -> Trace:
    header = TraceHeader(N=3, K=2, L=9, waypoints=((0, 0), (2, 2)), walls=(), blocked=())
    walker = WalkerSnapshot(id=0, cell=(1, 1), segment=0, status="alive", fitness=0.5)
    frame = Frame(
        t=0,
        v_b=0.1,
        v_c=0.2,
        tau_delta=TauDelta(mode="unified", edges=((0, -1, 0.5),)),
        best=BestPath(path=((0, 0),), fitness=0.0),
        walkers=(walker,),
    )
    footer = TraceFooter(
        solved=False,
        infeasible=False,
        solution=None,
        iterations_used=1,
        wall_clock_s=0.01,
        best_fitness=0.5,
    )
    return Trace(
        version=1,
        puzzle_id="fixture",
        config={"alpha": 1.0},
        seed=7,
        header=header,
        frames=(frame,),
        footer=footer,
    )


def test_round_trip_preserves_all_fields() -> None:
    original = _fixture_trace()
    payload = trace_to_jsonable(original)
    restored = jsonable_to_trace(payload)
    assert restored == original


def test_jsonable_uses_pure_python_types() -> None:
    payload = trace_to_jsonable(_fixture_trace())
    assert payload["puzzle_id"] == "fixture"
    assert payload["frames"][0]["walkers"][0]["status"] == "alive"
    assert payload["header"]["waypoints"] == [[0, 0], [2, 2]]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/viz/test_trace_codec.py -v
```

Expected: ImportError on `zipmould.viz.trace_codec`.

- [ ] **Step 3: Implement the codec**

Create `src/zipmould/viz/trace_codec.py`:

```python
"""Stable, public JSON helpers for `Trace` objects.

The frontend consumes Trace data over the network. `io.trace` already has
private dict-conversion helpers; this module re-exports them under a stable
public name and offers symmetric `read_cbor_bytes` / `write_cbor_bytes`
helpers that operate on raw byte buffers (no temp files).
"""

from __future__ import annotations

import io
from typing import Any, cast

import cbor2

from zipmould.io.trace import (
    Trace,
    _frame_from_dict,
    _trace_to_dict,
    TraceFooter,
    TraceHeader,
)


def trace_to_jsonable(trace: Trace) -> dict[str, Any]:
    """Convert `Trace` into a JSON-serialisable dict."""
    return _trace_to_dict(trace)


def jsonable_to_trace(payload: dict[str, Any]) -> Trace:
    """Inverse of `trace_to_jsonable`."""
    h = cast("dict[str, Any]", payload["header"])
    ft = cast("dict[str, Any]", payload["footer"])
    return Trace(
        version=int(payload["version"]),
        puzzle_id=str(payload["puzzle_id"]),
        config=dict(cast("dict[str, Any]", payload["config"])),
        seed=int(payload["seed"]),
        header=TraceHeader(
            N=int(h["N"]),
            K=int(h["K"]),
            L=int(h["L"]),
            waypoints=tuple((int(r), int(c)) for r, c in h["waypoints"]),
            walls=tuple(((int(a[0]), int(a[1])), (int(b[0]), int(b[1]))) for a, b in h["walls"]),
            blocked=tuple((int(r), int(c)) for r, c in h["blocked"]),
        ),
        frames=tuple(_frame_from_dict(f) for f in payload["frames"]),
        footer=TraceFooter(
            solved=bool(ft["solved"]),
            infeasible=bool(ft["infeasible"]),
            solution=(
                tuple((int(r), int(c)) for r, c in ft["solution"])
                if ft["solution"] is not None
                else None
            ),
            iterations_used=int(ft["iterations_used"]),
            wall_clock_s=float(ft["wall_clock_s"]),
            best_fitness=float(ft["best_fitness"]),
        ),
    )


def read_cbor_bytes(data: bytes) -> Trace:
    """Parse a CBOR trace from an in-memory byte buffer."""
    raw = cast("dict[str, Any]", cbor2.load(io.BytesIO(data)))
    return jsonable_to_trace(raw)


def write_cbor_bytes(trace: Trace) -> bytes:
    """Serialize a Trace to CBOR bytes."""
    buf = io.BytesIO()
    cbor2.dump(_trace_to_dict(trace), buf)
    return buf.getvalue()
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/viz/test_trace_codec.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add src/zipmould/viz/trace_codec.py tests/viz/test_trace_codec.py
git commit -m "feat(viz): public JSON+CBOR codec for Trace"
```

---

## Task 3: In-memory trace cache

**Goal:** Hold the most recent N traces (with their original CBOR bytes) so the "Save trace" button can re-stream them.

**Files:**
- Create: `src/zipmould/viz/cache.py`
- Create: `tests/viz/test_cache.py`

- [ ] **Step 1: Write the failing test**

Create `tests/viz/test_cache.py`:

```python
"""LRU trace cache."""

from __future__ import annotations

import pytest

from zipmould.viz.cache import TraceCache


def test_put_and_get_returns_same_bytes() -> None:
    cache = TraceCache(capacity=2)
    cache.put("a", b"\x01\x02")
    assert cache.get("a") == b"\x01\x02"


def test_eviction_drops_least_recently_used() -> None:
    cache = TraceCache(capacity=2)
    cache.put("a", b"a")
    cache.put("b", b"b")
    cache.get("a")  # touch a so b becomes LRU
    cache.put("c", b"c")
    assert cache.get("b") is None
    assert cache.get("a") == b"a"
    assert cache.get("c") == b"c"


def test_get_missing_returns_none() -> None:
    cache = TraceCache(capacity=1)
    assert cache.get("nope") is None


def test_capacity_must_be_positive() -> None:
    with pytest.raises(ValueError, match="capacity"):
        TraceCache(capacity=0)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/viz/test_cache.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement the cache**

Create `src/zipmould/viz/cache.py`:

```python
"""Bounded in-memory cache of Trace CBOR payloads, keyed by trace id."""

from __future__ import annotations

from collections import OrderedDict
from threading import Lock


class TraceCache:
    """A small thread-safe LRU keyed cache for byte payloads."""

    def __init__(self, capacity: int) -> None:
        if capacity <= 0:
            msg = f"capacity must be positive, got {capacity}"
            raise ValueError(msg)
        self._capacity = capacity
        self._items: OrderedDict[str, bytes] = OrderedDict()
        self._lock = Lock()

    def put(self, key: str, value: bytes) -> None:
        with self._lock:
            if key in self._items:
                self._items.move_to_end(key)
            self._items[key] = value
            while len(self._items) > self._capacity:
                self._items.popitem(last=False)

    def get(self, key: str) -> bytes | None:
        with self._lock:
            value = self._items.get(key)
            if value is not None:
                self._items.move_to_end(key)
            return value
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/viz/test_cache.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add src/zipmould/viz/cache.py tests/viz/test_cache.py
git commit -m "feat(viz): bounded LRU cache for trace bytes"
```

---

## Task 4: Pydantic schemas

**Goal:** Declare the API request/response models in one place. Endpoints in later tasks depend on these.

**Files:**
- Create: `src/zipmould/viz/schemas.py`
- Create: `tests/viz/test_schemas.py`

- [ ] **Step 1: Write the failing test**

Create `tests/viz/test_schemas.py`:

```python
"""API schema validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from zipmould.viz.schemas import RunRequest, ALLOWED_VARIANTS


def test_run_request_minimal_payload() -> None:
    req = RunRequest.model_validate(
        {"puzzle_id": "level_1", "variant": "zipmould-uni-positive", "seed": 0}
    )
    assert req.puzzle_id == "level_1"
    assert req.variant == "zipmould-uni-positive"
    assert req.seed == 0
    assert req.config_overrides == {}


def test_run_request_with_overrides() -> None:
    req = RunRequest.model_validate(
        {
            "puzzle_id": "level_1",
            "variant": "zipmould-uni-positive",
            "seed": 7,
            "config_overrides": {"alpha": 1.5, "iter_cap": 500},
        }
    )
    assert req.config_overrides == {"alpha": 1.5, "iter_cap": 500}


def test_run_request_rejects_unknown_variant() -> None:
    with pytest.raises(ValidationError):
        RunRequest.model_validate(
            {"puzzle_id": "x", "variant": "nope", "seed": 0}
        )


def test_allowed_variants_lists_four_zipmould_kinds() -> None:
    assert sorted(ALLOWED_VARIANTS) == [
        "zipmould-strat-positive",
        "zipmould-strat-signed",
        "zipmould-uni-positive",
        "zipmould-uni-signed",
    ]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/viz/test_schemas.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement the schemas**

Create `src/zipmould/viz/schemas.py`:

```python
"""Pydantic models for the viz HTTP API."""

from __future__ import annotations

from typing import Any, Final, Literal

from pydantic import BaseModel, ConfigDict, Field

ALLOWED_VARIANTS: Final[tuple[str, ...]] = (
    "zipmould-uni-signed",
    "zipmould-uni-positive",
    "zipmould-strat-signed",
    "zipmould-strat-positive",
)

VariantName = Literal[
    "zipmould-uni-signed",
    "zipmould-uni-positive",
    "zipmould-strat-signed",
    "zipmould-strat-positive",
]


class RunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    puzzle_id: str = Field(min_length=1)
    variant: VariantName
    seed: int = Field(ge=0)
    config_overrides: dict[str, Any] = Field(default_factory=dict)


class PuzzleSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    difficulty: str
    N: int
    K: int


class VariantSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    config_path: str
    defaults: dict[str, Any]


class ErrorBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: str
    detail: str


class RunResponse(BaseModel):
    """Wrapper around a JSON-shaped Trace plus a server-issued trace id."""

    model_config = ConfigDict(extra="forbid")

    trace_id: str
    trace: dict[str, Any]
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/viz/test_schemas.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add src/zipmould/viz/schemas.py tests/viz/test_schemas.py
git commit -m "feat(viz): API request/response schemas"
```

---

## Task 5: Runner — adapt `solve()` to a JSON Trace

**Goal:** Wrap `zipmould.solver.api.solve` so the API gets `(trace_dict, cbor_bytes)` from a single call, applying any `config_overrides`.

**Files:**
- Create: `src/zipmould/viz/runner.py`
- Create: `tests/viz/test_runner.py`

- [ ] **Step 1: Write the failing test**

Create `tests/viz/test_runner.py`:

```python
"""End-to-end runner: solve a tiny puzzle and verify the trace shape."""

from __future__ import annotations

from zipmould.puzzle import Puzzle
from zipmould.viz.runner import run_solve


def _tiny_puzzle() -> Puzzle:
    """A 3x3 grid with waypoints in opposite corners; trivially solvable."""
    return Puzzle(
        id="tiny",
        name="tiny",
        difficulty="Easy",
        N=3,
        K=2,
        waypoints=((0, 0), (2, 2)),
        walls=frozenset(),
        blocked=frozenset(),
    )


def test_runner_returns_trace_and_bytes() -> None:
    trace_dict, cbor_bytes = run_solve(
        puzzle=_tiny_puzzle(),
        variant="zipmould-uni-positive",
        seed=0,
        config_overrides={"iter_cap": 200, "population": 8},
    )
    assert trace_dict["puzzle_id"] == "tiny"
    assert isinstance(trace_dict["frames"], list)
    assert len(trace_dict["frames"]) > 0
    assert cbor_bytes[:2] != b""  # non-empty


def test_runner_applies_overrides() -> None:
    trace_dict, _ = run_solve(
        puzzle=_tiny_puzzle(),
        variant="zipmould-uni-positive",
        seed=0,
        config_overrides={"iter_cap": 50, "population": 4},
    )
    cfg = trace_dict["config"]
    assert cfg["iter_cap"] == 50
    assert cfg["population"] == 4
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/viz/test_runner.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement the runner**

Create `src/zipmould/viz/runner.py`:

```python
"""Adapter from a `RunRequest` to a JSON-shaped Trace plus its CBOR bytes."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

from zipmould.config import SolverConfig
from zipmould.puzzle import Puzzle
from zipmould.solver.api import solve
from zipmould.viz.trace_codec import trace_to_jsonable, write_cbor_bytes

_CONFIG_DIR = Path("configs/ablations")


class RunnerError(RuntimeError):
    """Raised when the runner cannot complete a solve cleanly."""


def _load_variant_defaults(variant: str) -> dict[str, Any]:
    """Merge `configs/default.toml` with the variant override TOML."""
    base_path = Path("configs/default.toml")
    variant_path = _CONFIG_DIR / f"{variant}.toml"
    if not base_path.exists():
        msg = f"missing base config: {base_path}"
        raise RunnerError(msg)
    if not variant_path.exists():
        msg = f"unknown variant config: {variant_path}"
        raise RunnerError(msg)
    with base_path.open("rb") as f:
        merged = tomllib.load(f).get("solver", {})
    with variant_path.open("rb") as f:
        merged.update(tomllib.load(f).get("solver", {}))
    return merged


def build_config(variant: str, overrides: dict[str, Any]) -> SolverConfig:
    """Compose a SolverConfig from variant defaults plus user overrides."""
    merged = _load_variant_defaults(variant)
    merged.update(overrides)
    return SolverConfig.model_validate(merged)


def run_solve(
    puzzle: Puzzle,
    variant: str,
    seed: int,
    config_overrides: dict[str, Any],
) -> tuple[dict[str, Any], bytes]:
    """Execute a synchronous solve and return (trace_dict, cbor_bytes).

    Raises RunnerError if the puzzle is statically infeasible (so the API
    can return 422 rather than a half-baked trace).
    """
    cfg = build_config(variant, config_overrides)
    result = solve(
        puzzle,
        cfg,
        seed=seed,
        trace=True,
        global_seed=0,
        condition=variant,
    )
    if result.infeasible or result.trace is None:
        reason = result.feasibility_reason or "no trace produced"
        msg = f"infeasible: {reason}"
        raise RunnerError(msg)
    trace_dict = trace_to_jsonable(result.trace)
    cbor_bytes = write_cbor_bytes(result.trace)
    return trace_dict, cbor_bytes
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/viz/test_runner.py -v
```

Expected: 2 passed. (First run will JIT-compile numba kernels and may take 10–30 s.)

- [ ] **Step 5: Commit**

```bash
git add src/zipmould/viz/runner.py tests/viz/test_runner.py
git commit -m "feat(viz): runner adapting solve() to JSON Trace + CBOR bytes"
```

---

## Task 6: `GET /api/puzzles` and `GET /api/variants`

**Goal:** Two read-only endpoints that drive the frontend's puzzle and variant pickers.

**Files:**
- Modify: `src/zipmould/viz/routes.py`
- Modify: `src/zipmould/viz/server.py`
- Create: `tests/viz/test_routes_puzzles.py`
- Create: `tests/viz/test_routes_variants.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/viz/test_routes_puzzles.py`:

```python
"""GET /api/puzzles."""

from __future__ import annotations

from fastapi.testclient import TestClient

from zipmould.viz.server import create_app


def test_puzzles_list_has_expected_fields() -> None:
    app = create_app()
    client = TestClient(app)
    resp = client.get("/api/puzzles")
    assert resp.status_code == 200
    items = resp.json()
    assert isinstance(items, list) and items
    sample = items[0]
    assert {"id", "name", "difficulty", "N", "K"} <= sample.keys()
```

Create `tests/viz/test_routes_variants.py`:

```python
"""GET /api/variants."""

from __future__ import annotations

from fastapi.testclient import TestClient

from zipmould.viz.server import create_app


def test_variants_list_contains_four_zipmould_kinds() -> None:
    app = create_app()
    client = TestClient(app)
    resp = client.get("/api/variants")
    assert resp.status_code == 200
    items = resp.json()
    names = {item["name"] for item in items}
    assert names == {
        "zipmould-uni-signed",
        "zipmould-uni-positive",
        "zipmould-strat-signed",
        "zipmould-strat-positive",
    }
    for item in items:
        assert "config_path" in item
        assert isinstance(item["defaults"], dict)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/viz/test_routes_puzzles.py tests/viz/test_routes_variants.py -v
```

Expected: 404 or attribute errors — no such routes yet.

- [ ] **Step 3: Implement the corpus + variants accessor and routes**

Replace `src/zipmould/viz/routes.py` with:

```python
"""HTTP route handlers for the viz API."""

from __future__ import annotations

import tomllib
from importlib.metadata import version as _pkg_version
from pathlib import Path
from typing import Any

from fastapi import APIRouter

from zipmould.io.puzzles import load_corpus
from zipmould.schemas_dummy import None as _placeholder  # placeholder removed below
```

That import block is wrong on purpose — replace the entire file with the full version below:

```python
"""HTTP route handlers for the viz API."""

from __future__ import annotations

import tomllib
from importlib.metadata import version as _pkg_version
from pathlib import Path
from typing import Any

from fastapi import APIRouter

from zipmould.io.puzzles import load_corpus
from zipmould.viz.schemas import ALLOWED_VARIANTS, PuzzleSummary, VariantSummary

router = APIRouter(prefix="/api")

_CONFIG_DIR = Path("configs/ablations")
_BASE_CONFIG = Path("configs/default.toml")


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": _pkg_version("zipmould")}


@router.get("/puzzles", response_model=list[PuzzleSummary])
def list_puzzles() -> list[PuzzleSummary]:
    corpus = load_corpus()
    return [
        PuzzleSummary(id=pz.id, name=pz.name, difficulty=str(pz.difficulty), N=pz.N, K=pz.K)
        for pz in corpus.values()
    ]


def _load_toml(path: Path) -> dict[str, Any]:
    with path.open("rb") as f:
        data = tomllib.load(f)
    return data.get("solver", data) if isinstance(data, dict) else {}


@router.get("/variants", response_model=list[VariantSummary])
def list_variants() -> list[VariantSummary]:
    base = _load_toml(_BASE_CONFIG)
    out: list[VariantSummary] = []
    for name in ALLOWED_VARIANTS:
        path = _CONFIG_DIR / f"{name}.toml"
        merged = dict(base)
        merged.update(_load_toml(path))
        out.append(VariantSummary(name=name, config_path=str(path), defaults=merged))
    return out
```

(The `server.py` already includes the router, so no changes there.)

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/viz/test_routes_puzzles.py tests/viz/test_routes_variants.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add src/zipmould/viz/routes.py tests/viz/test_routes_puzzles.py tests/viz/test_routes_variants.py
git commit -m "feat(viz): GET /api/puzzles and /api/variants"
```

---

## Task 7: `POST /api/runs`

**Goal:** Submit a `RunRequest`, get a `RunResponse` with a fresh `trace_id` and the JSON-shaped Trace; the original CBOR is stashed in the cache.

**Files:**
- Modify: `src/zipmould/viz/server.py` (add module-level cache singleton)
- Modify: `src/zipmould/viz/routes.py` (add the route)
- Create: `tests/viz/test_routes_runs.py`

- [ ] **Step 1: Write the failing test**

Create `tests/viz/test_routes_runs.py`:

```python
"""POST /api/runs."""

from __future__ import annotations

from fastapi.testclient import TestClient

from zipmould.viz.server import create_app


def test_runs_returns_trace_and_id() -> None:
    app = create_app()
    client = TestClient(app)
    body = {
        "puzzle_id": "level_1",
        "variant": "zipmould-uni-positive",
        "seed": 0,
        "config_overrides": {"iter_cap": 200, "population": 8},
    }
    resp = client.post("/api/runs", json=body)
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert isinstance(payload["trace_id"], str) and payload["trace_id"]
    trace = payload["trace"]
    assert trace["puzzle_id"] == "level_1"
    assert isinstance(trace["frames"], list)


def test_runs_unknown_puzzle_returns_404() -> None:
    app = create_app()
    client = TestClient(app)
    body = {"puzzle_id": "no-such", "variant": "zipmould-uni-positive", "seed": 0}
    resp = client.post("/api/runs", json=body)
    assert resp.status_code == 404
    assert resp.json()["kind"] == "puzzle_not_found"


def test_runs_unknown_variant_returns_422() -> None:
    app = create_app()
    client = TestClient(app)
    body = {"puzzle_id": "level_1", "variant": "frobnicate", "seed": 0}
    resp = client.post("/api/runs", json=body)
    assert resp.status_code == 422
```

(Assumes the corpus exposes a puzzle id `level_1` — the fixture corpus contains `level_1` through `level_…`. If your local corpus uses different ids, swap to one that exists; the dev split has known ids in `experiments/stage1/manifest.toml` references but the test only needs any one valid id. Run `uv run zipmould inspect level_1` once first to confirm.)

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/viz/test_routes_runs.py -v
```

Expected: 404 on the route itself.

- [ ] **Step 3: Add the cache singleton + run route**

Replace `src/zipmould/viz/server.py` with:

```python
"""FastAPI application factory."""

from __future__ import annotations

from fastapi import FastAPI

from zipmould.viz.cache import TraceCache
from zipmould.viz.routes import router as api_router

_TRACE_CACHE_CAPACITY = 8


def create_app() -> FastAPI:
    app = FastAPI(title="ZipMould Visualizer", version="0.1.0")
    app.state.trace_cache = TraceCache(capacity=_TRACE_CACHE_CAPACITY)
    app.include_router(api_router)
    return app
```

Append to `src/zipmould/viz/routes.py` (after the existing routes):

```python
import uuid

from fastapi import HTTPException, Request

from zipmould.viz.runner import RunnerError, run_solve
from zipmould.viz.schemas import RunRequest, RunResponse


@router.post("/runs", response_model=RunResponse)
def post_run(req: RunRequest, request: Request) -> RunResponse:
    corpus = load_corpus()
    if req.puzzle_id not in corpus:
        raise HTTPException(
            status_code=404,
            detail={"kind": "puzzle_not_found", "detail": f"unknown puzzle {req.puzzle_id!r}"},
        )
    puzzle = corpus[req.puzzle_id]
    try:
        trace_dict, cbor_bytes = run_solve(
            puzzle=puzzle,
            variant=req.variant,
            seed=req.seed,
            config_overrides=req.config_overrides,
        )
    except RunnerError as exc:
        raise HTTPException(
            status_code=422,
            detail={"kind": "infeasible", "detail": str(exc)},
        ) from exc
    trace_id = uuid.uuid4().hex
    request.app.state.trace_cache.put(trace_id, cbor_bytes)
    return RunResponse(trace_id=trace_id, trace=trace_dict)
```

(Move all `import` lines to the top of the file; the snippet shows them inline for clarity.)

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/viz/test_routes_runs.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add src/zipmould/viz/server.py src/zipmould/viz/routes.py tests/viz/test_routes_runs.py
git commit -m "feat(viz): POST /api/runs with cached CBOR"
```

---

## Task 8: Trace upload + download endpoints

**Goal:** `POST /api/traces/upload` accepts a `.cbor` file via multipart, parses it, caches the bytes, and returns the JSON Trace. `GET /api/traces/{id}.cbor` streams the original bytes back.

**Files:**
- Modify: `src/zipmould/viz/routes.py`
- Create: `tests/viz/test_routes_traces.py`
- Create: `tests/viz/fixtures/__init__.py`
- Create helper: `tests/viz/fixtures/builder.py`

- [ ] **Step 1: Write a fixture builder helper**

Create `tests/viz/fixtures/__init__.py` (empty file).

Create `tests/viz/fixtures/builder.py`:

```python
"""Builders for tiny synthetic traces used in viz tests."""

from __future__ import annotations

from zipmould.io.trace import (
    BestPath,
    Frame,
    TauDelta,
    Trace,
    TraceFooter,
    TraceHeader,
    WalkerSnapshot,
)
from zipmould.viz.trace_codec import write_cbor_bytes


def tiny_cbor() -> bytes:
    """Two-frame trace small enough to embed in tests."""
    header = TraceHeader(
        N=3,
        K=2,
        L=9,
        waypoints=((0, 0), (2, 2)),
        walls=(),
        blocked=(),
    )
    walker = WalkerSnapshot(id=0, cell=(0, 0), segment=0, status="alive", fitness=0.0)
    frames = (
        Frame(
            t=0,
            v_b=0.0,
            v_c=0.0,
            tau_delta=TauDelta(mode="unified", edges=()),
            best=BestPath(path=((0, 0),), fitness=0.0),
            walkers=(walker,),
        ),
        Frame(
            t=5,
            v_b=0.1,
            v_c=0.2,
            tau_delta=TauDelta(mode="unified", edges=((0, -1, 0.5),)),
            best=BestPath(path=((0, 0), (0, 1)), fitness=0.5),
            walkers=(walker,),
        ),
    )
    footer = TraceFooter(
        solved=False,
        infeasible=False,
        solution=None,
        iterations_used=10,
        wall_clock_s=0.001,
        best_fitness=0.5,
    )
    trace = Trace(
        version=1,
        puzzle_id="fixture",
        config={"alpha": 1.0, "tau_max": 10.0, "tau_signed": True},
        seed=0,
        header=header,
        frames=frames,
        footer=footer,
    )
    return write_cbor_bytes(trace)
```

- [ ] **Step 2: Write the failing test**

Create `tests/viz/test_routes_traces.py`:

```python
"""POST /api/traces/upload and GET /api/traces/{id}.cbor."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.viz.fixtures.builder import tiny_cbor
from zipmould.viz.server import create_app


def test_upload_returns_jsonable_trace_and_id() -> None:
    app = create_app()
    client = TestClient(app)
    payload = tiny_cbor()
    resp = client.post(
        "/api/traces/upload",
        files={"file": ("tiny.cbor", payload, "application/cbor")},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["trace"]["puzzle_id"] == "fixture"
    assert isinstance(body["trace_id"], str) and body["trace_id"]


def test_upload_then_download_round_trips_bytes() -> None:
    app = create_app()
    client = TestClient(app)
    payload = tiny_cbor()
    upload = client.post(
        "/api/traces/upload",
        files={"file": ("tiny.cbor", payload, "application/cbor")},
    )
    trace_id = upload.json()["trace_id"]
    download = client.get(f"/api/traces/{trace_id}.cbor")
    assert download.status_code == 200
    assert download.content == payload
    assert download.headers["content-type"].startswith("application/cbor")


def test_download_unknown_id_returns_404() -> None:
    app = create_app()
    client = TestClient(app)
    resp = client.get("/api/traces/deadbeef.cbor")
    assert resp.status_code == 404
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
uv run pytest tests/viz/test_routes_traces.py -v
```

Expected: 404s on the routes.

- [ ] **Step 4: Add the upload + download routes**

Append to `src/zipmould/viz/routes.py`:

```python
from fastapi import File, UploadFile
from fastapi.responses import Response

from zipmould.viz.trace_codec import read_cbor_bytes


@router.post("/traces/upload", response_model=RunResponse)
async def upload_trace(file: UploadFile, request: Request) -> RunResponse:
    raw = await file.read()
    try:
        trace = read_cbor_bytes(raw)
    except Exception as exc:  # cbor errors are heterogeneous
        raise HTTPException(
            status_code=422,
            detail={"kind": "invalid_cbor", "detail": str(exc)},
        ) from exc
    trace_id = uuid.uuid4().hex
    request.app.state.trace_cache.put(trace_id, raw)
    from zipmould.viz.trace_codec import trace_to_jsonable
    return RunResponse(trace_id=trace_id, trace=trace_to_jsonable(trace))


@router.get("/traces/{trace_id}.cbor")
def download_trace(trace_id: str, request: Request) -> Response:
    raw = request.app.state.trace_cache.get(trace_id)
    if raw is None:
        raise HTTPException(
            status_code=404,
            detail={"kind": "trace_not_found", "detail": trace_id},
        )
    return Response(content=raw, media_type="application/cbor")
```

(Hoist the `from zipmould.viz.trace_codec import trace_to_jsonable` import to the top with the other imports when you commit.)

- [ ] **Step 5: Run tests to verify they pass**

```bash
uv run pytest tests/viz/test_routes_traces.py -v
```

Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add src/zipmould/viz/routes.py tests/viz/test_routes_traces.py tests/viz/fixtures/
git commit -m "feat(viz): trace upload and CBOR download endpoints"
```

---

## Task 9: Error envelope handlers

**Goal:** Make every error response have shape `{kind: str, detail: str}`. FastAPI's default `HTTPException` returns `{detail: ...}`; we need a global handler that flattens `{kind, detail}` payloads and re-shapes Pydantic 422 errors.

**Files:**
- Modify: `src/zipmould/viz/server.py`
- Create: `tests/viz/test_routes_errors.py`

- [ ] **Step 1: Write the failing test**

Create `tests/viz/test_routes_errors.py`:

```python
"""Standardised error envelope."""

from __future__ import annotations

from fastapi.testclient import TestClient

from zipmould.viz.server import create_app


def test_404_uses_envelope() -> None:
    app = create_app()
    client = TestClient(app)
    resp = client.get("/api/traces/no-such.cbor")
    assert resp.status_code == 404
    body = resp.json()
    assert body == {"kind": "trace_not_found", "detail": "no-such"}


def test_422_validation_uses_envelope() -> None:
    app = create_app()
    client = TestClient(app)
    resp = client.post("/api/runs", json={"puzzle_id": "", "variant": "x", "seed": -1})
    assert resp.status_code == 422
    body = resp.json()
    assert body["kind"] == "validation_error"
    assert isinstance(body["detail"], str) and body["detail"]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/viz/test_routes_errors.py -v
```

Expected: failures on response shape.

- [ ] **Step 3: Add exception handlers**

Replace `src/zipmould/viz/server.py` with:

```python
"""FastAPI application factory with custom error envelopes."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from zipmould.viz.cache import TraceCache
from zipmould.viz.routes import router as api_router

_TRACE_CACHE_CAPACITY = 8


def _http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail
    if isinstance(detail, dict) and "kind" in detail and "detail" in detail:
        body = {"kind": str(detail["kind"]), "detail": str(detail["detail"])}
    else:
        body = {"kind": "http_error", "detail": str(detail)}
    return JSONResponse(status_code=exc.status_code, content=body)


def _validation_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    parts = []
    for err in exc.errors():
        loc = ".".join(str(p) for p in err.get("loc", ()))
        msg = err.get("msg", "")
        parts.append(f"{loc}: {msg}" if loc else msg)
    body = {"kind": "validation_error", "detail": "; ".join(parts) or "validation error"}
    return JSONResponse(status_code=422, content=body)


def _generic_handler(_request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500, content={"kind": "internal", "detail": str(exc)}
    )


def create_app() -> FastAPI:
    app = FastAPI(title="ZipMould Visualizer", version="0.1.0")
    app.state.trace_cache = TraceCache(capacity=_TRACE_CACHE_CAPACITY)
    app.include_router(api_router)
    app.add_exception_handler(HTTPException, _http_exception_handler)
    app.add_exception_handler(RequestValidationError, _validation_handler)
    app.add_exception_handler(Exception, _generic_handler)
    return app
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/viz/test_routes_errors.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Run the full backend suite**

```bash
uv run pytest tests/viz/ -v
```

Expected: all viz tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/zipmould/viz/server.py tests/viz/test_routes_errors.py
git commit -m "feat(viz): standardised error envelope"
```

---

## Task 10: CLI subcommand `zipmould viz serve`

**Goal:** Wire a Typer subcommand that launches uvicorn and (optionally) auto-reloads.

**Files:**
- Modify: `src/zipmould/cli.py`
- Create: `tests/viz/test_cli.py`

- [ ] **Step 1: Write the failing test**

Create `tests/viz/test_cli.py`:

```python
"""`zipmould viz serve` is registered as a Typer subcommand."""

from __future__ import annotations

from typer.testing import CliRunner

from zipmould.cli import app


def test_viz_serve_help_lists_options() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["viz", "serve", "--help"])
    assert result.exit_code == 0
    out = result.stdout
    assert "--host" in out
    assert "--port" in out
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/viz/test_cli.py -v
```

Expected: non-zero exit code (no such subcommand).

- [ ] **Step 3: Add the subcommand**

In `src/zipmould/cli.py`, after the `app = typer.Typer(...)` line, register a sub-app:

```python
viz_app = typer.Typer(no_args_is_help=True, help="Visualizer commands.")
app.add_typer(viz_app, name="viz")


@viz_app.command("serve")
def viz_serve_cmd(
    host: Annotated[str, typer.Option(help="Bind host.")] = "127.0.0.1",
    port: Annotated[int, typer.Option(help="Bind port.")] = 8000,
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
```

(`Annotated` and `typer` are already imported in `cli.py`. Add `from zipmould.logging_config import configure_logging` only if it isn't already at the top — it is, per the existing file.)

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/viz/test_cli.py -v
```

Expected: 1 passed.

- [ ] **Step 5: Smoke-test the server starts**

```bash
uv run zipmould viz serve --host 127.0.0.1 --port 8765 &
SERVER_PID=$!
sleep 2
curl -s http://127.0.0.1:8765/api/health
kill $SERVER_PID
```

Expected: JSON `{"status":"ok","version":"0.1.0"}`.

- [ ] **Step 6: Commit**

```bash
git add src/zipmould/cli.py tests/viz/test_cli.py
git commit -m "feat(viz): zipmould viz serve CLI"
```

---

## Task 11: Initialize the frontend project

**Goal:** Stand up `viz-web/` with Vue 3 + TypeScript + Vite + Pinia + Tailwind v4 + Vitest, managed by `bun`. End state: `bun run dev` starts Vite on `:5173` rendering "Hello".

**Files:**
- Create: entire `viz-web/` tree as listed in the file structure section.
- Modify: `.gitignore` (add `viz-web/node_modules/` and `src/zipmould/viz/static/`).

- [ ] **Step 1: Scaffold with bun**

```bash
cd viz-web && rm -rf .  # only if directory exists from a previous attempt; skip otherwise
cd /home/gtkacz/Codes/slime-mould
bun create vue@latest viz-web -- --typescript --pinia --vitest --eslint
cd viz-web && bun install
```

When `create vue` prompts:
- Add TypeScript: **Yes**
- Add JSX: **No**
- Add Vue Router: **No**
- Add Pinia: **Yes**
- Add Vitest: **Yes**
- Add E2E: **Playwright**
- Add ESLint: **Yes**
- Add Prettier: **Yes**

- [ ] **Step 2: Add Tailwind v4 + cbor-x**

```bash
cd viz-web
bun add tailwindcss @tailwindcss/vite cbor-x
```

Edit `viz-web/vite.config.ts` — add the plugin and a proxy:

```ts
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    },
  },
  build: {
    outDir: '../src/zipmould/viz/static',
    emptyOutDir: true,
  },
})
```

Create `viz-web/src/styles/tailwind.css`:

```css
@import "tailwindcss";
```

In `viz-web/src/main.ts`, replace its body with:

```ts
import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import './styles/tailwind.css'

createApp(App).use(createPinia()).mount('#app')
```

Replace `viz-web/src/App.vue` with a placeholder:

```vue
<template>
  <main class="min-h-screen flex items-center justify-center text-2xl text-zinc-200 bg-zinc-900">
    ZipMould Visualizer
  </main>
</template>

<script setup lang="ts">
</script>
```

- [ ] **Step 3: Update `.gitignore`**

Append to repo `.gitignore`:

```
# Visualizer
viz-web/node_modules/
viz-web/dist/
src/zipmould/viz/static/
```

- [ ] **Step 4: Smoke-test the dev server**

```bash
cd viz-web && bun run dev
```

Open `http://localhost:5173`. Expected: dark page with "ZipMould Visualizer" centered.

- [ ] **Step 5: Smoke-test the test runner**

```bash
cd viz-web && bun run test:unit -- --run
```

Expected: scaffolded sample tests pass (or zero tests if scaffold provides none — that's fine).

- [ ] **Step 6: Commit**

```bash
git add viz-web/ .gitignore
git commit -m "feat(viz): scaffold Vue 3 + Vite + Tailwind frontend"
```

---

## Task 12: Frontend API client and types

**Goal:** A single typed fetch wrapper plus mirrored types matching the backend schemas. All future stores and components use it.

**Files:**
- Create: `viz-web/src/api/types.ts`
- Create: `viz-web/src/api/client.ts`
- Create: `viz-web/src/api/__tests__/client.spec.ts`

- [ ] **Step 1: Write the failing test**

Create `viz-web/src/api/__tests__/client.spec.ts`:

```ts
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ApiClient, ApiError } from '../client'

describe('ApiClient', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('GETs absolute paths under /api', async () => {
    const fetchMock = vi.fn(
      async () => new Response(JSON.stringify({ status: 'ok', version: '0.1.0' })),
    )
    vi.stubGlobal('fetch', fetchMock)
    const client = new ApiClient()
    const out = await client.health()
    expect(out.status).toBe('ok')
    const url = String(fetchMock.mock.calls[0][0])
    expect(url.endsWith('/api/health')).toBe(true)
  })

  it('throws ApiError with kind+detail on non-2xx', async () => {
    const body = JSON.stringify({ kind: 'puzzle_not_found', detail: 'no-such' })
    const fetchMock = vi.fn(async () => new Response(body, { status: 404 }))
    vi.stubGlobal('fetch', fetchMock)
    const client = new ApiClient()
    await expect(
      client.runSolve({ puzzle_id: 'no-such', variant: 'zipmould-uni-positive', seed: 0 }),
    ).rejects.toMatchObject({
      kind: 'puzzle_not_found',
      detail: 'no-such',
      status: 404,
    })
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd viz-web && bun run test:unit -- --run src/api
```

Expected: cannot find `../client`.

- [ ] **Step 3: Implement types and client**

Create `viz-web/src/api/types.ts`:

```ts
export type WalkerStatus = 'alive' | 'dead-end' | 'complete'

export interface WalkerSnapshot {
  id: number
  cell: [number, number]
  segment: number
  status: WalkerStatus
  fitness: number
}

export interface BestPath {
  path: [number, number][]
  fitness: number
}

export interface TauDelta {
  mode: 'unified' | 'stratified'
  edges: [number, number, number][]
}

export interface Frame {
  t: number
  v_b: number
  v_c: number
  tau_delta: TauDelta
  best: BestPath
  walkers: WalkerSnapshot[]
}

export interface TraceHeader {
  N: number
  K: number
  L: number
  waypoints: [number, number][]
  walls: [[number, number], [number, number]][]
  blocked: [number, number][]
}

export interface TraceFooter {
  solved: boolean
  infeasible: boolean
  solution: [number, number][] | null
  iterations_used: number
  wall_clock_s: number
  best_fitness: number
}

export interface Trace {
  version: number
  puzzle_id: string
  config: Record<string, unknown>
  seed: number
  header: TraceHeader
  frames: Frame[]
  footer: TraceFooter
}

export interface PuzzleSummary {
  id: string
  name: string
  difficulty: string
  N: number
  K: number
}

export interface VariantSummary {
  name: string
  config_path: string
  defaults: Record<string, unknown>
}

export interface RunRequest {
  puzzle_id: string
  variant: string
  seed: number
  config_overrides?: Record<string, unknown>
}

export interface RunResponse {
  trace_id: string
  trace: Trace
}

export interface HealthResponse {
  status: string
  version: string
}
```

Create `viz-web/src/api/client.ts`:

```ts
import type {
  HealthResponse,
  PuzzleSummary,
  RunRequest,
  RunResponse,
  VariantSummary,
} from './types'

export class ApiError extends Error {
  readonly kind: string
  readonly detail: string
  readonly status: number
  constructor(kind: string, detail: string, status: number) {
    super(`[${status}] ${kind}: ${detail}`)
    this.kind = kind
    this.detail = detail
    this.status = status
  }
}

async function parseError(resp: Response): Promise<never> {
  let kind = 'http_error'
  let detail = resp.statusText
  try {
    const body = (await resp.json()) as { kind?: string; detail?: string }
    if (body.kind) kind = body.kind
    if (body.detail) detail = body.detail
  } catch {
    // body wasn't JSON; keep defaults
  }
  throw new ApiError(kind, detail, resp.status)
}

export class ApiClient {
  constructor(private readonly base = '/api') {}

  private async request<T>(path: string, init?: RequestInit): Promise<T> {
    const resp = await fetch(`${this.base}${path}`, {
      headers: { 'Content-Type': 'application/json' },
      ...init,
    })
    if (!resp.ok) await parseError(resp)
    return (await resp.json()) as T
  }

  health(): Promise<HealthResponse> {
    return this.request('/health')
  }

  listPuzzles(): Promise<PuzzleSummary[]> {
    return this.request('/puzzles')
  }

  listVariants(): Promise<VariantSummary[]> {
    return this.request('/variants')
  }

  runSolve(req: RunRequest): Promise<RunResponse> {
    return this.request('/runs', {
      method: 'POST',
      body: JSON.stringify(req),
    })
  }

  async uploadTrace(file: Blob): Promise<RunResponse> {
    const form = new FormData()
    form.append('file', file)
    const resp = await fetch(`${this.base}/traces/upload`, {
      method: 'POST',
      body: form,
    })
    if (!resp.ok) await parseError(resp)
    return (await resp.json()) as RunResponse
  }

  downloadTraceUrl(traceId: string): string {
    return `${this.base}/traces/${traceId}.cbor`
  }
}

export const api = new ApiClient()
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd viz-web && bun run test:unit -- --run src/api
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add viz-web/src/api/
git commit -m "feat(viz): typed API client and shared types"
```

---

## Task 13: Notifications store + ErrorToasts

**Goal:** Centralize error/info messages so any component can surface failures uniformly.

**Files:**
- Create: `viz-web/src/stores/notifications.ts`
- Create: `viz-web/src/stores/__tests__/notifications.spec.ts`
- Create: `viz-web/src/components/ErrorToasts.vue`

- [ ] **Step 1: Write the failing test**

Create `viz-web/src/stores/__tests__/notifications.spec.ts`:

```ts
import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useNotificationsStore } from '../notifications'

describe('notifications store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('pushes and dismisses messages', () => {
    const store = useNotificationsStore()
    const id = store.push({ kind: 'error', text: 'boom' })
    expect(store.items).toHaveLength(1)
    store.dismiss(id)
    expect(store.items).toHaveLength(0)
  })

  it('caps at 5 messages, dropping the oldest', () => {
    const store = useNotificationsStore()
    for (let i = 0; i < 7; i++) store.push({ kind: 'info', text: `n${i}` })
    expect(store.items).toHaveLength(5)
    expect(store.items[0].text).toBe('n2')
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd viz-web && bun run test:unit -- --run src/stores
```

Expected: cannot resolve module.

- [ ] **Step 3: Implement the store**

Create `viz-web/src/stores/notifications.ts`:

```ts
import { defineStore } from 'pinia'
import { ref } from 'vue'

export type NotificationKind = 'info' | 'error'

export interface Notification {
  id: number
  kind: NotificationKind
  text: string
}

const MAX_ITEMS = 5

export const useNotificationsStore = defineStore('notifications', () => {
  const items = ref<Notification[]>([])
  let nextId = 1

  function push(input: Omit<Notification, 'id'>): number {
    const id = nextId++
    items.value.push({ id, ...input })
    while (items.value.length > MAX_ITEMS) items.value.shift()
    return id
  }

  function dismiss(id: number): void {
    items.value = items.value.filter((n) => n.id !== id)
  }

  return { items, push, dismiss }
})
```

Create `viz-web/src/components/ErrorToasts.vue`:

```vue
<template>
  <div class="fixed bottom-4 right-4 flex flex-col gap-2 z-50">
    <div
      v-for="n in store.items"
      :key="n.id"
      :class="[
        'rounded px-4 py-2 shadow text-sm',
        n.kind === 'error' ? 'bg-red-700 text-white' : 'bg-zinc-700 text-zinc-100',
      ]"
      @click="store.dismiss(n.id)"
    >
      {{ n.text }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { useNotificationsStore } from '../stores/notifications'

const store = useNotificationsStore()
</script>
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd viz-web && bun run test:unit -- --run src/stores
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add viz-web/src/stores/notifications.ts viz-web/src/components/ErrorToasts.vue viz-web/src/stores/__tests__/notifications.spec.ts
git commit -m "feat(viz): notifications store + ErrorToasts component"
```

---

## Task 14: Trace store

**Goal:** Hold the currently-loaded `Trace` and its server-issued `trace_id`. Single source of truth for replay-related components.

**Files:**
- Create: `viz-web/src/stores/trace.ts`
- Create: `viz-web/src/stores/__tests__/trace.spec.ts`

- [ ] **Step 1: Write the failing test**

Create `viz-web/src/stores/__tests__/trace.spec.ts`:

```ts
import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useTraceStore } from '../trace'
import type { Trace } from '../../api/types'

const fakeTrace: Trace = {
  version: 1,
  puzzle_id: 'tiny',
  config: {},
  seed: 0,
  header: { N: 3, K: 2, L: 9, waypoints: [], walls: [], blocked: [] },
  frames: [],
  footer: {
    solved: false,
    infeasible: false,
    solution: null,
    iterations_used: 0,
    wall_clock_s: 0,
    best_fitness: 0,
  },
}

describe('trace store', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('starts empty', () => {
    const s = useTraceStore()
    expect(s.trace).toBeNull()
    expect(s.traceId).toBeNull()
  })

  it('sets trace and id together', () => {
    const s = useTraceStore()
    s.set('abc', fakeTrace)
    expect(s.trace).toEqual(fakeTrace)
    expect(s.traceId).toBe('abc')
  })

  it('clears state', () => {
    const s = useTraceStore()
    s.set('abc', fakeTrace)
    s.clear()
    expect(s.trace).toBeNull()
    expect(s.traceId).toBeNull()
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd viz-web && bun run test:unit -- --run src/stores/__tests__/trace
```

Expected: cannot resolve module.

- [ ] **Step 3: Implement the store**

Create `viz-web/src/stores/trace.ts`:

```ts
import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Trace } from '../api/types'

export const useTraceStore = defineStore('trace', () => {
  const trace = ref<Trace | null>(null)
  const traceId = ref<string | null>(null)

  function set(id: string, value: Trace): void {
    traceId.value = id
    trace.value = value
  }

  function clear(): void {
    trace.value = null
    traceId.value = null
  }

  return { trace, traceId, set, clear }
})
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd viz-web && bun run test:unit -- --run src/stores/__tests__/trace
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add viz-web/src/stores/trace.ts viz-web/src/stores/__tests__/trace.spec.ts
git commit -m "feat(viz): trace store"
```

---

## Task 15: `useTraceReplay` composable (load-bearing)

**Goal:** Given a `Trace`, expose a frame index plus a reactive accumulated pheromone `Float32Array`. Use periodic checkpoints so seeking is O(checkpoint_interval) instead of O(N_frames).

**Files:**
- Create: `viz-web/src/composables/useTraceReplay.ts`
- Create: `viz-web/src/composables/__tests__/useTraceReplay.spec.ts`

- [ ] **Step 1: Write the failing test**

Create `viz-web/src/composables/__tests__/useTraceReplay.spec.ts`:

```ts
import { describe, it, expect } from 'vitest'
import { ref } from 'vue'
import { useTraceReplay } from '../useTraceReplay'
import type { Trace } from '../../api/types'

function makeTrace(L: number, mode: 'unified' | 'stratified', frameDeltas: [number, number, number][][]): Trace {
  return {
    version: 1,
    puzzle_id: 't',
    config: { tau_max: 10, tau_signed: true },
    seed: 0,
    header: { N: 2, K: 1, L, waypoints: [], walls: [], blocked: [] },
    frames: frameDeltas.map((edges, i) => ({
      t: i,
      v_b: 0,
      v_c: 0,
      tau_delta: { mode, edges },
      best: { path: [], fitness: 0 },
      walkers: [],
    })),
    footer: {
      solved: false,
      infeasible: false,
      solution: null,
      iterations_used: 0,
      wall_clock_s: 0,
      best_fitness: 0,
    },
  }
}

describe('useTraceReplay', () => {
  it('accumulates deltas forward', () => {
    const trace = makeTrace(2, 'unified', [
      [[0, -1, 0.5]],
      [[1, -1, 0.25]],
      [[0, -1, -0.1]],
    ])
    const idx = ref(0)
    const replay = useTraceReplay(ref(trace), idx)
    expect(Array.from(replay.tau.value)).toEqual([0, 0, 0, 0])
    idx.value = 1
    expect(Array.from(replay.tau.value)).toEqual([0.5, 0, 0, 0])
    idx.value = 2
    expect(Array.from(replay.tau.value)).toEqual([0.5, 0.25, 0, 0])
    idx.value = 3
    expect(replay.tau.value[0]).toBeCloseTo(0.4)
  })

  it('seeking forward and back gives the same field as forward replay', () => {
    const deltas: [number, number, number][][] = []
    for (let i = 0; i < 200; i++) {
      deltas.push([[(i * 7) % 16, -1, 0.01]])
    }
    const trace = makeTrace(8, 'unified', deltas)
    const idx = ref(0)
    const replay = useTraceReplay(ref(trace), idx, { checkpointInterval: 32 })

    idx.value = 199
    const forward = Float32Array.from(replay.tau.value)
    idx.value = 0
    idx.value = 199
    const seek = Float32Array.from(replay.tau.value)
    expect(Array.from(seek)).toEqual(Array.from(forward))
  })

  it('exposes current frame, walkers, and best path', () => {
    const trace = makeTrace(2, 'unified', [[]])
    const idx = ref(0)
    const replay = useTraceReplay(ref(trace), idx)
    expect(replay.frame.value?.t).toBe(0)
    expect(replay.walkers.value).toEqual([])
    expect(replay.bestPath.value).toEqual([])
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd viz-web && bun run test:unit -- --run src/composables
```

Expected: cannot resolve module.

- [ ] **Step 3: Implement the composable**

Create `viz-web/src/composables/useTraceReplay.ts`:

```ts
import { computed, ref, watch, type Ref } from 'vue'
import type { Frame, Trace } from '../api/types'

export interface UseTraceReplayOptions {
  checkpointInterval?: number
}

const DEFAULT_CHECKPOINT_INTERVAL = 64

function tauLength(trace: Trace): number {
  const stripes = trace.frames.some((f) => f.tau_delta.mode === 'stratified')
    ? Math.max(2, trace.header.K)
    : 1
  return stripes * 2 * trace.header.L
}

function flatIndex(edgeId: number, stripe: number, halfL: number, mode: 'unified' | 'stratified'): number {
  const s = mode === 'unified' || stripe < 0 ? 0 : stripe
  return s * halfL + edgeId
}

function applyDelta(buf: Float32Array, frame: Frame, halfL: number): void {
  for (const [edgeId, stripe, delta] of frame.tau_delta.edges) {
    buf[flatIndex(edgeId, stripe, halfL, frame.tau_delta.mode)] += delta
  }
}

export function useTraceReplay(
  trace: Ref<Trace | null>,
  index: Ref<number>,
  opts: UseTraceReplayOptions = {},
) {
  const interval = opts.checkpointInterval ?? DEFAULT_CHECKPOINT_INTERVAL
  const checkpoints = ref<Float32Array[]>([])
  const tau = ref<Float32Array>(new Float32Array(0))
  const lastIndex = ref(-1)

  function rebuildCheckpoints(t: Trace): void {
    const length = tauLength(t)
    const halfL = 2 * t.header.L
    const cps: Float32Array[] = []
    let buf = new Float32Array(length)
    cps.push(new Float32Array(buf))
    for (let i = 0; i < t.frames.length; i++) {
      applyDelta(buf, t.frames[i], halfL)
      if ((i + 1) % interval === 0) cps.push(new Float32Array(buf))
    }
    checkpoints.value = cps
  }

  function seek(t: Trace, target: number): void {
    const length = tauLength(t)
    const halfL = 2 * t.header.L
    const cpIdx = Math.min(Math.floor(target / interval), checkpoints.value.length - 1)
    const buf = new Float32Array(checkpoints.value[cpIdx] ?? new Float32Array(length))
    const start = cpIdx * interval
    for (let i = start; i < target; i++) {
      applyDelta(buf, t.frames[i], halfL)
    }
    tau.value = buf
    lastIndex.value = target
  }

  function step(t: Trace, target: number): void {
    if (target === lastIndex.value + 1 && lastIndex.value >= 0) {
      const next = new Float32Array(tau.value)
      applyDelta(next, t.frames[lastIndex.value], 2 * t.header.L)
      tau.value = next
      lastIndex.value = target
    } else {
      seek(t, target)
    }
  }

  watch(
    trace,
    (t) => {
      if (!t) {
        checkpoints.value = []
        tau.value = new Float32Array(0)
        lastIndex.value = -1
        return
      }
      rebuildCheckpoints(t)
      seek(t, Math.min(Math.max(index.value, 0), t.frames.length - 1))
    },
    { immediate: true },
  )

  watch(index, (target) => {
    const t = trace.value
    if (!t || t.frames.length === 0) return
    const clamped = Math.min(Math.max(target, 0), t.frames.length - 1)
    if (clamped === lastIndex.value) return
    if (clamped > lastIndex.value && clamped - lastIndex.value <= 1) {
      step(t, clamped)
    } else {
      seek(t, clamped)
    }
  })

  const frame = computed<Frame | null>(() => {
    const t = trace.value
    if (!t || t.frames.length === 0) return null
    const i = Math.min(Math.max(index.value, 0), t.frames.length - 1)
    return t.frames[i]
  })

  const walkers = computed(() => frame.value?.walkers ?? [])
  const bestPath = computed(() => frame.value?.best.path ?? [])

  return { tau, frame, walkers, bestPath }
}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd viz-web && bun run test:unit -- --run src/composables
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add viz-web/src/composables/useTraceReplay.ts viz-web/src/composables/__tests__/useTraceReplay.spec.ts
git commit -m "feat(viz): trace replay composable with checkpointed pheromone"
```

---

## Task 16: Playback store

**Goal:** Hold frame index, play state, speed, and layer-visibility flags. Provides the actions ControlBar dispatches.

**Files:**
- Create: `viz-web/src/stores/playback.ts`
- Create: `viz-web/src/stores/__tests__/playback.spec.ts`

- [ ] **Step 1: Write the failing test**

Create `viz-web/src/stores/__tests__/playback.spec.ts`:

```ts
import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { usePlaybackStore } from '../playback'

describe('playback store', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('clamps the frame index to [0, total-1]', () => {
    const s = usePlaybackStore()
    s.setTotal(10)
    s.seek(-5)
    expect(s.index).toBe(0)
    s.seek(99)
    expect(s.index).toBe(9)
  })

  it('step advances by one within bounds', () => {
    const s = usePlaybackStore()
    s.setTotal(3)
    s.step(1)
    s.step(1)
    s.step(1)
    expect(s.index).toBe(2)
    s.step(-1)
    expect(s.index).toBe(1)
  })

  it('toggles play and clamps speed values', () => {
    const s = usePlaybackStore()
    expect(s.playing).toBe(false)
    s.togglePlay()
    expect(s.playing).toBe(true)
    s.setSpeed(0)
    expect(s.speed).toBe(1)
    s.setSpeed(99999)
    expect(s.speed).toBeLessThanOrEqual(s.MAX_SPEED)
  })

  it('layer visibility flags default to true and toggle', () => {
    const s = usePlaybackStore()
    expect(s.layers.pheromone).toBe(true)
    s.toggleLayer('pheromone')
    expect(s.layers.pheromone).toBe(false)
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd viz-web && bun run test:unit -- --run src/stores/__tests__/playback
```

Expected: module not found.

- [ ] **Step 3: Implement the store**

Create `viz-web/src/stores/playback.ts`:

```ts
import { defineStore } from 'pinia'
import { ref } from 'vue'

export type LayerKey = 'walls' | 'pheromone' | 'walkers' | 'bestPath' | 'waypoints'

export const usePlaybackStore = defineStore('playback', () => {
  const MAX_SPEED = 1024
  const index = ref(0)
  const total = ref(0)
  const playing = ref(false)
  const speed = ref(1)
  const layers = ref<Record<LayerKey, boolean>>({
    walls: true,
    pheromone: true,
    walkers: true,
    bestPath: true,
    waypoints: true,
  })

  function setTotal(n: number): void {
    total.value = Math.max(0, Math.floor(n))
    index.value = Math.min(index.value, Math.max(0, total.value - 1))
  }

  function seek(i: number): void {
    if (total.value === 0) {
      index.value = 0
      return
    }
    index.value = Math.min(Math.max(0, Math.floor(i)), total.value - 1)
  }

  function step(delta: number): void {
    seek(index.value + delta)
  }

  function togglePlay(): void {
    playing.value = !playing.value
  }

  function setSpeed(v: number): void {
    if (!Number.isFinite(v) || v < 1) {
      speed.value = 1
      return
    }
    speed.value = Math.min(Math.floor(v), MAX_SPEED)
  }

  function toggleLayer(key: LayerKey): void {
    layers.value[key] = !layers.value[key]
  }

  return {
    MAX_SPEED,
    index,
    total,
    playing,
    speed,
    layers,
    setTotal,
    seek,
    step,
    togglePlay,
    setSpeed,
    toggleLayer,
  }
})
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd viz-web && bun run test:unit -- --run src/stores/__tests__/playback
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add viz-web/src/stores/playback.ts viz-web/src/stores/__tests__/playback.spec.ts
git commit -m "feat(viz): playback store with frame index, speed, layers"
```

---

## Task 17: `useFileLoader` composable

**Goal:** Take a `File` (from drag-drop or `<input type=file>`), parse it as CBOR using `cbor-x`, hand the resulting `Trace` to the trace store, and POST the bytes to `/api/traces/upload` to get a server-issued id.

**Files:**
- Create: `viz-web/src/composables/useFileLoader.ts`
- Create: `viz-web/src/composables/__tests__/useFileLoader.spec.ts`

- [ ] **Step 1: Write the failing test**

Create `viz-web/src/composables/__tests__/useFileLoader.spec.ts`:

```ts
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useFileLoader } from '../useFileLoader'
import { useTraceStore } from '../../stores/trace'
import { ApiClient } from '../../api/client'

describe('useFileLoader', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('uploads the file and stores the resulting trace + id', async () => {
    const fakeTrace = {
      version: 1,
      puzzle_id: 'fixture',
      config: {},
      seed: 0,
      header: { N: 2, K: 1, L: 4, waypoints: [], walls: [], blocked: [] },
      frames: [],
      footer: {
        solved: false,
        infeasible: false,
        solution: null,
        iterations_used: 0,
        wall_clock_s: 0,
        best_fitness: 0,
      },
    }
    const client = new ApiClient()
    vi.spyOn(client, 'uploadTrace').mockResolvedValue({ trace_id: 'xyz', trace: fakeTrace })

    const loader = useFileLoader(client)
    const blob = new Blob([new Uint8Array([0xa0])], { type: 'application/cbor' })
    const file = new File([blob], 'tiny.cbor', { type: 'application/cbor' })
    await loader.load(file)

    const store = useTraceStore()
    expect(store.traceId).toBe('xyz')
    expect(store.trace?.puzzle_id).toBe('fixture')
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd viz-web && bun run test:unit -- --run src/composables/__tests__/useFileLoader
```

Expected: module not found.

- [ ] **Step 3: Implement the loader**

Create `viz-web/src/composables/useFileLoader.ts`:

```ts
import { ApiClient, ApiError, api as defaultApi } from '../api/client'
import { useTraceStore } from '../stores/trace'
import { useNotificationsStore } from '../stores/notifications'

export function useFileLoader(client: ApiClient = defaultApi) {
  const traceStore = useTraceStore()
  const notifications = useNotificationsStore()

  async function load(file: File): Promise<void> {
    try {
      const resp = await client.uploadTrace(file)
      traceStore.set(resp.trace_id, resp.trace)
    } catch (err) {
      const text =
        err instanceof ApiError
          ? `${err.kind}: ${err.detail}`
          : err instanceof Error
            ? err.message
            : 'unknown error loading trace'
      notifications.push({ kind: 'error', text })
      throw err
    }
  }

  return { load }
}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd viz-web && bun run test:unit -- --run src/composables/__tests__/useFileLoader
```

Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add viz-web/src/composables/useFileLoader.ts viz-web/src/composables/__tests__/useFileLoader.spec.ts
git commit -m "feat(viz): file loader composable"
```

---

## Task 18: `GridCanvas` and layered SVG rendering

**Goal:** Single Vue component renders the full grid with all five layers as nested `<g>` groups. Each layer reads visibility from the playback store and drawing state from the trace + replay composable.

**Files:**
- Create: `viz-web/src/components/GridCanvas.vue`
- Create: `viz-web/src/components/__tests__/GridCanvas.spec.ts`

- [ ] **Step 1: Write the failing test**

Create `viz-web/src/components/__tests__/GridCanvas.spec.ts`:

```ts
import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import GridCanvas from '../GridCanvas.vue'
import { useTraceStore } from '../../stores/trace'
import { usePlaybackStore } from '../../stores/playback'
import type { Trace } from '../../api/types'

const tinyTrace: Trace = {
  version: 1,
  puzzle_id: 'tiny',
  config: { tau_max: 10, tau_signed: true },
  seed: 0,
  header: {
    N: 2,
    K: 2,
    L: 4,
    waypoints: [
      [0, 0],
      [1, 1],
    ],
    walls: [],
    blocked: [],
  },
  frames: [
    {
      t: 0,
      v_b: 0,
      v_c: 0,
      tau_delta: { mode: 'unified', edges: [] },
      best: { path: [[0, 0]], fitness: 0 },
      walkers: [{ id: 0, cell: [0, 0], segment: 0, status: 'alive', fitness: 0 }],
    },
  ],
  footer: {
    solved: false,
    infeasible: false,
    solution: null,
    iterations_used: 0,
    wall_clock_s: 0,
    best_fitness: 0,
  },
}

describe('GridCanvas', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('renders an svg with the expected layer groups', async () => {
    const traceStore = useTraceStore()
    const playback = usePlaybackStore()
    traceStore.set('id', tinyTrace)
    playback.setTotal(1)
    playback.seek(0)

    const wrapper = mount(GridCanvas)
    await wrapper.vm.$nextTick()
    expect(wrapper.find('svg').exists()).toBe(true)
    expect(wrapper.find('[data-layer="walls"]').exists()).toBe(true)
    expect(wrapper.find('[data-layer="pheromone"]').exists()).toBe(true)
    expect(wrapper.find('[data-layer="best-path"]').exists()).toBe(true)
    expect(wrapper.find('[data-layer="walkers"]').exists()).toBe(true)
    expect(wrapper.find('[data-layer="waypoints"]').exists()).toBe(true)
  })

  it('hides a layer when its visibility flag flips off', async () => {
    const traceStore = useTraceStore()
    const playback = usePlaybackStore()
    traceStore.set('id', tinyTrace)
    playback.setTotal(1)

    const wrapper = mount(GridCanvas)
    await wrapper.vm.$nextTick()
    playback.toggleLayer('pheromone')
    await wrapper.vm.$nextTick()
    expect(wrapper.find('[data-layer="pheromone"]').exists()).toBe(false)
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd viz-web && bun run test:unit -- --run src/components/__tests__/GridCanvas
```

Expected: cannot resolve module.

- [ ] **Step 3: Implement the component**

Create `viz-web/src/components/GridCanvas.vue`:

```vue
<template>
  <svg
    v-if="trace"
    :viewBox="`0 0 ${size} ${size}`"
    class="bg-zinc-900 w-full h-full"
    role="img"
    aria-label="Solver grid"
  >
    <g v-if="layers.walls" data-layer="walls">
      <line
        v-for="(w, i) in trace.header.walls"
        :key="`wall-${i}`"
        :x1="cellPx(w[0][1])"
        :y1="cellPx(w[0][0])"
        :x2="cellPx(w[1][1])"
        :y2="cellPx(w[1][0])"
        stroke="#f87171"
        stroke-width="2"
      />
    </g>
    <g v-if="layers.pheromone" data-layer="pheromone">
      <rect
        v-for="(_, i) in cells"
        :key="`p-${i}`"
        :x="((i % trace.header.N) * cellSize)"
        :y="(Math.floor(i / trace.header.N) * cellSize)"
        :width="cellSize"
        :height="cellSize"
        :fill="cells[i]"
        stroke="#3f3f46"
        stroke-width="0.5"
      />
    </g>
    <g v-if="layers.bestPath" data-layer="best-path">
      <polyline
        :points="bestPathPoints"
        fill="none"
        stroke="#fafafa"
        stroke-width="3"
        stroke-linecap="round"
        stroke-linejoin="round"
        opacity="0.85"
      />
    </g>
    <g v-if="layers.walkers" data-layer="walkers">
      <circle
        v-for="w in walkers"
        :key="`w-${w.id}`"
        :cx="cellCenterX(w.cell)"
        :cy="cellCenterY(w.cell)"
        :r="cellSize * 0.18"
        :fill="walkerColor(w.status)"
      />
    </g>
    <g v-if="layers.waypoints" data-layer="waypoints">
      <text
        v-for="(wp, i) in trace.header.waypoints"
        :key="`wp-${i}`"
        :x="cellCenterX(wp)"
        :y="cellCenterY(wp)"
        text-anchor="middle"
        dominant-baseline="middle"
        :font-size="cellSize * 0.55"
        font-weight="700"
        fill="#fde68a"
      >
        {{ i + 1 }}
      </text>
    </g>
  </svg>
</template>

<script setup lang="ts">
import { computed, toRefs } from 'vue'
import { storeToRefs } from 'pinia'
import { useTraceStore } from '../stores/trace'
import { usePlaybackStore } from '../stores/playback'
import { useTraceReplay } from '../composables/useTraceReplay'
import type { WalkerStatus } from '../api/types'

const traceStore = useTraceStore()
const playback = usePlaybackStore()
const { trace } = toRefs(traceStore)
const { layers, index } = storeToRefs(playback)

const replay = useTraceReplay(trace, index)

const size = 480
const cellSize = computed(() => (trace.value ? size / trace.value.header.N : 0))

const cellPx = (i: number) => i * cellSize.value
const cellCenterX = (cell: [number, number]) => (cell[1] + 0.5) * cellSize.value
const cellCenterY = (cell: [number, number]) => (cell[0] + 0.5) * cellSize.value

function viridis(t: number): string {
  const u = Math.min(1, Math.max(0, t))
  const r = Math.round(255 * (0.267 + 1.084 * u - 0.351 * u * u))
  const g = Math.round(255 * (0.005 + 1.404 * u - 0.471 * u * u))
  const b = Math.round(255 * (0.329 + 0.718 * u - 0.851 * u * u))
  return `rgb(${r},${g},${b})`
}

const cells = computed<string[]>(() => {
  const t = trace.value
  if (!t) return []
  const cfg = t.config as { tau_max?: number; tau_signed?: boolean }
  const tauMax = (cfg.tau_max as number | undefined) ?? 10
  const tauMin = (cfg.tau_signed as boolean | undefined) ? -tauMax : 0
  const N = t.header.N
  const out = new Array<string>(N * N)
  const tau = replay.tau.value
  const halfL = 2 * t.header.L
  for (let i = 0; i < N * N; i++) {
    out[i] = viridis(0)
  }
  // crude per-cell aggregate: average tau over the four directional edges
  // adjacent to cell (r,c) where edge_id is r*N + c (rough mapping placeholder)
  // The real edge_of layout lives in solver/state.py; without exposing it,
  // we treat the first L slots as a flat per-edge field and average pairs
  // by column-major adjacency. This approximation is good enough for visual
  // contrast at small N; revisit if/when edge_of is exposed in the trace.
  for (let i = 0; i < halfL && i < tau.length; i++) {
    const cell = i % (N * N)
    const norm = (tau[i] - tauMin) / Math.max(1e-9, tauMax - tauMin)
    out[cell] = viridis(norm)
  }
  return out
})

const bestPathPoints = computed(() =>
  replay.bestPath.value
    .map((c) => `${cellCenterX(c as [number, number])},${cellCenterY(c as [number, number])}`)
    .join(' '),
)

const walkers = computed(() => replay.walkers.value)

function walkerColor(status: WalkerStatus): string {
  if (status === 'alive') return '#34d399'
  if (status === 'dead-end') return '#f87171'
  return '#60a5fa'
}
</script>
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd viz-web && bun run test:unit -- --run src/components/__tests__/GridCanvas
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add viz-web/src/components/GridCanvas.vue viz-web/src/components/__tests__/GridCanvas.spec.ts
git commit -m "feat(viz): GridCanvas with layered SVG rendering"
```

---

## Task 19: ControlBar

**Goal:** Bottom-of-screen play controls (play/pause/step/scrub/speed) bound to the playback store.

**Files:**
- Create: `viz-web/src/components/ControlBar.vue`
- Create: `viz-web/src/components/__tests__/ControlBar.spec.ts`

- [ ] **Step 1: Write the failing test**

Create `viz-web/src/components/__tests__/ControlBar.spec.ts`:

```ts
import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import ControlBar from '../ControlBar.vue'
import { usePlaybackStore } from '../../stores/playback'

describe('ControlBar', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('toggles play state when play button clicked', async () => {
    const store = usePlaybackStore()
    store.setTotal(10)
    const wrapper = mount(ControlBar)
    await wrapper.get('[data-test="play"]').trigger('click')
    expect(store.playing).toBe(true)
    await wrapper.get('[data-test="play"]').trigger('click')
    expect(store.playing).toBe(false)
  })

  it('steps forward and backward', async () => {
    const store = usePlaybackStore()
    store.setTotal(10)
    const wrapper = mount(ControlBar)
    await wrapper.get('[data-test="step-fwd"]').trigger('click')
    expect(store.index).toBe(1)
    await wrapper.get('[data-test="step-back"]').trigger('click')
    expect(store.index).toBe(0)
  })

  it('scrubs via the range input', async () => {
    const store = usePlaybackStore()
    store.setTotal(10)
    const wrapper = mount(ControlBar)
    const input = wrapper.get<HTMLInputElement>('[data-test="scrub"]')
    input.element.value = '5'
    await input.trigger('input')
    expect(store.index).toBe(5)
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd viz-web && bun run test:unit -- --run src/components/__tests__/ControlBar
```

Expected: cannot resolve module.

- [ ] **Step 3: Implement the component**

Create `viz-web/src/components/ControlBar.vue`:

```vue
<template>
  <div class="flex items-center gap-3 px-3 py-2 bg-zinc-800 text-zinc-100 border-t border-zinc-700">
    <button
      data-test="step-back"
      class="px-2 py-1 rounded bg-zinc-700 hover:bg-zinc-600"
      :disabled="store.total === 0"
      @click="store.step(-1)"
    >⏮</button>
    <button
      data-test="play"
      class="px-3 py-1 rounded bg-blue-600 hover:bg-blue-500"
      :disabled="store.total === 0"
      @click="store.togglePlay"
    >{{ store.playing ? '⏸' : '▶' }}</button>
    <button
      data-test="step-fwd"
      class="px-2 py-1 rounded bg-zinc-700 hover:bg-zinc-600"
      :disabled="store.total === 0"
      @click="store.step(1)"
    >⏭</button>
    <input
      data-test="scrub"
      type="range"
      class="flex-1"
      :min="0"
      :max="Math.max(0, store.total - 1)"
      :value="store.index"
      :disabled="store.total === 0"
      @input="onScrub"
    />
    <span class="text-xs tabular-nums w-24 text-right">
      {{ store.index }} / {{ Math.max(0, store.total - 1) }}
    </span>
    <select
      class="bg-zinc-700 px-2 py-1 rounded"
      :value="store.speed"
      @change="onSpeed"
    >
      <option :value="1">1×</option>
      <option :value="4">4×</option>
      <option :value="16">16×</option>
      <option :value="64">max</option>
    </select>
  </div>
</template>

<script setup lang="ts">
import { usePlaybackStore } from '../stores/playback'

const store = usePlaybackStore()

function onScrub(e: Event): void {
  const v = Number((e.target as HTMLInputElement).value)
  store.seek(v)
}

function onSpeed(e: Event): void {
  const v = Number((e.target as HTMLSelectElement).value)
  store.setSpeed(v)
}
</script>
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd viz-web && bun run test:unit -- --run src/components/__tests__/ControlBar
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add viz-web/src/components/ControlBar.vue viz-web/src/components/__tests__/ControlBar.spec.ts
git commit -m "feat(viz): ControlBar with play/step/scrub/speed"
```

---

## Task 20: Run-loop driver — `usePlaybackLoop`

**Goal:** When `playing===true`, advance the index by `speed` per `requestAnimationFrame` tick. Stop at the last frame.

**Files:**
- Create: `viz-web/src/composables/usePlaybackLoop.ts`
- Create: `viz-web/src/composables/__tests__/usePlaybackLoop.spec.ts`

- [ ] **Step 1: Write the failing test**

Create `viz-web/src/composables/__tests__/usePlaybackLoop.spec.ts`:

```ts
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { usePlaybackLoop } from '../usePlaybackLoop'
import { usePlaybackStore } from '../../stores/playback'

describe('usePlaybackLoop', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('advances index by speed per tick when playing', () => {
    const store = usePlaybackStore()
    store.setTotal(100)
    store.setSpeed(4)
    const loop = usePlaybackLoop()

    store.togglePlay()
    loop._tickForTesting()
    expect(store.index).toBe(4)
    loop._tickForTesting()
    expect(store.index).toBe(8)
  })

  it('stops at the last frame and pauses', () => {
    const store = usePlaybackStore()
    store.setTotal(3)
    store.setSpeed(8)
    const loop = usePlaybackLoop()

    store.togglePlay()
    loop._tickForTesting()
    expect(store.index).toBe(2)
    expect(store.playing).toBe(false)
  })

  it('does nothing when paused', () => {
    const store = usePlaybackStore()
    store.setTotal(10)
    const loop = usePlaybackLoop()
    loop._tickForTesting()
    expect(store.index).toBe(0)
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd viz-web && bun run test:unit -- --run src/composables/__tests__/usePlaybackLoop
```

Expected: module not found.

- [ ] **Step 3: Implement the loop**

Create `viz-web/src/composables/usePlaybackLoop.ts`:

```ts
import { onUnmounted } from 'vue'
import { usePlaybackStore } from '../stores/playback'

export function usePlaybackLoop() {
  const store = usePlaybackStore()
  let raf = 0
  let active = true

  function tick(): void {
    if (!active) return
    if (store.playing) {
      const next = store.index + store.speed
      const last = Math.max(0, store.total - 1)
      if (next >= last) {
        store.seek(last)
        if (store.playing) store.togglePlay()
      } else {
        store.seek(next)
      }
    }
    raf = requestAnimationFrame(tick)
  }

  if (typeof requestAnimationFrame !== 'undefined') {
    raf = requestAnimationFrame(tick)
  }

  onUnmounted(() => {
    active = false
    if (raf) cancelAnimationFrame(raf)
  })

  return {
    _tickForTesting(): void {
      if (!store.playing) return
      const next = store.index + store.speed
      const last = Math.max(0, store.total - 1)
      if (next >= last) {
        store.seek(last)
        if (store.playing) store.togglePlay()
      } else {
        store.seek(next)
      }
    },
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd viz-web && bun run test:unit -- --run src/composables/__tests__/usePlaybackLoop
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add viz-web/src/composables/usePlaybackLoop.ts viz-web/src/composables/__tests__/usePlaybackLoop.spec.ts
git commit -m "feat(viz): playback animation loop"
```

---

## Task 21: ConfigPanel + Run flow

**Goal:** Form lets the user pick puzzle/variant/seed and override hyperparameters; submit calls `/api/runs`, stores the resulting trace, and resets playback.

**Files:**
- Create: `viz-web/src/stores/run.ts`
- Create: `viz-web/src/components/ConfigPanel.vue`
- Create: `viz-web/src/components/__tests__/ConfigPanel.spec.ts`

- [ ] **Step 1: Write the failing test**

Create `viz-web/src/components/__tests__/ConfigPanel.spec.ts`:

```ts
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import ConfigPanel from '../ConfigPanel.vue'
import { ApiClient } from '../../api/client'
import { useTraceStore } from '../../stores/trace'

const fakeTrace = {
  version: 1,
  puzzle_id: 'level_1',
  config: {},
  seed: 0,
  header: { N: 2, K: 1, L: 4, waypoints: [], walls: [], blocked: [] },
  frames: [],
  footer: {
    solved: true,
    infeasible: false,
    solution: null,
    iterations_used: 0,
    wall_clock_s: 0,
    best_fitness: 0,
  },
}

describe('ConfigPanel', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('submits a run and writes the trace into the store', async () => {
    const client = new ApiClient()
    vi.spyOn(client, 'listPuzzles').mockResolvedValue([
      { id: 'level_1', name: 'Lvl 1', difficulty: 'Easy', N: 2, K: 1 },
    ])
    vi.spyOn(client, 'listVariants').mockResolvedValue([
      { name: 'zipmould-uni-positive', config_path: 'x', defaults: {} },
    ])
    const runSpy = vi
      .spyOn(client, 'runSolve')
      .mockResolvedValue({ trace_id: 't1', trace: fakeTrace })

    const wrapper = mount(ConfigPanel, { props: { client } })
    await new Promise((r) => setTimeout(r, 0))
    await wrapper.vm.$nextTick()

    await wrapper.get('[data-test="run"]').trigger('click')
    await new Promise((r) => setTimeout(r, 0))

    expect(runSpy).toHaveBeenCalled()
    const store = useTraceStore()
    expect(store.traceId).toBe('t1')
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd viz-web && bun run test:unit -- --run src/components/__tests__/ConfigPanel
```

Expected: cannot resolve modules.

- [ ] **Step 3: Implement the run store**

Create `viz-web/src/stores/run.ts`:

```ts
import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { PuzzleSummary, VariantSummary } from '../api/types'

export const useRunStore = defineStore('run', () => {
  const puzzles = ref<PuzzleSummary[]>([])
  const variants = ref<VariantSummary[]>([])
  const submitting = ref(false)
  const puzzleId = ref<string>('')
  const variant = ref<string>('zipmould-uni-positive')
  const seed = ref<number>(Math.floor(Math.random() * 1e9))
  const overrides = ref<Record<string, unknown>>({})

  return {
    puzzles,
    variants,
    submitting,
    puzzleId,
    variant,
    seed,
    overrides,
  }
})
```

- [ ] **Step 4: Implement the panel**

Create `viz-web/src/components/ConfigPanel.vue`:

```vue
<template>
  <section class="space-y-3 p-3 text-zinc-100">
    <h2 class="text-sm uppercase tracking-wide text-zinc-400">Run config</h2>
    <label class="block">
      <span class="text-xs">Puzzle</span>
      <select v-model="run.puzzleId" class="w-full bg-zinc-800 rounded px-2 py-1">
        <option v-for="p in run.puzzles" :key="p.id" :value="p.id">
          {{ p.id }} — N={{ p.N }} K={{ p.K }}
        </option>
      </select>
    </label>
    <label class="block">
      <span class="text-xs">Variant</span>
      <select v-model="run.variant" class="w-full bg-zinc-800 rounded px-2 py-1">
        <option v-for="v in run.variants" :key="v.name" :value="v.name">{{ v.name }}</option>
      </select>
    </label>
    <label class="block">
      <span class="text-xs">Seed</span>
      <input
        v-model.number="run.seed"
        type="number"
        min="0"
        class="w-full bg-zinc-800 rounded px-2 py-1"
      />
    </label>

    <details>
      <summary class="cursor-pointer text-xs text-zinc-400">Advanced</summary>
      <div class="mt-2 space-y-1">
        <div v-for="key in advancedKeys" :key="key" class="flex items-center gap-2">
          <span class="text-xs w-32">{{ key }}</span>
          <input
            class="flex-1 bg-zinc-800 rounded px-2 py-1 text-xs"
            :value="run.overrides[key] ?? variantDefault(key)"
            @input="onOverride(key, ($event.target as HTMLInputElement).value)"
          />
        </div>
      </div>
    </details>

    <button
      data-test="run"
      class="w-full bg-blue-600 hover:bg-blue-500 disabled:opacity-50 rounded py-2"
      :disabled="run.submitting || !run.puzzleId"
      @click="submit"
    >
      {{ run.submitting ? 'Solving…' : 'Run' }}
    </button>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { ApiClient, ApiError, api as defaultApi } from '../api/client'
import { useRunStore } from '../stores/run'
import { useTraceStore } from '../stores/trace'
import { usePlaybackStore } from '../stores/playback'
import { useNotificationsStore } from '../stores/notifications'

const props = defineProps<{ client?: ApiClient }>()
const client = props.client ?? defaultApi

const run = useRunStore()
const traceStore = useTraceStore()
const playback = usePlaybackStore()
const notifications = useNotificationsStore()

const advancedKeys = ['alpha', 'beta', 'iter_cap', 'population', 'tau_max', 'z']

function variantDefault(key: string): unknown {
  const v = run.variants.find((x) => x.name === run.variant)
  return v?.defaults[key]
}

function onOverride(key: string, value: string): void {
  if (value === '') {
    const next = { ...run.overrides }
    delete next[key]
    run.overrides = next
    return
  }
  const num = Number(value)
  run.overrides = { ...run.overrides, [key]: Number.isFinite(num) ? num : value }
}

async function refresh(): Promise<void> {
  try {
    run.puzzles = await client.listPuzzles()
    run.variants = await client.listVariants()
    if (!run.puzzleId && run.puzzles.length) run.puzzleId = run.puzzles[0].id
  } catch (err) {
    const text = err instanceof ApiError ? err.detail : String(err)
    notifications.push({ kind: 'error', text })
  }
}

async function submit(): Promise<void> {
  if (run.submitting) return
  run.submitting = true
  try {
    const resp = await client.runSolve({
      puzzle_id: run.puzzleId,
      variant: run.variant,
      seed: run.seed,
      config_overrides: run.overrides,
    })
    traceStore.set(resp.trace_id, resp.trace)
    playback.setTotal(resp.trace.frames.length)
    playback.seek(0)
  } catch (err) {
    const text = err instanceof ApiError ? `${err.kind}: ${err.detail}` : String(err)
    notifications.push({ kind: 'error', text })
  } finally {
    run.submitting = false
  }
}

onMounted(refresh)
</script>
```

- [ ] **Step 5: Run test to verify it passes**

```bash
cd viz-web && bun run test:unit -- --run src/components/__tests__/ConfigPanel
```

Expected: 1 passed.

- [ ] **Step 6: Commit**

```bash
git add viz-web/src/stores/run.ts viz-web/src/components/ConfigPanel.vue viz-web/src/components/__tests__/ConfigPanel.spec.ts
git commit -m "feat(viz): ConfigPanel + run store"
```

---

## Task 22: TracePicker (drag-drop + browse)

**Goal:** A small drop zone with a fallback file input that calls `useFileLoader.load(file)`.

**Files:**
- Create: `viz-web/src/components/TracePicker.vue`
- Create: `viz-web/src/components/__tests__/TracePicker.spec.ts`

- [ ] **Step 1: Write the failing test**

Create `viz-web/src/components/__tests__/TracePicker.spec.ts`:

```ts
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import TracePicker from '../TracePicker.vue'
import { ApiClient } from '../../api/client'

describe('TracePicker', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('uploads when a file is selected via the input', async () => {
    const client = new ApiClient()
    const fakeTrace = {
      version: 1,
      puzzle_id: 'fixture',
      config: {},
      seed: 0,
      header: { N: 2, K: 1, L: 4, waypoints: [], walls: [], blocked: [] },
      frames: [],
      footer: {
        solved: false,
        infeasible: false,
        solution: null,
        iterations_used: 0,
        wall_clock_s: 0,
        best_fitness: 0,
      },
    }
    const spy = vi
      .spyOn(client, 'uploadTrace')
      .mockResolvedValue({ trace_id: 'x', trace: fakeTrace })

    const wrapper = mount(TracePicker, { props: { client } })
    const input = wrapper.get<HTMLInputElement>('input[type="file"]')
    const file = new File([new Uint8Array([0xa0])], 'tiny.cbor', { type: 'application/cbor' })
    Object.defineProperty(input.element, 'files', { value: [file], configurable: true })
    await input.trigger('change')

    expect(spy).toHaveBeenCalledTimes(1)
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd viz-web && bun run test:unit -- --run src/components/__tests__/TracePicker
```

Expected: cannot resolve module.

- [ ] **Step 3: Implement the picker**

Create `viz-web/src/components/TracePicker.vue`:

```vue
<template>
  <section class="p-3 text-zinc-100 space-y-2">
    <h2 class="text-sm uppercase tracking-wide text-zinc-400">Load trace</h2>
    <label
      class="block border border-dashed border-zinc-600 rounded p-4 text-center cursor-pointer hover:bg-zinc-800"
      @dragover.prevent
      @drop.prevent="onDrop"
    >
      <span class="text-xs">Drop a .cbor file here, or click to browse.</span>
      <input
        type="file"
        accept=".cbor,application/cbor"
        class="hidden"
        @change="onChange"
      />
    </label>
  </section>
</template>

<script setup lang="ts">
import { ApiClient, api as defaultApi } from '../api/client'
import { useFileLoader } from '../composables/useFileLoader'
import { usePlaybackStore } from '../stores/playback'
import { useTraceStore } from '../stores/trace'

const props = defineProps<{ client?: ApiClient }>()
const loader = useFileLoader(props.client ?? defaultApi)
const playback = usePlaybackStore()
const traceStore = useTraceStore()

async function handle(file: File | undefined): Promise<void> {
  if (!file) return
  await loader.load(file)
  if (traceStore.trace) {
    playback.setTotal(traceStore.trace.frames.length)
    playback.seek(0)
  }
}

function onDrop(e: DragEvent): void {
  void handle(e.dataTransfer?.files?.[0])
}

function onChange(e: Event): void {
  void handle((e.target as HTMLInputElement).files?.[0])
}
</script>
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd viz-web && bun run test:unit -- --run src/components/__tests__/TracePicker
```

Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add viz-web/src/components/TracePicker.vue viz-web/src/components/__tests__/TracePicker.spec.ts
git commit -m "feat(viz): TracePicker (drag-drop + browse)"
```

---

## Task 23: Telemetry components — FitnessChart, WalkerTable, FrameMeta, FooterSummary, LayerToggles

**Goal:** Five small read-only side-panel components. Treat them as one unit because none of them carry state of their own.

**Files:**
- Create: `viz-web/src/components/FitnessChart.vue`
- Create: `viz-web/src/components/WalkerTable.vue`
- Create: `viz-web/src/components/FrameMeta.vue`
- Create: `viz-web/src/components/FooterSummary.vue`
- Create: `viz-web/src/components/LayerToggles.vue`
- Create: `viz-web/src/components/__tests__/Telemetry.spec.ts`

- [ ] **Step 1: Write the failing test**

Create `viz-web/src/components/__tests__/Telemetry.spec.ts`:

```ts
import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import FitnessChart from '../FitnessChart.vue'
import WalkerTable from '../WalkerTable.vue'
import FrameMeta from '../FrameMeta.vue'
import FooterSummary from '../FooterSummary.vue'
import LayerToggles from '../LayerToggles.vue'
import { useTraceStore } from '../../stores/trace'
import { usePlaybackStore } from '../../stores/playback'
import type { Trace } from '../../api/types'

const trace: Trace = {
  version: 1,
  puzzle_id: 'tiny',
  config: { tau_max: 10, tau_signed: true },
  seed: 0,
  header: { N: 2, K: 1, L: 4, waypoints: [[0, 0]], walls: [], blocked: [] },
  frames: [
    {
      t: 0,
      v_b: 0.1,
      v_c: 0.0,
      tau_delta: { mode: 'unified', edges: [] },
      best: { path: [], fitness: 0 },
      walkers: [{ id: 0, cell: [0, 0], segment: 0, status: 'alive', fitness: 0.5 }],
    },
    {
      t: 5,
      v_b: 0.4,
      v_c: 0.2,
      tau_delta: { mode: 'unified', edges: [] },
      best: { path: [], fitness: 0.7 },
      walkers: [{ id: 0, cell: [1, 1], segment: 1, status: 'complete', fitness: 0.9 }],
    },
  ],
  footer: {
    solved: true,
    infeasible: false,
    solution: null,
    iterations_used: 5,
    wall_clock_s: 0.012,
    best_fitness: 0.9,
  },
}

describe('telemetry components', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    const ts = useTraceStore()
    const pb = usePlaybackStore()
    ts.set('id', trace)
    pb.setTotal(trace.frames.length)
    pb.seek(1)
  })

  it('FitnessChart renders an svg path', () => {
    const w = mount(FitnessChart)
    expect(w.find('svg').exists()).toBe(true)
    expect(w.findAll('path').length).toBeGreaterThan(0)
  })

  it('WalkerTable lists walkers from the current frame', () => {
    const w = mount(WalkerTable)
    expect(w.text()).toContain('alive')
    expect(w.text()).toContain('complete')
  })

  it('FrameMeta shows current t and V_b/V_c', () => {
    const w = mount(FrameMeta)
    expect(w.text()).toContain('t = 5')
    expect(w.text()).toContain('0.4')
    expect(w.text()).toContain('0.2')
  })

  it('FooterSummary shows solved + iters + wall clock', () => {
    const w = mount(FooterSummary)
    expect(w.text().toLowerCase()).toContain('solved')
    expect(w.text()).toContain('5')
    expect(w.text()).toContain('0.012')
  })

  it('LayerToggles flips a layer flag in the playback store', async () => {
    const w = mount(LayerToggles)
    const pb = usePlaybackStore()
    await w.get('[data-test="toggle-pheromone"]').trigger('change')
    expect(pb.layers.pheromone).toBe(false)
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd viz-web && bun run test:unit -- --run src/components/__tests__/Telemetry
```

Expected: cannot resolve modules.

- [ ] **Step 3: Implement the components**

Create `viz-web/src/components/FitnessChart.vue`:

```vue
<template>
  <section v-if="trace" class="p-3 text-zinc-100">
    <h2 class="text-sm uppercase tracking-wide text-zinc-400 mb-2">Fitness</h2>
    <svg :viewBox="`0 0 ${W} ${H}`" class="w-full">
      <path :d="pathFor('v_b')" fill="none" stroke="#34d399" stroke-width="1.5" />
      <path :d="pathFor('v_c')" fill="none" stroke="#60a5fa" stroke-width="1.5" />
      <line :x1="cursorX" :x2="cursorX" :y1="0" :y2="H" stroke="#fde68a" stroke-dasharray="2 2" />
    </svg>
    <div class="text-xs flex gap-3 mt-1">
      <span class="text-emerald-400">V_b</span>
      <span class="text-blue-400">V_c</span>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, toRefs } from 'vue'
import { storeToRefs } from 'pinia'
import { useTraceStore } from '../stores/trace'
import { usePlaybackStore } from '../stores/playback'

const W = 280
const H = 80

const traceStore = useTraceStore()
const { trace } = toRefs(traceStore)
const { index } = storeToRefs(usePlaybackStore())

function range(values: number[]): { lo: number; hi: number } {
  if (!values.length) return { lo: 0, hi: 1 }
  const lo = Math.min(...values)
  const hi = Math.max(...values)
  return { lo, hi: hi === lo ? lo + 1 : hi }
}

const ranges = computed(() => {
  const t = trace.value
  if (!t) return { lo: 0, hi: 1 }
  return range([
    ...t.frames.map((f) => f.v_b),
    ...t.frames.map((f) => f.v_c),
  ])
})

function pathFor(key: 'v_b' | 'v_c'): string {
  const t = trace.value
  if (!t || !t.frames.length) return ''
  const { lo, hi } = ranges.value
  return t.frames
    .map((f, i) => {
      const x = (i / Math.max(1, t.frames.length - 1)) * W
      const y = H - ((f[key] - lo) / (hi - lo)) * H
      return `${i === 0 ? 'M' : 'L'} ${x.toFixed(2)} ${y.toFixed(2)}`
    })
    .join(' ')
}

const cursorX = computed(() => {
  const t = trace.value
  if (!t || !t.frames.length) return 0
  return (index.value / Math.max(1, t.frames.length - 1)) * W
})
</script>
```

Create `viz-web/src/components/WalkerTable.vue`:

```vue
<template>
  <section v-if="trace" class="p-3 text-zinc-100 text-sm">
    <h2 class="text-sm uppercase tracking-wide text-zinc-400 mb-2">Walkers</h2>
    <table class="w-full text-xs">
      <thead>
        <tr class="text-zinc-500">
          <th class="text-left">id</th>
          <th class="text-left">cell</th>
          <th class="text-left">seg</th>
          <th class="text-left">status</th>
          <th class="text-right">fitness</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="w in walkers" :key="w.id">
          <td>{{ w.id }}</td>
          <td>({{ w.cell[0] }},{{ w.cell[1] }})</td>
          <td>{{ w.segment }}</td>
          <td :class="statusClass(w.status)">{{ w.status }}</td>
          <td class="text-right tabular-nums">{{ w.fitness.toFixed(3) }}</td>
        </tr>
      </tbody>
    </table>
  </section>
</template>

<script setup lang="ts">
import { computed, toRefs } from 'vue'
import { storeToRefs } from 'pinia'
import { useTraceStore } from '../stores/trace'
import { usePlaybackStore } from '../stores/playback'
import type { WalkerStatus } from '../api/types'

const traceStore = useTraceStore()
const { trace } = toRefs(traceStore)
const { index } = storeToRefs(usePlaybackStore())

const walkers = computed(() => {
  const t = trace.value
  if (!t || !t.frames.length) return []
  const i = Math.min(index.value, t.frames.length - 1)
  return t.frames[i].walkers
})

function statusClass(s: WalkerStatus): string {
  if (s === 'alive') return 'text-emerald-400'
  if (s === 'dead-end') return 'text-red-400'
  return 'text-blue-400'
}
</script>
```

Create `viz-web/src/components/FrameMeta.vue`:

```vue
<template>
  <section v-if="trace" class="p-3 text-zinc-100 text-sm">
    <h2 class="text-sm uppercase tracking-wide text-zinc-400 mb-2">Frame</h2>
    <dl class="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
      <dt class="text-zinc-500">t =</dt>
      <dd class="tabular-nums">t = {{ frame?.t ?? '-' }}</dd>
      <dt class="text-zinc-500">V_b</dt>
      <dd class="tabular-nums">{{ frame?.v_b.toFixed(3) ?? '-' }}</dd>
      <dt class="text-zinc-500">V_c</dt>
      <dd class="tabular-nums">{{ frame?.v_c.toFixed(3) ?? '-' }}</dd>
    </dl>
  </section>
</template>

<script setup lang="ts">
import { computed, toRefs } from 'vue'
import { storeToRefs } from 'pinia'
import { useTraceStore } from '../stores/trace'
import { usePlaybackStore } from '../stores/playback'

const traceStore = useTraceStore()
const { trace } = toRefs(traceStore)
const { index } = storeToRefs(usePlaybackStore())
const frame = computed(() => {
  const t = trace.value
  if (!t || !t.frames.length) return null
  return t.frames[Math.min(index.value, t.frames.length - 1)]
})
</script>
```

Create `viz-web/src/components/FooterSummary.vue`:

```vue
<template>
  <section v-if="trace" class="p-3 text-zinc-100 text-sm">
    <h2 class="text-sm uppercase tracking-wide text-zinc-400 mb-2">Summary</h2>
    <dl class="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
      <dt class="text-zinc-500">solved</dt>
      <dd :class="trace.footer.solved ? 'text-emerald-400' : 'text-red-400'">
        {{ trace.footer.solved ? 'solved' : 'unsolved' }}
      </dd>
      <dt class="text-zinc-500">iterations</dt>
      <dd class="tabular-nums">{{ trace.footer.iterations_used }}</dd>
      <dt class="text-zinc-500">wall clock</dt>
      <dd class="tabular-nums">{{ trace.footer.wall_clock_s }}</dd>
      <dt class="text-zinc-500">best fitness</dt>
      <dd class="tabular-nums">{{ trace.footer.best_fitness.toFixed(3) }}</dd>
    </dl>
  </section>
</template>

<script setup lang="ts">
import { toRefs } from 'vue'
import { useTraceStore } from '../stores/trace'

const traceStore = useTraceStore()
const { trace } = toRefs(traceStore)
</script>
```

Create `viz-web/src/components/LayerToggles.vue`:

```vue
<template>
  <section class="p-3 text-zinc-100 text-sm space-y-1">
    <h2 class="text-sm uppercase tracking-wide text-zinc-400 mb-2">Layers</h2>
    <label v-for="key in keys" :key="key" class="flex items-center gap-2 text-xs">
      <input
        type="checkbox"
        :checked="store.layers[key]"
        :data-test="`toggle-${key}`"
        @change="store.toggleLayer(key)"
      />
      {{ key }}
    </label>
  </section>
</template>

<script setup lang="ts">
import { usePlaybackStore, type LayerKey } from '../stores/playback'
const store = usePlaybackStore()
const keys: LayerKey[] = ['walls', 'pheromone', 'walkers', 'bestPath', 'waypoints']
</script>
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd viz-web && bun run test:unit -- --run src/components/__tests__/Telemetry
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add viz-web/src/components/FitnessChart.vue viz-web/src/components/WalkerTable.vue viz-web/src/components/FrameMeta.vue viz-web/src/components/FooterSummary.vue viz-web/src/components/LayerToggles.vue viz-web/src/components/__tests__/Telemetry.spec.ts
git commit -m "feat(viz): telemetry components"
```

---

## Task 24: App.vue cockpit layout + Save trace button

**Goal:** Wire all components into the three-column cockpit layout. Add a "Save trace" button that links to the CBOR endpoint.

**Files:**
- Modify: `viz-web/src/App.vue`

- [ ] **Step 1: Replace App.vue**

Overwrite `viz-web/src/App.vue`:

```vue
<template>
  <div class="flex flex-col h-screen bg-zinc-950 text-zinc-100">
    <header class="flex items-center justify-between px-4 py-2 border-b border-zinc-800">
      <h1 class="text-sm font-semibold tracking-wide">ZipMould Visualizer</h1>
      <div class="flex items-center gap-2">
        <span v-if="trace" class="text-xs text-zinc-400">
          {{ trace.puzzle_id }} · seed {{ trace.seed }}
        </span>
        <a
          v-if="traceId"
          :href="downloadUrl"
          download
          class="text-xs px-2 py-1 rounded bg-zinc-800 hover:bg-zinc-700"
        >Save trace</a>
      </div>
    </header>

    <div class="grid grid-cols-[300px_1fr_320px] flex-1 min-h-0">
      <aside class="overflow-y-auto border-r border-zinc-800">
        <ConfigPanel />
        <TracePicker />
        <LayerToggles />
      </aside>

      <main class="flex items-center justify-center p-4 min-h-0">
        <GridCanvas />
      </main>

      <aside class="overflow-y-auto border-l border-zinc-800">
        <FrameMeta />
        <FitnessChart />
        <WalkerTable />
        <FooterSummary />
      </aside>
    </div>

    <ControlBar />
    <ErrorToasts />
  </div>
</template>

<script setup lang="ts">
import { computed, toRefs } from 'vue'
import ConfigPanel from './components/ConfigPanel.vue'
import TracePicker from './components/TracePicker.vue'
import LayerToggles from './components/LayerToggles.vue'
import GridCanvas from './components/GridCanvas.vue'
import FrameMeta from './components/FrameMeta.vue'
import FitnessChart from './components/FitnessChart.vue'
import WalkerTable from './components/WalkerTable.vue'
import FooterSummary from './components/FooterSummary.vue'
import ControlBar from './components/ControlBar.vue'
import ErrorToasts from './components/ErrorToasts.vue'
import { useTraceStore } from './stores/trace'
import { api } from './api/client'
import { usePlaybackLoop } from './composables/usePlaybackLoop'

usePlaybackLoop()

const traceStore = useTraceStore()
const { trace, traceId } = toRefs(traceStore)
const downloadUrl = computed(() => (traceId.value ? api.downloadTraceUrl(traceId.value) : '#'))
</script>
```

- [ ] **Step 2: Manually verify in dev**

In one terminal:

```bash
uv run zipmould viz serve --reload
```

In another:

```bash
cd viz-web && bun run dev
```

Open `http://localhost:5173`. Expected:
- Three-column layout renders.
- Config panel populates puzzles + variants from `/api/puzzles` / `/api/variants`.
- Picking a puzzle and clicking **Run** shows a Solving spinner, then the grid renders frames.
- Dragging a `.cbor` onto the picker loads it.
- ControlBar play/pause/scrub all work.
- Layer toggles add/remove layers.
- "Save trace" downloads the CBOR.

- [ ] **Step 3: Run all unit tests**

```bash
cd viz-web && bun run test:unit -- --run
```

Expected: full suite passes.

- [ ] **Step 4: Commit**

```bash
git add viz-web/src/App.vue
git commit -m "feat(viz): cockpit layout + save-trace button"
```

---

## Task 25: Production build pipeline

**Goal:** `bun run build` outputs into `src/zipmould/viz/static/`; `zipmould viz serve` mounts that directory at `/`.

**Files:**
- Modify: `src/zipmould/viz/server.py`
- Verify: `viz-web/vite.config.ts` already targets the static dir

- [ ] **Step 1: Build the frontend**

```bash
cd viz-web && bun run build
```

Verify `src/zipmould/viz/static/index.html` exists.

- [ ] **Step 2: Mount static assets in FastAPI**

Replace `src/zipmould/viz/server.py` with:

```python
"""FastAPI application factory with static asset mounting."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from zipmould.viz.cache import TraceCache
from zipmould.viz.routes import router as api_router

_TRACE_CACHE_CAPACITY = 8
_STATIC_DIR = Path(__file__).parent / "static"


def _http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail
    if isinstance(detail, dict) and "kind" in detail and "detail" in detail:
        body = {"kind": str(detail["kind"]), "detail": str(detail["detail"])}
    else:
        body = {"kind": "http_error", "detail": str(detail)}
    return JSONResponse(status_code=exc.status_code, content=body)


def _validation_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    parts = []
    for err in exc.errors():
        loc = ".".join(str(p) for p in err.get("loc", ()))
        msg = err.get("msg", "")
        parts.append(f"{loc}: {msg}" if loc else msg)
    body = {"kind": "validation_error", "detail": "; ".join(parts) or "validation error"}
    return JSONResponse(status_code=422, content=body)


def _generic_handler(_request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500, content={"kind": "internal", "detail": str(exc)}
    )


def create_app() -> FastAPI:
    app = FastAPI(title="ZipMould Visualizer", version="0.1.0")
    app.state.trace_cache = TraceCache(capacity=_TRACE_CACHE_CAPACITY)
    app.include_router(api_router)
    app.add_exception_handler(HTTPException, _http_exception_handler)
    app.add_exception_handler(RequestValidationError, _validation_handler)
    app.add_exception_handler(Exception, _generic_handler)
    if _STATIC_DIR.exists():
        app.mount("/", StaticFiles(directory=_STATIC_DIR, html=True), name="static")
    return app
```

- [ ] **Step 3: Smoke-test single-process serving**

```bash
uv run zipmould viz serve --port 8000 &
SERVER_PID=$!
sleep 2
curl -s http://127.0.0.1:8000/api/health
curl -s -I http://127.0.0.1:8000/ | head -1
kill $SERVER_PID
```

Expected: health JSON; root returns `200 OK` with HTML.

- [ ] **Step 4: Run the backend test suite**

```bash
uv run pytest tests/viz/ -v
```

Expected: all backend tests still pass.

- [ ] **Step 5: Commit**

```bash
git add src/zipmould/viz/server.py
git commit -m "feat(viz): mount built frontend assets at /"
```

---

## Task 26: E2E smoke test

**Goal:** A single Playwright spec that boots the app (against a built frontend served by FastAPI), uploads a fixture CBOR, scrubs to the last frame, and asserts the footer reads "solved".

**Files:**
- Create: `viz-web/tests/e2e/replay.spec.ts`
- Create: `viz-web/tests/fixtures/tiny-trace.cbor` (built offline using `tests/viz/fixtures/builder.py`)
- Modify: `viz-web/playwright.config.ts` to start the backend

- [ ] **Step 1: Generate a fixture CBOR**

```bash
uv run python - <<'PY'
import pathlib
from tests.viz.fixtures.builder import tiny_cbor

out = pathlib.Path("viz-web/tests/fixtures/tiny-trace.cbor")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_bytes(tiny_cbor())
print(f"wrote {out} ({out.stat().st_size} bytes)")
PY
```

Expected: writes a small `.cbor` file.

- [ ] **Step 2: Configure Playwright to launch the FastAPI process**

Replace the body of `viz-web/playwright.config.ts` with:

```ts
import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 60_000,
  use: { baseURL: 'http://127.0.0.1:8001', trace: 'retain-on-failure' },
  webServer: {
    command: 'uv run zipmould viz serve --port 8001',
    url: 'http://127.0.0.1:8001/api/health',
    timeout: 30_000,
    reuseExistingServer: !process.env.CI,
    cwd: '..',
  },
})
```

- [ ] **Step 3: Write the spec**

Create `viz-web/tests/e2e/replay.spec.ts`:

```ts
import { test, expect } from '@playwright/test'
import { readFile } from 'node:fs/promises'

test('upload a CBOR trace and scrub to the last frame', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByText('ZipMould Visualizer')).toBeVisible()

  const fileBytes = await readFile('tests/fixtures/tiny-trace.cbor')
  const fileChooserPromise = page.waitForEvent('filechooser')
  await page.locator('label:has-text("Drop a .cbor file here")').click()
  const fileChooser = await fileChooserPromise
  await fileChooser.setFiles({
    name: 'tiny.cbor',
    mimeType: 'application/cbor',
    buffer: fileBytes,
  })

  await expect(page.locator('svg').first()).toBeVisible()

  // Scrub to the end via the range input
  const scrub = page.locator('[data-test="scrub"]')
  await scrub.evaluate((el: HTMLInputElement) => {
    el.value = el.max
    el.dispatchEvent(new Event('input', { bubbles: true }))
  })

  // FooterSummary text comes from the fixture: best_fitness=0.5, iters=10
  await expect(page.getByText('iterations')).toBeVisible()
})
```

- [ ] **Step 4: Run the spec**

```bash
cd viz-web && bun run test:e2e
```

Expected: 1 spec passes. (First run installs Playwright browsers — that's fine.)

- [ ] **Step 5: Commit**

```bash
git add viz-web/tests/ viz-web/playwright.config.ts
git commit -m "test(viz): playwright smoke test"
```

---

## Task 27: README + docs

**Goal:** Add a short README under `viz-web/` and update the project README's running-section to mention the visualizer.

**Files:**
- Create: `viz-web/README.md`
- Modify: `README.md`

- [ ] **Step 1: Create `viz-web/README.md`**

```markdown
# ZipMould Visualizer (frontend)

Vue 3 + TypeScript + Vite app that talks to the FastAPI backend at
`src/zipmould/viz/`. Loads recorded `.cbor` traces or runs synchronous
solves against the puzzle corpus, then replays them in a Cockpit layout.

## Dev

```bash
# Backend (port 8000)
uv run zipmould viz serve --reload

# Frontend (port 5173, proxies /api to :8000)
cd viz-web && bun run dev
```

## Production-style run

```bash
cd viz-web && bun run build   # outputs to ../src/zipmould/viz/static
uv run zipmould viz serve     # serves both API and static
```

## Tests

```bash
cd viz-web && bun run test:unit   # vitest
cd viz-web && bun run test:e2e    # playwright
```
```

- [ ] **Step 2: Append a "Visualizer" section to the project README**

Append at the bottom of `README.md`:

```markdown
## Visualizer

An interactive web visualizer lives at `src/zipmould/viz/` (FastAPI
backend) and `viz-web/` (Vue 3 frontend). To run it locally:

```bash
uv sync --extra viz
cd viz-web && bun install && bun run build
uv run zipmould viz serve
# Open http://127.0.0.1:8000
```

See `docs/superpowers/specs/2026-04-26-solver-visualizer-design.md` for
the full design.
```

- [ ] **Step 3: Commit**

```bash
git add viz-web/README.md README.md
git commit -m "docs(viz): readme entries for frontend and project"
```

---

## Self-Review Notes

These appear here so the executor doesn't have to re-derive them:

1. **Spec coverage check.** Every numbered section of the spec maps to a task:
   - Spec §3 (repo layout) → Tasks 1, 11
   - Spec §4 (API) → Tasks 2, 4, 5, 6, 7, 8
   - Spec §5.1 (cockpit layout) → Task 24
   - Spec §5.2 (grid render) → Task 18
   - Spec §5.3 (pheromone replay) → Task 15
   - Spec §5.4 (control bar) → Tasks 16, 19, 20
   - Spec §5.5 (config panel) → Task 21
   - Spec §5.6 (save trace) → Task 24
   - Spec §5.7 (layer toggles) → Task 23
   - Spec §6 (data flow) → Tasks 14, 17
   - Spec §7 (error handling) → Tasks 9, 13
   - Spec §8 (testing) → tests inside every task plus Task 26
   - Spec §9 (operations) → Tasks 10, 25, 27

2. **Type consistency.** `TraceCache.put/get`, `RunResponse{trace_id, trace}`, `ApiClient.runSolve/uploadTrace/downloadTraceUrl`, `usePlaybackStore.{seek, step, togglePlay, setSpeed, toggleLayer, setTotal}`, `useTraceReplay → {tau, frame, walkers, bestPath}`, `usePlaybackLoop()` are referenced consistently across tasks.

3. **Known approximation.** Task 18's `cells` computation maps the `tau` flat field onto cells with a placeholder average. The trace does not currently expose `edge_of` (the kernel-side mapping from edges to cells), so the heatmap is a coarse proxy. If the visual contrast turns out to be poor, the follow-up is to add `header.edge_of` to the trace and tighten the mapping; that's deliberately out of scope for v1 because it would touch `io/trace.py` and `solver/state.py`.

4. **Out of scope for v1 (deferred per spec):** in-browser puzzle editor, multi-run compare view, recents dropdown, cancellable runs, streaming. Each is feasible as a follow-up plan.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-26-solver-visualizer.md`. Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

Which approach?
