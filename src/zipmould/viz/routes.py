"""HTTP route handlers for the viz API."""

from __future__ import annotations

from importlib.metadata import version as _pkg_version

from fastapi import APIRouter

router = APIRouter(prefix="/api")


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness probe; returns the installed package version."""
    return {"status": "ok", "version": _pkg_version("zipmould")}
