"""HTTP route handlers for the viz API."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _get_version

from fastapi import APIRouter

try:
    ZIPMOULD_VERSION: str = _get_version("zipmould")
except PackageNotFoundError:
    ZIPMOULD_VERSION = "unknown"

router = APIRouter(prefix="/api")


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness probe; returns the installed package version."""
    return {"status": "ok", "version": ZIPMOULD_VERSION}
