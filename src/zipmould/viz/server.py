"""FastAPI application factory.

`create_app` returns a fully wired ASGI app. A single uvicorn process
both serves the API and (in production) the built frontend assets.
"""

from __future__ import annotations

from fastapi import FastAPI

from zipmould.viz.cache import TraceCache
from zipmould.viz.routes import ZIPMOULD_VERSION
from zipmould.viz.routes import router as api_router

_TRACE_CACHE_CAPACITY = 8


def create_app() -> FastAPI:
    app = FastAPI(title="ZipMould Visualizer", version=ZIPMOULD_VERSION)
    app.state.trace_cache = TraceCache(capacity=_TRACE_CACHE_CAPACITY)
    app.include_router(api_router)
    return app
