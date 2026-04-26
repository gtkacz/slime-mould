"""HTTP route handlers for the viz API."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _get_version

from fastapi import APIRouter


def _resolve_zipmould_version() -> str:
    try:
        return _get_version("zipmould")
    except PackageNotFoundError:
        return "unknown"


ZIPMOULD_VERSION: str = _resolve_zipmould_version()

router = APIRouter(prefix="/api")


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness probe; returns the installed package version."""
    return {"status": "ok", "version": ZIPMOULD_VERSION}
