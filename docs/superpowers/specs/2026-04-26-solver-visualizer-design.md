# Solver Visualizer — Design Spec

**Date:** 2026-04-26
**Status:** Draft
**Author:** Gabriel Mitelman Tkacz (with Claude)

## 1. Purpose

Provide a single-user, locally hosted web app that lets a researcher inspect
ZipMould solver runs frame-by-frame. Two modes:

1. **Replay** — load a previously recorded `.cbor` trace from disk and scrub
   through it.
2. **Run live** — pick a puzzle from the corpus, choose a variant + seed +
   hyperparameter overrides, kick off a synchronous solve, then replay the
   resulting trace.

The audience is the author (research/debug, paper figure capture). It is not
deployed publicly and is not multi-user.

## 2. Non-Goals

- Multi-user hosting, authentication, or remote access.
- In-browser solving (no JS/WASM port of the kernel).
- Live frame streaming over WebSocket. Generate-then-replay is sufficient
  because Stage-1 runs typically complete in well under a second; if a future
  workload makes the wait painful, streaming can be added behind the same
  `/api/runs` contract.
- A user-drawn puzzle editor.
- Multi-run side-by-side comparison view.
- Auto-discovered "recent runs" dropdown (file picker is enough for v1).

## 3. Architecture

**Stack:** Vue 3 + TypeScript + Vite frontend (managed with `bun`); FastAPI +
uvicorn backend (managed with `uv`). One process serves both the API and the
built static assets in production; in development, `vite dev` proxies API
calls to FastAPI.

**Repository layout (additions only):**

```
src/zipmould/viz/
    __init__.py
    server.py                      # FastAPI app, mounts static, exposes /api
    routes.py                      # Endpoint handlers
    schemas.py                     # Pydantic request/response models
    runner.py                      # Wraps zipmould.solver.api.solve → JSON Trace
    trace_codec.py                 # CBOR ↔ JSON helpers (reuses io.trace dict shape)
    static/                        # Vite build output (gitignored)

viz-web/
    package.json                   # bun-managed
    bun.lockb
    vite.config.ts
    tsconfig.json
    index.html
    src/
        main.ts
        App.vue
        api/
            client.ts              # typed fetch wrapper around /api/*
            types.ts               # mirrors backend schemas
        stores/                    # Pinia
            playback.ts            # frame index, speed, play/pause
            trace.ts               # current Trace + accumulated pheromone field
            run.ts                 # live-run form state + submission status
            notifications.ts       # error/info toasts
        composables/
            useTraceReplay.ts      # frame indexer + checkpointed pheromone replay
            useFileLoader.ts       # drag-drop / browse for .cbor
        components/
            GridCanvas.vue
            PheromoneLayer.vue
            WalkerLayer.vue
            BestPathLayer.vue
            WaypointLayer.vue
            WallsLayer.vue
            ControlBar.vue
            ConfigPanel.vue
            TracePicker.vue
            FitnessChart.vue
            WalkerTable.vue
            FrameMeta.vue
            FooterSummary.vue
            LayerToggles.vue
            ErrorToasts.vue
        styles/                    # Tailwind v4
```

**Why this split.** The backend lives inside `src/zipmould/` so it imports
solver internals directly without a sys-path dance. The frontend is a sibling
package because mixing TypeScript source under `src/zipmould/` would confuse
both `ruff`/`pyright` and tooling that expects `src/` to be Python-only.

## 4. Backend API

All paths are under `/api`. Errors return JSON `{detail: str, kind: str}` with
appropriate HTTP status. Successful responses are JSON unless noted.

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/health` | Liveness probe. Returns `{status: "ok", version: ...}`. |
| `GET` | `/api/puzzles` | Lists puzzles in the corpus. Returns `[{id, N, K}, ...]`. |
| `GET` | `/api/variants` | Lists tunable solver conditions and their default config files. |
| `POST` | `/api/runs` | Synchronous solve. Body: `RunRequest`. Returns `TraceJSON`. |
| `POST` | `/api/traces/upload` | Multipart upload of a `.cbor`. Returns `TraceJSON`. |
| `GET` | `/api/traces/{id}.cbor` | Download last-run CBOR for "Save trace". |

### 4.1 `RunRequest`

```json
{
  "puzzle_id": "level_217",
  "variant": "zipmould-uni-positive",
  "seed": 42,
  "config_overrides": { "alpha": 1.2, "beta": 0.8 }
}
```

`variant` selects a base TOML config from `configs/ablations/`.
`config_overrides` is a flat dict applied on top via Pydantic
`SolverConfig.model_validate({...})`. Unknown keys raise 422.

### 4.2 `TraceJSON`

The Trace dict shape already produced by `zipmould.io.trace._trace_to_dict`
(header, frames, footer, config, seed, puzzle_id, version). The runner
also returns a generated `trace_id: str` (uuid4) so the client can request
the original CBOR back via `/api/traces/{id}.cbor`. The id and CBOR bytes
are held in an in-memory LRU cache (size 8) and dropped on server restart.

### 4.3 Data sources

- Puzzle corpus: `zipmould.io.puzzles.load_corpus()` → `dict[str, Puzzle]`.
  Cached at startup.
- Variant configs: read TOMLs from `configs/ablations/` once at startup.

## 5. Frontend

### 5.1 Layout (Cockpit)

```
+-----------------------------------------------------------+
|  ZipMould Visualizer                  [trace name / id]   |
+-----------------------------------------------------------+
|  ConfigPanel        |                |  FrameMeta         |
|  (puzzle, variant,  |                |  (t, V_b, V_c)     |
|   seed, advanced)   |                +--------------------+
|  [ Run ]            |   GridCanvas   |  FitnessChart      |
|                     |                |                    |
|  TracePicker        |                +--------------------+
|  (drag-drop / open) |                |  WalkerTable       |
|                     |                |                    |
|  LayerToggles       |                +--------------------+
|                     |                |  FooterSummary     |
+---------------------+----------------+--------------------+
|  ControlBar  [<<] [⏯] [>>]  [scrub --------●--------]  1× |
+-----------------------------------------------------------+
```

Three columns: 25% / 45% / 30%. ControlBar is full-width across the bottom.

### 5.2 Grid render

SVG. The corpus tops out at small N (current max ≤ 8), so SVG is fast and
gives free zoom, pan, and snapshot. Layers as `<g>` groups with toggle
bindings:

- **Walls** — `<line>` per walled edge, drawn first so cells overlay them
  cleanly on top.
- **Pheromone** — one `<rect>` per cell with fill driven by the average
  intensity of the cell's incident edges (cell-mean color is more legible than
  per-edge stripes at small N). Color scale: viridis from `tau_clip_min` to
  `tau_max`.
- **Best path** — single `<polyline>` from `frame.best.path`.
- **Walkers** — `<circle>` per walker, color by status
  (`alive` / `dead-end` / `complete`).
- **Waypoints** — numbered `<text>` overlays.

### 5.3 Pheromone replay (the load-bearing piece)

`tau_delta` is sparse per-frame. To render frame `t`, we need the full field
`tau[t] = tau[0] + Σ_{i≤t} apply(frame[i].tau_delta)`. Naïve forward
accumulation makes scrubbing O(N_frames) per seek.

`useTraceReplay.ts` solves this with periodic checkpoints:

- On trace load, walk all frames once forward, snapshotting `tau` into a
  `Float32Array` every `CHECKPOINT_INTERVAL` frames (default 64). Store
  checkpoints in an array of length `ceil(N_frames / 64)`.
- On seek to `t`: find the nearest preceding checkpoint, copy it into the
  working buffer, then apply deltas from that checkpoint forward to `t`.
- Forward play (`t -> t+1`) just applies one frame's `tau_delta`. No copy.

The full `tau` buffer is kept as a `Float32Array` of length
`2 * L * n_stripes` (the same shape the kernel uses), indexed as
`stripe * (2*L) + edge_id`.

### 5.4 ControlBar

- ⏯ play/pause toggle
- ⏮ ⏭ step ±1 frame
- Speed selector: `1×`, `4×`, `16×`, `max`
- Scrub bar: `<input type="range" min=0 max={N_frames-1}>` with hover preview
  of `frame.t` and `frame.v_b`
- Frame counter showing `frame.t` and the array index `i / N_frames`

Speed multipliers are interpreted as frames-advanced per animation tick
(`requestAnimationFrame`, ~60 Hz). `max` advances as many frames per tick as
the renderer can keep up with, capped so the tick budget stays under 16 ms.
Scrubbing always uses array index space; `frame.t` is read out of the trace
at the chosen index.

### 5.5 ConfigPanel + Run flow

1. User selects puzzle (dropdown from `/api/puzzles`), variant (dropdown from
   `/api/variants`), seed (integer, default = `Math.floor(Math.random()*1e9)`).
2. Optional "Advanced" disclosure exposes editable hyperparameters loaded from
   the variant's TOML defaults; edits become `config_overrides`.
3. Click **Run** → POST `/api/runs` → on success, replace `trace` store
   contents and reset `playback` to frame 0.
4. While in flight, the form disables and shows a spinner with elapsed time.

### 5.6 Save trace

Once a trace is loaded (from upload, file picker, or run), a "Save trace"
button issues `GET /api/traces/{id}.cbor`. For uploaded traces, the server
streams the original bytes back; for run traces, it streams the
just-generated CBOR.

### 5.7 Layer toggles

Single component with five checkboxes (walls, pheromone, walkers, best path,
waypoints) bound to a reactive object in the `playback` store. Each Layer
component reads its visibility flag.

## 6. Data Flow

```
File upload ─► /api/traces/upload ─► TraceJSON ─► trace store ─┐
File picker ─► useFileLoader (parse cbor in worker) ──────────┤
Run form ────► /api/runs ─────────► TraceJSON ────────────────┘
                                                                ▼
                                                  useTraceReplay
                                                        │
                                  ┌─────────────────────┼─────────────────────┐
                                  ▼                     ▼                     ▼
                            GridCanvas             FitnessChart           WalkerTable
                                  │
                                  └── playback store (current frame, speed, state)
                                          ▲
                                          └── ControlBar
```

All side-effects (mutating `playback.frame`) flow through Pinia actions. Components
are pure consumers of derived state.

## 7. Error Handling

**Backend** uses FastAPI exception handlers:

- `Puzzle not found` → 404 `{kind: "puzzle_not_found"}`.
- `Pydantic validation` (bad `config_overrides`, unknown variant) → 422 with
  field-level detail.
- `RunResult.infeasible == True` (puzzle fails feasibility precheck, so
  `RunResult.trace is None`) → 422 `{kind: "infeasible", detail:
  feasibility_reason}`. Corpus puzzles never trigger this in practice; the
  branch exists for safety.
- `RunResult.solved == False` with `infeasible == False` (iter cap reached
  without solution) → 200 with the full `TraceJSON`. The trace footer carries
  `solved=false`; the UI surfaces this in `FooterSummary`.
- Other unhandled exceptions → 500 `{kind: "internal", detail: str(e)}`.

**Frontend** has one `notifications` store and a single `ErrorToasts.vue`
mounted at the app root. Every API call routes errors through it. The trace
store rejects bad payloads (validated against `types.ts` Zod schemas)
without entering a half-loaded state — the previously loaded trace remains
visible.

## 8. Testing

**Backend:** `pytest` against FastAPI's `TestClient`.
- `test_traces_round_trip`: load fixture CBOR, round-trip through
  `/api/traces/upload`, assert frame count and footer match the on-disk file.
- `test_run_smoke`: POST `/api/runs` for a tiny synthetic puzzle, assert
  `solved=True`, frame count > 0.
- `test_invalid_overrides`: POST with garbage `config_overrides`, assert 422.

**Frontend:** `vitest` + `@vue/test-utils`.
- `useTraceReplay.spec.ts`: hand-built Trace fixture (3 frames, 4 edges),
  assert pheromone reconstruction is correct at every `t` and that
  checkpoint-based seek produces the same field as forward replay.
- `GridCanvas.spec.ts`: snapshot test with a fixed small Trace.
- `playback.spec.ts`: assert speed multipliers and step bounds.

**E2E:** `playwright` smoke. One golden-path test: launch backend +
frontend, upload a fixture CBOR via drag-drop, scrub to last frame,
assert `FooterSummary` reads "solved".

Coverage target: 80% on backend, ≥70% on frontend stores/composables.
Component snapshot/visual tests are best-effort.

## 9. Operations

**Dev:**

```bash
uv sync --extra viz
cd viz-web && bun install
# Terminal 1
uv run zipmould viz serve --reload
# Terminal 2
cd viz-web && bun run dev   # Vite at :5173 proxies /api to :8000
```

**Single-process run (after build):**

```bash
cd viz-web && bun run build           # outputs to ../src/zipmould/viz/static/
uv run zipmould viz serve              # FastAPI serves /api and static at :8000
```

`zipmould viz serve` is added to the existing Typer CLI (`src/zipmould/cli.py`).

**Dependencies:** add a `viz` extra in `pyproject.toml`:

```toml
[project.optional-dependencies]
viz = [
  "fastapi>=0.115,<1",
  "uvicorn[standard]>=0.32,<1",
  "python-multipart>=0.0.20,<1",
]
```

Frontend deps (managed via `bun`): `vue@^3.5`, `vue-router@^4.5`,
`pinia@^2.3`, `@vueuse/core`, `tailwindcss@^4`, `cbor-x` (for parsing CBOR
in a Web Worker), `vitest`, `@playwright/test`, `@vue/test-utils`.

Static assets are written into `src/zipmould/viz/static/` by the Vite
build. That path is gitignored; CI rebuilds it on demand.

## 10. Out of Scope (Reiteration for the Plan)

- Streaming during a run.
- Live editing of puzzles in-browser.
- Multi-trace overlays.
- User accounts, auth, deployment.
- Mobile / touch optimization (desktop-only target).

## 11. Open Questions

None blocking implementation. Future work:

- Should "Run" be cancellable mid-solve? Currently no — solves are short.
- Should the pheromone color scale auto-fit per frame or be fixed across
  the run? v1 ships **fixed** (better for visual continuity); revisit if
  contrast turns out to be poor on small `tau` ranges.
- Should `freeze_pheromone` from `solve()` be exposed in ConfigPanel? Not
  in v1 — it's an experimental knob unrelated to standard runs.
