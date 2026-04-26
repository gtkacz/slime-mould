"""FastAPI application factory with custom error envelopes."""

from __future__ import annotations

from http import HTTPStatus
from typing import cast

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from zipmould.viz.cache import TraceCache
from zipmould.viz.routes import ZIPMOULD_VERSION
from zipmould.viz.routes import router as api_router

_TRACE_CACHE_CAPACITY = 8


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
    app.state.trace_cache = TraceCache(capacity=_TRACE_CACHE_CAPACITY)
    app.include_router(api_router)
    app.add_exception_handler(HTTPException, _http_exception_handler)  # pyright: ignore[reportArgumentType]
    app.add_exception_handler(RequestValidationError, _validation_handler)  # pyright: ignore[reportArgumentType]
    app.add_exception_handler(Exception, _generic_handler)
    return app
