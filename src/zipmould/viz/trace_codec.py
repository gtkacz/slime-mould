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
    TraceFooter,
    TraceHeader,
    _frame_from_dict,  # pyright: ignore[reportPrivateUsage]
    _trace_to_dict,  # pyright: ignore[reportPrivateUsage]
)


def trace_to_jsonable(trace: Trace) -> dict[str, Any]:
    """Convert `Trace` into a JSON-serialisable dict."""
    return cast("dict[str, Any]", _trace_to_dict(trace))


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
