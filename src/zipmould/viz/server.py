"""FastAPI application factory with custom error envelopes."""

from __future__ import annotations

import os
from http import HTTPStatus
from pathlib import Path
from typing import cast

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.responses import Response
from starlette.types import Scope

from zipmould.viz.cache import TraceCache
from zipmould.viz.routes import ZIPMOULD_VERSION
from zipmould.viz.routes import router as api_router

_TRACE_CACHE_CAPACITY = 8
_STATIC_DIR = Path(__file__).parent / "static"
_ALLOWED_ORIGINS_ENV = "ZIPMOULD_ALLOWED_ORIGINS"


class CacheBustingStaticFiles(StaticFiles):
    """Serve the SPA shell fresh while allowing hashed assets to be cached."""

    def file_response(
        self,
        full_path: os.PathLike[str] | str,
        stat_result: os.stat_result,
        scope: Scope,
        status_code: int = HTTPStatus.OK.value,
    ) -> Response:
        response = super().file_response(full_path, stat_result, scope, status_code)
        path = Path(full_path)
        if path.name == "index.html":
            response.headers["Cache-Control"] = "no-cache, max-age=0, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        elif path.parent.name == "assets":
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        else:
            response.headers["Cache-Control"] = "public, max-age=600"
        return response


def _allowed_origins_from_env() -> list[str]:
    raw = os.environ.get(_ALLOWED_ORIGINS_ENV, "")
    return [origin.strip().rstrip("/") for origin in raw.split(",") if origin.strip()]


def _http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail
    if isinstance(detail, dict) and "kind" in detail and "detail" in detail:
        d = cast(dict[str, str], detail)
        body = {"kind": str(d["kind"]), "detail": str(d["detail"])}
    else:
        body = {"kind": "http_error", "detail": str(detail)}
    return JSONResponse(status_code=exc.status_code, content=body)


def _validation_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    parts: list[str] = []
    for err in exc.errors():
        loc = ".".join(str(p) for p in err.get("loc", ()))
        msg = str(err.get("msg", ""))
        parts.append(f"{loc}: {msg}" if loc else msg)
    body = {"kind": "validation_error", "detail": "; ".join(parts) or "validation error"}
    return JSONResponse(status_code=HTTPStatus.UNPROCESSABLE_ENTITY.value, content=body)


def _generic_handler(_request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=HTTPStatus.INTERNAL_SERVER_ERROR.value,
        content={"kind": "internal", "detail": str(exc)},
    )


def create_app() -> FastAPI:
    app = FastAPI(title="ZipMould Visualizer", version=ZIPMOULD_VERSION)
    allowed_origins = _allowed_origins_from_env()
    if allowed_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=allowed_origins,
            allow_credentials=False,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["Content-Type"],
        )
    app.state.trace_cache = TraceCache(capacity=_TRACE_CACHE_CAPACITY)
    app.include_router(api_router)
    app.add_exception_handler(HTTPException, _http_exception_handler)  # pyright: ignore[reportArgumentType]
    app.add_exception_handler(RequestValidationError, _validation_handler)  # pyright: ignore[reportArgumentType]
    app.add_exception_handler(Exception, _generic_handler)
    if _STATIC_DIR.exists():
        app.mount("/", CacheBustingStaticFiles(directory=_STATIC_DIR, html=True), name="static")
    return app
