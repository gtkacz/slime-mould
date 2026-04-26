"""HTTP-served visualizer for ZipMould solver runs.

This package exposes a FastAPI application that loads recorded `.cbor`
traces and runs synchronous solves against the puzzle corpus, returning
JSON-shaped traces consumable by the frontend.
"""

from __future__ import annotations

from zipmould.viz.server import create_app

__all__ = ["create_app"]
