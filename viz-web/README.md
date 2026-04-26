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
